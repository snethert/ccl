# Threading and Runtime Worker Model (Replacement Track)

**Status:** Draft (replacement-track baseline)

## Scope

This document defines required startup threading and worker-topology
assumptions for the replacement-track MVP runtime architecture.

Replacement-track startup is secure-only and shared-memory-first. Runtime
worker/thread capability is required at startup; single-runner portability mode
is not a valid replacement-lane baseline.

This document covers:

- Runtime worker topology and startup requirements
- Platform prerequisites (`SharedArrayBuffer`, Atomics, WASM shared memory)
- Required runtime/compiler mechanisms (TCRs, safepoints, GC coordination, synchronization)
- Runtime-vs-CL thread semantics boundary

This document does not define the full GC algorithm, full object layout, or
the complete kernel/runner message schema.

## Definitions

- **World:** One Lisp runtime instance with one shared heap (shared linear memory) and shared runtime state.
- **Runtime runner:** One WASM instance inside a runtime worker that executes one Lisp execution lane in a world.
- **Worker topology (required):** Startup roles that must be ready before runtime entry: runtime worker(s), kernel I/O worker, storage worker.
- **TCR:** Per-thread runtime record holding registers/roots/stacks/flags needed to run and to stop safely.
- **Safepoint:** A compiler-inserted point where a runtime runner can be safely interrupted/handshaken for GC, interrupts, or cancellation.

## Replacement-track startup contract (normative)

1. Startup must satisfy secure runtime capability gates for threading:
   - worker Atomics wait/notify usability (`SRG-03`)
   - WASM shared memory/thread capability (`SRG-04`)
   - required worker topology READY handshake (`SRG-05`)
2. Startup must enforce runtime thread capability now, while CL thread
   semantics remain explicitly deferred (`SRG-12`).
3. No fallback startup lane may replace missing threading prerequisites with a
   single-runner replacement mode; required-check failure is terminal.

## Execution model (shared heap runtime workers)

- All runtime runners in a world share the same heap, so Lisp objects are
  naturally visible across runtime lanes.
- Each runner has distinct per-thread state (TCR, stacks, bindings).
- Host capabilities (I/O, timers, UI) remain mediated by the JS microkernel;
  shared heap does not imply shared host objects or direct host-pointer sharing.

## Platform prerequisites

### Shared memory and Atomics

Replacement-track runtime threads require:

- `SharedArrayBuffer`-backed `WebAssembly.Memory` (`shared: true`) with fixed `maximum`.
- WebAssembly threads support (atomic instructions) in toolchain and runtime.
- Browser startup in `crossOriginIsolated` context so `SharedArrayBuffer` is available.

If these capabilities are missing, replacement startup must fail explicitly. It
must not continue in degraded single-runner replacement mode.

### Blocking and `Atomics.wait`

- Main-thread blocking waits are disallowed; blocking waits must occur in workers.
- A runner waiting on kernel completion should park via shared-memory wait/notify
  coordination in worker context.

## Required worker topology

Startup must initialize and receive deterministic READY handshakes for:

- runtime execution worker role(s),
- kernel I/O worker role,
- storage worker role.

Runtime entry is blocked until all required roles are ready, and startup fails
if any role is missing or not ready before timeout.

## Shared state placement

Because each runner is a separate WASM instance:

- State that is logically shared across runtime lanes must reside in shared linear memory.
- Per-instance WASM globals are valid only for per-runner TLS-like state (for example, current TCR pointer).
- Compiled code must not treat mutable WASM globals as cross-runner shared state.

The shared heap is necessary but not sufficient; shared invariants must be
represented in memory-backed runtime structures.

## Per-thread runtime state requirements

Each runtime runner must have:

- a TCR in shared memory (discoverable by GC and control paths),
- binding/special-variable stack state,
- control stack region and value/call stacks,
- thread-local flags (interrupt pending, safepoint state, stop-the-world handshake state).

Current ABI hooks:

- `wasm_set_current_tcr(TCR*)`
- `wasm_get_current_tcr() -> TCR*`

Host responsibility: the microkernel sets a runner's current TCR before
entering Lisp code in that runner.

## Safepoints and interrupt delivery

Safepoints are mandatory for bounded coordination:

- Compiler must insert safepoints frequently enough for bounded interrupt
  latency and GC handshakes.
- At a safepoint, a runner must expose roots, observe stop/interrupt flags, and
  be able to park without holding runtime locks indefinitely.

Interrupt delivery model:

- No Unix signals in browser contexts; interrupts are shared-memory flags plus
  safepoint polling.
- "Interrupt thread X" means setting interrupt state in X's TCR and optionally
  waking it with `Atomics.notify`.

### Latency target

Interrupts should be observed within <= 10ms for typical UI-driven workloads.
Loops that may run longer must include explicit safepoints (loop backedge or
allocation checks).

## GC coordination on shared heap

Shared-heap GC must coordinate across all runtime runners:

1. request world stop via shared state,
2. require runners to reach safepoints and acknowledge stopped state,
3. scan roots from all TCRs/stacks,
4. collect/compact as needed,
5. resume runners.

Because WASM locals/register roots are not externally visible, compiler/runtime
must guarantee that live Lisp pointers are represented in discoverable memory at
safepoints.

## Synchronization and memory ordering

Runtime invariants under parallel execution require:

- shared-memory synchronization primitives (mutex/event/condition-style),
- lock or lock-free atomic protocols for shared runtime structures,
- ordered publication for cross-thread object visibility (release/acquire patterns).

Unsynchronized user-level shared mutation may remain undefined behavior, but the
runtime's own shared structures must be data-race-free.

## Dynamic loading and shared code identity

Shared-heap runtime implies shared definitions:

- loading/redefinition is world-scoped and must be synchronized,
- callable-code indirections must be updated atomically and published to all runners,
- if function tables are per-runner, updates must be applied consistently to all
  runners (or replaced by shared indirection).

## I/O and microkernel boundary

- All host I/O remains microkernel-mediated.
- Runner-to-kernel request paths must be thread-safe (queues, request IDs,
  completion signaling).
- Waiting runners use worker-compatible shared-memory coordination; replacement
  startup does not define a single-runner fallback runtime lane.

## Runtime-vs-CL thread semantics boundary

- Required now: runtime worker/thread capability and shared-memory coordination
  needed to run the replacement architecture.
- Deferred: full Common Lisp thread semantics contract (API-level behavior,
  scheduling semantics, and user-visible threading guarantees).

This boundary must stay explicit in runtime policy and startup diagnostics.

## Failure and lifecycle concerns

- If a runner exits unexpectedly, the world must mark it dead and avoid
  indefinite waits on safepoints/locks.
- Stop-the-world protocols need timeout/escape behavior to avoid deadlock.
- Microkernel observability should include runner lifecycle and world-stop events.

## Open questions

- Precise safepoint handshake protocol/state machine (per-runner + world).
- Initial GC strategy and required barriers.
- Canonical shared representation of callable code.
- Whether function tables remain per-runner or move to shared indirection.
- Minimum locking profile needed for runtime data-race freedom on day one.
