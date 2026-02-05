#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_SH="$ROOT_DIR/scripts/wasm/env.sh"

INSTALL=0
INSTALL_RUNTIMES=0
BUILD=1
SUBPRIMS=0
SMOKE=0
CLEAN=1
DRYRUN=0
PRINT_ENV=0

usage() {
  cat <<'EOF'
Usage: scripts/wasm/macos-setup.sh [options]

Options:
  --install           Install core packages via Homebrew
  --install-runtimes  Install optional wasi-runtimes via Homebrew
  --no-build          Skip build steps
  --subprims          Build subprims provider module
  --smoke             Run node smoke tests (doc/wasm/js/all-smoke.mjs)
  --no-clean          Skip clean step before build
  --print-env         Print export lines and exit
  --dry-run           Print commands without executing
  -h, --help          Show this help

Examples:
  scripts/wasm/macos-setup.sh --install
  scripts/wasm/macos-setup.sh --subprims --smoke
  scripts/wasm/macos-setup.sh --print-env
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
    --install-runtimes) INSTALL_RUNTIMES=1 ;;
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

if ! need_cmd brew; then
  echo "error: Homebrew is required on macOS (https://brew.sh)" >&2
  exit 1
fi

if [ "$INSTALL" -eq 1 ]; then
  run brew install llvm lld wasi-libc wabt binaryen node python
fi

if [ "$INSTALL_RUNTIMES" -eq 1 ]; then
  run brew install wasi-runtimes
fi

if [ -f "$ENV_SH" ]; then
  # shellcheck source=/dev/null
  source "$ENV_SH" || true
fi

if [ -z "${CC:-}" ] || [ -z "${WASM_LD:-}" ]; then
  LLVM_ROOT="$(brew --prefix llvm 2>/dev/null || true)"
  if [ -z "$LLVM_ROOT" ] || [ ! -d "$LLVM_ROOT" ]; then
    LLVM_ROOT="$(brew --prefix llvm@18 2>/dev/null || true)"
  fi
  if [ -z "$LLVM_ROOT" ] || [ ! -d "$LLVM_ROOT" ]; then
    echo "error: llvm not found. Run with --install." >&2
    exit 1
  fi

  LLD_ROOT="$(brew --prefix lld 2>/dev/null || true)"
  if [ -z "$LLD_ROOT" ] || [ ! -d "$LLD_ROOT" ]; then
    LLD_ROOT="$LLVM_ROOT"
  fi

  WASI_PREFIX="$(brew --prefix wasi-libc 2>/dev/null || true)"
  if [ -z "$WASI_PREFIX" ] || [ ! -d "$WASI_PREFIX" ]; then
    echo "error: wasi-libc not found. Run with --install." >&2
    exit 1
  fi

  WASI_SYSROOT=""
  if [ -d "$WASI_PREFIX/share/wasi-sysroot" ]; then
    WASI_SYSROOT="$WASI_PREFIX/share/wasi-sysroot"
  elif [ -d "$WASI_PREFIX/wasi-sysroot" ]; then
    WASI_SYSROOT="$WASI_PREFIX/wasi-sysroot"
  elif [ -d "$WASI_PREFIX/include/wasm32-wasi" ]; then
    WASI_SYSROOT="$WASI_PREFIX"
  fi

  if [ -z "$WASI_SYSROOT" ]; then
    echo "error: could not locate WASI sysroot or headers under $WASI_PREFIX" >&2
    exit 1
  fi

  WASI_INCLUDE="$WASI_SYSROOT/include/wasm32-wasi"
  if [ ! -d "$WASI_INCLUDE" ]; then
    echo "error: could not locate WASI headers under $WASI_SYSROOT" >&2
    exit 1
  fi

  export PATH="$LLVM_ROOT/bin:$PATH"

  CC_CMD="$LLVM_ROOT/bin/clang"
  WASM_LD="$LLD_ROOT/bin/wasm-ld"
  if [ ! -x "$WASM_LD" ] && [ -x "$LLVM_ROOT/bin/wasm-ld" ]; then
    WASM_LD="$LLVM_ROOT/bin/wasm-ld"
  fi

  if [ ! -x "$CC_CMD" ]; then
    echo "error: clang not found at $CC_CMD" >&2
    exit 1
  fi
  if [ ! -x "$WASM_LD" ]; then
    echo "error: wasm-ld not found at $WASM_LD" >&2
    exit 1
  fi

  CC="$CC_CMD -D__wasi__ -isystem $WASI_INCLUDE"
fi

if [ "$PRINT_ENV" -eq 1 ]; then
  cat <<EOF
export CC='$CC'
export WASM_LD="$WASM_LD"
EOF
  exit 0
fi

WASM_TARGET="${WASM_TARGET:-wasm32-unknown-unknown}"
MAKE_ARGS=("WASM_TARGET=$WASM_TARGET" "CC=$CC" "WASM_LD=$WASM_LD")

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
  if ! need_cmd node; then
    echo "error: node is required for --smoke (brew install node)" >&2
    exit 1
  fi
  SMOKE_MODULES="$ROOT_DIR/doc/wasm/wasm-smoke-modules.json"
  if command -v ccl >/dev/null 2>&1; then
    run "$ROOT_DIR/scripts/wasm/compile-smoke-modules.sh" --output "$SMOKE_MODULES"
  elif [ ! -f "$SMOKE_MODULES" ]; then
    echo "error: ccl not found and $SMOKE_MODULES is missing. Install CCL or generate the bundle." >&2
    exit 1
  fi
  run node "$ROOT_DIR/doc/wasm/js/all-smoke.mjs"
fi
