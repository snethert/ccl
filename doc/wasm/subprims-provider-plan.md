# Subprims Provider Plan (WASM)

**Status:** Draft  
**Scope:** Minimal subprims provider required to reach `toplevel-loop` and yield
cleanly to the host in the WASM bring-up path.

## Decision: C-compiled WASM first, hand-optimized later

We will implement the first provider as **C-compiled WASM** for correctness and
iteration speed, with the explicit intent to **replace hot subprims** later with
hand-optimized WASM (by inspecting clang’s output and removing inefficiencies).

**Rationale:** C-compiled WASM gets us a working baseline quickly; we can then
profile and selectively replace hot subprims with hand-written versions once the
runtime is stable.

**Note on layout choice:** The PPC32 catch-frame layout does not map to any
currently compiled WASM codepaths, so the initial implementation follows the
ARM layout (as described in `lisp-kernel/arm-constants.s`) for consistency with
the existing WASM32 bring-up configuration.

## Minimal entry target (current milestone)

**Goal:** `start_lisp` reaches `toplevel-loop` and returns cleanly to the host
via the existing `:wasm-yield` path (see `level-1/l1-readloop-lds.lisp:20`).

**Important dependency:** This requires **at least one compiled Lisp function**
that can be invoked by `_SPfuncall` (i.e., real WASM-emitted code + a compatible
image). Without a WASM code generator or seed image, `toplevel-loop` cannot do
real work beyond the subprim boundary.

## Required subprims (tiered)

### Tier 0 (must-have for `toplevel-loop`)

These are directly referenced by `toplevel_loop` in `arm-spentry.s` and
`x86-subprims64.s`:

1. **`_SPmkcatch1v`**  
   - Creates a catch frame for tag in `arg_z` and links it into `tcr->catch_top`.
   - Mirrors ARM semantics in `lisp-kernel/arm-spentry.s:652`.

2. **`_SPfuncall`**  
   - Calls the function in the current function register (`nfn`/`fn`) with
     `nargs` arguments on the VSP.
   - Mirrors ARM semantics in `lisp-kernel/arm-spentry.s:409`.

3. **`_SPnthrow1value`**  
   - Unwinds to the catch frame for the tag on the VSP (see `throw`/`nthrow1v`).
   - Mirrors ARM semantics in `lisp-kernel/arm-spentry.s:681` and
     `lisp-kernel/arm-spentry.s:4404`.

### Tier 1 (likely needed immediately after Tier 0 works)

4. **`_SPthrow`**  
   - Full throw (multi-value) path, used by Lisp error handling and restarts.
   - ARM reference: `lisp-kernel/arm-spentry.s:652`.

5. **`_SPnthrowvalues`**  
   - Multi-value unwind path (often paired with `_SPthrow`).
   - ARM reference: `lisp-kernel/arm-spentry.s:672`.

6. **`_SPmkcatchmv`**  
   - Multi-value catch variant; required by some unwind paths.
   - ARM reference: `lisp-kernel/arm-spentry.s` (see `mkcatchmv`).

## Required runtime state / invariants

The provider will assume the **ARM-style TCR layout** (used by WASM32 bring-up):

- `tcr->save_vsp`, `tcr->save_tsp` (stack pointers)
- `tcr->catch_top` (catch frame chain)
- `tcr->valence` (foreign vs lisp)
- `tcr->last_lisp_frame` (manual cstack frames)

The provider must also respect:

- **VSP/TSP stack frame layouts** (`arm-constants.h` catch frame format).
- **Manual cstack frames** via `wasm_enter_lisp_frame` / `wasm_exit_lisp_frame`.
- **GC visibility**: catch frames and values pushed to VSP/TSP must be traceable.

## WASM register file ABI (proposal)

To implement Tier 0 subprims in C, we need a concrete register file model.
Proposed approach:

- Add `tcr->wasm_gprs[16]` for the ARM-style GPR set (`imm0..Rpc`).
- Use existing ARM register index macros (`arg_z`, `nargs`, `Rfn`, etc.) as
  indices into this array.
- Treat `tcr->save_vsp` / `tcr->save_tsp` as the canonical VSP/TSP pointers.

## Provider module design (MVP)

**Module:** `subprims.wasm` (built separately from the kernel)

**Imports:**
- `env.memory`
- `env.__indirect_function_table`
- `ccl.wasm_get_current_tcr` (from kernel)

**Exports:**
- `_SPmkcatch1v`, `_SPfuncall`, `_SPnthrow1value` (Tier 0)
- Tier 1 as they are implemented

**Table wiring:**
- JS installs provider exports into the shared table using
  `doc/wasm/subprims-map.json`.
- After installing a real provider, host sets `wasm_set_subprims_ready(1)`.

## Implementation notes per subprim (guidance)

### `_SPmkcatch1v`
- Allocate a `catch_frame` on TSP.
- Set `catch_tag`, `link`, `csp`, and metadata per ARM layout.
- Update `tcr->catch_top`.

### `_SPfuncall`
- Use `nfn`/`fn` register semantics consistent with ARM.
- Consume `nargs` and arguments on VSP.
- Enter the function’s codevector entrypoint (ABI to be defined by codegen).

### `_SPnthrow1value`
- Implement the unwind loop (`nthrow1v` in ARM).
- Run unwind-protects as required.
- Restore VSP/TSP and continue at catch target.

## Verification checklist (for Step 3)

- **Provider module loads** and table entries are installed (`installSubprimsTable`).
- `wasm_set_subprims_ready(1)` toggles correctly (already supported).
- A minimal host-driven flow can:
  1) enter `start_lisp`,  
  2) reach `toplevel-loop`,  
  3) return via `:wasm-yield` without trapping.

## Open dependencies (tracked)

- **WASM codegen** for Lisp functions (needed for `_SPfuncall` to do real work).
- A **WASM-compatible seed image** to provide the toplevel function.
