## Project overview

You are building a **Common Lisp system derived from CCL’s architecture** that targets **WebAssembly as the primary execution substrate**, with a **JavaScript microkernel** acting as the host “operating environment.” The goal is not to cram a POSIX Lisp into the browser; the goal is to deliver the **rational, portable parts of Common Lisp**—a **Lisp-2**, **macro system**, **reader/printer**, dynamic function definition/loading—inside a WASM process model that is honest about the web.

The project’s core bet is that **WASM instances are “processes”** (your “webrunners”), and that the JS side is a small, explicit kernel that provides the capabilities the runtime cannot provide itself: spawning, linking, I/O, scheduling, and coordination.

## Design goals and constraints

* **Keep the root Lisp minimal** so it can be **cloned** cheaply (spawn-from-image is the intended mechanism).
* **Dynamic loading** is essential: you want to **add new functions to a running environment** in WASM (not “spin up compilers,” not “rebuild the world”).
* **Safepoints are assumed** in generated code (same category of “given” as type checks): for interrupts, cancellation, and any future concurrency coordination.
* **Strings start as ASCII-only** with an explicit plan not to paint yourself into a corner for later UTF-8 support.
* Replacement-lane threading/concurrency is a runtime contract: secure-only startup requires worker/thread capability and shared-memory coordination for hot paths, while CL thread semantics remain explicitly deferred.
* **Quicklisp compatibility is a post‑MVP goal**: design the capability‑gated VFS so Quicklisp/ASDF can be enabled later, but keep it out of the current MVP scope.

## Big architecture: two halves

### 1) The JS microkernel (host-side)

The JS side is a **microkernel**, not an application wrapper. It owns the browser-specific reality and presents a narrow interface to the Lisp world.

High-level responsibilities you’ve described or implied:

* **Runner lifecycle**

  * spawn a new runner (likely a Web Worker + WASM instance in the “real concurrency” mode)
  * spawn-from-image / clone semantics (your preferred model for amortizing startup work)
  * terminate / restart / supervise runners

* **Module management**

  * fetch/load WASM modules and associated assets
  * link modules (WASM dynamic linking model as you implement it)
  * enforce a minimal “root image” that new runners clone

* **I/O and capability boundary**

  * all external interaction is mediated by the kernel
  * the Lisp does not “do syscalls”; it makes requests
  * I/O is the hard question you flagged explicitly, so the microkernel is where stream semantics, timers, filesystem-like abstractions, and UI/DOM interaction ultimately land

* **Coordination and messaging**

  * shared-memory channels are the normative transport for runtime hot paths
  * message/copy paths remain for bootstrap/control/diagnostics and explicitly labeled legacy lanes

In spirit, the JS microkernel is the “world,” and a runner is a process that lives inside it.

## Browser UI Toolkit (Status Note)

The browser UI toolkit is specified in `doc/wasm/browser-ui-spec.md`. A reference JavaScript implementation of the UI state model, command system, and rendering backends exists in `web-ui/` and is used for deterministic tests. Lisp<->JS runtime bridge integration is implemented for runtime output/event flow, typed command dispatch, debugger/restart payloads, inspector/place-edit updates, and job updates.

Current gap: the fully compiled Lisp UI persistence path is still blocked by
runtime bootstrap/function-binding stabilization in the loaded image state.
Root-image/toplevel non-interactive boot gating is in place, and the default
unattended persistence backend is already memory-first (`memory-snapshot`).

## Capability model (host feature matrix)

Because browser embeddings differ (sandboxed iframe vs. dedicated worker, `crossOriginIsolated` vs. not, storage policy, networking policy, etc.), the system uses an explicit capability model:

* The microkernel advertises which host capabilities exist in the current embedding.
* When Lisp code requests a missing capability, it MUST fail explicitly (no silent fallback).
* The Lisp-level failure mode is a condition of type `CAPABILITY-UNAVAILABLE` carrying a canonical capability key and operation name.

The canonical capability keys and the CLHS-ish feature mapping live in `doc/wasm/capability-matrix.md:1`.

### 2) The Lisp backend (CCL-derived)

On the Lisp side, the target is **a real Common Lisp environment**—but “real” in the sense of language machinery and developer experience, not “real” in the sense of pretending the browser is Unix.

Key features you’ve called out:

* **Lisp-2** (separate function and value namespaces)
* **Macros** as first-class compile-time tools
* **Reader and printer**
* **Dynamic loading / redefining** functions into a live image
* A compilation pipeline that can emit WASM-compatible code, with:

  * **safepoints** inserted into generated code
  * **type checks** inserted per your plan (and treated as normal, not exceptional)

The important separation is that the Lisp runtime is a language system, while “the OS” is the microkernel.

## Execution model and concurrency roadmap

### Replacement MVP mode: secure shared-memory runtime (required)

The replacement lane assumes secure runtime capabilities at startup:

* Worker/thread runtime capability is required for runtime execution.
* Shared-memory coordination (SAB + Atomics) is required for hot-path transport and signaling.
* Startup is strict no-fallback: if required capabilities are unavailable, the runtime fails explicitly instead of degrading to a portable mode.

### Legacy compatibility note (non-MVP)

Single-threaded/sandbox-compatible bring-up remains historical context for legacy lanes, but it is not the replacement MVP execution target.

In that model:

* A “thread” is a **runner** (practically: worker + WASM instance).
* **Safepoints** are used for interrupts/cancellation/cooperative coordination.
* Each runner can be a full Lisp world, spawned from the minimal image.

## Memory and GC: per-runner heap model

You described the intended approach as:

* **Each runner has its own heap**.
* Communication happens through a **shared memory channel** or messaging interface back to the spawning Lisp (and/or the microkernel).

That design has a decisive semantic consequence (which you already accept as the trade): Lisp heap objects do not naturally cross runner boundaries. Inter-runner communication becomes:

* serialized data, or
* shared foreign/binary buffers with explicit lifetime rules, or
* handles/references managed by the microkernel

This keeps GC local and avoids the shared-heap coordination problem.

## Object representation and tagging

The WASM backend follows CCL’s tagged-object approach, with the representation and tagging parameters determined by the target word size and alignment. WASM32 and WASM64 therefore use target-appropriate tagged words and layouts; shared tag-manipulation code should read the target’s tag configuration rather than baking in a single layout.

## Strings: ASCII first, without sealing off UTF-8 later

Your stated direction:

* treat “characters” as an initial fiction; internally represent alphanumeric data as constrained bytes/ints
* e.g., `(ascii 'a) -> i32`, `(ascii-string "abc") -> struct of ascii ints`
* the key requirement is to avoid an early representation that makes later UTF-8 normalization impossible or prohibitively painful

So the plan is: start narrow (ASCII), but preserve a message and string representation story that can later widen without breaking the system’s seams.

## How CCL fits in

The project is “to CCL” in the sense that you are using CCL’s worldview—kernel/runtime split, backend directories per target ABI, explicit low-level build control—as the structural model, but you are adapting it to a host where:

* there is no OS syscall surface you control
* the loader and I/O are host-mediated
* replacement-lane concurrency and shared memory are required at startup, while legacy environments are explicitly non-MVP
* “target triples” are less important than “execution world + ABI constraints”

You even used the existing CCL backend directory conventions as a reality check for naming, which is exactly how CCL wants you to think: the backend name encodes a concrete ABI world, not an abstract marketing label.

## Canonical rebuild command

To avoid out-of-sync artifacts, use one orchestrator command as the default:

```bash
scripts/wasm/rebuild-everything.sh
```

Script path: `scripts/wasm/rebuild-everything.sh`

This runs the full dependency-ordered rebuild:

1. `lisp-kernel/wasm32` (`doc/wasm/js/wasmcl.wasm`)
2. `wasm-boot.image`
3. runtime fasls/modules (`doc/wasm/wasm-runtime-modules.json` and `.idx`)
4. versioned startup artifacts:
   `doc/wasm/bootstrap-l0-contract.v1.json` and
   `doc/wasm/startup-symbol-scope.source_scope_v1.json`
5. `root.image` + manifest/resolution outputs (default enabled; non-fatal unless `--strict-root-image`)

Yes: this includes the versioned-artifact refresh path (the contract sidecar + startup symbol scope generation), so those files are regenerated in the same run instead of by separate ad hoc commands.

## Summary of what you are building

A **CCL-structured Common Lisp** that runs as a **WASM process**, hosted by a **JS microkernel**, with:

* minimal clonable root image
* dynamic function/module loading into live images
* explicit I/O boundary (host capabilities instead of syscalls)
* mandatory safepoints in generated code
* an ASCII-first string plan that keeps a door open to UTF-8
* a secure-only replacement MVP posture:

  * required worker/shared-memory runtime capability for active replacement lanes
  * legacy single-threaded sandbox compatibility documented as non-MVP context
* per-runner heaps and explicit inter-runner communication rather than a shared Lisp heap fantasy
