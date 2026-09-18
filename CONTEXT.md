# om-search

A command-line utility for finding documentation and commands on Omarchy Linux. Bundles the Omarchy manual for offline search, and adds live command lookup for the installed `omarchy` CLI.

## Language

**Manual**:
The Omarchy documentation set: 51 numbered markdown files in the `manual/` directory of the basecamp/omarchy repo (quattro branch). The canonical source of truth for how Omarchy works.
_Avoid_: docs, documentation, wiki

**Command tree**:
The full hierarchy of the installed `omarchy` CLI's groups and commands, as returned by `omarchy commands --json`. Live data, only present on machines with the `omarchy` CLI installed.
_Avoid_: commands, command list, CLI reference

**Search surface**:
The unified interactive interface of `om-search`. Returns both manual sections and command tree entries in a single ranked result set.
_Avoid_: search box, picker

**Index**:
The local searchable structure built from the manual and (when available) the command tree. Populated on first run and refreshed on update.
_Avoid_: database, cache

**Degraded mode**:
The state of `om-search` on a machine without the `omarchy` CLI. Docs search works from the bundled manual; the command surface is empty or disabled. Never a hard failure.

**Update hook**:
The mechanism that refreshes the bundled manual after the Omarchy system updates, so the docs stay in sync with the installed release. A pacman hook triggers `om-search --update`.
_Avoid_: refresh, sync job

**Fuzzy picker**:
The single hierarchical fzf session that powers `om-search`: Home, search,
manual-page, command-group, section, reader, and link routes share one
selector. Enter/Right descends or focuses the preview; Left/Escape backs out.

**Doc section (selected result)**:
A manual section selected in a list route. It is displayed in the fzf preview
reader without leaving the current result list; `Ctrl-O` remains the full-page
pager escape hatch.

## Architecture

**Hyprland**:
The Wayland compositor and window manager on Omarchy. Config files at `~/.config/hypr/*.lua` (Lua-based in the quattro branch; any `*.conf` in that directory is an orphaned pre-quattro leftover). Auto-reloads on file save. Users search for keybindings, window rules, monitors, animations, lock screen, night light.
_Avoid_: i3, sway

**Omarchy shell**:
The Quickshell-based desktop shell providing the status bar, notifications, and on-screen display. Replaced the old Waybar/Mako/SwayOSD stack in the quattro (Quickshell) era. Configured via `~/.config/omarchy/shell.json` (top-level keys: `bar`, `idle`, `plugins`, `version`). `shell.json` and user plugin code hot-reload on save; apply harder changes with `omarchy restart shell`, reset with `omarchy refresh shell`.
_Avoid_: panel, taskbar

**Bar**:
The status bar within the Omarchy shell. Layout and widgets are managed with `omarchy bar` (`use`, `position`, `transparent`, `put`, `move`, `set`) and the `bar` block of `shell.json`. Widgets are shell plugins identified like `omarchy.clock` or `omarchy.keyboard-layout`. Clone a built-in widget to customize it: `omarchy plugin clone <id>`.
_Avoid_: Waybar, polybar, eww

**Omarchy menu**:
The Quickshell launcher/menu. Config at `~/.config/omarchy/extensions/omarchy-menu.jsonc`, which hot-reloads on save. Replaced Walker.
_Avoid_: Walker, rofi, dmenu

**Notifications**:
Provided by the Omarchy shell (Quickshell), not a standalone daemon. Replaced Mako.
_Avoid_: Mako, dunst, notify-send

**Omarchy OSD**:
The on-screen display for volume, brightness, caps lock, and similar, rendered by the Omarchy shell (Quickshell). Replaced SwayOSD.
_Avoid_: SwayOSD, volume popup, osd window

**Shell plugins**:
The unit of Omarchy shell customization: bar widgets and other shell components. Manage with `omarchy plugin` (`add`, `clone`, `enable`, `disable`, `list`). Built-in plugins ship in the packaged shell and must be cloned (`omarchy plugin clone <id>`) before editing; user copies live under `~/.config/omarchy/plugins/`.
_Avoid_: widgets, modules

**Terminals**:
Supported terminals: Alacritty (`~/.config/alacritty/alacritty.toml`), Foot (`~/.config/foot/foot.ini`), Kitty (`~/.config/kitty/kitty.conf`), Ghostty (`~/.config/ghostty/config`). Apply changes with `omarchy restart terminal`. Users search for font configuration, transparency, color scheme.
_Avoid_: gnome-terminal, konsole

**Keybindings**:
Hyprland key assignments defined in `~/.config/hypr/bindings.lua`. View current bindings with `omarchy-menu-keybindings --print`. Re-binding an existing key requires an `unbind` directive before the new `bind`.
_Avoid_: hotkeys, shortcuts

## Search topics

See `docs/search-topics.md` for the full cross-reference of user-facing search terms mapped to Omarchy manual pages, commands, and failure-mode gotchas.