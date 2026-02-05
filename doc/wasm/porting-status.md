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
- **Fixnum helpers (kernel):** ⚠️  
  `wasm_return_fixnum_{add,sub,mul,ash,log*,neg}` helpers exist; arithmetic
  helpers now trap on overflow (bignum allocation pending).
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
- **WASM target arch description (compiler):** ⚠️  
  `compiler/WASM/wasm-arch.lisp` defines a WASM32 target arch with ARM layout
  and subprim indices; backend emission still missing.
- **WASM backend scaffold (compiler):** ⚠️  
  `compiler/WASM/wasm-backend.lisp` + `lib/wasmenv.lisp` provide a minimal
  backend entry; code emission not implemented.
- **WASM p2 dispatch stub (compiler):** ⚠️  
  `compiler/WASM/wasm2.lisp` defines a placeholder `*wasm2-specials*` dispatch
  table that traps until real codegen exists.
- **WASM codegen state scaffold (compiler):** ⚠️  
  `compiler/WASM/wasm2.lisp` now initializes backend state (register masks,
  target sizes) but still traps before emission.
- **WASM constant IR (compiler):** ⚠️  
  Initial `wasm-ir` capture records constant forms (`nil`, `t`, `fixnum`,
  `immediate`) while real emission is pending.
- **Constant-return entry stub (kernel):** ⚠️  
  `wasm_const_entry` returns the constant stored in the current function
  object (slot 2) and falls back to `wasm_set_const_value` for bring-up.
- **WASM constant-function metadata (compiler):** ⚠️  
  `compiler/WASM/wasm2.lisp` tags constant-return forms with
  `wasm-const-value` + `wasm-entry-index` in `afunc-lfun-info`.
- **WASM constant-function objects (compiler):** ⚠️  
  `compiler/WASM/wasm2.lisp` now synthesizes a minimal function object that
  points at `wasm_const_entry` and stores the constant value in slot 2.
- **WASM constant IR emitter (compiler):** ⚠️  
  `compiler/WASM/wasm2.lisp` now emits a minimal WASM module for constant
  forms and records the module bytes + export name in `afunc-lfun-info`.
- **WASM fixnum add IR emitter (compiler):** ⚠️  
  `compiler/WASM/wasm2.lisp` now emits a minimal WASM module for fixnum add
  and records the module bytes + export name in `afunc-lfun-info`.
- **WASM fixnum sub IR emitter (compiler):** ⚠️  
  `compiler/WASM/wasm2.lisp` now emits a minimal WASM module for fixnum sub
  and records the module bytes + export name in `afunc-lfun-info`.
- **WASM fixnum mul/ash/log IR emitters (compiler):** ⚠️  
  `compiler/WASM/wasm2.lisp` now emits minimal WASM modules for fixnum mul,
  fixnum ash, and fixnum logand/logior/logxor/lognot, recording module bytes +
  export names in `afunc-lfun-info`.
- **WASM fixnum neg IR emitter (compiler):** ⚠️  
  `compiler/WASM/wasm2.lisp` emits a minimal WASM module for fixnum negation
  (`%ineg`/`%%ineg`) and records module bytes + export name.
- **WASM fixnum-overflow operator (compiler):** ⚠️  
  `fixnum-overflow` now routes to overflow‑checked fixnum ops; overflow
  currently traps until bignum allocation exists in WASM.
- **Compiler module wiring (compiler):** ⚠️  
  `lib/compile-ccl.lisp` + `lib/systems.lisp` include WASM compiler modules;
  no target build integration yet.
- **WASM vinsn templates (compiler):** ⚠️  
  Stub `compiler/WASM/wasm-vinsns.lisp` added; templates not implemented.
- **WASM codegen & runtime integration:** ❌  
  Compiler emission + real subprims integration pending.
- **Funcall calling convention smoke test:** ✅  
  `funcall-smoke.mjs` validates VSP args → `arg_z/arg_y/arg_x` sync and
  single‑value return in `arg_z`.

## Tests

- **WASM smoke tests:** ✅  
  `smoke-test.mjs`, `kernel-request-smoke.mjs`, `stream-open-smoke.mjs`,
  `pending-stdin-smoke.mjs`, `ccl-step-smoke.mjs`, `funcall-smoke.mjs`,
  `const-funcall-smoke.mjs`, `const-module-smoke.mjs`,
  `fixnum-add-smoke.mjs`, `fixnum-sub-smoke.mjs`, `fixnum-ops-smoke.mjs`,
  `fixnum-overflow-smoke.mjs`.

## Major Gaps / Next Blockers

- Real Lisp toplevel entry (`start_lisp`) and event/step integration.
- Image format and loader policy (root image, cloning, module loading).
- Capability negotiation protocol beyond `CAPS` bitfield.
- Pathname/FS policy for `:fs/virtual` and persistent storage.
- Shared‑heap threading protocol (if pursued).
