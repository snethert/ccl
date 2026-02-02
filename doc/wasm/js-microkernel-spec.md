## JS microkernel specification

**Status:** Draft

## Scope

This specification defines the responsibilities, interfaces, and behavioral guarantees of the JavaScript microkernel that hosts WASM runners. It covers runner lifecycle management, module loading/linking, I/O mediation, and coordination primitives. It does not define the Lisp runtime’s internal semantics or the compiler backend.

## Goals

* Provide a minimal, explicit host API for WASM runners that avoids implicit OS assumptions.
* Support fast spawning via clone-from-image semantics.
* Mediate all external capabilities (I/O, timers, UI, storage) through explicit requests.
* Provide a single-threaded compatibility mode and a scalable multi-runner concurrency mode.

## Non-goals

* Implement a POSIX syscall surface in JavaScript.
* Provide transparent shared-heap Lisp objects across runners.
* Guarantee identical behavior across all browser embeddings beyond the supported capability set.

## Definitions

* **Runner:** A WASM instance (optionally inside a Web Worker) that hosts a Lisp world.
* **Kernel:** The JS microkernel process managing runners and host capabilities.
* **Image:** A serialized or preinitialized runtime snapshot used to spawn runners cheaply.
* **Request:** A structured message from a runner to the kernel for external services.

## Context

The JS microkernel is the “host operating environment” for WASM runners. It owns external capabilities and enforces the boundary between the Lisp runtime and the host. Runners are treated as processes, with communication occurring via explicit messages or shared buffers where available.

## Architecture overview

The microkernel provides:

* **Runner lifecycle management** (spawn, clone, terminate, supervise).
* **Module management** (fetch, load, link, cache).
* **Capability mediation** (I/O, timers, storage, UI).
* **Coordination and messaging** between runners and the host.

## Interfaces

### Kernel API (host-side)

The kernel exposes a minimal API to create and manage runners and to deliver responses:

* `createRunner(options) -> runnerId`
* `cloneRunner(imageId, options) -> runnerId`
* `terminateRunner(runnerId, reason?)`
* `sendToRunner(runnerId, message)`
* `registerImage(imageId, imageData)`

### Runner API (guest-side)

Runners call a narrow host surface, implemented as imports, to request capabilities:

* `kernel_request(opcode, payloadPtr, payloadLen) -> requestId`
* `kernel_poll(requestId) -> status`
* `kernel_wait(requestId, deadline) -> status`
* `kernel_log(level, payloadPtr, payloadLen)`

The payload format is a versioned, length-delimited message format agreed upon by kernel and runner.

## Functional requirements

* The kernel MUST be able to spawn a fresh runner with a minimal root image.
* The kernel MUST support spawn-from-image cloning semantics.
* The kernel MUST deliver responses to runner requests in a deterministic format.
* The kernel MUST provide a capability boundary: all external I/O MUST be mediated by the kernel.
* The kernel MUST support at least a single-threaded embedding mode.
* The kernel SHOULD support multi-runner concurrency where platform features allow it.

## Operational requirements

* The kernel SHOULD expose observability hooks (logging, metrics counters) for runner lifecycle events.
* The kernel SHOULD provide backpressure for request storms (queue limits or throttling).
* The kernel SHOULD allow graceful shutdown of runners.

## Failure modes

* If a runner crashes or terminates unexpectedly, the kernel MUST surface a termination event and release associated resources.
* If a request cannot be fulfilled, the kernel MUST return a structured error response to the runner.
* If a capability is unavailable in the current embedding (e.g., no shared memory), the kernel MUST report capability absence rather than silently degrade.

## Security and capability constraints

* The kernel MUST NOT grant implicit access to host resources not explicitly requested.
* The kernel MUST enforce origin and embedding restrictions for I/O and storage.
* The kernel MUST validate message boundaries and sizes from runners.

## Concurrency model

* **Baseline mode:** single-threaded runner with async I/O; requests yield/resume rather than blocking the host.
* **Concurrent mode:** multiple runners mapped to Web Workers where available, with message passing or shared buffers used for coordination.

## Image and module management

* The kernel MUST load a minimal root image before spawning runners.
* The kernel SHOULD cache loaded modules and images to reduce startup time.
* The kernel SHOULD support dynamic module loading requests from runners.

## Open questions

* What is the definitive message schema for kernel/runner requests?
* How should capability discovery be represented (static config vs. dynamic query)?
* What is the lifecycle policy for cached images and modules?
