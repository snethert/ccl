# Shared‑Heap Threading Protocol (Draft)

**Status:** Draft  
**Scope:** Concrete protocol sketch for shared‑heap threading. This is a
companion to `doc/wasm/threads.md` and focuses on the stop‑the‑world handshake
and minimal state machine.

## Goals

- Provide a deterministic stop‑the‑world handshake for GC and interrupts.
- Define minimal per‑runner state and a world‑level coordination block.
- Avoid relying on OS signals (browser‑safe).

## World State (shared memory)

All fields below live in shared linear memory:

- `world_state` (enum): `RUNNING`, `STOP_REQUESTED`, `STOPPED`
- `stop_epoch` (u32): increments on each stop request
- `stop_ack_count` (u32): number of runners that have acknowledged stop
- `runner_count` (u32): total live runners
- `stop_reason` (u32): `GC`, `INTERRUPT`, `DEBUG`, ...

## Runner State (per TCR, shared)

- `runner_state` (enum): `RUNNING`, `STOPPING`, `STOPPED`
- `last_stop_epoch` (u32)
- `interrupt_pending` (bool)
- `last_lisp_frame` / stack roots (as in current CCL)

## Stop‑the‑World Handshake (proposed)

1. **Request:** GC sets `world_state=STOP_REQUESTED`, increments `stop_epoch`,
   sets `stop_ack_count=0`, sets `stop_reason`.
2. **Notify:** Host or GC thread issues `Atomics.notify` on a shared location.
3. **Runners:** At safepoints, each runner observes `STOP_REQUESTED` and:
   - sets `runner_state=STOPPED`,
   - records `last_stop_epoch`,
   - increments `stop_ack_count`.
4. **Barrier:** GC waits until `stop_ack_count == runner_count`.
5. **GC:** Scan roots via all TCRs, collect.
6. **Resume:** Set `world_state=RUNNING` and signal runners.

## Required Safepoint Semantics

- Each runner must regularly poll `world_state` and `interrupt_pending`.
- At safepoints, all live Lisp pointers must be discoverable from memory
  (TCR/stack spill policy).

## Blocking and `kernel_wait`

- In shared‑heap mode, a runner may block using `Atomics.wait` when safe.
- `kernel_wait` can be used to wait for host request completion without
  busy‑waiting.

## Open Questions

- Exact memory ordering requirements (acquire/release placements).
- What is the minimal safepoint frequency for acceptable latency?
- How to coordinate GC with dynamic code loading and function table updates?
