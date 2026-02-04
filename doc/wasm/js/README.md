# JS Wiring Notes (WASM, No WASI)

This folder contains **sketch-level** JS wiring for instantiating the WASM CCL
kernel with a **shared subprims table**.

Key objects (created in JS):

* `WebAssembly.Table` (wired to `env.__indirect_function_table` for `call_indirect`)
* Optional: `WebAssembly.Memory` `env.memory` (if you want multiple modules to share one linear memory)

The subprims table order must match the ARM `sptab` order. The canonical list
is extracted from `lisp-kernel/arm-spentry.s` and checked in as:

* `doc/wasm/subprims-map.json`

`demo-runner.mjs` shows one possible convention:

1. Instantiate the kernel with `{ env: { memory, __indirect_function_table }, ccl: { subprims_table } }`.
2. Instantiate one or more "provider" modules that export subprim functions.
3. Install subprims into the shared table by matching export names from `subprims-map.json`.
4. Call the exported `wasm_set_cstack_bounds(base, size)` to establish a manual control stack region.
5. Call the kernel entrypoint `wasm_ccl_start`.

This design supports incremental optimization: a later-loaded module can
override any table slot with a faster handwritten WASM implementation.
