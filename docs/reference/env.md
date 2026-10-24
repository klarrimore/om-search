# Environment variables and file locations

## Environment

| Variable | Effect |
|----------|--------|
| `NO_COLOR` | Skip ANSI colour (honours the [no-color.org](https://no-color.org) convention). |
| `TERM=dumb` | Same as `NO_COLOR` — skips ANSI colour. |
| `XDG_DATA_HOME` | Override data directory. Default: `~/.local/share`. |
| `XDG_CONFIG_HOME` | Override config directory. Default: `~/.config`. |
| `XDG_STATE_HOME` | Override state directory for Omarchy theme lookup. Default: `~/.local/state`. |
| `_ARGCOMPLETE` | Set automatically during shell completion. Enables lazy `argcomplete` import. |

## File locations

| Path | Purpose |
|------|---------|
| `~/.config/om-search/config.toml` | User configuration (theme, keys). |
| `~/.local/share/om-search/index.json` | Pre-built JSON search index. |
| `~/.local/share/om-search/previews/` | Pre-rendered ANSI preview cache. |
| `~/.local/share/om-search/omarchy-repo/manual/` | Cloned Omarchy manual files. |
| `~/.local/state/omarchy/current/theme/colors.toml` | Active Omarchy theme palette. |

All paths resolve through `XDG_*_HOME` variables when set.