## Project overview

You are building a **Common Lisp system derived from CCL’s architecture** that targets **WebAssembly as the primary execution substrate**, with a **JavaScript microkernel** acting as the host “operating environment.” The goal is not to cram a POSIX Lisp into the browser; the goal is to deliver the **rational, portable parts of Common Lisp**—a **Lisp-2**, **macro system**, **reader/printer**, dynamic function definition/loading—inside a WASM process model that is honest about the web.

The project’s core bet is that **WASM instances are “processes”** (your “webrunners”), and that the JS side is a small, explicit kernel that provides the capabilities the runtime cannot provide itself: spawning, linking, I/O, scheduling, and coordination.

## How to begin a formal spec doc

Start by fixing the scope and contract: name the subsystem, the problem it solves, and the interfaces it must honor. A minimal opening template looks like this:

* **Title:** <Subsystem> Specification
* **Status:** Draft / Proposed / Accepted
* **Scope:** One paragraph describing what this spec covers and explicitly excludes.
* **Goals:** Bullet list of concrete outcomes (what correctness or UX means here).
* **Non-goals:** Explicit constraints or out-of-scope items.
* **Definitions:** Short glossary of terms used in the spec.
* **Context:** One paragraph tying this spec to surrounding subsystems (e.g., JS microkernel, runners, loader).

Then enumerate the core behaviors as requirements:

* **Functional requirements:** “The system MUST …”
* **Operational requirements:** “The system SHOULD …”
* **Failure modes:** “If X fails, the system MUST …”
* **Security/capabilities:** “The system MUST NOT …”

Finally, record decisions and tradeoffs:

* **Design decisions:** What was chosen and why.
* **Alternatives considered:** What was rejected and why.
* **Open questions:** Remaining unknowns that block implementation.

## Design goals and constraints you’ve stated

* **Keep the root Lisp minimal** so it can be **cloned** cheaply (spawn-from-image is the intended mechanism).
* **Dynamic loading** is essential: you want to **add new functions to a running environment** in WASM (not “spin up compilers,” not “rebuild the world”).
* **Safepoints are assumed** in generated code (same category of “given” as type checks): for interrupts, cancellation, and any future concurrency coordination.
* **Strings start as ASCII-only** with an explicit plan not to paint yourself into a corner for later UTF-8 support.
* Threads/concurrency are an execution-model decision, not a language requirement: you are willing to begin **single-threaded** (particularly for sandboxed iframe compatibility), and later add true parallelism where the platform permits it.
* **Quicklisp must run even in the browser**: provide a minimal capability-gated virtual filesystem (in-memory at first, IndexedDB later) so Quicklisp/ASDF see the file operations they expect.

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

  * in the single-threaded/sandbox case: message passing and async callbacks are the only viable universal primitive
  * in the full-featured case: support higher-performance coordination (Atomics / shared memory) when available, but not as an assumption everywhere

In spirit, the JS microkernel is the “world,” and a runner is a process that lives inside it.

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

### Baseline mode: single-threaded Lisp (portable everywhere)

You explicitly converged on this as a sensible first milestone:

* Works in **sandboxed iframes** that cannot rely on shared memory, Atomics, or WASM pthreads.
* Lets you port “all at once” in the sense of language/runtime, while deferring concurrency semantics.
* Still needs an **async boundary** for I/O: “blocking” must become “request + yield/resume” at the Lisp/kernel interface (even single-threaded), or the runtime freezes.

### Full mode: true concurrency via runners

Your earlier mental model was “threads are runners,” i.e., parallelism comes from multiple WASM instances.

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
* concurrency and shared memory are environment-dependent (worker vs sandbox iframe)
* “target triples” are less important than “execution world + ABI constraints”

You even used the existing CCL backend directory conventions as a reality check for naming, which is exactly how CCL wants you to think: the backend name encodes a concrete ABI world, not an abstract marketing label.

## Summary of what you are building

A **CCL-structured Common Lisp** that runs as a **WASM process**, hosted by a **JS microkernel**, with:

* minimal clonable root image
* dynamic function/module loading into live images
* explicit I/O boundary (host capabilities instead of syscalls)
* mandatory safepoints in generated code
* an ASCII-first string plan that keeps a door open to UTF-8
* a portability ladder:

  * single-threaded mode for hostile embed environments (sandboxed iframes)
  * true concurrency via multi-runner execution where the platform allows it
* per-runner heaps and explicit inter-runner communication rather than a shared Lisp heap fantasy
