# Capability Matrix (Browser runner Lisp / CCL→WASM)

**Status:** Draft

## Scope

This document defines a **capability-based contract** for the CCL→WASM Lisp
runtime and its JavaScript microkernel host.

It provides:

- A canonical list of **capability keys**.
- A decision mechanism for classifying features as **core**, **capability-backed**,
  or **rejected** in browser embeddings.
- The **required failure mode** when code requests a missing capability.

It does **not** define the concrete kernel request ABI; see
`doc/wasm/kernel-request-abi.md:1`.

## Core rules

- **Core** means: implementable entirely inside the Lisp + WASM runtime (no
  privileged host features).
- **Host capability** means: requires the JS microkernel and (in browser
  embeddings) browser APIs.
- When a capability is absent, the default behavior is: **signal a condition**
  of type `CAPABILITY-UNAVAILABLE` carrying a machine-readable capability key
  and an operation name. **No silent fallbacks.**

## Capability keys (canonical)

The keywords below are the canonical capability identifiers.

- `:io/stream` — stream plumbing + standard stream endpoints (stdin/stdout/stderr)
- `:persist/store` — key/value persistence (IndexedDB / OPFS / Cache, etc.)
- `:fs/virtual` — pathname layer over `:persist/store`
- `:net/http` — fetch-like HTTP client
- `:net/ws` — websocket client
- `:time/clock` — wall clock time and timezones
- `:time/timers` — timeouts/intervals/sleep
- `:ui/events` — DOM/event loop integration
- `:ui/render` — DOM/canvas/WebGPU access
- `:worker/spawn` — spawn additional runners
- `:sharedmem` — SharedArrayBuffer + Atomics (shared heap mode prerequisite)
- `:crypto/rng` — secure random
- `:introspect/debug` — stack traces, source maps, profiler hooks
- `:foreign/ffi` — JS↔WASM callable boundary and host calls

## Standard condition contract

On any operation requiring a missing host capability, signal a condition
carrying:

- `:capability` — keyword from the list above
- `:operation` — symbol or string (e.g. `OPEN`, `DIRECTORY`, `SPAWN-RUNNER`)
- `:details` — optional additional data (requested pathname/URL/mode/etc.)

The condition type name is `CAPABILITY-UNAVAILABLE` (or an equivalent exported
type), but the payload MUST be programmatically inspectable.

## Matrix

### 1. Files, pathnames, `LOAD`, compilation artifacts

**CLHS features:** `OPEN`, `WITH-OPEN-FILE`, `CLOSE`, `READ/WRITE-SEQUENCE`,
`FILE-LENGTH`, `FILE-POSITION`

- Requires: `:persist/store` for persistence; `:fs/virtual` if you want pathnames.
- Browser mapping: “file” = named object in store; stream is a view over bytes.
- Absent: `CAPABILITY-UNAVAILABLE` for `:persist/store` (or implement explicitly
  in-memory “ephemeral files” behind a distinct capability such as
  `:persist/ephemeral`).

**CLHS features:** pathnames (`MAKE-PATHNAME`, `PARSE-NAMESTRING`, logical
pathnames, `TRANSLATE-PATHNAME`, `*DEFAULT-PATHNAME-DEFAULTS*`)

- Requires: `:fs/virtual` for resolution against any backing store.
- Browser mapping: adopt a restricted pathname grammar (or logical-only) that
  maps to store keys; no OS devices/permissions.
- Policy choice (pick one and be consistent):
  - (A) Signal on pathname operations in the absence of `:fs/virtual`, or
  - (B) Support pathnames as pure syntax/data, but signal on operations that
    require resolution (`OPEN`, `DIRECTORY`, `TRUENAME`, etc.).

**CLHS features:** `PROBE-FILE`, `TRUENAME`, `RENAME-FILE`, `DELETE-FILE`,
`DIRECTORY`

- Requires: `:persist/store` + `:fs/virtual`.
- Browser mapping: store metadata index; `DIRECTORY` is a prefix/query over keys
  unless you emulate a directory tree.
- Absent: `CAPABILITY-UNAVAILABLE`.

**CLHS feature:** `LOAD`

- Requires: minimum `:io/stream` if loading from an existing stream; plus
  `:persist/store`/`:fs/virtual` if loading by name; plus your module/dylink
  story if loading compiled code.
- Browser mapping: `(load "x")` resolves via `:fs/virtual` to bytes, then the
  loader (source or fasl).
- Absent: if only named loads fail, `(load stream)` may still work if streams
  exist.

**CLHS features:** `COMPILE-FILE`, `COMPILE-FILE-PATHNAME`

- Requires: `:persist/store` if it writes an output artifact; may require
  `:worker/spawn` if you offload compilation; may require `:sharedmem`
  depending on design.
- Browser mapping: compile to your chosen artifact (fasl-like bytes or wasm
  module); store under a deterministic key; return a pathname-like designator if
  `:fs/virtual` exists.
- Absent: signal; do not pretend compilation succeeded if you cannot
  materialize/load the result.

### 2. Streams and terminal assumptions

**CLHS features:** streams and the fundamental stream protocol (`READ-CHAR`,
`READ-LINE`, `WRITE-CHAR`, `FINISH-OUTPUT`, `FORCE-OUTPUT`, `CLEAR-INPUT`, etc.)

- Requires: `:io/stream`.
- Browser mapping: stdin/stdout/stderr are microkernel-provided SIDs; other
  streams are memory-backed or store-backed.

**CLHS features:** `INTERACTIVE-STREAM-P`, `TERPRI`, `FRESH-LINE`

- Requires: `:io/stream`.
- Browser mapping: “interactive” means the microkernel designates it; do not
  infer TTY semantics.

### 3. Networking

Sockets/HTTP are not in CLHS proper; implementations add them.

- Requires: `:net/http` for HTTP; `:net/ws` for bidirectional.
- Browser mapping: provide packages (`NET`, `HTTP`) or Gray-streams over
  fetch/websocket.
- Absent: signal capability condition; no fake local networking.

### 4. Time and environment

**CLHS features:** `GET-UNIVERSAL-TIME`, `GET-DECODED-TIME`,
`ENCODE-UNIVERSAL-TIME`, `DECODE-UNIVERSAL-TIME`, `SLEEP`

- Requires: `:time/clock` for “now”; `:time/timers` for sleep/timers.
- Browser mapping: use JS `Date` / `performance.now` and timers; define
  resolution/monotonicity policy.
- Absent: arithmetic encode/decode may still be supported, but “now” and
  “sleep” MUST signal.

**CLHS features:** `ROOM`, `LISP-IMPLEMENTATION-TYPE`, `MACHINE-TYPE`,
`MACHINE-INSTANCE`, `SOFTWARE-TYPE`, `SOFTWARE-VERSION`

- Requires: optionally `:introspect/debug` or `:foreign/ffi` (to query
  UA/platform).
- Browser mapping: report conservative values; avoid leaking excessive UA detail
  unless explicitly desired.

### 5. OS/process model (mostly reject)

`RUN-PROGRAM`, environment variables, signals, process control are not CLHS
standard but are common extensions.

- Browser policy: do not implement as if real.
- If provided for non-browser embeddings, make it explicitly “host command” and
  capability-gated (e.g. `:host/command`).

### 6. Concurrency and synchronization

Threads/locks are not in CLHS proper; CCL has them.

- Requires: `:worker/spawn` for multiple runners; `:sharedmem` for shared-heap +
  Atomics; otherwise you are in message-passing land with different
  EQ/identity semantics.
- Browser mapping:
  - With `:sharedmem`: implement shared-heap threads with Atomics; microkernel
    mediates blocking via `Atomics.wait` only when `crossOriginIsolated` is true.
  - Without `:sharedmem`: either (A) no threads, or (B) isolated processes with
    copy/serialize semantics and no shared identity (a distinct subsystem; do
    not call it “threads”).
- Absent: signal on thread creation or lock primitives.

### 7. Randomness / crypto

**CLHS feature:** `RANDOM`

- Requires: `:crypto/rng` for high-quality entropy; otherwise implement a
  deterministic PRNG.
- Browser mapping: seed from crypto API when available; document determinism for
  reproducibility.
- Absent: still implement `RANDOM`, but seed is weak/deterministic unless the
  user provides a seed; do not misrepresent entropy quality.

### 8. UI integration (non-CLHS, but real)

Event loop hooks, callbacks, rendering.

- Requires: `:ui/events` and optionally `:ui/render`.
- Browser mapping: maintain a clear boundary: Lisp registers handlers;
  microkernel dispatches; no implicit re-entrancy unless specified.
- Absent: Lisp runs headless.

### 9. Introspection / debugging

**CLHS features:** conditions, restarts, `*DEBUGGER-HOOK*`, `BREAK`,
`INVOKE-DEBUGGER`

- Requires: core for conditions/restarts; `:introspect/debug` for stack trace
  quality and source locations.
- Browser mapping: can be fully in-Lisp with optional microkernel help for
  symbolicated traces.
- Absent: debugger still exists but with degraded backtraces.

## Practical defaults

Opinionated defaults consistent with the project constraints:

- Always implement: `:io/stream`, conditions/restarts, reader/printer, packages,
  compiler core, loader core.
- Implement if possible: `:persist/store` + `:fs/virtual` (so `LOAD` and
  `COMPILE-FILE` are sane).
- Only implement threads if `:sharedmem` is available; otherwise “no threads”.
- Networking and UI are explicit add-ons; never implicit assumptions.

This matrix is the decision mechanism: when a CLHS-ish feature comes up, decide
whether it is core, capability-backed, or rejected, and record the exact failure
mode.

