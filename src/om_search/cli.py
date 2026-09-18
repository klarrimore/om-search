"""om-search CLI entry point and hierarchical navigation orchestration."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from om_search.commands import Command, parse_commands_json
from om_search.config import load_config, write_default_config
from om_search.index import (
    INDEX_FILENAME,
    build_candidates,
    build_index,
    display_label,
    load_index,
)
from om_search.manual import Section, list_pages, parse_manual_file
from om_search.paths import data_dir, manual_dir, repo_dir
from om_search.picker import (
    build_navigation_dataset,
    keys_cheatsheet,
    navigation_full_text,
    navigation_preview,
    navigation_reader_move,
    navigation_reader_preview,
    navigation_row,
    navigation_rows,
    navigation_transition_action,
    run_fzf,
    view_markdown,
)
from om_search.theme import color_enabled
from om_search.update import ensure_manual, update_manual



def _render_text(text: str) -> None:
    """Render preview text with the available markdown renderer."""
    if not color_enabled():
        print(text)
        return
    if shutil.which("mdcat"):
        result = subprocess.run(["mdcat", "--ansi", "-"], input=text, capture_output=True, text=True)
        print(result.stdout, end="")
        return
    if shutil.which("bat"):
        result = subprocess.run(
            ["bat", "--language=md", "--paging=never", "--wrap=character",
             "--decorations=never", "--color=always", "-"],
            input=text, capture_output=True, text=True,
        )
        print(result.stdout, end="")
        return
    print(text)
def find_commands() -> list[Command]:
    """Capture the live command tree, returning [] in degraded mode."""
    try:
        result = subprocess.run(
            ["omarchy", "commands", "--json"],
            capture_output=True,
            text=True,
            check=True,
        )
        return parse_commands_json(result.stdout)
    except (FileNotFoundError, subprocess.CalledProcessError, PermissionError):
        return []


def _ensure_manual() -> Path:
    """Ensure the manual exists and return its directory."""
    ensure_manual(repo_dir())
    mdir = manual_dir()
    if not mdir.exists():
        print("Manual not found. Run `om-search update` first.", file=sys.stderr)
        sys.exit(1)
    return mdir


def _load_content(mdir: Path) -> tuple[list[Section], dict[str, str]]:
    index_data = load_index(data_dir() / INDEX_FILENAME)
    if index_data is not None:
        return index_data
    sections: list[Section] = []
    page_texts: dict[str, str] = {}
    for path in sorted(mdir.glob("*.md")):
        parsed = parse_manual_file(path)
        sections.extend(parsed)
        page_texts[path.name] = path.read_text(encoding="utf-8")
    return sections, page_texts


def _load_sections(mdir: Path) -> list[Section]:
    """Compatibility wrapper used by update and external callers."""
    return _load_content(mdir)[0]


def cmd_update() -> int:
    """Update the manual, rebuild its index, and report command availability."""
    if not update_manual(repo_dir()):
        print("Update failed.", file=sys.stderr)
        return 1
    print("Manual updated.")
    mdir = manual_dir()
    if mdir.exists():
        build_index(mdir, data_dir() / INDEX_FILENAME)
        print("Search index rebuilt.")
        print(f"{len(_load_sections(mdir))} doc sections indexed.")
    else:
        print("No manual directory found; index not built.", file=sys.stderr)
    commands = find_commands()
    if commands:
        print(f"{len(commands)} commands indexed.")
    else:
        print("Command tree not available (degraded mode).")
    return 0


def cmd_preview(key1: str, key2: str = "") -> int:
    """Legacy preview endpoint retained for callers outside the new picker."""
    if key1.startswith("omarchy"):
        print(key1)
        if key2:
            print()
            print(key2)
        return 0
    index_data = load_index(data_dir() / INDEX_FILENAME)
    if index_data is not None:
        sections, page_texts = index_data
        if key2:
            match = next((s for s in sections if s.page_file == key1 and s.anchor == key2), None)
            if match is not None:
                _render_text(match.text)
                return 0
        if key1 in page_texts:
            _render_text(page_texts[key1])
            return 0
    path = manual_dir() / key1
    if path.is_file():
        if key2:
            match = next((s for s in parse_manual_file(path) if s.anchor == key2), None)
            _render_text(match.text if match else path.read_text(encoding="utf-8"))
        else:
            _render_text(path.read_text(encoding="utf-8"))
    else:
        print(key1)
    return 0


def cmd_nav_data(dataset: str, route_id: str) -> int:
    try:
        sys.stdout.write(navigation_rows(Path(dataset), route_id))
    except (OSError, ValueError) as exc:
        print(f"Invalid navigation dataset: {exc}", file=sys.stderr)
        return 1
    return 0


def cmd_nav_preview(dataset: str, preview_id: str) -> int:
    try:
        text = navigation_preview(Path(dataset), preview_id)
    except (OSError, ValueError) as exc:
        print(f"Invalid navigation dataset: {exc}", file=sys.stderr)
        return 1
    _render_text(text)
    return 0


def _reader_viewport(value: str) -> int:
    if not re.fullmatch(r"[0-9]+", value) or int(value) <= 0:
        raise ValueError("viewport must be a positive decimal")
    return int(value)


def cmd_nav_reader_preview(
    dataset: str, preview_id: str, viewport_lines: str = "24"
) -> int:
    try:
        viewport = _reader_viewport(viewport_lines)
        text = navigation_reader_preview(Path(dataset), preview_id, viewport)
    except (OSError, ValueError) as exc:
        print(f"Invalid navigation reader: {exc}", file=sys.stderr)
        return 1
    sys.stdout.write(text)
    return 0


def cmd_nav_reader_move(
    dataset: str,
    preview_id: str,
    movement: str,
    viewport_lines: str = "24",
) -> int:
    try:
        viewport = _reader_viewport(viewport_lines)
        navigation_reader_move(Path(dataset), preview_id, movement, viewport)
    except (OSError, ValueError) as exc:
        print(f"Invalid navigation reader: {exc}", file=sys.stderr)
        return 1
    return 0


def cmd_nav_open(dataset: str, row_id: str) -> int:
    try:
        text, heading = navigation_full_text(Path(dataset), row_id)
    except (OSError, ValueError) as exc:
        print(f"Invalid navigation row: {exc}", file=sys.stderr)
        return 1
    view_markdown(text, jump_to=heading or None)
    return 0


def cmd_nav_copy(dataset: str, row_id: str) -> int:
    try:
        row = navigation_row(Path(dataset), row_id, kinds={"cmd"})
    except (OSError, ValueError) as exc:
        print(f"Invalid navigation row: {exc}", file=sys.stderr)
        return 1
    payload = row.get("payload")
    if not isinstance(payload, str):
        return 1
    try:
        subprocess.run(["wl-copy"], input=payload, text=True, check=False)
    except OSError as exc:
        print(f"Unable to copy command: {exc}", file=sys.stderr)
        return 1
    return 0


def cmd_nav_transition(dataset: str, route_id: str, args: list[str]) -> int:
    enter_kind = ""
    focus_kind = ""
    parent_route_id = "0"
    row_id = ""
    links = False
    i = 0
    while i < len(args):
        token = args[i]
        if token == "--enter" and i + 2 < len(args):
            enter_kind = args[i + 1]
            parent_route_id = args[i + 2]
            i += 3
        elif token == "--focus" and i + 2 < len(args):
            focus_kind = args[i + 1]
            parent_route_id = args[i + 2]
            i += 3
        elif token == "--row" and i + 1 < len(args):
            row_id = args[i + 1]
            i += 2
        elif token == "--links":
            links = True
            i += 1
        else:
            i += 1
    try:
        action = navigation_transition_action(
            Path(dataset),
            route_id,
            enter_kind=enter_kind,
            focus_kind=focus_kind,
            parent_route_id=parent_route_id,
            row_id=row_id,
            links=links,
        )
    except (OSError, ValueError) as exc:
        print(f"Invalid navigation transition: {exc}", file=sys.stderr)
        return 1
    print(action)
    return 0


def _flat_output(
    sections: list[Section],
    commands: list[Command],
    mode: str,
    page_filter: str | None,
    group_filter: str | None,
    query: str,
) -> int:
    candidates = build_candidates(sections, commands, mode, page_filter, group_filter, query)
    if not candidates:
        print("No content indexed.", file=sys.stderr)
        return 1
    for candidate in candidates:
        print(display_label(candidate))
    return 0


def _entry_key(entry_route: str, args_page: str | None, args_group: str | None) -> str:
    if args_page:
        return f"page:{args_page}"
    if args_group:
        return f"group:{args_group}"
    return entry_route


def cmd_picker(
    query: str = "",
    mode: str = "all",
    page_filter: str | None = None,
    group_filter: str | None = None,
    plain: bool = False,
    entry_route: str = "search:all",
) -> int:
    """Load content once, then either print flat results or run one fzf."""
    mdir = _ensure_manual()
    sections, page_texts = _load_content(mdir)
    commands = find_commands()
    if mode == "cmd" and not commands:
        print("Command tree not available (degraded mode).", file=sys.stderr)
        return 1
    if plain or not sys.stdout.isatty():
        return _flat_output(sections, commands, mode, page_filter, group_filter, query)

    cfg = load_config()
    with build_navigation_dataset(sections, commands, cfg=cfg, page_texts=page_texts) as dataset:
        key = _entry_key(entry_route, page_filter, group_filter)
        route_id = dataset.entry_routes.get(key)
        if route_id is None or route_id == "0":
            if key.startswith("page:"):
                print(f"Manual page not found: {page_filter}", file=sys.stderr)
            elif key.startswith("group:"):
                print(f"Command group not found: {group_filter}", file=sys.stderr)
            else:
                print("No navigation route available.", file=sys.stderr)
            return 1
        selected = run_fzf(dataset.path, route_id, query=query, cfg=cfg)
        if selected is None:
            return 0
        try:
            row = navigation_row(dataset.path, selected)
        except (OSError, ValueError):
            return 0
        if row.get("kind") == "cmd":
            payload = row.get("payload")
            if isinstance(payload, str):
                print(payload)
        return 0


def _list_pages(mdir: Path) -> list[dict[str, str | int]]:
    index_data = load_index(data_dir() / INDEX_FILENAME)
    if index_data is not None:
        seen: set[str] = set()
        result: list[dict[str, str | int]] = []
        for section in index_data[0]:
            if section.page_file not in seen:
                seen.add(section.page_file)
                result.append({"number": section.page_number, "title": section.page_title, "file": section.page_file})
        result.sort(key=lambda page: page["number"])
        return result
    return [{"number": p.page_number, "title": p.page_title, "file": p.page_file} for p in list_pages(mdir)]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="om-search",
        description="Search the Omarchy Linux manual and CLI commands from the terminal.",
    )
    parser.add_argument("query", nargs="*", default=[], help="Optional search query to pre-fill the picker")
    parser.add_argument("--docs", action="store_true", default=False, help="Search manual documentation only")
    parser.add_argument("--cmds", action="store_true", default=False, help="Search CLI commands only")
    parser.add_argument("--page", type=str, default=None, metavar="FILE", help="Search within a specific manual page")
    parser.add_argument("--group", type=str, default=None, metavar="NAME", help="Search within a specific command group")
    parser.add_argument("--update", action="store_true", default=False, help="Refresh the manual from upstream")
    parser.add_argument("--pages", action="store_true", default=False, help="Browse manual pages")
    parser.add_argument("--groups", action="store_true", default=False, help="Browse command groups")
    parser.add_argument("--completion", action="store_true", default=False, help="Print shell completion setup and exit")
    parser.add_argument("--keys", action="store_true", default=False, help="Print the keybinding cheatsheet and exit")
    parser.add_argument("--init-config", action="store_true", default=False, help="Write a default config and exit")
    parser.add_argument("--no-color", action="store_true", default=False, help="Disable ANSI colour")
    parser.add_argument("--print", dest="plain", action="store_true", default=False, help="Print ranked results")
    return parser


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    # fzf invokes all private endpoints as raw subcommands.
    if argv and argv[0] == "nav-data" and len(argv) >= 3:
        return cmd_nav_data(argv[1], argv[2])
    if argv and argv[0] == "nav-preview" and len(argv) >= 3:
        return cmd_nav_preview(argv[1], argv[2])
    if argv and argv[0] == "nav-reader-preview":
        if len(argv) in {3, 4}:
            return cmd_nav_reader_preview(*argv[1:])
        print("Invalid navigation reader: invalid command arguments", file=sys.stderr)
        return 1
    if argv and argv[0] == "nav-reader-move":
        if len(argv) in {4, 5}:
            return cmd_nav_reader_move(*argv[1:])
        print("Invalid navigation reader: invalid command arguments", file=sys.stderr)
        return 1
    if argv and argv[0] == "nav-open" and len(argv) >= 3:
        return cmd_nav_open(argv[1], argv[2])
    if argv and argv[0] == "nav-copy" and len(argv) >= 3:
        return cmd_nav_copy(argv[1], argv[2])
    if argv and argv[0] == "nav-transition" and len(argv) >= 3:
        return cmd_nav_transition(argv[1], argv[2], argv[3:])
    if argv and argv[0] == "preview" and len(argv) >= 2:
        return cmd_preview(argv[1], argv[2] if len(argv) > 2 else "")

    parser = build_parser()
    if os.environ.get("_ARGCOMPLETE"):
        import argcomplete
        argcomplete.autocomplete(parser)
    args = parser.parse_args(argv)
    if args.no_color:
        os.environ["NO_COLOR"] = "1"
    query = " ".join(args.query)
    if args.completion:
        print("Add to ~/.bashrc or ~/.zshrc:")
        print('  eval "$(register-python-argcomplete om-search)"')
        return 0
    if args.keys:
        print(keys_cheatsheet(), end="")
        return 0
    if args.init_config:
        path = write_default_config()
        print(f"Config at {path}")
        return 0
    if args.update:
        return cmd_update()

    if args.docs and args.cmds:
        mode = "all"
    elif args.docs:
        mode = "doc"
    elif args.cmds:
        mode = "cmd"
    else:
        mode = "all"

    entry_route = "home" if not query else "search:all"
    if args.pages:
        entry_route, mode = "pages", "doc"
    elif args.groups:
        entry_route, mode = "groups", "cmd"
    elif args.page:
        entry_route, mode = "search:doc", "doc"
    elif args.group:
        entry_route, mode = "search:cmd", "cmd"
    elif args.docs:
        entry_route = "search:doc"
    elif args.cmds:
        entry_route = "search:cmd"
    return cmd_picker(
        query=query,
        mode=mode,
        page_filter=args.page,
        group_filter=args.group,
        plain=args.plain,
        entry_route=entry_route,
    )
