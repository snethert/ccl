# macOS (iMac Pro) WASM Toolchain Setup

This document mirrors the Linux bring-up toolchain (clang + wasm-ld + WASI headers)
for the current **no-WASI runtime** CCL WASM32 kernel build.

## 1) Install Packages (Homebrew)

Match the Linux clang-18 toolchain:

```bash
brew install llvm@18
```

WASI headers + WASM utilities:

```bash
brew install wasi-libc wabt binaryen
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

Point the build at Homebrew's LLVM and wasm-ld:

```bash
export LLVM_ROOT="$(brew --prefix llvm@18)"
export PATH="$LLVM_ROOT/bin:$PATH"
export WASM_LD="$LLVM_ROOT/bin/wasm-ld"
```

Find the WASI sysroot/headers installed by `wasi-libc`:

```bash
find "$(brew --prefix wasi-libc)" -maxdepth 4 -type d \
  \( -name wasi-sysroot -o -path "*/include/wasm32-wasi" \)
```

If you see a `wasi-sysroot` directory, set:

```bash
export WASI_SYSROOT="/path/to/wasi-sysroot"
```

Then use:

```bash
export CC="$LLVM_ROOT/bin/clang --sysroot=$WASI_SYSROOT"
```

If you only see `include/wasm32-wasi` (no sysroot), set `WASI_SYSROOT` to its parent
and keep `--sysroot` as above.

## 3) Build The Kernel + Subprims

```bash
make -C lisp-kernel/wasm32 WASM_TARGET=wasm32-wasi CC="$CC" WASM_LD="$WASM_LD" clean
make -C lisp-kernel/wasm32 WASM_TARGET=wasm32-wasi CC="$CC" WASM_LD="$WASM_LD"
```

Subprims provider (optional):

```bash
make -C lisp-kernel/wasm32/subprims WASM_TARGET=wasm32-wasi CC="$CC" WASM_LD="$WASM_LD" clean
make -C lisp-kernel/wasm32/subprims WASM_TARGET=wasm32-wasi CC="$CC" WASM_LD="$WASM_LD"
```

## 4) Verify "No WASI Runtime" + Smoke Tests

```bash
wasm-objdump -x doc/wasm/js/wasmcl.wasm | rg 'wasi_snapshot_preview1' || true
```

Run all JS smoke tests:

```bash
node doc/wasm/js/all-smoke.mjs
```

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

1. The Makefiles default to `clang` and `wasm-ld-18`. On macOS you'll typically
   have `wasm-ld` without the version suffix. Always pass `WASM_LD=...` (and
   `CC=...`) to avoid name mismatches.
2. `wasi-libc` provides headers, but some toolchains lack the WASI compiler-rt
   builtins (`libclang_rt.builtins-wasm32.a`). If you see errors like
   `undefined symbol: __muloti4`, install `wasi-runtimes` or switch to a
   full `wasi-sdk` sysroot.
3. Keep the build **no-WASI runtime**: compile with `--target=wasm32-wasi`
   for headers, but link freestanding with `wasm-ld` and do **not** link
   against `wasi-libc`.
4. `source ./emsdk_env.sh` mutates `PATH` (and can override Node/Clang).
   Use a separate shell when building with the Homebrew LLVM toolchain.
