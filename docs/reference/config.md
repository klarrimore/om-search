# Configuration file

**Path**: `~/.config/om-search/config.toml`

Created with:

```sh
om-search --init-config
```

## Format

```toml
[theme]
source = "omarchy"               # "omarchy" | "catppuccin" | "none"

[theme.custom]
# Optional colour overrides — any missing token falls through to the
# theme source or built-in Catppuccin Mocha palette.
# background = "#1e1e2e"
# foreground = "#cdd6f4"
# accent = "#89b4fa"

[keys]
# Additional Ctrl chords (plain letters are reserved for search input).
down = "ctrl-j"
up = "ctrl-k"
half_page_down = "ctrl-d"
half_page_up = "ctrl-u"
preview_down = "ctrl-f"
preview_up = "ctrl-b"
copy = "ctrl-y"
help = "?"
```

## Theme sources

| Value | Behaviour |
|-------|-----------|
| `omarchy` (default) | Read the active Omarchy theme's `colors.toml`. Re-themes on theme switch. |
| `catppuccin` | Built-in Catppuccin Mocha palette. Fallback when Omarchy is unavailable. |
| `none` | No custom fzf theming — use fzf's default terminal colours. Does **not** disable ANSI rendering or override `NO_COLOR`/`--no-color`. |

## Colour tokens (under `[theme.custom]`)

Overrideable under `[theme.custom]`. Only hex values accepted:

- `background`, `dark_background`
- `foreground`, `bright_foreground`
- `accent`, `selection`, `muted`
- `red`, `green`, `bright_blue`

## Key actions

Configurable under `[keys]`. Values are lowercase fzf key names (e.g.
`ctrl-j`, `ctrl-d`, `?`).

| Action | Default | Effect |
|--------|---------|--------|
| `down` | `ctrl-j` | Move selection or cursor down |
| `up` | `ctrl-k` | Move selection or cursor up |
| `half_page_down` | `ctrl-d` | Half-page cursor down in reader |
| `half_page_up` | `ctrl-u` | Half-page cursor up in reader |
| `preview_down` | `ctrl-f` | Page or preview down |
| `preview_up` | `ctrl-b` | Page or preview up |
| `copy` | `ctrl-y` | Copy command to clipboard and print |
| `help` | `?` | Toggle help overlay |

Built-in keys that are **not configurable**: `Up`, `Down`, `PageUp`, `PageDown`,
`Left`, `Right`, `Alt-Left`, `Alt-Right`, `Enter`, `Tab`, `Escape`, `Ctrl-]`,
`Ctrl-O`, `Ctrl-L`, `Ctrl-C`.