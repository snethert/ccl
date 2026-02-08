# WASM MVP Unattended Execution Plan

Status: In Progress (RZ0.6 pivot)  
Owner: Codex execution workflow  
Last updated: 2026-02-08

## Purpose

Provide a strict, sequential unattended plan to close the remaining MVP gaps
after the runtime-bundle/manifest/start-lisp work:

1. Persistence backend decoupling from host-only privileges.
2. Runtime bootstrap closure for compiled-Lisp persistence entries.
3. Documentation and status reconciliation against current reality.

This plan is aligned with `web-ide/phase-8/implementation-plan.md` (RZ0.6).
Active blocker reasoning and experiment log lives in:
`doc/wasm/wasm-ui-persistence-problem-tracker.md`.

## Current baseline assumptions

- `npm --prefix web-ui test` is green.
- `node doc/wasm/js/all-smoke.mjs` is green.
- Strict non-interactive root-image start-lisp gate is green:
  - `node doc/wasm/js/start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive`
- Persistence backend decoupling is landed; compiled-Lisp runtime bootstrap path
  remains unstable and is the active blocker.

## Global execution rules

1. Execute stages in order; do not skip gates.
2. Do not proceed when current stage exit criteria fail.
3. After each stage, record:
   - commands run
   - pass/fail
   - files touched
   - blocker notes
4. If a gate fails, stop and fix before continuing.

## Stage A: Lock Boot Gate (No Regression)

### A1. Baseline capture
1. `git status --short`
2. `npm --prefix web-ui test`
3. `node doc/wasm/js/all-smoke.mjs`
4. `node doc/wasm/js/start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive`

Exit criteria:
- All four commands succeed.
- Any failure is treated as regression and fixed before Stage B.

## Stage B: Persistence Backend Decoupling (Memory-Snapshot Default)

### B1. Contract and flags
1. Define canonical backend selector:
   - CLI: `--persist-backend memory-snapshot|lmdb|idb`
   - ENV: `CCL_PERSIST_BACKEND`
2. Define canonical snapshot path selector:
   - CLI: `--persist-snapshot-file <path>`
   - ENV: `CCL_PERSIST_SNAPSHOT_FILE`
3. Default unattended backend: `memory-snapshot`.

Exit criteria:
- Selector contract is documented and wired in smoke/harness entrypoints.

### B2. Implement memory-snapshot store
1. Add `memory-snapshot` persistence store in `doc/wasm/js/persist-service.mjs`:
   - Load snapshot file once at startup into in-memory KV/chunk/metadata maps.
   - Execute all FS operations in-memory.
2. Track dirty state:
   - Set `dirty=true` only for mutating logical changes.
3. Flush policy:
   - On clean process exit, if dirty, write full snapshot to temp file then
     atomic rename over target file.
   - If not dirty, do not write.
4. Failure policy:
   - Corrupt snapshot file fails with explicit error (plus reset option/flag).

Exit criteria:
- Runtime operations no longer require live LMDB/IDB access in default lane.
- Snapshot write path is atomic and deterministic.

### B3. Wire into microkernel + harness + smokes
1. Microkernel host path selects backend via canonical flags/env.
2. `doc/wasm/js/wasm-ui-persist-smoke.mjs` defaults to `memory-snapshot`.
3. `web-ui/tests/browser/harness.mjs` defaults to `memory-snapshot` for unattended mode.
4. LMDB/IDB remain explicit integration-only modes.

Exit criteria:
- Default unattended persistence flow does not require host privilege toggling.

### B4. Tests for memory-snapshot semantics
1. Add/extend tests covering:
   - load existing snapshot
   - dirty write on exit
   - no-op when clean
   - recovery from interrupted write (previous snapshot preserved)
2. Keep LMDB tests behind `CCL_ENABLE_LMDB_TESTS=1`.
3. Keep IndexedDB smoke as optional host/browser integration lane.

Exit criteria:
- Memory-snapshot backend has deterministic coverage and passes in sandbox lane.

## Stage C: Integration Lanes (Host-Only, Non-Blocking for Default Dev)

1. LMDB lane:
   - `make -f scripts/wasm/persist-host.mk persist-host-lmdb`
2. IndexedDB/browser lane:
   - `make -f scripts/wasm/persist-host.mk persist-idb-up`
   - open URL from `persist-idb-url`
   - `make -f scripts/wasm/persist-host.mk persist-idb-down`

Exit criteria:
- Integration lanes are documented and isolated from default unattended flow.

## Stage D: Runtime Bootstrap Closure (Current Top Blocker)

### D1. Reproduce and pin failure envelope
1. Probe compiled entry execution:
   - `node doc/wasm/js/wasm-ui-persist-smoke.mjs --image minimal --probe-entry WASM-UI-MARK-PERSISTED --verbose`
2. Record whether failure is:
   - const-pool install failure, or
   - entry call hang after install.
3. Log findings in:
   - `doc/wasm/wasm-ui-persistence-problem-tracker.md`

Exit criteria:
- Reproduction mode and exact stage of failure are deterministic.

### D2. Close const-pool/runtime defects in loader path
1. Keep kernel const-pool materialization compatible with emitted compiler
   payload shapes (including forward reference forms).
2. Validate on direct probes that symbol/cons payload installs are no longer the
   blocking class.
3. Rebuild wasm kernel artifacts and re-run persistence probe gate.

Exit criteria:
- No deterministic const-pool rejection remains for emitted UI module payloads.

### D3. Close image bootstrap/function-binding gap
1. Verify boot/minimal/root image sequencing invariants (load/reset/install/start).
2. Ensure required function bindings for compiled persistence entries are present
   before probe execution.
3. Validate `WASM-UI-*` probes and full persistence smoke under default
   `memory-snapshot`.

Exit criteria:
- `node doc/wasm/js/wasm-ui-persist-smoke.mjs` passes without hang.

## Stage E: Documentation Reconciliation

Update docs to match the memory-first decision and current gate state:

- `doc/wasm/roadmap.md`
- `doc/wasm/porting-status.md`
- `doc/wasm/project-overview.md`
- `doc/wasm/persistence-service-spec.md`
- `doc/wasm/persistence-dev-environment.md`
- `doc/testing.md`
- `doc/wasm/testing.md`
- `web-ui/FRONT-END-DEV-PLAN.md`

Run contradiction scan:

```bash
rg -n "entry 320|const-pool|strict.*timeout|host-only.*default|IndexedDB.*default|LMDB.*required|skip.*persistence" doc web-ui web-ide
```

Exit criteria:
- No status/plan doc contradicts current decisions.

## Final signoff sequence

```bash
npm --prefix web-ui test
node doc/wasm/js/start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive
CCL_PERSIST_BACKEND=memory-snapshot CCL_PERSIST_SNAPSHOT_FILE=.tmp/persist-smoke.snapshot.json node doc/wasm/js/wasm-ui-persist-smoke.mjs
node doc/wasm/js/all-smoke.mjs
make -f scripts/wasm/persist-host.mk persist-host-lmdb
```

Exit criteria:
- Default lane green without host privilege coupling.
- Host integration lane remains explicit and green.

## Definition of done (MVP runtime track)

All must be true:
1. Strict non-interactive root-image start-lisp gate passes.
2. Compiled-Lisp UI persistence path passes with `memory-snapshot` default backend.
3. Default unattended development/test path does not require host-only persistence privileges.
4. LMDB/IDB lanes remain available as integration checks.
5. Status docs and phase plans are internally consistent.
