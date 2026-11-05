#!/usr/bin/env bash
set -euo pipefail
patch_root="$(cd "$(dirname "$0")" && pwd)"
checkout="${1:?Usage: ./ondevice/apply.sh /path/to/clean/pinned/StikDebug}"
base=395c4d5a0b5960536c22564f948049122383f3fb
test "$(git -C "$checkout" rev-parse HEAD)" = "$base" || { echo 'Wrong upstream revision.'; exit 1; }
test -z "$(git -C "$checkout" status --porcelain)" || { echo 'Checkout must be clean; existing changes were preserved.'; exit 1; }
git -C "$checkout" apply --check "$patch_root"/patches/*.patch
git -C "$checkout" apply "$patch_root"/patches/*.patch
echo 'Patches applied. Choose your free Personal Team locally in Xcode.'
