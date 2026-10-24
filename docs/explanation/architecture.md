# Architecture: hierarchical fzf routes

om-search does not open a separate fzf process for each mode or page. Instead
it starts **one** fzf session that routes through a hierarchy of named routes,
all within the same selector.

## Route model

The picker reads a **navigation dataset** — a directory of JSON files written
once at startup and read by fzf's `--preview`, `--bind`, and `--header`
mechanisms. Each route in the dataset contains:

- A **breadcrumb** (shown in the header)
- A **hint** (shown below the breadcrumb)
- A list of **rows** (displayed in the main window)
- A parent route ID for back-navigation

The route tree:

```
home
├── search (all | doc | cmd)
├── pages (browse by page)
│   └── search in page
├── groups (browse by group)
│   └── search in group
└── reader (document preview — not a list route)
    └── links (cross-reference link selection)
```

### Route transitions

- **Enter / Right** — descends into a route or opens a document. Implemented
  via `om-search nav-transition <dataset> <route>` which returns the new
  route's row data.
- **Left / Escape** — backs up one level by calling `nav-transition` with the
  parent route ID.
- **Escape at Home** — quits fzf (standard fzf escape behaviour).

### Reader as a route

When a document is focused (Tab or selection of a doc row), the preview pane
enlarges and the fzf prompt changes to "reading". Movement keys now control
the reader cursor instead of list navigation. This is not a separate window or
pager — it's the same fzf session with transformed key bindings, gated on the
prompt text.

### Cross-reference links

When a document contains `[label](NN-slug.md#anchor)` links, pressing Ctrl-L
opens a **links route** (child of the current reader position). Each link is a
row; selecting one opens the linked section. The back-stack returns through the
link list to the original document.

## Why fzf?

- Single binary dependency — no curses toolkit, no UI framework
- Fast fuzzy matching out of the box (begin/end tiebreaking)
- ANI preview, `--bind` transform expressions, and prompt-gated key remapping
  make the hierarchical reader possible without a second process
- Already installed on Omarchy

## Why not a separate pager process for everything?

`less` (via Ctrl-O) is available as an escape hatch for reading long documents,
but the inline reader avoids process overhead for quick lookups. The pre-built
preview cache (ANSI files) brings reader startup to ~35ms instead of reparsing
the 500KB+ index on every cursor move.