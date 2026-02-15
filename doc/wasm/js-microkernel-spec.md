## JS microkernel specification

**Status:** Draft (replacement-track secure-only posture)

## Scope

This specification defines the responsibilities, interfaces, and behavioral guarantees of the JavaScript microkernel that hosts WASM worlds and runners. It covers world/runner lifecycle management, module loading/linking, I/O mediation, and coordination primitives. It does not define the Lisp runtime’s internal semantics or the compiler backend.

## Goals

* Provide a minimal, explicit host API for WASM runners that avoids implicit OS assumptions.
* Support fast spawning via clone-from-image semantics.
* Mediate all external capabilities (I/O, timers, UI, storage) through explicit requests.
* Enforce a secure-only replacement startup profile with explicit hard-fail on missing required capabilities.
* Support shared-memory worker topology for runtime, kernel I/O, storage, and UI bridge hot paths.

## Non-goals

* Implement a POSIX syscall surface in JavaScript.
* Provide transparent sharing of JS objects across runners.
* Guarantee identical behavior across all browser embeddings beyond the supported capability set.

## Definitions

* **World:** A logical Lisp runtime environment (heap + global runtime state). A world may be hosted by a single runner or by multiple runners, depending on the embedding and capabilities.
* **Runner:** A WASM instance (hosted in a Worker for replacement lanes) that executes Lisp code with required shared-memory/Atomics capability and deterministic role ownership.
* **Kernel:** The JS microkernel process managing worlds/runners and host capabilities (I/O, timers, module loading, etc.).
* **Image:** A serialized or preinitialized runtime snapshot used to spawn worlds cheaply.
* **Request:** A structured message from a runner to the kernel for external services.

## Context

The JS microkernel is the “host operating environment” for WASM worlds and runners. It owns external capabilities and enforces the boundary between the Lisp runtime and the host. Host interactions use explicit requests; the kernel may support several execution modes depending on available platform features (see Concurrency model).

## Architecture overview

The microkernel provides:

* **World lifecycle management** (spawn, clone, terminate, supervise).
* **Runner lifecycle management** (spawn, attach-to-world, terminate, supervise).
* **Module management** (fetch, load, link, cache).
* **Capability mediation** (I/O, timers, storage, UI).
* **Coordination and messaging** between runners and the host.

## Interfaces

### Kernel API (host-side)

The kernel exposes a minimal API to create and manage worlds/runners and to deliver responses:

* `createWorld(options) -> worldId`
* `cloneWorld(imageId, options) -> worldId`
* `createRunner(worldId, options) -> runnerId`
* `terminateRunner(runnerId, reason?)`
* `terminateWorld(worldId, reason?)`
* `sendToRunner(runnerId, message)`
* `registerImage(imageId, imageData)`

**Reference implementation (bring-up):** see [`scripts/wasm/lib/world-kernel.mjs`](../../scripts/wasm/lib/world-kernel.mjs).

### Runner API (guest-side)

Runners call a narrow host surface, implemented as WASM imports, to request capabilities.

**Import module name:** `ccl`

**Required imports (ABI compatibility surface):**

* `kernel_request(opcode, payloadPtr, payloadLen) -> requestId`
* `kernel_poll(requestId) -> status`
* `kernel_result(requestId) -> int32`
* `kernel_response_size(requestId) -> uint32`
* `kernel_copy_response(requestId, dstPtr, dstLen) -> uint32`
* `kernel_drop_request(requestId) -> void`

**Optional import (compatibility optimization only):**

* `kernel_wait(requestId, deadlineMs) -> status`

The payload format and opcode registry are defined in `doc/wasm/kernel-request-abi.md:1`.

### Request lifecycle (guest-visible)

* The guest calls `kernel_request(...)` and receives a `requestId`.
* The guest observes completion via `kernel_poll(requestId)` (or `kernel_wait` where supported).
* When status indicates completion, the guest reads:
  * `kernel_result(requestId)` for the operation's primary result, and
  * `kernel_response_size`/`kernel_copy_response` for any response payload bytes.
* The guest MUST call `kernel_drop_request(requestId)` exactly once to release host-side resources associated with the request ID (even on error paths).

### Shared-channel and direct-write response evolution (TODO)

Replacement-track hot-path transport is shared-channel-first. Copy-response handling is compatibility-only for bootstrap/control/diagnostics lanes.

TODO(zero-copy): Provide optional ABI extensions that avoid copy-path responses by writing directly into guest linear memory (caller-provided output buffers or a shared arena/ring buffer). Any direct-write form MUST define explicit lifetime and invalidation rules; compatibility copy-path behavior remains limited to non-hot lanes.

### Replacement-track startup contract (normative)

For replacement-track runtime lanes:

* Startup MUST satisfy the secure runtime gate contract (`SRG-01`..`SRG-12`).
* Required capabilities (cross-origin isolation, `SharedArrayBuffer`, Atomics/worker wait, worker topology, shared-memory transport policy) are mandatory, not optional.
* Any required capability failure MUST terminate startup with explicit diagnostics and MUST NOT silently degrade to a portable fallback lane.
* Hot-path runtime/kernel/storage/UI traffic MUST use shared-memory channel mappings defined by `IPCP-*` contracts.

## Functional requirements

* The kernel MUST be able to spawn a fresh world with a minimal root image.
* The kernel MUST support spawn-from-image cloning semantics for worlds.
* The kernel MUST deliver responses to runner requests in a deterministic format.
* The kernel MUST provide a capability boundary: all external I/O MUST be mediated by the kernel.
* The kernel MUST enforce replacement-track worker topology and role ownership for startup.
* The kernel MUST require shared-memory/Atomics capability for replacement-track runtime execution.
* If required replacement capabilities are unavailable, startup MUST hard-fail with explicit diagnostics; no degraded fallback runtime is launched.

## Operational requirements

* The kernel SHOULD expose observability hooks (logging, metrics counters) for world and runner lifecycle events.
* The kernel SHOULD provide backpressure for request storms (queue limits or throttling).
* The kernel SHOULD allow graceful shutdown of runners.

## Failure modes

* If a runner crashes or terminates unexpectedly, the kernel MUST surface a termination event and release associated resources.
* If a request cannot be fulfilled, the kernel MUST return a structured error response to the runner.
* If a required replacement capability is unavailable, the kernel MUST emit explicit failure diagnostics and abort startup rather than silently degrade.

## Security and capability constraints

* The kernel MUST NOT grant implicit access to host resources not explicitly requested.
* The kernel MUST enforce origin and embedding restrictions for I/O and storage.
* The kernel MUST validate message boundaries and sizes from runners.

## Concurrency model

Replacement-track execution uses a secure-only worker model:

* Runtime lanes execute in workers with required `SharedArrayBuffer` and Atomics capabilities.
* Hot-path transport is shared-memory-first; copy/message lanes are control/diagnostics compatibility paths only.
* `kernel_wait` may be used when supported, but startup capability checks remain strict and no-fallback.
* If required capabilities are missing, startup fails explicitly and deterministically.

Legacy single-runner portable bring-up behavior may exist in historical lanes, but it is not the normative replacement-track contract.

## Image and module management

* The kernel MUST load a minimal root image before spawning runners.
* The kernel SHOULD cache loaded modules and images to reduce startup time.
* The kernel SHOULD support dynamic module loading requests from runners.

## Open questions

* Yield/resume API for Stage 2: bring‑up exposes `wasm_ccl_start` (boot +
  `start_lisp`), `wasm_ccl_start_lisp` (post‑load entry), and an explicit
  stepping interface (`wasm_ccl_step`; see `doc/wasm/yield-resume.md:1`).
  Open question: how should these integrate with the long‑term toplevel and
  scheduling model?
* How should capability discovery be represented beyond an initial `CAPS` opcode (static config vs. dynamic query)?
* What is the lifecycle policy for cached images and modules?
* What is the stop-the-world / safepoint protocol between runners for GC and interrupts?
