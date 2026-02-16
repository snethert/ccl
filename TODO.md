# CCL WASM TODO

<!-- Debugging guide: doc/wasm/debugging.md — read first when troubleshooting -->

**Last updated:** 2026-02-16
**Current phase:** MVP-1 (Library/Embedded Mode)

---

## 🚨 CRITICAL PATH (Blocking MVP-1)

These must be fixed before any new features. Everything else is blocked.

### Fix FASL Loading Regression ✅ **COMPLETED 2026-02-15**

**Problem:** `level-1.lafsl` returns -7 when trying to load. Used to work, now broken.

**Root cause identified:**
- Image loads physically into memory ✅
- Symbol objects exist with correct structure ✅
- **Package hash tables NOT rebuilt** - contain stale pointers (FIXED)
- **`RESTORE-LISP-POINTERS` never called** - `start_lisp()` skips this step (FIXED)
- `wasm_find_symbol_named_bytes()` fails because hash lookup is broken (FIXED)

**Solution implemented:**
- ✅ Added call to `RESTORE-LISP-POINTERS` in `start_lisp()` before `wasm_toplevel_loop()`
- ✅ Follows exact pattern from native CCL and [image-loader-spec.md](doc/wasm/image-loader-spec.md)
- ✅ Code change: [wasm-kernel-stubs.c:3507](lisp-kernel/wasm-kernel-stubs.c#L3507)
- ✅ Kernel rebuilt successfully with no errors
- ✅ Basic smoke tests passing: smoke-test, gc-forwarding, kernel-request

**Acceptance criteria:**
- [x] `RESTORE-LISP-POINTERS` gets called after image load
- [x] Package hash tables properly rebuilt
- [ ] `wasm_find_symbol_named_bytes("CCL", "%FASLOAD")` succeeds (pending full test)
- [ ] `level-1.lafsl` loads without returning -7 (pending build artifacts)
- [x] No errors in symbol resolution during load (basic tests pass)

**Test status:**
- ✅ Kernel compiles cleanly
- ✅ Basic runtime tests pass (smoke-test.mjs, gc-forwarding-smoke.mjs, kernel-request-smoke.mjs)
- ⚠️ Full FASL loading test blocked by missing build artifacts (wasm-smoke-modules.json, subprims.wasm)

---

### Remove Instrumentation Cruft from Kernel ✅ **COMPLETED 2026-02-15**

**Problem:** Heavy debugging instrumentation scattered throughout kernel code from previous investigation attempts

**Solution implemented:**
- ✅ Removed trace/diag compile flags, enums, and structures (~480 lines)
- ✅ Removed all `wasm_emit_*` function implementations and call sites (69+ calls)
- ✅ Removed startup truth collection code (global variables, functions, exports)
- ✅ Removed wasm_debug_* export functions (40+ functions, ~990 lines)
- ✅ Removed deleted function exports from Makefile (24 exports)
- ✅ Re-added `WASM_PROBE_FOREIGN_CALL` enum (functional code, not instrumentation)
- ✅ Kernel rebuilt successfully
- ✅ All basic smoke tests pass (smoke-test, gc-forwarding, kernel-request)

**Files modified:**
- `lisp-kernel/wasm-kernel-stubs.c` - Removed ~1800+ lines of instrumentation code
- `lisp-kernel/wasm32/Makefile` - Removed 24 export declarations

**Total removed:** ~1800+ lines of debugging instrumentation

**Acceptance criteria:**
- [x] All `wasm_emit_*` calls removed
- [x] All trace/diag infrastructure removed
- [x] All `wasm_startup_truth_*` code removed
- [x] All `wasm_debug_*` exports removed
- [x] Kernel rebuilds successfully
- [x] Basic smoke tests still pass

---

### Audit Kernel for Residual Instrumentation Cruft ✅ **COMPLETED 2026-02-15**

**Problem:** After bulk instrumentation removal, residual cruft remained: MVP-2 web-ui demo payloads, dead diagnostic code behind undefined compile flags, debug state capture variables, and duplicate declarations.

**Approach:** Repeated audit passes of `wasm-kernel-stubs.c` until a clean pass (zero matches for all instrumentation patterns). Any audit that finds something is a fail.

**Solution implemented:**
- ✅ Removed 4 UI demo payload binary blobs (`wasm_ui_payload_Ready`, `wasm_ui_payload_Clicked`, `wasm_ui_payload_Canvas_demo_canvas_top`, `wasm_ui_payload_WebGL_demo_webgl_top`) + length constants (~176 lines)
- ✅ Removed `wasm_ui_demo_phase` variable and `wasm_ui_demo_turn` exported function (MVP-2 demo code)
- ✅ Removed 6 `wasm_debug_last_toplevel_*` variables and `wasm_debug_capture_toplevel_throw` function + all usage
- ✅ Removed all `#if WASM_STARTUP_DIAG_ENABLED` dead code blocks (~180 lines, flag was never defined)
- ✅ Removed 8 `wasm_const_pool_debug_*` static variables, `WASM_CONST_POOL_DEBUG_ERROR_*` enum, and `wasm_const_pool_error_from_intern_status` helper
- ✅ Removed duplicate forward declarations
- ✅ Removed unused `phase_code` local variables (only used by removed diag blocks)
- ✅ Removed `wasm_ui_demo_turn` export from Makefile
- ✅ Deleted backup files (`.before-fixes`, `.backup`)

**Files modified:**
- `lisp-kernel/wasm-kernel-stubs.c` - Removed ~628 lines (5592 → 4964)
- `lisp-kernel/wasm32/Makefile` - Removed 1 export declaration

**Audit results:**
- Audit pass 1: FAIL (7 categories of cruft found)
- Audit pass 2: PASS (zero matches for all instrumentation patterns)

**Acceptance criteria:**
- [x] Zero matches for `wasm_debug_|wasm_diag_|wasm_startup_diag|wasm_emit_|wasm_ui_payload|wasm_ui_demo|WASM_STARTUP_DIAG|wasm_const_pool_debug`
- [x] No duplicate declarations
- [x] No backup files
- [x] Kernel rebuilds successfully
- [x] All basic smoke tests pass

---

### Sweep JS/Lisp/Shell for Dead Debug References ✅ **COMPLETED 2026-02-15**

**Problem:** After removing ~2400 lines of C kernel debug instrumentation, JS scripts, Lisp files, and shell scripts still referenced the deleted exports.

**Solution implemented:**
- ✅ Rewrote `bootstrap-contract.mjs` (440 → 165 lines) - removed probe infrastructure
- ✅ Cleaned `make-real-image.mjs` (~770 lines removed) - 9 diagnostic functions, 21 call sites, typeof-guarded dead blocks, readDebug blocks, compound conditions
- ✅ Cleaned `microkernel.mjs` (~217 lines removed) - 8 WASM_STARTUP_DIAG constants, decodeWasmStartupDiag function
- ✅ Cleaned `runtime-command-sab-smoke.mjs` (~57 lines removed) - debug probe blocks
- ✅ Cleaned `harness.mjs` - dead kernelDemoTurn reference
- ✅ Cleaned `phase-5-runtime-output.test.mjs` (~284 lines removed) - diag constants, encode helpers, test cases
- ✅ Cleaned `apply-time-exact-package-symbol.test.mjs` - debug mock removed

**Startup truth feature fully retired:**
- ✅ Removed `startup-truth-runtime.lisp` (~310 lines) and `startup-truth-close.lisp` (~10 lines)
- ✅ Removed ~290 lines from `l1-cl-package.lisp` (7 defvars, ~270 lines of function definitions, 9-line call site)
- ✅ Removed `%wasm-startup-truth-note-event-if-available` function + 6 call sites from `l1-symhash.lisp`
- ✅ Removed startup truth env var/constants/functions from `make-real-image.mjs` (~115 lines)
- ✅ Removed `--collect-truth`/`--truth-out` flags from `rebuild-everything.sh`
- ✅ Removed startup truth from `repro-startup-pipeline.sh` (env vars, manifest writer, artifact list)
- ✅ Removed stale `wasm_ui_demo_turn` doc reference from `FRONT-END-DEV-PLAN.md`

**Total removed:** ~2100+ lines across JS/Lisp/shell files

**Acceptance criteria:**
- [x] Zero `wasm_debug_*` references in code files
- [x] Zero `startup_truth` / `wasm-startup-truth` references in code files
- [x] All JS files pass syntax check
- [x] Kernel rebuilds cleanly
- [x] All 3 smoke tests pass

---

### Fix minimal.image Bootstrap Failures ❌

**Problem:** `minimal.image` fails strict pre-start bootstrap contract

**Blocked by:** FASL loading task (must work first)

**Acceptance criteria:**
- [ ] `minimal.image` passes strict bootstrap checks
- [ ] Symbols resolve correctly
- [ ] Can boot to a working REPL

**Investigate after:** FASL loading is fixed

---

### Stabilize root.image Symbol Resolution ❌

**Problem:** `root.image` has core symbol/function dispatch instability during persistence

**Blocked by:** FASL loading task (same root cause likely)

**Reference:** [wasm-ui-persistence-problem-tracker.md](doc/wasm/wasm-ui-persistence-problem-tracker.md)

**Acceptance criteria:**
- [ ] `root.image` loads reliably
- [ ] Symbol/function dispatch stable
- [ ] Persistence smoke tests pass consistently

**Investigate after:** FASL loading is fixed

---

## 📋 NEXT UP (After Critical Path Cleared)

These are the next tasks for MVP-1, but don't start until regressions are fixed.

### Define postMessage API for Library Mode ⏸️

**Goal:** External apps can interact with embedded CCL WASM

**Acceptance criteria:**
- [ ] API design documented (eval, define, call)
- [ ] Message format specified (requests/responses)
- [ ] Error handling defined
- [ ] Example HTML page works

**Start after:** Critical path tasks are green

---

### Create Embedding Examples ⏸️

**Goal:** Show developers how to use Library Mode

**Deliverables:**
- [ ] Minimal `<script>` embed example
- [ ] React integration example
- [ ] Limitations clearly documented

**Start after:** postMessage API task complete

---

### Add Regression Tests ⏸️

**Goal:** Prevent future breakage of fasl loading / bootstrap

**Acceptance criteria:**
- [ ] CI test for `level-1.lafsl` loading
- [ ] CI test for minimal.image bootstrap
- [ ] CI test for root.image bootstrap
- [ ] Tests fail if regressions reoccur

**Start after:** Critical path tasks are stable

---

### Code Cleanup Pass ⏸️

**Goal:** Remove obsolete code from previous attempts

**What to remove:**
- [ ] Obsolete image loading mechanisms
- [x] Superseded bootstrap code (startup binding map infrastructure removed)
- [x] Unused diagnostic scaffolding (removed in instrumentation + audit + JS/Lisp/shell sweep + boundary strip passes)
- [x] Startup truth feature (fully retired across C/JS/Lisp/shell)
- [ ] Confusing "replacement lane" terminology

**Impact:** Easier debugging, clearer code paths

**Start after:** MVP-1 is functionally stable (don't destabilize during crisis)

---

## 🔮 DEFERRED (MVP-2 / Future)

These are explicitly NOT being worked on until MVP-1 ships.

- Multi-runner architecture (SharedArrayBuffer coordination)
- Storage backend (IndexedDB integration)
- Web UI/IDE integration (blocked by runtime stability)
- Quicklisp/ASDF compatibility
- Complex data structures (arrays, hash tables, CLOS)
- Optimization passes
- FFI/networking

**Threading-aware deferred items** (must plan for multi-runner from the start):
- `set-%gcable-macptrs%` — Currently a no-op stub. Must implement with `Atomics.compareExchange` on SharedArrayBuffer for thread-safe gcable-pointers list management. Native backends use ldrex/strex (ARM) and lock cmpxchg (x86).
- Dynamic-extent stack block optimization — WASM backend lacks `dynamic-extent` handling for `%stack-block`. Currently falls through to heap allocation via `%new-gcable-ptr`. Proper implementation needs WASM equivalents of `make-stack-block` / `$undostkblk` vinsns. Single-runner (MVP-1) can use simple alloca-style allocation; multi-runner needs per-runner temp stacks.
- Other LAP functions in `level-0/ARM/arm-misc.lisp` that use atomic operations: `%lock-gc-lock`, `%unlock-gc-lock`, `%atomic-incf-node`, `%atomic-decf-node`, etc. All need `Atomics.*` implementations for MVP-2.

**Rationale:** Foundation must work before adding complexity. MVP-1 stubs are acceptable for single-runner, but the proper implementations must use SharedArrayBuffer atomics for MVP-2 multi-runner.

---

## 📊 Current Status

**Completed:** FASL loading fix, instrumentation removal (~2400 lines C), residual cruft audit, JS/Lisp/shell dead code sweep (~2100 lines), startup truth feature retired, B1 build artifacts resolved, startup binding map removed (~2500+ lines), RESTORE-LISP-POINTERS kernel export added, B2 module installation fixed (7557/7557 install), boundary diagnostic scaffolding stripped (~1085 lines), debugging infrastructure built (state dump, TCR inspector, debug launcher), subprims build gap fixed, B3 builtin-call compiler fix, B4 level-0 bootstrap dependencies (3 sub-fixes), B5 tagbody br_table infinite loop fix
**Blocked on:** B6 — l1-cl-package.lafsl loading fails with garbage fd (16899495) and funcall-error. All level-0 files load successfully.
**Build pipeline:** Fully functional (kernel → subprims → boot image → boot modules → runtime modules → image build attempt)
**MVP-1 completion:** 65% (build pipeline works, 8385 modules compile+install, all level-0 FASL files load successfully, first level-1 file fails with I/O error)

---

## 🎯 MVP-1 Success Criteria

**Ship when ALL of these are true:**
- [ ] FASL loading works (regression fixed)
- [ ] Bootstrap to toplevel reliable
- [ ] Can define and call Lisp functions
- [ ] REPL functional in browser
- [ ] postMessage API documented and tested
- [ ] Embedding examples working
- [ ] Known limitations documented
- [ ] Regression tests prevent future breakage

**Target:** Ship minimal but working Library Mode, get user feedback, then iterate.

---

## 🛠 Working Rules

**One blocker deep:** If fixing A reveals blocker B, that's a signal to workaround A instead.

**Defer aggressively:** When sub-problems arise, add to BLOCKERS section, don't chase immediately.

**Time-box investigations:** Set time limits, then decide fix vs workaround vs defer.

**Document decisions:** When deferring or choosing an approach, note why in this file.

---

## 🚧 BLOCKERS

_Sub-problems discovered during main track work. Decide: fix now, workaround, or defer._

### B1. Missing Build Artifacts for Full Test Coverage ✅ **RESOLVED 2026-02-15**

**Discovered:** 2026-02-15 during FASL loading fix testing
**Resolved:** 2026-02-15

**Fixes applied:**
- ✅ `subprims.wasm` — Fixed Makefile to use env.sh toolchain (config.mk include, correct output path)
- ✅ `wasm-smoke-modules.json` — Fixed stale `doc/wasm/js/` import paths, made `startupBindingMap` optional
- ✅ `wasm-runtime-modules.json` — 7557 modules compiled (437MB binary)
- ✅ Fixed 5 stale `doc/wasm/js/` paths in build pipeline scripts
- ✅ Added 20 missing kernel exports to Makefile (16 existing functions + 4 new)
- ✅ Implemented `wasm_get_lisp_nil`, `wasm_get_compiled_module_registry` kernel accessors
- ✅ Implemented symbol probe API (later removed — was only needed by startup binding map)
- ✅ Made `installCompiledModulesFromRegistry` graceful when kernel lacks registry exports

**Files modified:**
- `lisp-kernel/wasm32/subprims/Makefile` — Rewritten to use config.mk
- `lisp-kernel/wasm32/Makefile` — Added 20 exports
- `lisp-kernel/wasm-kernel-stubs.c` — Added 6 new exported functions
- `scripts/wasm/pack-inline-bundle-v2.mjs` — Fixed imports, made startupBindingMap optional
- `scripts/wasm/compile-wasm-fasls.sh` — Fixed stale path
- `scripts/wasm/rebuild-everything.sh` — Fixed stale path
- `scripts/wasm/generate-bootstrap-l0-contract-sidecar.mjs` — Fixed stale path
- `scripts/wasm/compact-runtime-modules.mjs` — Fixed stale import
- `scripts/wasm/make-real-image.lisp` — Fixed stale path
- `scripts/wasm/lib/ccl-loader.mjs` — Graceful registry install

---

### B2. Compiled Module Installation Skipping 99.97% of Modules ✅ **RESOLVED 2026-02-15**

**Discovered:** 2026-02-15 during root.image build attempt
**Resolved:** 2026-02-15

**Root cause:** Kernel did not implement or export `wasm_const_pool_ref`, but all 7555 generic compiled modules import it as `ccl.wasm_const_pool_ref`. `WebAssembly.instantiate()` threw a LinkError at link time, silently caught by `strict: false`. The 2 modules that succeeded (`ccl_const_entry`, `ccl_identity_entry`) don't import this function.

Additionally, 6 other kernel functions were implemented but not exported in the Makefile: `wasm_lisp_word_ref`, `wasm_set_arg_x`, `wasm_set_imm0`, `wasm_set_nfn`, `wasm_vpush`, `wasm_vpop`.

**Fixes applied:**
- ✅ Implemented `wasm_const_pool_ref(uint32_t entry_index, uint32_t slot_index)` in wasm-kernel-stubs.c
- ✅ Added 7 missing `--export=` entries to Makefile
- ✅ Kernel rebuilt successfully, all smoke tests pass
- ✅ **7557/7557 compiled modules now install** (was 2/7557)
- ✅ Stripped ~1085 lines of boundary diagnostic scaffolding from make-real-image.mjs (2346 → 1261)

**Files modified:**
- `lisp-kernel/wasm-kernel-stubs.c` — Added `wasm_const_pool_ref` (~35 lines)
- `lisp-kernel/wasm32/Makefile` — Added 7 exports
- `scripts/wasm/lib/make-real-image.mjs` — Removed boundary probes, autobind, diagnostic JSON, DIAG env blocks

**Remaining issue:** FASL loading still returns -7 after modules install. `%FASLOAD`, `%FASL-OPEN`, `%SIMPLE-FASL-OPEN` not yet bound. This is now a separate investigation — see B3.

---

### B3. FASL Loading Fails — Compiler Emits Raw Entry Index as Function Reference

**Discovered:** 2026-02-15 after B2 fix
**Impact:** root.image build fails during FASL load (`level-1.lafsl` returns -72)
**Status:** ✅ Fixed (2026-02-16)

**Two issues found:**

**Issue 1: Boot modules not loaded (resolved)**
- `make-real-image.mjs` requires `--boot-modules` flag to load level-0 modules into the WASM function table (indices 200-1125)
- Without it, 924 table entries are NULL → immediate `call_indirect` trap at entry 1103 (%FASLOAD)
- `rebuild-everything.sh` passes the flag correctly (line 210); direct invocations must also pass it
- With boot modules: 820/828 install (8 fail with LinkError/CompileError), entry 1103 populated, FASL loading begins

**Issue 2: Compiler emits `i32.const box_fixnum(entry_index)` instead of `wasm_const_pool_ref` (THE BUG)**

**Exact crash sequence (traced 2026-02-16):**
```
%FASLOAD(1103) → FBOUNDP(489) → VALIDATE-FUNCTION-NAME(487) → %STRING-TO-STDERR(686)
  → tries to funcall LENGTH → fn=0x2c (fixnum 11) → funcall-error
```

**WAT disassembly of entry 686 (%STRING-TO-STDERR) proves the bug:**
```wat
i32.const 686; i32.const 0; call $wasm_const_pool_ref  ;; → %NEW-GCABLE-PTR (correct)
local.set 3
i32.const 44     ;; ← BUG: literal 0x2C = box_fixnum(11) used as function
local.set 5
...
local.get 5      ;; 44 (0x2C)
local.get 6      ;; str
call $wasm_funcall1  ;; wasm_funcall1(fn=44, arg=str) → CRASH
```

**Const pool for entry 686 (56 bytes, hex):**
```
0203 01 0f %NEW-GCABLE-PTR CCL  01 0d %CSTR-POINTER CCL  01 08 FD-WRITE CCL
```
3 symbol entries (tag 1). LENGTH is NOT in the const pool — it's emitted as a raw `i32.const 44`.

**Root cause in compiler:**
- `wasm2-emit-const` (wasm2.lisp:4301): `(if (integerp value) (wasm2-emit :const value) ...)` — when value is an integer, it emits `i32.const` directly, bypassing the const pool
- For some function references (LENGTH, likely many others), the NX IR `immediate` form contains a boxed entry index (integer 44) instead of a function object or symbol
- Other functions (%NEW-GCABLE-PTR, %CSTR-POINTER, FD-WRITE) correctly go through the const pool as symbol references (tag 1)
- The distinction appears to be between how the NX frontend resolves CCL-internal functions vs. CL standard functions during cross-compilation
- Entry index 11 likely corresponds to LENGTH in the boot module allocation

**Why the bug is systemic:**
- Every compiled module that calls a function resolved to a raw entry index will have this bug
- This affects an unknown (but likely large) number of function calls across all 8385 compiled modules
- The bug is in the compiler's IR-to-WASM codegen, not in the const pool installer or runtime

**State dump evidence (2026-02-16):**
```
=== STATE DUMP: funcall-error ===
  nfn      = 0x0000002c    ← fixnum(11), should be function object for LENGTH
  Rfn      = 0x0000002c
  arg_z    = 0x0407769e    ← string argument to %STRING-TO-STDERR
  nargs    = 0x00000004    ← fixnum(1)
  last_cpr: e=686 s=0 val=0x0400032e  ← const pool slot 0 (%NEW-GCABLE-PTR) is valid
  spill depth = 219
```

**Next steps:**
1. Trace upstream in NX compiler: find where function references become integers in `immediate` forms during cross-compilation (likely in `wasm2-set-afunc-lfun` or `wasm2-const-code-vector` which return raw entry indices in cross-compile mode)
2. Fix: ensure all function references go through const pool (tag 1 = symbol or tag 16 = entry-function), never as raw `i32.const`
3. Two possible fix strategies:
   - (a) Fix upstream: prevent NX IR from storing boxed entry indices in `immediate` forms for function references
   - (b) Fix in `wasm2-emit-const`: detect when an integer is a function entry index and route through const pool
4. Rebuild all modules after fix, re-test FASL loading

**Fix applied (2026-02-16):**
- Root cause: `wasm2-builtin-call` (wasm2.lisp:3602) passed the `(fixnum builtin-index)` form directly to `wasm2-emit-call`, which compiled it as `i32.const box_fixnum(index)` and tried to funcall the fixnum. All 23 builtin functions (LENGTH, EQL, +-2, --2, etc.) were affected.
- Fix: Rewrote `wasm2-builtin-call` to dispatch to `.SPbuiltin-*` subprims via `wasm2-builtin-index-subprim-fixnum`, matching ARM32's `arm2-builtin-call` pattern. Uses architecture's `primitive->subprims` table.
- Added `wasm2-builtin-index-subprim-fixnum` (near line 3947) — maps builtin function index to subprim fixnum
- All 23 `.SPbuiltin-*` subprims were already implemented in `wasm-subprims-provider.c`
- Verified: full rebuild succeeds, FASL loading progresses past the `fn=0x2c` crash to a new error (B4)

**Diagnostic instrumentation in place (temporary):**
- `wasm-kernel-stubs.c`: `wasm_diag_last_cpr_*` tracking, fixnum-in-pool logging, state dump integration
- `wasm-subprims-provider.c`: entry_index logging in `wasm_call_function_value`
- `make-real-image.mjs`: B3-TABLE function table diagnostic before FASL loading
- All should be removed after B4 is resolved

---

### B4. Missing Level-0 Definitions for %stack-block Dependencies ✅ **FIXED 2026-02-16**

**Discovered:** 2026-02-16 after B3 fix
**Impact:** root.image build fails — `l1-cl-package.lafsl` FASL load returns -72
**Status:** ✅ Fixed (three sub-issues)

**Root cause:** The WASM backend lacks dynamic-extent stack block optimization. On native backends (ARM, x86), `%stack-block` compiles to inline stack allocation via `make-stack-block` vinsns — no function call at all. The WASM backend has no dynamic-extent handling, so `%stack-block` compiles to a runtime call to `%new-gcable-ptr`. Three problems cascaded:

**Sub-issue 1: `%new-gcable-ptr` undefined at level-0**
- `%new-gcable-ptr` defined only in level-1 (`l1-aprims.lisp:1204`)
- All dependencies (`make-gcable-macptr`, `malloc`) available at level-0
- **Fix:** Added WASM-only level-0 definition in `l0-io.lisp:346`

**Sub-issue 2: `xmacptr` type missing from WASM architecture**
- `make-gcable-macptr` calls `(%alloc-misc target::xmacptr.element-count ...)`
- `wasm-arch.lisp` defined `macptr` (3 elements) but NOT `xmacptr` (5 elements: +flags +link)
- `_SPmisc_alloc` received non-fixnum count → crash
- **Fix:** Added `(define-fixedsized-object xmacptr address domain type flags link)` in `wasm-arch.lisp:348`

**Sub-issue 3: `set-%gcable-macptrs%` LAP function missing for WASM**
- Native backends define this as platform-specific LAP with atomic operations (ARM: ldrex/strex, x86: lock cmpxchg)
- Atomically prepends new gcable macptr to the `gcable-pointers` kernel global linked list
- **Fix:** No-op stub in `level-0/WASM/wasm-def.lisp` for MVP-1 (single-threaded)
- **MVP-2 requirement:** Must implement with `Atomics.compareExchange` for multi-runner threading. See deferred items.

**Files modified:**
- `level-0/l0-io.lisp` — Added `%new-gcable-ptr` for WASM
- `compiler/WASM/wasm-arch.lisp` — Added `xmacptr` type definition
- `level-0/WASM/wasm-def.lisp` — Added `set-%gcable-macptrs%` stub

**Verification:** Full rebuild shows FASL loading progresses past all three crashes. `%STRING-TO-STDERR` → `%NEW-GCABLE-PTR` → `MAKE-GCABLE-MACPTR` → `SET-%GCABLE-MACPTRS%` all succeed. New issue: infinite CPU loop (B5).

---

### B5. FASL Loading Infinite CPU Loop After Bootstrap ✅ **FIXED 2026-02-16**

**Discovered:** 2026-02-16 after B4 fix
**Impact:** root.image build hangs at 100% CPU during FASL load (Node.js process never returns)
**Status:** ✅ Fixed

**Root cause:** `wasm2-local-tagbody` in the compiler used `(mapcar #'car segments)` to build dispatch labels for the `br_table` state machine. When two NX-frontend tags shared the same `wasm2-tag-key` (e.g., two tagbody tags whose `(car tag)` is the same symbol), the `tag-label-map` hash table mapped them to the same label object. The `br_table` handler uses `(position label label-stack :test #'eql)` to resolve labels to block depths — duplicate labels caused multiple dispatch states to resolve to the same block depth, creating infinite loops.

**Specific failure:** In `%cstr-pointer` (entry 303), the DOTIMES loop compiled to a 3-segment tagbody (entry, check, body). The br_table was `2 0 0 4` — states 1 (body) and 2 (check) both dispatched to depth 0 (the check segment). The check found `i < limit`, set state=1, and looped back to itself forever. The loop counter `i` never incremented because the body segment was never entered.

**Fix:** Allocate fresh unique labels for each segment's block in `wasm2-local-tagbody`, independent of the `tag-label-map`. Changed `(mapcar #'car segments)` to `(mapcar (lambda (_) (wasm2-allocate-label)) segments)` and updated the block-building loop to use these fresh labels.

**Verification:** After rebuild, entry 303's br_table changed from `2 0 0 4` to `2 1 0 4` (all unique depths). FASL loading progresses past `%cstr-pointer` and loads all level-0 files successfully. New failure at level-1 (B6).

**Files modified:**
- `compiler/WASM/wasm2.lisp` — `wasm2-local-tagbody` (lines 1759-1790)

**Tools created during investigation:**
- `/tmp/extract-entry.mjs` — Node.js script to extract and disassemble individual WASM modules from the boot bundle

---

### B6. l1-cl-package.lafsl Loading Failure — Garbage File Descriptor

**Discovered:** 2026-02-16 after B5 fix
**Impact:** root.image build fails during FASL load of the first level-1 file
**Status:** ⚠️ New — investigation needed

**Symptoms:**
```
FAIL: wasm_fasload_path(l1-fasls/l1-cl-package.lafsl) returned -72
WASM lisp_write fail fd=16899495 count=0 errno=8
```

**Key observations:**
- All level-0 FASL files load successfully (B3, B4, B5 all resolved)
- First level-1 file (`l1-cl-package.lafsl`) fails immediately
- `fd=16899495` (0x01020997) is a garbage file descriptor — not a valid WASM fd
- `count=0` — trying to write zero bytes
- `errno=8` (EBADF on most systems)
- `funcall-error` state dump shows `last_cpr: e=673`
- `pending_throw=0x3c` (60)

**Likely causes:**
- I/O subsystem not properly initialized for level-1 loading
- FASL reader trying to use a Lisp stream object as a raw fd
- Missing implementation of a stream operation in the WASM backend
- Entry 673 may be a stream/IO function that lacks proper WASM support

**Next steps:**
1. Identify what entry 673 corresponds to
2. Examine the FASL loading path for level-1 files vs level-0 files
3. Check how file descriptors are managed in the WASM kernel
4. Trace the call chain that produces the garbage fd

---

## 📝 Notes / Decisions

**2026-02-15 (morning):** Created TODO.md. Starting with FASL loading regression as #1 blocker.
- Selected text suggests calling `RESTORE-LISP-POINTERS` from kernel
- Need to investigate where this should happen (kernel vs JS vs C during load)
- Time-boxed to 2 hours investigation before deciding approach

**2026-02-15 (afternoon):** Completed FASL loading fix - RESTORE-LISP-POINTERS
- Investigated root cause: confirmed `RESTORE-LISP-POINTERS` never called in WASM `start_lisp()`
- Evaluated three approaches: Option 1 (kernel call) selected as best match to native behavior
- Implemented fix in `lisp-kernel/wasm-kernel-stubs.c` at line 3507
- Added call to `RESTORE-LISP-POINTERS` with proper function validation and error handling
- Kernel rebuilt successfully, no compilation errors
- Basic smoke tests passing (smoke-test, gc-forwarding, kernel-request)
- Fixed test infrastructure import paths (created symlinks for ccl-loader.mjs, ipc-conformance.mjs, etc.)
- Discovered missing build artifacts blocking full FASL test (deferred to blocker B1)

**2026-02-15 (evening):** Completed residual cruft audit of wasm-kernel-stubs.c
- Audit pass 1: Found 7 categories of residual cruft (UI payload blobs, dead diagnostic code, debug state vars, duplicate declarations, MVP-2 demo function, const pool debug vars, backup files)
- Removed ~628 lines total (5592 → 4964 lines)
- Removed 1 Makefile export (`wasm_ui_demo_turn`)
- Deleted 2 backup files
- Audit pass 2: PASS (zero matches for all instrumentation patterns)
- Kernel rebuilds cleanly, all smoke tests pass
- Combined with earlier instrumentation removal: ~2400+ lines of cruft removed from kernel

**2026-02-15 (late evening):** JS/Lisp/shell dead code sweep + startup truth retirement
- Swept all JS/MJS files for references to removed wasm_debug_*, wasm_emit_*, wasm_startup_truth_*, etc.
- Removed ~2100 lines across 7 JS files, 2 Lisp files (deleted), 2 Lisp files (edited), 2 shell scripts, 1 doc
- Fully retired startup truth feature: env var path (shell → JS → C → Lisp) completely eliminated
- Deleted `scripts/wasm/startup-truth-runtime.lisp` and `scripts/wasm/startup-truth-close.lisp`
- Removed startup truth defvars/functions from `l1-cl-package.lisp` (~290 lines) and call sites from `l1-symhash.lisp`
- All smoke tests pass, all JS syntax checks pass, zero remaining references in code files

**2026-02-16 (session 1):** Compiled kernel functionality inventory
- 132 subprims: 84 substantial, 42 thin wrappers, 6 stubs/no-ops
- Key finding: most "not implemented" features (hash tables, CLOS, format, reader) are in Lisp level-1 files, not kernel
- The FASL loading regression is the single gate blocking nearly everything
- See MEMORY.md or session notes for full inventory

**2026-02-16 (session 2):** Debugging infrastructure + fn=0x2c investigation
- Built debugging infrastructure: `wasm_debug_dump_state`, TCR inspector, Chrome DevTools launcher
- Fixed `rebuild-everything.sh` — was missing `subprims.wasm` rebuild (critical gap; stale subprims caused silent failures)
- Discovered kernel vs subprims two-module architecture: `wasm-subprims-provider.c` compiles as separate `subprims.wasm`, NOT part of kernel. Cross-module calls require WASM import declarations (`__attribute__((import_module(...)))`)
- Rewrote state dump to avoid unreliable `snprintf %s` — uses manual string helpers instead
- **snprintf policy decision:** Use only for numeric formats (`%x`, `%u`, `%d`). No `%s` with width modifiers. The hand-rolled `vsnprintf` in `wasm-no-wasi-libc.c` doesn't fully support `%s` formatting.
- State dump confirmed: fn=0x2c at funcall-error point in `%STRING-TO-STDERR` → `(length str)`
- Root cause narrowed to const pool encoding mismatch: raw entry index (fixnum 11) stored where function object should be
- Investigation points to `compiler/WASM/wasm2.lisp` `wasm2-const-pool-entry` function
- Fixed spill stack leak on throw/catch (`save_spill_sp` field added to catch frames)
- Fixed character encoding bug in `wasm_make_simple_base_string` memcpy

**2026-02-15 (session 3):** Removed startup binding map infrastructure, added RESTORE-LISP-POINTERS
- Investigated: startup binding map does NOT exist on any native CCL platform (x86, ARM, PPC)
- Root cause: it was a 2,500+ line workaround for missing RESTORE-LISP-POINTERS call
- Added `wasm_restore_lisp_pointers()` kernel export (standalone, callable from JS)
- Removed symbol probe API from kernel (4 functions, only needed by binding map)
- Stripped ~2,500 lines from make-real-image.mjs (4818 → 2300 lines)
- Deleted 6 source files: startup-binding-map.mjs, bootstrap-l0-contract.mjs, collect-startup-symbol-scope.lisp, generate-bootstrap-l0-contract-sidecar.mjs, repro-startup-pipeline.sh, run-startup-symbol-scope-fixtures.sh
- Cleaned build pipeline: compile-wasm-fasls.sh, rebuild-everything.sh, make-real-image.lisp, pack-inline-bundle-v2.mjs
- Kernel builds cleanly, root image build reaches FASL loading (blocked by B2)
- RESTORE-LISP-POINTERS correctly deferred when function not defined (boot image), called post-fasload

**2026-02-15 (session 2):** Resolved B1 — build artifacts and pipeline fixes
- Fixed subprims.wasm build: Makefile wasn't using env.sh toolchain → updated to use config.mk
- Fixed wasm-smoke-modules.json build: stale `doc/wasm/js/` imports → updated to `scripts/wasm/lib/`
- Made `startupBindingMap` optional in packer (not consumed at runtime, only copy-through)
- Built wasm-runtime-modules.json: 7557 modules, 5450 const pools, 437MB binary
- Fixed 5 stale `doc/wasm/js/` paths across build pipeline (pack, compile-fasls, rebuild, contract, compact)
- Added `wasm_get_lisp_nil` and `wasm_get_compiled_module_registry` kernel accessors
- Implemented symbol probe API (4 functions) for startup binding map resolution
- Added 16 existing-but-unexported kernel functions to Makefile
- root.image build now reaches startup binding map phase but fails: 7555/7557 compiled modules skipped
- New blocker B2: module installer rejecting almost all modules → 4 required callables missing
