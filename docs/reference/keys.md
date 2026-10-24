# Keybindings

## Built-in (always available)

These keys are hard-coded and cannot be remapped. They work in all routes.

| Key | List mode | Reader mode |
|-----|-----------|-------------|
| `Up` / `Down` | Move selection | Move cursor by line |
| `PageUp` / `PageDown` | Page the list | Move cursor by page |
| `Left` | Back one route (quit at Home) | Move cursor by character |
| `Right` | Descend or open | Move cursor by character |
| `Alt-Left` | — | Move cursor by word left |
| `Alt-Right` | — | Move cursor by word right |
| `Enter` | Descend into route or open | Refresh preview (stay in reader) |
| `Tab` | Focus reader on selected doc | Unfocus, return to list |
| `Escape` | Back one route (quit at Home) | Return to list |
| `Ctrl-]` | — | Toggle cursor mode (word ↔ character) |
| `Ctrl-O` | Open doc in full-screen pager | (same) |
| `Ctrl-L` | Follow cross-reference links on doc/link rows | (same) |
| `Ctrl-C` | Abort | Abort |

## Configurable

These supplement the built-in keys. Configured in
`~/.config/om-search/config.toml` under `[keys]`. Only Ctrl chords and `?` are
remappable — plain letters stay reserved for fuzzy-search input.

| Action | Default | List mode | Reader mode |
|--------|---------|-----------|-------------|
| `down` | `Ctrl-J` | Move selection down | Move cursor by line |
| `up` | `Ctrl-K` | Move selection up | Move cursor by line |
| `half_page_down` | `Ctrl-D` | Half-page down | Move cursor half a page |
| `half_page_up` | `Ctrl-U` | Half-page up | Move cursor half a page |
| `preview_down` | `Ctrl-F` | Scroll preview down | Move cursor by page |
| `preview_up` | `Ctrl-B` | Scroll preview up | Move cursor by page |
| `copy` | `Ctrl-Y` | Accept and copy command | — |
| `help` | `?` | Show keybinding overlay in preview | (same) |

Print your active bindings:

```sh
om-search --keys
```