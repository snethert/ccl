# macOS WASM Toolchain Setup

**Status:** Active
**Scope:** macOS-specific WASM toolchain installation and verification
**Last Updated:** 2026-02-15
**Doc Version:** 1.0.0

This document mirrors the Linux bring-up toolchain (clang + wasm-ld + WASI headers)
for the current **no-WASI runtime** CCL WASM32 kernel build.

## 1) Install Packages (Homebrew)

Install a wasm-capable toolchain (Apple clang can parse wasm targets but cannot
emit wasm objects):

```bash
brew install llvm lld wasi-libc
```

WASM utilities:

```bash
brew install wabt binaryen
```

Optional: compiler-rt / libc++ runtimes for WASI (only if you hit builtins/link errors):

```bash
brew install wasi-runtimes
```

Node + Python (used by scripts and JS smoke tests):

```bash
brew install node python
```

## 2) Environment Setup

Use the helper script to export a working toolchain:

```bash
source scripts/wasm/env.sh
```

This sets:

- `CC` to Homebrew `clang` with `-D__wasi__` and the WASI headers.
- `WASM_LD` to Homebrew `wasm-ld` (from `lld`).

To inspect the effective values:

```bash
scripts/wasm/macos-setup.sh --print-env
```

## 3) Build The Kernel + Subprims

```bash
make -C lisp-kernel/wasm32 clean
make -C lisp-kernel/wasm32
```

Subprims provider (optional):

```bash
make -C lisp-kernel/wasm32/subprims clean
make -C lisp-kernel/wasm32/subprims
```

## 4) Verify "No WASI Runtime" + Smoke Tests

```bash
wasm-objdump -x build/wasm32/wasmcl.wasm | rg 'wasi_snapshot_preview1' || true
```

Run all JS smoke tests:

```bash
node scripts/wasm/tests/all-smoke.mjs
```

These smoke tests are sandbox-safe. External LMDB/IndexedDB integration tests
are listed in `doc/testing.md`. Default unattended persistence direction is the
memory-first snapshot backend documented in
`doc/wasm/persistence-dev-environment.md`.

## Automation Script

There is a helper script that sets the toolchain env and runs the build:

```bash
scripts/wasm/macos-setup.sh --install
scripts/wasm/macos-setup.sh --subprims --smoke
scripts/wasm/macos-setup.sh --print-env
```

## 5) Emscripten (Optional)

### Option A: emsdk (official SDK)

```bash
git clone https://github.com/emscripten-core/emsdk.git
cd emsdk
./emsdk update
./emsdk install latest
./emsdk activate latest
source ./emsdk_env.sh
emcc --check
```

### Option B: Homebrew formula

```bash
brew install emscripten
```

## Hidden Gotchas

1. Apple clang can parse wasm targets but cannot emit wasm object code.
   Use Homebrew `llvm` + `lld`.
2. The Makefiles default to `clang` and `wasm-ld-18`. The recommended path
   is to `source scripts/wasm/env.sh`, which sets `CC` and `WASM_LD`.
3. `wasi-libc` provides headers, but some toolchains lack the WASI compiler-rt
   builtins (`libclang_rt.builtins-wasm32.a`). If you see errors like
   `undefined symbol: __muloti4`, install `wasi-runtimes` or switch to a
   full `wasi-sdk` sysroot.
4. Keep the build **no-WASI runtime**: compile with WASI headers but link
   freestanding with `wasm-ld` and do **not** link against `wasi-libc`.
5. `source ./emsdk_env.sh` mutates `PATH` (and can override Node/Clang).
   Use a separate shell when building with the Homebrew LLVM toolchain.
