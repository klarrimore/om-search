# om-search

Search the [Omarchy Linux](https://github.com/basecamp/omarchy) manual and CLI
commands from the terminal. Bundles the full manual for offline use and pulls
the live command tree from the installed `omarchy` CLI when available.

## Quick start

### Install

**On Omarchy / Arch Linux (AUR):**

```sh
yay -S om-search
```

**With uv (any distro):**

```sh
sudo pacman -S --needed uv   # or install uv from https://docs.astral.sh/uv/
uv tool install om-search
```

See [Install](docs/how-to/install.md) for all methods (PyPI, source, AUR).

### First search

```sh
om-search
```

This opens a fuzzy finder (fzf) at a Home route with three choices:

- **Search all** — search docs and commands together (also the default when
  you type a query on the command line)
- **Manual pages** — browse pages, pick one to search within
- **Command groups** — browse groups, pick one to search within

Type to filter, `Enter` to descend, `Esc` to go back or quit.

### Search from the terminal

```sh
om-search screenshot            # open the picker with "screenshot" typed in
om-search screenshot region     # multi-word query
```

### Find a CLI command

```sh
om-search --cmds wallpaper       # search commands only
```

Select one and press `Enter` — the command (e.g. `omarchy theme bg next`)
prints to stdout. Press `Ctrl-Y` to print *and* copy to the Wayland clipboard
in one step.

### Read a manual section

```sh
om-search --docs navigation      # search docs only
```

Select a result. The selected section opens in the preview reader on the right.
Press `Tab` to focus the reader and scroll with arrow keys, `Enter` or `Esc`
to return to the list. Press `Ctrl-O` to open the full page in an interactive
pager (`less`), positioned at the matched heading.

### Keep the manual up to date

```sh
om-search --update
```

This pulls the latest manual from upstream and rebuilds the search index.
If installed via the AUR package, a pacman hook runs this automatically after
every system update.

## Next steps

- [Search, filter, and browse](docs/how-to/search.md) — source filters, page
  and group scoping, scoped search
- [Navigating the reader](docs/how-to/reader.md) — cursor modes, cross-reference
  links, pager escape
- [Configuration](docs/how-to/configure.md) — theme, keybindings, config file
- [CLI reference](docs/reference/cli.md) — all flags and subcommands
- [Keybindings](docs/reference/keys.md) — every key, default and configurable
- [How it works](docs/explanation/architecture.md) — hierarchical fzf routes,
  indexing, degraded mode

## License

MIT — see [LICENSE](LICENSE).