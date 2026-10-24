# Search, filter, and browse

## Basic search

```sh
om-search                        # home route — pick a source
om-search <term>                 # search all sources, pre-filled
om-search screenshot region      # multi-word query
```

Results are ranked: exact title/heading matches first, then broader body
matches, with newer manual pages breaking ties. The picker fuzzy-matches
against page titles, section headings, command descriptions, and body excerpts.

## Source filtering

```sh
om-search --docs <term>          # manual documentation only
om-search --cmds <term>          # CLI commands only
```

## Browse by page or group

```sh
om-search --pages                # browse pages, pick one to search within
om-search --groups               # browse command groups, pick one
om-search --page 04-navigation.md   # search within a specific page
om-search --group capture           # search within a specific command group
```

The breadcrumb header at the top of the picker shows your current route.
`Esc` / `Left` backs up one level. `Esc` at the Home route quits.

## Print results (no picker)

```sh
om-search --print screenshot     # print ranked results as plain text
om-search screenshot | grep key  # auto-degrades when piped
```

When stdout is not a terminal (e.g. piped to `grep` or run in a script), the
picker is skipped and ranked results print as plain text automatically.

## Degraded mode

On machines without the `omarchy` CLI (non-Omarchy Linux), the command surface
is disabled. Doc search still works — `om-search` never hard-fails.