# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

### Fixed
- Interactive search query (`om-search <term>`) now filters the picker correctly instead of displaying all results — fzf `--nth 4,5` operated on the transformed (single-field) line, making the fields unreachable. (#8)
- Body-text matching now actually works: the picker presents and searches both the display field and the body excerpt via fzf `--with-nth 4,5`. Previously `--with-nth 4` limited both display and search to the title/heading, so words appearing only in a section body were unfindable. The excerpt is shown dimmed (ANSI) and stripped back off on selection.

### Changed
- CLI argument parsing… switched to flags (``--docs``, ``--pages``, etc.) instead of subparsers, following the Omarchy CLI convention.  The ``preview`` subcommand remains for fzf integration. (#5)
- Picker header now reflects the active filter mode and scope. (#5)
- Sections and previews now read from the pre-built index with fallback to on-disk parsing. (#7)
- Doc viewer now renders markdown to ANSI (`glow` → `mdcat` → `bat`) and opens it in an interactive pager (`less -RFX`), instead of piping raw markdown into a pager. Package now depends on `glow` (rendering) and `less` (paging).

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

[Unreleased]: https://github.com/klarrimore/om-search/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/klarrimore/om-search/releases/tag/v0.1.0