# Configure om-search

Configuration lives at `~/.config/om-search/config.toml`. A starter config is
available:

```sh
om-search --init-config
```

This writes a commented default that won't overwrite an existing file.

## Theme

```toml
[theme]
source = "omarchy"    # "omarchy" (default) | "catppuccin" | "none"
```

- **`omarchy`** — follow the active Omarchy desktop theme (reads the theme's
  `colors.toml`). Re-themes automatically when you switch themes.
- **`catppuccin`** — built-in Catppuccin Mocha palette. Used as fallback when
  the Omarchy theme is unavailable.
- **`none`** — no colour; overrides any colour setting including `--no-color`.

### Custom colours

You can override individual tokens under a `[theme.colors]` block:

```toml
[theme]
source = "omarchy"

[theme.colors]
background = "#1e1e2e"
foreground = "#cdd6f4"
accent = "#89b4fa"
```

Valid tokens: `background`, `foreground`, `accent`, `selection`, `muted`,
`red`, `green`, `bright_blue`, `dark_background`, `bright_foreground`.
Missing tokens fall through to the active theme or built-in palette.

## Keybindings

```toml
[keys]
down = "ctrl-j"
up = "ctrl-k"
half_page_down = "ctrl-d"
half_page_up = "ctrl-u"
preview_down = "ctrl-f"
preview_up = "ctrl-b"
copy = "ctrl-y"
help = "?"
```

These supplement the built-in selector keys (arrows, page keys, Enter, Esc,
Tab) which are **not** configurable. Only Ctrl chords and `?` are rebindable —
plain letter keys cannot be bound because they are reserved for fuzzy-search
input.

Print your current effective bindings:

```sh
om-search --keys
```

See the [Keybindings reference](docs/reference/keys.md) for the full set.