"""fzf integration: preview rendering and post-selection actions."""

import shutil
import subprocess
import sys
from typing import cast

from om_search.config import Config, load_config
from om_search.index import (
    Candidate,
    CmdCandidate,
    DocCandidate,
    INDEX_FILENAME,
    load_index,
)
from om_search.manual import parse_manual_file
from om_search.paths import config_path, data_dir, manual_dir
from om_search.theme import fzf_color_spec, resolve_palette


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


# Friendly labels for the help cheatsheet, in display order.
_KEY_LABELS: list[tuple[str, str]] = [
    ("down", "Move down"),
    ("up", "Move up"),
    ("half_page_down", "Half page down"),
    ("half_page_up", "Half page up"),
    ("preview_down", "Preview scroll down"),
    ("preview_up", "Preview scroll up"),
    ("open", "Open selection"),
    ("copy", "Copy command"),
    ("help", "Show this help"),
]


def _fmt_key(key: str) -> str:
    """Render an fzf key name the way herdr shows chords: ``Ctrl + J``."""
    return " + ".join(part.capitalize() for part in key.split("-"))


def keys_cheatsheet(cfg: Config | None = None) -> str:
    """Return a plain-text keybinding cheatsheet for the help overlay."""
    cfg = cfg or load_config()
    lines = ["om-search — keybindings", ""]
    for action, label in _KEY_LABELS:
        key = cfg.keys.get(action, "")
        if not key:
            continue
        lines.append(f"  {label:<20} {_fmt_key(key)}")
    lines += [
        "  Quit                 Esc",
        "",
        "Type to fuzzy-search titles and body text.",
        f"Rebind in {config_path()}",
    ]
    return "\n".join(lines) + "\n"


def _base_fzf_args(cfg: Config) -> list[str]:
    """Shared themed/bordered flags and navigation binds (herdr-like look)."""
    args = [
        "--layout=reverse",
        "--border=rounded",
        "--border-label= om-search ",
        "--prompt=  ",
        "--pointer=▶",
        "--marker=✓",
        "--info=inline",
    ]
    palette = resolve_palette(cfg.theme_source, cfg.theme_custom)
    if palette:
        spec = fzf_color_spec(palette)
        if spec:
            args += ["--color", spec]
    for bind in cfg.movement_binds():
        args += ["--bind", bind]
    return args


def _nav_hint(cfg: Config) -> str:
    """A compact second header line advertising the vim-style navigation."""
    down = _fmt_key(cfg.keys.get("down", "ctrl-j"))
    up = _fmt_key(cfg.keys.get("up", "ctrl-k"))
    help_key = cfg.keys.get("help", "?")
    return f"{down}/{up} move · Enter open · {help_key} keys · Esc quit"


def run_fzf(
    candidates: list[str],
    query: str = "",
    mode: str = "all",
    page_filter: str | None = None,
    group_filter: str | None = None,
    cfg: Config | None = None,
) -> str | None:
    """Run fzf over the rendered candidates, returning the selected line.

    Returns None when the user cancels (no selection).
    Fields 4 (display) and 5 (dimmed body excerpt) are both presented and
    searched via ``--with-nth 4,5`` so body content is discoverable — fzf
    only matches text it presents, so the excerpt must be shown to be found.
    The UI is themed to the active Omarchy theme and keys come from config.
    """
    cfg = cfg or load_config()
    preview_cmd = "om-search preview {2} {3}"
    header = f"{picker_header(mode, page_filter, group_filter)}\n{_nav_hint(cfg)}"

    cmd = ["fzf"]
    cmd += _base_fzf_args(cfg)
    cmd += [
        "--tiebreak=begin,end",
        "--ansi",
        "--delimiter",
        "\t",
        "--with-nth",
        "4,5",
        "--preview",
        preview_cmd,
        "--preview-window",
        "right:60%:wrap:border-rounded",
        "--header",
        header,
    ]

    copy = cfg.keys.get("copy")
    if copy:
        cmd += ["--bind", f"{copy}:execute-silent(echo -n {{2}} | wl-copy)+accept"]
    help_key = cfg.keys.get("help")
    if help_key:
        # Show the cheatsheet in the preview pane; moving the selection
        # re-runs --preview and restores the doc, giving a natural toggle.
        cmd += ["--bind", f"{help_key}:change-preview(om-search --keys)"]

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
    cfg: Config | None = None,
) -> str | None:
    """Run fzf over a simple list of strings (no tab-delimited fields).

    Returns the selected line, or None on cancel. Themed to match the picker.
    """
    cfg = cfg or load_config()
    cmd = ["fzf", "--tiebreak=end"]
    cmd += _base_fzf_args(cfg)
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