# Update the manual

## One-time update

```sh
om-search --update
```

This pulls the latest Omarchy manual from the `quattro` branch of the upstream
repository and rebuilds the search index and preview files.

## Automatic updates (AUR install)

When installed via the AUR package, a pacman hook at
`/usr/share/libalpm/hooks/om-search.hook` runs `om-search --update` after every
`omarchy` package upgrade. The hook is installed automatically by the AUR
package — no manual setup needed.

## What gets updated

- **Manual files**: cloned sparsely and shallowly into
  `~/.local/share/om-search/omarchy-repo/manual/`
- **Search index**: rebuilt into `~/.local/share/om-search/index.json`
- **Preview cache**: pre-rendered ANSI preview files regenerated for faster
  picker performance
- **Command tree**: re-queried from the installed `omarchy` CLI (not cached in
  the index — always live)