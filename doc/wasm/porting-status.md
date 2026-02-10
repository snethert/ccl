# Porting Status Checklist (CCL→WASM)

**Status:** Living document  
**Purpose:** Track what is implemented, partially complete, or missing.

## Track Split (Normative)

- Legacy compatibility lane: current unattended defaults and memory-snapshot
  persistence behavior remain documented for ongoing compatibility workflows.
- Replacement lane target architecture: secure-only startup gates,
  shared-memory-first runtime/UI transport, required worker topology, and
  Storage V2 local-core persistence profile.
- References in this file to memory-snapshot defaults are legacy-lane status
  notes, not replacement-lane target posture.

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
  `start_lisp` entry is callable in bring-up flows and strict root-image
  bootstrap checks are now passing (`root.image` manifest lane). `minimal.image`
  still fails strict pre-start bootstrap contract (expected bring-up lane).
- **Image boot path:** ⚠️  
  `wasm_ccl_load_image` works for the minimal image and the cross‑xload boot
  image (`wasm-boot.image` from `cross-xload-level-0 :wasm32`).
  `doc/wasm/js/load-image.mjs` now supports explicit loader modes
  (`boot-only|start-lisp|run-toplevel`), manifest hash validation, strict
  module policy controls, scripted stdin preload, and bootstrap contract modes
  (`strict|warn|off`, default strict). Root-lane compiled-Lisp UI persistence
  smoke is now green with save/restore wired through runtime file-backed
  persistence (`/ui/wasm-ui-state.bin`) and legacy-lane memory-snapshot
  dirty-flush regression checks; remaining work is core dispatch hardening plus
  replacement-lane convergence.

## JS microkernel / host

- **kernel_request ABI (MVP):** ✅  
  `CAPS`, `LOG`, `STREAM_*`, `TIME_NOW`.
- **Named byte sources registry:** ✅  
  `registerNamedBlob(s)` for `NAMED_RO`.
- **World/runner manager (reference):** ✅  
  `world-kernel.mjs` (bring-up helper).
- **Async PENDING (stdin):** ✅  
  Optional via `asyncStdin`.
- **kernel_wait (Stage‑3):** ❌  
  Deferred.

## Web UI (Browser Toolkit)

- **Reference state/command/layout model (JS):** ✅  
  Implemented in `web-ui/src/`, with deterministic tests in `web-ui/tests/`.
- **DOM/Canvas/WebGL backends (JS):** ✅  
  Implemented in `web-ui/backends/`.
- **Lisp<->JS bridge (WASM runner integration):** ⚠️  
  Runtime bridge flow is implemented for `runtime.output`, typed command dispatch,
  debugger/restart payloads, inspector/place-edit updates, and job lifecycle
  events (`web-ui/bridge/runtime.mjs`, `web-ui/src/runtime-bridge.mjs`,
  `KERNEL_OP_RUNTIME_EVENT`, `KERNEL_OP_RUNTIME_COMMAND_POLL`). Full compiled-Lisp
  UI path remains partial pending compiler/image bring-up blockers.

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
  supports multi-form mvcall, with spill/restore validation and allowlisted
  no-spill subprim checks enforced at codegen time.
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
  `runtime-modules-manifest-smoke.mjs`, `root-image-manifest-smoke.mjs`,
  `compiled-modules-refresh-smoke.mjs`, `stream-open-smoke.mjs`,
  `pending-stdin-smoke.mjs`, `ccl-step-smoke.mjs`, `step-demo.mjs`,
  `start-lisp-noninteractive-smoke.mjs`,
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
- **Known gate status:** ⚠️  
  `node doc/wasm/js/start-lisp-noninteractive-smoke.mjs` is green in default
  mode (contract-enforced fail case + warn-mode continuation case), and strict
  root gate is passing when explicitly requested. `node doc/wasm/js/all-smoke.mjs`
  is green with current regenerated artifacts. Root-lane compiled-Lisp UI
  persistence smoke is now passing
  (`node doc/wasm/js/wasm-ui-persist-smoke.mjs --verbose --image root`).

## Major Gaps / Next Blockers

- Permanent fix for root-lane core symbol/function dispatch instability
  discovered during persistence trap investigation.
- Continue hardening regression gates for the new UI save/restore persistence
  path while preserving legacy unattended `memory-snapshot` defaults and
  keeping replacement-lane Storage V2 requirements explicit.
- Capability negotiation protocol beyond `CAPS` bitfield.
- Ongoing integration hardening for LMDB/IndexedDB lanes while keeping
  `memory-snapshot` as legacy unattended default.
- Replacement-lane worker/shared-memory startup and transport contracts remain
  the architecture target (secure-only, no-fallback).
