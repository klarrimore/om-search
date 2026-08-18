# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.1.0]: https://github.com/klarrimore/om-search/releases/tag/v0.1.0