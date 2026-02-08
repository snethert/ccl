#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUTPUT="$ROOT_DIR/doc/wasm/wasm-ui-modules.json"
DRYRUN=0

usage() {
  cat <<'USAGE'
Usage: scripts/wasm/compile-ui-modules.sh [options]

Options:
  --output PATH   Write bundle to PATH (default: doc/wasm/wasm-ui-modules.json)
  --dry-run       Print commands without executing
  -h, --help      Show this help
USAGE
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

CCL_BIN=""
if command -v ccl >/dev/null 2>&1; then
  CCL_BIN="ccl"
elif [ -x "$ROOT_DIR/dx86cl64" ]; then
  CCL_BIN="$ROOT_DIR/dx86cl64"
fi

if [ -z "$CCL_BIN" ]; then
  echo "error: ccl not found in PATH and dx86cl64 missing; install CCL to build UI modules" >&2
  exit 1
fi

SCRIPT="$ROOT_DIR/scripts/wasm/compile-ui-modules.lisp"
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
run "$CCL_BIN" --no-init --batch -l "$SCRIPT" -- --output "$INLINE_TMP"
run node "$PACK_SCRIPT" --manifest "$INLINE_TMP" --out-manifest "$OUTPUT"

if [ "$DRYRUN" -eq 0 ]; then
  rm -f "$INLINE_TMP"
fi
