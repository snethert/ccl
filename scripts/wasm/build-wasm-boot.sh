#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DRYRUN=0
FORCE=0

usage() {
  cat <<'EOF'
Usage: scripts/wasm/build-wasm-boot.sh [options]

Options:
  --force        Recompile even if level-0 fasls are up to date
  --dry-run      Print commands without executing
  -h, --help     Show this help
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
    --force) FORCE=1 ;;
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

if [ -n "${CCL_BIN:-}" ]; then
  if [ ! -x "$CCL_BIN" ] && ! command -v "$CCL_BIN" >/dev/null 2>&1; then
    echo "error: CCL_BIN is set but not executable: $CCL_BIN" >&2
    exit 1
  fi
else
  CCL_BIN="$ROOT_DIR/dx86cl64"
  if [ ! -x "$CCL_BIN" ]; then
    if command -v ccl >/dev/null 2>&1; then
      CCL_BIN="ccl"
    else
      echo "error: ccl not found in PATH and $ROOT_DIR/dx86cl64 is missing" >&2
      exit 1
    fi
  fi
fi

SCRIPT="$ROOT_DIR/scripts/wasm/build-wasm-boot.lisp"
if [ ! -f "$SCRIPT" ]; then
  echo "error: missing $SCRIPT" >&2
  exit 1
fi

if [ "$FORCE" -eq 1 ]; then
  run "$CCL_BIN" --no-init --batch -l "$SCRIPT" -- --force
else
  run "$CCL_BIN" --no-init --batch -l "$SCRIPT"
fi
