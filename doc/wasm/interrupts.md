# Interrupts and Interrupt Handling (WASM)

**Status:** Draft (replacement-track secure-only posture)

## Scope
This document defines the interrupt model for the WASM-based CCL runtime, the
microkernel boundary, and the browser UI toolkit integration. It covers:

- the **cooperative safepoint interrupt** model used in secure replacement runtime lanes,
- the **stop-the-world** interrupt coordination model used in shared-heap worker topologies,
- the **UI turn / yield** integration requirements,
- host ABI considerations and capability gating,
- constraints and invariants that keep interrupts deterministic and safe.

It does **not** define GC internals, full threading semantics, or a complete
scheduler. It also does not prescribe compiler IR details beyond safepoint
requirements.

## Definitions

- **World:** A logical Lisp runtime instance (heap + global runtime state).
- **Runner:** A WASM instance executing Lisp code (optionally in a Worker).
- **TCR:** Thread Control Record; per-runner state (registers, stacks, flags).
- **Safepoint:** Compiler-inserted point where the runner can be safely
  interrupted/handshaken (GC, interrupts, cancellation).
- **Interrupt pending:** A flag indicating that an interrupt should be delivered
  at the next safe boundary.
- **UI turn:** The UI state machine phase boundary (signals → commands → render → backend → idle)
  used by the JS reference model.

## Design Goals

- **Secure-only startup alignment:** Interrupt assumptions must match required startup capabilities (`SharedArrayBuffer`, Atomics, worker topology).
- **Deterministic delivery:** Interrupts are delivered only at explicit, safe boundaries.
- **Bounded latency:** Interrupts must be observed within bounded time via frequent safepoints.
- **No reentrancy surprises:** Commands run to completion or yield; interrupts do not
  implicitly re-enter command execution.
- **UI safety:** IME composition and focus reconciliation are never interrupted.
- **Upgrade path:** The model should extend to shared-heap multi-runner mode without
  semantic changes to Lisp-visible interrupt behavior.

## Constraints (WASM + Browser)

- There are **no Unix signals** in the browser; interrupts must be **cooperative**.
- The **main thread must not block**; blocking waits are only permitted in
  Workers with SharedArrayBuffer and Atomics.
- Without stack switching/asyncify, **interrupts cannot suspend arbitrary call stacks**;
  they must be observed at explicit boundaries.
- If required secure capabilities are unavailable, startup must fail explicitly;
  no fallback execution mode is allowed for replacement lanes.

## Primary Model: Secure Runtime Worker, Cooperative Interrupts

### Summary
In replacement-track runtime lanes, interrupts are implemented as **flags** that are
polled at **safepoints** and at the **explicit stepping boundary**
(`wasm_ccl_step`). The host can request an interrupt, but delivery is
cooperative and bounded by safepoint frequency and step cadence.

### Mechanics

- **Interrupt flag location:** Per-runner flag stored in the runner's TCR
  or equivalent runtime structure in linear memory.
- **Polling points:**
  - Compiler-inserted safepoints in generated code.
  - The explicit step boundary (`wasm_ccl_step`) that drives the toplevel loop.
- **Delivery:** When the interrupt flag is observed, the runtime enters the
  Lisp-level interrupt handler (or signals a condition), then clears the flag
  according to runtime policy.

### Lisp-level delivery path (CCL model)

The canonical CCL path for deferred interrupts is:

1. **Poll:** `check_pending_interrupt` (or equivalent) observes `tcr.interrupt_pending`.
2. **Trap:** `uuo_interrupt_now` (a nullary UUO) is invoked.
3. **Exception:** the trap resolves to `error_interrupt`.
4. **Handler:** the exception path calls `raise_thread_interrupt(TCR*)`, which
   signals the Lisp-level interrupt condition/handler.

In the WASM bring-up, the **intended** path is the same: the poll path should
trigger an interrupt trap/handler entry that ultimately calls
`raise_thread_interrupt`. In the current WASM integration, pending interrupts
are delivered cooperatively by calling `cmain` (which runs
`thread-handle-interrupts`) when `interrupt_pending` is set and interrupts are
enabled. This happens at the toplevel loop boundary and when interrupts are
re-enabled in `_SPbind_interrupt_level*` / `_SPunbind_interrupt_level`.

On WASM, `thread-handle-interrupts` begins with a WASM-only hook:

- `wasm-handle-pending-interrupt` reads `tcr.interrupt-pending`, clears it,
  increments `*wasm-interrupt-count*`, and calls `*wasm-ui-interrupt-hook*`.
- The default hook (`wasm-default-ui-interrupt-hook`) enqueues a UI signal
  (`ui:interrupt`) and yields the UI turn.

This keeps the interrupt delivery path Lisp-visible and deterministic while
leaving non-WASM platforms unchanged.

### Host API Expectations

- The host must be able to **request an interrupt** for a runner by setting
  its interrupt flag (directly or via a microkernel API).
- The host must **not assume immediate delivery**; delivery happens only
  at safepoints / step boundaries.

### Interaction with Yield/Resume

- Interrupts must be compatible with the explicit yield/resume boundary
  described in `doc/wasm/yield-resume.md`.
- If the runner is **blocked** (e.g., waiting on a pending kernel request),
  delivery occurs when the runner resumes and hits a safepoint.

## UI Integration: Turn/Yield Boundary

The UI toolkit defines a deterministic UI turn state machine and forbids
synchronous blocking on the UI thread. Interrupts must respect this model.

### Required UI Semantics

- **No reentrancy:** A command runs to completion or yields; interrupts must
  not re-enter command execution mid-turn.
- **IME safety:** Composition must not be interrupted by focus reconciliation.
- **Explicit yield:** An interrupt that affects UI state should enqueue a
  UI signal and cause a yield boundary, not mutate state from a backend callback.

### Recommended Mapping (Baseline)

- Map **UI-relevant interrupts** to `enqueueUiSignal` followed by
  `yieldUiTurn`, so the next UI turn processes the signal deterministically.
- Keep interrupt delivery **outside** of command execution; if an interrupt
  arrives mid-turn, it should be recorded and applied at the next safe boundary.

## Shared-Heap Coordination Model

Replacement-track runtime lanes assume SharedArrayBuffer + Atomics capability.
Interrupts across workers sharing one heap use a stop-the-world handshake in
shared memory.

### World State (Shared)

- `world_state`: `RUNNING`, `STOP_REQUESTED`, `STOPPED`
- `stop_epoch`: incremented per stop request
- `stop_ack_count`: number of runners that acknowledged stop
- `runner_count`: total runners
- `stop_reason`: enum (`GC`, `INTERRUPT`, `DEBUG`, ...)

### Runner State (Per TCR, Shared)

- `runner_state`: `RUNNING`, `STOPPING`, `STOPPED`
- `last_stop_epoch`: last seen `stop_epoch`
- `interrupt_pending`: boolean

### Handshake Sketch (Interrupt)

1. Request: set `world_state=STOP_REQUESTED`, increment `stop_epoch`, set
   `stop_reason=INTERRUPT`, set `stop_ack_count=0`.
2. Notify: `Atomics.notify` on a shared location (optional).
3. Runners: at safepoints, observe stop request, set `runner_state=STOPPED`,
   record `last_stop_epoch`, increment `stop_ack_count`.
4. Barrier: wait until `stop_ack_count == runner_count`.
5. Delivery: perform interrupt logic / GC scan (if combined).
6. Resume: set `world_state=RUNNING` and notify runners.

### Compatibility Requirements

- Interrupt semantics must match the secure runtime cooperative model from the Lisp
  perspective (interrupts observed at safepoints, not asynchronously).
- Compiled code must ensure **roots are discoverable at safepoints**.

## Capability and ABI Considerations

### Capability Gating

- Interrupt support in replacement runtime lanes requires SharedArrayBuffer + Atomics.
- The microkernel must signal capability availability via `KERNEL_OP_CAPS`.

### ABI / Microkernel

- The secure runtime model can use an **out-of-band host flag** or a minimal
  microkernel API to request an interrupt.
- Interrupt requests may include `Atomics.notify` to wake blocked workers where
  supported by the runtime scheduler.

## Safepoint Requirements

- Safepoints must be **frequent enough** to provide bounded interrupt latency.
- At safepoints, **all live Lisp pointers must be discoverable** via TCR/stack
  or spill policy.
- Safepoints must not occur while holding runtime invariants that cannot be
  safely interrupted (locks, partial object construction, etc.).

## Open Questions

- Exact interrupt handler entry path in the WASM runtime (subprim vs. central poll).
- Interaction between interrupt delivery and pending kernel requests.
- Required memory ordering for shared-heap interrupt flags and stop handshake.
- Minimal safepoint frequency target for acceptable UI responsiveness.

## References

- `doc/wasm/yield-resume.md`
- `doc/wasm/threads.md`
- `doc/wasm/threads-protocol.md`
- `doc/wasm/js-microkernel-spec.md`
- `doc/wasm/kernel-request-abi.md`
- `doc/wasm/browser-ui-spec.md`
- `web-ui/src/state.mjs`
- `doc/wasm/decisions.md`
- `doc/wasm/subprims-execution-prompt.md`
