# Porting Status Checklist (CCL→WASM)

**Status:** Living document  
**Purpose:** Track what is implemented, partially complete, or missing.

## Kernel (C, WASM backend)

- **Build (freestanding, no WASI runtime):** ✅  
  `lisp-kernel/wasm32/Makefile` builds `doc/wasm/js/wasmcl.wasm`.
- **KERNEL_IMPORTS table (WASM):** ✅  
  Table points at kernel-owned functions and stubs.
- **Subprims readiness flag (host-set):** ✅  
  `wasm_set_subprims_ready` / `wasm_get_subprims_ready` exports.
- **Subprims provider module (separate build):** ⚠️  
  `lisp-kernel/wasm32/subprims/Makefile` builds `doc/wasm/js/subprims.wasm`.
- **Tier‑0 subprims (C):** ✅  
  `_SPmkcatch1v`, `_SPnthrow1value`, `_SPfuncall` implemented with cooperative
  unwind + table‑index function entry ABI; `_SPfuncall` syncs arg regs from
  VSP per WASM calling convention (see `doc/wasm/ABI.md`).
- **Tier‑1 subprims (C):** ⚠️  
  `_SPthrow`, `_SPnthrowvalues`, `_SPmkcatchmv` implemented; unwind‑protect
  frames still trap in the WASM provider.
- **kernel_request ABI wrappers:** ✅  
  Synchronous + staged helpers in `wasm-host.c`.
- **Streams (stdin/stdout/stderr):** ✅  
  `lisp_read/lisp_write` routed through `kernel_request`.
- **Named read‑only stream open/stat:** ✅  
  `lisp_open/lisp_stat` via `NAMED_RO` stream kind.
- **Real Lisp toplevel entry:** ⚠️  
  `start_lisp` can run a stub toplevel loop with the minimal boot image; real
  Lisp REPL still pending.
- **Image boot path:** ⚠️  
  `wasm_ccl_load_image` + minimal image generator load successfully (boot-only);
  real root image still pending.

## JS microkernel / host

- **kernel_request ABI (MVP):** ✅  
  `CAPS`, `LOG`, `STREAM_*`, `TIME_NOW`.
- **Named byte sources registry:** ✅  
  `registerNamedBlob(s)` for `NAMED_RO`.
- **World/runner manager (reference):** ✅  
  `world-kernel.mjs` (bring‑up helper).
- **Async PENDING (stdin):** ✅  
  Optional via `asyncStdin`.
- **kernel_wait (Stage‑3):** ❌  
  Deferred.

## Lisp runtime (Level‑1)

- **CAPABILITY‑UNAVAILABLE condition:** ✅  
  Implemented; gated by `*capability-unavailable-on-enosys*`.
- **Yield on EWOULDBLOCK:** ✅  
  `*wasm-yield-on-eagain*` + toplevel catch hook.
- **Stream classes for WASM:** ⚠️  
  Uses existing FD stream system; richer stream kinds pending.
- **Filesystem/pathnames:** ❌  
  Policy for `:fs/virtual` not finalized.

## Compiler / backend

- **Subprims ABI decisions:** ✅  
  Table‑index calling convention documented.
- **WASM function entry ABI:** ✅  
  Entry points are fixnum table indices; cooperative unwind flag defined.
- **WASM GC root discipline (doc):** ✅  
  Operand stack excluded; TCR register file is authoritative; spill rules
  documented in `doc/wasm/ABI.md`.
- **WASM codegen & runtime integration:** ❌  
  Compiler emission + real subprims integration pending.
- **Funcall calling convention smoke test:** ✅  
  `funcall-smoke.mjs` validates VSP args → `arg_z/arg_y/arg_x` sync and
  single‑value return in `arg_z`.

## Tests

- **WASM smoke tests:** ✅  
  `smoke-test.mjs`, `kernel-request-smoke.mjs`, `stream-open-smoke.mjs`,
  `pending-stdin-smoke.mjs`, `ccl-step-smoke.mjs`.

## Major Gaps / Next Blockers

- Real Lisp toplevel entry (`start_lisp`) and event/step integration.
- Image format and loader policy (root image, cloning, module loading).
- Capability negotiation protocol beyond `CAPS` bitfield.
- Pathname/FS policy for `:fs/virtual` and persistent storage.
- Shared‑heap threading protocol (if pursued).
