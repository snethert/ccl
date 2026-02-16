#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MODULES_DIR="${CCL_WASM_MODULES_DIR:-$ROOT_DIR/build/wasm32/modules}"
mkdir -p "$MODULES_DIR"
OUTPUT="$MODULES_DIR/wasm-phase0a-tests.json"
DRYRUN=0

usage() {
  cat <<'EOF'
Usage: scripts/wasm/compile-phase0a-tests.sh [options]

Compiles Phase 0A WASM LAP bridge unit tests into a module bundle.

Options:
  --output PATH   Write bundle to PATH (default: build/wasm32/modules/wasm-phase0a-tests.json)
  --dry-run       Print commands without executing
  -h, --help      Show this help
EOF
}

run() {
  if [ "$DRYRUN" -eq 1 ]; then
    printf '+ %q' "$@"
    printf '\n'
  else
    "$@"
  fi
}

while [ "${1:-}" != "" ]; do
  case "$1" in
    --output)
      shift
      OUTPUT="${1:-}"
      if [ -z "$OUTPUT" ]; then
        echo "error: --output requires a path" >&2
        exit 1
      fi
      ;;
    --dry-run) DRYRUN=1 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "error: unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
  shift
done

if ! command -v ccl >/dev/null 2>&1; then
  echo "error: ccl not found in PATH (install CCL to compile Phase 0A tests)" >&2
  exit 1
fi

SCRIPT="$ROOT_DIR/scripts/wasm/compile-phase0a-tests.lisp"
if [ ! -f "$SCRIPT" ]; then
  echo "error: missing $SCRIPT" >&2
  exit 1
fi

PACK_SCRIPT="$ROOT_DIR/scripts/wasm/pack-inline-bundle-v2.mjs"
if [ ! -f "$PACK_SCRIPT" ]; then
  echo "error: missing $PACK_SCRIPT" >&2
  exit 1
fi

INLINE_TMP="${OUTPUT}.inline-v1.tmp.json"
run ccl --no-init --batch -l "$SCRIPT" -- --output "$INLINE_TMP"
run node "$PACK_SCRIPT" --manifest "$INLINE_TMP" --out-manifest "$OUTPUT"

if [ "$DRYRUN" -eq 0 ]; then
  rm -f "$INLINE_TMP"
  echo "Phase 0A test bundle written to $OUTPUT"
fi
