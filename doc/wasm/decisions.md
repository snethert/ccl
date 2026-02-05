# Decision Log (CCL→WASM)

**Status:** Living document  
**Purpose:** Record decisions that constrain implementation, with a short
reason and links to the canonical spec(s).

## ADR-0001 — Copy-based kernel_request responses (baseline)

**Status:** Accepted  
**Decision:** The kernel_request ABI uses copy-based response buffers as the
required baseline; zero-copy variants are optional future extensions.  
**Why:** Keeps the ABI simple and portable across environments without
SharedArrayBuffer/Atomics.  
**References:** `doc/wasm/kernel-request-abi.md:60`, `doc/wasm/js-microkernel-spec.md:72`

## ADR-0002 — Keep CCL KERNEL_IMPORTS table (WASM keeps Lisp-side contract)

**Status:** Accepted  
**Decision:** WASM builds keep the Lisp-side KERNEL_IMPORTS table and route
host services through kernel-owned wrappers (often stubs) that call
`kernel_request`.  
**Why:** Preserves CCL’s existing kernel/FFI import model while adapting the
host boundary to the microkernel.  
**References:** `doc/wasm/kernel-request-abi.md:1`, `lisp-kernel/wasm-kernel-imports.c:1`

## ADR-0003 — Subprims are table indices, SUBPRIMS_BASE is sentinel

**Status:** Accepted  
**Decision:** Subprims are fixnum indices into a WASM function table; no
PC-style address arithmetic is used.  
**Why:** Matches the WASM execution model and remains stable across memory
growth.  
**References:** `doc/wasm/ABI.md:1`

## ADR-0004 — No WASI runtime (freestanding link)

**Status:** Accepted  
**Decision:** Compile with a wasm32 target + WASI headers (e.g.
`--target=wasm32-wasi` on Linux; on macOS use `-D__wasi__` with WASI headers),
but link freestanding (no `wasi_snapshot_preview1` imports).  
**Why:** Keep the kernel portable and host-controlled; avoid implicit POSIX.  
**References:** `doc/wasm/build.md:1`

## ADR-0005 — Stage‑2 stepping baseline (explicit yield/resume)

**Status:** Accepted  
**Decision:** Stage‑2 async uses explicit stepping (`wasm_ccl_step`) rather
than stack‑suspension toolchains; Stage‑3 `kernel_wait` is deferred.  
**Why:** Portable and simple; avoids asyncify/stack‑switch complexity.  
**References:** `doc/wasm/yield-resume.md:1`

## ADR-0006 — Single‑runner baseline, shared‑heap threads deferred

**Status:** Accepted  
**Decision:** Single‑runner is the portable baseline; shared‑heap threads are
optional and require a separate protocol and runtime changes.  
**Why:** Works in sandboxed iframes and avoids SAB/Atomics dependency.  
**References:** `doc/wasm/project-overview.md:100`, `doc/wasm/threads.md:1`

## ADR-0007 — Named read‑only streams (NAMED_RO) as initial file surface

**Status:** Accepted  
**Decision:** `STREAM_OPEN` kind `NAMED_RO` opens a named byte source and
returns size via response payload.  
**Why:** Minimal “file‑like” input for bring‑up and image/asset loading.  
**References:** `doc/wasm/kernel-request-abi.md:254`, `doc/wasm/streams-spec.md:10`

## ADR-0008 — start_lisp returns to host until real toplevel wired

**Status:** Accepted (temporary)  
**Decision:** `start_lisp` returns to the host; stepping interfaces are used
for bring‑up.  
**Why:** Real toplevel + loader integration is not yet wired for WASM.  
**References:** `doc/wasm/build.md:136`, `doc/wasm/yield-resume.md:94`

## ADR-0009 — Capability signaling via CAPABILITY‑UNAVAILABLE

**Status:** Accepted  
**Decision:** Missing host capabilities signal `CAPABILITY-UNAVAILABLE`, with
an implementation hook in the stream layer (feature‑gated).  
**Why:** Explicit failure is required for portable embeddings.  
**References:** `doc/wasm/capability-matrix.md:50`

## ADR-0010 — Track WASM 3.0 in spec research

**Status:** Accepted  
**Decision:** Include WASM 3.0 in spec research and compatibility checks.  
**Why:** WebAssembly 3.0 may change or clarify platform expectations that
affect the backend and host ABI decisions.  
**References:** (tracking note; update with concrete spec links as they are adopted)
