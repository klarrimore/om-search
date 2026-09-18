"""fzf integration: preview rendering and post-selection actions."""

import os
import re
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
from om_search.theme import color_enabled, fzf_color_spec, resolve_palette


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


def page_text(cand: DocCandidate) -> str:
    """Read the whole page for a doc candidate (for the open action).

    Opening a result shows the entire page — not just the matched
    subsection — so the reader keeps surrounding context and can scroll to
    adjacent sections. :func:`view_markdown` positions the pager at the
    matched heading. Prefers the pre-built index, falls back to disk.
    """
    index_data = load_index(data_dir() / INDEX_FILENAME)
    if index_data is not None:
        _, page_texts = index_data
        full = page_texts.get(cand.page_file)
        if full:
            return full
    path = manual_dir() / cand.page_file
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def heading_line(rendered: str, heading: str) -> int:
    """Return the 1-based line of ``heading`` in ``rendered`` output, or 0.

    Renderers (notably glow) inject ANSI resets *between* words, so a literal
    pager search for the heading text fails. Instead we scan the ANSI-stripped
    lines and match the heading phrase on a line that still carries its ``#``
    markers, which distinguishes the heading from body mentions.
    """
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
    """Return (kind, payload) for a selected candidate.

    ``doc`` -> ``("view", markdown)``  — rendered and paged by
    :func:`view_markdown`.
    ``cmd`` -> ``("echo", path)``       — printed to stdout for the shell.
    """
    if cand.type == "doc":
        return ("view", page_text(cast(DocCandidate, cand)))
    cmd = cast(CmdCandidate, cand)
    return ("echo", cmd.path)


def render_markdown(text: str) -> str:
    """Render markdown to ANSI using the best renderer available.

    Prefers true-markdown renderers (glow, mdcat) that style headings, lists
    and code; falls back to syntax-highlighted source (bat); finally returns
    the text unchanged. Never raises — a failing renderer is skipped.
    """
    if not color_enabled():
        # No-colour terminals: keep layout (glow's notty style) but no ANSI.
        if shutil.which("glow"):
            try:
                result = subprocess.run(
                    ["glow", "-s", "notty", "-"],
                    input=text, capture_output=True, text=True,
                )
                if result.returncode == 0 and result.stdout:
                    return result.stdout
            except OSError:
                pass
        return text
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


_ESC_LESSKEY_SRC = "#command\n\\e quit\n"


def _esc_lesskey_file() -> str | None:
    """Write (once) a lesskey source binding Esc -> quit; return its path.

    less >= 582 reads key bindings from the file named by ``LESSKEYIN``. This
    makes Esc quit the pager so it acts as a "back" key (returning to the
    picker loop); arrow keys still scroll because less longest-matches their
    escape sequences. Older less ignores ``LESSKEYIN`` and simply keeps ``q``.
    """
    try:
        path = data_dir() / "esc.lesskey"
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


# Bottom-line pager prompt: advertise that Esc/q go back, plus scroll/search.
# The short-prompt slot (-Ps) is the one less shows for piped stdin.
_LESS_PROMPT = "-Psq/Esc: back  \u00b7  \u2191\u2193/jk: scroll  \u00b7  /: search"


def view_markdown(text: str, jump_to: str | None = None) -> None:
    """Render markdown and show it in an interactive pager when possible.

    Renders with :func:`render_markdown`, then pages through ``less``. When
    ``jump_to`` (a heading) is given, the pager opens positioned at that
    section via ``+<line>`` so the reader lands on the match but can scroll
    for surrounding context. Esc (as well as ``q``) quits the pager so it acts
    as a "back" key, returning to the picker; a prompt line advertises this.
    ``-R`` keeps ANSI colour; the pager uses the alternate screen (no ``-X``)
    so quitting restores the caller's screen for a clean return to fzf. Falls
    back to writing to stdout when there is no TTY or no ``less``.
    """
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
    return f"Mode: {scope}  |  Enter: read · Ctrl+O: full · Ctrl+L: links · Ctrl+Y: copy"


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
        "  Open full page       Ctrl + O",
        "  Back / quit          Esc  (also Ctrl + C)",
        "",
        "Type to fuzzy-search titles and body text.",
        "(q is search input here, not quit — use Esc.)",
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
    if not color_enabled():
        args += ["--color", "bw"]
    else:
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
    return f"{down}/{up} move · Enter read · Ctrl+O full page · {help_key} keys · Esc quit"


BACK = "\x00BACK\x00"  # sentinel: user asked to pop back to the parent list

# Reading mode: Enter on a doc enlarges the preview and remaps movement keys
# to scroll it, emulating "focus the right pane" (fzf has no real focus-preview
# action). The mode flag is carried in the prompt so `transform` binds can test
# it; Esc leaves reading mode and Ctrl-O opens the full page in the pager.
_READING_MARK = "reading"
_READING_PROMPT = "  reading — Esc: back · Ctrl+O: full · Ctrl+L: links  "
_NORMAL_PROMPT = "  "
_READ_WIN = "right,90%,wrap,border-rounded"
_NORMAL_WIN = "right,60%,wrap,border-rounded"


def _reading_binds(cfg: Config) -> list[str]:
    """fzf --bind args implementing modal reading mode over the preview pane."""
    k = cfg.keys

    def modal(key: str, prev: str, lst: str) -> list[str]:
        return [
            "--bind",
            f"{key}:transform:[[ $FZF_PROMPT == *{_READING_MARK}* ]] "
            f"&& echo {prev} || echo {lst}",
        ]

    binds: list[str] = [
        # Enter: a doc opens in the (enlarged) right pane; a command is accepted.
        "--bind",
        "enter:transform:[[ {1} == doc ]] && "
        f'echo "change-preview(om-search preview {{2}})'
        f"+change-preview-window({_READ_WIN})"
        f'+change-prompt({_READING_PROMPT})" || echo accept',
        # Esc: leave reading mode (restore pane), else abort (caller = back/quit).
        "--bind",
        f"esc:transform:[[ $FZF_PROMPT == *{_READING_MARK}* ]] && "
        f'echo "change-preview(om-search preview {{2}} {{3}})'
        f"+change-preview-window({_NORMAL_WIN})"
        f'+change-prompt({_NORMAL_PROMPT})" || echo abort',
        # Ctrl-O: open the full page in the scrollable pager (docs only).
        "--bind",
        'ctrl-o:transform:[[ {1} == doc ]] && echo "execute(om-search open {2} {3})"',
        # Ctrl-L: follow a cross-reference link on this page (docs only).
        "--bind",
        'ctrl-l:transform:[[ {1} == doc ]] && echo "execute(om-search links {2})"',
    ]
    # While reading, movement keys scroll the preview instead of the list.
    binds += modal(k.get("down", "ctrl-j"), "preview-down", "down")
    binds += modal(k.get("up", "ctrl-k"), "preview-up", "up")
    binds += modal(k.get("half_page_down", "ctrl-d"),
                   "preview-half-page-down", "half-page-down")
    binds += modal(k.get("half_page_up", "ctrl-u"),
                   "preview-half-page-up", "half-page-up")
    binds += modal("down", "preview-down", "down")
    binds += modal("up", "preview-up", "up")
    binds += modal("pgdn", "preview-page-down", "page-down")
    binds += modal("pgup", "preview-page-up", "page-up")
    return binds


def run_fzf(
    candidates: list[str],
    query: str = "",
    mode: str = "all",
    page_filter: str | None = None,
    group_filter: str | None = None,
    cfg: Config | None = None,
    back: bool = False,
) -> str | None:
    """Run fzf over the rendered candidates, returning the selected line.

    Returns None when the user cancels (no selection).
    Fields 4 (display) and 5 (dimmed body excerpt) are both presented and
    searched via ``--with-nth 4,5`` so body content is discoverable — fzf
    only matches text it presents, so the excerpt must be shown to be found.
    The UI is themed to the active Omarchy theme and keys come from config.

    When ``back`` is set (a scoped picker drilled in from a page/group list),
    Left arrow and Esc return the :data:`BACK` sentinel so the caller can pop
    back to its parent list instead of exiting.
    """
    cfg = cfg or load_config()
    preview_cmd = "om-search preview {2} {3}"
    nav = _nav_hint(cfg)
    if back:
        nav += " · ←: back"
    header = f"{picker_header(mode, page_filter, group_filter)}\n{nav}"

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
    if back:
        # Left arrow becomes an accept key reported on the first output line.
        cmd += ["--expect", "left"]

    copy = cfg.keys.get("copy")
    if copy:
        cmd += ["--bind", f"{copy}:execute-silent(echo -n {{2}} | wl-copy)+accept"]
    help_key = cfg.keys.get("help")
    if help_key:
        # Show the cheatsheet in the preview pane; moving the selection
        # re-runs --preview and restores the doc, giving a natural toggle.
        cmd += ["--bind", f"{help_key}:change-preview(om-search --keys)"]

    # Modal reading mode (Enter=read in pane, movement scrolls it, Esc=back,
    # Ctrl-O=full pager). Appended last so it overrides the plain movement
    # binds from _base_fzf_args (fzf uses the last bind for a key).
    cmd += _reading_binds(cfg)

    if query:
        cmd.extend(["--query", query])

    proc = subprocess.run(
        cmd,
        input="\n".join(candidates) + "\n",
        text=True,
        capture_output=True,
    )
    if back:
        lines = proc.stdout.split("\n")
        key = lines[0].strip() if lines else ""
        if key == "left" or proc.returncode == 130:  # Left or Esc/Ctrl-C
            return BACK
        for line in lines[1:]:
            if line.strip():
                return line.strip()
        return None
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