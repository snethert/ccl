# WASM UI Persistence Problem Resolution Tracker (Temporary)

Status: Active  
Owner: Runtime/WASM MVP execution track  
Started: 2026-02-08  
Last Updated: 2026-02-08 (late pass; after aborted forced runtime bundle rebuild)

## Purpose

Track root-cause analysis and permanent-fix execution for the compiled-Lisp UI
persistence blocker. This is a temporary working document for active debugging;
once resolved, conclusions are folded into:

- `doc/wasm/mvp-unattended-execution-report.md`
- `doc/wasm/porting-status.md`
- `doc/wasm/roadmap.md`
- `doc/wasm/persistence-service-spec.md` (if contract changes are required)

## Build Command Note (Critical)

**ALWAYS COMPILE WASM C ARTIFACTS THROUGH `scripts/wasm/env.sh` SO `CC`/`WASM_LD` ARE SET CORRECTLY.**
**DO NOT HAND-INVOKE `clang`/`wasm-ld` WITH AD-HOC FLAGS FOR NORMAL DEV BUILDS.**

Use exactly:

```bash
/bin/zsh -lc 'source scripts/wasm/env.sh && make -C lisp-kernel/wasm32 CC="$CC" WASM_LD="$WASM_LD"'
/bin/zsh -lc 'source scripts/wasm/env.sh && make -C lisp-kernel/wasm32/subprims clean && make -C lisp-kernel/wasm32/subprims CC="$CC" WASM_LD="$WASM_LD"'
```

## Problem Statement

The default unattended lane now uses memory-first snapshot persistence, but
`doc/wasm/js/wasm-ui-persist-smoke.mjs` still fails when invoking compiled UI
persistence entry functions. The prior hard hang has shifted to deterministic
throw-path failures (`wasm_pending_throw_p=1`) returned as raw Lisp objects
through `wasm_test_entry_funcall`.

This prevents closure of the remaining MVP runtime blocker.

## Non-Negotiable Constraints (Permanent Fix Policy)

1. No workaround that bypasses compiled-Lisp UI persistence behavior.
2. No host-permission coupling in the default unattended path.
3. Fix must preserve existing boot/start-lisp green gates.
4. Fix must include regression coverage that fails on reintroduction.
5. Debug-only instrumentation must remain optional and bounded.

## Current Reproduction

### Command

```bash
node doc/wasm/js/wasm-ui-persist-smoke.mjs --verbose --image minimal
```

### Observed

- Harness reaches: kernel/subprims init, image load, `wasm_ccl_start_lisp`,
  module installation.
- Current failing point in full smoke is `mark-persisted`:
  - minimal image: `FAIL: mark persisted failed: 16842623`
  - root image: `FAIL: mark persisted failed: 16826239`
- Probe-only runs can still return successfully as process-level commands, but
  many entry results are throw objects (not valid fixnum return codes).
- Kernel-request stream does not show a persistence backend contract failure;
  this is still a runtime/bootstrap binding defect path.

## Confirmed Facts (Evidence Summary)

1. `memory-snapshot` persistence backend and snapshot tests pass.
2. `node doc/wasm/js/all-smoke.mjs` passes.
3. `npm --prefix web-ui run test:sandbox` passes.
4. Entry call probe for `WASM-UI-DEMO` can return normally with probe-safe
   module bodies.
5. Persistence-related entry probes either hang at `FUNCALL` or fail module
   const-pool install depending on module body shape.
6. Rebuilding `wasm-ui-modules` does not by itself clear the blocker.
7. `wasm-boot.image` const-pool install can return `NIL` until
   `wasm_reset_root_image_runtime_state` runs; ordering is significant for boot
   image host flows.
8. Forward `cons` references in const pools are emitted by the compiler
   (example: `(1 . 2)` encoded with later indices), and strict backward-only
   loader assumptions caused deterministic install failures.
9. Kernel const-pool installer now supports forward `cons` references (patched
   in `lisp-kernel/wasm-kernel-stubs.c`), removing that failure class.
10. Function constants for key bootstrap symbols (for example
    `COMMON-LISP::CAR`, `CCL::SET-PACKAGE`, `CCL::%FASLOAD`) still resolve to
    `UDF` in the current image state, which blocks compiled entry execution.
11. Current `root.image` runtime sanity check still reports no CL package:
    `wasm_debug_find_package_common_lisp_raw() == wasm_get_lisp_nil()`.
12. Added const-pool fallback logging now shows concrete synthesized names:
    package fallbacks: `COMMON-LISP`, `CCL`
    symbol fallbacks include: `BOUNDP`, `SYMBOL-VALUE`, `SET`, `READ`, `PRIN1`,
    `OPEN`, `CLOSE`, `ERROR`, `%HANDLERS%`, and
    `*WASM-UI-PERSIST-LABEL-STATE*`.
13. `doc/wasm/wasm-runtime-modules.json` is currently a tiny v2 manifest
    (`wasm-runtime-modules.bin` 5957 bytes, `.idx` 71 bytes, functions=1),
    matching the previously observed under-populated runtime bundle.
14. Forced rebuild of runtime modules currently does not complete because
    `compiler/WASM/wasm2.lisp` spill-discipline allowlist rejects emitted
    `:call-subprim-no-spill` subprims from `l1-boot-1` (`104`, then `160`).
15. Patches landed in-progress:
    - `scripts/wasm/compile-wasm-fasls.sh`: force recompilation when
      `--modules-out`/`--modules-debug-out` is requested.
    - `compiler/WASM/wasm2.lisp`: allowlist extended with
      `.SPmkcatchmv`, `.SPnthrowvalues`.
    - `lisp-kernel/wasm-kernel-stubs.c`: fallback logs include exact
      package/symbol names for diagnosis.

## Working Hypotheses (Ranked)

1. **H1 (Highest):** runtime image/bootstrap is functionally incomplete in the
   active artifact lane (missing effective `COMMON-LISP`/`CCL` package graph),
   so const-pool install creates fallback package/symbol objects whose function
   cells are `UDF`; compiled entry execution then throws on core operations.
2. **H2:** runtime modules artifact generation bug (module collection from
   `%wasm-compiled-modules%` when modules are up-to-date) produced a
   too-small runtime bundle, and `root.image` generated from this lane cannot
   satisfy expected bootstrap invariants.
3. **H3:** forcing full runtime bundle rebuild is currently blocked by stale
   WASM spill-discipline allowlist coverage in `compiler/WASM/wasm2.lisp`
   (newly emitted no-spill subprims for `l1-boot-1`).
4. **H4 (Lower):** after full bundle rebuild is fixed, remaining throw paths
   may still expose secondary runtime defects, but current evidence points first
   to artifact/bootstrap incompleteness.

## Permanent-Fix Execution Plan

## PF-1: Minimal Failing Primitive Isolation

- Build micro-variants of failing entries and isolate the first expression form
  that causes non-returning behavior.
- Target categories:
  - literal/symbol constants
  - special-variable access
  - pathname construction
  - stream open/read/write
  - reader (`read`) usage

Exit criteria:
- A single minimal function body that reliably reproduces the hang.

## PF-2: Compiler/Runtime Differential Analysis

- Compare generated artifacts for:
  - known-good entry (`WASM-UI-DEMO`)
  - minimal failing entry from PF-1
- Inspect const-pool installation, entry metadata, and runtime call flow.
- Confirm whether failure is compile-time emission, const-pool install, or
  runtime execution semantics.

Exit criteria:
- Root cause is narrowed to a specific subsystem and code location.

## PF-3: Implement Product Fix (No Behavioral Bypass)

- Apply a real fix in compiler/runtime/lisp runtime path where defect is
  located.
- Keep compiled UI persistence behavior intact (no fallback to fake JS-only
  semantics).

Exit criteria:
- Target root cause resolved in code.

## PF-4: Restore Canonical UI Persistence Path

- Ensure `scripts/wasm/compile-ui-modules.lisp` compiles intended production
  entry behavior (not debugging scaffolds).
- Validate `wasm-ui-persist-smoke` end-to-end under `memory-snapshot` default.

Exit criteria:
- Smoke passes without debug flags.

## PF-5: Regression Gates

- Add/extend smokes and tests so failure mode cannot silently recur:
  - entry probe checks for persistence functions
  - timeout/hang detection around persistence smoke
  - if applicable, compiler-level regression test for identified defect

Exit criteria:
- CI/default unattended flow fails fast on regression.

## Active Task Board

- [x] Create temporary tracker and baseline constraints.
- [x] Add bounded kernel request tracing support.
- [x] Add entry-level probe controls in persistence smoke harness.
- [x] Complete PF-1 primitive isolation.
- [x] Complete PF-2 differential analysis.
- [ ] Land PF-3 permanent root-cause fix (runtime bundle/bootstrap closure).
- [ ] Complete PF-4 canonical path validation.
- [ ] Complete PF-5 regression gates and doc reconciliation.

## Decision Log

### 2026-02-08 — Keep Debug Instrumentation Optional

Decision:
- Keep deep tracing/probe features behind explicit flags.

Reason:
- Needed for unattended diagnosis but must not alter default behavior.

### 2026-02-08 — Treat This As Runtime Defect, Not Permission Defect

Decision:
- Continue root-cause investigation in compiled runtime path.

Reason:
- Hang reproduces with in-memory/memory-snapshot backend and no post-entry host
  request activity.

### 2026-02-08 — Promote Forward Const-Pool Reference Handling To Product Fix

Decision:
- Implement forward `cons` const-pool support in kernel loader instead of
  constraining compiler output ordering.

Reason:
- Compiler emits valid forward references for quoted cons payloads; rejecting
  them at load-time creates deterministic false failures.

### 2026-02-08 — Log Exact Fallback Names In Kernel Const-Pool Loader

Decision:
- Extend fallback logging to print the exact package/symbol name bytes.

Reason:
- Needed to prove whether fallback creation is expected (edge package) or
  symptomatic of missing core package state (`COMMON-LISP`, `CCL`).

### 2026-02-08 — Force Recompile For Runtime Bundle Emission

Decision:
- When `compile-wasm-fasls.sh` emits `--modules-out`/`--modules-debug-out`,
  force recompilation so every runtime module contributes to
  `%wasm-compiled-modules%` in-process.

Reason:
- Without force, up-to-date modules were skipped and runtime bundle emission
  captured only newly compiled entries, producing an incomplete artifact.

## Experiment Log (Append-Only)

### 2026-02-08 E01

Command:
- `node doc/wasm/js/wasm-ui-persist-smoke.mjs --probe-entry WASM-UI-DEMO --image minimal`

Result:
- Returns normally (`raw=0`, `fixnum=0`).

Interpretation:
- Entry invocation mechanism itself is functional.

### 2026-02-08 E02

Command:
- `node doc/wasm/js/wasm-ui-persist-smoke.mjs --verbose --probe-entry WASM-UI-MARK-PERSISTED --image minimal`

Result:
- Hangs after probe entry call begins.

Interpretation:
- Failure is specific to persistence-related entry body semantics.

### 2026-02-08 E03

Command:
- `node doc/wasm/js/wasm-ui-persist-smoke.mjs --image minimal --probe-entry WASM-UI-MARK-PERSISTED --verbose`

Result:
- Prior to kernel patch: const-pool install failed at entry 323 when quoted
  cons payload used forward indices.
- After kernel patch: module install succeeds; entry call advances to Lisp
  `FUNCALL` and then hangs.

Interpretation:
- Forward-const-pool defect was real and fixed.
- Remaining blocker moved to function binding/bootstrap execution.

### 2026-02-08 E04

Command:
- Direct const-pool probes for function constants (`COMMON-LISP::CAR`,
  `CCL::SET-PACKAGE`, `CCL::%FASLOAD`) on loaded images.

Result:
- Function-constant install resolves to `NIL` (UDF function cell) in current
  runtime image state.

Interpretation:
- Core bootstrap function bindings are missing; compiled execution cannot
  progress reliably.

### 2026-02-08 E05

Command:
- Direct const-pool install probes on `wasm-boot.image` before vs. after
  `wasm_reset_root_image_runtime_state`.

Result:
- Before reset: even symbol const-pool install returns `NIL`.
- After reset: symbol const-pool install succeeds.

Interpretation:
- Boot-image loader ordering is a hard invariant; reset/stack/runtime setup must
  occur before const-pool install in boot-image host flows.

### 2026-02-08 E06

Command:
- `scripts/wasm/compile-ui-modules.sh`
- `node doc/wasm/js/wasm-ui-persist-smoke.mjs --image minimal --verbose`
- `node doc/wasm/js/wasm-ui-persist-smoke.mjs --image root --verbose`

Result:
- UI bundle rebuilt with explicit non-recursive entry forms.
- Full smoke still fails at `mark-persisted` with throw-object fixnums:
  - minimal: `16842623`
  - root: `16826239`

Interpretation:
- Wrapper recursion was not the remaining root cause.
- Failure is still upstream runtime/bootstrap binding state.

### 2026-02-08 E07

Command:
- Rebuild kernel with fallback-name logging:
  `/bin/zsh -lc 'source scripts/wasm/env.sh && make -C lisp-kernel/wasm32 CC=\"$CC\" WASM_LD=\"$WASM_LD\"'`
- Probe:
  `node doc/wasm/js/wasm-ui-persist-smoke.mjs --image minimal --verbose --probe-entry WASM-UI-MARK-PERSISTED`

Result:
- Const-pool fallback logs include:
  - package: `COMMON-LISP`, `CCL`
  - symbols: `BOUNDP`, `SYMBOL-VALUE`, `SET`, `READ`, `PRIN1`, `OPEN`,
    `CLOSE`, `ERROR`, `%HANDLERS%`, `*WASM-UI-PERSIST-LABEL-STATE*`, others.

Interpretation:
- Core package/symbol resolution is not available in active runtime image lane;
  fallback synthesis is contaminating execution with `UDF` fcells.

### 2026-02-08 E08

Command:
- direct package sanity probe (after load/reset/start):
  `wasm_debug_find_package_common_lisp_raw()` vs `wasm_get_lisp_nil()`
  on `minimal.image` and `root.image`

Result:
- For both images:
  - `wasm_debug_find_package_common_lisp_raw() == wasm_get_lisp_nil()`

Interpretation:
- `COMMON-LISP` package is effectively absent in current active image artifacts.

### 2026-02-08 E09

Command:
- Inspect runtime bundle manifest:
  `doc/wasm/wasm-runtime-modules.json`

Result:
- v2 bundle currently tiny/incomplete:
  - `wasm-runtime-modules.bin`: 5957 bytes
  - `wasm-runtime-modules.idx`: 71 bytes
  - functions: `1`

Interpretation:
- Active runtime artifact lane is not representative of a full runtime module
  closure; this is consistent with missing package/bootstrap state.

### 2026-02-08 E10

Command:
- Forced rebuild:
  `/bin/zsh -lc 'source scripts/wasm/env.sh && scripts/wasm/compile-wasm-fasls.sh --modules-out doc/wasm/wasm-runtime-modules.json'`

Result:
- Initial hard failures during `l1-boot-1` compile:
  - `WASM2 spill discipline: call-subprim-no-spill not allowlisted: 104`
  - after allowlist patch, next failure:
    `... not allowlisted: 160`
- Added no-spill allowlist entries in `compiler/WASM/wasm2.lisp`:
  `.SPmkcatchmv`, `.SPnthrowvalues`
- Next forced rebuild advanced through most of level-1/lib modules and helper,
  but run was user-aborted before completion confirmation.

Interpretation:
- Runtime bundle rebuild path is directionally correct but currently blocked by
  stale compiler allowlist coverage and interrupted execution.

## Proposed Precise Next Steps

1. Complete forced runtime bundle rebuild to deterministic success (no abort):
`/bin/zsh -lc 'source scripts/wasm/env.sh && scripts/wasm/compile-wasm-fasls.sh --modules-out doc/wasm/wasm-runtime-modules.json'`.
If spill-discipline rejects another fixnum, map it to subprim symbol and extend
`*wasm2-no-spill-subprim-symbols*` in `compiler/WASM/wasm2.lisp`.
2. Verify rebuilt runtime artifact is full-sized and coherent:
confirm `doc/wasm/wasm-runtime-modules.bin`/`.idx` grew materially beyond
current tiny values and module/function counts are realistic.
3. Rebuild boot/root images from the corrected runtime artifact:
`scripts/wasm/build-wasm-boot.sh`, then
`node doc/wasm/js/make-real-image.mjs --modules doc/wasm/wasm-runtime-modules.json --output doc/wasm/root.image`.
4. Re-run package sanity probes before persistence smoke:
assert `wasm_debug_find_package_common_lisp_raw() != wasm_get_lisp_nil()`
after load/reset/start on `minimal.image` and `root.image`.
5. Re-run persistence validation:
`node doc/wasm/js/wasm-ui-persist-smoke.mjs --image minimal --verbose`,
then `node doc/wasm/js/wasm-ui-persist-smoke.mjs --image root --verbose`.
6. If package sanity is fixed but persistence still fails, decode throw object
   identity (arg_y/arg_z/nfn) and continue PF-3 with a targeted runtime fix.

## Exit Conditions for Tracker Retirement

This temporary tracker is retired only when all are true:

1. `node doc/wasm/js/wasm-ui-persist-smoke.mjs` passes in default unattended
   mode.
2. Root cause and fix are documented in permanent status/report docs.
3. Regression tests for the identified failure mode are merged.
