"""om-search CLI — entry point and orchestration."""

import subprocess
import sys
from pathlib import Path

from om_search.commands import Command, parse_commands_json
from om_search.index import build_candidates, parse_fzf_line, render_candidate
from om_search.manual import parse_manual_file
from om_search.paths import repo_dir, manual_dir
from om_search.picker import action_for, run_fzf
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


def cmd_update() -> int:
    """Update the manual repository and re-cache commands."""
    ok = update_manual(repo_dir())
    if ok:
        print("Manual updated.")
    else:
        print("Update failed.", file=sys.stderr)
        return 1

    # Re-capture commands
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

    # Resolve a relative page_file against the manual directory
    resolved = key1
    if not os.path.isabs(key1) and not key1.startswith("omarchy"):
        resolved = str(manual_dir() / key1)

    is_file = os.path.isfile(resolved)
    if is_file:
        # Doc preview: read the file and show the section
        from om_search.manual import parse_manual_file

        sections = parse_manual_file(Path(resolved))
        if key2:
            matching = [s for s in sections if s.anchor == key2]
            if matching:
                print(matching[0].text)
            else:
                # Fall back: print the whole file
                print(open(resolved).read())
        else:
            print(open(resolved).read())
    else:
        # Command preview: show path + description
        print(key1)
        if key2:
            print()
            print(key2)

    return 0


def cmd_picker(query: str = "") -> int:
    """Open the fzf fuzzy picker over the manual and commands."""
    # Ensure manual is available
    repo = repo_dir()
    ensure_manual(repo)
    mdir = manual_dir()

    if not mdir.exists():
        print("Manual not found. Run `om-search update` first.", file=sys.stderr)
        return 1

    # Parse all manual files
    sections = []
    for f in sorted(mdir.glob("*.md")):
        sections.extend(parse_manual_file(f))

    # Capture commands (degraded mode if missing)
    commands = find_commands()

    # Build and render candidates
    candidates = build_candidates(sections, commands)
    lines = [render_candidate(c) for c in candidates]

    if not lines:
        print("No content indexed.", file=sys.stderr)
        return 1

    # Run fzf
    selected = run_fzf(lines, query=query)
    if selected is None:
        # User cancelled
        return 0

    # Parse and dispatch
    cand = parse_fzf_line(selected)
    if cand is None:
        return 0

    pager, payload = action_for(cand)

    # Execute the action
    if pager == "echo":
        print(payload)
    else:
        subprocess.run([pager], input=payload.encode(), check=False)

    return 0


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        return cmd_picker(query="")
    elif argv[0] == "update":
        return cmd_update()
    elif argv[0] == "preview" and len(argv) >= 2:
        return cmd_preview(argv[1], argv[2] if len(argv) > 2 else "")
    else:
        return cmd_picker(query=" ".join(argv))