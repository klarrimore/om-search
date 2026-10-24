# CLI reference

## Synopsis

```
om-search [--docs | --cmds] [--pages | --groups] [--page FILE | --group NAME]
          [--print | --no-color] [--update | --keys | --init-config | --completion]
          [query ...]
```

## Flags

| Flag | Description |
|------|-------------|
| `query ...` | Optional search query. Pre-fills the picker when interactive, or filters printed results with `--print`. |
| `--docs` | Search manual documentation only. |
| `--cmds` | Search CLI commands only. |
| `--pages` | Browse manual pages, then pick one to search within. |
| `--groups` | Browse command groups, then pick one to search within. |
| `--page FILE` | Search within a specific manual page (e.g. `04-navigation.md`). |
| `--group NAME` | Search within a specific command group (e.g. `capture`). |
| `--update` | Pull the latest manual from upstream and rebuild the search index. |
| `--print` | Print ranked results as plain text to stdout. |
| `--no-color` | Disable ANSI colour. Implies `NO_COLOR=1` for child processes. |
| `--keys` | Print the current keybinding cheatsheet and exit. |
| `--init-config` | Write a commented default config and exit (no-op if one exists). |
| `--completion` | Print shell completion setup to add to `~/.bashrc` or `~/.zshrc`. |
| `--help` | Print help and exit. |

## Auto-detection

- When stdout is not a terminal (piped into `grep`, run in CI), the picker is
  skipped and results print as plain text — same as `--print`.
- On machines without the `omarchy` CLI, command results are omitted. Doc
  search works normally. This is **degraded mode** — never a hard error.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success (including user quit from the picker) |
| 1 | Update failed, invalid arguments, or navigation error |

## Internal subcommands

These are used internally by the fzf picker and should not be invoked directly:

| Command | Purpose |
|---------|---------|
| `nav-data <dataset> <route>` | Route manifest |
| `nav-preview <dataset> <row>` | Preview for a list row |
| `nav-reader-preview <dataset> <preview> [lines]` | Reader viewport |
| `nav-reader-move <dataset> <preview> <movement> [lines]` | Reader cursor movement |
| `nav-transition <dataset> <route> [--enter|--focus|--links]` | Route transitions |
| `nav-open <dataset> <row>` | Open in full-screen pager (Ctrl-O) |
| `nav-copy <dataset> <row>` | Copy command to clipboard (Ctrl-Y) |
| `preview <key1> [key2]` | Legacy preview (retained for external callers) |