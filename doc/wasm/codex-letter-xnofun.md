# Analysis Request: WASM CCL XNOFUN Startup Errors

**To**: CODEX (OpenAI)
**From**: CCL WASM engineering (via Claude Code)
**Task type**: READ-ONLY analysis and recommendations. Do NOT modify files.
**Scope**: `ccl/` repository. Focus areas enumerated below.

---

## Background

CCL (Clozure Common Lisp) has a WASM32 backend. A deterministic startup launcher
(`scripts/wasm/lib/load-image.mjs`) loads a pre-built Lisp image (`root.image`,
~2.1 GB), fills a WASM function table from a `startup-plan.json` manifest, and
calls `wasm_ccl_start_lisp`. Two Lisp-level XNOFUN errors appear at startup:

```
funcall-err: code=13 sym=RUNTIME-BRIDGE-PUMP-COMMANDS fcell=0x0027f006
funcall-err: code=13 sym=%ERR-DISP fcell=0x0027f006
```

Both are caught non-fatally by an outer catch frame; `wasm_ccl_start_lisp` returns 0.
But they indicate broken function bindings that will impair the running toplevel.

---

## Established Facts (read these first)

Full analysis is at `doc/wasm/xnofun-fcell-repair-analysis.md`. Summary:

1. **Table entries are correct.** `startup-plan.json` has entries 6679 and 8314
   for the two functions, both in the module range (202–8971). They ARE filled
   at load time from `modules.bin`.

2. **Symbol fcells are wrong.** Both symbols have `fcell=0x0027f006` = FALSE stub
   (a 3-slot function with entry 1410, the "unbound" sentinel). These stale
   fcells are baked into `root.image` at build time.

3. **`%err-disp`** — `(defun %err-disp ...)` is in `level-1/l1-error-signal.lisp:30`.
   The file `build/wasm32/l1-fasls/l1-error-signal.lafsl` (653 bytes) exists but
   is NOT in the `requiredFasls` list in `scripts/wasm/lib/make-real-image.mjs`.
   The defun never executes. Fcell stays FALSE.

4. **`runtime-bridge-pump-commands`** — `(defun runtime-bridge-pump-commands ...)`
   is inside the `#+wasm32-target` progn in `level-1/l1-readloop-lds.lisp` at
   line 1320. The FASL `build/wasm32/l1-fasls/l1-readloop-lds.lafsl` IS in
   `requiredFasls` and IS loaded. Yet the symbol's fcell is still FALSE.
   **Root cause of this case is unknown.**

5. **Build sequence in `make-real-image.mjs`**:
   ```
   1. Load boot image (wasm-boot.image)
   2. Install compiled modules from modules.bin (fills WASM table)
   3. Image fixup pass 1: patch boot-module symbol fcells (bootNamedFunctions only)
   4. Image fixup pass 2 (UDF patch): replace fcells pointing to entry-131 UDF
      pseudofunctions with FALSE stub (entry 1410)
   5. Run cold-boot-init (wasm_run_cold_boot_init)
   6. Load requiredFasls via wasm_fasload_path
   7. wasm_restore_lisp_pointers()
   8. Phase 2A: proactive const pool install
   9. wasm_reset_root_image_runtime_state() → clears nrs_WASM_COMPILED_MODULES.vcell
   10. wasm_set_toplfunc_entry(toplevelEntryIndex)
   11. wasm_trigger_gc() — compacting GC
   12. wasm_save_image_direct() → saves root.image
   ```

6. **Kernel repair exports** available after `wasm_ccl_load_image`:
   ```c
   // Repairs only if fcell == nrs_UDF.vcell:
   int32_t wasm_repair_udf_binding(uint32_t name_ptr, uint32_t name_len, uint32_t entry_index);

   // Force-rebinds all matching symbols unconditionally:
   int32_t wasm_force_rebind_scan(uint32_t table_ptr, uint32_t table_count);
   ```
   `wasm_force_rebind_scan` is at `lisp-kernel/wasm-kernel-stubs.c:6680`.

---

## Proposed Fixes (for your review)

### Fix A (certain): Add `l1-error-signal.lafsl` to requiredFasls
File: `scripts/wasm/lib/make-real-image.mjs`
Location: `requiredFasls` array, around line 1448
Change:
```javascript
  "l1-fasls/l1-error-signal.lafsl",   // ADD THIS
  "l1-fasls/l1-error-system.lafsl",
```
Effect: `(defun %err-disp ...)` will run during FASL loading, setting the fcell.

### Fix B (uncertain): Post-FASL `wasm_force_rebind_scan` in make-real-image.mjs
After the `requiredFasls` loop (around line 1798 in `make-real-image.mjs`), add
a `wasm_force_rebind_scan` pass over all `compiledModulesBundle.functions`. This
would catch any symbol whose fcell is still FALSE or UDF after FASL loading.
The scan requires writing a packed table into WASM memory (the same format used
by `wasm_force_rebind_scan`'s `table_ptr` argument).

### Fix C (load-time workaround): `wasm_force_rebind_scan` in load-image.mjs
In `scripts/wasm/lib/load-image.mjs`, after filling module table entries and
before `wasm_set_subprims_ready`, call `wasm_force_rebind_scan` using
`plan.namedFunctions` from startup-plan.json. Write names and the packed table
to the bottom of the cstack area (WASM address: `memory.buffer.byteLength - cstackSize`),
which is available at that point (Lisp hasn't started, cstack unused).

This fixes the CURRENT root.image without a rebuild but partially undoes the
Phase 3 "zero load-time fixup" architectural goal.

---

## Questions for CODEX Analysis

Please analyze the following questions with READ-ONLY access. Provide citations
with file:line_number for all findings. Do NOT edit any files.

### Q1: Why is `runtime-bridge-pump-commands` still unbound after FASL loading?

Inspect `scripts/wasm/lib/make-real-image.mjs` steps 3–6 above.
Specifically:
- Does the UDF patch (step 4) run BEFORE or AFTER FASL loading (step 6)?
  If BEFORE, the comment "FASL loading overwrites" should hold. Verify by line number.
- Can `wasm_fasload_path` return rc=0 even if a form within the FASL signals an error?
  Read `lisp-kernel/wasm-kernel-stubs.c` around `wasm_fasload_path` (line ~4910) and
  its catch frame setup.
- Does `l1-readloop-lds.lisp`'s `#+wasm32-target` progn (lines 474–1334) have any
  form that could fail during FASL execution in the make-real-image.mjs environment
  BEFORE reaching `defun runtime-bridge-pump-commands` at line 1320?
- Could `wasm_reset_root_image_runtime_state()` (step 9) or the GC (step 11) cause
  the function object created by FASL's `defun` to become unreachable and collected?
  Read `lisp-kernel/wasm-kernel-stubs.c:6772` and the GC's treatment of symbol fcells.

### Q2: Is the NRS symbol `%err-disp` a special case?

`lisp_globals.h:144`: `#define nrs_ERRDISP (nrs_symbol(2))  /* %err-disp */`
This places `%err-disp` in the kernel's "named root symbol" area at a fixed address.
- Is `nrs_ERRDISP` the same object as the heap-interned `%err-disp` symbol, or
  is it a separate object that gets synced?
- Does `wasm_ccl_load_image` restore `nrs_ERRDISP.fcell` from the saved image,
  or does it reset to a default (UDF pseudofunction)?
- If Fix A (adding `l1-error-signal.lafsl`) causes `defun %err-disp` to run,
  does the defun update `nrs_ERRDISP.fcell`, the heap symbol's fcell, or both?

### Q3: Is Fix C (load-time `wasm_force_rebind_scan`) safe and correct?

Read `lisp-kernel/wasm-kernel-stubs.c:6680` (`wasm_force_rebind_scan`).
- Is it safe to call `wasm_force_rebind_scan` at the point in `load-image.mjs`
  after `wasm_ccl_load_image` + table fill + before `wasm_set_subprims_ready`?
- Does it correctly handle `%err-disp` as an NRS symbol (i.e., will it find and
  patch the symbol in the loaded image's memory areas)?
- The function only matches `subtag_simple_base_string` pnames. Are there any
  WASM CCL symbols with `subtag_simple_general_string` (wide-char) pnames that
  would be missed? Would `%err-disp` or `runtime-bridge-pump-commands` be missed?

### Q4: Is Fix B (post-FASL force-rebind in make-real-image.mjs) correct?

- After FASL loading (step 6), is it safe to call `wasm_force_rebind_scan`?
  What Lisp invariants must hold for the call to be safe?
- The function allocates new function objects via `wasm_misc_alloc`. Will these
  be tracked by the subsequent GC (step 11)?
- If `wasm_force_rebind_scan` is called after FASL loading but BEFORE the GC,
  will the allocated function objects survive the GC?

### Q5: Are there other symbols with the same problem?

Scan `scripts/wasm/lib/make-real-image.mjs`'s `requiredFasls` list (lines 1417–1457)
against the level-1 source files and determine: are there other `defun` forms in
these FASLs that might be failing to set fcells for the same or related reasons?
Specifically look for functions that:
- Are inside `#+wasm32-target` progns in source
- Are called early in the startup sequence (toplevel, error handling, etc.)

### Q6: Architectural alternative — bake fcells at build time via post-FASL JS scan

The existing image fixup in `make-real-image.mjs` (lines 1291–1414) does a
JavaScript-level scan of WASM memory to find and patch symbol fcells. This scan
uses `bootNamedFunctions` only (intentionally excludes level-1 functions).
- Could this JS-level scan be extended to run AFTER FASL loading with all
  named functions to catch level-1 symbols with bad fcells?
- What are the risks of patching level-1 function fcells via the JS scan
  (which allocates new function objects using `malloc`) vs using the kernel's
  `wasm_force_rebind_scan` (which uses `wasm_misc_alloc`)?
- Is there a difference in how the GC would treat function objects allocated
  via `malloc` vs `wasm_misc_alloc`?

---

## Key Files for Analysis

```
level-1/l1-error-signal.lisp                          — defun %err-disp (line 30)
level-1/l1-readloop-lds.lisp                          — defun runtime-bridge-pump-commands (line 1320)
                                                         #+wasm32-target progn (lines 474–1334)
level-1/l1-boot-3.lisp:45                             — (setq %err-disp %xerr-disp) — what does this do?
scripts/wasm/lib/make-real-image.mjs:1249–1414        — image fixup (UDF patch, bootNamedFunctions only)
scripts/wasm/lib/make-real-image.mjs:1417–1457        — requiredFasls list (MISSING l1-error-signal)
scripts/wasm/lib/make-real-image.mjs:1524–1797        — FASL loading loop
scripts/wasm/lib/make-real-image.mjs:1846–1907        — reset, GC, save
scripts/wasm/lib/load-image.mjs                       — Phase 3 load-time launcher (314 lines)
lisp-kernel/wasm-kernel-stubs.c:4910                  — wasm_fasload_path implementation
lisp-kernel/wasm-kernel-stubs.c:6484                  — wasm_repair_udf_binding
lisp-kernel/wasm-kernel-stubs.c:6575                  — wasm_repair_udf_bindings_scan
lisp-kernel/wasm-kernel-stubs.c:6680                  — wasm_force_rebind_scan
lisp-kernel/wasm-kernel-stubs.c:6772                  — wasm_reset_root_image_runtime_state
lisp-kernel/lisp_globals.h:144                        — nrs_ERRDISP definition
build/wasm32/images/startup-plan.json                 — namedFunctions, functionTable.entries
build/wasm32/l1-fasls/l1-error-signal.lafsl           — 653 bytes, exists but not loaded
build/wasm32/l1-fasls/l1-readloop-lds.lafsl           — 6783 bytes, in requiredFasls
```

---

## Constraints for CODEX Response

- READ-ONLY. Do not modify any files. Do not suggest patches as diffs.
- Cite specific file:line_number for every claim.
- For each question (Q1–Q6), provide a clear CONCLUSION (YES/NO/UNCLEAR)
  followed by supporting evidence.
- If the root cause of Q1 is identified with high confidence, say so explicitly.
- Flag any additional risks or edge cases not covered by the proposed fixes.
- Format the response as a structured report (one section per question).
