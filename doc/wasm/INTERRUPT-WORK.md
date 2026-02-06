# Interrupt Work Plan (MVP)

**Status:** Draft
**Goal:** Implement a minimal, correct, and testable interrupt mechanism in the
single-runner (portable) WASM environment, with a clear upgrade path to
shared-heap multi-runner mode.

## MVP Definition

The MVP interrupt system is complete when:

- The host can request an interrupt for a runner.
- The runner observes and delivers the interrupt at a safepoint / step boundary.
- Delivery is deterministic and non-reentrant.
- UI integration respects turn boundaries and IME composition constraints.
- A smoke test proves end-to-end behavior in the JS harness.

## Current Decisions (WASM Bring-up)

- **Flag location:** `tcr.interrupt_pending` (per-runner, in linear memory).
- **Host API:** `wasm_request_interrupt_tcr(tcr)` via the JS microkernel.
- **Delivery:** `wasm_maybe_deliver_interrupt` calls `cmain` when pending + enabled.
- **Lisp hook:** `thread-handle-interrupts` begins with `wasm-handle-pending-interrupt`
  (clears flag, increments `*wasm-interrupt-count*`, calls `*wasm-ui-interrupt-hook*`).
- **UI mapping:** default hook enqueues `ui:interrupt` and yields the UI turn.
- **Platform scope:** all changes are `#+wasm32-target` (other platforms unchanged).

## Step-by-Step Plan

### 1) Define the Interrupt Flag Location (Runtime)

- Choose where the interrupt pending flag lives (TCR or equivalent runtime
  structure in linear memory).
- Ensure the flag is reachable from:
  - compiler-inserted safepoints, and
  - the toplevel / `wasm_ccl_step` boundary.

**Exit criteria:** A clear runtime location and accessor exists for
`interrupt_pending`.

### 2) Add a Host-Facing Interrupt Request API

- In the JS microkernel, add a minimal API (internal if preferred) to request
  an interrupt for a runner (e.g., `requestInterrupt(runnerId)`), which sets
  the interrupt flag in the runner’s memory.
- Avoid ABI changes unless necessary; this can be a direct host-side write in
  the bring-up harness.

**Exit criteria:** Host can set the interrupt flag for a specific runner.

### 3) Implement Polling at Safe Boundaries

- Add an interrupt check at the explicit step boundary:
  - `wasm_ccl_step` should poll and deliver if pending.
- Add or verify compiler safepoints are calling the poll path.
- Ensure the interrupt is **cleared** after delivery per runtime policy.

**Exit criteria:** Interrupts are delivered deterministically without
re-entrant command execution.

### 4) Define Lisp-Level Interrupt Delivery Behavior

- Decide on the Lisp-visible behavior:
  - signal a condition,
  - invoke a standard handler,
  - or call a runtime hook.
- Make the behavior consistent across safepoints and step boundaries.

**Exit criteria:** A single, documented path for interrupt delivery exists.

### 5) UI Integration (Turn/Yield Safety)

- Map UI-affecting interrupts to **signals** and **turn yield**:
  - enqueue a UI signal (e.g., `ui:interrupt`) and
  - force `yieldUiTurn` if a turn is active.
- Ensure IME composition is not interrupted.

**Exit criteria:** Interrupt-triggered UI changes only occur at turn boundaries.

### 6) Add Minimal Tests (JS Harness)

- Add a JS smoke test that:
  1. starts a runner,
  2. triggers an interrupt request,
  3. steps the runner to a safepoint,
  4. asserts that interrupt delivery occurred.
- Optional: a UI smoke that asserts `yieldUiTurn` and signal enqueue.

**Exit criteria:** Tests pass in the `doc/wasm/js` harness.

### 7) Document and Wire the Upgrade Path

- Update `doc/wasm/interrupts.md` with any ABI or runtime changes made.
- If needed, update `doc/wasm/threads-protocol.md` to align with the chosen
  interrupt flag location.

**Exit criteria:** Documentation matches implementation.

## Implementation Notes (MVP Scope)

- No SharedArrayBuffer or Atomics required.
- No asyncify/stack switching required.
- No full scheduler required.
- Interrupts are cooperative and bounded by safepoint cadence.

## Future Work (Post-MVP)

- Implement the stop-the-world protocol in shared-heap mode.
- Add `Atomics.notify` wakeups when runners are blocked in workers.
- Define memory ordering for shared interrupt flags.
- Add latency measurement / diagnostics for safepoint frequency.
