# CCL WASM Build Configuration
#
# This file defines default values for the WASM build environment.
# All values can be overridden via environment variables.
#
# Example:
#   CCL_WASM_CC=/custom/clang make
#   CCL_WASM_BUILD_DIR=/tmp/build make

# ============================================================================
# Toolchain Configuration
# ============================================================================

# C Compiler (default: clang)
# Override: CCL_WASM_CC=/path/to/clang
CCL_WASM_CC ?= clang

# WASM Linker (default: wasm-ld)
# Override: CCL_WASM_LD=/path/to/wasm-ld
CCL_WASM_LD ?= wasm-ld

# WASM Target Triple (default: wasm32-unknown-unknown)
# Override: CCL_WASM_TARGET=wasm32-wasi
CCL_WASM_TARGET ?= wasm32-unknown-unknown

# ============================================================================
# Build Paths
# ============================================================================

# Root build directory (default: build/wasm32 from repo root)
# Override: CCL_WASM_BUILD_DIR=/custom/build/path
CCL_WASM_BUILD_DIR ?= $(REPO_ROOT)/build/wasm32

# Derived paths (normally don't override these)
CCL_WASM_KERNEL_DIR ?= $(CCL_WASM_BUILD_DIR)/kernel
CCL_WASM_IMAGES_DIR ?= $(CCL_WASM_BUILD_DIR)/images
CCL_WASM_MODULES_DIR ?= $(CCL_WASM_BUILD_DIR)/modules
CCL_WASM_SUBPRIMS_DIR ?= $(CCL_WASM_BUILD_DIR)/subprims

# ============================================================================
# Compiler and Linker Flags
# ============================================================================

# Additional C compiler flags
# Override: CCL_WASM_CFLAGS="-DDEBUG -Wall"
CCL_WASM_CFLAGS ?=

# Additional linker flags
# Override: CCL_WASM_LDFLAGS="--strip-debug"
CCL_WASM_LDFLAGS ?=

# ============================================================================
# Platform-Specific Configuration
# ============================================================================

# WASI Sysroot (auto-detected if not set)
# Override: CCL_WASM_SYSROOT=/path/to/wasi-sysroot
#
# Common locations:
#   macOS Homebrew:  /usr/local/opt/wasi-libc/share/wasi-sysroot
#                    /opt/homebrew/opt/wasi-libc/share/wasi-sysroot
#   Linux:           /usr/share/wasi-sysroot (if using wasi-sdk)
#                    Headers in /usr/include/wasm32-wasi (package manager)
CCL_WASM_SYSROOT ?=

# Memory growth (0=disabled, 1=enabled)
CCL_WASM_ALLOW_MEMORY_GROWTH ?= 1

# ============================================================================
# Build Options
# ============================================================================

# Optimization level (-O0, -O1, -O2, -O3, -Os, -Oz)
CCL_WASM_OPT ?= -O2

# Debug symbols (-g)
CCL_WASM_DEBUG ?= -g

# Version control revision (auto-detected from git)
VC_REVISION ?= $(shell git describe --dirty 2>/dev/null || echo unknown)
