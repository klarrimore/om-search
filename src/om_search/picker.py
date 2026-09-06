"""fzf integration: preview rendering and post-selection actions."""

import shutil
import subprocess
import sys
from typing import cast

from om_search.index import (
    Candidate,
    CmdCandidate,
    DocCandidate,
    INDEX_FILENAME,
    load_index,
)
from om_search.manual import parse_manual_file
from om_search.paths import data_dir, manual_dir


def section_text(cand: DocCandidate) -> str:
    """Read the section text for a doc candidate.

    Tries the pre-built index first, then falls back to parsing the
    markdown file from disk.
    """
    # Try index first
    index_path = data_dir() / INDEX_FILENAME
    index_data = load_index(index_path)
    if index_data is not None:
        sections, page_texts = index_data
        for s in sections:
            if (
                s.page_file == cand.page_file
                and s.anchor == cand.anchor
                and s.heading == cand.heading
            ):
                return s.text
        # Section not found by anchor — return full page text
        full = page_texts.get(cand.page_file, "")
        if full:
            return full

    # Fallback: parse from disk
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
    """Return (kind, payload) for a selected candidate.

    ``doc`` -> ``("view", markdown)``  — rendered and paged by
    :func:`view_markdown`.
    ``cmd`` -> ``("echo", path)``       — printed to stdout for the shell.
    """
    if cand.type == "doc":
        return ("view", section_text(cast(DocCandidate, cand)))
    cmd = cast(CmdCandidate, cand)
    return ("echo", cmd.path)


def render_markdown(text: str) -> str:
    """Render markdown to ANSI using the best renderer available.

    Prefers true-markdown renderers (glow, mdcat) that style headings, lists
    and code; falls back to syntax-highlighted source (bat); finally returns
    the text unchanged. Never raises — a failing renderer is skipped.
    """
    renderers = [
        ["glow", "-s", "auto", "-"],
        ["mdcat", "--ansi", "-"],
        ["bat", "--language=md", "--color=always", "--paging=never",
         "--decorations=never", "-"],
    ]
    for cmd in renderers:
        if not shutil.which(cmd[0]):
            continue
        try:
            result = subprocess.run(
                cmd, input=text, capture_output=True, text=True
            )
        except OSError:
            continue
        if result.returncode == 0 and result.stdout:
            return result.stdout
    return text


def view_markdown(text: str) -> None:
    """Render markdown and show it in an interactive pager when possible.

    Renders with :func:`render_markdown`, then pages through ``less -R`` so
    the output is both pretty and scrollable/searchable. ``-F`` prints
    directly (no pager) when the content fits one screen; ``-X`` keeps it in
    the scrollback. Falls back to writing to stdout when there is no TTY or
    no ``less``.
    """
    rendered = render_markdown(text)
    if sys.stdout.isatty() and shutil.which("less"):
        subprocess.run(
            ["less", "-R", "-F", "-X"], input=rendered.encode(), check=False
        )
        return
    if not rendered.endswith("\n"):
        rendered += "\n"
    sys.stdout.write(rendered)


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
    Fields 4 (display) and 5 (dimmed body excerpt) are both presented and
    searched via ``--with-nth 4,5`` so body content is discoverable — fzf
    only matches text it presents, so the excerpt must be shown to be found.
    """
    preview_cmd = "om-search preview {2} {3}"

    cmd = [
        "fzf",
        "--tiebreak=begin,end",
        "--ansi",
        "--delimiter",
        "\t",
        "--with-nth",
        "4,5",
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