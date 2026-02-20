# WASM Subprims ABI (Decisions)

**Status:** Active
**Scope:** WASM backend subprims ABI decisions and calling conventions
**Last Updated:** 2026-02-20
**Doc Version:** 1.1.0

This document captures the current decisions for the WASM backend subprims ABI.

## Summary

- **Subprims are represented as fixnum indices** into a WASM function table.
- **`SUBPRIMS_BASE` is a sentinel** for WASM and is set to `0`.
- Calls use a **uniform C ABI** with implicit TCR state and a **single dispatcher**.
- The dispatcher performs **`call_indirect`** using the table index extracted from the fixnum.
- The WASM table order **must match the ARM `sptab` order** so indices align.
- The current TCR pointer is accessed via **`wasm_get_current_tcr` / `wasm_set_current_tcr`**.
- Post-MVP2 runtime uses **two profiles**: `dev` (dynamic) and `fast`
  (compilerless/closed-world for selected hot paths).

## Execution Profiles (Post-MVP2)

### `dev` profile (default, mutable runtime)

- Keep the current ABI: subprim fixnum indices + dispatcher + `call_indirect`.
- Keep dynamic behaviors: runtime compilation, function/method redefinition, and
  host callbacks for const-pool/function-designator resolution.
- `_SPfuncall` continues entry-index dispatch via `call_indirect`.

### `fast` profile (finished app runtime)

- Saved app excludes compiler payload and treats hot paths as closed-world.
- Compiler may emit direct subprim imports for allowlisted hot paths instead of
  going through `wasm_call_subprim_fixnum`.
- Hot-path generic calls are forbidden unless rewritten as direct concrete calls
  (or compile-time expanded wrappers).
- Runtime method/function redefinition is disallowed for fast-profile hot paths.

### `call_indirect` policy

- The core kernel ABI remains entry-index based and still supports
  `call_indirect` for compatibility.
- A strict "no `call_indirect`" gate is valid only for fast-profile app modules
  produced by the specialized pipeline.
- Enforcement is by opcode scan for `0x11` on fast-profile app modules (not on
  kernel/provider/bootstrap artifacts).

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
- WASM local spills use a dedicated **spill stack** (not the VSP). The runtime
  scans this spill stack during GC.

### Spill/Restore Invariants (MUST)

- Every `:call-subprim` site emitted by `compiler/WASM/wasm2.lisp` MUST be
  enclosed by a balanced spill/restore region (`:spill-locals` before,
  `:restore-locals` after).
- `:call-subprim-no-spill` MUST be used only for the explicit allowlist of
  VSP-sensitive subprims (`.SPthrow`, `.SPmkcatch1v`, `.SPnthrow1value`,
  `.SPsave-values`, `.SPadd-values`, `.SPrecover-values`, `.SPprogvsave`,
  `.SPprogvrestore`, `.SPconslist`).
- After every subprim call, argument/result registers MUST be read from the
  TCR register file (`arg_z`, `arg_y`, `arg_x`, `nargs`) and never from stale
  cached locals.
- Any path that materializes multiple values on VSP MUST either:
  - consume them immediately in the same dynamic region, or
  - call `wasm_restore_vsp` before continuing with single-value assumptions.
- Function epilogues MUST end with balanced spill depth (`0`), so no spill
  frame can leak across control-flow joins or returns.

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
  `_SPfuncall` mirrors the top 3 VSP arguments into `arg_z`, `arg_y`, and `arg_x` for
  ARM‑compatible calling semantics.
- Single‑value return uses `arg_z` with `nargs = 1`. Multi‑value returns
  remain Tier‑1 (values on VSP + `nargs` count).
- `_SPfuncall` resolves `nfn` (symbol → fcell, function → entrypoint) and
  dispatches via `call_indirect` using the entrypoint index.

### Boot Entry Stub (Bring‑Up)

- Minimal boot images may point `%toplevel-function%` at a stub function object.
- The stub entrypoint is a **table index**; current bring‑up uses **index 200** (validated by the ABI contract — see `WASM_BOOT_ENTRY_INDEX` in `abi-constants.mjs`).
- The host should install the kernel export `wasm_boot_entry` at that table slot.
- The kernel exports `wasm_get_tcr_toplevel_function` and
  `wasm_set_tcr_toplevel_function` to read/write the per‑TCR toplevel slot
  (`vs_area->high - node_size`). `start_lisp` and `wasm_run_toplevel` will
  use the slot when `%toplevel-function%` is NIL.
- The funcall smoke test uses a second stub entrypoint at **index 201**
  (`wasm_test_entry`) to validate the calling convention. (Validated by ABI contract: `WASM_TEST_ENTRY_INDEX`.)
- The compiler constant-return stub uses **index 202** (`wasm_const_entry`). (Validated by ABI contract: `WASM_CONST_ENTRY_INDEX`.)
  The entrypoint reads the constant from the current function object
  (`uvref` slot 2 / `deref(fn, 3)`), falling back to `wasm_set_const_value`
  if no function object is available.
- Minimal compiled code can import `wasm_return_constant` to set `arg_z` and
  `nargs` without hardcoding TCR offsets. The constant-only codegen uses this
  helper and exports the entrypoint as `ccl_const_entry`.
- Minimal fixnum add code can import `wasm_return_fixnum_add` to consume
  `arg_z`/`arg_y` (as fixnums) and return a single fixnum in `arg_z`.
- Minimal fixnum sub code can import `wasm_return_fixnum_sub` to consume
  `arg_z`/`arg_y` (as fixnums) and return a single fixnum in `arg_z`.
- Minimal fixnum mul code can import `wasm_return_fixnum_mul` to consume
  `arg_z`/`arg_y` (as fixnums) and return a single fixnum in `arg_z`.
- Minimal fixnum ash code can import `wasm_return_fixnum_ash` to consume
  `arg_z`/`arg_y` (as fixnums) and return a single fixnum in `arg_z`.
- Minimal fixnum logand/logior/logxor code can import `wasm_return_fixnum_logand`,
  `wasm_return_fixnum_logior`, or `wasm_return_fixnum_logxor` to operate on
  `arg_z`/`arg_y` and return a single fixnum in `arg_z`.
- Minimal fixnum lognot code can import `wasm_return_fixnum_lognot` to operate
  on `arg_z` and return a single fixnum in `arg_z`.
- Minimal fixnum negation code can import `wasm_return_fixnum_neg` to negate
  `arg_z` and return a single fixnum in `arg_z`.
- Compiled WASM modules can also import lightweight register helpers:
  - `wasm_get_arg_z` / `wasm_get_arg_y` (read incoming arguments)
  - `wasm_get_nargs` (read the raw argument count)
  - `wasm_set_arg_z` / `wasm_set_arg_y` / `wasm_set_arg_x` (update argument registers)
  - `wasm_set_nargs` (set the fixnum argument count)
  - `wasm_set_nfn` (update `nfn`/`Rfn` for `_SPfuncall`)
  - `wasm_set_imm0` (set `imm0` to a LispObj/fixnum)
  - `wasm_get_nfn` (read current function object)
- Multi‑value helpers are available for bring‑up:
  - `wasm_return_values2`, `wasm_return_values3`, `wasm_return_values4`
    set `arg_z`, push values onto the VSP, and set `nargs` (returning the
    primary value).
  - `wasm_vpush` pushes a single LispObj onto the VSP (updates `vsp` + `save_vsp`).
  - `wasm_vpop` pops a single LispObj from the VSP (updates `vsp` + `save_vsp`).
  - `wasm_spill_push` / `wasm_spill_pop` push/pop LispObj values on the WASM
    spill stack used by compiler local spilling (distinct from the VSP).
  - `wasm_get_mv` returns the Nth value (0‑based, raw index) from `arg_z`/VSP.
  - `wasm_get_mv_indexed` accepts a **fixnum** index and returns the Nth value.
  - `wasm_restore_vsp` pops extra values when `nargs > 1` and resets VSP.
- Compiled modules can perform Lisp calls via:
  - `wasm_funcall0`, `wasm_funcall1`, `wasm_funcall2` (function object +
    0–2 arguments). These helpers set up VSP/nargs and call `_SPfuncall`
    internally, returning the primary value and discarding extra values.
  - `wasm_funcall0_mv`, `wasm_funcall1_mv`, `wasm_funcall2_mv` preserve
    multiple values on the VSP for mv‑pass contexts.

### Compiled Module Registry (Bring‑Up)

- The nilreg symbol `%wasm-compiled-modules%` is reserved to hold a registry
  of compiled WASM modules embedded in the image.
- The kernel exports `wasm_get_compiled_module_registry` to return the current
  value of that symbol (LispObj). The host can use this to discover modules
  after `wasm_ccl_load_image`.
- The registry is a list of **simple vectors**. Each entry vector has 4 slots:
  1) `module-bytes` (u8 vector), 2) `export-name` (string),
  3) `entry-index` (fixnum), 4) `module-version` (fixnum).
  A 5th optional slot MAY be present: `const-pool-bytes` (u8 vector, see
  `doc/wasm/const-pool.md`).

- The kernel exports `wasm_const_pool_install(entry_index, ptr, len)` to
  install a constant pool for a compiled module and `wasm_const_pool_ref` for
  lookup from generated code.

**Overflow note (bring‑up):** the fixnum arithmetic helpers allocate bignums
via a minimal WASM heap allocator. Add/sub/neg and 64‑bit products produce
**1–2 digit bignums**, while large `ash` shifts can produce **arbitrary‑digit
bignums** (including negative values via two’s‑complement digits). `_SPfix_overflow`
and `_SPmakes32` are implemented in both the kernel and provider; the provider
imports the kernel’s `wasm_box_signed_64` helper for bignum allocation. Full
bignum support (arbitrary digits beyond fixnum‑derived ops, GC integration)
remains pending.

### Non‑local Transfer (Tier‑0, cooperative unwind)

- `_SPnthrow1value` unwinds the catch chain and restores TCR state, then sets
  `tcr->wasm_pending_throw` to a non‑zero fixnum. The single value remains in
  `arg_z` with `nargs = 1`; VSP is restored to the target catch frame’s
  `save_vsp`.
- **Generated code MUST** check `tcr->wasm_pending_throw` after calls and
  propagate the unwind by returning without further work.
- The catch cleanup point **MUST** clear `tcr->wasm_pending_throw` once control
  is re‑established.
- Compiled modules may use `wasm_clear_pending_throw` to clear the pending-throw
  flag after a successful `nthrow`-based exit from a local catch.
- Unwind‑protect frames are Tier‑1 (cooperative). Generated code should branch
  to cleanup on `pending_throw`, run the cleanup form, then propagate the
  pending throw. Current bring‑up preserves the **primary** value only.

## Migration Implications

The following changes will be required (no code included here):

- Any place that computes a subprim address via `SUBPRIMS_BASE` must instead treat the subprim value as **an index**.
- Any "PC-in-subprims-range" checks must be reworked for WASM.
- `dev` profile compiler output continues to use dispatcher/table-index paths.
- `fast` profile compiler output may use direct subprim imports for allowlisted
  hot paths, with module-level `0x11` opcode gating.

## ABI Contract Validation

All tag constants, struct layouts, kernel opcodes, boot entry indices, and
named subprim indices are validated at build time by the ABI contract system:

- **C:** `_Static_assert` in `build/wasm32/abi-validate.h` (included via `wasm-constants-bridge.h`)
- **Lisp:** Load-time `assert` in `build/wasm32/abi-validate.lisp` (loaded from `wasm-arch.lisp`)
- **JS:** Constants imported from generated `scripts/wasm/lib/abi-constants.mjs`
- **Python:** Constants imported from generated `build/wasm32/abi_constants.py`

The canonical source is C headers; the generator is `scripts/wasm/generate_abi_contract.py`.
Any constant drift is caught at compile time (C) or load time (Lisp) with a diagnostic
message identifying the mismatched value.

## Status

- Header added: `lisp-kernel/wasm-subprims.h` (dispatcher declaration and helpers).
- Runtime now implements `call_indirect` and imports the WASM table.
- Post-MVP2 profile split (`dev` vs `fast`) is now part of the ABI planning
  contract.
- ABI contract system validates all cross-language constants at build time.
