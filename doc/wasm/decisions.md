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

**Status:** Superseded  
**Decision:** `start_lisp` can now be entered after a boot‑only load via
`wasm_ccl_start_lisp`; stepping interfaces remain the host‑controlled
baseline.  
**Why:** The loader path now supports a post‑load `start_lisp` entry without
reinitializing the kernel.  
**References:** `doc/wasm/image-loader-spec.md:20`, `doc/wasm/build.md:179`

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
**References:** `doc/wasm/spec/README.md:1`, `doc/wasm/spec/core-multipage/index.html:1`

## ADR-0011 — PROGV uses a VSP sentinel instead of TSP frames (WASM)

**Status:** Accepted (temporary)  
**Decision:** `_SPprogvsave/_SPprogvrestore` record bindings on the VSP with a
sentinel binding entry (`sym = unbound_marker`) that stores the previous
`db_link` and `vsp`.  
**Why:** The WASM bring‑up does not yet model true TSP frames. Using a VSP
sentinel keeps bindings GC‑visible, avoids relying on incomplete tstack
semantics, and keeps unwind/restore logic self‑contained in the provider.  
**References:** `lisp-kernel/wasm-subprims-provider.c` (progv save/restore),
`lisp-kernel/arm-spentry.s` (tstack‑based reference).

## ADR-0012 — Constant pool v1 for non-immediate constants (WASM2)

**Status:** Accepted  
**Decision:** WASM2 compiled modules may carry a per‑module constant pool
(`constPool`) with v1 entries limited to `symbol`, `string`, `vector`, and
`function`. The loader materializes the pool before activating the module and
exposes entries via `const-pool-ref` indices.  
**Why:** Provides a portable, explicit mechanism for non‑immediate constants
without embedding raw Lisp object addresses in WASM code.  
**References:** `doc/wasm/const-pool.md:1`, `compiler/WASM/wasm2.lisp:1668`

## ADR-0013 — WASM FFI uses direct module imports (external-call)

**Status:** Accepted  
**Decision:** `external-call` on WASM compiles to **direct imports** from the
`ccl` module (the kernel instance). Import signatures are `i32`-only, with
arguments unboxed per their representation type and a single `i32` return
value (boxed into a Lisp fixnum on return).  
**Why:** Keeps the MVP FFI path simple, avoids a secondary `kernel_request`
channel, and matches the existing WASM2 external import machinery.  
**Notes:**  
- The external name must be a literal string at compile time.  
- Supported argument/result representations are the WASM FFI subset
  (`:address`, `:signed/unsigned-{fullword,halfword,byte}`, `:void`).  
- Up to 7 arguments are supported by the current import type set.  
**References:** `compiler/WASM/wasm2.lisp:1836`, `compiler/WASM/wasm-ffi.lisp:1`

## ADR-0014 — WASM fasl bring-up uses wasm32-only OS/FFI stubs

**Status:** Accepted  
**Decision:** For `#+wasm32-target`, OS/FFI-dependent operations in
`level-1/linux-files.lisp` are stubbed to signal capability unavailability,
no-op, or return conservative defaults (e.g. page size `4096`,
`cpu-count = 1`, `*max-os-open-files* = 32`). All behavior changes are guarded
with `#+wasm32-target` / `#-wasm32-target` so non‑WASM backends are unchanged.  
**Why:** The WASM runtime does not provide POSIX filesystem/process/mmap/dlopen
facilities yet. Stubbing these paths is the minimum to allow `l1-boot-3` and
WASM fasl compilation to complete while the host ABI matures.  
**Notes:** Pre‑existing compile warnings were not addressed as part of the
WASM fasl bring‑up.  
**References:** `level-1/linux-files.lisp:1`, `doc/wasm/capability-matrix.md:1`

## ADR-0015 — WASM2 complex lowers to a generic call

**Status:** Accepted (temporary)  
**Decision:** The WASM2 backend handles the `complex` operator by emitting a
generic `(complex ...)` call via the normal call emitter instead of a dedicated
opcode.  
**Why:** WASM2 previously lacked a `complex` opcode; lowering to the generic
call unblocks compilation (e.g. `coerce-to-complex`) without affecting other
backends.  
**References:** `compiler/WASM/wasm2.lisp:1`
