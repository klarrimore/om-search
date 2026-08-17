# om-search

Search the Omarchy Linux manual and CLI commands from the terminal.

## What it does

- Bundles the [Omarchy manual](https://github.com/basecamp/omarchy/tree/quattro/manual) for offline search
- Pulls the live `omarchy` CLI command tree on systems where it is installed
- Opens an interactive fzf picker: type to fuzzy-match across manual sections and commands together
- Doc results open in a markdown viewer (`glow`) or `less`
- Command results print to stdout; `Ctrl-Y` copies the command to the clipboard (Wayland)

## Install

- **AUR**: `yay -S om-search` (or `paru -S om-search`)
- **PyPI**: `uv tool install om-search` or `pip install om-search`

## Usage

```sh
om-search            # open the picker
om-search screenshot # open the picker with "screenshot" pre-filled
om-search update     # pull the latest manual and re-index commands
```

On machines without the `omarchy` CLI (e.g. non-Omarchy distros), the command
surface is disabled and doc search still works — degraded mode.

## How it works

The manual is cloned shallowly and sparsely into the XDG data dir
(`~/.local/share/om-search/omarchy-repo/manual`), tracking the `quattro`
branch. A pacman hook (shipped in `packaging/`) triggers `om-search update`
after every system update so the docs stay in sync with the installed release.

## Development

```sh
uv sync --extra dev
uv run pytest
uv run mypy src/
```
