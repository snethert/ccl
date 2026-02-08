# WASM UI Persistence Problem Resolution Tracker (Temporary)

Status: Active  
Owner: Runtime/WASM MVP execution track  
Started: 2026-02-08  
Last Updated: 2026-02-08 (eighth pass; save-boundary closure verified, blocker re-scoped to UI preflight runtime trap)

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

The default unattended lane now uses memory-first snapshot persistence, and
root-image strict loader/manifest gates are green. The remaining blocker is in
compiled-Lisp UI persistence execution after `start_lisp`.

Current harness invariants show:

- `wasm_ccl_start_lisp` returns normally.
- `root.image` now passes strict pre-start/post-start bootstrap contracts.
- `minimal.image` still fails strict pre-start contract (expected bring-up lane).
- In root lane, compiled UI preflight (`WASM-UI-LABEL-STATE`) traps with
  `RuntimeError: unreachable` after successful module install.

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
node doc/wasm/js/wasm-ui-persist-smoke.mjs --verbose --image root
node doc/wasm/js/wasm-ui-persist-smoke.mjs --verbose --image minimal
```

### Observed

- Harness reaches: kernel/subprims init, image load, runtime bundle install,
  runtime reset, boot entry install.
- `root.image` lane:
  - pre-start/post-start bootstrap contracts both pass.
  - compiled UI modules install successfully.
  - preflight call then fails:
    `FAIL: Lisp UI not runnable in persistence smoke: unreachable`.
- `minimal.image` lane:
  - fails early (by design under strict contract):
    `FAIL: pre-start bootstrap contract failed: COMMON-LISP package is NIL ...`
- Kernel-request stream does not show persistence backend contract failure;
  this remains runtime/image bootstrap state.

## Confirmed Facts (Evidence Summary)

1. `memory-snapshot` persistence backend and snapshot tests pass.
2. `npm --prefix web-ui test` passes.
3. `node doc/wasm/js/all-smoke.mjs` passes.
4. `node doc/wasm/js/start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive`
   passes.
5. Runtime bundle artifacts are coherent and current:
   - modules: `7620`
   - `doc/wasm/wasm-runtime-modules.bin`: `436,499,792` bytes
   - `doc/wasm/wasm-runtime-modules.idx`: `125,673` bytes
6. `scripts/wasm/compile-ui-modules.sh` currently succeeds and emits:
   - `doc/wasm/wasm-ui-modules.json`
   - `doc/wasm/wasm-ui-modules.bin`
   - `doc/wasm/wasm-ui-modules.idx`
7. `wasm_save_image_direct` now preserves save-time area integrity by disabling
   EGC around direct save and restoring the prior EGC state afterward.
8. Save-boundary instrumentation now shows non-empty dynamic range at save time
   in successful runs, and pre-save/reload-pre bootstrap state parity.
9. Regenerated `doc/wasm/root.image` + `doc/wasm/root.image.manifest.json`
   pass strict manifest + bootstrap validation.
10. `node doc/wasm/js/load-image.mjs --mode start-lisp --manifest doc/wasm/root.image.manifest.json --stdin-text "(quit)\n" --close-stdin`
    succeeds with:
    - `bootstrap_contract pre-start ok`
    - `wasm_ccl_start_lisp rc=0`
    - `bootstrap_contract post-start ok`
11. `load-image` contract enforcement (`--bootstrap-contract strict|warn|off`)
    remains active; strict mode is now valid for root lane.
12. Kernel const-pool loader now handles forward references beyond `cons`:
    - forward refs in `vector`, `function-vector`, `gvector`, and `cons`
      are created in first pass and patched in second pass.
13. This forward-ref fix clears the prior on-demand install failure class
    observed at runtime entry `3712` (`STRING-INPUT-STREAM-IOBLOCK-OFFSET`).
14. Root lane persistence smoke progresses past bootstrap and module install:
    - pre-start contract OK
    - post-start contract OK
    - compiled UI modules install
    - first compiled UI preflight call traps with `unreachable`.
15. Root lane still shows fallback symbol synthesis during UI module install
    (`OPEN`, `READ`, `PRIN1`, etc.), which is likely relevant to the preflight
    trap but no longer blocks installation itself.
16. Minimal lane still fails strict pre-start bootstrap contract (CL package
    NIL / TOPLEVEL missing), and remains a bring-up lane.
17. The remaining blocker is no longer save-boundary state loss; it is compiled
    UI entry runtime behavior after successful root bootstrap closure.
18. Persistence backend plumbing is not the current blocker: failure occurs
    before backend write semantics are exercised.
19. Existing foundational patches remain required and active:
    - `wasm_reset_root_image_runtime_state` preserves `%TOPLEVEL-FUNCTION%`
    - `wasm_exit_lisp_frame` tolerates pre-unwound host-entered exits
    - loader/runtime bootstrap contract probes are shared between tools.
20. Strict build gating remains valuable: invalid root candidates are rejected
    during generation and no manifest refresh occurs on failed sanity checks.

## Working Hypotheses (Ranked)

1. **H1 (Highest):** the current blocker is now inside compiled UI entry
   execution (`WASM-UI-LABEL-STATE` preflight) after successful root bootstrap,
   not image save/reload boundary integrity.
2. **H2:** residual fallback symbol/package synthesis in UI module install
   indicates some core bindings are still unresolved at runtime call boundary;
   the trapped preflight path likely dereferences a missing/invalid callable.
3. **H3:** one or more compiled UI module lambda/spec forms may still encode a
   runtime shape that triggers a deterministic subprim/runtime trap (`unreachable`)
   even with successful const-pool install.
4. **H4:** minimal lane bootstrap failure is real but secondary for current
   closure; root lane must be stabilized first because it already reaches the
   compiled entry preflight boundary.
5. **H5 (Lower):** full runtime const-pool preinstall OOB defects may remain as
   separate hardening work but are not the root blocker for the current root
   lane failure path.

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
- [x] Execute Step 1 bootstrap contract enforcement in tooling.
- [x] Enforce bootstrap sanity gate in root-image build flow.
- [ ] Land PF-3 permanent root-cause fix (compiled UI preflight/runtime trap closure on root lane).
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

### 2026-02-08 E11

Command:
- completed forced runtime bundle rebuild and verification:
  `/bin/zsh -lc 'source scripts/wasm/env.sh && scripts/wasm/compile-wasm-fasls.sh --modules-out doc/wasm/wasm-runtime-modules.json'`

Result:
- runtime bundle now full-sized and coherent:
  - functions: `4799`
  - modules: `7620`
  - `wasm-runtime-modules.bin`: `436,499,792` bytes
  - `wasm-runtime-modules.idx`: `125,673` bytes

Interpretation:
- prior tiny/incomplete bundle state was real and is now resolved.

### 2026-02-08 E12

Command:
- validate `load -> reset -> start_lisp` with strict noninteractive lane:
  `node doc/wasm/js/start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive`

Result:
- root-image strict start-lisp lane now passes after:
  - preserving `nrs_TOPLFUNC` in reset
  - tolerating pre-unwound host-entered frames in `wasm_exit_lisp_frame`

Interpretation:
- start_lisp/runtime frame regressions are fixed, but this did not clear the UI
  persistence blocker.

### 2026-02-08 E13

Command:
- second-pass loader sequencing fix in UI smoke:
  - install boot entry
  - install runtime bundle
  - install registry modules
  - then call `wasm_ccl_start_lisp`

Result:
- `wasm-ui-persist-smoke` now fails early and deterministically with:
  `FAIL: COMMON-LISP package missing after start_lisp`

Interpretation:
- this is a cleaner/faster failure that confirms bootstrap closure is still
  missing before UI module const-pool install.

### 2026-02-08 E14

Command:
- inspect `%TOPLEVEL-FUNCTION%` raw object on loaded images via debug exports:
  `wasm_debug_get_nrs_toplfunc_raw`, `wasm_debug_function_entry_index`,
  `wasm_debug_misc_subtag`

Result:
- `minimal.image`: function object, entry index `200` (expected boot stub)
- `root.image`: misc object with subtag `0` (pseudofunction path), not a
  function object (`entry index = -1`)

Interpretation:
- root-image toplevel seed is materially different from minimal and likely does
  not execute the expected bootstrap closure.

### 2026-02-08 E15

Command:
- attempted full runtime const-pool preinstall (`installConstPools: true`) after
  load/reset on root lane.

Result:
- reproducible failure:
  `compiled module install failed ccl_generic_entry_443 ... RuntimeError: memory access out of bounds`
- fallback logging explodes with hundreds of synthesized core symbols/packages.

Interpretation:
- full const-pool preinstall is not currently a viable bootstrap workaround.

### 2026-02-08 E16

Command:
- comparative image-lane bootstrap probe (single script, identical host/runtime
  setup) across:
  - `doc/wasm/minimal.image`
  - `doc/wasm/root.image`
  - `wasm-boot.image`
- probe fields:
  - CL package pointer (`wasm_debug_find_package_common_lisp_raw`)
  - `%TOPLEVEL-FUNCTION%` raw object/subtag/entry index
  - `TOPLEVEL` symbol lookup
  - before reset, after reset, pre-start, post-start

Result:
- `minimal.image`:
  - CL package always NIL
  - `%TOPLEVEL-FUNCTION%` starts as function entry 200, then NIL after start
  - `TOPLEVEL` symbol lookup returns 0
- `root.image`:
  - CL package always NIL
  - `%TOPLEVEL-FUNCTION%` starts as non-function (subtag 0), then NIL after start
  - `TOPLEVEL` symbol lookup returns 0
- `wasm-boot.image`:
  - CL package non-NIL at all measured points
  - `%TOPLEVEL-FUNCTION%` starts as function entry 4528, then NIL after start
  - `TOPLEVEL` symbol lookup returns non-NIL symbol object

Interpretation:
- bootstrap health diverges by image artifact, not by host loader/runtime setup.
- `wasm-boot.image` has expected bootstrap closure; saved images do not.

### 2026-02-08 E17

Command:
- strict loader gate:
  `node doc/wasm/js/load-image.mjs --mode start-lisp --manifest doc/wasm/root.image.manifest.json --stdin-text \"(quit)\\n\" --close-stdin`

Result:
- command exits successfully (`wasm_ccl_start_lisp rc=0`) with strict manifest
  hash checks and full runtime bundle install.

Interpretation:
- `start_lisp rc=0` is not a sufficient readiness signal; package/bootstrap
  invariants must be checked explicitly.

### 2026-02-08 E18

Command:
- `node doc/wasm/js/wasm-ui-persist-smoke.mjs --verbose --image root`
- `node doc/wasm/js/wasm-ui-persist-smoke.mjs --verbose --image minimal`

Result:
- root lane fails pre-start bootstrap contract with:
  - CL package NIL
  - TOPLEVEL symbol missing (`0`)
  - `%TOPLEVEL-FUNCTION%` non-callable (pseudofunction/misc object)
- minimal lane fails pre-start bootstrap contract with:
  - CL package NIL
  - TOPLEVEL symbol missing (`0`)
  - `%TOPLEVEL-FUNCTION%` still callable (entry 200), but contract still fails.

Interpretation:
- Shared sanity contract is now active and catches the bootstrap defect at the
  earliest safe boundary, before persistence entry execution.

### 2026-02-08 E19

Command:
- strict contract:
  `node doc/wasm/js/load-image.mjs --mode start-lisp --modules doc/wasm/wasm-runtime-modules.json --stdin-text "(quit)\n" --close-stdin doc/wasm/root.image`
- warn contract:
  `node doc/wasm/js/load-image.mjs --mode start-lisp --bootstrap-contract warn --modules doc/wasm/wasm-runtime-modules.json --stdin-text "(quit)\n" --close-stdin doc/wasm/root.image`

Result:
- strict mode fails pre-start on contract violation.
- warn mode continues, `wasm_ccl_start_lisp rc=0`, then reports post-start
  contract warnings (CL package still NIL; TOPLEVEL missing).

Interpretation:
- contract enforcement is operational and confirms that return code alone is not
  a sufficient image-readiness signal.

### 2026-02-08 E20

Command:
- manifest-gated strict start:
  `node doc/wasm/js/load-image.mjs --mode start-lisp --manifest doc/wasm/root.image.manifest.json --stdin-text "(quit)\n" --close-stdin`

Result:
- fails hash check before runtime start:
  `kernelWasm hash mismatch ... expected ... got ...`

Interpretation:
- local kernel rebuild invalidated current manifest; image+manifest must be
  regenerated together before using manifest-gated validation.

### 2026-02-08 E21

Command:
- `node doc/wasm/js/make-real-image.mjs --modules doc/wasm/wasm-runtime-modules.json --output /tmp/ccl-root-image-sanity-test-<ts>.image --manifest-out /tmp/ccl-root-image-sanity-test-<ts>.image.manifest.json`

Result:
- command fails hard with:
  - `FAIL: bootstrap sanity check failed; manifest not updated: emitted root.image candidate bootstrap sanity failed ...`
  - nested strict failure from `load-image` pre-start contract:
    CL package NIL, TOPLEVEL missing, `%TOPLEVEL-FUNCTION%` non-callable.
- no manifest file is emitted for the failed candidate.

Interpretation:
- root-image build now correctly blocks publication of invalid artifacts and
  converts bootstrap integrity into an explicit build gate.

### 2026-02-08 E22

Command:
- `node doc/wasm/js/start-lisp-noninteractive-smoke.mjs`

Result:
- default harness now passes with:
  - strict minimal-lane contract failure expectation
  - warn-mode minimal-lane continuation expectation (`wasm_ccl_start_lisp rc=0`)
  - strict root lane skipped unless explicitly requested.

Interpretation:
- non-interactive loader smoke remains deterministic and useful during
  bootstrap closure work instead of providing stale “green” signals.

### 2026-02-08 E23

Command:
- `node doc/wasm/js/all-smoke.mjs --no-ui`

Result:
- fails early at `root-image-manifest-smoke` with:
  `FAIL: kernelWasm hash mismatch ...`

Interpretation:
- artifact hash contract is actively enforcing consistency; stale manifest
  state is surfaced immediately and should not be masked.

### 2026-02-08 E24

Command:
- instrumented boundary run:
  `node doc/wasm/js/make-real-image.mjs --modules doc/wasm/wasm-runtime-modules.json --output /tmp/ccl-root-boundary-<ts>.image --manifest-out /tmp/ccl-root-boundary-<ts>.image.manifest.json --bootstrap-boundary-report /tmp/ccl-root-boundary-<ts>.bootstrap.json`

Result:
- captured deterministic diff:
  - pre-save: `cl=0x4020016`, `toplevel_sym=0x40201c6`,
    `toplfunc_raw=0x4036546`, entry `4528`, subtag `42`
  - reload pre-start: `cl=nil`, `toplevel_sym=0`,
    `toplfunc_raw=0x4036546`, entry `-1`, subtag `0`
  - reload post-start: still `cl=nil`, `toplevel_sym=0`
- strict sanity gate then fails as expected.

Interpretation:
- divergence is now proven at the save boundary itself: state is valid before
  save and invalid immediately after fresh reload of emitted bytes.

### 2026-02-08 E25

Command:
- source audit + targeted kernel experiment:
  - audited `lisp-kernel/wasm-kernel-stubs.c` and `lib/dumplisp.lisp`
  - temporary test seeding `nrs_TOPLFUNC <- nrs_RESTORE_LISP_POINTERS.fcell`
    before `save_application()` inside `wasm_save_image_direct`
  - rebuilt kernel and re-ran boundary probe

Result:
- test did not restore package/bootstrap closure; candidate remained invalid.
- source gap confirmed: wasm path calls low-level `save_application()` directly,
  while Lisp `save-application` path wraps lifecycle prep/restore logic via
  `save-image` helpers.

Interpretation:
- likely blocker is broader save lifecycle semantics bypass, not just missing
  `%TOPLEVEL-FUNCTION%` seed.

### 2026-02-08 E26

Command:
- attempted scripted save path from `make-real-image.mjs`:
  - `wasm_run_script_with_output("scripts/wasm/make-real-image.lisp", --output …)`
  - retry without output argv payload

Result:
- output-arg path returns `-12`.
- no-output retry returns `-4`.

Interpretation:
- current runtime lane cannot yet rely on `wasm_run_script_with_output` as a
  production save path; direct scripted bridge remains blocked.

### 2026-02-08 E27

Command:
- instrumented `wasm_save_image_direct` to attempt
  `%SAVE-APPLICATION-INTERNAL` first, with explicit branch logging.
- rebuilt kernel and re-ran boundary probe.

Result:
- logs show:
  - `WASM save-image: trying %save-application-internal`
  - `WASM save-image: %save-application-internal symbol not found`
  - fallback to `save_application`.
- boundary failure unchanged.

Interpretation:
- semantic-save invocation is not currently reachable from this image lane.

### 2026-02-08 E28

Command:
- expanded bootstrap probe fields:
  - `allpkgs`, `allpkgs_car`, `allpkgs_cdr`, `allpkgs_names`
- boundary probe before save and after fresh reload.

Result:
- pre-save package list is structurally valid.
- reload pre-start keeps the same list-head pointer but zeroes its payload
  (`car/cdr`), and package-name lookup collapses to NIL.

Interpretation:
- saved artifact preserves some raw pointers but loses object contents/typing in
  the same region.

### 2026-02-08 E29

Command:
- instrumented `save_application_internal` area bounds logging in `image.c`.
- sequential run (rebuild then probe, no parallel overlap).

Result:
- save-time ranges in failing run:
  - `nil=[0x3fff000,0x4000428)`
  - `ro=[0x20000,0x408a0)`
  - `dyn=[0x40587e8,0x40587e8)` (empty)
  - `mstatic=[0x2020000,0x2020000)` (empty)
  - `scons=[0x4020000,0x4020000)` (empty)
- failing roots remain at:
  - `allpkgs=0x40201bd`
  - `toplfunc_raw=0x4036546`

Interpretation:
- failing roots lie outside the non-empty saved sections in this run, strongly
  implicating section-coverage/area-state defects.

### 2026-02-08 E30

Command:
- WASM-only change to disable static-cons low-bound trimming in
  `save_application_internal` (`#ifndef WASM32` gate around trimming block).
- rebuilt kernel and re-ran boundary probe.

Result:
- no improvement; boundary failure pattern unchanged.

Interpretation:
- failure is not fixed by trimming bypass alone; broader area-state issue
  remains.

### 2026-02-08 E31

Command:
- reran authoritative boundary probe sequentially:
  1) `/bin/zsh -lc 'source scripts/wasm/env.sh && make -C lisp-kernel/wasm32 CC="$CC" WASM_LD="$WASM_LD"'`
  2) `node doc/wasm/js/make-real-image.mjs ...`

Result:
- same deterministic failure and same save-time/restore-time diagnostics.

Interpretation:
- evidence is reproducible and not an artifact of stale parallel build/probe
  overlap.

### 2026-02-08 E32

Command:
- apply direct-save stability fix in `wasm_save_image_direct`:
  - detect/record `egc_was_enabled`
  - disable EGC before `save_application()`
  - restore EGC after save completes
- rebuild kernel with canonical command:
  `/bin/zsh -lc 'source scripts/wasm/env.sh && make -C lisp-kernel/wasm32 CC="$CC" WASM_LD="$WASM_LD"'`
- rerun boundary report image build.

Result:
- root candidate build succeeds.
- boundary report no longer shows save/reload bootstrap divergence for root lane.
- regenerated artifacts:
  - `doc/wasm/root.image`
  - `doc/wasm/root.image.manifest.json`

Interpretation:
- save-boundary section coverage/state-loss issue is no longer the active
  blocker for root lane.

### 2026-02-08 E33

Command:
- strict root loader validation:
  `node doc/wasm/js/load-image.mjs --mode start-lisp --manifest doc/wasm/root.image.manifest.json --stdin-text "(quit)\n" --close-stdin`

Result:
- strict manifest validation succeeds.
- `bootstrap_contract pre-start ok`
- `wasm_ccl_start_lisp rc=0`
- `bootstrap_contract post-start ok`

Interpretation:
- root-image strict start path is healthy after regeneration.

### 2026-02-08 E34

Command:
- full root persistence smoke:
  `node doc/wasm/js/wasm-ui-persist-smoke.mjs --verbose --image root`

Result:
- load/reset/install/start sequence succeeds.
- bootstrap contracts pass both pre-start and post-start.
- compiled UI modules install (`installed=8/8`).
- failure moves to first compiled UI preflight call:
  `FAIL: Lisp UI not runnable in persistence smoke: unreachable`.

Interpretation:
- blocker moved from bootstrap/save boundary to compiled UI runtime execution.

### 2026-02-08 E35

Command:
- minimal lane persistence smoke:
  `node doc/wasm/js/wasm-ui-persist-smoke.mjs --verbose --image minimal`

Result:
- fails strict pre-start contract (`COMMON-LISP` package NIL, `TOPLEVEL`
  missing) before compiled UI preflight.

Interpretation:
- minimal lane remains expected bootstrap-incomplete bring-up lane; root lane
  remains primary closure target.

### 2026-02-08 E36

Command:
- forward-reference const-pool repair in kernel loader:
  - allow forward indices during first-pass object creation
  - add second-pass patching for `vector`/`function-vector`/`gvector`/`cons`
- validate by rerunning loader on previously failing module path.

Result:
- prior const-pool install failure class (notably entry `3712`) is cleared.
- loader can continue into runtime call boundary where current failure is
  `unreachable`.

Interpretation:
- const-pool forward-reference handling is no longer the immediate blocker.

## Proposed Precise Next Steps

1. Isolate the exact failing compiled entry and callable target:
   - run root smoke with entry probes around `WASM-UI-LABEL-STATE`,
     `WASM-UI-MARK-PERSISTED`, `WASM-UI-MARK-DIRTY`, `WASM-UI-SAVE-STATE`.
   - capture which symbol/function cell is unresolved immediately before the
     `unreachable` trap.
2. Add deterministic trap localization in runtime call path:
   - instrument `wasm_funcall_common`/subprim dispatch for entry ID + callee raw
     object/subtag at failure boundary.
   - keep logs behind explicit trace flag.
3. Reconcile UI module compiler output with runtime expectations:
   - inspect generated lambda/spec forms for the failing entry.
   - verify emitted constant/function objects are non-recursive and callable in
     runtime lane.
4. Eliminate remaining fallback-driven ambiguity:
   - reduce/resolve core symbol fallback creation during UI module install
     (`OPEN`, `READ`, `PRIN1`, etc.) in root lane.
   - confirm those symbols resolve to callable fcells before preflight.
5. Preserve current hard gates while fixing runtime entry path:
   - keep `make-real-image.mjs` strict sanity gate enabled.
   - keep `load-image` and `wasm-ui-persist-smoke` bootstrap contract checks in
     strict mode for root lane.
6. Regression-gate closure sequence:
   - `node doc/wasm/js/load-image.mjs --mode start-lisp --manifest doc/wasm/root.image.manifest.json --stdin-text "(quit)\n" --close-stdin`
   - `node doc/wasm/js/wasm-ui-persist-smoke.mjs --verbose --image root`
   - `node doc/wasm/js/wasm-ui-persist-smoke.mjs --verbose --image minimal`
   - `node doc/wasm/js/all-smoke.mjs`
   - `npm --prefix web-ui test`

## Exit Conditions for Tracker Retirement

This temporary tracker is retired only when all are true:

1. `node doc/wasm/js/wasm-ui-persist-smoke.mjs` passes in default unattended
   mode.
2. Root cause and fix are documented in permanent status/report docs.
3. Regression tests for the identified failure mode are merged.
