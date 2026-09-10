# om-search

Search the [Omarchy Linux](https://github.com/basecamp/omarchy) manual and CLI commands from the terminal.

## What it does

- Bundles the Omarchy manual for offline search
- Pulls the live `omarchy` CLI command tree on systems where it is installed
- Opens an interactive fzf picker: type to fuzzy-match across manual sections and commands together
- Fuzzy-matches against page titles and section headings in the picker display
- Doc results are rendered as markdown (`glow`, falling back to `mdcat` or `bat`) and opened in an interactive pager (`less`)
- Command results print to stdout; `Ctrl-Y` copies the command to the clipboard (Wayland)

## Install

### AUR (recommended on Omarchy / Arch Linux)

```sh
yay -S om-search
# or
paru -S om-search
```

The Arch package depends on `arch-wiki-lite` for local Arch Wiki text search.
The larger `arch-wiki-docs` HTML dump is optional and only needed for
`wiki-search-html`.

### PyPI

Requires `uv`:

```sh
sudo pacman -S --needed uv
```

```sh
uv tool install om-search
# or
pip install om-search
```

### From source

```sh
sudo pacman -S --needed uv
git clone https://github.com/klarrimore/om-search.git
cd om-search
uv build
uv tool install dist/*.whl
```

## Usage

```sh
om-search                    # open the picker with all sources
om-search screenshot         # open the picker, pre-filled with "screenshot"
om-search --docs             # search manual documentation only
om-search --cmds             # search CLI commands only
om-search --pages            # browse manual pages, pick one to search within
om-search --groups           # browse command groups, pick one to search within
om-search --page 04-navigation.md   # search within a specific page
om-search --group capture    # search within a specific command group
om-search --update           # pull the latest manual and re-index commands
```

On machines without the `omarchy` CLI (non-Omarchy distros), the command
surface is disabled and doc search still works -- degraded mode.

## Navigation model

`om-search` follows the Omarchy CLI style: common operations at the top
level, specialised scoping via flags.  The default picker shows all
documentation sections and CLI commands interleaved.  Use `--docs` or
`--cmds` to focus one source, or drill into a specific page or group
with `--page` or `--group`.

The `--pages` and `--groups` flags open a page/group browser (also fzf).
Picking a result launches a picker scoped to that page or group.

## Appearance and keybindings

The picker follows a herdr-style TUI: a rounded, bordered layout whose colours
track the **active Omarchy theme** (read from the theme's `colors.toml`, so it
re-themes when you switch themes), with vim-style navigation and a `?` help
overlay.

Default keys (all configurable):

| Key | Action |
| --- | --- |
| `Ctrl-J` / `Ctrl-K` | move down / up |
| `Ctrl-D` / `Ctrl-U` | half page down / up |
| `Ctrl-F` / `Ctrl-B` | scroll the preview |
| `Enter` | open the selection |
| `Ctrl-Y` | copy a command to the clipboard |
| `?` | show the keybindings (in the preview pane) |
| `Esc` | quit |

Plain letters still go to the fuzzy query — a fuzzy finder can't use bare
`j`/`k` for movement, so the vim navigation is on `Ctrl` chords.

Configure theme and keys in `~/.config/om-search/config.toml` (herdr-style
`[theme]` and `[keys]` tables):

```sh
om-search --init-config   # write a commented starter config
om-search --keys          # print the current keybindings
```

```toml
[theme]
# "omarchy" (default, follow active theme) | "catppuccin" | "none"
source = "omarchy"

[keys]
down = "ctrl-j"
up = "ctrl-k"
help = "?"
```

## How it works

The manual is cloned shallowly and sparsely into the XDG data dir
(`~/.local/share/om-search/omarchy-repo/manual/`), tracking the `quattro`
branch of the upstream Omarchy repository. On update it is parsed once into a
pre-built JSON index (`~/.local/share/om-search/index.json`) that the picker
and preview use directly for fast startup, so the 51 manual pages are not
re-parsed on every keystroke. A pacman hook (shipped in
`packaging/om-search.hook` and installed via the AUR package) triggers
`om-search --update` after every system update so the docs stay in sync
with the installed release.

## Development

```sh
sudo pacman -S --needed uv
uv sync --extra dev
uv run pytest
uv run mypy src/
```

## Packaging

The `packaging/` directory contains:

- **PKGBUILD** -- Arch Linux / AUR package recipe
- **om-search.hook** -- pacman hook that refreshes the doc index after an `omarchy` package upgrade

The AUR package intentionally uses `arch-wiki-lite` instead of the larger
`arch-wiki-docs` package. Install `arch-wiki-docs` only when browser-style
offline HTML lookup via `wiki-search-html` is needed.

## License

MIT -- see [LICENSE](LICENSE).
