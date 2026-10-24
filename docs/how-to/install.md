# Install om-search

## AUR (recommended on Omarchy / Arch Linux)

```sh
yay -S om-search
# or
paru -S om-search
```

The AUR package includes a pacman hook that automatically runs
`om-search --update` after every system update, keeping the bundled manual in
sync with the installed release.

## PyPI with uv

Requires [uv](https://docs.astral.sh/uv/) (install via pacman or the Astral
installer):

```sh
sudo pacman -S --needed uv
uv tool install om-search
```

## Source

```sh
sudo pacman -S --needed uv
git clone https://github.com/klarrimore/om-search.git
cd om-search
uv build
uv tool install dist/*.whl
```

## Dependencies

The Arch package depends on `arch-wiki-lite` for local Arch Wiki text search.
The larger `arch-wiki-docs` HTML dump is optional and only needed for
`wiki-search-html`.

Runtime dependencies installed automatically:

- `fzf` — fuzzy picker
- `glow` — markdown rendering in the pager
- `less` — full-page pager (Ctrl-O)
- Python 3.12+ with `argcomplete`

## Verify the install

```sh
om-search --help
om-search --update    # clone the manual and build the index
om-search             # open the picker
```