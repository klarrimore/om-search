#!/usr/bin/env bash
#
# Install (or update) the om-search entries in the Omarchy menu.
#
# The Quickshell Omarchy menu reads a single user extension file at
# ~/.config/omarchy/extensions/omarchy-menu.jsonc. This script merges the
# marker-delimited om-search block from the sibling omarchy-menu.jsonc into
# that file without disturbing your other customizations. It is idempotent:
# re-running replaces the managed block in place. Run with --uninstall to
# remove it. The menu hot-reloads on save, so changes apply immediately.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="$SCRIPT_DIR/omarchy-menu.jsonc"
TARGET="${XDG_CONFIG_HOME:-$HOME/.config}/omarchy/extensions/omarchy-menu.jsonc"
DEFAULT_TEMPLATE="/usr/share/omarchy/config/omarchy/extensions/omarchy-menu.jsonc"

BEGIN='// >>> om-search'
END='// <<< om-search'

uninstall=false
[[ "${1:-}" == "--uninstall" ]] && uninstall=true

if [[ ! -f "$SOURCE" ]]; then
  echo "error: cannot find $SOURCE" >&2
  exit 1
fi

mkdir -p "$(dirname "$TARGET")"

# Seed the target file if it does not exist yet.
if [[ ! -f "$TARGET" ]]; then
  if [[ -f "$DEFAULT_TEMPLATE" ]]; then
    cp "$DEFAULT_TEMPLATE" "$TARGET"
  else
    printf '{\n}\n' >"$TARGET"
  fi
fi

# Back up before touching anything.
backup="$TARGET.bak.$(date +%s)"
cp "$TARGET" "$backup"

# Strip any existing managed block (idempotency / uninstall).
stripped="$(awk -v b="$BEGIN" -v e="$END" '
  index($0, b) { skip = 1 }
  !skip        { print }
  index($0, e) { skip = 0 }
' "$TARGET")"

if $uninstall; then
  printf '%s\n' "$stripped" >"$TARGET"
  echo "Removed om-search menu block from $TARGET"
  echo "Backup: $backup"
  exit 0
fi

# Extract the managed block (inclusive of markers) from the source file.
block="$(awk -v b="$BEGIN" -v e="$END" '
  index($0, b) { grab = 1 }
  grab         { print }
  index($0, e) { grab = 0 }
' "$SOURCE")"

if [[ -z "$block" ]]; then
  echo "error: no om-search marker block found in $SOURCE" >&2
  exit 1
fi

# Re-insert the block immediately after the opening brace of the target.
# Every managed entry ends with a comma, so it is valid wherever it lands.
printf '%s\n' "$stripped" | awk -v block="$block" '
  !done && /^[[:space:]]*\{/ { print; print block; done = 1; next }
  { print }
  END { if (!done) exit 2 }
' >"$TARGET" || {
  echo "error: could not find an opening { in $TARGET; restoring backup" >&2
  cp "$backup" "$TARGET"
  exit 1
}

echo "Installed om-search entries into $TARGET"
echo "Backup: $backup"
echo "Open the menu with Super+Space -> Manual (it hot-reloads on save)."
