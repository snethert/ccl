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

**Note:** We are not currently passing `TCR*` as an explicit parameter to
entrypoints. That remains a possible future ABI variant, but the current design
assumes `wasm_get_current_tcr()` is the single authoritative access path.

## Calling Convention

- Subprims are `void` C functions with **no explicit arguments**.
- All state is read from and written to the TCR.
- Entry/exit boundaries must update `last_lisp_frame` using the manual cstack.
- The host must establish a manual cstack region before starting the kernel
  (via `wasm_set_cstack_bounds(base, size)`).

## GC Roots and Spill Rules

- The WASM operand stack is **never** part of the GC root set.
- GC roots live in **TCR fields** plus the **explicit Lisp stacks** in linear
  memory (VSP/TSP/cstack).
- The TCR register file (`tcr->wasm_gprs`) is the **authoritative** source of
  register state at safepoints.
- If compiled code caches registers in WASM locals, it **must spill** those
  cached values back into `tcr->wasm_gprs` before:
  - any call that may trigger GC,
  - any call into runtime helpers or subprims,
  - any host/kernel boundary (`kernel_request`),
  - any explicit safepoint check or cooperative yield.

## Register File (WASM32)

- WASM32 builds add `tcr->wasm_gprs[16]` as an in-memory register file.
- The ARM register index macros (`arg_z`, `nargs`, `Rfn`, etc.) are used as
  indices into this array.
- `tcr->save_vsp` / `tcr->save_tsp` are treated as the canonical VSP/TSP
  pointers for WASM subprims.

## Lisp Function Entry ABI (WASM32)

- `_function.entrypoint` is a **fixnum table index** (not a PC/address).
- `_function.codevector` mirrors the same index (GC sanity check).
- Entry functions have signature `void ()` and use the **current TCR**
  (`wasm_get_current_tcr`) plus the register file/VSP for arguments/results.
- `nargs` is a fixnum count. Arguments live on the VSP (stack grows down).
  `_SPfuncall` mirrors the top 3 VSP arguments into `arg_z/arg_y/arg_x` for
  ARM‑compatible calling semantics.
- Single‑value return uses `arg_z` with `nargs = 1`. Multi‑value returns
  remain Tier‑1 (values on VSP + `nargs` count).
- `_SPfuncall` resolves `nfn` (symbol → fcell, function → entrypoint) and
  dispatches via `call_indirect` using the entrypoint index.

### Boot Entry Stub (Bring‑Up)

- Minimal boot images may point `%toplevel-function%` at a stub function object.
- The stub entrypoint is a **table index**; current bring‑up uses **index 200**.
- The host should install the kernel export `wasm_boot_entry` at that table slot.

### Non‑local Transfer (Tier‑0, cooperative unwind)

- `_SPnthrow1value` unwinds the catch chain and restores TCR state, then sets
  `tcr->wasm_pending_throw` to a non‑zero fixnum. The single value remains in
  `arg_z` with `nargs = 1`; VSP is restored to the target catch frame’s
  `save_vsp`.
- **Generated code MUST** check `tcr->wasm_pending_throw` after calls and
  propagate the unwind by returning without further work.
- The catch cleanup point **MUST** clear `tcr->wasm_pending_throw` once control
  is re‑established.
- Unwind‑protect frames remain Tier‑1; the provider currently traps if such a
  frame is encountered.

## Migration Implications

The following changes will be required (no code included here):

- Any place that computes a subprim address via `SUBPRIMS_BASE` must instead treat the subprim value as **an index**.
- Any "PC-in-subprims-range" checks must be reworked for WASM.
- The compiler must emit calls via the dispatcher or otherwise use table indices.

## Status

- Header added: `lisp-kernel/wasm-subprims.h` (dispatcher declaration and helpers).
- Runtime now implements `call_indirect` and imports the WASM table.
