# WASM Build Notes (No WASI Runtime)

This describes the current “bring-up” build of the CCL WASM32 kernel on Linux
(Mint/Ubuntu-style packaging), with a **strict no-WASI runtime** constraint:
the resulting `wasmcl.wasm` must **not** import `wasi_snapshot_preview1.*`.

## Summary (Current Decisions)

- Compile with a wasm32 target and WASI headers.
  - Linux: `--target=wasm32-wasi`.
  - macOS: Homebrew `clang` with `-D__wasi__` and `-isystem .../include/wasm32-wasi` (see `scripts/wasm/env.sh`).
- Link **freestanding** with `wasm-ld` and **do not** link against `wasi-libc`.
- Provide a minimal C “libc shim” inside the kernel (`lisp-kernel/wasm-no-wasi-libc.c`).
- The host (JS microkernel) provides `env.memory` (imported linear memory).
- The host (JS microkernel) provides `env.__indirect_function_table` (imported function table for `call_indirect`).
- The host (JS microkernel) provides the **kernel_request ABI** imports under module `ccl`
  (`kernel_request`, `kernel_poll`, `kernel_result`, `kernel_response_size`, `kernel_copy_response`, `kernel_drop_request`).
- The host must call `wasm_set_cstack_bounds(base, size)` before starting Lisp.
- The host may also call `wasm_set_cstack_pointer(sp)` to set/restore the cstack SP.

## Prerequisites (Mint/Ubuntu)

These packages are expected:

- `clang-18`
- `lld-18` (provides `wasm-ld-18`)
- `wasi-libc` (headers only, for compilation)
- Optional: `wabt` (for `wasm-objdump`, `wasm2wat`)
- Optional: `binaryen` (for `wasm-opt`)

Tool locations you should have:

```bash
clang --version
wasm-ld-18 --version
wasm-objdump --version
```

## Prerequisites (macOS + Homebrew)

Install a wasm-capable toolchain. Apple clang can parse wasm targets but
cannot emit wasm objects; you need Homebrew LLVM + LLD:

```bash
brew install llvm lld wasi-libc
```

Use the helper to export the correct toolchain variables:

```bash
source scripts/wasm/env.sh
```

This sets:

- `CC` to Homebrew `clang` with WASI headers and `-D__wasi__`
- `WASM_LD` to Homebrew `wasm-ld`

## Toolchain Sanity Check

After `source scripts/wasm/env.sh`, verify the toolchain:

```bash
$CC --version
$WASM_LD --version
```

## Note About `wasi-libc` Layout

On Mint/Ubuntu, `wasi-libc` does **not** ship a `wasi-sysroot/` directory (that
layout comes from `wasi-sdk`). The headers live under:

- `/usr/include/wasm32-wasi`

That’s why `dpkg -L wasi-libc | rg 'wasi-sysroot$'` returns nothing.

On macOS/Homebrew, headers live under:

- `/usr/local/opt/wasi-libc/share/wasi-sysroot/include/wasm32-wasi`
- or `/opt/homebrew/opt/wasi-libc/share/wasi-sysroot/include/wasm32-wasi`

## Build The Kernel

**IMPORTANT (macOS/Homebrew):** You MUST run the toolchain setup script **before**
invoking `make`, otherwise the build will fail (commonly with
`fatal error: 'errno.h' file not found`).

```bash
source scripts/wasm/env.sh
make -C lisp-kernel/wasm32 CC="$CC"
```

Build output is currently produced by `lisp-kernel/wasm32/Makefile` into:

- `doc/wasm/js/wasmcl.wasm`

Build command (Linux / `--target=wasm32-wasi` toolchains):

```bash
make -C lisp-kernel/wasm32 WASM_TARGET=wasm32-wasi clean
make -C lisp-kernel/wasm32 WASM_TARGET=wasm32-wasi
```

On macOS, if `scripts/wasm/env.sh` is not used, this explicit command works:

```bash
make -C lisp-kernel/wasm32 WASM_TARGET=wasm32-wasi \
  CC='/usr/local/opt/llvm@18/bin/clang-18 --sysroot=/usr/local/opt/wasi-libc/share/wasi-sysroot'
```

On macOS (after `source scripts/wasm/env.sh`), you can also run:

```bash
make -C lisp-kernel/wasm32 CC="$CC"
```

## Build The Subprims Provider (Scaffold)

This optional build produces a separate `subprims.wasm` module for the shared
subprims table:

```bash
make -C lisp-kernel/wasm32/subprims WASM_TARGET=wasm32-wasi clean
make -C lisp-kernel/wasm32/subprims WASM_TARGET=wasm32-wasi
```

On macOS (after `source scripts/wasm/env.sh`), just run:

```bash
make -C lisp-kernel/wasm32/subprims CC="$CC"
```

The JS host should only call `wasm_set_subprims_ready(1)` when the provider
exports the required Tier 0 subprims (`_SPmkcatch1v`, `_SPfuncall`,
`_SPnthrow1value`).

## Verify “No WASI Runtime”

Confirm there are **no** `wasi_snapshot_preview1` imports:

```bash
wasm-objdump -x doc/wasm/js/wasmcl.wasm | rg 'wasi_snapshot_preview1' || true
```

Expected imports (current model):

- `env.memory`
- `env.__indirect_function_table`
- `ccl.kernel_request`
- `ccl.kernel_poll`
- `ccl.kernel_result`
- `ccl.kernel_response_size`
- `ccl.kernel_copy_response`
- `ccl.kernel_drop_request`

## Run The Node Smoke Test

This validates:

- `call_indirect` subprims dispatch via `wasm_call_subprim_fixnum`
- manual cstack relocation across `memory.grow`
- kernel_request ABI wiring via `kernel-request-smoke.mjs`

After building `doc/wasm/js/wasmcl.wasm`, run all smoke tests:

```bash
node doc/wasm/js/all-smoke.mjs
```

To run a single test, invoke it directly. The authoritative list is in
`doc/wasm/js/all-smoke.mjs`.

These smoke tests are sandbox-safe. External tests (LMDB and IndexedDB) are
documented in `doc/testing.md`.

**Standing rule:** Every smoke test must be standalone and must be added to
`doc/wasm/js/all-smoke.mjs`. When a new smoke test is created, run:

```bash
node doc/wasm/js/all-smoke.mjs
node doc/wasm/js/<new-test>.mjs
```

## Compile WASM Smoke Modules

Generate the compiler-emitted module bundle used by `compiler-smoke.mjs`:

```bash
scripts/wasm/compile-smoke-modules.sh --output doc/wasm/wasm-smoke-modules.json
```

`scripts/wasm/{macos,linux}-setup.sh --smoke` will run this automatically when
`ccl` is available on the host.

## Load A Heap Image (Boot-Only)

The kernel can also load an OpenMCL heap image from a host-provided byte blob
and return to JS **without** entering Lisp yet (it skips `start_lisp`).

```bash
node doc/wasm/js/load-image.mjs /path/to/ccl.image
```
To enter Lisp after loading (requires subprims + boot entry). For real images,
pass the compiled-modules bundle produced by `compile-wasm-fasls.sh`:
```bash
node doc/wasm/js/load-image.mjs --start-lisp --modules /path/to/wasm-runtime-modules.json /path/to/ccl.image
```
To run the toplevel once (explicit entry, no stepping):
```bash
node doc/wasm/js/load-image.mjs --run --modules /path/to/wasm-runtime-modules.json /path/to/ccl.image
```

## Generate A Minimal WASM Image

Build a tiny bring-up image with a stub toplevel function entrypoint:

```bash
python3 scripts/wasm/make_minimal_image.py --output doc/wasm/minimal.image
```

The default entrypoint table index is `200` (see `doc/wasm/ABI.md`).

To exercise the toplevel loop with the minimal image:

```bash
node doc/wasm/js/load-image.mjs --run doc/wasm/minimal.image
```
Or to boot via `start_lisp` instead of the explicit toplevel run:
```bash
node doc/wasm/js/load-image.mjs --start-lisp doc/wasm/minimal.image
```
(`minimal.image` does not require the compiled-modules bundle.)

## Generate A Real WASM Image (Seed)

Build a real WASM32 heap image with `%toplevel-function%` seeded to
`toplevel-loop` (so `start_lisp` can enter the real Lisp toplevel once the
image is loaded).

### Option A (Host CCL, recommended)

1. Cross-compile the WASM32 fasls needed by `level-1.lafsl`, and emit the
   compiled-modules bundle used by the JS loader:

```bash
scripts/wasm/compile-wasm-fasls.sh --modules-out doc/wasm/wasm-runtime-modules.json
```
This produces `doc/wasm/wasm-runtime-modules.json` plus the sidecar
`doc/wasm/wasm-runtime-modules.bin` in the same directory.
The bundle writer deduplicates identical const-pool payloads to keep the
sidecar size bounded.

If you already have a large legacy bundle, compact it in place without
recompiling:

```bash
node scripts/wasm/compact-runtime-modules.mjs --manifest doc/wasm/wasm-runtime-modules.json --in-place
```

For stronger size reduction, also compress deduplicated const pools (gzip is
browser-safe):

```bash
node scripts/wasm/compact-runtime-modules.mjs --manifest doc/wasm/wasm-runtime-modules.json --in-place --compress-const-pools
```

For max compression in Node-only workflows, use Brotli:

```bash
node scripts/wasm/compact-runtime-modules.mjs --manifest doc/wasm/wasm-runtime-modules.json --in-place --const-pool-encoding br --brotli-quality 7
```

2. Build the wasm boot image via cross-xload:

```bash
scripts/wasm/build-wasm-boot.sh
```

3. Run the real-image policy script on the host (it injects `:wasm32-target`
   into `*features*` if missing, so a normal 64-bit host CCL is sufficient):

```bash
ccl --no-init --batch -l scripts/wasm/make-real-image.lisp -- --output doc/wasm/root.image
```
On non-WASM hosts this now preserves the host workflow by delegating to
`node doc/wasm/js/make-real-image.mjs` under the hood.

4. Validate the real image in the JS loader (uses the compiled-modules bundle):

```bash
node doc/wasm/js/load-image.mjs --start-lisp --modules doc/wasm/wasm-runtime-modules.json doc/wasm/root.image
```
Current status: this script path produces loadable wasm images. Note that a raw
host `save-application` image (without the wasm helper path) is still not a
drop-in wasm heap image format.

### Option B (Node helper, wasm-only path)

Run the Node helper to load the boot image, execute the Lisp script, and
extract the generated image from the persistence store:

```bash
node doc/wasm/js/make-real-image.mjs --modules doc/wasm/wasm-runtime-modules.json --output doc/wasm/root.image
```
Current status: working; this path now produces a loadable image. Validate with:

```bash
node doc/wasm/js/load-image.mjs doc/wasm/root.image
```

### Option C (native wasm32 CCL, optional)

If you already have a **WASM32-target** CCL, you can run the Lisp script
directly (it will still inject `:wasm32-target` into `*features*` if missing):

```bash
ccl --no-init --batch -l scripts/wasm/make-real-image.lisp -- --output doc/wasm/root.image
```

## JS Wiring (Sketch-Level)

See:

- `doc/wasm/js/README.md`
- `doc/wasm/js/ccl-loader.mjs`
- `doc/wasm/js/demo-runner.mjs`

The demo runner:

- Instantiates the kernel with a shared `WebAssembly.Memory` and `WebAssembly.Table`.
- Installs subprims into the shared table by matching export names.
- Calls `wasm_set_cstack_bounds` to establish a manual control stack region.
- Calls `wasm_set_subprims_ready(1)` when a real subprims provider module is installed.
- Installs the boot entrypoint (minimal image uses table index 200 → `wasm_boot_entry`).
- Calls `wasm_ccl_start` to enter the kernel (or `wasm_ccl_step`/`wasm_run_toplevel` for host‑controlled toplevel).
  For a boot‑only load followed by toplevel entry, use `wasm_ccl_start_lisp`.

## Subprims Artifacts

WASM subprims indices must match the ARM `sptab` order (`lisp-kernel/arm-spentry.s`),
with WASM-only stub entries appended at the end.
Artifacts are generated from ARM and checked in:

- `doc/wasm/subprims-map.json`
- `lisp-kernel/wasm-subprims-map.h`
- `lisp-kernel/wasm-subprims-standin.c`

Regenerate:

```bash
python3 scripts/wasm/generate_subprims_artifacts.py
```

## Bring-Up Status / Limitations

- Many OS/POSIX interfaces are stubbed out for WASM32 bring-up.
- Boot image + compiled module bundle can enter `start_lisp` without immediate macro-apply/UDF traps.
- Real image generation is supported in both host-script and Node-helper
  workflows; host script delegates to the helper on non-WASM runtimes.
- The “no-WASI libc” shims are intentionally minimal (bump `malloc`, no real stdio/formatting).
