# JS Wiring Notes (WASM, No WASI)

This folder contains **sketch-level** JS wiring for instantiating the WASM CCL
kernel with a **shared subprims table**.

Key objects (created in JS):

* `WebAssembly.Table` (wired to `env.__indirect_function_table` for `call_indirect`)
* Optional: `WebAssembly.Memory` `env.memory` (if you want multiple modules to share one linear memory)
* A JS microkernel that implements the `ccl.kernel_request` ABI (see `microkernel.mjs`)
* Optional: a lightweight world/runner manager (`world-kernel.mjs`) that composes the microkernel with runner lifecycle helpers

The subprims table order must match the ARM `sptab` order, with WASM-only
stub entries appended at the end. The canonical list is extracted from
`lisp-kernel/arm-spentry.s` and checked in as:

* `doc/wasm/subprims-map.json`

`demo-runner.mjs` shows one possible convention:

1. Instantiate the kernel with `{ env: { memory, __indirect_function_table }, ccl: { ...kernel_request imports..., subprims_table } }`.
2. Instantiate one or more "provider" modules that export subprim functions.
3. Install subprims into the shared table by matching export names from `subprims-map.json`.
4. If the provider exports the Tier 0 subprims (`_SPmkcatch1v`, `_SPfuncall`, `_SPnthrow1value`), call `wasm_set_subprims_ready(1)`.
5. Call the exported `wasm_set_cstack_bounds(base, size)` to establish a manual control stack region.
6. Install the boot entrypoint (the minimal image uses table index 200 → `wasm_boot_entry`), then choose an entry path: `wasm_ccl_start` (boot + `start_lisp`), `wasm_ccl_start_lisp` (enter `start_lisp` after a boot‑only load), `wasm_run_toplevel` (one-shot toplevel), or `wasm_ccl_step` (host-stepped toplevel).

If you load a heap image via `wasm_ccl_load_image`, install compiled modules
from the registry (see `installCompiledModulesFromRegistry`) before entering
`start_lisp` or stepping the toplevel.

`world-kernel.mjs` provides a minimal reference API for:

* registering images
* creating worlds and runners
* loading an image into a runner
* starting the kernel (`runner.start`, which uses `wasm_ccl_start_lisp` if an image was loaded), entering Lisp after `loadImage` (`runner.startLisp`), or stepping (`runner.step`)
* feeding stdin / closing stdin
* querying runner objects via `getRunner(runnerId)`

This design supports incremental optimization: a later-loaded module can
override any table slot with a faster handwritten WASM implementation.
