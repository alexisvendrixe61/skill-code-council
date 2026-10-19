#!/usr/bin/env bash
# Refuses to continue unless the worktree is on a council/ branch.
# Usage: bash guard.sh <worktree path> && git -C <worktree path> commit ...
set -u
WT="${1:?worktree path required}"
CURRENT=$(git -C "$WT" branch --show-current 2>/dev/null)
case "$CURRENT" in
  council/*) echo "OK: $WT is on $CURRENT"; exit 0 ;;
  *) echo "STOP: $WT is on '${CURRENT:-unknown}', not a council/ branch. Refusing to write." >&2; exit 1 ;;
esac
