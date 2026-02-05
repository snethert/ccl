#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

INSTALL=0
BUILD=1
SUBPRIMS=0
SMOKE=0
CLEAN=1
DRYRUN=0
PRINT_ENV=0

usage() {
  cat <<'EOF'
Usage: scripts/wasm/linux-setup.sh [options]

Options:
  --install     Install packages via apt-get
  --no-build    Skip build steps
  --subprims    Build subprims provider module
  --smoke       Run node smoke tests (doc/wasm/js/all-smoke.mjs)
  --no-clean    Skip clean step before build
  --print-env   Print export lines and exit
  --dry-run     Print commands without executing
  -h, --help    Show this help

Examples:
  scripts/wasm/linux-setup.sh --install
  scripts/wasm/linux-setup.sh --subprims --smoke
  scripts/wasm/linux-setup.sh --print-env
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

need_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "error: missing command: $cmd" >&2
    return 1
  fi
  return 0
}

while [ "${1:-}" != "" ]; do
  case "$1" in
    --install) INSTALL=1 ;;
    --no-build) BUILD=0 ;;
    --subprims) SUBPRIMS=1 ;;
    --smoke) SMOKE=1 ;;
    --no-clean) CLEAN=0 ;;
    --print-env) PRINT_ENV=1 ;;
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

if ! need_cmd apt-get; then
  echo "error: apt-get not found. This script targets Debian/Ubuntu." >&2
  exit 1
fi

sudo_cmd=()
if [ "$(id -u)" -ne 0 ]; then
  if need_cmd sudo; then
    sudo_cmd=(sudo)
  else
    echo "error: sudo not found; run as root for --install." >&2
    if [ "$INSTALL" -eq 1 ]; then
      exit 1
    fi
  fi
fi

if [ "$INSTALL" -eq 1 ]; then
  run "${sudo_cmd[@]}" apt-get update
  run "${sudo_cmd[@]}" apt-get install -y \
    clang-18 lld-18 wasi-libc wabt binaryen nodejs python3
fi

if [ ! -d /usr/include/wasm32-wasi ]; then
  echo "error: /usr/include/wasm32-wasi not found (wasi-libc headers missing)" >&2
  exit 1
fi

CC="clang-18"
WASM_LD="wasm-ld-18"

if ! command -v "$CC" >/dev/null 2>&1; then
  echo "error: $CC not found. Install clang-18 or adjust CC." >&2
  exit 1
fi
if ! command -v "$WASM_LD" >/dev/null 2>&1; then
  echo "error: $WASM_LD not found. Install lld-18 or adjust WASM_LD." >&2
  exit 1
fi

if [ "$PRINT_ENV" -eq 1 ]; then
  cat <<EOF
export CC="$CC"
export WASM_LD="$WASM_LD"
export WASM_TARGET="wasm32-wasi"
EOF
  exit 0
fi

MAKE_ARGS=("WASM_TARGET=wasm32-wasi" "CC=$CC" "WASM_LD=$WASM_LD")

if [ "$BUILD" -eq 1 ]; then
  if [ "$CLEAN" -eq 1 ]; then
    run make -C "$ROOT_DIR/lisp-kernel/wasm32" "${MAKE_ARGS[@]}" clean
  fi
  run make -C "$ROOT_DIR/lisp-kernel/wasm32" "${MAKE_ARGS[@]}"
fi

if [ "$SUBPRIMS" -eq 1 ]; then
  if [ "$CLEAN" -eq 1 ]; then
    run make -C "$ROOT_DIR/lisp-kernel/wasm32/subprims" "${MAKE_ARGS[@]}" clean
  fi
  run make -C "$ROOT_DIR/lisp-kernel/wasm32/subprims" "${MAKE_ARGS[@]}"
fi

if [ "$SMOKE" -eq 1 ]; then
  node_cmd=""
  if command -v node >/dev/null 2>&1; then
    node_cmd="node"
  elif command -v nodejs >/dev/null 2>&1; then
    node_cmd="nodejs"
  else
    echo "error: node not found (install nodejs)" >&2
    exit 1
  fi
  SMOKE_MODULES="$ROOT_DIR/doc/wasm/wasm-smoke-modules.json"
  if command -v ccl >/dev/null 2>&1; then
    run "$ROOT_DIR/scripts/wasm/compile-smoke-modules.sh" --output "$SMOKE_MODULES"
  elif [ ! -f "$SMOKE_MODULES" ]; then
    echo "error: ccl not found and $SMOKE_MODULES is missing. Install CCL or generate the bundle." >&2
    exit 1
  fi
  run "$node_cmd" "$ROOT_DIR/doc/wasm/js/all-smoke.mjs"
fi
