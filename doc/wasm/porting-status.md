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
- **Compiled module registry hook:** ✅  
  `%wasm-compiled-modules%` nilreg slot added; kernel exports
  `wasm_get_compiled_module_registry`, compiler records module entries, and
  JS loader installs them via `installCompiledModulesFromRegistry`.
- **Subprims provider module (separate build):** ✅  
  `lisp-kernel/wasm32/subprims/Makefile` builds `doc/wasm/js/subprims.wasm`.
- **Tier‑0 subprims (C):** ✅  
  `_SPmkcatch1v`, `_SPnthrow1value`, `_SPfuncall` implemented with cooperative
  unwind + table‑index function entry ABI; `_SPfuncall` syncs arg regs from
  VSP per WASM calling convention (see `doc/wasm/ABI.md`).
- **Fixnum helpers (kernel):** ⚠️  
  `wasm_return_fixnum_{add,sub,mul,ash,log*,neg}` helpers exist; arithmetic
  helpers allocate bignums on overflow via the minimal heap allocator (1–2
  digits for add/sub/neg/mul; arbitrary digits for large `ash` shifts).
- **Subprims (kernel + provider):** ✅  
  `_SPfix_overflow` + `_SPmakes32` implemented in both kernel and provider;
  provider imports `wasm_box_signed_64` from the kernel to allocate bignums.
- **Tier‑1 subprims (C):** ⚠️  
  `_SPthrow`, `_SPnthrowvalues`, `_SPmkcatchmv` implemented; provider still
  traps on native unwind‑protect frames, but the WASM compiler now emits
  cooperative cleanup in‑module with multi‑value preservation.
- **kernel_request ABI wrappers:** ✅  
  Synchronous + staged helpers in `wasm-host.c`.
- **Compiled-code helper exports:** ✅  
  `wasm_get_arg_y`, `wasm_get_nargs`, `wasm_set_arg_{z,y,x}`, `wasm_set_nargs`,
  `wasm_set_nfn`, `wasm_set_imm0`, `wasm_get_nfn`, `wasm_vpush`, `wasm_vpop`,
  `wasm_clear_pending_throw`,
  `wasm_call_subprim_fixnum`, `wasm_funcall{0,1,2}`, `wasm_funcall{0,1,2}_mv`,
  `wasm_return_values{2,3,4}`, `wasm_get_mv`, `wasm_get_mv_indexed`,
  `wasm_restore_vsp`.
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
- **Stream classes for WASM:** ✅  
  `wasm-stream` classes layered on `fd-stream`; `open` defaults to
  `wasm-stream` and standard streams are WASM‑compatible.
- **Filesystem/pathnames:** ✅  
  `:fs/virtual` policy enforced; mutating operations signal
  `capability-unavailable` and `current-directory-name` is `/`.

## Compiler / backend

- **Subprims ABI decisions:** ✅  
  Table‑index calling convention documented.
- **WASM function entry ABI:** ✅  
  Entry points are fixnum table indices; cooperative unwind flag defined.
- **WASM GC root discipline (doc):** ✅  
  Operand stack excluded; TCR register file is authoritative; spill rules
  documented in `doc/wasm/ABI.md`.
- **WASM target arch description (compiler):** ✅  
  `compiler/WASM/wasm-arch.lisp` defines a WASM32 target arch with ARM layout
  and subprim indices.
- **WASM backend scaffold (compiler):** ✅  
  `compiler/WASM/wasm-backend.lisp` + `lib/wasmenv.lisp` provide a minimal
  backend entry and route `p2-compile` through WASM2 emission.
- **WASM p2 dispatch (compiler):** ⚠️  
  `compiler/WASM/wasm2.lisp` lowers basic expressions (lexicals, let/setq,
  call, if, progn, values/mv-bind/nth-value) into a minimal IR and emits
  generic modules; `values` now supports >4 values via VSP pushes (MVP helper).
  Local control flow (`block`/`return-from`, `tagbody`/`go`) lowers via
  structured WASM IR. `catch`/`throw` implemented; `unwind-protect`
  now compiles to cooperative cleanup with full multiple-value preservation,
  and closures capture cells for inherited vars. `multiple-value-call` now
  supports multi-form mvcall.
- **WASM codegen state scaffold (compiler):** ✅  
  `compiler/WASM/wasm2.lisp` initializes backend state (register masks,
  target sizes) and emits WASM modules.
- **WASM constant IR (compiler):** ✅  
  `wasm-ir` capture records constant forms (`nil`, `t`, `fixnum`,
  `immediate`) and drives WASM emission.
- **Constant-return entry stub (kernel):** ✅  
  `wasm_const_entry` returns the constant stored in the current function
  object (slot 2) and falls back to `wasm_set_const_value` for bring-up.
- **WASM constant-function metadata (compiler):** ✅  
  `compiler/WASM/wasm2.lisp` tags constant-return forms with
  `wasm-const-value` + `wasm-entry-index` in `afunc-lfun-info`.
- **WASM constant-function objects (compiler):** ✅  
  `compiler/WASM/wasm2.lisp` now synthesizes a minimal function object that
  points at `wasm_const_entry` and stores the constant value in slot 2.
- **WASM constant IR emitter (compiler):** ✅  
  `compiler/WASM/wasm2.lisp` now emits a minimal WASM module for constant
  forms and records the module bytes + export name in `afunc-lfun-info`.
- **WASM fixnum add IR emitter (compiler):** ✅  
  `compiler/WASM/wasm2.lisp` now emits a minimal WASM module for fixnum add
  and records the module bytes + export name in `afunc-lfun-info`.
- **WASM fixnum sub IR emitter (compiler):** ✅  
  `compiler/WASM/wasm2.lisp` now emits a minimal WASM module for fixnum sub
  and records the module bytes + export name in `afunc-lfun-info`.
- **WASM fixnum mul/ash/log IR emitters (compiler):** ✅  
  `compiler/WASM/wasm2.lisp` now emits minimal WASM modules for fixnum mul,
  fixnum ash, and fixnum logand/logior/logxor/lognot, recording module bytes +
  export names in `afunc-lfun-info`.
- **WASM fixnum neg IR emitter (compiler):** ✅  
  `compiler/WASM/wasm2.lisp` emits a minimal WASM module for fixnum negation
  (`%ineg`/`%%ineg`) and records module bytes + export name.
- **WASM fixnum-overflow operator (compiler):** ⚠️  
  `fixnum-overflow` now routes to overflow‑checked fixnum ops; overflow
  allocates a 1–2 digit bignum in WASM (full bignum support still pending).
- **Compiler module wiring (compiler):** ⚠️  
  `lib/compile-ccl.lisp` + `lib/systems.lisp` include WASM compiler modules;
  no target build integration yet.
- **WASM vinsn templates (compiler):** ⚠️  
  Minimal template registration added in `compiler/WASM/wasm-vinsns.lisp`;
  no target-specific templates yet.
- **WASM codegen & runtime integration:** ⚠️  
  Generic modules emitted for basic forms with call helpers and compiled
  module registry installs; `block`/`tagbody` lower in WASM2. `catch`/`throw`
  route through subprims with pending-throw clearing; `unwind-protect`
  cleanup and closures are now supported (cooperative, multi-value preserved).
- **Funcall calling convention smoke test:** ✅  
  `funcall-smoke.mjs` validates VSP args → `arg_z/arg_y/arg_x` sync and
  single‑value return in `arg_z`.

## Tests

- **WASM smoke tests:** ✅  
  `smoke-test.mjs`, `kernel-request-smoke.mjs`,
  `compiled-modules-refresh-smoke.mjs`, `stream-open-smoke.mjs`,
  `pending-stdin-smoke.mjs`, `ccl-step-smoke.mjs`, `step-demo.mjs`,
  `funcall-smoke.mjs`, `const-funcall-smoke.mjs`,
  `const-module-smoke.mjs`, `if-smoke.mjs`, `if-arg-smoke.mjs`,
  `identity-smoke.mjs`, `identity-y-smoke.mjs`,
  `fixnum-add-smoke.mjs`, `fixnum-sub-smoke.mjs`, `fixnum-ops-smoke.mjs`,
  `fixnum-overflow-smoke.mjs`, `compiler-smoke.mjs`, `float-smoke.mjs`,
  `web-ui-list-smoke.mjs`, `web-ui-virtual-smoke.mjs`,
  `web-ui-canvas-smoke.mjs`, `web-ui-webgl-smoke.mjs`,
  `web-ui-command-ui-smoke.mjs`, `web-ui-persist-smoke.mjs`,
  `web-ui-layout-focus-smoke.mjs`, `web-ui-inspector-smoke.mjs`,
  `web-ui-debugger-smoke.mjs`, `closure-unwind-mv-smoke.mjs`,
  `mv-helpers-smoke.mjs`, `mvcall-smoke.mjs`.

## Major Gaps / Next Blockers

- Real Lisp toplevel entry (`start_lisp`) and event/step integration.
- Image format and loader policy (root image, cloning, module loading).
- Capability negotiation protocol beyond `CAPS` bitfield.
- Persistent storage policy beyond read‑only named streams.
- Shared‑heap threading protocol (if pursued).
