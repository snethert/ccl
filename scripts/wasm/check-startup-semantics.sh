#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STARTUP_FILE="lisp-kernel/wasm-kernel-stubs.c"

usage() {
  cat <<'USAGE'
Usage: scripts/wasm/check-startup-semantics.sh [BASE [HEAD]]

Checks startup semantic guardrails:
- No forbidden startup bypass patterns added to lisp-kernel/wasm-kernel-stubs.c
- No level-0/level-1 changes in the inspected diff

Diff selection:
- No args: staged + unstaged changes vs HEAD
- BASE:    BASE..HEAD
- BASE HEAD: BASE..HEAD
USAGE
}

if [ "$#" -gt 2 ]; then
  usage >&2
  exit 2
fi

if ! git -C "$ROOT_DIR" rev-parse --git-dir >/dev/null 2>&1; then
  echo "error: $ROOT_DIR is not a git repository" >&2
  exit 2
fi

DIFF_STARTUP=""
CHANGED_LEVEL=""

if [ "$#" -eq 0 ]; then
  DIFF_STARTUP+="$(git -C "$ROOT_DIR" diff --no-color --unified=0 HEAD -- "$STARTUP_FILE")"
  DIFF_STARTUP+=$'\n'
  DIFF_STARTUP+="$(git -C "$ROOT_DIR" diff --cached --no-color --unified=0 HEAD -- "$STARTUP_FILE")"

  CHANGED_LEVEL="$({
    git -C "$ROOT_DIR" diff --name-only HEAD -- level-0 level-1
    git -C "$ROOT_DIR" diff --cached --name-only HEAD -- level-0 level-1
  } | sort -u)"
else
  BASE="$1"
  HEAD_REF="${2:-HEAD}"
  RANGE="${BASE}..${HEAD_REF}"

  DIFF_STARTUP="$(git -C "$ROOT_DIR" diff --no-color --unified=0 "$RANGE" -- "$STARTUP_FILE")"
  CHANGED_LEVEL="$(git -C "$ROOT_DIR" diff --name-only "$RANGE" -- level-0 level-1 | sort -u)"
fi

ADDED_STARTUP="$(printf '%s\n' "$DIFF_STARTUP" | rg '^\+[^+]' || true)"
FORBIDDEN_REGEX='(%intern|%findsym|wasm_const_pool_make_symbol|wasm_const_pool_ensure_package|wasm_const_pool_register_package|wasm_find_symbol_named_bytes_scan\(|creating symbol fallback|creating package fallback|nrs_KEYWORD_PACKAGE\.vcell\s*=|WASM_LOAD_ENTRY_INDEX|make_header\(subtag_function, 2\))'

VIOLATIONS="$(printf '%s\n' "$ADDED_STARTUP" | rg -n -i "$FORBIDDEN_REGEX" || true)"

FAILED=0
if [ -n "$VIOLATIONS" ]; then
  FAILED=1
  echo "FAIL: forbidden startup bypass patterns detected in added lines of $STARTUP_FILE" >&2
  echo "$VIOLATIONS" >&2
fi

if [ -n "$CHANGED_LEVEL" ]; then
  FAILED=1
  echo "FAIL: level-0/level-1 changes detected (startup debug work must not touch Lisp semantic layers)" >&2
  echo "$CHANGED_LEVEL" >&2
fi

if [ "$FAILED" -ne 0 ]; then
  exit 1
fi

echo "PASS: startup semantics guardrails satisfied"
