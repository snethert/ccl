# CCL→WASM Roadmap (Two-Mode, Two-Phase Strategy)

**Last updated:** 2026-02-15
**Status:** Early Development / Experimental

**See also:** [README.md](README.md) for current status, [porting-status.md](porting-status.md) for detailed features

---

## Executive Summary

This port targets **two distinct deployment modes**:

1. **Library/Embedded Mode** - Single-runner, postMessage interface, works in any context
2. **Full Runtime Mode** - Multi-runner, SharedArrayBuffer, secure context required, full IDE capabilities

**Current Strategy:** Build Library Mode first (MVP-1), then Full Runtime Mode (MVP-2).

**Rationale:** Library Mode is simpler, validates core architecture, and provides a shippable artifact. Full Runtime Mode requires working foundation plus threading/SAB coordination.

---

## 🚨 Critical Issues

### Regression: FASL Loading Broken

**Status:** ❌ **BLOCKING**

The system **used to load fasls without trouble**. Now:
- `level-1.lafsl` returns -7 (load failure)
- `minimal.image` fails strict bootstrap
- `root.image` has bootstrap symbol resolution failures

**This is a regression that must be fixed before new features.**

### Code Cleanup Needed

**Status:** ⚠️ Technical debt

There is **code from previous attempts littered throughout** the codebase that needs removal:
- Obsolete approaches to image loading
- Superseded bootstrap mechanisms
- Unused diagnostic scaffolding
- Conflicting terminology ("replacement lane" vs actual use cases)

**Impact:** Makes debugging harder, obscures working code paths.

---

## Two Deployment Modes (Architecture)

### Mode 1: Library/Embedded Mode

**Use case:** CCL WASM as a library/DLL embedded in web applications

**Characteristics:**
- ✅ Single WASM runner (no threading)
- ✅ postMessage interface for external communication
- ✅ Works in any browser context (no secure requirements)
- ✅ Limited capabilities (no persistence, no FFI, stdio only)
- ✅ Small footprint, fast startup

**Target users:** Developers embedding Lisp in existing apps

**Example:**
```html
<script src="ccl-wasm.js"></script>
<script>
  CCL.eval("(+ 1 2)").then(result => console.log(result));
</script>
```

### Mode 2: Full Runtime Mode

**Use case:** Complete development environment (web-ui/ide vision)

**Characteristics:**
- ⚠️ Multi-runner with Web Workers
- ⚠️ SharedArrayBuffer + Atomics for coordination
- ⚠️ Requires secure context (COOP + COEP headers)
- ⚠️ Full storage backend (IndexedDB)
- ⚠️ Complete IDE capabilities
- ⚠️ Larger footprint, richer features

**Target users:** Developers using CCL as their primary environment

**Requirements:**
```http
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp
```

**Note:** Requires hosting control, cannot be embedded in arbitrary sites.

---

## Two-Phase Strategy

### MVP-1: Library/Embedded Mode (Current Focus)

**Goal:** Ship a working single-runner CCL WASM that can be embedded in web apps

**Prerequisites:**
1. ✅ WASM kernel builds
2. ✅ Basic compiler works (constants, fixnums, control flow)
3. ❌ **FASL loading works** (currently broken - regression)
4. ❌ **Image bootstrap stable** (currently broken)
5. ❌ Symbol/function dispatch reliable (currently unstable)
6. ⚠️ Single-runner REPL functional
7. ⚠️ postMessage API defined and tested

**Success criteria:**
- Can load and run Lisp code dynamically
- REPL works end-to-end
- Can be embedded via `<script>` tag
- Documented limitations clear
- Real users can evaluate it

**Timeline:** Fix regressions first, then stabilize, then ship

### MVP-2: Full Runtime Mode (Future)

**Goal:** Multi-runner environment with full IDE capabilities

**Prerequisites:**
1. ✅ MVP-1 shipped and validated
2. ❌ Multi-runner coordination design finalized
3. ❌ SharedArrayBuffer ring buffers implemented
4. ❌ Worker spawn/clone from image
5. ❌ Secure context detection and gating
6. ❌ Storage backend (IndexedDB integration)
7. ❌ web-ui/ide integration

**Success criteria:**
- Multiple runners communicate via SAB
- Full development environment works
- Persistence across sessions
- Thread-like concurrency model
- Production-ready for hosted use

**Timeline:** After MVP-1 is stable and field-tested

---

## Detailed Phases

### ✅ Phase 1: Kernel Bring-up (DONE)

**Goal:** Kernel compiles and links as freestanding WASM

**Status:** Complete

**Delivered:**
- `lisp-kernel/wasm32/` builds to `wasmcl.wasm` (~1MB)
- KERNEL_IMPORTS table defined
- `kernel_request` ABI wrappers
- Manual cstack management
- Step/yield entrypoints

**Reality check:** This works and is stable.

---

### ✅ Phase 2: JS Microkernel MVP (DONE)

**Goal:** Minimal JS host that can drive the kernel

**Status:** Complete

**Delivered:**
- `kernel_request` implementation (CAPS, LOG, STREAM, TIME_NOW)
- Named byte sources for NAMED_RO streams
- Runner scaffolding (single runner only)
- Basic I/O (stdin/stdout/stderr)

**Reality check:** stdio works, basic kernel interaction works.

---

### ⚠️ Phase 3: Compiler Backend (PARTIAL)

**Goal:** Emit WASM code compatible with subprims ABI

**Status:** Minimal implementation only (~8,900 lines)

**What works:**
- ✅ Constants (nil, t, fixnums, symbols)
- ✅ Fixnum arithmetic (add, sub, mul, ash, logical ops)
- ✅ Basic control flow (if, progn, block/return-from, tagbody/go)
- ✅ Catch/throw via subprims
- ✅ Unwind-protect (cooperative cleanup)
- ✅ Closures (basic capture cells)
- ✅ Multi-value support (values, mv-bind, nth-value)

**What's missing:**
- ❌ Arrays and vectors
- ❌ Hash tables
- ❌ Structures and classes (CLOS)
- ❌ Optimization passes
- ❌ Type checking (documented but not implemented)
- ❌ Most Common Lisp features

**Blockers:**
- Need stable runtime before expanding compiler
- Should validate minimal feature set works first

---

### ❌ Phase 4: Image Loading & Bootstrap (BROKEN - REGRESSION)

**Goal:** Load images and boot to toplevel

**Status:** Broken (used to work)

**Current failures:**
- ❌ `level-1.lafsl` returns -7 (load failure)
- ❌ `minimal.image` fails strict bootstrap
- ❌ `root.image` has symbol resolution failures
- ❌ Core symbol/function dispatch unstable during persistence

**Tracking:**
- [wasm-ui-persistence-problem-tracker.md](wasm-ui-persistence-problem-tracker.md)
- Various logs in `doc/wasm/repro/`

**This is the #1 blocker for MVP-1.**

**Required actions:**
1. Identify what changed to break fasl loading
2. Fix the regression
3. Stabilize bootstrap symbol resolution
4. Clean up obsolete code from previous attempts
5. Add regression tests to prevent future breakage

---

### ⏸️ Phase 5: Multi-Runner Architecture (DEFERRED to MVP-2)

**Goal:** SharedArrayBuffer-based multi-runner coordination

**Status:** Not started (intentionally deferred)

**Design exists for:**
- Per-runner heaps with explicit communication
- SAB-based ring buffers for hot paths
- Worker spawn/clone from image
- Message routing between runners

**Not implementing until:**
- MVP-1 is stable and shipped
- Single-runner mode is field-tested
- Clear user demand for threading model

**When implemented:**
- Requires secure context (COOP + COEP)
- No fallback to single-runner (fail explicitly)
- Targets Full Runtime Mode only

---

### ⏸️ Phase 6: Storage Backend (DEFERRED to MVP-2)

**Goal:** Persistent storage via IndexedDB

**Status:** Not started

**Design exists in:**
- [persistence-service-spec.md](persistence-service-spec.md)
- Current memory-snapshot backend is legacy compatibility only

**Requirements:**
- Secure context (same as multi-runner)
- Full Runtime Mode only
- Library Mode has no persistence (by design)

**Not implementing until:** MVP-2

---

### ⏸️ Phase 7: Web UI/IDE Integration (DEFERRED to MVP-2)

**Goal:** Full browser-based development environment

**Status:** Reference implementation exists, integration broken

**Current state:**
- ✅ UI spec exists: [browser-ui-spec.md](browser-ui-spec.md)
- ✅ Reference JS implementation in `web-ui/`
- ⚠️ Lisp↔JS bridge partially implemented
- ❌ Full integration blocked by image loading regression

**Not implementing until:**
- MVP-1 stable
- Image loading fixed
- Bootstrap stable
- MVP-2 multi-runner architecture in place

---

## Current Focus (Next 30 Days)

### Priority 1: Fix Regressions ❌ BLOCKING

**Tasks:**
1. Debug and fix `level-1.lafsl` load failure (returns -7)
2. Fix minimal.image bootstrap failures
3. Fix root.image symbol resolution
4. Stabilize core symbol/function dispatch
5. Add regression tests

**Success metric:** Can boot to toplevel reliably

### Priority 2: Code Cleanup ⚠️

**Tasks:**
1. Remove obsolete code from previous attempts
2. Consolidate bootstrap mechanisms
3. Clean up diagnostic scaffolding
4. Update confusing terminology (replace "replacement lane" with "Full Runtime Mode")
5. Document what's obsolete vs active

**Success metric:** Clear code paths, easier debugging

### Priority 3: Stabilize Single-Runner MVP-1 ⚠️

**Tasks:**
1. Validate compiler backend features work end-to-end
2. Define and implement postMessage API
3. Create embedding examples
4. Write integration tests
5. Document limitations clearly

**Success metric:** MVP-1 shippable

---

## What We're NOT Doing (Yet)

These are explicitly deferred until MVP-1 is stable:

- ❌ Multi-runner/threading implementation
- ❌ SharedArrayBuffer coordination
- ❌ Storage backend (IndexedDB)
- ❌ Web UI/IDE integration
- ❌ Quicklisp/ASDF compatibility
- ❌ FFI/callbacks
- ❌ Networking
- ❌ Complex data structures (arrays, hash tables, CLOS)
- ❌ Optimization passes

**Rationale:** These require working foundation. Fix what's broken, ship what works, then expand.

---

## Success Criteria by Phase

### MVP-1 Success (Library/Embedded Mode)
- [ ] FASL loading works (regression fixed)
- [ ] Bootstrap to toplevel reliable
- [ ] Can define and call Lisp functions
- [ ] REPL functional in browser
- [ ] postMessage API documented and tested
- [ ] Embedding examples working
- [ ] Known limitations documented
- [ ] At least 3 external users successfully embed it

### MVP-2 Success (Full Runtime Mode)
- [ ] Multi-runner spawning works
- [ ] SAB-based coordination functional
- [ ] Storage backend persists across sessions
- [ ] Web UI/IDE fully integrated
- [ ] Can develop real applications in-browser
- [ ] Performance acceptable for interactive use
- [ ] Deployment guide for secure context setup

---

## Key Architectural Decisions

### Two Modes Are Intentional

**Library Mode** and **Full Runtime Mode** serve different users:
- Library users want embeddability and simplicity
- Full runtime users want power and don't mind secure context requirements

**This is not a fallback strategy.** Both modes are first-class, designed for different scenarios.

### Sequential Delivery Strategy

We're building Library Mode first because:
1. It's simpler (validates architecture)
2. It has clear deliverable (embeddable CCL WASM)
3. It provides user feedback
4. It doesn't require solving hard concurrency problems
5. Foundation must work before adding threading complexity

### No Silent Degradation

Both modes fail explicitly when capabilities are unavailable:
- Library Mode signals CAPABILITY-UNAVAILABLE for threading, storage, etc.
- Full Runtime Mode refuses to start without secure context
- No "try threading, fall back to single-runner" behavior

This preserves clarity about what works in which mode.

---

## Status Legend

- ✅ Complete and working
- ⚠️ Partial implementation or has known issues
- ❌ Not working or broken
- ⏸️ Intentionally deferred

---

## Document Cross-References

- **Current status:** [README.md](README.md)
- **Architecture vision:** [project-overview.md](project-overview.md)
- **Feature details:** [porting-status.md](porting-status.md)
- **Active blockers:** [wasm-ui-persistence-problem-tracker.md](wasm-ui-persistence-problem-tracker.md)
- **Build instructions:** [build.md](build.md)
