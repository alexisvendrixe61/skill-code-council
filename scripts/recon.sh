#!/usr/bin/env bash
# Phase 0 helper: creates the council output folder and gathers objective signals.
# Usage: bash recon.sh <review|solve|build> [scope paths...]
# Run it from the repo root, or from the parent folder of a new project in build mode.
# Prints OUT=<abs path> and TS=<timestamp>. Use those literal values later,
# because shell variables do not survive between separate commands.
set -u

MODE="${1:?mode required: review|solve|build}"; shift
SCOPE=("${@:-.}")
TS=$(date +%Y%m%d-%H%M%S)
EXCLUDES=(-x "*/node_modules/*" -x "*/.venv/*" -x "*/venv/*" -x "*/.council/*" -x "*/dist/*" -x "*/build/*")

in_git_repo() { git rev-parse --git-dir >/dev/null 2>&1; }

ensure_tool() {  # ensure_tool <command> <pip package>
  command -v "$1" >/dev/null 2>&1 && return 0
  pip install -q --break-system-packages "$2" >/dev/null 2>&1 || pip install -q --user "$2" >/dev/null 2>&1
  command -v "$1" >/dev/null 2>&1
}

detect_test_cmd() {
  if [ -f pyproject.toml ] || [ -f pytest.ini ] || [ -f setup.cfg ] || [ -d tests ]; then
    find . -name '*.py' -not -path './.council/*' -not -path './.venv/*' | grep -q . \
      && { echo "python3 -m pytest -q"; return; }
  fi
  [ -f package.json ] && grep -q '"test"' package.json && { echo "npm test --silent"; return; }
  [ -f go.mod ] && { echo "go test ./..."; return; }
  [ -f Cargo.toml ] && { echo "cargo test -q"; return; }
  echo ""
}

section() { printf '\n## %s\n\n```\n' "$1"; }
endsection() { printf '```\n'; }

ROOT=$( (in_git_repo && git rev-parse --show-toplevel) || pwd)
OUT="$ROOT/.council/$TS"
mkdir -p "$OUT"
SIG="$OUT/signals.md"
echo "# Objective signals ($TS)" > "$SIG"

BRANCH="(no git)"; SHA="(no git)"; DIRTY="n/a"
if in_git_repo; then
  EXCL="$(git rev-parse --git-common-dir)/info/exclude"
  mkdir -p "$(dirname "$EXCL")"; grep -qxF '.council/' "$EXCL" 2>/dev/null || echo '.council/' >> "$EXCL"
  BRANCH=$(git rev-parse --abbrev-ref HEAD); SHA=$(git rev-parse HEAD)
  DIRTY=$(git status --porcelain --untracked-files=no | wc -l | tr -d ' ')
  { section "Git"; echo "branch: $BRANCH"; echo "sha: $SHA"; echo "modified tracked files: $DIRTY"
    git status --short --untracked-files=no | head -20; endsection; } >> "$SIG"
  { section "Files per extension (tracked)"
    git ls-files | sed -n 's/.*\.\([A-Za-z0-9]*\)$/\1/p' | sort | uniq -c | sort -rn | head -15; endsection; } >> "$SIG"
fi

TEST_SUMMARY="no tests found"
if [ "$MODE" != "build" ]; then
  TEST_CMD=$(detect_test_cmd)
  if [ -n "$TEST_CMD" ]; then
    TEST_OUT=$(timeout 300 bash -c "$TEST_CMD" 2>&1); TEST_RC=$?
    TEST_SUMMARY="$TEST_CMD -> exit $TEST_RC: $(echo "$TEST_OUT" | grep -E 'passed|failed|error|ok|FAIL' | tail -1)"
    { section "Tests: $TEST_CMD (exit $TEST_RC)"; echo "$TEST_OUT" | tail -30; endsection; } >> "$SIG"
  fi

  LIZARD_COUNT="n/a"
  if ensure_tool lizard lizard; then
    LIZ=$(timeout 300 lizard -w -L 30 -C 10 -a 4 "${EXCLUDES[@]}" "${SCOPE[@]}" 2>/dev/null)
    LIZARD_COUNT=$(echo "$LIZ" | grep -c 'warning:' || true)
    { section "Functions over limits (lizard: >30 lines, CCN >10, >4 params): $LIZARD_COUNT"
      echo "$LIZ" | head -40; endsection; } >> "$SIG"
  fi

  if ls "${SCOPE[@]}" 2>/dev/null | grep -q . && find "${SCOPE[@]}" -name '*.py' -not -path '*/.council/*' | grep -q .; then
    if ensure_tool ruff ruff; then
      RULES=(--select E,F,B,SIM,UP,C90)  # sensible default when the repo has no ruff config
      { [ -f ruff.toml ] || [ -f .ruff.toml ] || grep -q '\[tool.ruff' pyproject.toml 2>/dev/null; } && RULES=()
      RUFF=$(timeout 120 ruff check --output-format concise --exclude .council "${RULES[@]}" "${SCOPE[@]}" 2>&1)
      { section "ruff ($(echo "$RUFF" | grep -cE ':[0-9]+:[0-9]+:' || true) issues)"; echo "$RUFF" | head -40; endsection; } >> "$SIG"
    fi
  fi
fi

python3 - "$OUT/meta.json" <<PY
import json, sys
json.dump({"ts": "$TS", "mode": "$MODE", "repo": "$(basename "$ROOT")", "root": "$ROOT",
           "branch": "$BRANCH", "sha": "$SHA", "uncommitted": "$DIRTY",
           "tests": """$TEST_SUMMARY""".strip(), "lizard_count": "${LIZARD_COUNT:-n/a}"},
          open(sys.argv[1], "w"), indent=2)
PY

echo "OUT=$OUT"
echo "TS=$TS"
echo "BRANCH=$BRANCH SHA=$SHA UNCOMMITTED=$DIRTY"
echo "Signals written to $SIG"
