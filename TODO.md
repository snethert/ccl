# CCL WASM TODO

<!-- Entry index lookup tool: scripts/wasm/lookup-entry.mjs <index> -->
<!-- Debugging guide: doc/wasm/debugging.md — read first when troubleshooting -->

**Last updated:** 2026-02-18
**Current phase:** MVP-1 (Library/Embedded Mode)
**Plan:** [doc/wasm/deterministic-startup-plan.md](doc/wasm/deterministic-startup-plan.md)

---

## 🚨 ACTIVE WORK — Deterministic Startup Pipeline

Full plan: [deterministic-startup-plan.md](doc/wasm/deterministic-startup-plan.md)

### Phase 0A: All 280+ WASM LAP Bridge Functions ✅

**Goal:** Define WASM equivalents for every ARM LAP function in `level-0/ARM/`.

**Status:** All 12 files implemented (333 defuns across 12 files).

**Files** (in `level-0/WASM/`):
- [x] `wasm-misc.lisp` — 61 functions (atomics, threading, memory, copy)
- [x] `wasm-utils.lisp` — 39 functions (GC, heap, area walking, macptr)
- [x] `wasm-bignum.lisp` — 75 functions (digit arithmetic)
- [x] `wasm-float.lisp` — 48 functions (IEEE754 manipulation)
- [x] `wasm-array.lisp` — 23 functions (boole ops, array access)
- [x] `wasm-hash.lisp` — 11 functions (hash table ops)
- [x] `wasm-numbers.lisp` — 15 functions (fixnum/float ops)
- [x] `wasm-clos.lisp` — 10 functions (slot lookup, trampolines)
- [x] `wasm-symbol.lisp` — 10 functions (symbol ops, hashing)
- [x] `wasm-pred.lisp` — 2 functions (eql, equal)
- [x] `wasm-io.lisp` — 1 function (%get-errno)
- [x] `wasm-def.lisp` — 38 frame/def operations

### Phase 0AA: Unit Tests for LAP Bridge Functions ⚠️

**Goal:** Thorough unit testing of all Phase 0A bridge functions.

**Status:** 144 test functions compile; 0/144 pass at runtime (blocked by FASL regression).

**Files:**
- [x] `scripts/wasm/compile-phase0a-tests.lisp` — 144 test functions
- [x] `scripts/wasm/compile-phase0a-tests.sh` — compilation wrapper
- [x] `scripts/wasm/tests/phase0a-bridge-smoke.mjs` — JS test runner

**Test categories:**
- A: Pure fixnum ops (signum, ilogcount, iash, intlen, truncate, gcd)
- B: Vector ops (copy-gvector, boole-*, init-misc, allocate-list)
- C: Bignum ops (udiv64by32)
- D: Float ops (CLZ, FPU stubs)
- E: String/symbol ops (pname-hash, string-hash)
- S: Stub verification (GC, thread, frame stubs)

**Blocking:** All 144 tests trap at runtime due to FASL loading regression.
Will pass once Phase 0B / FASL fix unblocks runtime execution.

**Bug found:** Uncommitted `defwasm2 wasm2-%fixnum-set` definitions in wasm2.lisp
used non-existent acode operators, breaking cross-compilation loading. Fixed.

---

### Phase 0B: Zero-Relocation Image Base ✅

**Goal:** Image base = `__heap_base`. Bias = 0. No relocation walk.

- [x] Extract `__heap_base` from kernel in `rebuild-everything.sh`
- [x] Make `xwasmfasload.lisp` read image base from env var (`CCL_WASM_IMAGE_BASE`)
- [x] Relocation walk: already a no-op when bias=0 (`image.c:456`)

**How it works:**
- `rebuild-everything.sh` extracts `__heap_base` from `wasmcl.wasm` (via `__stack_pointer` init value in wasm-objdump), aligns to 64KiB (matching kernel's `ReserveMemoryForHeap()`)
- Exports `CCL_WASM_IMAGE_BASE` hex value; `xwasmfasload.lisp` reads it as `:image-base-address`
- At runtime, kernel computes `image_base` from same `__heap_base` → `bias = image_base - ACTUAL_IMAGE_BASE(header) = 0`
- C relocation walk (`relocate_area_contents`) already skips when `bias=0`
- Current kernel: `__heap_base=76592` → aligned `image_base=0x20000`

---

### Phase 1: Verified Build ⚠️

**Goal:** Rebuild with Phase 0 changes. Verify everything works.

- [x] Kernel + subprims build
- [x] All 12 wasm-*.lisp files compile and load (333 bridge functions)
- [x] Boot image written (`wasm-boot.image`)
- [x] 1110 boot modules compiled
- [x] 7557 runtime modules compiled
- [x] Phase 0B image base extraction works (`__heap_base=76592 → 0x20000`)
- [ ] Root image build — fails with `ksignalerr` during cold-boot-init

**Bugs fixed during Phase 1:**
- `GENERAL-AREF2` unimplemented opcode: `%aref2`/`%aref3`/`%aset2`/`%aset3` rewrote to use `row-major-aref` + `array-row-major-index`
- Unclosed paren in `wasm-bignum.lisp` `truncate-guess-loop` (line 695)
- Unclosed paren in `wasm-float.lisp` `%double-float->short-float` (line 369)
- Funcall argument ordering: `wasm_funcall_common` push loop was reversed — vsp[0]=first arg instead of vsp[0]=last arg (ARM convention). Fixed in commit `31d89be7`.
- `%car/%cdr` slot index swap in `wasm2.lisp` — fixed FASL loading regression (fn=0x2c)

**Bugs fixed during Phase 1 (continued):**
- **Arg register convention: aligned to ARM (2026-02-17):** The WASM compiler prologue (`wasm2-arg-prologue-ir`, `wasm2-closed-arg-prologue-ir`) had a porting bug — missing `(reverse req)` from ARM — causing `arg_z = first param` instead of `arg_z = last param`. Fixed prologue to be nargs-aware: for 2-arg functions, first param reads `:arg1` (arg_y), second/last param reads `:arg0` (arg_z). Reverted `wasm_sync_arg_regs_from_vsp` to ARM TOS-based convention (`vsp_ptr[0]` → arg_z). Call-setup sites (`:set-arg0`/`:set-arg1`) were already correct. There is no "WASM convention" — the mapping was a bug.
- **Const pool fixnum boxing (2026-02-17):** `pool_data[i] = (LispObj)raw` stored unboxed fixnums. Fixed to `pool_data[i] = box_fixnum(...)`.

**Bugs fixed during Phase 1 (2026-02-17 sessions 3-4):**
- **`%pname-hash`/`%string-hash` char-code fix:** `(uvref str i)` returns tagged characters, but hash algorithms expect integer codes. Fixed both functions to use `(char-code (uvref str i))`. This resolved the `%KERNEL-RESTART` XFUNBND error during cold-boot-init step 60 (hash table resize).
- **Ivector const pool support:** Added const pool tag 17 (ivector) to both the cross-compiler serializer (`wasm2.lisp`) and C installer (`wasm-kernel-stubs.c`). Specialized arrays (u16-vector, u8-vector, etc.) are now correctly serialized with their target subtags and element data, instead of being flattened to generic simple-vectors.
- **`target::` package resolution bug:** `target::subtag-*` references in `wasm2.lisp` resolved at read time to the HOST x86-64 architecture, not the WASM target. Fixed by using `wasm::subtag-*` directly. Also added TARGET package nickname redirect to `build-wasm-boot.lisp` as a safety measure.

**Bugs fixed during Phase 1 (2026-02-17 session 5):**
- **Subprims .rodata data segment collision:** Both kernel (`wasmcl.wasm`) and subprims (`subprims.wasm`) used default `--global-base=1024`, causing their `.rodata` and BSS regions to overlap in shared linear memory. The subprims `__wasm_init_memory` start function's `memory.fill` for BSS zeroing destroyed kernel `.rodata` at addresses 0x7B0–0x189C. This corrupted the ".image" suffix string → `open()` shim didn't intercept → `load_openmcl_image` never called → Fatal. Fixed with `--global-base=1064960` in subprims Makefile, relocating subprims data to 0x104000.
- **Verbose ivec-cp diagnostic logging:** Removed per-element const pool logging in `wasm-kernel-stubs.c` that generated millions of lines during const pool installation.
- **Heap size:** Increased from 128 MB to 3.9 GB (`reserved_area_size = 3994u << 20` in `pmcl-kernel.c`, `reserve = 4058 * (1 << 20)` in `make-real-image.mjs`). 1 GB produced 3,982 "reserve failed" errors; 3.9 GB produces zero. All 7,557 runtime modules install successfully (0 failed, ~40 minutes).
- **Module installation progress logging:** Added progress counter to `installCompiledModulesFromBundle` loop in `ccl-loader.mjs` (every 500 modules).

- **Boot modules omission diagnosed:** Entry 1123 crash was caused by running `make-real-image.mjs` without `--boot-modules`. The 1,110 level-0 functions (entries 0–~1400, including `%RUN-COLD-BOOT-INIT` at 1123) are in the boot modules bundle, not the runtime modules bundle. Without `--boot-modules build/wasm32/modules/wasm-boot-modules.json`, these entries are never populated in the function table. The runtime modules (entries ~1404–8904) install successfully but cold-boot-init immediately calls entry 1123 and crashes.

**CRITICAL: `--boot-modules` is required.** Always pass `--boot-modules build/wasm32/modules/wasm-boot-modules.json` when running `make-real-image.mjs` directly. The `rebuild-everything.sh` script does this automatically. Running without boot modules produces a misleading "null function" crash with no warning.

**Resolved blocker (2026-02-17):** `_SPbuiltin_length` / `_SPbuiltin_seqtype` infinite recursion during cold-boot-init. Fixed by adding inline fast paths (vectorH, simple-vector, CL ivectors, proper lists) matching ARM assembly logic. Both subprims now handle common types without calling into Lisp.

**Resolved blocker (2026-02-18):** Module consolidation: 2 of 11 merged batches failed `WebAssembly.Module()` validation (bad stack discipline in ~2 Lisp functions). Added `validate-wasm-bytes` + fallback to individual modules in `compile-wasm-fasls.lisp`. Result: 7557/7557 modules installed, 0 failed (was 6057/7557).

**Resolved blocker (2026-02-18):** `_SPbuiltin_ash` OOB crash during cold-boot-init. Root cause: `%pname-hash` and `%string-hash` in `wasm-symbol.lisp` used 32-bit unsigned arithmetic (`#xFFFFFFFF` masks, `(ash x 5)` on 27-bit values) that overflows WASM32's 30-bit fixnums → bignums → corrupted pointers → OOB crash in `wasm_lisp_word_ref`. Fix: rewrote both hash functions with split hi16/lo16 accumulator — all intermediates ≤ 16 bits, well within fixnum range.

**Resolved blocker (2026-02-18):** Infinite `SYMBOL-NAME` loop in `%GET-HASHED-HTAB-SYMBOL` during cold-boot-init. Root cause: hash value mismatch between cross-compilation (x86-64 HOST) and WASM runtime. The x86-64 `%pname-hash` LAP returns the full 32-bit accumulator. During cross-compilation, `mixup-hash-code` (#+cross-compiling version) masks this to `target::target-most-positive-fixnum` = 29 bits on WASM32. But our WASM `%pname-hash` only returned 27 bits. The 2-bit difference (bits 27-28) caused symbol lookups to start at wrong hash table slots → infinite linear probing. Fix: changed final return from `(logand hi #x7FF)` (27 bits) to `(logand hi #x1FFF)` (29 bits). Verified against 24 test strings: `(logand native-x86-64-hash #x1FFFFFFF)` = our 29-bit split, 0 mismatches.

**Current blocker:** TBD — awaiting rebuild with 29-bit hash fix.

**Tooling added:**
- `scripts/wasm/check-freshness.sh` — Detects stale build artifacts across the full dependency chain
- `scripts/wasm/lookup-entry.mjs` — Annotates funcall traces with function names
- Phase0A test runner now warns when test modules are stale relative to kernel/subprims

**Deliverable:** `doc/wasm/calling-convention-abi.md` — authoritative ABI spec for all calling convention sites.

---

### Phase 2: Build-Time Completeness + Launch Artifacts ❌

**Goal:** Complete image + precomputed launch data.

- [ ] Proactive const pool installation (all pools installed before image save)
- [ ] `startup-plan.json` emitted (flat function table map)
- [ ] `modules.bin` emitted (uncompressed concatenated WASM modules)

---

### Phase 3: Deterministic Launcher ❌

**Goal:** Launch = read plan → load image → fill table → run.

- [ ] DELETE `bootstrap-contract.mjs` (163 lines)
- [ ] DELETE `bootstrap-function-resolver.mjs` (975 lines)
- [ ] REWRITE `load-image.mjs` (1093 → ~200 lines)
- [ ] REWRITE `microkernel.mjs` (2054 → ~600 lines)
- [ ] SIMPLIFY `ccl-loader.mjs` (keep only runtime dynamic compilation)
- [ ] Parallel module compilation (`Promise.all()`)
- [ ] REPL functional

---

## 📋 NEXT UP (After Deterministic Startup)

### Define postMessage API for Library Mode ⏸️
### Create Embedding Examples ⏸️
### Add Regression Tests ⏸️

---

## 🔮 DEFERRED (MVP-2 / Future)

- Multi-runner architecture (SharedArrayBuffer coordination)
- Storage backend (IndexedDB integration)
- Web UI/IDE integration
- Quicklisp/ASDF compatibility
- Complex data structures (arrays, hash tables, CLOS)
- Optimization passes
- FFI/networking
- V8 WASM code cache (second-launch optimization)
- Module merging (Binaryen wasm-merge)
- Direct kernel imports (replace request/response buffer)
- Streaming compilation (browser deployment)

---

## 📊 Current Status

**Completed:** B1-B6 fixes, funcall ordering fix, ABI spec, diagnostic cleanup, instrumentation removal (~4500 lines), startup truth retirement, startup binding map removal (~2500 lines), debugging infrastructure, cold-boot init extraction (Phase 1a-1c), hash function char-code fix, ivector const pool support, target:: package resolution fix, subprims .rodata collision fix, heap increase to 3.9 GB, `_SPbuiltin_length`/`_SPbuiltin_seqtype` inline fast paths, module consolidation (merge + pack dedup), module validation fallback (7557/7557 installed)
**Blocked on:** awaiting rebuild after `%pname-hash` 29-bit hash fix. Previous blockers (`_SPbuiltin_ash` OOB, SYMBOL-NAME infinite loop, `_SPbuiltin_length` recursion, 1500 failed merged modules, spill stack overflow, `%KERNEL-RESTART` XFUNBND, $hprimes subtag, .rodata corruption) resolved.
**Build pipeline:** Functional (kernel → subprims → boot image → modules → image assembly)
**MVP-1 completion:** 65% → Phase 0 unblocks everything

---

## 🎯 MVP-1 Success Criteria

- [ ] Deterministic startup (Phases 0-3 complete)
- [ ] Bootstrap to toplevel reliable
- [ ] Can define and call Lisp functions
- [ ] REPL functional in browser
- [ ] postMessage API documented and tested
- [ ] Embedding examples working
- [ ] Known limitations documented
- [ ] Regression tests prevent future breakage

---

## 🛠 Working Rules

**One blocker deep:** If fixing A reveals blocker B, that's a signal to workaround A instead.
**Defer aggressively:** When sub-problems arise, add to BLOCKERS section, don't chase immediately.
**Time-box investigations:** Set time limits, then decide fix vs workaround vs defer.
**Document decisions:** When deferring or choosing an approach, note why in this file.

---

## 🚧 RESOLVED BLOCKERS (History)

### B1. Missing Build Artifacts ✅ (2026-02-15)
Fixed subprims.wasm Makefile, stale import paths, added 20 kernel exports.

### B2. Module Installation Skipping 99.97% ✅ (2026-02-15)
Implemented `wasm_const_pool_ref`, added 7 missing Makefile exports. 7557/7557 modules install.

### B3. Compiler Emits Raw Entry Index as Function Ref ✅ (2026-02-16)
Rewrote `wasm2-builtin-call` to dispatch via `.SPbuiltin-*` subprims.

### B4. Missing Level-0 Definitions ✅ (2026-02-16)
Added `%new-gcable-ptr` for WASM, `xmacptr` type, `set-%gcable-macptrs%` stub.

### B5. Tagbody br_table Infinite Loop ✅ (2026-02-16)
Fresh unique labels per segment in `wasm2-local-tagbody`.

### B6. l1-cl-package.lafsl Loading Failure ⚠️ (2026-02-16)
Root cause: 280+ missing WASM LAP bridge functions. Systemic fix: Phase 0A.

---

## 📝 Session Notes

**2026-02-18 (session 2):** Diagnosed and fixed TWO `%pname-hash` bugs:

1. **Bignum overflow crash**: `%pname-hash` intermediate arithmetic produced bignums on WASM32 (e.g., `(ash (logand accum #x7FFFFFF) 5)` → up to 32 bits → bignum → corrupted pointers → OOB crash in `wasm_lisp_word_ref`). Fix: rewrote with split hi16/lo16 accumulator — all intermediates ≤ 16 bits.

2. **Hash value mismatch (27-bit vs 29-bit)**: After fixing the bignum crash, cold-boot-init hit an infinite `SYMBOL-NAME` loop in `%GET-HASHED-HTAB-SYMBOL`. Root cause: the x86-64 HOST's `%pname-hash` LAP returns the full 32-bit accumulator. During cross-compilation, the `#+cross-compiling` `mixup-hash-code` masks to `target::target-most-positive-fixnum` = 29 bits on WASM32. But our WASM version only returned 27 bits (matching ARM LAP convention, but the boot image was built by x86-64 HOST). Verified with 24 test strings on HOST: `(logand native-x86-64-hash #x1FFFFFFF)` = our 29-bit split, 0 mismatches. Fix: changed return mask from `#x7FF` (27 bits) to `#x1FFF` (29 bits). Max result = `#x1FFFFFFF` = `most-positive-fixnum` on WASM32 — always a fixnum.

Also added heap bounds guards to `wasm_lisp_word_ref` (permanent safety) and ASH fallback diagnostics (temporary). Found `%KERNEL-RESTART` entry-index mismatch (fcell points to entry 524 = `%SHORT-FLOAT-RATIO` — function never compiled as WASM module).

**2026-02-18:** Module validation fallback implemented and verified. Added `validate-wasm-bytes` function to `compile-wasm-fasls.lisp` — writes merged module bytes to temp file, runs `wasm-validate` (WABT), falls back to individual modules on failure. Modified `merge-module-batches` to return `(values merged-batches failed-entries)` and `write-module-bundle` to append failures to individual list. Full rebuild result: 9 valid merged batches + 1502 individual (1500 validation fallback + 2 original), 7557/7557 modules installed (0 failed), 5446 const pools, ~770 MB binary. Cold-boot-init now gets past the previous `_SPbuiltin_length` recursion blocker (inline fast paths added previously) but crashes with `memory access out of bounds` in `wasm_lisp_word_ref` during `_SPbuiltin_ash` Lisp fallback.

**2026-02-17 (session 5):** Found and fixed subprims .rodata data segment collision — both kernel and subprims used `--global-base=1024`, causing the subprims `__wasm_init_memory` BSS zeroing to destroy kernel `.rodata` (addresses 0x7B0–0x189C). Fixed with `--global-base=1064960` in subprims Makefile. This was the root cause of the boot image Fatal crash — ".image" suffix was being zeroed, so `open()` shim never intercepted, `load_openmcl_image` never called. Also increased heap from 128 MB to 3 GB (1 GB still had 3,982 "reserve failed" errors). Removed verbose per-element ivec-cp diagnostic logging from `wasm-kernel-stubs.c`. Boot image now loads successfully; cold-boot-init reaches entry 1123 then crashes with `null function or function signature mismatch`.

**2026-02-17 (sessions 3-4):** Fixed `%pname-hash`/`%string-hash` — both used `(uvref str i)` which returns tagged characters; hash algorithm expects integer codes. Wrapping with `char-code` resolved the `%KERNEL-RESTART` XFUNBND crash at step 60 (hash table resize). Next crash was `_SPsubtag_misc_ref` — `$hprimes` (u16-vector) was being created as fixnum-vector. Root cause: the const pool serializer treated all non-string vectors as generic simple-vectors. Added ivector const pool tag (17) with element-type-to-subtag mapping. Hit secondary bug: `target::subtag-*` in `wasm2.lisp` resolved at read time to HOST (x86-64) subtag values, not WASM target. Fixed by using `wasm::subtag-*` directly. Also added TARGET package nickname redirect to `build-wasm-boot.lisp`. Verified `$hprimes` now gets subtag=0xd7 (u16-vector). Boot progressed past hash tables to new crash: spill stack overflow in `TRUNCATE-NO-REM` (entry 822).

**2026-02-17 (session 2):** Corrected arg register convention fix. Previous session wrongly changed runtime to match compiler bug. Actual fix: WASM compiler prologue (`wasm2-arg-prologue-ir`, `wasm2-closed-arg-prologue-ir`) was missing ARM's `(reverse req)` — porting bug causing `arg_z = first param`. Fixed prologue to be nargs-aware (for 2-arg: first→arg_y, last→arg_z). Reverted `wasm_sync_arg_regs_from_vsp` to ARM TOS-based. Full rebuild passes; root image still fails with `%KERNEL-RESTART` undefined (same blocker, unrelated to arg ordering).

**2026-02-17:** Systemic audit of argument ordering conventions across compiler, C runtime, and JS host. Built `check-freshness.sh` stale artifact detection tool, added phase0a test compilation to `rebuild-everything.sh`, added staleness warnings to test runner. Confirmed all 144 phase0a test failures are pre-existing (not caused by sync fix).

**2026-02-16 (session 3):** Wrote `doc/wasm/calling-convention-abi.md` — authoritative spec covering all 8 calling convention sites. Confirmed ABI is internally consistent for default path (`*wasm2-use-arg-regs*` = nil). Documented latent bug in arg-regs optimization (disabled). Cleaned all diagnostic code from kernel stubs and subprims. Root image build now terminates with `ksignalerr` (was hanging indefinitely due to noisy DIAG logging).

**2026-02-16 (session 2):** Fixed funcall argument ordering bug (commit `31d89be7`). Confirmed FASL regression was already fixed. Root image build went from crashing at `_SPmisc_alloc` to hanging (now progresses through package loading).

**2026-02-16:** Designed deterministic startup plan. Key insights:
- Const pools installed on-demand (`installConstPools: false`), not proactively → Phase 2A fixes this
- Image contains all Lisp state except WASM function refs → launch only rebuilds function table
- Zero relocation possible: set image base = `__heap_base`
- Kernel-JS uses request/response buffer ABI (not direct imports) — preserve import contract
- 280+ ARM LAP functions have no WASM equivalents — all needed, no shortcuts
- Net result of Phase 3: delete ~2800 lines of JS, gain deterministic startup
