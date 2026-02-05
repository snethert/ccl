# WASM Build Notes (No WASI Runtime)

This describes the current “bring-up” build of the CCL WASM32 kernel on Linux
(Mint/Ubuntu-style packaging), with a **strict no-WASI runtime** constraint:
the resulting `wasmcl.wasm` must **not** import `wasi_snapshot_preview1.*`.

## Summary (Current Decisions)

- Compile with `--target=wasm32-wasi` to use the distro-provided WASI headers.
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

## Note About `wasi-libc` Layout

On Mint/Ubuntu, `wasi-libc` does **not** ship a `wasi-sysroot/` directory (that
layout comes from `wasi-sdk`). The headers live under:

- `/usr/include/wasm32-wasi`

That’s why `dpkg -L wasi-libc | rg 'wasi-sysroot$'` returns nothing.

## Build The Kernel

Build output is currently produced by `lisp-kernel/wasm32/Makefile` into:

- `doc/wasm/js/wasmcl.wasm`

Build command:

```bash
make -C lisp-kernel/wasm32 WASM_TARGET=wasm32-wasi clean
make -C lisp-kernel/wasm32 WASM_TARGET=wasm32-wasi
```

## Build The Subprims Provider (Scaffold)

This optional build produces a separate `subprims.wasm` module for the shared
subprims table:

```bash
make -C lisp-kernel/wasm32/subprims WASM_TARGET=wasm32-wasi clean
make -C lisp-kernel/wasm32/subprims WASM_TARGET=wasm32-wasi
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

After building `doc/wasm/js/wasmcl.wasm`, run:

```bash
node doc/wasm/js/smoke-test.mjs
node doc/wasm/js/funcall-smoke.mjs
node doc/wasm/js/kernel-request-smoke.mjs
node doc/wasm/js/stream-open-smoke.mjs
node doc/wasm/js/pending-stdin-smoke.mjs
node doc/wasm/js/step-demo.mjs
node doc/wasm/js/ccl-step-smoke.mjs
```

## Load A Heap Image (Boot-Only)

The kernel can also load an OpenMCL heap image from a host-provided byte blob
and return to JS **without** entering Lisp yet (it skips `start_lisp`).

```bash
node doc/wasm/js/load-image.mjs /path/to/ccl.image
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
- Calls `wasm_ccl_start` to enter the kernel.

## Subprims Artifacts

WASM subprims indices must match the ARM `sptab` order (`lisp-kernel/arm-spentry.s`).
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
- `start_lisp` can run a stub toplevel loop when the minimal image + boot entrypoint are installed; the real Lisp toplevel is still pending, so use `wasm_ccl_step` for the Stage‑2 stepping baseline while the full entry/loader path is integrated.
- The “no-WASI libc” shims are intentionally minimal (bump `malloc`, no real stdio/formatting).
