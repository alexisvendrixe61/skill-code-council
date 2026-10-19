#!/usr/bin/env bash
# Phase 5 helper: creates the isolated council branch and worktree.
# review/solve: bash make_worktree.sh <review|solve> <TS> <base-sha>     (run inside the repo)
# build:        bash make_worktree.sh build <TS> <new-project-dir>
# Prints WT=<abs path> and BRANCH=<name>. The original branch is never checked out or modified.
set -euo pipefail

MODE="$1"; TS="$2"; TARGET="$3"
BRANCH="council/$MODE-$TS"

if [ "$MODE" = "build" ]; then
  mkdir -p "$TARGET"; cd "$TARGET"
  [ -d .git ] || git init -q -b main
  git rev-parse HEAD >/dev/null 2>&1 || git commit -q --allow-empty -m "Initial empty commit"
  REPO=$(pwd); BASE=main
else
  REPO=$(git rev-parse --show-toplevel); BASE="$TARGET"
fi

WT="$(dirname "$REPO")/$(basename "$REPO")-council-$TS"
git -C "$REPO" worktree add -q -b "$BRANCH" "$WT" "$BASE"
bash "$(dirname "$0")/guard.sh" "$WT" >/dev/null

echo "WT=$WT"
echo "BRANCH=$BRANCH"
echo "BASE=$(git -C "$REPO" rev-parse "$BASE")"
