#!/usr/bin/env bash
#
# CCL WASM Environment Setup
#
# This script auto-detects the WASM toolchain on your system and exports
# the necessary environment variables for building.
#
# Usage:
#   source scripts/wasm/env.sh
#
# Or with custom paths:
#   CCL_WASM_SYSROOT=/path/to/sysroot source scripts/wasm/env.sh

set -euo pipefail

# ============================================================================
# Auto-detect Repository Root
# ============================================================================

# Get the directory containing this script
# Use ${BASH_SOURCE[0]:-$0} to handle being sourced vs executed
SCRIPT_FILE="${BASH_SOURCE[0]:-$0}"
SCRIPT_DIR="$(cd "$(dirname "${SCRIPT_FILE}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# ============================================================================
# Platform Detection
# ============================================================================

OS="$(uname -s)"
case "${OS}" in
  Darwin*)
    PLATFORM="macos"
    ;;
  Linux*)
    PLATFORM="linux"
    ;;
  *)
    echo "Warning: Unsupported platform '${OS}', assuming Linux-like" >&2
    PLATFORM="linux"
    ;;
esac

# ============================================================================
# Toolchain Auto-detection (macOS Homebrew)
# ============================================================================

if [[ "${PLATFORM}" == "macos" ]]; then
  # Find Homebrew prefix
  brew_prefix="$(brew --prefix 2>/dev/null || true)"
  prefixes=(
    "${brew_prefix}/opt"
    /usr/local/opt
    /opt/homebrew/opt
  )

  find_opt() {
    local name="$1"
    for p in "${prefixes[@]}"; do
      if [[ -d "${p}/${name}" ]]; then
        printf '%s\n' "${p}/${name}"
        return 0
      fi
    done
    return 1
  }

  llvm_path="$(find_opt llvm || true)"
  lld_path="$(find_opt lld || true)"
  wasi_path="$(find_opt wasi-libc || true)"

  if [[ -z "${llvm_path}" || -z "${lld_path}" || -z "${wasi_path}" ]]; then
    cat <<'EOF' >&2
Missing Homebrew dependencies. Install:
  brew install llvm lld wasi-libc
EOF
    return 1
  fi

  # Set toolchain paths if not already set
  if [[ -z "${CCL_WASM_CC:-}" ]]; then
    export CCL_WASM_CC="${llvm_path}/bin/clang"
  fi

  if [[ -z "${CCL_WASM_LD:-}" ]]; then
    export CCL_WASM_LD="${lld_path}/bin/wasm-ld"
  fi

  if [[ -z "${CCL_WASM_SYSROOT:-}" ]]; then
    export CCL_WASM_SYSROOT="${wasi_path}/share/wasi-sysroot"
  fi
fi

# ============================================================================
# Toolchain Auto-detection (Linux)
# ============================================================================

if [[ "${PLATFORM}" == "linux" ]]; then
  # Use system clang/wasm-ld if not set
  if [[ -z "${CCL_WASM_CC:-}" ]]; then
    if command -v clang-18 >/dev/null 2>&1; then
      export CCL_WASM_CC=clang-18
    elif command -v clang >/dev/null 2>&1; then
      export CCL_WASM_CC=clang
    fi
  fi

  if [[ -z "${CCL_WASM_LD:-}" ]]; then
    if command -v wasm-ld-18 >/dev/null 2>&1; then
      export CCL_WASM_LD=wasm-ld-18
    elif command -v wasm-ld >/dev/null 2>&1; then
      export CCL_WASM_LD=wasm-ld
    fi
  fi

  # Linux usually has headers in /usr/include/wasm32-wasi (no sysroot needed)
  # but we can set it if the user wants to override
  if [[ -z "${CCL_WASM_SYSROOT:-}" ]]; then
    if [[ -d /usr/share/wasi-sysroot ]]; then
      export CCL_WASM_SYSROOT=/usr/share/wasi-sysroot
    fi
  fi
fi

# ============================================================================
# Set Default Environment Variables
# ============================================================================

# Build directory (default: build/wasm32 from repo root)
export CCL_WASM_BUILD_DIR="${CCL_WASM_BUILD_DIR:-${REPO_ROOT}/build/wasm32}"
export CCL_WASM_KERNEL_DIR="${CCL_WASM_KERNEL_DIR:-${CCL_WASM_BUILD_DIR}/kernel}"
export CCL_WASM_IMAGES_DIR="${CCL_WASM_IMAGES_DIR:-${CCL_WASM_BUILD_DIR}/images}"
export CCL_WASM_MODULES_DIR="${CCL_WASM_MODULES_DIR:-${CCL_WASM_BUILD_DIR}/modules}"
export CCL_WASM_SUBPRIMS_DIR="${CCL_WASM_SUBPRIMS_DIR:-${CCL_WASM_BUILD_DIR}/subprims}"

# Target triple
export CCL_WASM_TARGET="${CCL_WASM_TARGET:-wasm32-unknown-unknown}"

# Optimization and debug
export CCL_WASM_OPT="${CCL_WASM_OPT:--O2}"
export CCL_WASM_DEBUG="${CCL_WASM_DEBUG:--g}"

# Memory growth
export CCL_WASM_ALLOW_MEMORY_GROWTH="${CCL_WASM_ALLOW_MEMORY_GROWTH:-1}"

# ============================================================================
# Construct Compiler Command with Sysroot
# ============================================================================

# If we have a sysroot, add the appropriate flags
if [[ -n "${CCL_WASM_SYSROOT:-}" ]]; then
  # For macOS, we need -D__wasi__ and -isystem flags
  if [[ "${PLATFORM}" == "macos" ]]; then
    export CCL_WASM_CC="${CCL_WASM_CC} -D__wasi__ -isystem ${CCL_WASM_SYSROOT}/include/wasm32-wasi"
  else
    # For Linux with a sysroot, use --sysroot
    export CCL_WASM_CC="${CCL_WASM_CC} --sysroot=${CCL_WASM_SYSROOT}"
  fi
elif [[ "${PLATFORM}" == "linux" ]]; then
  # On Linux without explicit sysroot, wasi headers are usually in /usr/include/wasm32-wasi
  # The compiler should find them automatically with --target=wasm32-wasi
  :
fi

# ============================================================================
# Validation
# ============================================================================

if [[ -z "${CCL_WASM_CC:-}" ]] || [[ -z "${CCL_WASM_LD:-}" ]]; then
  cat <<'EOF' >&2
ERROR: Could not auto-detect WASM toolchain.

Please install the required tools:
  macOS:  brew install llvm lld wasi-libc
  Linux:  Install clang, lld, and wasi-libc from your package manager

Or set the environment variables manually:
  export CCL_WASM_CC=/path/to/clang
  export CCL_WASM_LD=/path/to/wasm-ld
  export CCL_WASM_SYSROOT=/path/to/wasi-sysroot  # optional
EOF
  return 1
fi

# ============================================================================
# Summary
# ============================================================================

cat <<EOF
CCL WASM Environment Configured
================================
Platform:      ${PLATFORM}
Compiler:      ${CCL_WASM_CC}
Linker:        ${CCL_WASM_LD}
Target:        ${CCL_WASM_TARGET}
Sysroot:       ${CCL_WASM_SYSROOT:-<none, using system headers>}
Build Dir:     ${CCL_WASM_BUILD_DIR}
Optimization:  ${CCL_WASM_OPT}
Debug:         ${CCL_WASM_DEBUG}

Ready to build. Run:
  make -C lisp-kernel/wasm32
EOF
