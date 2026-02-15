## Project overview

**Status: Early Development / Experimental** • **See [README.md](README.md) for current implementation status**

This is a **Common Lisp system derived from CCL's architecture** that targets **WebAssembly as the primary execution substrate**, with a **JavaScript microkernel** acting as the host "operating environment." The goal is not to cram a POSIX Lisp into the browser; the goal is to deliver the **rational, portable parts of Common Lisp**—a **Lisp-2**, **macro system**, **reader/printer**, dynamic function definition/loading—inside a WASM process model that is honest about the web.

**WASM instances serve as "processes"** (webrunners), with the JS side acting as a small, explicit kernel that provides capabilities the runtime cannot provide itself: spawning, linking, I/O, scheduling, and coordination.

**This document describes the architectural vision and design goals.** For what's actually implemented vs. what remains broken or incomplete, see [README.md](README.md) and [porting-status.md](porting-status.md).

## Design goals and constraints

**Note**: These are design goals. Implementation status varies significantly—see markers below and [README.md](README.md) for reality.

* **Keep the root Lisp minimal** so it can be **cloned** cheaply (spawn-from-image is the intended mechanism). - ⚠️ Design complete, implementation broken
* **Dynamic loading** is essential: you want to **add new functions to a running environment** in WASM (not "spin up compilers," not "rebuild the world"). - ❌ Currently broken (image loading fails)
* **Safepoints are assumed** in generated code (same category of "given" as type checks): for interrupts, cancellation, and any future concurrency coordination. - ⚠️ Architectural assumption, partial implementation
* **Strings use UTF-8 wire format** (CCL's internal UTF-32 ↔ UTF-8 at boundary ↔ JS's UTF-16) for full Unicode support from day one. - ✅ Design complete
* **Full Runtime Mode (MVP-2) concurrency**: Secure-context-only startup requires worker/thread capability and shared-memory coordination for hot paths, while CL thread semantics remain explicitly deferred. - ❌ Not implemented (single-runner only)
* **Quicklisp compatibility is a post‑MVP goal**: design the capability‑gated VFS so Quicklisp/ASDF can be enabled later, but keep it out of the current MVP scope. - ⏸️ Deferred as planned

**Legend**: ✅ Working | ⚠️ Partial | ❌ Not working | ⏸️ Intentionally deferred

## Big architecture: two halves

### 1) The JS microkernel (host-side)

The JS side is a **microkernel**, not an application wrapper. It owns the browser-specific reality and presents a narrow interface to the Lisp world.

**High-level responsibilities** (implementation status varies):

* **Runner lifecycle**
  * spawn a new runner (Web Worker + WASM instance) - ❌ not implemented (single-runner only)
  * spawn-from-image / clone semantics - ❌ broken (image loading fails)
  * terminate / restart / supervise runners - ❌ not implemented

* **Module management**
  * fetch/load WASM modules and associated assets - ⚠️ basic loading works
  * link modules (WASM dynamic linking) - ⚠️ minimal, not tested
  * enforce a minimal "root image" that new runners clone - ❌ broken (bootstrap failures)

* **I/O and capability boundary**
  * all external interaction mediated by kernel - ✅ working (`kernel_request` ABI)
  * Lisp makes requests, not syscalls - ✅ architecture enforced
  * stream semantics (stdin/stdout/stderr) - ✅ working via `kernel_request`
  * timers - ❌ capability-gated, not in MVP
  * filesystem-like abstractions - ⚠️ virtual-only stub (signals errors)
  * UI/DOM interaction - ⚠️ partial (post-MVP, see browser-ui-spec.md)

* **Coordination and messaging**
  * shared-memory channels for hot paths - ❌ not implemented
  * message/copy paths for bootstrap/control - ⚠️ basic support only

**Current reality**: The microkernel exists and handles basic I/O (`kernel_request`), but multi-runner coordination, shared-memory transport, and advanced features are not implemented.

In spirit, the JS microkernel is the "world," and a runner is a process that lives inside it.

## Browser UI Toolkit (MVP-2 - Partial Implementation)

**Status: Deferred to MVP-2 per phased strategy (see [README.md](README.md) and [roadmap.md](roadmap.md))**

The browser UI toolkit is specified in [browser-ui-spec.md](browser-ui-spec.md). A reference JavaScript implementation of the UI state model, command system, and rendering backends exists in `web-ui/` and is used for deterministic tests.

**Current implementation gaps:**
- Lisp↔JS runtime bridge partially implemented (output/event flow, typed commands)
- Fully compiled Lisp UI persistence path blocked by runtime bootstrap/function-binding instability
- Image loading has documented failures (`level-1.lafsl` returns -7, minimal.image bootstrap issues)
- Core symbol/function dispatch instability during persistence operations (tracked in [wasm-ui-persistence-problem-tracker.md](wasm-ui-persistence-problem-tracker.md))

Root-image/toplevel non-interactive boot gating is in place, and the default unattended persistence backend is memory-first (`memory-snapshot`), but overall UI functionality remains experimental.

## Capability model (host feature matrix)

**Status**: ✅ Architecture implemented and working

Because browser embeddings differ (sandboxed iframe vs. dedicated worker, `crossOriginIsolated` vs. not, storage policy, networking policy, etc.), the system uses an explicit capability model:

* The microkernel advertises which host capabilities exist in the current embedding - ✅ working
* When Lisp code requests a missing capability, it MUST fail explicitly (no silent fallback) - ✅ enforced
* The Lisp-level failure mode is a condition of type `CAPABILITY-UNAVAILABLE` carrying a canonical capability key and operation name - ✅ implemented

The canonical capability keys and the CLHS-ish feature mapping live in [capability-matrix.md](capability-matrix.md).

**Implementation note**: The capability gating mechanism works correctly. Most capabilities are currently unavailable (FFI, networking, real filesystem, threading) because those features aren't implemented yet, not because of browser limitations.

### 2) The Lisp backend (CCL-derived)

On the Lisp side, the target is **a real Common Lisp environment**—but "real" in the sense of language machinery and developer experience, not "real" in the sense of pretending the browser is Unix.

**Architectural goals** (implementation status varies—see [README.md](README.md)):

* **Lisp-2** (separate function and value namespaces) - ✅ core semantics implemented
* **Macros** as first-class compile-time tools - ⚠️ basic support, limited testing
* **Reader and printer** - ⚠️ basic functionality, UTF-8 wire format
* **Dynamic loading / redefining** functions into a live image - ❌ currently broken (image loading returns -7)
* A compilation pipeline that can emit WASM-compatible code:
  * **Compiler backend** - ⚠️ ~8,900 lines, supports only constants, fixnum arithmetic, basic control flow
  * **Missing**: arrays, hash tables, structures, classes, optimization passes
  * **safepoints** - ✅ architectural assumption, implementation partial
  * **type checks** - ❌ mostly absent (documented as "given" but not implemented)

**Reality check**: The current implementation is a minimal proof-of-concept that demonstrates basic Lisp compilation to WASM. Most Common Lisp features are missing or stubbed. See the maturity matrix in [README.md](README.md#-implementation-maturity-matrix) for component-by-component status.

The important separation is that the Lisp runtime is a language system, while "the OS" is the microkernel.

## Execution model and concurrency roadmap

**Current Implementation Status**: Single-runner only. Concurrency architecture is designed but not implemented.

### Full Runtime Mode (MVP-2): secure shared-memory runtime (PLANNED)

**Status: Architecture defined, implementation deferred to MVP-2**

The Full Runtime Mode design requires secure runtime capabilities at startup:

* Worker/thread runtime capability required for runtime execution - ❌ not implemented
* Shared-memory coordination (SAB + Atomics) for hot-path transport - ❌ not implemented
* Strict no-fallback startup - ❌ not enforced yet

### Library Mode (MVP-1): Single-runner implementation

**Status: Partially working (blocked by fasl loading regression)**

The current implementation provides:

* Single WASM instance execution (no threading)
* **Safepoints** - ✅ architectural assumption, partial implementation
* Basic interrupt mechanism - ⚠️ planned in [INTERRUPT-WORK.md](INTERRUPT-WORK.md), minimal tests only
* Image spawning - ❌ broken (image loading fails)

### Multi-runner architecture (MVP-2)

Multi-runner concurrency ("threads" as separate runner instances/workers) is architecturally designed but not yet implemented. Each runner having its own heap with explicit inter-runner communication is the architectural intent, but only single-runner execution (MVP-1) currently exists.

## Memory and GC: per-runner heap model

**Design Status**: Architecture complete, single-runner implementation only

The intended approach:

* **Each runner has its own heap** - ✅ design complete (but only one runner exists)
* Communication through **shared memory channel** or messaging - ❌ not implemented (no multi-runner support)

That design has a decisive semantic consequence: Lisp heap objects do not naturally cross runner boundaries. Inter-runner communication becomes:

* serialized data, or
* shared foreign/binary buffers with explicit lifetime rules, or
* handles/references managed by the microkernel

**Current reality**: Single heap in single runner. GC is local as designed, but multi-runner coordination doesn't exist yet, so the architectural benefits are theoretical.

This keeps GC local and avoids the shared-heap coordination problem (once multiple runners are implemented).

## Object representation and tagging

**Status**: ✅ Architecture defined and implemented for basic types

The WASM backend follows CCL's tagged-object approach, with the representation and tagging parameters determined by the target word size and alignment. WASM32 and WASM64 therefore use target-appropriate tagged words and layouts; shared tag-manipulation code should read the target's tag configuration rather than baking in a single layout.

**Current implementation**: Basic tagged objects work (fixnums, cons cells, symbols). Complex types (arrays, hash tables, structures, classes) are not yet implemented in the compiler backend.

## Strings and Characters: UTF-32 ↔ UTF-8 ↔ UTF-16

**Status**: ✅ Design complete, implementation in progress

**The Three-Encoding Model:**

```
CCL (internal)  →  Wire Protocol  →  JavaScript (internal)
   UTF-32       ↔     UTF-8       ↔      UTF-16
```

**Design principles:**

* **CCL side (internal):** Keep CCL's native UTF-32 character representation (32-bit Unicode codepoints)
  - No artificial limitations
  - Full Unicode support as CCL expects
  - No conversion overhead within Lisp code

* **Boundary (wire format):** UTF-8 encoding for all strings crossing CL↔JS boundary
  - Standard web encoding
  - Compact for common text (1 byte for ASCII, 2-3 bytes for most Unicode, up to 4 for all codepoints)
  - Use TextEncoder/TextDecoder on JS side (standard browser APIs)
  - Kernel exports: `wasm_string_to_utf8`, `wasm_utf8_to_string`

* **JavaScript side (internal):** Keep JS's native UTF-16 string representation
  - No conversion overhead within JS code
  - TextEncoder/TextDecoder handle UTF-8 ↔ UTF-16 automatically

**Why UTF-8 at the boundary:**
- Standard web practice
- Efficient encoding
- No surrogate pair issues (unlike UTF-16)
- No size overhead (unlike UTF-32 which is always 4 bytes)
- Full Unicode support
- TextEncoder/TextDecoder are fast, well-tested browser APIs

**Implementation:** Convert only at the boundary; each side uses its native representation internally. Minimal overhead (~10 lines of conversion code per side).

**See:** [decisions.md](decisions.md) ADR-0002 for detailed rationale.

## How CCL fits in

**Status**: Architectural structure in place, implementation incomplete

The project is "derived from CCL" in the sense that it uses CCL's worldview—kernel/runtime split, backend directories per target ABI, explicit low-level build control—as the structural model, but adapted to a host where:

* there is no OS syscall surface you control - ✅ architecture honors this
* the loader and I/O are host-mediated - ⚠️ I/O works, loader broken
* Full Runtime Mode (MVP-2) concurrency and shared memory required at startup - ❌ not implemented
* "target triples" less important than "execution world + ABI constraints" - ✅ approach followed

**Current reality**: The CCL directory structure and conventions are followed (`compiler/WASM/`, `lisp-kernel/wasm32/`, etc.), but the implementation is far more minimal than CCL's other backends. The backend name encodes a concrete ABI world (WASM32/WASM64), as CCL intends, but the actual implementation is a small subset of what those names might imply.

## Canonical rebuild command

To avoid out-of-sync artifacts, use one orchestrator command as the default:

```bash
scripts/wasm/rebuild-everything.sh
```

Script path: `scripts/wasm/rebuild-everything.sh`

This runs the full dependency-ordered rebuild:

1. `lisp-kernel/wasm32` (`build/wasm32/kernel/wasmcl.wasm`) - ✅ builds successfully
2. `build/wasm32/wasm-boot.image` - ⚠️ builds but has stability issues
3. runtime fasls/modules (`build/wasm32/modules/wasm-runtime-modules.json` and `.idx`) - ⚠️ partial
4. versioned startup artifacts:
   `build/wasm32/modules/bootstrap-l0-contract.v1.json` and
   `build/wasm32/modules/startup-symbol-scope.source_scope_v1.json` - ✅ generates
5. `build/wasm32/images/root.image` + manifest/resolution outputs - ❌ has documented bootstrap failures

**Note**: Build completion doesn't guarantee runtime stability. See [README.md](README.md) for current execution status.

Yes: this includes the versioned-artifact refresh path (the contract sidecar + startup symbol scope generation), so those files are regenerated in the same run instead of by separate ad hoc commands.

## Summary: Vision vs. Current Reality

**Architectural Vision**: A **CCL-structured Common Lisp** that runs as a **WASM process**, hosted by a **JS microkernel**.

**Design Goals** (see [README.md](README.md) for implementation status):

* ⚠️ Minimal clonable root image - designed, but image loading currently broken
* ❌ Dynamic function/module loading into live images - broken (`level-1.lafsl` fails)
* ✅ Explicit I/O boundary - working (host capabilities instead of syscalls)
* ⚠️ Mandatory safepoints in generated code - architectural assumption, partial implementation
* ✅ UTF-8 wire format for strings - design complete (UTF-32 internal, UTF-8 boundary, full Unicode)
* ❌ Full Runtime Mode (MVP-2) - not implemented
  * Worker/shared-memory runtime capability - not implemented
  * Currently single-runner only (MVP-1), no threading
* ✅ Per-runner heaps design - architecture complete (but only one runner exists)

**Current State**: This is a **working proof-of-concept** that demonstrates:
- WASM kernel compilation
- Basic Lisp expression compilation (constants, fixnum arithmetic, simple control flow)
- Minimal exception handling (catch/throw)
- stdio via kernel_request

It is **NOT yet**:
- A stable runtime environment
- Feature-complete for Common Lisp
- Capable of dynamic loading (broken)
- Multi-runner/threaded (not implemented)

See [README.md](README.md) for detailed status and [porting-status.md](porting-status.md) for feature-by-feature breakdown.
