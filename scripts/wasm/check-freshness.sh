#!/usr/bin/env bash
# check-freshness.sh — Detect stale WASM build artifacts
#
# Checks every artifact in the build pipeline against its source dependencies.
# Reports which artifacts are stale and what rebuild commands to run.
#
# Usage:
#   scripts/wasm/check-freshness.sh          # full report
#   scripts/wasm/check-freshness.sh --quiet  # exit code only (0=fresh, 1=stale)

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILD_DIR="${CCL_WASM_BUILD_DIR:-$ROOT_DIR/build/wasm32}"

# --- Artifact paths ---
KERNEL_WASM="$BUILD_DIR/kernel/wasmcl.wasm"
SUBPRIMS_WASM="$BUILD_DIR/subprims/subprims.wasm"
BOOT_IMAGE="$ROOT_DIR/wasm-boot.image"
BOOT_MODULES="$BUILD_DIR/modules/wasm-boot-modules.json"
RUNTIME_MODULES="$BUILD_DIR/modules/wasm-runtime-modules.json"
PHASE0A_TESTS="$BUILD_DIR/modules/wasm-phase0a-tests.json"
ROOT_IMAGE="$BUILD_DIR/images/root.image"

# --- Color codes (disabled if not a tty) ---
if [ -t 1 ]; then
  RED=$'\033[0;31m'
  GREEN=$'\033[0;32m'
  YELLOW=$'\033[0;33m'
  BOLD=$'\033[1m'
  RESET=$'\033[0m'
else
  RED='' GREEN='' YELLOW='' BOLD='' RESET=''
fi

# --- Helpers ---

# Get modification time as epoch seconds
mtime_epoch() {
  local f="$1"
  if [ ! -f "$f" ]; then
    echo "0"
    return
  fi
  # BSD stat (macOS)
  stat -f '%m' "$f" 2>/dev/null || stat -c '%Y' "$f" 2>/dev/null || echo "0"
}

# Get human-readable mtime
mtime_human() {
  local f="$1"
  if [ ! -f "$f" ]; then
    echo "MISSING"
    return
  fi
  stat -f '%Sm' -t '%Y-%m-%d %H:%M:%S' "$f" 2>/dev/null || \
    date -r "$(stat -c '%Y' "$f" 2>/dev/null)" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || \
    echo "unknown"
}

# Find the newest file matching any of the given patterns
# Outputs: epoch_seconds path
newest_among() {
  local newest_time=0
  local newest_file=""
  for f in "$@"; do
    if [ -f "$f" ]; then
      local t
      t=$(mtime_epoch "$f")
      if [ "$t" -gt "$newest_time" ]; then
        newest_time=$t
        newest_file=$f
      fi
    fi
  done
  echo "$newest_time"
  echo "$newest_file"
}

# Expand globs into file list
expand_sources() {
  for pattern in "$@"; do
    # Use compgen for safe glob expansion
    compgen -G "$pattern" 2>/dev/null || true
  done
}

# --- Rebuild command lookup (no associative arrays for bash 3.2) ---
rebuild_cmd_for() {
  case "$1" in
    kernel)          echo "make -C lisp-kernel/wasm32 clean all" ;;
    subprims)        echo "make -C lisp-kernel/wasm32/subprims clean all" ;;
    boot_image)      echo "scripts/wasm/build-wasm-boot.sh --force" ;;
    boot_modules)    echo "(rebuilt as part of boot image build)" ;;
    runtime_modules) echo "scripts/wasm/compile-wasm-fasls.sh --force" ;;
    phase0a_tests)   echo "scripts/wasm/compile-phase0a-tests.sh" ;;
    root_image)      echo "scripts/wasm/rebuild-everything.sh" ;;
    *)               echo "unknown" ;;
  esac
}

# --- Main logic ---

MODE="report"
case "${1:-}" in
  --quiet) MODE="quiet" ;;
  --help|-h)
    echo "Usage: $0 [--quiet]"
    echo ""
    echo "Check WASM build artifacts for staleness against source dependencies."
    echo ""
    echo "  (no args)  Full human-readable report"
    echo "  --quiet    Exit code only: 0=all fresh, 1=something stale"
    exit 0
    ;;
esac

ANY_STALE=0
STALE_NAMES=""

# check_one NAME LABEL ARTIFACT SOURCE_PATTERNS...
check_one() {
  local name="$1"
  local label="$2"
  local artifact="$3"
  shift 3

  local art_rel="${artifact#$ROOT_DIR/}"
  local art_time_h
  art_time_h=$(mtime_human "$artifact")

  if [ ! -f "$artifact" ]; then
    if [ "$MODE" = "report" ]; then
      printf "  ${RED}MISS${RESET}  %-22s %s\n" "$label" "$art_rel"
      printf "        ${YELLOW}fix: %s${RESET}\n" "$(rebuild_cmd_for "$name")"
    fi
    ANY_STALE=1
    STALE_NAMES="$STALE_NAMES $name"
    return
  fi

  local art_time
  art_time=$(mtime_epoch "$artifact")

  # Expand all source patterns and find the newest
  local sources
  sources=$(expand_sources "$@")

  local newest_time=0
  local newest_file=""
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    local t
    t=$(mtime_epoch "$f")
    if [ "$t" -gt "$newest_time" ]; then
      newest_time=$t
      newest_file=$f
    fi
  done <<< "$sources"

  if [ "$newest_time" -gt "$art_time" ]; then
    local stale_rel="${newest_file#$ROOT_DIR/}"
    if [ "$MODE" = "report" ]; then
      printf "  ${RED}STALE${RESET} %-22s %s  (%s)\n" "$label" "$art_rel" "$art_time_h"
      printf "        ${YELLOW}newer: %s${RESET}\n" "$stale_rel"
      printf "        ${YELLOW}fix:   %s${RESET}\n" "$(rebuild_cmd_for "$name")"
    fi
    ANY_STALE=1
    STALE_NAMES="$STALE_NAMES $name"
  else
    if [ "$MODE" = "report" ]; then
      printf "  ${GREEN}OK${RESET}    %-22s %s  (%s)\n" "$label" "$art_rel" "$art_time_h"
    fi
  fi
}

if [ "$MODE" = "report" ]; then
  echo ""
  printf "${BOLD}WASM Build Artifact Freshness Check${RESET}\n"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
fi

# 1. Kernel
check_one "kernel" "Kernel" "$KERNEL_WASM" \
  "$ROOT_DIR/lisp-kernel/*.c" \
  "$ROOT_DIR/lisp-kernel/*.h" \
  "$ROOT_DIR/lisp-kernel/wasm32/*.c" \
  "$ROOT_DIR/lisp-kernel/wasm32/Makefile"

# 2. Subprims
check_one "subprims" "Subprims" "$SUBPRIMS_WASM" \
  "$ROOT_DIR/lisp-kernel/wasm-subprims-provider.c" \
  "$ROOT_DIR/lisp-kernel/wasm-subprims.h" \
  "$ROOT_DIR/lisp-kernel/lisp-exceptions.h" \
  "$ROOT_DIR/lisp-kernel/lisp.h"

# 3. Boot Image (depends on kernel + compiler + level-0)
check_one "boot_image" "Boot Image" "$BOOT_IMAGE" \
  "$KERNEL_WASM" \
  "$SUBPRIMS_WASM" \
  "$ROOT_DIR/compiler/WASM/*.lisp" \
  "$ROOT_DIR/compiler/*.lisp" \
  "$ROOT_DIR/level-0/*.lisp" \
  "$ROOT_DIR/scripts/wasm/build-wasm-boot.lisp" \
  "$ROOT_DIR/scripts/wasm/build-wasm-boot.sh"

# 4. Boot Modules (produced alongside boot image)
check_one "boot_modules" "Boot Modules" "$BOOT_MODULES" \
  "$BOOT_IMAGE" \
  "$KERNEL_WASM" \
  "$SUBPRIMS_WASM"

# 5. Runtime Modules (depends on boot modules + level-1)
check_one "runtime_modules" "Runtime Modules" "$RUNTIME_MODULES" \
  "$BOOT_MODULES" \
  "$ROOT_DIR/level-1/*.lisp" \
  "$ROOT_DIR/scripts/wasm/compile-wasm-fasls.lisp" \
  "$ROOT_DIR/scripts/wasm/compile-wasm-fasls.sh"

# 6. Phase 0A Tests (depends on kernel + subprims + boot modules)
check_one "phase0a_tests" "Phase 0A Tests" "$PHASE0A_TESTS" \
  "$KERNEL_WASM" \
  "$SUBPRIMS_WASM" \
  "$BOOT_MODULES" \
  "$ROOT_DIR/scripts/wasm/compile-phase0a-tests.lisp" \
  "$ROOT_DIR/scripts/wasm/compile-phase0a-tests.sh"

# 7. Root Image (depends on everything)
check_one "root_image" "Root Image" "$ROOT_IMAGE" \
  "$KERNEL_WASM" \
  "$SUBPRIMS_WASM" \
  "$BOOT_MODULES" \
  "$RUNTIME_MODULES"

if [ "$MODE" = "report" ]; then
  echo ""
  if [ "$ANY_STALE" -eq 1 ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    printf "${RED}${BOLD}STALE ARTIFACTS DETECTED${RESET}\n"
    echo ""

    # Check if kernel or subprims changed (cascading staleness)
    case "$STALE_NAMES" in
      *kernel*|*subprims*)
        printf "  ${BOLD}Recommended:${RESET} Full rebuild (kernel/subprims changed)\n"
        printf "    ${YELLOW}scripts/wasm/rebuild-everything.sh${RESET}\n"
        echo ""
        ;;
    esac

    # Check if only tests are stale
    local_count=0
    for n in $STALE_NAMES; do local_count=$((local_count + 1)); done
    if [ "$local_count" -eq 1 ]; then
      case "$STALE_NAMES" in
        *phase0a_tests*)
          printf "  ${BOLD}Quick fix:${RESET} Recompile tests only\n"
          printf "    ${YELLOW}scripts/wasm/compile-phase0a-tests.sh${RESET}\n"
          echo ""
          ;;
      esac
    fi
  else
    printf "${GREEN}${BOLD}All artifacts are fresh.${RESET}\n"
    echo ""
  fi
fi

exit $ANY_STALE
