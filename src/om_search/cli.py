"""om-search CLI — entry point and orchestration."""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from om_search.commands import Command, list_groups, parse_commands_json
from om_search.index import build_candidates, parse_fzf_line, render_candidate
from om_search.manual import Section, list_pages, parse_manual_file
from om_search.paths import repo_dir, manual_dir
from om_search.picker import action_for, run_fzf, run_simple_fzf
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
    """Parse every markdown file in the manual directory."""
    sections: list[Section] = []
    for f in sorted(mdir.glob("*.md")):
        sections.extend(parse_manual_file(f))
    return sections


def cmd_update() -> int:
    """Update the manual repository and re-cache commands."""
    ok = update_manual(repo_dir())
    if ok:
        print("Manual updated.")
    else:
        print("Update failed.", file=sys.stderr)
        return 1

    cmds = find_commands()
    if cmds:
        print(f"{len(cmds)} commands indexed.")
    else:
        print("Command tree not available (degraded mode).")
    return 0


def cmd_preview(key1: str, key2: str = "") -> int:
    """Render preview content for the fzf preview window (internal command).

    key1 is the file path (for doc) or command path (for cmd).
    key2 is the anchor (for doc) or description (for cmd).
    """
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

        if shutil.which("mdcat"):
            result = subprocess.run(
                ["mdcat", "--ansi", "-"],
                input=text,
                capture_output=True,
                text=True,
            )
            print(result.stdout, end="")
        else:
            print(text)
    else:
        print(key1)
        if key2:
            print()
            print(key2)
    return 0


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

    pager, payload = action_for(cand)
    if pager == "echo":
        print(payload)
    else:
        subprocess.run([pager], input=payload.encode(), check=False)
    return 0


def cmd_pages(query: str = "") -> int:
    """Browse manual pages: pick one, then search within it."""
    mdir = _ensure_manual()
    pages = list_pages(mdir)

    if not pages:
        print("No pages found.", file=sys.stderr)
        return 1

    items = [
        f"{p.page_number:02d}  {p.page_title}  ({p.page_file})"
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
    return parser


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    # Intercept the preview subcommand before argparse — fzf calls this
    # with raw positional args and no flags.
    if argv and argv[0] == "preview" and len(argv) >= 2:
        return cmd_preview(argv[1], argv[2] if len(argv) > 2 else "")

    parser = build_parser()
    args = parser.parse_args(argv)

    query = " ".join(args.query)

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