"""Hierarchical fzf navigation, previews, and markdown rendering."""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from om_search.commands import Command, list_groups
from om_search.config import Config, load_config
from om_search.index import (
    Candidate,
    CmdCandidate,
    DocCandidate,
    INDEX_FILENAME,
    build_candidates,
    load_index,
)
from om_search.manual import Section, extract_links, parse_manual_file
from om_search.paths import config_path, data_dir, manual_dir
from om_search.theme import color_enabled, fzf_color_spec, resolve_palette


# ---------------------------------------------------------------------------
# Existing preview/pager primitives


def section_text(cand: DocCandidate) -> str:
    """Read the selected section, preferring the pre-built index."""
    index_data = load_index(data_dir() / INDEX_FILENAME)
    if index_data is not None:
        sections, page_texts = index_data
        for section in sections:
            if (section.page_file, section.anchor, section.heading) == (
                cand.page_file,
                cand.anchor,
                cand.heading,
            ):
                return section.text
        return page_texts.get(cand.page_file, "")
    try:
        sections = parse_manual_file(manual_dir() / cand.page_file)
    except FileNotFoundError:
        return ""
    for section in sections:
        if section.anchor == cand.anchor and section.heading == cand.heading:
            return section.text
    return sections[0].text if sections else ""


def page_text(cand: DocCandidate) -> str:
    """Read the complete manual page for a document candidate."""
    index_data = load_index(data_dir() / INDEX_FILENAME)
    if index_data is not None:
        full = index_data[1].get(cand.page_file)
        if full:
            return full
    try:
        return (manual_dir() / cand.page_file).read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def heading_line(rendered: str, heading: str) -> int:
    """Return the 1-based line containing a rendered markdown heading."""
    target = re.sub(r"\s+", " ", heading).strip()
    if not target:
        return 0
    fallback = 0
    for i, line in enumerate(rendered.splitlines(), start=1):
        clean = re.sub(r"\s+", " ", _ANSI_RE.sub("", line)).strip()
        if target in clean:
            if "#" in clean:
                return i
            if not fallback:
                fallback = i
    return fallback


def action_for(cand: Candidate) -> tuple[str, str]:
    """Return the legacy post-selection action for a candidate."""
    if cand.type == "doc":
        return ("view", page_text(cast(DocCandidate, cand)))
    return ("echo", cast(CmdCandidate, cand).path)


def render_markdown(text: str) -> str:
    """Render markdown with glow, mdcat, bat, or plain text fallback."""
    if not color_enabled():
        if shutil.which("glow"):
            try:
                result = subprocess.run(
                    ["glow", "-s", "notty", "-"],
                    input=text,
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0 and result.stdout:
                    return result.stdout
            except OSError:
                pass
        return text
    renderers = [
        ["glow", "-s", "auto", "-"],
        ["mdcat", "--ansi", "-"],
        ["bat", "--language=md", "--color=always", "--paging=never", "--decorations=never", "-"],
    ]
    for command in renderers:
        if not shutil.which(command[0]):
            continue
        try:
            result = subprocess.run(command, input=text, capture_output=True, text=True)
        except OSError:
            continue
        if result.returncode == 0 and result.stdout:
            return result.stdout
    return text


_ESC_LESSKEY_SRC = "#command\n\\e quit\n"


def _esc_lesskey_file() -> str | None:
    """Write the lesskey source binding Escape to quit."""
    path = data_dir() / "esc.lesskey"
    try:
        if path.read_text(encoding="utf-8") != _ESC_LESSKEY_SRC:
            path.write_text(_ESC_LESSKEY_SRC, encoding="utf-8")
        return str(path)
    except FileNotFoundError:
        try:
            path.write_text(_ESC_LESSKEY_SRC, encoding="utf-8")
            return str(path)
        except OSError:
            return None
    except OSError:
        return None


_LESS_PROMPT = "-Psq/Esc: back  ·  ↑↓/jk: scroll  ·  /: search"


def view_markdown(text: str, jump_to: str | None = None) -> None:
    """Render markdown in less when interactive, otherwise write stdout."""
    rendered = render_markdown(text)
    if sys.stdout.isatty() and shutil.which("less"):
        args = ["less", "-R", _LESS_PROMPT]
        if jump_to:
            line = heading_line(rendered, jump_to)
            if line:
                args.append(f"+{line}")
        env = os.environ.copy()
        keyfile = _esc_lesskey_file()
        if keyfile:
            env["LESSKEYIN"] = keyfile
        subprocess.run(args, input=rendered.encode(), env=env, check=False)
        return
    if not rendered.endswith("\n"):
        rendered += "\n"
    sys.stdout.write(rendered)


# ---------------------------------------------------------------------------
# Dataset model


@dataclass(frozen=True)
class NavRow:
    """One exact seven-field row consumed by fzf."""

    kind: str
    row_id: str
    target_route_id: str
    parent_route_id: str
    preview_id: str
    display: str
    search_text: str

    def wire(self) -> str:
        fields = (
            self.kind,
            self.row_id,
            self.target_route_id,
            self.parent_route_id,
            self.preview_id,
            self.display,
            self.search_text,
        )
        return "\t".join(field.replace("\t", " ").replace("\n", " ") for field in fields)


@dataclass
class NavigationDataset:
    """A temporary, mode-0700 complete navigation dataset."""

    temporary: tempfile.TemporaryDirectory[str]
    manifest: dict[str, Any]
    entry_routes: dict[str, str]

    @property
    def path(self) -> Path:
        return Path(self.temporary.name)

    def __enter__(self) -> NavigationDataset:
        return self

    def __exit__(self, *_: object) -> None:
        self.temporary.cleanup()


def _plain_search(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[`*_#]", "", text)).strip()


def _hint(cfg: Config, *, reading: bool, home: bool = False) -> str:
    configured = f"{_fmt_key(cfg.keys.get('down', 'ctrl-j'))}/{_fmt_key(cfg.keys.get('up', 'ctrl-k'))}"
    if reading:
        return f"↑↓ move cursor · PgUp/PgDn page cursor · {configured} move · Tab/Enter focus · Esc/← back · ? keys"
    if home:
        return f"↑↓ select · PgUp/PgDn page · {configured} move · Enter/→ open · Tab focus reader · Esc quit · ? keys"
    return f"↑↓ select · PgUp/PgDn page · {configured} move · Enter/→ open · Tab focus reader · Esc/← back · ? keys"


def route_hint(cfg: Config, route_id: str, reading: bool = False) -> str:
    """Return the generic route-aware hint used by transition helpers."""
    del route_id
    return _hint(cfg, reading=reading)


def _add_file(path: Path, text: str) -> str:
    path.write_text(text, encoding="utf-8")
    return path.name


def _candidate_preview_files(
    root: Path,
    preview_id: str,
    section: Section | None,
    full_text: str,
) -> tuple[str, str]:
    preview_file = _add_file(root / f"preview-{preview_id}.txt", section.text if section else full_text)
    full_file = _add_file(root / f"full-{preview_id}.txt", full_text)
    return preview_file, full_file


def build_navigation_dataset(
    sections: list[Section],
    commands: list[Command],
    *,
    cfg: Config | None = None,
    page_texts: dict[str, str] | None = None,
) -> NavigationDataset:
    """Materialize all fixed routes, rows, previews, and opaque numeric IDs."""
    cfg = cfg or load_config()
    page_texts = page_texts or {}
    temporary = tempfile.TemporaryDirectory(prefix="om-search-nav-")
    root = Path(temporary.name)
    root.chmod(0o700)
    routes: dict[str, dict[str, Any]] = {}
    rows_manifest: dict[str, dict[str, Any]] = {}
    previews: dict[str, dict[str, Any]] = {}
    route_rows: dict[str, list[NavRow]] = {}
    next_route = 1
    next_row = 1
    next_preview = 1

    def rid() -> str:
        nonlocal next_route
        value = str(next_route)
        next_route += 1
        return value

    def rowid() -> str:
        nonlocal next_row
        value = str(next_row)
        next_row += 1
        return value

    def pid() -> str:
        nonlocal next_preview
        value = str(next_preview)
        next_preview += 1
        return value

    def add_route(name: str, parent: str, breadcrumb: str) -> str:
        route_id = rid()
        routes[route_id] = {
            "name": name,
            "parent_route_id": parent,
            "breadcrumb": breadcrumb,
            "hint": _hint(cfg, reading=False, home=name == "home"),
            "rows_file": "",
        }
        route_rows[route_id] = []
        return route_id

    def add_preview(
        section: Section | None,
        page_file: str,
        anchor: str,
        heading: str,
        full_text: str,
    ) -> str:
        preview_id = pid()
        preview_file, full_file = _candidate_preview_files(root, preview_id, section, full_text)
        previews[preview_id] = {
            "file": preview_file,
            "full_file": full_file,
            "page_file": page_file,
            "anchor": anchor,
            "heading": heading,
        }
        return preview_id

    def add_row(
        route_id: str,
        kind: str,
        display: str,
        search_text: str,
        *,
        target: str = "0",
        parent: str | None = None,
        preview: str = "0",
        payload: str = "",
        page_file: str = "",
        anchor: str = "",
        heading: str = "",
    ) -> NavRow:
        row_id = rowid()
        parent_id = parent if parent is not None else str(routes[route_id]["parent_route_id"])
        row = NavRow(kind, row_id, target, parent_id, preview, display, search_text)
        route_rows[route_id].append(row)
        rows_manifest[row_id] = {
            "kind": kind,
            "route_id": route_id,
            "target_route_id": target,
            "parent_route_id": parent_id,
            "preview_id": preview,
            "display": display,
            "search_text": search_text,
            "payload": payload,
            "page_file": page_file,
            "anchor": anchor,
            "heading": heading,
        }
        return row

    def section_for(page_file: str, anchor: str) -> Section | None:
        matches = [s for s in sections if s.page_file == page_file and (not anchor or s.anchor == anchor)]
        return matches[0] if matches else None

    # Fixed top-level routes.
    home = add_route("home", "0", "Home")
    search_all = add_route("search:all", home, "Home › Search all")
    search_doc = add_route("search:doc", home, "Home › Documentation")
    search_cmd = add_route("search:cmd", home, "Home › Commands")
    pages = add_route("pages", home, "Home › Manual pages")
    groups = add_route("groups", home, "Home › Command groups") if commands else "0"

    add_row(home, "route", "Search all", "Search all", target=search_all, parent="0")
    add_row(home, "route", "Manual pages", "Manual pages", target=pages, parent="0")
    if groups != "0":
        add_row(home, "route", "Command groups", "Command groups", target=groups, parent="0")

    page_routes: dict[str, str] = {}
    page_info: dict[str, tuple[int, str]] = {}
    for section in sorted(sections, key=lambda s: (s.page_number, s.heading)):
        if section.page_file not in page_routes:
            breadcrumb = f"Home › Manual pages › {section.page_title}"
            page_routes[section.page_file] = add_route(f"page:{section.page_file}", pages, breadcrumb)
            page_info[section.page_file] = (section.page_number, section.page_title)
    for page_file, route_id in page_routes.items():
        number, title = page_info[page_file]
        add_row(pages, "route", f"{number:02d}  {title}  ({page_file})", f"{title} {page_file}", target=route_id, parent=home)

    group_routes: dict[str, str] = {}
    for group in list_groups(commands):
        group_routes[group] = add_route(f"group:{group}", groups, f"Home › Command groups › {group}")
        add_row(groups, "route", f"omarchy {group}", group, target=group_routes[group], parent=home)

    # Make the complete set of search rows and scoped page/group rows.
    docs_by_key: dict[tuple[str, str, str], Section] = {
        (s.page_file, s.anchor, s.heading): s for s in sections
    }
    links_routes: dict[tuple[str, str], str] = {}

    def make_doc_row(route_id: str, section: Section, parent: str) -> None:
        full = page_texts.get(section.page_file, section.text)
        preview = add_preview(section, section.page_file, section.anchor, section.heading, full)
        display = f"[doc] {section.page_title} / {section.heading}" if section.heading else f"[doc] {section.page_title}"
        links_key = (route_id, section.page_file)
        if links_key not in links_routes:
            seen: set[tuple[str, str]] = set()
            valid_links: list[tuple[str, str, str, Section]] = []
            for label, page, anchor in extract_links(full):
                if (page, anchor) in seen:
                    continue
                seen.add((page, anchor))
                target_section = section_for(page, anchor)
                if target_section is not None:
                    valid_links.append((label, page, anchor, target_section))
            if not valid_links:
                links_routes[links_key] = "0"
            else:
                link_route = add_route(
                    f"links:{section.page_file}",
                    route_id,
                    f"{routes[route_id]['breadcrumb']} › Links: {section.page_title}",
                )
                links_routes[links_key] = link_route
                for label, page, anchor, target_section in valid_links:
                    target_full = page_texts.get(page, target_section.text)
                    target_preview = add_preview(
                        target_section, page, target_section.anchor,
                        target_section.heading, target_full,
                    )
                    target = f"{page}#{anchor}" if anchor else page
                    add_row(
                        link_route,
                        "link",
                        f"{label}  →  {target}",
                        f"{label} {target}",
                        preview=target_preview,
                        parent=route_id,
                        page_file=page,
                        anchor=target_section.anchor,
                        heading=target_section.heading,
                    )
        add_row(
            route_id,
            "doc",
            display,
            f"{display} {_plain_search(section.text)}",
            target=links_routes[links_key],
            parent=parent,
            preview=preview,
            page_file=section.page_file,
            anchor=section.anchor,
            heading=section.heading,
        )

    def make_cmd_row(route_id: str, command: Command, parent: str) -> None:
        display = f"[cmd] {command.path}  ::  {command.description}"
        preview = add_preview(None, "", "", "", command.description)
        add_row(
            route_id,
            "cmd",
            display,
            display,
            parent=parent,
            preview=preview,
            payload=command.path,
        )

    candidates_by_route: dict[str, list[Candidate]] = {
        search_all: build_candidates(sections, commands, "all"),
        search_doc: build_candidates(sections, commands, "doc"),
        search_cmd: build_candidates(sections, commands, "cmd"),
    }
    for route_id, candidates in candidates_by_route.items():
        for candidate in candidates:
            if candidate.type == "doc":
                doc = cast(DocCandidate, candidate)
                matched_section = docs_by_key.get((doc.page_file, doc.anchor, doc.heading))
                if matched_section is not None:
                    make_doc_row(route_id, matched_section, home)
            else:
                cmd_candidate = cast(CmdCandidate, candidate)
                matching = next((c for c in commands if c.path == cmd_candidate.path), None)
                if matching is not None:
                    make_cmd_row(route_id, matching, home)

    for page_file, route_id in page_routes.items():
        for section in sorted((s for s in sections if s.page_file == page_file), key=lambda s: s.heading):
            make_doc_row(route_id, section, pages)
    for group, route_id in group_routes.items():
        for command in sorted((c for c in commands if c.group == group), key=lambda c: c.path):
            make_cmd_row(route_id, command, groups)

    for route_id, rows in route_rows.items():
        rows_file = root / f"route-{route_id}.tsv"
        rows_file.write_text("".join(row.wire() + "\n" for row in rows), encoding="utf-8")
        routes[route_id]["rows_file"] = rows_file.name

    manifest: dict[str, Any] = {
        "version": 1,
        "routes": routes,
        "rows": rows_manifest,
        "previews": previews,
        "entry_routes": {
            "home": home,
            "search:all": search_all,
            "search:doc": search_doc,
            "search:cmd": search_cmd,
            "pages": pages,
            "groups": groups,
            "page": page_routes,
            "group": group_routes,
        },
    }
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return NavigationDataset(temporary, manifest, {"home": home, "search:all": search_all, "search:doc": search_doc, "search:cmd": search_cmd, "pages": pages, "groups": groups, **{f"page:{k}": v for k, v in page_routes.items()}, **{f"group:{k}": v for k, v in group_routes.items()}})


def _load_manifest(dataset_dir: Path) -> dict[str, Any]:
    """Validate and load a private navigation dataset manifest."""
    root = dataset_dir.expanduser().resolve()
    if not root.is_dir() or root.stat().st_mode & 0o077:
        raise ValueError("invalid navigation dataset directory")
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file() or manifest_path.resolve().parent != root:
        raise ValueError("invalid navigation manifest")
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("invalid navigation manifest") from exc
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("invalid navigation manifest")
    for key in ("routes", "rows", "previews"):
        if not isinstance(data.get(key), dict):
            raise ValueError("invalid navigation manifest")
    return data


def _decimal_id(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9]+", value))


def _manifest_item(manifest: dict[str, Any], section: str, value: str) -> dict[str, Any]:
    if not _decimal_id(value):
        raise ValueError("invalid navigation id")
    item = manifest[section].get(value)
    if not isinstance(item, dict):
        raise ValueError("unknown navigation id")
    return item

def navigation_rows(dataset_dir: Path, route_id: str) -> str:
    manifest = _load_manifest(dataset_dir)
    route = _manifest_item(manifest, "routes", route_id)
    rows_file = route.get("rows_file")
    if not isinstance(rows_file, str):
        raise ValueError("invalid navigation route")
    root = dataset_dir.expanduser().resolve()
    path = root / rows_file
    if path.resolve().parent != root or not path.is_file():
        raise ValueError("invalid navigation rows")
    return path.read_text(encoding="utf-8")


def navigation_preview(dataset_dir: Path, preview_id: str) -> str:
    manifest = _load_manifest(dataset_dir)
    if preview_id == "0":
        return ""
    preview = _manifest_item(manifest, "previews", preview_id)
    filename = preview.get("file")
    if not isinstance(filename, str):
        raise ValueError("invalid navigation preview")
    root = dataset_dir.expanduser().resolve()
    path = root / filename
    if path.resolve().parent != root or not path.is_file():
        raise ValueError("invalid navigation preview")
    return path.read_text(encoding="utf-8")

def _reader_preview_path(
    root: Path, manifest: dict[str, Any], preview_id: str
) -> Path:
    preview = _manifest_item(manifest, "previews", preview_id)
    filename = preview.get("file")
    if not isinstance(filename, str):
        raise ValueError("invalid navigation preview")
    path = root / filename
    if path.resolve().parent != root or not path.is_file():
        raise ValueError("invalid navigation preview")
    return path


def _reader_state_paths(root: Path, preview_id: str) -> tuple[Path, Path]:
    cache = root / f"reader-{preview_id}.ansi"
    cursor = root / f"cursor-{preview_id}.txt"
    if cache.resolve().parent != root or cursor.resolve().parent != root:
        raise ValueError("invalid navigation reader state")
    return cache, cursor


def _reader_rendered(
    root: Path, manifest: dict[str, Any], preview_id: str
) -> str:
    cache, _ = _reader_state_paths(root, preview_id)
    if cache.is_file():
        return cache.read_text(encoding="utf-8")
    source = _reader_preview_path(root, manifest, preview_id).read_text(encoding="utf-8")
    rendered = render_markdown(source)
    cache.write_text(rendered, encoding="utf-8")
    return rendered


def _reader_cursor_path(root: Path, preview_id: str) -> Path:
    _, cursor = _reader_state_paths(root, preview_id)
    return cursor


def _reader_detail_paths(root: Path, preview_id: str) -> tuple[Path, Path]:
    column = root / f"cursor-column-{preview_id}.txt"
    mode = root / f"cursor-mode-{preview_id}.txt"
    if column.resolve().parent != root or mode.resolve().parent != root:
        raise ValueError("invalid navigation reader state")
    return column, mode


def _read_reader_cursor(cursor_path: Path) -> int:
    try:
        value = cursor_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return 0
    if not re.fullmatch(r"[0-9]+", value.strip()):
        raise ValueError("invalid navigation reader cursor")
    return int(value.strip())


def _read_detail(path: Path, default: str) -> str:
    try:
        value = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return default
    return value


def _write_reader_cursor(cursor_path: Path, cursor: int, root: Path) -> None:
    fd, temporary = tempfile.mkstemp(prefix=f".{cursor_path.name}.", dir=str(root), text=True)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(str(cursor))
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.replace(cursor_path)
    except BaseException:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass
        raise


def _write_detail(path: Path, value: str, root: Path) -> None:
    _write_reader_cursor(path, int(value) if value.isdigit() else 0, root) if path.name.startswith("cursor-column-") else path.write_text(value, encoding="utf-8")


def _reader_lines(dataset_dir: Path, preview_id: str) -> tuple[Path, list[str]]:
    manifest = _load_manifest(dataset_dir)
    if preview_id == "0":
        raise ValueError("navigation reader requires a preview id")
    _manifest_item(manifest, "previews", preview_id)
    root = dataset_dir.expanduser().resolve()
    rendered = _reader_rendered(root, manifest, preview_id)
    return root, rendered.splitlines()


def navigation_reader_move(
    dataset_dir: Path, preview_id: str, movement: str, viewport_lines: int = 24
) -> int:
    """Move the line, word, or character cursor for one document preview."""
    allowed = {"reset", "up", "down", "page-up", "page-down", "left", "right",
               "word-left", "word-right", "toggle-mode"}
    if movement not in allowed:
        raise ValueError("invalid navigation reader movement")
    root, lines = _reader_lines(dataset_dir, preview_id)
    if viewport_lines <= 0:
        raise ValueError("invalid navigation reader viewport")
    cursor_path = _reader_cursor_path(root, preview_id)
    column_path, mode_path = _reader_detail_paths(root, preview_id)
    line = _read_reader_cursor(cursor_path)
    column = int(_read_detail(column_path, "0"))
    mode = _read_detail(mode_path, "word")
    if movement == "toggle-mode":
        mode = "char" if mode == "word" else "word"
    elif lines:
        if movement == "reset":
            line, column = 0, 0
        elif movement in {"up", "down", "page-up", "page-down"}:
            step = 1 if movement in {"up", "down"} else max(1, viewport_lines - 2)
            line = max(0, min(line + (-step if movement in {"up", "page-up"} else step), len(lines) - 1))
            column = min(column, len(lines[line]))
        else:
            text = lines[line]
            if movement in {"left", "word-left"}:
                if movement == "word-left":
                    column = max(0, text.rfind(" ", 0, max(0, column - 1)) + 1)
                else:
                    column = max(0, column - 1)
            else:
                if movement == "word-right":
                    match = re.search(r"\s+", text[column:])
                    column = len(text) if not match else min(len(text), column + match.end())
                else:
                    column = min(len(text), column + 1)
    _write_reader_cursor(cursor_path, line, root)
    _write_reader_cursor(column_path, column, root)
    mode_path.write_text(mode, encoding="utf-8")
    return line


def navigation_reader_preview(
    dataset_dir: Path, preview_id: str, viewport_lines: int = 24
) -> str:
    """Return a centered viewport with a word or character cursor."""
    root, lines = _reader_lines(dataset_dir, preview_id)
    if viewport_lines <= 0:
        raise ValueError("invalid navigation reader viewport")
    if not lines:
        return "Line 0/0\n"
    cursor_path = _reader_cursor_path(root, preview_id)
    column_path, mode_path = _reader_detail_paths(root, preview_id)
    line = max(0, min(_read_reader_cursor(cursor_path), len(lines) - 1))
    column = max(0, min(int(_read_detail(column_path, "0")), len(lines[line])))
    mode = _read_detail(mode_path, "word")
    content_lines = max(1, viewport_lines - 1)
    start = max(0, min(line - content_lines // 2, len(lines) - content_lines))
    rows: list[str] = []
    for index in range(start, min(len(lines), start + content_lines)):
        text = lines[index]
        if index != line:
            rows.append(f"  {text}")
            continue
        if mode == "char" and column < len(text):
            if color_enabled():
                marked = text[:column] + "\x1b[7m" + text[column] + "\x1b[0m" + text[column + 1:]
            else:
                marked = text[:column] + "|" + text[column] + "|" + text[column + 1:]
        else:
            marked = text
        rows.append(f"▶ {marked}")
    return "\n".join([f"Line {line + 1}/{len(lines)}", *rows]) + "\n"


def navigation_row(dataset_dir: Path, row_id: str, *, kinds: set[str] | None = None) -> dict[str, Any]:
    manifest = _load_manifest(dataset_dir)
    row = _manifest_item(manifest, "rows", row_id)
    if kinds is not None and row.get("kind") not in kinds:
        raise ValueError("navigation row kind mismatch")
    return row
def navigation_full_text(dataset_dir: Path, row_id: str) -> tuple[str, str]:
    """Return validated full-page text and heading for a document row."""
    manifest = _load_manifest(dataset_dir)
    row = _manifest_item(manifest, "rows", row_id)
    preview_id = row.get("preview_id")
    if not isinstance(preview_id, str):
        raise ValueError("invalid navigation preview")
    preview = _manifest_item(manifest, "previews", preview_id)
    filename = preview.get("full_file")
    if not isinstance(filename, str):
        raise ValueError("invalid navigation full page")
    root = dataset_dir.expanduser().resolve()
    path = root / filename
    if path.resolve().parent != root or not path.is_file():
        raise ValueError("invalid navigation full page")
    return path.read_text(encoding="utf-8"), str(row.get("heading", ""))



def navigation_route(dataset_dir: Path, route_id: str) -> dict[str, Any]:
    manifest = _load_manifest(dataset_dir)
    return _manifest_item(manifest, "routes", route_id)


def _action_text(value: str) -> str:
    return value.replace(")", "\\)")


def navigation_transition_action(
    dataset_dir: Path,
    route_id: str,
    *,
    enter_kind: str = "",
    focus_kind: str = "",
    parent_route_id: str = "0",
    row_id: str = "",
    links: bool = False,
) -> str:
    """Produce one fzf transform action for a validated route transition."""
    manifest = _load_manifest(dataset_dir)
    root = dataset_dir.expanduser().resolve()
    dataset_arg = shlex.quote(str(root))
    cfg = load_config()
    row: dict[str, Any] | None = None
    if row_id:
        row = _manifest_item(manifest, "rows", row_id)
        expected_kind = enter_kind or focus_kind
        if expected_kind and row.get("kind") != expected_kind:
            raise ValueError("navigation row kind mismatch")
    current_route_id = str(row.get("route_id", parent_route_id)) if row else parent_route_id
    if links and route_id == "0":
        parent = navigation_route(root, current_route_id)
        header = f"No links on this page · {parent['breadcrumb']} · {_hint(cfg, reading=True)}"
        return f"change-header({_action_text(header)})+refresh-preview"
    if focus_kind in {"doc", "link"}:
        parent = navigation_route(root, current_route_id)
        header = f"{parent['breadcrumb']} · {_hint(cfg, reading=True)}"
        return (
            f"change-header({_action_text(header)})+"
            f"execute-silent(om-search nav-reader-move {dataset_arg} {{5}} reset \"$FZF_PREVIEW_LINES\")+"
            "change-prompt(  reading  )+"
            f"change-preview(om-search nav-reader-preview {dataset_arg} {{5}} \"$FZF_PREVIEW_LINES\")+"
            "change-preview-window(right,90%,wrap,border-rounded)+refresh-preview"
        )
    if enter_kind in {"doc", "link"}:
        parent = navigation_route(root, current_route_id)
        header = f"{parent['breadcrumb']} · {_hint(cfg, reading=True)}"
        return (
            f"change-header({_action_text(header)})+"
            f"execute-silent(om-search nav-reader-move {dataset_arg} {{5}} reset \"$FZF_PREVIEW_LINES\")+"
            "change-prompt(  reading  )+"
            f"change-preview(om-search nav-reader-preview {dataset_arg} {{5}} \"$FZF_PREVIEW_LINES\")+"
            "change-preview-window(right,90%,wrap,border-rounded)+refresh-preview"
        )
    if enter_kind == "cmd":
        return "accept"
    if not _decimal_id(route_id) or route_id not in manifest["routes"]:
        return "abort"
    route = manifest["routes"][route_id]
    breadcrumb = str(route["breadcrumb"])
    hint = str(route["hint"])
    return (
        f"reload-sync(om-search nav-data {dataset_arg} {route_id})+"
        f"change-header({_action_text(breadcrumb + ' · ' + hint)})+"
        "change-prompt(  )+clear-query+refresh-preview"
    )


# ---------------------------------------------------------------------------
# fzf interface


def picker_header(mode: str = "all", page_filter: str | None = None, group_filter: str | None = None) -> str:
    """Legacy compact header helper retained for callers and docs."""
    scope = {"doc": "docs only", "cmd": "commands only"}.get(mode, "all sources")
    parts = [scope]
    if page_filter:
        parts.append(f"page: {page_filter}")
    if group_filter:
        parts.append(f"group: {group_filter}")
    return "Mode: " + ", ".join(parts)

_KEY_LABELS: list[tuple[str, str]] = [
    ("down", "Move down"),
    ("up", "Move up"),
    ("half_page_down", "Half page cursor down"),
    ("half_page_up", "Half page cursor up"),
    ("preview_down", "Page cursor down"),
    ("preview_up", "Page cursor up"),
    ("open", "Open selection"),
    ("copy", "Copy command"),
    ("help", "Show this help"),
]


def _fmt_key(key: str) -> str:
    return " + ".join(part.capitalize() for part in key.split("-"))


def keys_cheatsheet(cfg: Config | None = None) -> str:
    """Return the contextual keybinding cheatsheet."""
    cfg = cfg or load_config()
    lines = ["om-search — keybindings", "", "  Built-in selector keys", "  Up / Down          select or move cursor by line", "  PageUp / PageDown  page lists or cursor", "  Left / Right       character cursor in reader", "  Alt-Left / Alt-Right word cursor in reader", "  Ctrl-]             toggle cursor mode", "  Enter / Right      open or descend", "  Tab                focus / unfocus reader", "  Left / Escape      back (Escape quits at Home)", ""]
    for action, label in _KEY_LABELS:
        key = cfg.keys.get(action, "")
        if key:
            lines.append(f"  {label:<20} {_fmt_key(key)}")
    lines += [
        "  Open full page       Ctrl + O",
        "  Follow links         Ctrl + L",
        "  Back / quit          Esc  (also Ctrl + C)",
        "",
        "Type to fuzzy-search titles and body text.",
        "(Plain letters remain search input.)",
        f"Rebind additional Ctrl chords in {config_path()}",
    ]
    return "\n".join(lines) + "\n"


def _base_fzf_args(cfg: Config) -> list[str]:
    args = ["--layout=reverse", "--border=rounded", "--border-label= om-search ", "--prompt=  ", "--pointer=▶", "--marker=✓", "--info=inline"]
    if not color_enabled():
        args += ["--color", "bw"]
    else:
        palette = resolve_palette(cfg.theme_source, cfg.theme_custom)
        if palette:
            spec = fzf_color_spec(palette)
            if spec:
                args += ["--color", spec]
    return args


def _movement_transform(
    dataset_arg: str, key: str, list_action: str, reader_movement: str
) -> str:
    reader_action = (
        f"execute-silent(om-search nav-reader-move {dataset_arg} {{5}} "
        f"{reader_movement} \\\"$FZF_PREVIEW_LINES\\\")+refresh-preview"
    )
    return (
        f"{key}:transform:[[ \"$FZF_PROMPT\" == *reading* ]] && echo \"{reader_action}\" || "
        f"echo \"change-prompt(  )+change-preview(om-search nav-preview {dataset_arg} {{5}})+{list_action}+refresh-preview\""
    )


def run_fzf(
    dataset_dir: Path | str,
    route_id: str,
    query: str = "",
    cfg: Config | None = None,
) -> str | None:
    """Run one fzf process for the complete hierarchical session."""
    cfg = cfg or load_config()
    root = Path(dataset_dir).expanduser().resolve()
    initial = navigation_rows(root, route_id)
    route = navigation_route(root, route_id)
    dataset_arg = shlex.quote(str(root))
    preview_cmd = f"om-search nav-preview {dataset_arg} {{5}}"
    reader_preview_cmd = f"om-search nav-reader-preview {dataset_arg} {{5}} \\\"$FZF_PREVIEW_LINES\\\""
    normal_window = "right,60%,wrap,border-rounded"
    cmd = ["fzf"] + _base_fzf_args(cfg) + [
        "--tiebreak=begin,end",
        "--ansi",
        "--delimiter", "\t",
        "--with-nth", "6,7",
        "--preview", preview_cmd,
        "--preview-window", normal_window,
        "--header", f"{route['breadcrumb']}\n{route['hint']}",
    ]

    # Built-in arrows/page keys are always available; configured chords are extra.
    movement_binds = [
        _movement_transform(dataset_arg, "down", "down", "down"),
        _movement_transform(dataset_arg, "up", "up", "up"),
        _movement_transform(dataset_arg, "pgdn", "page-down", "page-down"),
        _movement_transform(dataset_arg, "pgup", "page-up", "page-up"),
        _movement_transform(dataset_arg, cfg.keys.get("down", "ctrl-j"), "down", "down"),
        _movement_transform(dataset_arg, cfg.keys.get("up", "ctrl-k"), "up", "up"),
        _movement_transform(dataset_arg, cfg.keys.get("half_page_down", "ctrl-d"), "half-page-down", "page-down"),
        _movement_transform(dataset_arg, cfg.keys.get("half_page_up", "ctrl-u"), "half-page-up", "page-up"),
    ]
    for bind in movement_binds:
        if bind.split(":", 1)[0]:
            cmd += ["--bind", bind]
    for key, movement in (
        ("left", "left"),
        ("right", "right"),
        ("alt-left", "word-left"),
        ("alt-right", "word-right"),
        ("ctrl-]", "toggle-mode"),
    ):
        cmd += ["--bind", f"{key}:transform:[[ \"$FZF_PROMPT\" == *reading* ]] && echo \"execute-silent(om-search nav-reader-move {dataset_arg} {{5}} {movement} \\\"$FZF_PREVIEW_LINES\\\")+refresh-preview\" || echo refresh-preview"]

    # Preview-only configured keys page the reader while focused.
    for key, reader_movement, list_action in (
        (cfg.keys.get("preview_down", "ctrl-f"), "page-down", "preview-down"),
        (cfg.keys.get("preview_up", "ctrl-b"), "page-up", "preview-up"),
    ):
        if key:
            action = (
                f"transform:[[ \"$FZF_PROMPT\" == *reading* ]] && echo "
                f"\"execute-silent(om-search nav-reader-move {dataset_arg} {{5}} "
                f"{reader_movement} \\\"$FZF_PREVIEW_LINES\\\")+refresh-preview\" || "
                f"echo \"change-preview({preview_cmd})+{list_action}+refresh-preview\""
            )
            cmd += ["--bind", f"{key}:{action}"]

    enter = f"om-search nav-transition {dataset_arg} {{3}} --enter {{1}} {{4}} --row {{2}}"
    cmd += ["--bind", f"enter:transform:[[ \"$FZF_PROMPT\" == *reading* ]] && echo refresh-preview || {enter}"]
    cmd += ["--bind", f"right:transform:[[ \"$FZF_PROMPT\" == *reading* ]] && echo refresh-preview || {enter}"]
    focus = f"om-search nav-transition {dataset_arg} 0 --focus {{1}} {{4}} --row {{2}}"
    cmd += ["--bind", f"tab:transform:[[ \"$FZF_PROMPT\" == *reading* ]] && echo \"change-prompt(  )+change-preview({preview_cmd})+change-preview-window({normal_window})+refresh-preview\" || ([[ {{1}} == doc || {{1}} == link ]] && {focus} || echo refresh-preview)"]
    cmd += ["--bind", f"left:transform:[[ \"$FZF_PROMPT\" == *reading* ]] && echo \"change-prompt(  )+change-preview({preview_cmd})+change-preview-window({normal_window})+refresh-preview\" || om-search nav-transition {dataset_arg} {{4}}"]
    cmd += ["--bind", f"esc:transform:[[ \"$FZF_PROMPT\" == *reading* ]] && echo \"change-prompt(  )+change-preview({preview_cmd})+change-preview-window({normal_window})+refresh-preview\" || om-search nav-transition {dataset_arg} {{4}}"]
    cmd += ["--bind", f"ctrl-o:transform:[[ {{1}} == doc || {{1}} == link ]] && echo \"execute(om-search nav-open {dataset_arg} {{2}})\" || echo refresh-preview"]
    cmd += ["--bind", f"ctrl-l:transform:[[ \"$FZF_PROMPT\" == *reading* ]] && [[ {{1}} == doc || {{1}} == link ]] && om-search nav-transition {dataset_arg} {{3}} --links {{4}} --row {{2}} || echo refresh-preview"]

    copy = cfg.keys.get("copy")
    if copy:
        cmd += ["--bind", f"{copy}:transform:[[ {{1}} == cmd ]] && echo \"execute-silent(om-search nav-copy {dataset_arg} {{2}})+accept\" || echo refresh-preview"]
    help_key = cfg.keys.get("help")
    if help_key:
        help_action = (
            f"transform:[[ \"$FZF_PROMPT\" == *'reading help'* ]] && echo "
            f"\"change-prompt(  reading  )+change-preview({reader_preview_cmd})+refresh-preview\" || "
            f"[[ \"$FZF_PROMPT\" == *reading* ]] && echo "
            f"\"change-prompt(  reading help  )+change-preview(om-search --keys)+refresh-preview\" || "
            f"[[ \"$FZF_PROMPT\" == *help* ]] && echo "
            f"\"change-prompt(  )+change-preview({preview_cmd})+refresh-preview\" || "
            f"echo \"change-prompt(  help  )+change-preview(om-search --keys)+refresh-preview\""
        )
        cmd += ["--bind", f"{help_key}:{help_action}"]

    if query:
        cmd += ["--query", query]
    result = subprocess.run(cmd, input=initial, text=True, capture_output=True)
    for line in result.stdout.splitlines():
        if line.strip():
            fields = line.split("\t")
            if len(fields) >= 2 and _decimal_id(fields[1]):
                return fields[1]
    return None


# Compatibility helper for external callers that only need to render a key list.
def _nav_hint(cfg: Config) -> str:
    return f"{_fmt_key(cfg.keys.get('down', 'ctrl-j'))}/{_fmt_key(cfg.keys.get('up', 'ctrl-k'))} move · Enter/→ open · ? keys · Esc back"
