# Integration

## Theme sync

om-search follows the active Omarchy desktop theme so it doesn't look out of
place when the user switches themes.

On every invocation (including the fzf preview process), the picker reads
`~/.local/state/omarchy/current/theme/colors.toml` — a normalized palette that
Omarchy writes for each theme. The palette is translated into an `fzf --color`
spec. When the user changes themes, the next invocation picks up the new
colours.

If the Omarchy palette is unavailable (non-Omarchy Linux, not installed),
a built-in Catppuccin Mocha palette is used as fallback. The `--no-color`
flag and `NO_COLOR` environment variable override everything.

## Pacman hook

The AUR package installs a pacman hook at
`/var/lib/pacman/local/om-search/om-search.hook` that runs
`om-search --update` after every `omarchy` package upgrade. This keeps the
bundled manual in sync with the installed release without user intervention.

The hook targets the `omarchy` package specifically — not all packages. A full
system update only triggers a manual refresh when the Omarchy itself was
updated.

## Degraded mode

On machines without the `omarchy` CLI:

- **documentation** — works fully (the manual is bundled)
- **commands** — the command surface is empty; the Home route shows only
  "Search all" and "Manual pages"

This is not a hard failure. om-search never crashes or refuses to run when
the CLI is absent. The option to search commands is simply omitted.

`om-search` also degrades gracefully when stdout is not a terminal: the picker
is skipped and results print as plain text, enabling headless/CI use.

## Clipboard integration

Command copy (Ctrl-Y) uses `wl-copy` (Wayland clipboard). This works on
Omarchy and any Wayland desktop with `wl-clipboard` installed.