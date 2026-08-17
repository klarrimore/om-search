# om-search

A command-line utility for finding documentation and commands on Omarchy Linux. Bundles the Omarchy manual for offline search, and adds live command lookup for the installed `omarchy` CLI.

## Language

**Manual**:
The Omarchy documentation set: 51 numbered markdown files in the `manual/` directory of the basecamp/omarchy repo (quattro branch). The canonical source of truth for how Omarchy works.
_Avoid_: docs, documentation, wiki

**Command tree**:
The full hierarchy of the installed `omarchy` CLI's groups and commands, as returned by `omarchy commands --json`. Live data, only present on machines with the `omarchy` CLI installed.
_Avoid_: commands, command list, CLI reference

**Search surface**:
The unified interactive interface of `om-search`. Returns both manual sections and command tree entries in a single ranked result set.
_Avoid_: search box, picker

**Index**:
The local searchable structure built from the manual and (when available) the command tree. Populated on first run and refreshed on update.
_Avoid_: database, cache

**Degraded mode**:
The state of `om-search` on a machine without the `omarchy` CLI. Docs search works from the bundled manual; the command surface is empty or disabled. Never a hard failure.

**Update hook**:
The mechanism that refreshes the bundled manual after the Omarchy system updates, so the docs stay in sync with the installed release. A pacman hook triggers `om-search update`.
_Avoid_: refresh, sync job

**Fuzzy picker**:
The interactive result selector (fzf) that `om-search` always opens. When invoked without arguments, starts empty. When invoked with a query (`om-search screenshot`), pre-populates the search prompt. Ships with Omarchy, so a zero-install dependency for the target audience.

**Doc section (selected result)**:
A manual section chosen from the fuzzy picker. Displayed through a markdown viewer / `less`.
_Avoid_: open in browser, open in editor

**Command (selected result)**:
An `omarchy` CLI command chosen from the fuzzy picker. Printed to stdout. The user can also copy it to the clipboard via a keybinding.
_Avoid_: execute directly, shell out
