# Linux (Debian/Ubuntu) WASM Toolchain Setup

This mirrors the Linux bring-up toolchain for the current **no-WASI runtime**
CCL WASM32 kernel build.

## 1) Install Packages (apt)

```bash
sudo apt-get update
sudo apt-get install -y \
  clang-18 lld-18 wasi-libc wabt binaryen \
  nodejs python3
```

Optional (if you use `rg` in checks):

```bash
sudo apt-get install -y ripgrep
```

If `clang-18` / `lld-18` are not available in your distro, install from
`apt.llvm.org` or adjust the version in the commands below.

## 2) Verify Tooling

```bash
clang-18 --version
wasm-ld-18 --version
wasm-objdump --version
```

Confirm WASI headers exist:

```bash
test -d /usr/include/wasm32-wasi && echo "ok: WASI headers present"
```

## 3) Build The Kernel + Subprims

```bash
make -C lisp-kernel/wasm32 WASM_TARGET=wasm32-wasi CC=clang-18 WASM_LD=wasm-ld-18 clean
make -C lisp-kernel/wasm32 WASM_TARGET=wasm32-wasi CC=clang-18 WASM_LD=wasm-ld-18
```

Subprims provider (optional):

```bash
make -C lisp-kernel/wasm32/subprims WASM_TARGET=wasm32-wasi CC=clang-18 WASM_LD=wasm-ld-18 clean
make -C lisp-kernel/wasm32/subprims WASM_TARGET=wasm32-wasi CC=clang-18 WASM_LD=wasm-ld-18
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

There is a helper script that installs packages, builds, and runs smoke tests:

```bash
scripts/wasm/linux-setup.sh --install
scripts/wasm/linux-setup.sh --subprims --smoke
scripts/wasm/linux-setup.sh --print-env
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

### Option B: Distro package

```bash
sudo apt-get install -y emscripten
```

## Hidden Gotchas

1. The Makefiles default to `clang` and `wasm-ld-18`. Always pass `CC=clang-18`
   and `WASM_LD=wasm-ld-18` if multiple versions are installed.
2. Keep the build **no-WASI runtime**: compile with `--target=wasm32-wasi` for
   headers, but link freestanding with `wasm-ld` and do **not** link against
   `wasi-libc`.
3. Debian/Ubuntu `wasi-libc` provides headers in `/usr/include/wasm32-wasi` but
   does not ship a `wasi-sysroot/` directory.
4. Some distros ship `nodejs` without a `node` symlink. If `node` is missing,
   use `nodejs` or install a newer Node from Nodesource.
