# om-search — Omarchy menu plugin

Adds a **Manual** submenu to the Quickshell Omarchy menu (`Super+Space`) that
launches [`om-search`](../README.md) in its various modes:

| Row                     | Runs                                                       |
| ----------------------- | ---------------------------------------------------------- |
| Search Everything       | `om-search`                                                |
| Search Docs             | `om-search --docs`                                         |
| Search Commands         | `om-search --cmds`                                         |
| Browse Pages            | `om-search --pages`                                        |
| Browse Command Groups   | `om-search --groups`                                       |
| Update Manual           | `om-search --update` (in a floating presentation terminal) |

Interactive pickers open with `omarchy-launch-tui`; the non-interactive update
runs in a floating terminal with the Omarchy presentation wrapper. Every row is
gated on `command -v om-search`, so the submenu stays hidden on machines where
om-search is not installed.

## Why a menu entry (and not a bar widget)

The Omarchy menu reads exactly one user extension file,
`~/.config/omarchy/extensions/omarchy-menu.jsonc`, and hot-reloads it on save.
That makes a menu entry the lightest-weight, no-QML way to surface a terminal
tool like om-search. See the field reference in
[`omarchy-menu.jsonc`](omarchy-menu.jsonc).

## Install

```sh
./install.sh
```

The installer is idempotent and non-destructive:

1. Creates `~/.config/omarchy/extensions/` if needed (seeding the file from the
   Omarchy default template when there is none).
2. Backs up your current extension file to `omarchy-menu.jsonc.bak.<epoch>`.
3. Merges the marker-delimited om-search block into your file, **preserving any
   other menu customizations you already have**. Re-running replaces the block
   in place rather than duplicating it.

Remove it again with:

```sh
./install.sh --uninstall
```

### Manual install

If you have no other menu customizations, you can copy the file directly — it
is a complete, valid extension file on its own:

```sh
cp omarchy-menu.jsonc ~/.config/omarchy/extensions/omarchy-menu.jsonc
```

Otherwise, paste the block between the `>>> om-search` / `<<< om-search`
markers into your existing `~/.config/omarchy/extensions/omarchy-menu.jsonc`.

The menu hot-reloads on save; open it with `Super+Space` and pick **Manual**,
or jump straight in with `omarchy menu summon om-search`.

## Packaging note

To ship this with the AUR package, run `install.sh` as a per-user step (it
must write to the user's `~/.config`, not to system paths), or document the
one-liner above in the package's post-install message. Do not install it into
`/usr/share/omarchy/` — that tree is owned by the `omarchy` package and is
overwritten on update.
