#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

STRICT=0
if [[ "${1:-}" == "--strict" ]]; then
  STRICT=1
fi

TARGETS=(
  "compiler/WASM"
  "lib/wasmenv.lisp"
  "lisp-kernel/platform-wasm32.h"
  "lisp-kernel/wasm-subprims-map.h"
  "doc/wasm/ABI.md"
)

# Retirement signals we still need to burn down in wasm-facing code.
PATTERN='(require "ARMENV"|require "ARM-ARCH"|arm::|arm-constants\.h|ARM sptab|sptab order|nargs=imm2|arg_z/arg_y/arg_x)'

echo "ARM retirement audit root: $ROOT_DIR"
echo "Scanning targets: ${TARGETS[*]}"
echo

if ! command -v rg >/dev/null 2>&1; then
  echo "error: rg is required" >&2
  exit 2
fi

HITS="$(rg -n --no-heading -e "$PATTERN" "${TARGETS[@]}" || true)"
COUNT=0
if [[ -n "$HITS" ]]; then
  COUNT="$(printf '%s\n' "$HITS" | wc -l | tr -d ' ')"
fi

echo "total_hits=$COUNT"

if [[ "$COUNT" -gt 0 ]]; then
  echo
  echo "Top hits (first 120):"
  printf '%s\n' "$HITS" | head -n 120
  echo
  echo "Per-file hit counts:"
  printf '%s\n' "$HITS" \
    | awk -F: '{counts[$1]++} END {for (k in counts) printf "%4d %s\n", counts[k], k}' \
    | sort -nr
fi

if [[ "$STRICT" -eq 1 && "$COUNT" -gt 0 ]]; then
  echo
  echo "strict mode failed: ARM-coupled markers remain"
  exit 1
fi

exit 0
