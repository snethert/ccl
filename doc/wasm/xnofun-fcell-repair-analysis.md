# XNOFUN Startup Errors — Root Cause Analysis & Fix Plan

## Symptom

After Phase 3 deterministic startup (`load-image.mjs`), `wasm_ccl_start_lisp` catches two
Lisp-level XNOFUN (code=13) errors before returning rc=0:

```
funcall-err: code=13 sym=RUNTIME-BRIDGE-PUMP-COMMANDS fcell=0x0027f006
funcall-err: code=13 sym=%ERR-DISP fcell=0x0027f006
```

Both symbols have the same `fcell=0x0027f006`, which is the FALSE stub (a 3-slot function
vector with entry index 1410). Calling FALSE triggers XNOFUN because it is the
"no-op unbound function" installed by the UDF patch during image build.

---

## Key Facts Established

### Function table entries ARE correct at load time

`startup-plan.json` namedFunctions and module entries:

| Symbol | Entry Index | In module entries? |
|---|---|---|
| RUNTIME-BRIDGE-PUMP-COMMANDS | 6679 | YES — filled at load time |
| %ERR-DISP | 8314 | YES — filled at load time |
| TOPLEVEL-LOOP | 6573 | YES — filled at load time |

All three are in the 202–8971 module range, covered by the 8675 entries filled
from `modules.bin` at startup. The WASM function table is correct.

### The SYMBOL FCELLS are wrong, not the table

Both symbols have `fcell = FALSE stub (0x0027f006)` baked into `root.image`. At
load time, fcells are restored as-is. Even though entry 6679 and 8314 are filled
in the table, the symbols' fcells don't point to function objects with those entries.

### Both functions ARE defined in level-1 source

- `%ERR-DISP` — `defun` at `level-1/l1-error-signal.lisp:30`
- `RUNTIME-BRIDGE-PUMP-COMMANDS` — `defun` at `level-1/l1-readloop-lds.lisp:1320`
  (inside `#+wasm32-target` progn starting at line 474)

---

## Root Causes

### Cause 1: `l1-error-signal.lafsl` missing from requiredFasls

`make-real-image.mjs` loads FASLs from `requiredFasls` (line 1417). This list
includes `l1-error-system.lafsl` but NOT `l1-error-signal.lafsl`.

The FASL `build/wasm32/l1-fasls/l1-error-signal.lafsl` (653 bytes) exists and
was compiled on Mar 3 04:06 — same rebuild session. But it is never loaded.
Therefore `(defun %err-disp ...)` never executes, and the fcell stays as
FALSE (from the UDF patch).

**Fix**: Add `"l1-fasls/l1-error-signal.lafsl"` before `"l1-fasls/l1-error-system.lafsl"`
in `requiredFasls`.

### Cause 2: `runtime-bridge-pump-commands` fcell not persisted (mechanism TBD)

`l1-readloop-lds.lafsl` IS in `requiredFasls`. It should define the function.
Yet fcell is still FALSE in the saved image. The mechanism is unclear.

Three candidate explanations (not yet disambiguated):

**Candidate A — FASL progn fails before defun**
The `#+wasm32-target` progn (lines 474–1334) has many forms before
`defun runtime-bridge-pump-commands` at line 1320. If any earlier form
(e.g., a `defconstant` with a conflicting value) signals an error that is
caught at the FASL top level, the progn may abort. The defun at line 1320
never runs. The FASL returns rc=0 (error caught), and the build continues
without noticing the skipped definition.

**Candidate B — GC doesn't trace level-1 fcells**
The FASL does define the function (fcell is updated). Then `wasm_trigger_gc()`
runs before save. If the GC has a bug where it doesn't trace or forward
fcells for "young" or "late-allocated" function objects, those objects are
freed. The fcell in the saved image points to freed memory, which by
coincidence or reuse resolves to the FALSE stub at `0x0027f006`.

**Candidate C — Image fixup second pass overwrites FASL-defined fcells**
The UDF patch (lines 1396–1410 in make-real-image.mjs) runs BEFORE FASL
loading and only patches fcells pointing to entry-131 pseudofunctions.
However, if any subsequent step scans and re-patches functions, it could
overwrite FASL-defined fcells. This seems unlikely given the code structure,
but has not been ruled out.

---

## Available Kernel Repair Exports

Two kernel exports can repair fcells at any point after `wasm_ccl_load_image`:

```c
// Repairs ONE symbol — only if fcell == nrs_UDF.vcell (NOT false)
int32_t wasm_repair_udf_binding(uint32_t name_ptr, uint32_t name_len,
                                uint32_t entry_index);

// Force-rebinds ALL matching symbols unconditionally, regardless of current fcell.
// Walks all non-stack memory areas.
// Table format: [name_offset:u32, name_len:u32, entry_index:u32] × count
int32_t wasm_force_rebind_scan(uint32_t table_ptr, uint32_t table_count);
```

`wasm_force_rebind_scan` is exactly what we need: it overwrites regardless of
current fcell value. It was designed for "pre-restore-lisp-pointers" use when
fcells have stale build-phase bindings.

---

## Proposed Fix Strategy

### Fix A — Build time (make-real-image.mjs): `l1-error-signal.lafsl`

Add to `requiredFasls` BEFORE `l1-error-system.lafsl`:
```javascript
"l1-fasls/l1-error-signal.lafsl",
"l1-fasls/l1-error-system.lafsl",
```

This directly fixes `%err-disp`. Requires rebuild.

### Fix B — Build time (make-real-image.mjs): post-FASL force-rebind

After the `requiredFasls` loop (line 1798), add a `wasm_force_rebind_scan`
pass over ALL `compiledModulesBundle.functions` that still have FALSE fcells:

```
After requiredFasls loop:
  For each fn in compiledModulesBundle.functions:
    If fn's symbol fcell == FALSE (not a true compiled function)
    → call wasm_force_rebind_scan to patch it to the correct entry
```

This catches `runtime-bridge-pump-commands` and any others that slip through.

The JS-side image fixup code (lines 1291–1414) already does equivalent heap
scanning in JavaScript — the post-FASL pass would instead call the kernel's
`wasm_force_rebind_scan` which is faster and handles the Lisp memory model correctly.

### Fix C — Load time (load-image.mjs): runtime repair using startup-plan.json

After filling module table entries and before `wasm_set_subprims_ready`, call
`wasm_force_rebind_scan` with the `namedFunctions` from `startup-plan.json`:

```
After filling 8675 module table entries:
  Write name strings to scratch area (bottom of cstack: memory.buffer.byteLength - cstackSize)
  Write packed table [name_ptr, name_len, entry_index] for each namedFunction
  Call wasm_force_rebind_scan(tablePtr, tableCount)
  → repairs any symbol whose fcell != a valid function
```

This fixes the CURRENT root.image without rebuilding. No rebuild required.
Downside: adds ~100ms and some complexity to load-image.mjs, partially
undoing the Phase 3 "zero load-time fixup" goal.

### Recommended approach

**Short term**: Fix C in load-image.mjs (fixes current image immediately, no rebuild).
**Long term**: Fixes A + B in make-real-image.mjs (bakes correct fcells into future images).

---

## Files to Modify

| File | Change | Priority |
|---|---|---|
| `scripts/wasm/lib/load-image.mjs` | Add wasm_force_rebind_scan after table fill | Short-term fix |
| `scripts/wasm/lib/make-real-image.mjs` | Add l1-error-signal.lafsl + post-FASL force-rebind | Long-term fix |

---

## Open Question for CODEX Review

The mechanism behind Candidate A/B/C for `runtime-bridge-pump-commands` is still
unclear. CODEX is asked to provide a read-only analysis (see `doc/wasm/codex-letter-xnofun.md`).

---

## References

- `level-1/l1-error-signal.lisp:30` — `(defun %err-disp ...)`
- `level-1/l1-readloop-lds.lisp:474–1334` — `#+wasm32-target` progn
- `level-1/l1-readloop-lds.lisp:1320` — `(defun runtime-bridge-pump-commands ...)`
- `scripts/wasm/lib/make-real-image.mjs:1249–1414` — image fixup + UDF patch
- `scripts/wasm/lib/make-real-image.mjs:1417–1457` — requiredFasls list
- `lisp-kernel/wasm-kernel-stubs.c:6484–6563` — `wasm_repair_udf_binding`
- `lisp-kernel/wasm-kernel-stubs.c:6575–6770` — `wasm_repair_udf_bindings_scan` / `wasm_force_rebind_scan`
- `lisp-kernel/lisp_globals.h:144` — `nrs_ERRDISP (nrs_symbol(2))` — `%err-disp` is an NRS symbol
- `build/wasm32/images/startup-plan.json` — namedFunctions[RUNTIME-BRIDGE-PUMP-COMMANDS]=6679, [%ERR-DISP]=8314
