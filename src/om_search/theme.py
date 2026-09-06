"""Theme the fzf UI to match the active Omarchy theme (herdr-like look).

Omarchy writes a normalized palette to ``<active theme>/colors.toml`` with
named tokens (background, foreground, accent, selection, ...). We read that
and translate it into an ``fzf --color`` spec so the picker follows whatever
theme the desktop is on, switching automatically when the user changes themes.
Falls back to a built-in Catppuccin Mocha palette off Omarchy.
"""

import tomllib
from pathlib import Path

from om_search.paths import active_theme_dir

# Built-in fallback (Catppuccin Mocha) — herdr's out-of-box family — used when
# no Omarchy theme palette is available.
CATPPUCCIN_MOCHA: dict[str, str] = {
    "mode": "dark",
    "background": "#1e1e2e",
    "dark_background": "#181825",
    "foreground": "#cdd6f4",
    "bright_foreground": "#ffffff",
    "selection": "#313244",
    "muted": "#585b70",
    "accent": "#89b4fa",
    "red": "#f38ba8",
    "green": "#a6e3a1",
    "bright_blue": "#74c7ec",
}


def load_palette(theme_dir: Path | None = None) -> dict[str, str] | None:
    """Read the active Omarchy theme palette, or ``None`` when unavailable."""
    tdir = theme_dir or active_theme_dir()
    colors = tdir / "colors.toml"
    try:
        with open(colors, "rb") as fh:
            data = tomllib.load(fh)
    except (FileNotFoundError, NotADirectoryError, PermissionError, tomllib.TOMLDecodeError):
        return None
    # Keep only scalar string entries (the palette); ignore any tables.
    return {k: v for k, v in data.items() if isinstance(v, str)}


def resolve_palette(
    source: str = "omarchy",
    overrides: dict[str, str] | None = None,
) -> dict[str, str] | None:
    """Resolve the palette for a theme source.

    ``omarchy``    -> the active theme, falling back to Catppuccin.
    ``catppuccin`` -> the built-in Catppuccin Mocha palette.
    ``none``       -> ``None`` (no colours; fzf inherits the terminal).
    ``overrides`` (from ``[theme.custom]``) are layered on top.
    """
    if source == "none":
        return None
    if source == "catppuccin":
        palette = dict(CATPPUCCIN_MOCHA)
    else:  # "omarchy" (default)
        palette = load_palette() or dict(CATPPUCCIN_MOCHA)
    if overrides:
        palette.update({k: v for k, v in overrides.items() if isinstance(v, str)})
    return palette


def fzf_color_spec(palette: dict[str, str]) -> str:
    """Build an ``fzf --color`` value from a palette.

    Missing tokens are simply skipped, so a partial palette still themes what
    it can.
    """
    def c(*names: str) -> str | None:
        for n in names:
            if palette.get(n):
                return palette[n]
        return None

    mapping: dict[str, str | None] = {
        "bg": c("background"),
        "fg": c("foreground"),
        "hl": c("accent", "blue"),
        "fg+": c("bright_foreground", "light_foreground", "foreground"),
        "bg+": c("selection"),
        "hl+": c("bright_blue", "accent"),
        "gutter": c("background"),
        "border": c("muted", "selection"),
        "label": c("muted", "foreground"),
        "header": c("accent", "blue"),
        "info": c("muted", "dark_foreground"),
        "prompt": c("accent", "green"),
        "pointer": c("red", "accent"),
        "marker": c("green", "accent"),
        "spinner": c("accent"),
        "query": c("bright_foreground", "foreground"),
        "preview-bg": c("dark_background", "background"),
        "preview-fg": c("foreground"),
    }
    parts = [f"{k}:{v}" for k, v in mapping.items() if v]
    return ",".join(parts)
