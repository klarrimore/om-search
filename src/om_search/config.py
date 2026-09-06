"""User configuration for om-search — theme and keybindings.

Modeled on herdr's ``config.toml``: a ``[theme]`` table and a ``[keys]`` table,
read from ``~/.config/om-search/config.toml`` and layered over built-in
defaults. Missing file or bad values fall back to the defaults, never an error.
"""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from om_search.paths import config_path

# Action -> default fzf key. Only Ctrl-chords, Enter, and "?" are bound so that
# plain letters keep flowing into the fuzzy query (a fuzzy finder cannot use
# bare j/k for movement — those are search input). This mirrors herdr's vim
# navigation as closely as an fzf picker allows.
DEFAULT_KEYS: dict[str, str] = {
    "down": "ctrl-j",
    "up": "ctrl-k",
    "half_page_down": "ctrl-d",
    "half_page_up": "ctrl-u",
    "preview_down": "ctrl-f",
    "preview_up": "ctrl-b",
    "copy": "ctrl-y",
    "help": "?",
    "open": "enter",
}

# Actions bound to real fzf movement/preview actions. "open" and "copy" are
# handled separately (accept / clipboard), so they are not in this map.
_MOVEMENT_ACTIONS: dict[str, str] = {
    "down": "down",
    "up": "up",
    "half_page_down": "half-page-down",
    "half_page_up": "half-page-up",
    "preview_down": "preview-half-page-down",
    "preview_up": "preview-half-page-up",
}

VALID_THEME_SOURCES = ("omarchy", "catppuccin", "none")


@dataclass
class Config:
    theme_source: str = "omarchy"
    theme_custom: dict[str, str] = field(default_factory=dict)
    keys: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_KEYS))

    def movement_binds(self) -> list[str]:
        """Return ``key:action`` bind strings for navigation and preview."""
        binds = []
        for action, fzf_action in _MOVEMENT_ACTIONS.items():
            key = self.keys.get(action)
            if key:
                binds.append(f"{key}:{fzf_action}")
        return binds


def load_config(path: Path | None = None) -> Config:
    """Load config, layering user values over defaults. Never raises."""
    cfg = Config()
    p = path or config_path()
    try:
        with open(p, "rb") as fh:
            data = tomllib.load(fh)
    except (FileNotFoundError, NotADirectoryError, PermissionError, tomllib.TOMLDecodeError):
        return cfg

    theme = data.get("theme")
    if isinstance(theme, dict):
        src = theme.get("source")
        if isinstance(src, str) and src in VALID_THEME_SOURCES:
            cfg.theme_source = src
        custom = theme.get("custom")
        if isinstance(custom, dict):
            cfg.theme_custom = {
                k: v for k, v in custom.items() if isinstance(v, str)
            }

    keys = data.get("keys")
    if isinstance(keys, dict):
        for action, key in keys.items():
            if action in DEFAULT_KEYS and isinstance(key, str):
                # An empty string unbinds the action.
                cfg.keys[action] = key

    return cfg


CONFIG_TEMPLATE = """\
# om-search configuration
# Place this file at ~/.config/om-search/config.toml

[theme]
# Where the picker's colours come from:
#   "omarchy"    follow the active Omarchy theme (default; switches with it)
#   "catppuccin" a fixed Catppuccin Mocha palette
#   "none"       no colours; inherit the terminal
# source = "omarchy"

# Override individual fzf colour roles on top of the resolved palette.
# Accepts hex values keyed by palette token name.
# [theme.custom]
# accent = "#f5c2e7"
# background = "#11111b"

[keys]
# fzf key names. Ctrl-chords keep plain typing free for the search query.
# Set a value to "" to unbind it. "open" is always Enter.
# down = "ctrl-j"
# up = "ctrl-k"
# half_page_down = "ctrl-d"
# half_page_up = "ctrl-u"
# preview_down = "ctrl-f"
# preview_up = "ctrl-b"
# copy = "ctrl-y"
# help = "?"
"""


def write_default_config(path: Path | None = None) -> Path:
    """Write the commented default config if it does not already exist."""
    p = path or config_path()
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(CONFIG_TEMPLATE, encoding="utf-8")
    return p
