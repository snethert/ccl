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
MODULES_OUT="${MODULES_OUT:-$MODULES_DIR/wasm-runtime-modules.json}"
BOOT_MODULES_OUT="${BOOT_MODULES_OUT:-$MODULES_DIR/wasm-boot-modules.json}"

usage() {
  cat <<'EOF'
Usage: scripts/wasm/rebuild-everything.sh [options]

Rebuild canonical WASM artifacts in dependency order so outputs stay in sync.

Default steps:
  1) lisp-kernel/wasm32 -> build/wasm32/kernel/wasmcl.wasm
  2) wasm-boot.image rebuild
  3) WASM fasls/modules
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

log "Step 0: Generate ABI contract artifacts"
run python3 "$ROOT_DIR/scripts/wasm/generate_abi_contract.py" --build-dir "$BUILD_DIR"

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
BOOT_ARGS+=(--boot-modules-out "$BOOT_MODULES_OUT")

log "repo=$ROOT_DIR"
log "branch=$(git -C "$ROOT_DIR" symbolic-ref --short -q HEAD || echo detached) head=$(git -C "$ROOT_DIR" rev-parse --short HEAD)"
log "force=$FORCE build_root_image=$BUILD_ROOT_IMAGE root_image_allow_fail=$ROOT_IMAGE_ALLOW_FAIL"

run make -C "$ROOT_DIR/lisp-kernel/wasm32" ${MAKE_ARGS[@]+"${MAKE_ARGS[@]}"} all
run make -C "$ROOT_DIR/lisp-kernel/wasm32/subprims" clean all

# Phase 0B: Extract __heap_base from the kernel so the boot image can use it
# as :image-base-address, ensuring bias=0 (no relocation walk at load time).
# In wasm-ld, __heap_base == initial __stack_pointer (both set to memoryPtr
# after stack placement).  We read it from wasm-objdump and align to 64KiB
# (heap_segment_size), matching the kernel's ReserveMemoryForHeap() alignment.
KERNEL_WASM="${CCL_WASM_KERNEL_DIR:-$BUILD_DIR/kernel}/wasmcl.wasm"
if [ -f "$KERNEL_WASM" ] && command -v wasm-objdump >/dev/null 2>&1; then
  RAW_HEAP_BASE=$(wasm-objdump -x "$KERNEL_WASM" 2>/dev/null \
    | grep '__stack_pointer.*init' \
    | sed 's/.*init i32=//' \
    | tr -d '[:space:]')
  if [ -n "$RAW_HEAP_BASE" ] && [ "$RAW_HEAP_BASE" -gt 0 ] 2>/dev/null; then
    # Align up to 64KiB (heap_segment_size = 0x10000)
    ALIGNED_IMAGE_BASE=$(( ($RAW_HEAP_BASE + 0xFFFF) & ~0xFFFF ))
    CCL_WASM_IMAGE_BASE=$(printf '%x' $ALIGNED_IMAGE_BASE)
    export CCL_WASM_IMAGE_BASE
    log "heap_base=$RAW_HEAP_BASE image_base=0x$CCL_WASM_IMAGE_BASE ($(printf '%d' $ALIGNED_IMAGE_BASE))"
    echo "$CCL_WASM_IMAGE_BASE" > "$BUILD_DIR/.heap-base"
  else
    log "WARN: could not extract __heap_base from $KERNEL_WASM"
  fi
else
  log "WARN: kernel wasm or wasm-objdump not found; skipping image base extraction"
fi

run "$ROOT_DIR/scripts/wasm/build-wasm-boot.sh" ${BOOT_ARGS[@]+"${BOOT_ARGS[@]}"}

# Compute the start entry index for level-1 so it doesn't overlap boot functions.
# Use the next-entry-index sidecar file (written by build-wasm-boot.lisp) which
# captures *wasm2-next-entry-index* after all level-0 functions are compiled.
# This is the FUNCTION entry index counter, not just the module count.
# The Lisp script writes the sidecar next to its inline-v1 temp file
NEXT_ENTRY_INDEX_FILE="${BOOT_MODULES_OUT}.inline-v1.tmp.next-entry-index"
if [ -f "$NEXT_ENTRY_INDEX_FILE" ]; then
  BOOT_NEXT_INDEX=$(tr -d '[:space:]' < "$NEXT_ENTRY_INDEX_FILE")
  if [ -n "$BOOT_NEXT_INDEX" ] && [ "$BOOT_NEXT_INDEX" -gt 0 ] 2>/dev/null; then
    log "boot next-entry-index=$BOOT_NEXT_INDEX (from sidecar file)"
    COMPILE_ARGS+=(--start-entry-index "$BOOT_NEXT_INDEX")
  else
    log "WARN: could not read next-entry-index from $NEXT_ENTRY_INDEX_FILE"
  fi
elif [ -f "$BOOT_MODULES_OUT" ]; then
  # Fallback: use max module entry index from the bundle index
  BOOT_MAX_INDEX=$(node --input-type=module -e "
    import fs from 'fs';
    import { decodeModuleBundleIndexV2 } from '$ROOT_DIR/scripts/wasm/lib/module-bundle-v2.mjs';
    const idxPath = process.argv[1].replace(/\.json\$/, '.idx');
    const idxBytes = fs.readFileSync(idxPath);
    const decoded = decodeModuleBundleIndexV2(idxBytes);
    let maxIdx = 0;
    for (const m of decoded.modules) {
      if (m.entryIndex > maxIdx) maxIdx = m.entryIndex;
    }
    console.log(maxIdx);
  " "$BOOT_MODULES_OUT" 2>/dev/null || echo "")
  if [ -n "$BOOT_MAX_INDEX" ] && [ "$BOOT_MAX_INDEX" -gt 0 ] 2>/dev/null; then
    LEVEL1_START=$((BOOT_MAX_INDEX + 1))
    log "boot modules max entry index=$BOOT_MAX_INDEX, level-1 starts at $LEVEL1_START (fallback)"
    COMPILE_ARGS+=(--start-entry-index "$LEVEL1_START")
  else
    log "WARN: could not determine boot entry index range, using default"
  fi
fi

run "$ROOT_DIR/scripts/wasm/compile-wasm-fasls.sh" ${COMPILE_ARGS[@]+"${COMPILE_ARGS[@]}"}

# Phase 0A tests — recompile if the script exists
if [ -f "$ROOT_DIR/scripts/wasm/compile-phase0a-tests.sh" ]; then
  log "RUN (phase0a tests, non-fatal): scripts/wasm/compile-phase0a-tests.sh"
  "$ROOT_DIR/scripts/wasm/compile-phase0a-tests.sh" || log "WARN: phase0a test compilation failed (non-fatal)"
fi

# Phase 2C: Merge singleton modules to reduce instantiation count.
# Uses wasm-merge to combine individual-function modules into multi-export
# batches, reducing load-time instantiations from ~2600 to ~40.
if command -v wasm-merge >/dev/null 2>&1; then
  log "merging singleton modules (boot)..."
  run node "$ROOT_DIR/scripts/wasm/merge-singleton-modules.mjs" \
    --manifest "$BOOT_MODULES_OUT" --in-place --batch-size 100

  log "merging singleton modules (runtime)..."
  run node "$ROOT_DIR/scripts/wasm/merge-singleton-modules.mjs" \
    --manifest "$MODULES_OUT" --in-place --batch-size 100
else
  log "WARN: wasm-merge not found; skipping singleton module merge"
fi

if [ "$BUILD_ROOT_IMAGE" -eq 1 ]; then
  ROOT_CMD=(
    node --max-old-space-size=8192 "$ROOT_DIR/scripts/wasm/lib/make-real-image.mjs"
    --output "$ROOT_IMAGE_OUT"
    --manifest-out "$ROOT_IMAGE_MANIFEST_OUT"
    --modules "$MODULES_OUT"
    --boot-modules "$BOOT_MODULES_OUT"
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
log "  ${BOOT_MODULES_OUT#$ROOT_DIR/}"
if [ "$BUILD_ROOT_IMAGE" -eq 1 ]; then
  log "  ${ROOT_IMAGE_OUT#$ROOT_DIR/}"
  log "  ${ROOT_IMAGE_MANIFEST_OUT#$ROOT_DIR/}"
fi

log ""
log "Build artifacts location: ${BUILD_DIR#$ROOT_DIR/}"

log "git status (short):"
git -C "$ROOT_DIR" status --short

# Post-build freshness check
if [ -f "$ROOT_DIR/scripts/wasm/check-freshness.sh" ]; then
  log ""
  "$ROOT_DIR/scripts/wasm/check-freshness.sh" || true
fi
