# Search Topics

Cross-reference mapping user-facing search terms to Omarchy manual pages,
CLI commands, architecture components, and known gotchas. Intended as a
reference for om-search index coverage and future test-fixture generation.

## Theme management

Users searching for themes, wallpapers, or visual customization.

| Term | Manual page | CLI commands | Gotchas |
|------|-------------|--------------|---------|
| theme | `04-navigation` (Themes section) | `omarchy-theme-list`, `omarchy-theme-current`, `omarchy-theme-set`, `omarchy-theme-next`, `omarchy-theme-bg-next`, `omarchy-theme-install` | Theme names use display format: `"Tokyo Night"` not `tokyo-night` |
| wallpaper | `omarchy-theme-bg-next` | | |
| font | | `omarchy-font-list`, `omarchy-font-current`, `omarchy-font-set` | |

## Screenshots & screen recording

| Term | Manual page | CLI commands | Gotchas |
|------|-------------|--------------|---------|
| screenshot | `12-screenshots-recording` | `omarchy-cmd-screenshot` | Print Screen key freezes screen |
| screen recording | `12-screenshots-recording` | | Alt+Print Screen opens picker |
| recording | `12-screenshots-recording` | | |

## Keybindings & navigation

| Term | Manual page | CLI commands | Gotchas |
|------|-------------|--------------|---------|
| keybindings | | `omarchy-menu-keybindings --print` | Re-binding needs `unbind` before `bind` in `~/.config/hypr/bindings.lua` |
| shortcuts | | | |
| navigation | `04-navigation` | | Super+Space opens menu |
| hotkeys | | | |

## Window manager (Hyprland)

| Term | Manual page | CLI commands | Gotchas |
|------|-------------|--------------|---------|
| hyprland | | | Config is Lua in quattro (not conf); auto-reloads on save |
| window rules | | `hyprctl reload` | Syntax changes between Hyprland versions; check wiki |
| animations | | | In `~/.config/hypr/looknfeel.lua` |
| gaps | | | In `~/.config/hypr/looknfeel.lua` |
| borders | | | In `~/.config/hypr/looknfeel.lua` |
| monitors | | `hyprctl monitors` | Edit `~/.config/hypr/monitors.lua` |
| display | | | |

## Status bar (Waybar)

| Term | Manual page | CLI commands | Gotchas |
|------|-------------|--------------|---------|
| waybar | | `omarchy-restart-waybar`, `omarchy-refresh-waybar`, `omarchy-toggle-waybar` | Does NOT auto-reload -- must run `omarchy-restart-waybar` |
| status bar | | | Config: `~/.config/waybar/config.jsonc`, styling: `style.css` |
| bar modules | | | |

## Lock screen & idle

| Term | Manual page | CLI commands | Gotchas |
|------|-------------|--------------|---------|
| lock screen | | `omarchy-lock-screen` | Config at `~/.config/hypr/hyprlock.lua` |
| idle | | | Config at `~/.config/hypr/hypridle.lua` |
| suspend | | | |
| screen off | | | |

## Night light

| Term | Manual page | CLI commands | Gotchas |
|------|-------------|--------------|---------|
| night light | | `omarchy-toggle-nightlight` | Config at `~/.config/hypr/hyprsunset.lua` |
| blue light | | | |

## App launcher (Walker)

| Term | Manual page | CLI commands | Gotchas |
|------|-------------|--------------|---------|
| walker | | `omarchy-restart-walker` | Config: `~/.config/walker/config.toml` |
| app launcher | | | |

## Notifications (Mako)

| Term | Manual page | CLI commands | Gotchas |
|------|-------------|--------------|---------|
| mako | | | Config under `~/.config/mako/` |
| notifications | | | |
| osd | | | SwayOSD at `~/.config/swayosd/` |

## Package management

| Term | Manual page | CLI commands | Gotchas |
|------|-------------|--------------|---------|
| install package | | `omarchy-pkg-add`, `omarchy-pkg-aur-add` | `omarchy-pkg-add` is canonical; `omarchy-pkg-install` also exists |
| remove package | | `omarchy-pkg-drop` | |
| aur | | `omarchy-pkg-aur-add` | |

## System operations

| Term | Manual page | CLI commands | Gotchas |
|------|-------------|--------------|---------|
| update | | `omarchy-update` | Full system update |
| version | | `omarchy-version` | |
| shutdown | | `omarchy-system-shutdown` | |
| reboot | | `omarchy-system-reboot` | |
| debug | | `omarchy-debug --no-sudo --print` | Without flags it launches an interactive sudo prompt that hangs |
| upload logs | | `omarchy-upload-log` | |
| fingerprint | | `omarchy-setup-fingerprint` | |
| reinstall | | `omarchy-reinstall` | Destructive; ask before running |

## Config reset & refresh

| Term | Manual page | CLI commands | Gotchas |
|------|-------------|--------------|---------|
| reset config | | `omarchy-refresh-waybar`, `omarchy-refresh-hyprland`, `omarchy-refresh-config` | Creates timestamped backup; seek confirmation before running |
| refresh | | `omarchy-refresh-<app>` | |
| restore defaults | | | |

## Terminal configuration

| Term | Manual page | CLI commands | Gotchas |
|------|-------------|--------------|---------|
| alacritty | | | Config: `~/.config/alacritty/alacritty.toml` |
| kitty | | `omarchy-restart-terminal` | Config: `~/.config/kitty/kitty.conf` |
| ghostty | | | Config: `~/.config/ghostty/config` |
| terminal font | | | |

## Themes & customisation (advanced)

| Term | Manual page | CLI commands | Gotchas |
|------|-------------|--------------|---------|
| custom theme | | | Create dir under `~/.config/omarchy/themes/`; stock themes at `~/.local/share/omarchy/themes/` |
| hooks | | | Scripts in `~/.config/omarchy/hooks/{theme-set,font-set,post-update}` |
| theme set | | | Hook receives theme name as $1 |

## Source file locations

Paths users commonly search for or reference:

| Path | Contains |
|------|----------|
| `~/.config/hypr/` | Hyprland Lua configs (bindings, monitors, input, looknfeel, envs, autostart, hypridle, hyprlock, hyprsunset) |
| `~/.config/waybar/` | Waybar config.jsonc + style.css |
| `~/.config/walker/config.toml` | Walker launcher config |
| `~/.config/mako/` | Notification daemon config |
| `~/.config/swayosd/` | On-screen display config |
| `~/.config/omarchy/themes/` | Custom themes |
| `~/.config/omarchy/hooks/` | Automation hooks |
| `~/.local/share/omarchy/themes/` | Stock themes (read-only, managed by git) |
| `~/.local/share/omarchy/bin/` | Source scripts |
| `~/.local/share/omarchy/config/` | Default config templates |
| `~/.local/share/omarchy/default/` | System defaults |
| `~/.local/share/omarchy/migrations/` | Update migrations |
| `~/.local/share/omarchy/install/` | Installation scripts |

## Command categories

Omarchy provides ~145 commands in 10 prefix categories:

| Category | Pattern | Example | Count (approx) |
|----------|---------|---------|----------------|
| Config reset | `omarchy-refresh-*` | `omarchy-refresh-waybar` | ~10 |
| Service restart | `omarchy-restart-*` | `omarchy-restart-waybar` | ~5 |
| Toggle | `omarchy-toggle-*` | `omarchy-toggle-nightlight` | ~5 |
| Theme | `omarchy-theme-*` | `omarchy-theme-set` | ~10 |
| Install software | `omarchy-install-*` | `omarchy-install-docker-dbs` | ~10 |
| Launch | `omarchy-launch-*` | `omarchy-launch-browser` | ~10 |
| System command | `omarchy-cmd-*` | `omarchy-cmd-screenshot` | ~15 |
| Package management | `omarchy-pkg-*` | `omarchy-pkg-add` | ~5 |
| Initial setup | `omarchy-setup-*` | `omarchy-setup-fingerprint` | ~10 |
| System updates | `omarchy-update-*` | `omarchy-update` | ~5 |

Plus non-prefixed commands: `omarchy-version`, `omarchy-debug`, `omarchy-lock-screen`,
`omarchy-menu-keybindings`, `omarchy-font-*`, `omarchy-system-*`, `omarchy-upload-log`,
`omarchy-reinstall`.

See the skill reference `skill://omarchy/references/commands.md` for the
authoritative command list.

## Related

- Architecture glossary in `../CONTEXT.md`
- Manual fixtures in `../tests/fixtures/manual/`
- Command fixture in `../tests/fixtures/commands/full-tree.json`