# WASM Subprims ABI (Decisions)

This document captures the current decisions for the WASM backend subprims ABI.

## Summary

- **Subprims are represented as fixnum indices** into a WASM function table.
- **`SUBPRIMS_BASE` is a sentinel** for WASM and is set to `0`.
- Calls use a **uniform C ABI** with implicit TCR state and a **single dispatcher**.
- The dispatcher performs **`call_indirect`** using the table index extracted from the fixnum.
- The WASM table order **must match the ARM `sptab` order** so indices align.
- The current TCR pointer is accessed via **`wasm_get_current_tcr` / `wasm_set_current_tcr`**.

## Rationale

WASM tables are first-class VM objects and are **distinct from linear memory**. Function pointers are **table indices**, not code addresses. Any design that treats subprims as PC-style addresses will break when compiled to WASM.

Using fixnum indices:

- matches the WASM model directly,
- remains stable across memory growth,
- avoids fake address arithmetic.

## Representation

### Subprim Identity

- A subprim is a **fixnum** whose value is the **table index**.
- `SUBPRIMS_BASE` is **unused** (set to `0`), not an address.

### Dispatcher

```
void wasm_call_subprim_fixnum(LispObj sp_index_fixnum);
```

Implementation:

1. Extract index from fixnum.
2. `call_indirect` into the WASM table ordered like `arm-spentry.s`.
3. Subprim uses **implicit TCR/VSP/ALLOCPTR** state in linear memory.

### Table Wiring

The WASM build uses the module's function-pointer table (indirect function
table) for `call_indirect` dispatch. For multi-module setups, link all modules
against an **imported table** and have the host provide and populate it with
subprim implementations in ARM `sptab` order.

Toolchain note: Clang's `import_module`/`import_name` attributes apply to
functions, not tables or globals, so table imports are typically controlled by
the linker (e.g. wasm-ld flags like `--import-table`).

### Current TCR Access

Subprims need a stable way to find the "current thread" state. In the current
bring-up we expose this as exported functions:

```
void wasm_set_current_tcr(TCR *tcr);
TCR *wasm_get_current_tcr(void);
```

The host can connect multiple modules by importing these functions from the
kernel instance when instantiating provider/compiled-code modules.

## Calling Convention

- Subprims are `void` C functions with **no explicit arguments**.
- All state is read from and written to the TCR.
- Entry/exit boundaries must update `last_lisp_frame` using the manual cstack.
- The host must establish a manual cstack region before starting the kernel
  (via `wasm_set_cstack_bounds(base, size)`).

## Register File (WASM32)

- WASM32 builds add `tcr->wasm_gprs[16]` as an in-memory register file.
- The ARM register index macros (`arg_z`, `nargs`, `Rfn`, etc.) are used as
  indices into this array.
- `tcr->save_vsp` / `tcr->save_tsp` are treated as the canonical VSP/TSP
  pointers for WASM subprims.

## Migration Implications

The following changes will be required (no code included here):

- Any place that computes a subprim address via `SUBPRIMS_BASE` must instead treat the subprim value as **an index**.
- Any "PC-in-subprims-range" checks must be reworked for WASM.
- The compiler must emit calls via the dispatcher or otherwise use table indices.

## Status

- Header added: `lisp-kernel/wasm-subprims.h` (dispatcher declaration and helpers).
- Runtime now implements `call_indirect` and imports the WASM table.
