# Codex Read-Only Analysis Request: CCL WASM Image Size Reduction & Startup Architecture

**Mode: READ-ONLY ANALYSIS ONLY. Do not modify any files. Do not write patches.**

**Constraint: Report only facts. Do not speculate. Trace actual code paths and report what you find. Code examples in the report are fine, but no files should be changed.**

---

## The System

Clozure Common Lisp (CCL) compiled to WASM32, running inside a Node.js host. Two deployment phases:

- **Build time** (`make-real-image.mjs`): Assembles a root.image from a boot image, ~8,600 compiled WASM modules, and level-1 FASL files.
- **Launch time** (`load-image.mjs`): Loads root.image into WASM memory, fills the function table from a startup plan, and starts Lisp.

Key files:

| File | Role |
|------|------|
| `scripts/wasm/lib/make-real-image.mjs` | Build pipeline — module install, GC, const pools, image save |
| `scripts/wasm/lib/load-image.mjs` | Runtime launcher — image load, table fill, on-demand const pools |
| `lisp-kernel/wasm-kernel-stubs.c` | C kernel stubs — `wasm_trigger_gc`, `wasm_save_image_direct`, `wasm_const_pool_purge_all`, `wasm_force_rebind_scan` |
| `lisp-kernel/wasm32/Makefile` | Kernel linker flags (including `--table-base=256`) |
| `scripts/wasm/rebuild-everything.sh` | Top-level rebuild orchestrator |
| `scripts/wasm/lib/ccl-loader.mjs` | Module instantiation, const pool install, subprims table |

---

## What Changed (March 1–7, 2026)

Between commits `7359c70a` (Phase 2) and `40af098c` (latest), we made 8 commits attempting to reduce the image from 435 MiB to < 5 MiB and achieve deterministic startup. Here is every significant change, in chronological order:

### Change 1: Function-table collision fix (`553ded6a`)

**Problem:** Both `wasmcl.wasm` (kernel) and `subprims.wasm` were linked without `--table-base`, so `wasm-ld` assigned C function-pointer indices starting at 1. `installSubprimsTable()` then overwrote indices 0–136 with subprim functions, silently clobbering the kernel's C function pointers (`markhtabvs`, `mark_weak_htabv`, etc.). When `gc()` called `markhtabvs()` via `call_indirect`, it dispatched to `_SPbuiltin_gt` instead, causing `misc_ref` crash on non-misc object during cold-load drain.

**Fix:** Added `--table-base=256` to both Makefiles. Changed `subprimsTableInitial` from 256 to 512 across 36 JS files.

**Risk assessment:** This was a silent corruption bug. The fix is mechanical but touches many files. If any caller still uses `subprimsTableInitial: 256`, function pointers above index 256 won't have table slots.

### Change 2: Pre-save GC in `wasm_save_image_direct` (`d7e54001`)

**Problem:** Without GC before save, the image includes all dead heap data from the build — 3–5x bloat.

**Fix:** Added `wasm_trigger_gc()` call inside `wasm_save_image_direct` in C, after disabling EGC, before calling `save_application()`.

**Risk:** The GC runs with EGC disabled, so the entire heap is one contiguous area. This is the correct state for `save_application`. However, this GC is *in addition to* the JS-side pre-save GC (line 1977 of make-real-image.mjs). The image is now GC'd twice before save — once from JS, once from C. This is wasteful but not incorrect.

### Change 3: Post-module-install GC (`a6144e84`)

**Problem:** After installing ~8,600 compiled modules, the heap balloons to several GB of mostly garbage from WASM module instantiation. Any subsequent Lisp execution triggers a full mark-sweep-compact GC on this bloated heap.

**Fix:** Added explicit `ex.wasm_trigger_gc()` call at make-real-image.mjs line 1799, right after module installation completes.

**Risk:** None identified. This is a straightforward compaction before further work.

### Change 4: Skip proactive const-pool install (`bda1d865`)

**Problem:** The proactive const-pool installation loop tried to install ~7,000 pools into the Lisp heap during build. Each install allocates Lisp objects and can trigger full GC. With a multi-GB heap in interpreted WASM, this is O(n²) total GC work and took hours.

**Fix:** Skip the loop entirely. Only the ~778 pools installed during module instantiation are baked into root.image. The remaining ~7,222 are deferred to launch-time on-demand installation via `wasm_host_install_const_pool` callback.

**What this means for launch:** When Lisp code calls a function whose const pool isn't installed, the kernel calls `wasm_host_install_const_pool(entryIndex)`. The JS host (`load-image.mjs`, lines 226–278) looks up the entry in the startup plan, copies the const pool bytes from `modules.bin` into WASM memory scratch space, and calls `wasm_const_pool_install(entryIndex, ptr, len)`.

**Risk:** This is the biggest architectural question. ~7,222 const pools are NOT in the saved image. They must be installed on-demand at runtime. If:
- `wasm_const_pool_install` fails at runtime (out of memory, heap corruption)
- The callback fires from a context where memory growth is unsafe
- The `modules.bin` file is out of sync with `root.image`

...then startup will fail with obscure errors. The manifest marks this as `constPools.baked: "partial"`.

### Change 5: Skip Lisp save path for partial pools (`419a71e1`)

**Problem:** `%save-application-internal` is a Lisp function. When const pools are partial, its own const pool may not be installed, causing `misc_ref bad tag` crash.

**Fix:** Temporarily clear `wasm_subprims_ready` before `wasm_save_image_direct` so the kernel uses the C-level `save_application` fallback instead of the Lisp path.

**Risk:** The C-level `save_application` may differ from the Lisp `%save-application-internal` in subtle ways (e.g., what it includes in the image, how it handles certain heap objects). We have not verified that the two paths produce identical images.

### Change 6: Skip invariant fcell gate (`40af098c`)

**Problem:** The invariant gate called `wasm_set_symbol_function_entry` for ~4,756 runtime symbols. Each unresolved symbol triggers an O(N) heap scan. With 4,756 × multi-GB heap, this took hours.

**Fix:** Skip entirely. `wasm_force_rebind_scan` (a single heap scan, line 1887) already rebound 3,177 symbols. The remaining ~1,600 are expected to resolve at launch via function table entries.

**Risk:** 1,579 symbols have function cells (fcells) that point to UDF (undefined function) stubs at build time. If any of these symbols are called before their const pool is installed at runtime, the call will trap with `WASM_XFUNBND`. We have no inventory of which symbols are affected or whether they include critical startup paths.

### Change 7: Const pool purge before save (`wasm_const_pool_purge_all`)

**Problem:** Const pool data deep-copies gvectors (classes, instances, slot-vectors) into each pool entry. 7,889 installs create 18.7M gvectors, 38.5M cons, 2.4M function-vectors — ~2 GB of bloat.

**Fix:** `wasm_const_pool_purge_all()` clears all 8,979 pool table entries, then GC reclaims the deep-copied objects. Image: 2,104 MiB → 2.8 MiB.

**Risk:** After purge, ALL const pools must be re-installed at launch (not just the ~7,222 deferred ones). If the purge clears pools that were installed during module instantiation, those 778 "baked" pools are also gone. The code at line 1949 still reports `constPoolsInstalled.size` as "pre-baked in image" — but after purge, none are baked. The manifest says `baked: "partial"`, but reality is `baked: "none"`.

---

## The Build Pipeline (Current State)

```
1. Load boot image into WASM memory
2. Install boot modules (entries 202–1413) into function table
3. Install runtime modules (entries 1421–8971) into function table
4. Image fixup: scan boot-image symbols, patch entry indices
5. wasm_run_cold_boot_init() — cold-load drain
6. FASL loading — 16 level-1 .lafsl files
7. POST-MODULE-INSTALL GC                    ← Change 3
8. RESTORE-LISP-POINTERS (rehash packages)
9. SKIP proactive const pool install         ← Change 4
10. Force-rebind scan (3177 symbols)
11. SKIP invariant fcell gate                ← Change 6
12. Reset root image runtime state
13. Pre-toplfunc GC
14. Set TOPLEVEL-LOOP entry
15. Const pool purge (all 8979 entries)      ← Change 7
16. Pre-save GC (JS side)
17. SAVE IMAGE (C-level fallback)            ← Changes 2, 5
```

---

## Questions for Codex Analysis

### Question 1: Const Pool State Consistency

After step 15 (purge all 8,979 entries) and step 16 (GC), the saved image has zero const pools. At launch, `load-image.mjs` must install every single one on-demand.

**Trace these code paths and answer:**

a) In `wasm_const_pool_purge_all` (`lisp-kernel/wasm-kernel-stubs.c`), what exactly is cleared? Is it just the pool table slot (setting to NIL/NULL), or does it also mark the heap objects for collection? Does the GC know to collect the orphaned pool data?

b) In `load-image.mjs` line 226–278, `installConstPoolOnDemand` calls `wasm_const_pool_install(entryIndex, ptr, len)`. Trace what `wasm_const_pool_install` does in the kernel. Does it allocate new Lisp heap objects? If so, what triggers GC if the heap fills up during bulk on-demand installation at launch?

c) The manifest says `constPools.baked: "partial"` and `constPools.count: 778`. After the purge, this is inaccurate. What does `load-image.mjs` do with this information? Does it affect behavior or is it purely informational?

### Question 2: Force-Rebind Coverage Gap

`wasm_force_rebind_scan` rebound 3,177 of 4,756 runtime symbols. 1,579 symbols were NOT rebound.

**Trace and answer:**

a) In `wasm_force_rebind_scan` (`wasm-kernel-stubs.c`), what causes a symbol to NOT be rebound? Is it because the symbol wasn't found in the heap scan, or because the scan found it but skipped it for some reason?

b) Are any of the 1,579 unbound symbols on the critical startup path? Specifically: are any called by `TOPLEVEL-LOOP`, `%TOPLEVEL-FUNCTION`, or the first few functions in a REPL startup sequence?

c) At launch, how do these 1,579 symbols get their fcells fixed? The invariant gate is skipped. Force-rebind already ran. What mechanism resolves them? Is it purely the on-demand const pool install callback, or is there another path?

### Question 3: Memory Growth During On-Demand Install

`load-image.mjs` lines 203–221 (`ensureScratch`) may grow WASM memory during const pool installation. It calls `wasm_memory_grow_and_relocate` if available.

**Trace and answer:**

a) What does `wasm_memory_grow_and_relocate` do? Does it relocate Lisp heap pointers? If so, does it invalidate any cached pointers held by the kernel or by JavaScript?

b) `ensureScratch` is called from `installConstPoolOnDemand`, which is called from the kernel via `wasm_host_install_const_pool` import. This means memory growth can happen mid-Lisp-execution. Is this safe? Can the kernel's stack frames, registers, or TCR state become invalid if memory grows?

c) The pre-allocated scratch at lines 377–382 attempts to avoid mid-execution growth. But does `maxCpSize` cover all const pools? What if a const pool is larger than any entry in the startup plan?

### Question 4: Double GC Before Save

The image is GC'd twice before save:
1. JS-side: `ex.wasm_trigger_gc()` at make-real-image.mjs line 1977
2. C-side: `wasm_trigger_gc()` inside `wasm_save_image_direct` (from commit d7e54001)

**Trace and answer:**

a) Is the C-side GC in `wasm_save_image_direct` still present? If so, the JS-side GC at line 1977 is redundant — or vice versa.

b) After the JS-side GC (line 1977), `copyBytesToScratch` at line 1982 grows memory. Then `wasm_save_image_direct` is called. Does the C-side GC inside `wasm_save_image_direct` compact correctly even though memory was grown between the two GCs?

### Question 5: Startup Plan Accuracy

The startup plan is generated at build time and consumed at launch time. After the changes above, several plan fields may be stale:

a) `constPools.baked: "partial"` — should this be `"none"` given the purge?

b) `constPools.count: 778` — does this number still mean anything after purge?

c) `memory.initialPages` — this was captured during the build. At launch, `load-image.mjs` uses it to create the WASM memory (line 130) and compute `blobBase` (lines 137–139). If the build-time memory size doesn't match the saved image's expectations, what happens?

d) `functionTable.size` — is 512 sufficient? The build uses ~8,675 entries. Trace how `load-image.mjs` determines the table size and whether it can under-allocate.

### Question 6: Proposed Solution

Based on your analysis of questions 1–5, propose a solution architecture that addresses:

1. **Const pool lifecycle correctness**: How should const pools be managed across build → save → launch to ensure no pools are silently missing?
2. **Startup reliability**: What guarantees should the system provide about symbol resolution before `wasm_ccl_start_lisp` is called?
3. **Memory safety during on-demand install**: What invariants must hold when `wasm_host_install_const_pool` fires mid-execution?
4. **Manifest accuracy**: What fields need updating and what validation should `load-image.mjs` perform?

Code examples are welcome in the proposal. Do not modify any existing files.

---

## File Locations for Reference

```
lisp-kernel/wasm-kernel-stubs.c          — C kernel stubs (search for wasm_const_pool_purge_all, wasm_force_rebind_scan, wasm_save_image_direct, wasm_trigger_gc, wasm_const_pool_install, wasm_memory_grow_and_relocate)
lisp-kernel/gc-common.c                  — GC mark/sweep/compact (const pool marking, NRS forwarding)
lisp-kernel/wasm32/Makefile              — Kernel link flags
scripts/wasm/lib/make-real-image.mjs     — Build pipeline (lines 1794–2050 are the critical section)
scripts/wasm/lib/load-image.mjs          — Launch pipeline (lines 183–382 are on-demand const pool install)
scripts/wasm/lib/ccl-loader.mjs          — installCompiledModulesFromBundle, installConstPoolBytes, installSubprimsTable
scripts/wasm/rebuild-everything.sh       — Full rebuild orchestrator
```

---

## Deliverable

A report with:
1. Factual answers to Questions 1–5 (trace code paths, cite line numbers)
2. A proposed solution architecture for Question 6 (code examples OK, no file modifications)
3. Any additional risks or inconsistencies discovered during the analysis
