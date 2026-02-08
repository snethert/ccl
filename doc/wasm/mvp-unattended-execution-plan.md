# WASM MVP Unattended Execution Plan

Status: Draft  
Owner: Codex execution workflow  
Last updated: 2026-02-08

## Purpose
Provide a strict, sequential, unattended plan to close the remaining WASM MVP gaps:
1. `compiler-smoke` FFI regression (`ffi-add` returns `0`, expected `42`)
2. Spill/restore discipline around subprim calls
3. Real root-image + real toplevel boot path
4. Compiled Lisp UI path parity (remove partial/demo dependency)

This plan assumes the current baseline where:
- `npm --prefix web-ui test` is green.
- `node doc/wasm/js/all-smoke.mjs` is red due to `compiler-smoke`.

## Global Execution Rules
1. Do not run steps out of order.
2. Do not proceed to the next step until the current step exit criteria pass.
3. After each step, record:
- command(s) run
- pass/fail
- artifacts touched
- blocker notes
4. If a step fails, stop and apply the step's rollback/fallback instructions.
5. Keep all edits on a dedicated branch for this plan execution.

## Environment Preconditions
1. Confirm repo root:
```bash
pwd
```
Exit criteria: working directory is repository root.

2. Confirm toolchain availability:
```bash
node --version
npm --version
clang --version || true
wasm-ld --version || true
```
Exit criteria: Node and npm available.

3. Capture baseline git/worktree:
```bash
git status --short
```
Exit criteria: status captured in execution log.

4. Capture baseline smoke state:
```bash
npm --prefix web-ui test
node doc/wasm/js/all-smoke.mjs
```
Exit criteria:
- `web-ui` tests pass.
- `all-smoke` fails with the known `compiler-smoke` FFI mismatch.

## Stage A: Fix `compiler-smoke` FFI Regression (Gate 1)

### A1. Reproduce and isolate
1. Run only compiler smoke:
```bash
node doc/wasm/js/compiler-smoke.mjs
```
Exit criteria: deterministic reproduction of `ffi-add` mismatch.

2. Locate `ffi-add` definition and call path:
```bash
rg -n "ffi-add|external-call|compiler-smoke" doc/wasm/js scripts/wasm compiler/WASM lisp-kernel
```
Exit criteria: file list of exact compile path and runtime call path.

### A2. Inspect generated module and ABI binding
3. Rebuild smoke module bundle:
```bash
scripts/wasm/compile-smoke-modules.sh --output doc/wasm/wasm-smoke-modules.json
```
Exit criteria: bundle regenerated successfully.

4. Inspect manifest entry for failing function:
```bash
rg -n "ffi|external|add" doc/wasm/wasm-smoke-modules.json
```
Exit criteria: failing module entry located.

5. Validate host import registration path:
```bash
rg -n "external-call|ccl\\.|ffi|import" compiler/WASM lisp-kernel doc/wasm/js/microkernel.mjs doc/wasm/js/ccl-loader.mjs
```
Exit criteria: clear map from compiler lowering -> wasm import -> host implementation.

### A3. Implement fix
6. Patch compiler lowering and/or host shim so `ffi-add` returns correct boxed/unboxed value.
Files likely involved:
- `compiler/WASM/wasm2.lisp`
- `compiler/WASM/wasm-ffi.lisp`
- `lisp-kernel/wasm-host.c`
- `doc/wasm/js/microkernel.mjs`

Exit criteria: code compiles with no new syntax/runtime errors.

7. Add/extend focused regression tests:
- Existing:
  - `doc/wasm/js/compiler-smoke.mjs`
  - `scripts/wasm/compile-smoke-modules.lisp`
- Add assertion coverage for:
  - argument marshalling
  - return-value boxing
  - non-happy-path type handling

Exit criteria: test coverage explicitly checks the prior failure mode.

### A4. Validate Gate 1
8. Run targeted checks:
```bash
node doc/wasm/js/compiler-smoke.mjs
node doc/wasm/js/runtime-command-smoke.mjs
```
Exit criteria: both pass.

9. Run full smoke suite:
```bash
node doc/wasm/js/all-smoke.mjs
```
Exit criteria: passes fully.

10. If step 9 fails for reasons unrelated to FFI:
- log failure
- classify as new blocker
- continue only if failure is outside Stage A scope and non-blocking for Stage B.

## Stage B: Spill/Restore Discipline Around Subprim Calls (Gate 2)

### B1. Inventory and rules
11. Enumerate all WASM subprim call emission sites:
```bash
rg -n "subprim|call_subprim|wasm_call_subprim|SP" compiler/WASM
```
Exit criteria: call-site inventory captured.

12. Define mandatory spill/restore invariants in one doc section:
- live GC roots preserved across every subprim call
- arg registers restored deterministically
- VSP/TSP discipline consistent before/after call

Target doc:
- `doc/wasm/ABI.md`

Exit criteria: invariants documented with unambiguous MUST rules.

### B2. Implement and enforce
13. Patch emission paths to enforce invariant at each call site.
Exit criteria: all inventoried call sites updated or explicitly exempted.

14. Add static/assertion checks in codegen where possible.
Exit criteria: build/test fails if a call path skips required spill/restore sequence.

15. Add runtime smoke coverage for closure/allocation and unwind-heavy paths:
- extend `doc/wasm/js/closure-unwind-mv-smoke.mjs`
- extend/add compiled module smoke fixture

Exit criteria: targeted tests include allocation + multi-value + unwind interactions.

### B3. Validate Gate 2
16. Run targeted tests:
```bash
node doc/wasm/js/closure-unwind-mv-smoke.mjs
node doc/wasm/js/mvcall-smoke.mjs
node doc/wasm/js/compiler-smoke.mjs
```
Exit criteria: all pass.

17. Run full smoke:
```bash
node doc/wasm/js/all-smoke.mjs
```
Exit criteria: pass.

## Stage C: Real Root Image + Real Toplevel Boot (Gate 3)

### C1. Policy and artifact contract
18. Finalize root-image policy and cache semantics in:
- `doc/wasm/image-loader-spec.md`
- `doc/wasm/roadmap.md`

Must define:
- root image source of truth
- clone semantics
- invalidation/refresh policy

Exit criteria: policy section complete and non-contradictory.

19. Rebuild runtime module bundle and root image artifacts:
```bash
scripts/wasm/compile-wasm-fasls.sh --modules-out doc/wasm/wasm-runtime-modules.json
```
and image build path currently used by repo.

Exit criteria: runtime modules + image artifacts produced without manual intervention.

### C2. Loader and entrypoint wiring
20. Wire loader to use real root image (not stub/minimal fallback in normal path).
Likely files:
- `doc/wasm/js/ccl-loader.mjs`
- `doc/wasm/js/load-image.mjs`
- Lisp/kernel entrypoint glue

Exit criteria: default boot path enters real toplevel-capable image.

21. Add explicit smoke that validates post-load real toplevel behavior:
- load image
- enter `wasm_ccl_start_lisp`
- evaluate a minimal form roundtrip

Exit criteria: smoke is deterministic and added to `all-smoke`.

### C3. Validate Gate 3
22. Run:
```bash
node doc/wasm/js/start-lisp-smoke.mjs
node doc/wasm/js/load-image.mjs --start-lisp --modules doc/wasm/wasm-runtime-modules.json doc/wasm/root.image
node doc/wasm/js/all-smoke.mjs
```
Exit criteria: all pass.

## Stage D: Compiled Lisp UI Path Parity (Gate 4)

### D1. Remove partial/demo dependency
23. Identify and remove default kernel-demo fallback for normal UI turn path.
Likely files:
- `web-ui/tests/browser/harness.mjs`
- `doc/wasm/js/web-ui-*.mjs`
- loader/runtime glue

Exit criteria: compiled Lisp UI path is primary in smoke/harness execution.

24. Make wasm UI persistence smoke non-skip for normal build:
- `doc/wasm/js/wasm-ui-persist-smoke.mjs`

Exit criteria: no skip due to missing runnable Lisp UI module set in standard configuration.

### D2. Expand parity assertions
25. Add parity assertions between JS reference model and compiled Lisp path for:
- typed command dispatch roundtrip
- debugger restart invoke
- inspector place edit lifecycle
- persistence restore determinism

Target tests:
- `web-ui/tests/phase-5-runtime-integration.test.mjs`
- `doc/wasm/js/web-ui-command-ui-smoke.mjs`
- `doc/wasm/js/wasm-ui-persist-smoke.mjs`

Exit criteria: parity checks fail on behavior divergence.

### D3. Validate Gate 4
26. Run:
```bash
npm --prefix web-ui test
node doc/wasm/js/web-ui-command-ui-smoke.mjs
node doc/wasm/js/wasm-ui-persist-smoke.mjs
node doc/wasm/js/all-smoke.mjs
```
Exit criteria: all pass.

## Stage E: Documentation and Status Reconciliation (Gate 5)

27. Update status docs to reflect real state:
- `doc/wasm/roadmap.md`
- `doc/wasm/porting-status.md`
- `doc/wasm/project-overview.md`
- `doc/testing.md`
- `doc/wasm/testing.md`
- `web-ui/FRONT-END-DEV-PLAN.md`

Exit criteria: no contradictions between:
- test reality
- roadmap
- phase plans
- bridge status

28. Run contradiction scan:
```bash
rg -n "pending|partial|blocked|pass|fails|not yet implemented|Complete" doc web-ui web-ide
```
Exit criteria: flagged lines reviewed; stale claims removed.

## Final Signoff Sequence
29. Full validation run (strict order):
```bash
npm --prefix web-ui test
node doc/wasm/js/all-smoke.mjs
```
Exit criteria: both pass.

30. Capture final artifact/report bundle:
- git diff summary
- commands executed
- final pass/fail matrix
- remaining deferred items (if any)

31. Update `doc/wasm/roadmap.md` near-term focus to next true work after MVP blockers are clear.
Exit criteria: roadmap no longer lists resolved blockers.

## Failure Handling Protocol
If any gate fails:
1. Stop progression immediately.
2. Record failing command and exact stderr.
3. Classify as:
- code regression
- environment/toolchain issue
- stale/invalid test expectation
4. Create/append blocker note in `doc/wasm/roadmap.md` and `doc/wasm/porting-status.md`.
5. Resume only after blocker resolution commit.

## Definition of Done (MVP Runtime Track)
All conditions must be true:
1. `npm --prefix web-ui test` passes.
2. `node doc/wasm/js/all-smoke.mjs` passes.
3. `compiler-smoke` FFI regression fixed with regression coverage.
4. Spill/restore discipline documented and enforced by tests/assertions.
5. Real root-image + real toplevel boot path validated by smoke.
6. Compiled Lisp UI path (including persistence smoke) runs without demo-only dependency.
7. Status docs are internally consistent and reflect actual test results.
