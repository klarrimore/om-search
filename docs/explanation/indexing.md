# Indexing

## Pre-built JSON index

On update (`om-search --update` or the pacman hook), the manual is parsed once
and written to `~/.local/share/om-search/index.json`. This avoids re-parsing
the 300+ searchable sections on every keystroke.

Each entry in the index records:

- Page file, page number, page title
- Section heading, anchor, body text excerpt
- The full body text for rendering

The index is read at startup by the picker. Sections and page texts are loaded
into memory once and reused across all routes.

## Preview cache

`build_index` also writes one **preview file** per documentation entry into
`~/.local/share/om-search/previews/`. Each file contains the pre-rendered ANSI
text for that section (via `glow`/`mdcat`/`bat`).

The fzf preview command reads these files directly — it does not parse the
manual or call a markdown renderer on every cursor move. This cuts preview
latency from ~55ms to ~35ms per selection.

## Body-text matching

Every section's body text (cleaned of Markdown formatting, truncated to 120
characters) is stored as the fifth fzf candidate field. The picker uses
`--with-nth 6,7` to search both the display label and the body excerpt, so
words that appear only in a section's body (not its heading) are still
findable.

## Command tree

The command tree is **not** cached in the index. It is queried live from the
installed `omarchy` CLI via `omarchy commands --json` on every invocation. This
keeps the command surface always current with the installed version.

## Index versioning

The index format includes a `INDEX_VERSION` field. When the format changes,
`--update` regenerates the index. An old-format index is silently replaced on
the next update.