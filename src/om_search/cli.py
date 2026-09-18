"""om-search CLI — entry point and orchestration."""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from om_search.commands import Command, list_groups, parse_commands_json
from om_search.index import (
    INDEX_FILENAME,
    DocCandidate,
    build_candidates,
    build_index,
    display_label,
    load_index,
    parse_fzf_line,
    preview_key,
    render_candidate,
)
from om_search.manual import Section, extract_links, list_pages, parse_manual_file
from om_search.paths import data_dir, manual_dir, preview_dir, repo_dir
from om_search.config import write_default_config
from om_search.picker import (
    BACK,
    action_for,
    keys_cheatsheet,
    page_text,
    run_fzf,
    run_simple_fzf,
    view_markdown,
)
from om_search.theme import color_enabled
from om_search.update import ensure_manual, update_manual

# cmd_picker returns this to its caller (cmd_pages/cmd_groups) when the user
# asked to pop back to the parent list rather than exit.
GO_BACK = -1


def find_commands() -> list[Command]:
    """Capture the command tree from the installed omarchy CLI.

    Returns an empty list when the CLI is not available (degraded mode).
    """
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
    """Ensure the manual is cloned and return its path.  Exits on failure."""
    repo = repo_dir()
    ensure_manual(repo)
    mdir = manual_dir()
    if not mdir.exists():
        print("Manual not found. Run `om-search update` first.", file=sys.stderr)
        sys.exit(1)
    return mdir


def _load_sections(mdir: Path) -> list[Section]:
    """Load sections from the pre-built index, or parse from disk."""
    index_path = data_dir() / INDEX_FILENAME
    index_data = load_index(index_path)
    if index_data is not None:
        return index_data[0]
    # Fallback: parse every markdown file
    result: list[Section] = []
    for f in sorted(mdir.glob("*.md")):
        result.extend(parse_manual_file(f))
    return result


def cmd_update() -> int:
    """Update the manual repository, rebuild index, and re-cache commands."""
    ok = update_manual(repo_dir())
    if ok:
        print("Manual updated.")
    else:
        print("Update failed.", file=sys.stderr)
        return 1

    # Rebuild the pre-built index
    mdir = manual_dir()
    if mdir.exists():
        build_index(mdir, data_dir() / INDEX_FILENAME)
        print("Search index rebuilt.")
        sections = _load_sections(mdir)
        print(f"{len(sections)} doc sections indexed.")
    else:
        print("No manual directory found; index not built.", file=sys.stderr)

    cmds = find_commands()
    if cmds:
        print(f"{len(cmds)} commands indexed.")
    else:
        print("Command tree not available (degraded mode).")
    return 0


def cmd_open(page_file: str, anchor: str = "") -> int:
    """Open a full manual page in the pager, positioned at a section.

    Internal command invoked by the picker's Ctrl-O binding. Resolves the
    heading for ``anchor`` so :func:`view_markdown` can jump to it.
    """
    heading = ""
    index_data = load_index(data_dir() / INDEX_FILENAME)
    sections = index_data[0] if index_data is not None else _load_sections(manual_dir())
    for s in sections:
        if s.page_file == page_file and s.anchor == anchor:
            heading = s.heading
            break
    cand = DocCandidate(
        page_file=page_file, anchor=anchor, page_title="", heading=heading
    )
    view_markdown(page_text(cand), jump_to=heading or None)
    return 0


def cmd_links(page_file: str) -> int:
    """Pick a cross-reference link on ``page_file`` and jump to that page.

    Internal command invoked by the picker's Ctrl-L binding. Lists the page's
    manual links; selecting one opens that page's scoped doc picker (pre-filtered
    to the linked section when the link carries an anchor). Backing out of the
    target returns to the link list.
    """
    links = extract_links(page_text(DocCandidate(page_file=page_file)))
    if not links:
        print("No links on this page.", file=sys.stderr)
        return 0

    items: list[str] = []
    seen: set[tuple[str, str]] = set()
    for label, page, anchor in links:
        if (page, anchor) in seen:
            continue
        seen.add((page, anchor))
        target = f"{page}#{anchor}" if anchor else page
        items.append(f"{label}  →  {target}")

    header = "Follow a link  |  Enter: go  |  Esc: back"
    while True:
        selected = run_simple_fzf(items, header=header)
        if selected is None:
            return 0
        target = selected.rsplit("→", 1)[-1].strip()
        page, _, anchor = target.partition("#")
        query = anchor.replace("-", " ") if anchor else ""
        result = cmd_picker(mode="doc", page_filter=page, query=query)
        if result != GO_BACK:
            return result
        # else: user backed out of the target page — reshow the link list


def cmd_preview(key1: str, key2: str = "") -> int:
    """Render preview content for the fzf preview window (internal command).

    Reads from the pre-built index for speed.  Falls back to parsing
    the markdown file from disk when the index is unavailable.

    key1 is the page file name (for doc) or command path (for cmd).
    key2 is the anchor (for doc) or description (for cmd).
    """
    # Fast path: a pre-rendered per-entry preview file (avoids parsing the
    # whole index on every selection). Only docs/pages have these.
    pfile = preview_dir() / preview_key(key1, key2)
    if pfile.is_file():
        try:
            _render_text(pfile.read_text(encoding="utf-8"))
            return 0
        except OSError:
            pass  # fall through to the index on any read error

    # Fall back to the pre-built index.
    index_path = data_dir() / INDEX_FILENAME
    index_data = load_index(index_path)
    if index_data is not None:
        sections, page_texts = index_data
        text: str | None = None
        if key2:
            matching = [s for s in sections if s.page_file == key1 and s.anchor == key2]
            text = matching[0].text if matching else None
        if text is None:
            text = page_texts.get(key1)
        if text:
            _render_text(text)
            return 0

    # Fallback: read from disk
    import os

    resolved = key1
    if not os.path.isabs(key1) and not key1.startswith("omarchy"):
        resolved = str(manual_dir() / key1)

    is_file = os.path.isfile(resolved)
    if is_file:
        sections = parse_manual_file(Path(resolved))
        if key2:
            matching = [s for s in sections if s.anchor == key2]
            if matching:
                text = matching[0].text
            else:
                text = Path(resolved).read_text(encoding="utf-8")
        else:
            text = Path(resolved).read_text(encoding="utf-8")

        _render_text(text)
    else:
        print(key1)
        if key2:
            print()
            print(key2)
    return 0


def _render_text(text: str) -> None:
    """Render markdown text to the terminal with color and formatting.

    Tries mdcat (true markdown rendering), then bat (syntax-highlighted
    markdown source), then falls back to plain text. Emits no ANSI when
    colour is disabled (NO_COLOR / TERM=dumb).
    """
    if not color_enabled():
        print(text)
        return
    if shutil.which("mdcat"):
        result = subprocess.run(
            ["mdcat", "--ansi", "-"],
            input=text,
            capture_output=True,
            text=True,
        )
        print(result.stdout, end="")
        return

    if shutil.which("bat"):
        result = subprocess.run(
            ["bat", "--language=md", "--paging=never", "--wrap=character", "--decorations=never", "--color=always", "-"],
            input=text,
            capture_output=True,
            text=True,
        )
        print(result.stdout, end="")
        return

    print(text)


def cmd_picker(
    query: str = "",
    mode: str = "all",
    page_filter: str | None = None,
    group_filter: str | None = None,
    plain: bool = False,
) -> int:
    """Open the fzf fuzzy picker over the manual and commands.

    Degrades to plain, greppable output when stdout is not a TTY or ``plain``
    (``--print``) is set — so `om-search … | grep` and headless/CI use work.
    """
    mdir = _ensure_manual()
    sections = _load_sections(mdir)
    commands = find_commands()
    candidates = build_candidates(
        sections,
        commands,
        mode,
        page_filter,
        group_filter,
        query,
    )

    if not candidates:
        print("No content indexed.", file=sys.stderr)
        return 1

    if plain or not sys.stdout.isatty():
        for c in candidates:
            print(display_label(c))
        return 0

    lines = [render_candidate(c) for c in candidates]

    # Docs are now read inside the picker (Enter = reading mode in the right
    # pane; Ctrl-O = full pager), so the picker returns only for a command
    # selection or a back/cancel. A scoped picker (drilled in from a page or
    # group list) lets Left/Esc pop back to that list.
    scoped = bool(page_filter or group_filter)
    selected = run_fzf(lines, query, mode, page_filter, group_filter, back=scoped)
    if selected == BACK:
        return GO_BACK
    if selected is None:
        return 0
    cand = parse_fzf_line(selected)
    if cand is None:
        return 0
    kind, payload = action_for(cand)
    if kind == "echo":
        print(payload)
    else:
        # Fallback: a doc came back (e.g. no reading binds) — open the pager.
        view_markdown(payload, jump_to=getattr(cand, "heading", "") or None)
    return 0


def _list_pages(
    mdir: Path,
) -> list[dict[str, str | int]]:
    """List manual pages, preferring the pre-built index over disk scan."""
    index_path = data_dir() / INDEX_FILENAME
    index_data = load_index(index_path)
    if index_data is not None:
        sections, _ = index_data
        seen: set[str] = set()
        result: list[dict[str, str | int]] = []
        for s in sections:
            if s.page_file not in seen:
                seen.add(s.page_file)
                result.append({
                    "number": s.page_number,
                    "title": s.page_title,
                    "file": s.page_file,
                })
        result.sort(key=lambda p: p["number"])
        return result
    # Fallback: disk scan
    return [
        {"number": p.page_number, "title": p.page_title, "file": p.page_file}
        for p in list_pages(mdir)
    ]


def cmd_pages(query: str = "") -> int:
    """Browse manual pages: pick one, then search within it."""
    mdir = _ensure_manual()
    pages = _list_pages(mdir)

    if not pages:
        print("No pages found.", file=sys.stderr)
        return 1

    items = [
        f"{p['number']:02d}  {p['title']}  ({p['file']})"
        for p in pages
    ]
    header = "Pick a page to search within  |  Enter: select  |  Esc/Ctrl-C: cancel"
    while True:
        selected = run_simple_fzf(items, header=header, query=query)
        if selected is None:
            return 0
        # Extract the page file from the selected line (last parenthesised chunk)
        page_file = selected.rsplit("(", 1)[-1].rstrip(")")
        result = cmd_picker(mode="doc", page_filter=page_file)
        if result != GO_BACK:
            return result
        # else: user pressed ←/Esc in the scoped picker — reshow the page list


def cmd_groups(query: str = "") -> int:
    """Browse command groups: pick one, then search within it."""
    commands = find_commands()

    if not commands:
        print("Command tree not available (degraded mode).", file=sys.stderr)
        return 1

    groups = list_groups(commands)
    items = [f"omarchy {g}" for g in groups]
    header = "Pick a group to search within  |  Enter: select  |  Esc/Ctrl-C: cancel"
    while True:
        selected = run_simple_fzf(items, header=header, query=query)
        if selected is None:
            return 0
        group = selected.removeprefix("omarchy ")
        result = cmd_picker(mode="cmd", group_filter=group)
        if result != GO_BACK:
            return result
        # else: user pressed ←/Esc in the scoped picker — reshow the group list


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser.

    Uses flags instead of subparsers to avoid ambiguity between positional
    query args and subcommand names.  The ``preview`` subcommand is an
    exception — it is intercepted in ``main()`` before the parser runs
    because fzf calls ``om-search preview`` with raw positional args.
    """
    parser = argparse.ArgumentParser(
        prog="om-search",
        description="Search the Omarchy Linux manual and CLI commands from the terminal.",
    )

    parser.add_argument(
        "query",
        nargs="*",
        default=[],
        help="Optional search query to pre-fill the picker",
    )
    parser.add_argument(
        "--docs",
        action="store_true",
        default=False,
        help="Search manual documentation only",
    )
    parser.add_argument(
        "--cmds",
        action="store_true",
        default=False,
        help="Search CLI commands only",
    )
    parser.add_argument(
        "--page",
        type=str,
        default=None,
        metavar="FILE",
        help="Search within a specific manual page (filename)",
    )
    parser.add_argument(
        "--group",
        type=str,
        default=None,
        metavar="NAME",
        help="Search within a specific command group",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        default=False,
        help="Refresh the manual from upstream",
    )
    parser.add_argument(
        "--pages",
        action="store_true",
        default=False,
        help="Browse manual pages, pick one to search within",
    )
    parser.add_argument(
        "--groups",
        action="store_true",
        default=False,
        help="Browse command groups, pick one to search within",
    )
    parser.add_argument(
        "--completion",
        action="store_true",
        default=False,
        help="Print shell completion setup and exit",
    )
    parser.add_argument(
        "--keys",
        action="store_true",
        default=False,
        help="Print the keybinding cheatsheet and exit",
    )
    parser.add_argument(
        "--init-config",
        action="store_true",
        default=False,
        help="Write a default config to ~/.config/om-search/config.toml and exit",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        default=False,
        help="Disable ANSI colour (also honors NO_COLOR and TERM=dumb)",
    )
    parser.add_argument(
        "--print",
        dest="plain",
        action="store_true",
        default=False,
        help="Print ranked results as plain text instead of opening the picker",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    # Intercept the preview subcommand before argparse — fzf calls this
    # with raw positional args and no flags.
    if argv and argv[0] == "preview" and len(argv) >= 2:
        return cmd_preview(argv[1], argv[2] if len(argv) > 2 else "")
    if argv and argv[0] == "open" and len(argv) >= 2:
        return cmd_open(argv[1], argv[2] if len(argv) > 2 else "")
    if argv and argv[0] == "links" and len(argv) >= 2:
        return cmd_links(argv[1])

    parser = build_parser()
    # argcomplete only acts during shell completion (when the shell sets
    # _ARGCOMPLETE); importing it lazily keeps it off the normal startup path.
    if os.environ.get("_ARGCOMPLETE"):
        import argcomplete
        argcomplete.autocomplete(parser)
    args = parser.parse_args(argv)

    # A --no-color flag disables colour everywhere by setting NO_COLOR, which
    # child processes (fzf, the preview/pager subprocesses) inherit.
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
    if args.pages:
        return cmd_pages(query)
    if args.groups:
        return cmd_groups(query)

    # Determine mode from flags
    if args.docs and args.cmds:
        mode = "all"
    elif args.docs:
        mode = "doc"
    elif args.cmds:
        mode = "cmd"
    else:
        mode = "all"

    return cmd_picker(
        query=query,
        mode=mode,
        page_filter=args.page,
        group_filter=args.group,
        plain=args.plain,
    )
