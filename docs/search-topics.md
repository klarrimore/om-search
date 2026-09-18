# Search Topics

Cross-reference mapping user-facing search terms to Omarchy manual pages,
CLI commands, architecture components, and known gotchas. Intended as a
reference for om-search index coverage and future test-fixture generation.

## Theme management

Users searching for themes, wallpapers, or visual customization.

| Term | Manual page | CLI commands | Gotchas |
|------|-------------|--------------|---------|
| theme | `04-navigation` (Themes section) | `omarchy theme list`, `omarchy theme current`, `omarchy theme set <name>`, `omarchy theme switcher`, `omarchy theme install <url>`, `omarchy theme update` | Theme names use display format: `"Tokyo Night"` not `tokyo-night` |
| wallpaper | | `omarchy theme bg next`, `omarchy theme bg set <path>`, `omarchy theme bg-switcher` | |
| font | | `omarchy font list`, `omarchy font current`, `omarchy font set` | |

## Screenshots, recording & capture

| Term | Manual page | CLI commands | Gotchas |
|------|-------------|--------------|---------|
| screenshot | `12-screenshots-recording` | `omarchy capture screenshot [smart\|region\|windows\|fullscreen]` | Print Screen key freezes screen |
| screen recording | `12-screenshots-recording` | `omarchy capture screenrecording [--fullscreen] [--stop-recording]` | Alt+Print Screen opens picker |
| ocr / extract text | | `omarchy capture text` | OCR from a screenshot region |
| qr code | | `omarchy capture qr` | Decodes a QR from a screenshot region |

## Keybindings & navigation

| Term | Manual page | CLI commands | Gotchas |
|------|-------------|--------------|---------|
| keybindings | | `omarchy menu keybindings` | Re-binding needs `unbind` before `bind` in `~/.config/hypr/bindings.lua` |
| shortcuts | | | |
| navigation | `04-navigation` | `omarchy menu` | Super+Space opens the menu |
| hotkeys | | | |

## Window manager (Hyprland)

| Term | Manual page | CLI commands | Gotchas |
|------|-------------|--------------|---------|
| hyprland | | `omarchy restart hyprctl` | Config is Lua in quattro (not conf); auto-reloads on save |
| window rules | | `hyprctl reload` | Syntax changes between Hyprland versions; check wiki |
| animations | | | In `~/.config/hypr/looknfeel.lua` |
| gaps | | `omarchy hyprland window gaps toggle` | In `~/.config/hypr/looknfeel.lua` |
| borders | | | In `~/.config/hypr/looknfeel.lua` |
| transparency | | `omarchy hyprland window transparency toggle` | |
| monitors | | `hyprctl monitors` | Edit `~/.config/hypr/monitors.lua` |
| display | | | |

## Status bar (Omarchy shell)

Quickshell-based; replaced Waybar in the quattro era.

| Term | Manual page | CLI commands | Gotchas |
|------|-------------|--------------|---------|
| status bar | | `omarchy bar use\|position\|put\|move\|set`, `omarchy toggle bar`, `omarchy restart shell`, `omarchy refresh shell` | Config: `~/.config/omarchy/shell.json` (`bar` block); hot-reloads on save |
| waybar | | | Removed in quattro; now the Omarchy shell / `omarchy bar` |
| bar widgets / modules | | `omarchy plugin list`, `omarchy plugin clone <id>`, `omarchy plugin enable\|disable <id>` | Widgets are shell plugins, e.g. `omarchy.clock`, `omarchy.keyboard-layout`; clone before editing |

## Lock screen & idle

| Term | Manual page | CLI commands | Gotchas |
|------|-------------|--------------|---------|
| lock screen | | `omarchy system lock` | Idle-to-lock timeout in `shell.json` -> `idle.lock` (seconds) |
| idle | | `omarchy toggle idle` | `shell.json` `idle` block (`screensaver`, `lock`); no more `hypridle.lua` |
| screensaver | | `omarchy toggle screensaver` | `idle.screensaver` in `shell.json` |
| suspend | | `omarchy toggle suspend` | |
| screen off | | | |

## Night light

| Term | Manual page | CLI commands | Gotchas |
|------|-------------|--------------|---------|
| night light | | `omarchy toggle nightlight`, `omarchy restart hyprsunset`, `omarchy refresh hyprsunset` | Config at `~/.config/hypr/hyprsunset.conf` (schedules/profiles) |
| blue light | | | |

## App launcher / menu

Quickshell menu; replaced Walker in the quattro era.

| Term | Manual page | CLI commands | Gotchas |
|------|-------------|--------------|---------|
| menu / launcher | | `omarchy menu`, `omarchy menu clipboard\|emoji\|file\|input\|timezone` | Config: `~/.config/omarchy/extensions/omarchy-menu.jsonc` (hot-reloads) |
| app launcher | | `omarchy menu` | |
| walker | | | Removed in quattro; now `omarchy menu` |

## Notifications & OSD

Both provided by the Omarchy shell (Quickshell); Mako and SwayOSD are gone.

| Term | Manual page | CLI commands | Gotchas |
|------|-------------|--------------|---------|
| notifications | | `omarchy toggle notification silencing` | Rendered by the Omarchy shell; no standalone daemon |
| mako | | | Removed in quattro |
| osd | | | Omarchy OSD, part of the shell; no SwayOSD |

## Package management

| Term | Manual page | CLI commands | Gotchas |
|------|-------------|--------------|---------|
| install package | | `omarchy pkg add`, `omarchy pkg aur add` | `omarchy pkg add` is canonical; `omarchy pkg install` also exists |
| remove package | | `omarchy pkg drop`, `omarchy pkg remove` | |
| aur | | `omarchy pkg aur add` | |

## System operations

| Term | Manual page | CLI commands | Gotchas |
|------|-------------|--------------|---------|
| update | | `omarchy update` | Subcommands: `omarchy update available\|firmware\|keyring\|system pkgs\|aur pkgs` |
| version | | `omarchy version`, `omarchy version channel`, `omarchy version pkgs` | |
| shutdown | | `omarchy system shutdown` | |
| reboot | | `omarchy system reboot` | |
| logout | | `omarchy system logout` | |
| stats | | `omarchy system stats` | |
| debug | | `omarchy debug --no-sudo --print` | Ungrouped legacy binary (not in `omarchy commands`); without flags it hangs on a sudo prompt |
| reminder | | `omarchy reminder <minutes> [message]`, `omarchy reminder show`, `omarchy reminder clear` | Desktop-notification reminders |
| fingerprint | | `omarchy setup security fingerprint` | |
| reinstall | | `omarchy reinstall` | Destructive; ask before running |

## Config reset & refresh

| Term | Manual page | CLI commands | Gotchas |
|------|-------------|--------------|---------|
| reset config | | `omarchy refresh shell`, `omarchy refresh hyprland`, `omarchy refresh config <path>` | Creates timestamped backup; seek confirmation before running |
| refresh | | `omarchy refresh <target>` | Targets include: shell, hyprland, hyprsunset, herdr, tmux, config, pacman, limine, plymouth, sddm |
| restore defaults | | | No `refresh waybar` any more; use `refresh shell` |

## Terminal configuration

| Term | Manual page | CLI commands | Gotchas |
|------|-------------|--------------|---------|
| alacritty | | `omarchy restart terminal` | Config: `~/.config/alacritty/alacritty.toml` |
| foot | | `omarchy restart terminal` | Config: `~/.config/foot/foot.ini` |
| kitty | | `omarchy restart terminal` | Config: `~/.config/kitty/kitty.conf` |
| ghostty | | `omarchy restart terminal` | Config: `~/.config/ghostty/config` |
| default terminal | | `omarchy default terminal <alacritty\|foot\|ghostty\|kitty>` | |
| terminal font | | | |

## Themes & customisation (advanced)

| Term | Manual page | CLI commands | Gotchas |
|------|-------------|--------------|---------|
| custom theme | | `omarchy theme dir <name>`, `omarchy theme install <url>` | Create/overlay a dir under `~/.config/omarchy/themes/`; stock themes at `/usr/share/omarchy/themes/` (read-only) |
| hooks | | `omarchy hook install <type> <file>` | Scripts run from `~/.config/omarchy/hooks/`; installed via `omarchy hook install` |
| plugins | | `omarchy plugin add <git-url>`, `omarchy plugin clone <id>` | Clone built-in shell plugins before editing; user copies live in `~/.config/omarchy/plugins/` |

## Source file locations

Paths users commonly search for or reference:

| Path | Contains |
|------|----------|
| `~/.config/hypr/` | Hyprland Lua configs (bindings, monitors, input, looknfeel, autostart, hyprland) plus `hyprsunset.conf`, `xdph.conf` |
| `~/.config/omarchy/shell.json` | Omarchy shell config: `bar`, `idle`, `plugins`, `version` |
| `~/.config/omarchy/extensions/omarchy-menu.jsonc` | Quickshell menu/launcher config |
| `~/.config/omarchy/plugins/` | User shell plugins (cloned or git-added) |
| `~/.config/omarchy/themes/` | Custom / overlay themes |
| `~/.config/omarchy/hooks/` | Automation hooks |
| `/usr/share/omarchy/` | Package source, READ-ONLY: `bin/`, `config/`, `default/`, `themes/`, `shell/`, `migrations/`, `install/` |
| `/usr/share/omarchy/themes/` | Stock themes (read-only, managed by the omarchy package) |
| `$OMARCHY_PATH` | Resolves to `/usr/share/omarchy` |

## Command model

Omarchy ships a single `omarchy` CLI that dispatches `omarchy <group> <action>`
to the underlying `omarchy-*` binaries (367 routes across groups such as
`theme`, `bar`, `plugin`, `capture`, `menu`, `pkg`, `refresh`, `restart`,
`toggle`, `system`, `update`, `hook`, `reminder`). Prefer the grouped form; the
`omarchy-*` binaries remain on `PATH`. A few legacy binaries (e.g.
`omarchy-debug`) exist on `PATH` but are not listed in the command tree.

List everything with `omarchy commands` (or `omarchy commands --json`); scope to
one group with `omarchy <group> --help`.

## Related

- Architecture glossary in `../CONTEXT.md`
- Manual fixtures in `../tests/fixtures/manual/`
- Command fixture in `../tests/fixtures/commands/full-tree.json`