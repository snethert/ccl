# CCL→WASM Roadmap (Two-Mode, Two-Phase Strategy)

**Status:** Active
**Scope:** Development roadmap, phased delivery strategy, and current priorities
**Last Updated:** 2026-02-15
**Doc Version:** 1.0.0

**See also:** [README.md](README.md) for current status, [porting-status.md](porting-status.md) for detailed features

---

## Executive Summary

This port targets **two distinct deployment modes**:

1. **Library/Embedded Mode** - Single-runner, postMessage interface, works in any context
2. **Full Runtime Mode** - Multi-runner, SharedArrayBuffer, secure context required, full IDE capabilities

**Current Strategy:** Build Library Mode first (MVP-1), then Full Runtime Mode (MVP-2).

**Rationale:** Library Mode is simpler, validates core architecture, and provides a shippable artifact. Full Runtime Mode requires working foundation plus threading/SAB coordination.

---

## Current Status

### What's Been Fixed

- ✅ **RESTORE-LISP-POINTERS** called after image load (package hash tables rebuilt)
- ✅ **Build pipeline** end-to-end functional (kernel → boot image → modules → root image attempt)
- ✅ **Instrumentation cruft** removed (~2400 lines C, ~2100 lines JS/Lisp/shell)
- ✅ **Startup truth feature** fully retired
- ✅ **Startup binding map** removed (~2500 lines, was unnecessary workaround)
- ✅ **Boot image auto-build** when missing during root image build
- ✅ **Build artifacts** resolved (subprims.wasm, runtime modules, stale paths fixed)

### Current Blocker

**B2: Compiled module installation skips 99.97% of modules** (7555/7557)

- Root image build reaches FASL loading but fails
- Module installer rejects almost all modules — only 2 install
- FASL loading traps with "table index is out of bounds"
- Uninvestigated — next critical-path task

See [TODO.md](../../TODO.md) for full details.

### Code Cleanup Completed

- ✅ Removed ~2400 lines of kernel instrumentation (wasm_emit_*, wasm_debug_*, startup truth)
- ✅ Removed ~2100 lines of JS/Lisp/shell dead code referencing deleted exports
- ✅ Removed ~2500 lines of startup binding map infrastructure (6 files deleted)
- ✅ Retired startup truth feature (env var path shell → JS → C → Lisp eliminated)
- ⚠️ Remaining: obsolete image loading mechanisms, "replacement lane" terminology in some docs

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
- ⏸️ Multi-runner with Web Workers
- ⏸️ SharedArrayBuffer + Atomics for coordination
- ⏸️ Requires secure context (COOP + COEP headers)
- ⏸️ Full storage backend (IndexedDB)
- ⏸️ Complete IDE capabilities
- ⏸️ Larger footprint, richer features

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
3. ✅ Image loading works (RESTORE-LISP-POINTERS fixed)
4. ✅ Build pipeline end-to-end functional
5. ❌ **Compiled module installation** (B2 — 7555/7557 skipped)
6. ❌ **FASL loading works end-to-end** (blocked by B2)
7. ❌ Symbol/function dispatch reliable
8. ❌ Single-runner REPL functional
9. ⏸️ postMessage API defined and tested

**Success criteria:**
- Can load and run Lisp code dynamically
- REPL works end-to-end
- Can be embedded via `<script>` tag
- Documented limitations clear
- Real users can evaluate it

**Timeline:** Fix B2, then stabilize, then ship

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

**Delivered:**
- `lisp-kernel/wasm32/` builds to `build/wasm32/kernel/wasmcl.wasm` (~1MB)
- KERNEL_IMPORTS table defined
- `kernel_request` ABI wrappers
- Manual cstack management
- Step/yield entrypoints

---

### ✅ Phase 2: JS Microkernel MVP (DONE)

**Goal:** Minimal JS host that can drive the kernel

**Delivered:**
- `kernel_request` implementation (CAPS, LOG, STREAM, TIME_NOW)
- Named byte sources for NAMED_RO streams
- Runner scaffolding (single runner only)
- Basic I/O (stdin/stdout/stderr)

---

### ⚠️ Phase 3: Compiler Backend (PARTIAL)

**Goal:** Emit WASM code compatible with subprims ABI

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
- ❌ Type checking

---

### ⚠️ Phase 4: Image Loading & Bootstrap (PARTIAL)

**Goal:** Load images and boot to toplevel

**What works:**
- ✅ Image loading into memory (sections map correctly)
- ✅ RESTORE-LISP-POINTERS called (package hash tables rebuilt)
- ✅ Boot image build and auto-build
- ✅ Compiled module compilation (7557 modules)
- ✅ Build pipeline orchestration

**Current blocker:**
- ❌ Compiled module installation (B2): 7555/7557 modules skipped
- ❌ FASL loading (blocked by B2): function table entries not populated
- ❌ Root image bootstrap (blocked by B2)

**Required actions:**
1. Investigate why module installer rejects 99.97% of modules
2. Fix module installation
3. Validate FASL loading end-to-end
4. Stabilize bootstrap symbol resolution
5. Add regression tests

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

---

### ⏸️ Phase 6: Storage Backend (DEFERRED to MVP-2)

**Goal:** Persistent storage via IndexedDB

**Status:** Not started

**Requirements:**
- Secure context (same as multi-runner)
- Full Runtime Mode only
- Library Mode has no persistence (by design)

---

### ⏸️ Phase 7: Web UI/IDE Integration (DEFERRED to MVP-2)

**Goal:** Full browser-based development environment

**Status:** Reference implementation exists, integration blocked by runtime stability

---

## Current Focus

### Priority 1: Fix Compiled Module Installation ❌ BLOCKING

**Task:** Investigate and fix B2 (7555/7557 modules skipped)

**Success metric:** All or nearly all compiled modules install successfully

### Priority 2: Validate FASL Loading ❌ (blocked by P1)

**Task:** End-to-end FASL loading after module installation fixed

**Success metric:** Can boot to toplevel reliably

### Priority 3: Stabilize Single-Runner MVP-1 ⏸️

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

- ⏸️ Multi-runner/threading implementation
- ⏸️ SharedArrayBuffer coordination
- ⏸️ Storage backend (IndexedDB)
- ⏸️ Web UI/IDE integration
- ⏸️ Quicklisp/ASDF compatibility
- ⏸️ FFI/callbacks
- ⏸️ Networking
- ⏸️ Complex data structures (arrays, hash tables, CLOS)
- ⏸️ Optimization passes

**Rationale:** Fix what's broken, ship what works, then expand.

---

## Success Criteria by Phase

### MVP-1 Success (Library/Embedded Mode)
- [ ] Compiled module installation works (B2 fixed)
- [ ] FASL loading works end-to-end
- [ ] Bootstrap to toplevel reliable
- [ ] Can define and call Lisp functions
- [ ] REPL functional in browser
- [ ] postMessage API documented and tested
- [ ] Embedding examples working
- [ ] Known limitations documented

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

Library Mode first because:
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

---

## Related Documentation

- **Current status:** [README.md](README.md)
- **Architecture vision:** [project-overview.md](project-overview.md)
- **Feature details:** [porting-status.md](porting-status.md)
- **Task tracking:** [TODO.md](../../TODO.md)
- **Build instructions:** [build.md](build.md)
- **Decisions:** [decisions.md](decisions.md)
