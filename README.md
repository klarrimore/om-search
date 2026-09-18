# om-search

Search the [Omarchy Linux](https://github.com/basecamp/omarchy) manual and CLI commands from the terminal.

## What it does

- Bundles the Omarchy manual for offline search
- Pulls the live `omarchy` CLI command tree on systems where it is installed
- Opens one hierarchical fzf session: Home, search, manual-page, command-group,
  section, reader, and cross-reference routes all share the same selector
- Fuzzy-matches page titles, section headings, command descriptions, and body
  excerpts in every list route
- Docs focus in the preview reader; `Ctrl-O` remains the full-page pager escape
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
om-search --print foo        # print ranked results as plain text (no picker)
om-search --no-color         # disable ANSI colour (also honors NO_COLOR/TERM=dumb)
```


When stdout is not a terminal (e.g. piped into `grep`), the picker is skipped and
the ranked results are printed as plain text automatically, the same as `--print`.
On machines without the `omarchy` CLI (non-Omarchy distros), the command
surface is disabled and doc search still works -- degraded mode.

`om-search` starts at a Home route with `Search all`, `Manual pages`, and
`Command groups` when the live command tree is available. `Enter` or `Right`
descends into a route; `Left` or `Escape` backs out. Selecting a document
focuses its preview as a reader without leaving the current result list.

`--docs` and `--cmds` enter source-filtered search routes. `--pages` and
`--groups` enter their browsing routes, while `--page` and `--group` enter a
specific scoped route. Cross-references opened with `Ctrl-L` use the same fzf
session and return to their link list before the originating route.

## Appearance and keybindings

The picker follows a herdr-style TUI: a rounded, bordered layout whose colours
track the **active Omarchy theme** (read from the theme's `colors.toml`, so it
re-themes when you switch themes), with vim-style navigation and a `?` help
overlay.

| Key | Action |
| --- | --- |
| `Up` / `Down` | select in lists / move between lines in the reader |
| `PageUp` / `PageDown` | page lists / page the reader cursor |
| `Left` / `Right` | back in lists / move by character in the reader |
| `Alt-Left` / `Alt-Right` | move by word in the reader |
| `Ctrl-]` | toggle word and character cursor modes |
| `Enter` | descend, focus a document, or accept a command |
| `Tab` | focus / unfocus the reader |
| `Escape` | back one route; Escape quits at Home |
| `Ctrl-J` / `Ctrl-K` | additional configured move down / up |
| `Ctrl-D` / `Ctrl-U` | additional configured half-page cursor movement |
| `Ctrl-L` | follow cross-reference links |
| `Ctrl-Y` | copy and accept a command |
| `?` | show the keybindings in the preview |

Plain letters remain fuzzy-search input. Configure the additional Ctrl chords
in `~/.config/om-search/config.toml`.

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
