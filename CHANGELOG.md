# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-09-19

### Added
- `NO_COLOR`, `TERM=dumb`, and a `--no-color` flag are now honored — the fzf UI, the doc renderer, and the pager all drop ANSI colour when asked. `--no-color` sets `NO_COLOR` so child processes (fzf, preview, pager) inherit it.
- Plain output for non-interactive use: a `--print` flag emits ranked results as plain text, and om-search auto-degrades to the same when stdout is not a TTY — so `om-search --docs foo | grep …` and headless/CI use work instead of failing to open a picker.

### Changed
- Preview latency roughly halved (~55ms → ~35ms per selection): `build_index` now writes a per-entry preview file, and the preview path reads that file directly instead of parsing the whole 426KB index on every cursor move. Run `om-search --update` (or the pacman hook) to generate the preview files.
- Faster startup: `argcomplete` is imported only during shell completion, off the normal launch path.

## [0.3.0] - 2026-09-19

### Fixed
- Doc navigation: the manual parser now splits sections on `###` (H3) as well as `##` (H2). The current Omarchy manual uses H3 for most subsections, so 24 of 51 pages previously collapsed into a single unnavigable blob — every doc hit opened the whole page instead of the matched subsection. Sectioning the manual this way takes it from 186 to 301 searchable sections. Rebuild the local index with `om-search --update` to pick up the finer sections.
- Doc viewer "back" key: pressing Esc in an open doc now returns to the picker (a `LESSKEYIN` binding maps Esc to quit `less`; arrow keys still scroll because less longest-matches their escape sequences). Previously only `q` closed the pager and Esc did nothing, so there was no working back button. A bottom prompt now advertises `q/Esc: back · ↑↓/jk: scroll · /: search`.
- Drill-down "back": in the `--pages`/`--groups` flow, pressing Left (or Esc) in the scoped picker now returns to the page/group list instead of exiting, so you can browse into a page, back out, and pick another. The header advertises `←: back`.

### Changed
- Doc reading: pressing Enter on a doc now opens it in the **right pane** and gives that pane focus — the preview enlarges and the movement keys (Ctrl-J/K, arrows, PgUp/Dn) scroll it, with Esc returning to the list. This "reading mode" is emulated with fzf `transform` binds keyed off the prompt, since fzf has no native focus-preview action. **Ctrl-O** opens the full page in the scrollable `less` pager instead, positioned at the matched heading (via `less +<line>` computed from the rendered output so it works through glow's ANSI styling); Esc/`q` return to the picker. Selecting a command still accepts and prints it.
- Omarchy menu plugin: added nerd-font icons to every Manual row, trimmed the submenu from six rows to four (dropped the redundant scoped `--docs`/`--cmds` searches, which Search already covers), and switched the interactive pickers to `omarchy-launch-or-focus-tui` with per-mode `--app-id`s so re-opening a mode focuses its existing window instead of spawning a new terminal.

## [0.2.0] - 2026-09-18

### Added
- Source filtering: `--docs` and `--cmds` flags to search only documentation or only CLI commands. (#5)
- Page and group browsing: `--pages` and `--groups` flags for drill-down navigation. (#5)
- `--page <file>` and `--group <name>` flags for scoped search within a specific page or command group. (#5)
- `--update` flag (replaces the ``update`` subcommand) for refreshing the manual. (#5)
- Page list and group list helpers exposed from the library layer. (#5)
- Pre-built JSON index for faster startup and preview rendering. (#7)
- Body-text matching in fzf search (body excerpts indexed as a fifth candidate field). (#7)
- Index rebuilt automatically after manual clone and pull. (#7)
- `build_index` and `load_index` helpers exposed from the index layer. (#7)
- herdr-style TUI: rounded bordered layout, vim-style navigation (`Ctrl-J`/`Ctrl-K`, half-page and preview scroll), and a `?` help overlay rendered in the preview pane.
- Picker colours follow the active Omarchy theme (parsed from the theme's `colors.toml`) and re-theme on theme switch; `catppuccin` and `none` sources also available.
- TOML configuration at `~/.config/om-search/config.toml` with `[theme]` and `[keys]` tables. New `--init-config` (write a starter config) and `--keys` (print the keybindings) flags.
- Ranking eval fixture covering first-result relevance and newest-manual-page tie-break behavior.
- Omarchy menu plugin that adds om-search launchers to the Quickshell menu.

### Fixed
- Interactive search query (`om-search <term>`) now filters the picker correctly instead of displaying all results — fzf `--nth 4,5` operated on the transformed (single-field) line, making the fields unreachable. (#8)
- Body-text matching now actually works: the picker presents and searches both the display field and the body excerpt via fzf `--with-nth 4,5`. Previously `--with-nth 4` limited both display and search to the title/heading, so words appearing only in a section body were unfindable. The excerpt is shown dimmed (ANSI) and stripped back off on selection.
- Initial search queries now filter out unrelated zero-score candidates when direct matches exist, preventing broad fuzzy matches like `herdr` from flooding the picker.
- Command surface restored on current Omarchy: `omarchy commands --json` now emits an `{ok, commands: [...]}` envelope whose items carry `route`/`group`/`name`/`summary`. The parser ignored this shape and returned zero commands, silently dropping every machine into docs-only degraded mode. The full-tree test fixture was regenerated in the real envelope shape (quattro/Quickshell command tree) and the fixture tests updated accordingly.

### Changed
- CLI argument parsing… switched to flags (``--docs``, ``--pages``, etc.) instead of subparsers, following the Omarchy CLI convention.  The ``preview`` subcommand remains for fzf integration. (#5)
- Picker header now reflects the active filter mode and scope. (#5)
- Sections and previews now read from the pre-built index with fallback to on-disk parsing. (#7)
- Doc viewer now renders markdown to ANSI (`glow` → `mdcat` → `bat`) and opens it in an interactive pager (`less -RFX`), instead of piping raw markdown into a pager. Package now depends on `glow` (rendering) and `less` (paging).
- Arch packaging now depends on `arch-wiki-lite`; `arch-wiki-docs` is optional for `wiki-search-html` instead of being required.
- Initial search queries now pre-rank candidates so exact title, heading, and command-path matches appear before weaker body matches, with newer manual pages first when relevance ties.
- Doc results now use compact page/section labels and cleaned, sentence-aware body synopses without repeated headings or Markdown noise.
- Reconciled the domain docs (`CONTEXT.md`, `docs/search-topics.md`) to the current Omarchy release (quattro/Quickshell): documented the Omarchy shell (`shell.json`, `omarchy bar`, `omarchy plugin`), the Quickshell menu, shell-based notifications/OSD, and the Foot terminal in place of the removed Waybar/Walker/Mako/SwayOSD stack; migrated command references to the `omarchy <group> <action>` model and corrected source paths to `/usr/share/omarchy`.

## [0.1.0] - 2026-08-18

### Added
- Fuzzy search over the full Omarchy manual for offline use. (#1)
- Live `omarchy` CLI command tree capture on systems where the CLI is installed. (#1)
- Unified fzf picker showing manual sections and commands in a single ranked list. (#1)
- Doc results rendered through glow/mdcat or less; commands printed to stdout with Ctrl-Y clipboard copy (Wayland). (#1)
- Interleaved doc/command candidate ordering for discoverability. (#2)
- Type tags (`[doc]`, `[cmd]`) in picker display for quick identification. (#2)
- `om-search update` command to pull the latest manual and re-index commands. (#1)
- Degraded mode: doc search works without the `omarchy` CLI installed. (#1)

### Changed
- Preview window renders through mdcat for coloured markdown when available. (#2)

### Fixed
- Encoding portability for cross-platform manual file reading. (#3)

### Infrastructure
- AUR PKGBUILD and pacman hook for automatic manual refresh after Omarchy system updates. (#3)
- PyPI package metadata, MIT license, classifiers, and project URLs. (#4)
- Development toolchain: pytest, mypy, uv build. (#1)

[Unreleased]: https://github.com/klarrimore/om-search/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/klarrimore/om-search/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/klarrimore/om-search/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/klarrimore/om-search/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/klarrimore/om-search/releases/tag/v0.1.0
