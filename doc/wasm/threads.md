# Threading (Shared-Heap) Concerns and Requirements

**Status:** Draft

## Scope

This document records the constraints and requirements for the **optional shared-heap, multi-runner execution mode**.

The baseline bring-up target remains **single-runner** (no shared memory/Atomics required). This document exists so that if/when shared-heap threading is pursued, the constraints are explicit up front rather than discovered by failure.

It covers:

- What “threads” mean in this project (runners + shared heap)
- Platform prerequisites (SharedArrayBuffer, Atomics, worker restrictions)
- Required runtime/compiler mechanisms (TCRs, safepoints, GC coordination, synchronization)
- Consequences for I/O, dynamic loading, and failure handling

It does **not** define the full GC algorithm, the full object layout, or the full kernel/runner message schema.

## Definitions

- **World:** One Lisp runtime instance: **one shared heap** (shared linear memory) + shared global runtime state.
- **Runner:** One WASM instance (typically inside a Web Worker) that executes **one Lisp thread** in a world.
- **TCR:** Per-thread runtime record (CCL terminology) holding registers/roots/stacks/flags needed to run and to stop safely.
- **Safepoint:** A compiler-inserted point where a runner can be safely interrupted/handshaken for GC, interrupts, or cancellation.

## Model (What “shared heap threads” means)

- All Lisp threads in a world share the same heap, so Lisp objects are naturally visible across threads.
- A runner is “a thread” only in the sense of *concurrent execution*; each runner has distinct per-thread state (TCR, stacks, bindings).
- Host capabilities (I/O, timers, UI) remain mediated by the JS microkernel; shared heap does not imply shared host objects.

## Platform prerequisites / constraints

### Shared memory and Atomics

True parallel threads require:

- `SharedArrayBuffer`-backed `WebAssembly.Memory` (`shared: true`, and a fixed `maximum`).
- WebAssembly threads features (atomic instructions) enabled in the toolchain and runtime.
- In browsers: a `crossOriginIsolated` environment (COOP/COEP) to enable `SharedArrayBuffer`.

If shared memory/Atomics are unavailable, the system MUST run in a single-runner mode and MUST fail thread creation explicitly.

### Blocking and `Atomics.wait`

- Browsers generally forbid `Atomics.wait` on the main thread; blocking waits must occur in workers.
- If a runner blocks waiting for I/O completion, it should do so via an atomic wait on shared memory (or via cooperative yield/resume in single-runner mode).

## Shared state placement (avoid “per-instance globals” bugs)

Because each runner is a separate WASM instance:

- Any runtime state that is logically shared across threads MUST live in shared linear memory (the shared heap).
- Per-instance WASM globals are only safe for per-thread/TLS-like state (e.g., “current TCR pointer” for that runner).
- Compiled code MUST NOT assume that mutable WASM globals are shared across runners.

Practical consequence: “the heap” is necessary but not sufficient; the runtime must be structured so that shared invariants are memory-backed.

## Per-thread state requirements (TCR, stacks, bindings)

Each runner/thread MUST have:

- A TCR stored in shared memory (so other threads/GC can locate it).
- A binding stack / special binding state (dynamic variables are thread-local in Common Lisp).
- A control stack (“cstack”) region and any value/call stacks (CCL VSP/CSP analogs).
- Thread-local flags: interrupt pending, safepoint state, stop-the-world handshake state, etc.

The ABI needs a reliable “current TCR” lookup. The current bring-up model exposes:

- `wasm_set_current_tcr(TCR*)`
- `wasm_get_current_tcr() -> TCR*`

Host responsibility: the microkernel MUST set the runner’s current TCR before entering Lisp code in that runner.

## Safepoints and interrupts

Safepoints are the mechanism that makes shared-heap threading implementable:

- The compiler MUST insert safepoints frequently enough to provide bounded interrupt latency and to allow GC handshakes.
- At a safepoint, a runner MUST be in a state where:
  - its roots are discoverable (via TCR-held registers/stack pointers),
  - it can observe stop-the-world/interrupt flags,
  - it can park (block) without holding internal runtime locks indefinitely.

Interrupt delivery model:

- There are no Unix signals in the browser; “interrupts” must be implemented as flags in shared memory + polling at safepoints.
- “Interrupt this thread” becomes: set flag in that thread’s TCR and (optionally) wake it via `Atomics.notify`.

## Garbage collection coordination (shared heap)

With a shared heap, GC MUST coordinate across runners:

- The world MUST maintain a registry of all thread TCRs (in shared memory).
- A stop-the-world GC MUST:
  1. request a world stop (shared flag),
  2. cause all runners to reach a safepoint and acknowledge “stopped,”
  3. scan roots from all TCRs/stacks,
  4. perform collection/compaction as needed,
  5. resume runners.

Key concern: roots in WASM locals/registers are not externally visible. The compiler/runtime MUST ensure that any live Lisp pointers are representable in memory at safepoints (e.g., spilled to known stack locations and/or recorded in the TCR).

## Synchronization primitives and memory ordering

To preserve runtime invariants under parallel execution:

- The runtime MUST provide low-level synchronization primitives (mutex, condition variable/event) implemented on shared memory with Atomics.
- Internal runtime structures (allocator/ALLOCPTR, symbol/value cells, hash tables, package state, etc.) MUST be protected by locks or made lock-free with well-defined atomic protocols.
- Publication of newly allocated objects visible to other threads MUST use appropriate ordering (store-release / load-acquire patterns).

Common Lisp does not require data-race-free behavior for unsynchronized shared mutation; the implementation may treat racy code as undefined behavior. However, the runtime itself MUST be data-race-free for its own shared structures.

## Dynamic loading, redefinition, and “code identity”

Shared heap implies shared definitions:

- Loading/redefining functions affects the world and MUST be synchronized (a world lock or stop-the-world phase).
- If callable code is represented via table indices or other indirections, updating that indirection MUST be done atomically and made visible to all runners.
- If each runner has its own function table, dynamic loading MUST update all runners’ tables consistently (or the design MUST use a single shared indirection that all runners consult).

This area is a primary threading concern because it couples:

- global mutability (function cells, fdefinition, generic function caches),
- visibility/publication semantics, and
- per-runner instantiation details (tables/instances are not automatically shared).

## I/O and the JS microkernel boundary

Even with shared heap threads:

- Host capabilities are not shared “by pointer”; all I/O remains mediated by the microkernel.
- Runner→kernel requests MUST be thread-safe (kernel request queues, IDs, completion signaling).
- A runner waiting for a kernel response may block via an atomic wait on shared memory (worker-only), or yield cooperatively in single-runner mode.

## Failure modes and lifecycle concerns

- If a runner terminates unexpectedly, the world MUST handle orphaned TCRs/locks (at minimum: mark the thread dead and avoid waiting for its safepoints forever).
- Stop-the-world protocols MUST have timeouts/escape hatches to avoid deadlock if a runner is wedged.
- The microkernel SHOULD provide observability for runner lifecycle and “world stop” events.

## Open questions (to answer before “real threads”)

- What is the precise safepoint handshake protocol and state machine (per-thread + world)?
- What GC strategy is assumed initially (stop-the-world copying/mark-sweep/mark-compact), and what barriers are needed?
- What is the canonical representation of “callable code” in the shared heap (table index, module+export id, etc.)?
- Are function tables shared across runners, or replicated per runner with synchronized updates?
- What are the minimum locks needed to make the runtime itself data-race-free on day one?
