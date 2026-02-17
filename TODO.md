# CCL WASM TODO

<!-- Debugging guide: doc/wasm/debugging.md — read first when troubleshooting -->

**Last updated:** 2026-02-16
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

**Current blocker:** Root image build fails during cold-boot-init with `ksignalerr` (arg_y=0x18 / fixnum 6, last const-pool-ref entry=856 slot=9). The system loads packages and installs const pools successfully, then errors during initialization code.

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

**Completed:** B1-B6 fixes, funcall ordering fix, ABI spec, diagnostic cleanup, instrumentation removal (~4500 lines), startup truth retirement, startup binding map removal (~2500 lines), debugging infrastructure, cold-boot init extraction (Phase 1a-1c)
**Blocked on:** `ksignalerr` during cold-boot-init (arg_y=0x18, entry 856) — investigate error code and function
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

**2026-02-16 (session 3):** Wrote `doc/wasm/calling-convention-abi.md` — authoritative spec covering all 8 calling convention sites. Confirmed ABI is internally consistent for default path (`*wasm2-use-arg-regs*` = nil). Documented latent bug in arg-regs optimization (disabled). Cleaned all diagnostic code from kernel stubs and subprims. Root image build now terminates with `ksignalerr` (was hanging indefinitely due to noisy DIAG logging).

**2026-02-16 (session 2):** Fixed funcall argument ordering bug (commit `31d89be7`). Confirmed FASL regression was already fixed. Root image build went from crashing at `_SPmisc_alloc` to hanging (now progresses through package loading).

**2026-02-16:** Designed deterministic startup plan. Key insights:
- Const pools installed on-demand (`installConstPools: false`), not proactively → Phase 2A fixes this
- Image contains all Lisp state except WASM function refs → launch only rebuilds function table
- Zero relocation possible: set image base = `__heap_base`
- Kernel-JS uses request/response buffer ABI (not direct imports) — preserve import contract
- 280+ ARM LAP functions have no WASM equivalents — all needed, no shortcuts
- Net result of Phase 3: delete ~2800 lines of JS, gain deterministic startup
