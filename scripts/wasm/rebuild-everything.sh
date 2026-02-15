#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Source environment setup to get build directories
if [ -f "$ROOT_DIR/scripts/wasm/env.sh" ]; then
  # shellcheck source=/dev/null
  . "$ROOT_DIR/scripts/wasm/env.sh" >/dev/null 2>&1 || true
fi

FORCE=1
BUILD_ROOT_IMAGE=1
ROOT_IMAGE_ALLOW_FAIL=1

# Use environment variables for build paths with fallbacks
BUILD_DIR="${CCL_WASM_BUILD_DIR:-$ROOT_DIR/build/wasm32}"
IMAGES_DIR="${CCL_WASM_IMAGES_DIR:-$BUILD_DIR/images}"
MODULES_DIR="${CCL_WASM_MODULES_DIR:-$BUILD_DIR/modules}"

ROOT_IMAGE_OUT="${ROOT_IMAGE_OUT:-$IMAGES_DIR/root.image}"
ROOT_IMAGE_MANIFEST_OUT="${ROOT_IMAGE_MANIFEST_OUT:-$IMAGES_DIR/root.image.manifest.json}"
ROOT_IMAGE_RESOLUTION_OUT="${ROOT_IMAGE_RESOLUTION_OUT:-$MODULES_DIR/startup-symbol-resolution.source_scope_v1.json}"
MODULES_OUT="${MODULES_OUT:-$MODULES_DIR/wasm-runtime-modules.json}"
CONTRACT_OUT="${CONTRACT_OUT:-$MODULES_DIR/bootstrap-l0-contract.v1.json}"
SCOPE_OUT="${SCOPE_OUT:-$MODULES_DIR/startup-symbol-scope.source_scope_v1.json}"

usage() {
  cat <<'EOF'
Usage: scripts/wasm/rebuild-everything.sh [options]

Rebuild canonical WASM artifacts in dependency order so outputs stay in sync.

Default steps:
  1) lisp-kernel/wasm32 -> build/wasm32/kernel/wasmcl.wasm
  2) wasm-boot.image rebuild
  3) WASM fasls/modules + contract + startup symbol scope
  4) root.image rebuild (allowed to fail by default)

Environment variables:
  CCL_WASM_BUILD_DIR        Build output directory (default: build/wasm32)
  CCL_WASM_IMAGES_DIR       Image files directory (default: $BUILD_DIR/images)
  CCL_WASM_MODULES_DIR      Module files directory (default: $BUILD_DIR/modules)

Options:
  --no-force                Do incremental builds where supported
  --no-root-image           Skip root.image rebuild
  --strict-root-image       Treat root.image failure as fatal
  --root-image PATH         root.image output path
  --manifest-out PATH       root.image manifest output path
  --resolution-out PATH     startup symbol resolution output path
  --modules-out PATH        runtime modules manifest output path
  -h, --help                Show this help
EOF
}

resolve_path() {
  local value="$1"
  if [[ "$value" = /* ]]; then
    printf '%s\n' "$value"
  else
    printf '%s\n' "$ROOT_DIR/$value"
  fi
}

log() {
  printf '[rebuild-everything] %s\n' "$*"
}

run() {
  log "RUN: $*"
  "$@"
}

while [ "${1:-}" != "" ]; do
  case "$1" in
    --no-force)
      FORCE=0
      ;;
    --no-root-image)
      BUILD_ROOT_IMAGE=0
      ;;
    --strict-root-image)
      ROOT_IMAGE_ALLOW_FAIL=0
      ;;
    --root-image)
      if [ -z "${2:-}" ]; then
        echo "error: --root-image requires a path" >&2
        exit 1
      fi
      ROOT_IMAGE_OUT="$(resolve_path "$2")"
      shift
      ;;
    --manifest-out)
      if [ -z "${2:-}" ]; then
        echo "error: --manifest-out requires a path" >&2
        exit 1
      fi
      ROOT_IMAGE_MANIFEST_OUT="$(resolve_path "$2")"
      shift
      ;;
    --resolution-out)
      if [ -z "${2:-}" ]; then
        echo "error: --resolution-out requires a path" >&2
        exit 1
      fi
      ROOT_IMAGE_RESOLUTION_OUT="$(resolve_path "$2")"
      shift
      ;;
    --modules-out)
      if [ -z "${2:-}" ]; then
        echo "error: --modules-out requires a path" >&2
        exit 1
      fi
      MODULES_OUT="$(resolve_path "$2")"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
  shift
done

if ! command -v node >/dev/null 2>&1; then
  echo "error: node is required" >&2
  exit 1
fi
if ! command -v make >/dev/null 2>&1; then
  echo "error: make is required" >&2
  exit 1
fi
if ! command -v git >/dev/null 2>&1; then
  echo "error: git is required" >&2
  exit 1
fi

# Create build directories
mkdir -p "$BUILD_DIR" "$IMAGES_DIR" "$MODULES_DIR"

MAKE_ARGS=()
if [ -n "${CC:-}" ]; then
  MAKE_ARGS+=("CC=$CC")
fi
if [ -n "${WASM_LD:-}" ]; then
  MAKE_ARGS+=("WASM_LD=$WASM_LD")
fi

COMPILE_ARGS=()
if [ "$FORCE" -eq 1 ]; then
  COMPILE_ARGS+=(--force)
fi
COMPILE_ARGS+=(--modules-out "$MODULES_OUT")

BOOT_ARGS=()
if [ "$FORCE" -eq 1 ]; then
  BOOT_ARGS+=(--force)
fi

log "repo=$ROOT_DIR"
log "branch=$(git -C "$ROOT_DIR" symbolic-ref --short -q HEAD || echo detached) head=$(git -C "$ROOT_DIR" rev-parse --short HEAD)"
log "force=$FORCE build_root_image=$BUILD_ROOT_IMAGE root_image_allow_fail=$ROOT_IMAGE_ALLOW_FAIL"

run make -C "$ROOT_DIR/lisp-kernel/wasm32" "${MAKE_ARGS[@]}" all
run "$ROOT_DIR/scripts/wasm/build-wasm-boot.sh" "${BOOT_ARGS[@]}"
run "$ROOT_DIR/scripts/wasm/compile-wasm-fasls.sh" "${COMPILE_ARGS[@]}"

if [ "$BUILD_ROOT_IMAGE" -eq 1 ]; then
  ROOT_CMD=(
    node "$ROOT_DIR/doc/wasm/js/make-real-image.mjs"
    --output "$ROOT_IMAGE_OUT"
    --manifest-out "$ROOT_IMAGE_MANIFEST_OUT"
    --modules "$MODULES_OUT"
    --startup-symbol-scope "$SCOPE_OUT"
    --startup-symbol-resolution-out "$ROOT_IMAGE_RESOLUTION_OUT"
    --startup-symbol-contract "$CONTRACT_OUT"
  )
  if [ "$ROOT_IMAGE_ALLOW_FAIL" -eq 1 ]; then
    log "RUN (root image, non-fatal): ${ROOT_CMD[*]}"
    "${ROOT_CMD[@]}" || log "WARN: root.image rebuild failed (allowed); inspect logs/output paths"
  else
    run "${ROOT_CMD[@]}"
  fi
fi

log "sync rebuild complete. key outputs:"
log "  ${CCL_WASM_KERNEL_DIR:-$BUILD_DIR/kernel}/wasmcl.wasm"
log "  wasm-boot.image"
log "  ${MODULES_OUT#$ROOT_DIR/}"
log "  ${CONTRACT_OUT#$ROOT_DIR/}"
log "  ${SCOPE_OUT#$ROOT_DIR/}"
if [ "$BUILD_ROOT_IMAGE" -eq 1 ]; then
  log "  ${ROOT_IMAGE_OUT#$ROOT_DIR/}"
  log "  ${ROOT_IMAGE_MANIFEST_OUT#$ROOT_DIR/}"
  log "  ${ROOT_IMAGE_RESOLUTION_OUT#$ROOT_DIR/}"
fi

log ""
log "Build artifacts location: ${BUILD_DIR#$ROOT_DIR/}"

log "git status (short):"
git -C "$ROOT_DIR" status --short
