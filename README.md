# om-search

Search the [Omarchy Linux](https://github.com/basecamp/omarchy) manual and CLI commands from the terminal.

## What it does

- Bundles the Omarchy manual for offline search
- Pulls the live `omarchy` CLI command tree on systems where it is installed
- Opens an interactive fzf picker: type to fuzzy-match across manual sections and commands together
- Doc results open in a markdown viewer (`glow` / `mdcat`) or `less`
- Command results print to stdout; `Ctrl-Y` copies the command to the clipboard (Wayland)

## Install

### AUR (recommended on Omarchy / Arch Linux)

```sh
yay -S om-search
# or
paru -S om-search
```

### PyPI

```sh
uv tool install om-search
# or
pip install om-search
```

### From source

```sh
git clone https://github.com/klarrimore/om-search.git
cd om-search
uv build
uv tool install dist/*.whl
```

## Usage

```sh
om-search            # open the picker
om-search screenshot # open the picker with "screenshot" pre-filled
om-search update     # pull the latest manual and re-index commands
```

On machines without the `omarchy` CLI (non-Omarchy distros), the command
surface is disabled and doc search still works -- degraded mode.

## How it works

The manual is cloned shallowly and sparsely into the XDG data dir
(`~/.local/share/om-search/omarchy-repo/manual/`), tracking the `quattro`
branch of the upstream Omarchy repository. A pacman hook (shipped in
`packaging/om-search.hook` and installed via the AUR package) triggers
`om-search update` after every system update so the docs stay in sync
with the installed release.

## Development

```sh
uv sync --extra dev
uv run pytest
uv run mypy src/
```

## Packaging

The `packaging/` directory contains:

- **PKGBUILD** -- Arch Linux / AUR package recipe
- **om-search.hook** -- pacman hook that refreshes the doc index after an `omarchy` package upgrade

## License

MIT -- see [LICENSE](LICENSE).