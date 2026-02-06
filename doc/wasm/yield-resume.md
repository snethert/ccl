# Stage 2 Yield/Resume Model (Async `kernel_request`)

**Status:** Draft (design note)

## Problem

In the Stage 1 bring-up, the JS microkernel completes `kernel_request` calls synchronously. This lets the WASM kernel use a simple synchronous wrapper (`poll` once, then read result/response).

For browsers and other async-only environments, many operations (notably I/O) cannot complete synchronously. In **Stage 2**, a request may remain **PENDING** and the runner MUST NOT busy-wait or block the host event loop.

This document records the design space for how the runner yields and later resumes execution when host results arrive.

See also:

- `doc/wasm/kernel-request-abi.md:1`
- `doc/wasm/js-microkernel-spec.md:1`

## Constraints (WASM + browser reality)

- There is no Unix signal model for interrupts; "async events" must be delivered via explicit polling/safepoints.
- The browser main thread MUST NOT block. Workers may block only in limited ways (e.g. `Atomics.wait` with `SharedArrayBuffer`, and only when permitted by the embedding).
- Without toolchain help (stack switching / asyncify), a deep call stack cannot be transparently suspended and resumed. Any yield must occur at an explicit boundary.

## Goals

- Keep the host ABI (`kernel_request`) stable while enabling async completion.
- Preserve a portable baseline that works without `SharedArrayBuffer` / Atomics.
- Avoid invasive rewrites where possible, but be explicit about where rewrites are unavoidable.

## Options

### Option A: Explicit stepping API (portable baseline)

Add an explicit exported API that allows the host to "drive" the runner:

- `wasm_ccl_step() -> status`

The kernel runs until it reaches a boundary where it would block (e.g. an I/O operation needs host data), then returns to JS with a status indicating it is blocked.

To make this work, all potentially blocking host operations must either:

- return `-EWOULDBLOCK` (or similar) and propagate up to the step boundary, or
- enqueue a request and return control to JS immediately, with the continuation represented explicitly in Lisp/kernel state.

**Pros**

- Works everywhere (including sandboxed iframes).
- Keeps the host fully in control of scheduling.

**Cons**

- Requires discipline: all code that can trigger host I/O must be able to unwind to the step boundary without "pretending to block".
- Likely implies an event-loop style Lisp toplevel eventually.

### Option B: Toolchain-assisted suspend/resume (Asyncify / stack switching)

Use a toolchain feature to suspend a WASM call stack inside `kernel_request` and resume it later.

**Pros**

- Preserves synchronous-looking code paths (fewer invasive rewrites).

**Cons**

- Toolchain complexity and constraints (performance overhead; incompatibilities with some low-level assumptions).
- Harder to reason about with manual cstack and GC root visibility.

### Option C: Blocking waits in workers (Stage 3 optimization)

When `SharedArrayBuffer` + Atomics are available (and the runner is in a Worker),
implement `kernel_wait(requestId, deadlineMs)` and allow the runner to block
efficiently without spinning.

**Pros**

- Keeps synchronous semantics for many operations.
- Potentially very fast.

**Cons**

- Not universally available (e.g. not in sandboxed iframes; not on non-isolated pages).
- Still needs Option A or B as the portable baseline.

## Recommended direction

- Treat **Option A (explicit stepping)** as the portable Stage 2 baseline.
- Implement **Option C (blocking waits)** as an optional Stage 3 optimization where available.
- Only consider **Option B (asyncify/stack switching)** if Option A becomes prohibitively invasive for the desired UX/performance.

**Current bring-up status:** the reference microkernel does not implement
`kernel_wait` yet; Stage 3 is intentionally deferred until a SharedArrayBuffer +
Atomics embedding is in place.

## Minimal Stage 2 API (implemented for bring-up)

The kernel now exports a minimal stepping interface (see `lisp-kernel/wasm-ccl-step.c:1`):

- `wasm_ccl_init() -> i32` (idempotent; resets stepping state)
- `wasm_ccl_step(deadlineMs: i32) -> i32`
- `wasm_ccl_blocked_request_id() -> u32` (0 if not blocked on a request)
- `wasm_ccl_exit_code() -> i32`
- `wasm_ccl_last_error() -> i32` (0 if no trapped error)

`wasm_ccl_step` currently returns:

- `0` (`STEP_RUNNING`): made progress; host may call again soon
- `1` (`STEP_BLOCKED`): waiting for host data (`kernel_request` is PENDING) or would-block (`-EWOULDBLOCK`)
- `2` (`STEP_EXITED`): clean shutdown (EOF for the current bring-up loop)
- `3` (`STEP_TRAPPED`): fatal error (see `wasm_ccl_last_error`)

This is a correctness/portability baseline for Stage 2. The full Lisp runtime now
uses the same boundary: `wasm_ccl_step` drives the Lisp toplevel loop and returns
`STEP_BLOCKED` when the toplevel yields (via `:wasm-yield`), `STEP_EXITED` when the
top‑level function exits, and `STEP_TRAPPED` if a non‑local transfer escapes the
boundary.

## Lisp-level yield hook (bring-up scaffolding)

The Lisp stream layer now exposes a minimal hook to unwind to a host-controlled
boundary when I/O would block:

- `ccl::*wasm-yield-on-eagain*` (default `NIL`)
- When true, `EWOULDBLOCK/EAGAIN` in `with-eagain` causes a `throw :wasm-yield`
  carrying a small plist `(:direction <keyword> :fd <integer>)`.
- The toplevel loop (`toplevel-loop`) catches `:wasm-yield` and returns to the
  caller, allowing the embedding to regain control.

This does **not** provide full continuation semantics; it is a coarse-grained
bring-up tool. The real Stage-2 integration will still require explicit
stepping at safe boundaries (Option A).
