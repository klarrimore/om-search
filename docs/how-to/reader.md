# Navigate documents in the reader

Selecting a doc result opens it in the preview reader on the right pane, with
the matched section visible. This is not the external pager — it's an in-place
reader using the same fzf session.

## Reader controls

| Key | Action |
|-----|--------|
| `Up` / `Down` | move cursor by line |
| `PageUp` / `PageDown` | move cursor by page |
| `Left` / `Right` | move cursor by character |
| `Alt-Left` / `Alt-Right` | move cursor by word |
| `Ctrl-]` | toggle cursor mode (word ↔ character) |

Plain letters remain fuzzy-search input at all times.

## Focusing and unfocusing

Press **`Tab`** to toggle between the list and reader. When the reader is
focused (the prompt shows "reading"), the movement keys above scroll the
document. Press `Tab` again to return to the result list.

Press **`Esc`** or **`Left`** to leave the reader and return to the list.
`Esc` at the Home route quits om-search entirely.

## Pager escape hatch

Press **`Ctrl-O`** to open the current doc in the full-screen `less` pager.
The pager opens positioned at the matched heading. `q` or `Esc` returns to
the picker.

## Cross-reference links

When the focused document contains links to other manual pages (shown as
`[label](NN-title.md#anchor)`), press **`Ctrl-L`** to open a link selection
list. Choose a link to navigate to that section. `Esc` returns to the link
list, and again to the original document.

This works for:

- Links to other pages: `[See navigation](04-navigation.md#window-rules)`
- Same-page anchors (treated as scrolling to that heading)

## Copying a command

If the focused item is a command result (tagged `[cmd]`), pressing **`Ctrl-Y`**
prints it to stdout and copies it to the Wayland clipboard in one step.