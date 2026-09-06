"""om-search CLI — entry point and orchestration."""

import argparse
import argcomplete
import shutil
import subprocess
import sys
from pathlib import Path

from om_search.commands import Command, list_groups, parse_commands_json
from om_search.index import (
    INDEX_FILENAME,
    build_candidates,
    build_index,
    load_index,
    parse_fzf_line,
    render_candidate,
)
from om_search.manual import Section, list_pages, parse_manual_file
from om_search.paths import data_dir, repo_dir, manual_dir
from om_search.config import write_default_config
from om_search.picker import (
    action_for,
    keys_cheatsheet,
    run_fzf,
    run_simple_fzf,
    view_markdown,
)
from om_search.update import ensure_manual, update_manual


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


def cmd_preview(key1: str, key2: str = "") -> int:
    """Render preview content for the fzf preview window (internal command).

    Reads from the pre-built index for speed.  Falls back to parsing
    the markdown file from disk when the index is unavailable.

    key1 is the page file name (for doc) or command path (for cmd).
    key2 is the anchor (for doc) or description (for cmd).
    """
    # Try pre-built index first
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
    markdown source), then falls back to plain text.
    """
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
) -> int:
    """Open the fzf fuzzy picker over the manual and commands."""
    mdir = _ensure_manual()
    sections = _load_sections(mdir)
    commands = find_commands()
    candidates = build_candidates(sections, commands, mode, page_filter, group_filter)
    lines = [render_candidate(c) for c in candidates]

    if not lines:
        print("No content indexed.", file=sys.stderr)
        return 1

    selected = run_fzf(lines, query, mode, page_filter, group_filter)
    if selected is None:
        return 0

    cand = parse_fzf_line(selected)
    if cand is None:
        return 0

    kind, payload = action_for(cand)
    if kind == "echo":
        print(payload)
    else:
        view_markdown(payload)
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
    selected = run_simple_fzf(items, header=header, query=query)

    if selected is None:
        return 0

    # Extract the page file from the selected line (last parenthesised chunk)
    page_file = selected.rsplit("(", 1)[-1].rstrip(")")
    return cmd_picker(mode="doc", page_filter=page_file)


def cmd_groups(query: str = "") -> int:
    """Browse command groups: pick one, then search within it."""
    commands = find_commands()

    if not commands:
        print("Command tree not available (degraded mode).", file=sys.stderr)
        return 1

    groups = list_groups(commands)
    items = [f"omarchy {g}" for g in groups]
    header = "Pick a group to search within  |  Enter: select  |  Esc/Ctrl-C: cancel"
    selected = run_simple_fzf(items, header=header, query=query)

    if selected is None:
        return 0

    group = selected.removeprefix("omarchy ")
    return cmd_picker(mode="cmd", group_filter=group)


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
    return parser


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    # Intercept the preview subcommand before argparse — fzf calls this
    # with raw positional args and no flags.
    if argv and argv[0] == "preview" and len(argv) >= 2:
        return cmd_preview(argv[1], argv[2] if len(argv) > 2 else "")

    parser = build_parser()
    argcomplete.autocomplete(parser)
    args = parser.parse_args(argv)

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
    )