# Yield/Resume Model for Replacement Runtime Startup

**Status:** Draft (replacement-track baseline)

## Scope

This document defines how runtime execution yields and resumes around async
`kernel_request` completion in the replacement track. It assumes secure startup
capabilities and required worker topology are already enforced.

Non-secure/no-shared-memory embeddings are not supported for replacement-lane
startup.

See also:

- `doc/wasm/kernel-request-abi.md:1`
- `doc/wasm/js-microkernel-spec.md:1`
- `doc/wasm/tickets/RPL-01-secure-runtime-gating.md:99`

## Problem

`kernel_request` operations can complete asynchronously. Runtime runners must
yield when a request is pending and later resume without busy-waiting, blocking
the browser main thread, or violating startup gate invariants.

## Required prerequisites

Replacement-lane yield/resume assumes:

- secure startup context with `SharedArrayBuffer` availability,
- worker Atomics wait/notify support (`SRG-03`),
- WASM shared memory/thread capability (`SRG-04`),
- required worker topology ready (`SRG-05`),
- strict no-fallback startup mode (`SRG-11`).

If prerequisites fail, startup fails; runtime does not switch to a degraded
non-secure or single-runner replacement lane.

## Design constraints

- No Unix signal model; async control is explicit via shared state and
  safepoint/yield boundaries.
- Browser main thread must never block.
- Blocking waits are worker-only operations.
- Without stack-suspension tooling, deep call stacks still require explicit
  yield boundaries.

## Replacement-track direction

### Option A: Explicit stepping boundary (required control-plane contract)

The kernel exports host-driven stepping (`wasm_ccl_step`) and returns explicit
status values when blocked, exited, or trapped. This remains the normative
control-plane boundary for deterministic integration and diagnostics.

### Option C: Worker blocking wait path (required runtime posture)

Runtime workers use shared-memory wait/notify coordination to avoid spin loops
when request completion is pending. The replacement architecture requires
worker-capable blocking semantics; this is not an optional portability add-on.

### Option B: Toolchain suspend/resume (deferred exploration)

Toolchain-driven stack suspension remains optional research and is not required
for replacement MVP startup.

## Minimal stepping API (implemented bring-up contract)

Kernel exports (see `lisp-kernel/wasm-ccl-step.c:1`):

- `wasm_ccl_init() -> i32`
- `wasm_ccl_step(deadlineMs: i32) -> i32`
- `wasm_ccl_blocked_request_id() -> u32` (0 if not blocked)
- `wasm_ccl_exit_code() -> i32`
- `wasm_ccl_last_error() -> i32` (0 if no trapped error)

`wasm_ccl_step` status values:

- `0` (`STEP_RUNNING`): made progress
- `1` (`STEP_BLOCKED`): pending host completion or would-block boundary
- `2` (`STEP_EXITED`): clean shutdown
- `3` (`STEP_TRAPPED`): fatal error

## Lisp-level yield hook (current scaffolding)

Current stream-layer hook:

- `ccl::*wasm-yield-on-eagain*` (default `T` on `wasm32`)
- `EWOULDBLOCK/EAGAIN` in `with-eagain` can `throw :wasm-yield`
  with `(:direction <keyword> :fd <integer>)`
- `toplevel-loop` catches `:wasm-yield` and returns to the host boundary

This remains coarse-grained scaffolding. Replacement startup still assumes
secure worker/shared-memory prerequisites and strict startup gating.

## Legacy note

Portable/non-secure Stage-2 bring-up descriptions are retained only as legacy
context for historical lanes. They are not normative for replacement MVP
startup behavior.
