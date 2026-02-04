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

## Verify “No WASI Runtime”

Confirm there are **no** `wasi_snapshot_preview1` imports:

```bash
wasm-objdump -x doc/wasm/js/wasmcl.wasm | rg 'wasi_snapshot_preview1' || true
```

Expected imports (current model):

- `env.memory`
- `env.__indirect_function_table`

## JS Wiring (Sketch-Level)

See:

- `doc/wasm/js/README.md`
- `doc/wasm/js/ccl-loader.mjs`
- `doc/wasm/js/demo-runner.mjs`

The demo runner:

- Instantiates the kernel with a shared `WebAssembly.Memory` and `WebAssembly.Table`.
- Installs subprims into the shared table by matching export names.
- Calls `wasm_set_cstack_bounds` to establish a manual control stack region.
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
- `start_lisp` is currently a stub (traps) until the real entry/loader path is implemented.
- The “no-WASI libc” shims are intentionally minimal (bump `malloc`, no real stdio/formatting).
