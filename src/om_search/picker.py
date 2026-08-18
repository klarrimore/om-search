"""fzf integration: preview rendering and post-selection actions."""

import shutil
import subprocess
from typing import cast

from om_search.index import Candidate, CmdCandidate, DocCandidate
from om_search.manual import parse_manual_file
from om_search.paths import manual_dir


def section_text(cand: DocCandidate) -> str:
    """Read the section text for a doc candidate from its manual file."""
    path = manual_dir() / cand.page_file
    try:
        sections = parse_manual_file(path)
    except FileNotFoundError:
        return ""
    for s in sections:
        if s.anchor == cand.anchor and s.heading == cand.heading:
            return s.text
    return sections[0].text if sections else ""


def action_for(cand: Candidate) -> tuple[str, str]:
    """Return (command, payload) to run once the user selects a candidate.

    Doc candidates open with a markdown viewer (glow) or fall back to less.
    Command candidates print the command string to stdout.
    """
    if cand.type == "doc":
        text = section_text(cast(DocCandidate, cand))
        if shutil.which("glow"):
            return ("glow", text)
        if shutil.which("less"):
            return ("less", text)
        return ("cat", text)
    else:
        cmd = cast(CmdCandidate, cand)
        return ("echo", cmd.path)


def picker_header(
    mode: str = "all",
    page_filter: str | None = None,
    group_filter: str | None = None,
) -> str:
    """Build the fzf header line describing the active filter."""
    parts: list[str] = []
    if mode == "doc":
        parts.append("docs only")
    elif mode == "cmd":
        parts.append("commands only")
    else:
        parts.append("all sources")

    if page_filter:
        parts.append(f"page: {page_filter}")
    if group_filter:
        parts.append(f"group: {group_filter}")

    scope = ", ".join(parts)
    return f"Mode: {scope}  |  Enter: open  |  Ctrl-Y: copy command"


def run_fzf(
    candidates: list[str],
    query: str = "",
    mode: str = "all",
    page_filter: str | None = None,
    group_filter: str | None = None,
) -> str | None:
    """Run fzf over the rendered candidates, returning the selected line.

    Returns None when the user cancels (no selection).
    """
    preview_cmd = "om-search preview {2} {3}"

    cmd = [
        "fzf",
        "--tiebreak=begin,end",
        "--ansi",
        "--delimiter",
        "\t",
        "--with-nth",
        "4",
        "--preview",
        preview_cmd,
        "--preview-window",
        "right:60%:wrap",
        "--bind",
        "ctrl-y:execute-silent(echo -n {2} | wl-copy)+accept",
        "--header",
        picker_header(mode, page_filter, group_filter),
    ]
    if query:
        cmd.extend(["--query", query])

    proc = subprocess.run(
        cmd,
        input="\n".join(candidates) + "\n",
        text=True,
        capture_output=True,
    )
    out = proc.stdout.strip()
    return out or None


def run_simple_fzf(
    items: list[str],
    header: str = "",
    query: str = "",
) -> str | None:
    """Run fzf over a simple list of strings (no tab-delimited fields).

    Returns the selected line, or None on cancel.
    """
    cmd = [
        "fzf",
        "--tiebreak=end",
    ]
    if header:
        cmd.extend(["--header", header])
    if query:
        cmd.extend(["--query", query])

    proc = subprocess.run(
        cmd,
        input="\n".join(items) + "\n",
        text=True,
        capture_output=True,
    )
    out = proc.stdout.strip()
    return out or None