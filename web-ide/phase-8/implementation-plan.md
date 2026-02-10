# Phase 8 Detailed Plan: Release Packaging and Operational Readiness

## Document Control
- Status: Planned
- Last Updated: February 9, 2026
- Parent Plan: `web-ide/implementation-plan.md`
- Doctrine Sources:
  - `web-ide/ide-doctrine.md`
  - `web-ui/ui-doctrine.md`
  - `web-ide/phase-0/`
  - `web-ide/phase-1/implementation-plan.md`
  - `web-ide/phase-2/implementation-plan.md`
  - `web-ide/phase-3/implementation-plan.md`
  - `web-ide/phase-4/implementation-plan.md`
  - `web-ide/phase-5/implementation-plan.md`
  - `web-ide/phase-6/implementation-plan.md`
  - `web-ide/phase-7/implementation-plan.md`

## Phase 8 Outcome
Transition the system from engineering-complete to release-ready by defining deterministic artifacts, deployment and rollback mechanics, operational runbooks, and objective go/no-go gates.

## Scope
### In Scope
- Release artifact contract and versioning policy.
- Deterministic build and packaging workflow with reproducible outputs.
- Runtime and browser compatibility matrix with explicit support policy.
- Security and capability hardening for default deployments.
- Observability baseline for client/runtime diagnostics.
- Data durability and rollback operations for sessions/snapshots.
- Release process documentation and operator runbooks.
- Staged rollout process with objective release gates.

### Out of Scope
- New major product capabilities outside doctrine commitments.
- Multi-user collaboration/cloud sync systems.
- Runtime architecture rewrite implementation itself (owned by runtime-track plans),
  while release gating in this phase still depends on runtime replacement
  milestone closure artifacts.
- Long-term analytics platform beyond immediate operational telemetry.

## Baseline
- Phases 0 through 7 are complete.
- Phase 7 quality gates and acceptance coverage are in place.
- `web-ui` test suites are currently green.
- Runtime bridge, typed command dispatch, debugger, inspector, sessions, and customization are operational.

## Runtime Replacement Dependencies (Normative)

Phase 8 release packaging/execution must consume (not redefine) runtime-track
replacement milestones:

- Secure runtime gating posture from `doc/wasm/tickets/RPL-01-secure-runtime-gating.md`.
- Runtime/UI shared-path closure from `doc/wasm/tickets/RPL-04-runtime-ui-bridge-shared-path.md`.
- Storage V2 local-core closure from `doc/wasm/tickets/RPL-05-storage-v2-local-core.md`.
- Runtime/backend cutover closure artifacts from `doc/wasm/tickets/RPL-09-cutover-and-legacy-removal.md` and `doc/wasm/backend-tickets/BPL-09-cutover-and-arm-retirement.md`.

This phase must not treat legacy memory-snapshot defaults as the replacement
target architecture for release-signoff decisions.

## Progress Snapshot
- M0 `RZ0`: In Progress (runtime bundle + manifest + loader refactor + legacy-lane memory-snapshot persistence decoupling + bootstrap contract enforcement landed; root-lane compiled-Lisp UI preflight trap is closed; UI save/restore persistence semantics are now wired to legacy memory-snapshot contract; remaining work is core dispatch hardening + tracker retirement cleanup while replacement-track dependencies remain authoritative for release architecture posture).
- M1 `RZ1`: Planned.
- M2 `RZ2`: Planned.
- M3 `RZ3`: Planned.
- M4 `RZ4`: Planned.
- M5 `RZ5`: Planned.
- M6 `RZ6`: Planned.
- M7 `RZ7`: Planned.
- M8 `RZ8`: Planned.

## Phase 8 Success Criteria
- Release artifacts are deterministic, signed/checksummed, and reproducible.
- Support matrix and compatibility policy are explicit and test-backed.
- Default deployment posture is safe and capability constrained.
- Operators can diagnose, recover, and roll back without ad hoc procedures.
- Rollout gates are objective and integrated into standard release flow.

## Pre-Phase Gate: RZ0 (MVP Blocker Closure)
### Goal
Finish the remaining MVP blocker closure work before Phase 8 release packaging:
stabilize persistence semantics after root-lane compiled-Lisp UI runtime
closure under strict manifest/bootstrap loader validation.

RZ0 is a legacy-lane stabilization gate. It does not supersede runtime
replacement-track architecture requirements.

### Why This Is A Prerequisite
- `doc/wasm/roadmap.md` and `doc/wasm/porting-status.md` still mark this as open.
- Packaging and release-gate hardening (RZ1-RZ8) is lower value until runtime boot policy is deterministic.

### Code-Grounded Findings (Current)
1. `doc/wasm/js/load-image.mjs` now supports explicit mode control and deterministic non-interactive inputs (`--mode`, `--stdin-text`, `--close-stdin`, `--expect-rc`) and enforces bootstrap sanity by default (`--bootstrap-contract strict`).
2. `doc/wasm/js/load-image.mjs` defaults module installs to strict mode in `start-lisp` flows, with explicit opt-out (`--allow-partial-modules`) only for bring-up scenarios.
3. Runtime modules are emitted/consumed via `ccl-wasm-modules-v2` manifest + `.bin` + `.idx`, and loader resolution uses indexed bundle plumbing.
4. `doc/wasm/js/make-real-image.mjs` emits manifest output and now hard-fails bootstrap-invalid root-image candidates before manifest publication.
5. Memory-first persistence (`memory-snapshot`) is now the default unattended lane to avoid host-permission coupling.
6. `doc/wasm/image-loader-spec.md` still requires final cleanup to remove/close residual open questions and align with implemented defaults.

### Code-Grounded Findings (Third Pass, Runtime Bootstrap)
1. Kernel const-pool install now handles forward references in `cons`, `vector`,
   `function-vector`, and `gvector` via first-pass creation + second-pass patching.
2. Root save/reload closure has been restored for regenerated artifacts; strict
   manifest and pre-start/post-start bootstrap checks now pass for `root.image`.
3. `wasm-ui-persist-smoke` root lane now passes full compiled UI preflight and
   transition sequence after UI module simplification away from fragile
   core-symbol call dependencies.
4. `minimal.image` remains strict pre-start contract-incomplete and is retained
   as a bring-up lane.
5. UI save/restore is now wired to persistence-service semantics via
   file-backed runtime ops (`/ui/wasm-ui-state.bin`) plus dirty-flush
   regression checks in `wasm-ui-persist-smoke`.
6. Top blocker is now permanent core dispatch hardening, not root-lane
   preflight execution or persistence semantics.

### RZ0 Deliverables
- Deterministic runtime bundle contract (`ccl-wasm-modules-v2` + `.bin` + `.idx`) for runtime modules.
- Root-image manifest contract + generator output tied to image/module hashes.
- Loader mode contract with explicit non-interactive `start_lisp` validation path.
- Memory-first persistence backend contract: bootstrap from file, run all ops against in-memory IFB-like KV, flush snapshot file on clean exit only when dirty.
- Default unattended path does not require host-only persistence backends.
- Smoke coverage that fails fast on hang, partial module install, or manifest mismatch.
- Updated docs (`build.md`, `image-loader-spec.md`, `roadmap.md`, `porting-status.md`) with no contradictions.
- Temporary blocker reasoning log maintained in
  `doc/wasm/wasm-ui-persistence-problem-tracker.md` until closure.

### RZ0 Sequential Execution Plan (Unattended)
#### RZ0.1 Baseline and Failure Envelope
1. Capture baseline state:
   - `git status --short`
   - `npm --prefix web-ui test`
   - `node doc/wasm/js/all-smoke.mjs`
2. Capture blocker-specific baseline:
   - `node doc/wasm/js/wasm-ui-persist-smoke.mjs`
   - `node doc/wasm/js/load-image.mjs --start-lisp --modules doc/wasm/wasm-runtime-modules.json doc/wasm/root.image` (record current behavior)
3. Exit criteria:
   - Baseline logs recorded in execution notes.
   - Known blocker behavior reproduced without introducing new unrelated failures.

#### RZ0.2 Runtime Bundle Contract Unification (v2 Required)
1. Update runtime modules build pipeline so `scripts/wasm/compile-wasm-fasls.sh --modules-out ...` always emits:
   - manifest with `format: ccl-wasm-modules-v2`
   - sidecar binary (`.bin`)
   - index (`.idx`)
2. Preferred low-risk implementation:
   - keep `scripts/wasm/compile-wasm-fasls.lisp` as inline/offset emitter
   - add post-pack step in `scripts/wasm/compile-wasm-fasls.sh` using `scripts/wasm/pack-inline-bundle-v2.mjs` (same pattern already used by smoke/UI scripts)
3. Add validation smoke:
   - new `doc/wasm/js/runtime-modules-manifest-smoke.mjs`
   - assert `format`, `binary`, `index`, and successful `resolveBundleEntries(...)`.
4. Wire smoke into `doc/wasm/js/all-smoke.mjs`.
5. Exit criteria:
   - `doc/wasm/wasm-runtime-modules.json` resolves as v2 in loader path.
   - No runtime module install path depends on legacy-only format.

#### RZ0.3 Root-Image Manifest Policy and Build Output
1. Define root-image manifest schema (new doc artifact):
   - `doc/wasm/root-image-manifest.schema.json`
   - include hashes for: `root.image`, runtime bundle manifest, runtime binary, runtime index, `wasmcl.wasm`, `subprims.wasm`
   - include policy fields: build tool versions, entrypoint index, expected loader mode, generated-at UTC
2. Extend image builder:
   - `doc/wasm/js/make-real-image.mjs` adds `--manifest-out` (default near output image)
   - emit SHA-256 hashes and canonical JSON order
3. Keep host script parity:
   - `scripts/wasm/make-real-image.lisp` forwards manifest options when delegating to Node helper.
4. Add smoke:
   - new `doc/wasm/js/root-image-manifest-smoke.mjs`
   - verifies produced image bytes match manifest hash.
5. Exit criteria:
   - every generated `root.image` has a manifest artifact and reproducible hash contract.

#### RZ0.4 Loader Contract Refactor (Non-Interactive `start_lisp`)
1. Refactor `doc/wasm/js/load-image.mjs` mode handling:
   - introduce explicit `--mode boot-only|start-lisp|run-toplevel`
   - retain `--run` / `--start-lisp` as compatibility aliases
2. Introduce policy inputs:
   - `--manifest PATH` to validate image/modules/kernel hashes before boot
   - `--strict-modules` default `true` in `start-lisp` mode
   - `--allow-partial-modules` explicit opt-out for bring-up only
3. Add non-interactive controls:
   - `--stdin-script PATH` and/or `--stdin-text STRING`
   - `--close-stdin` default on in non-interactive mode
   - `--expect-rc N` to make return code contract explicit
4. Ensure install path consistency:
   - use `installCompiledModulesFromBundle(... strict: true ...)` for default path
   - fail hard on `failed > 0` unless explicit non-strict mode selected
5. Exit criteria:
   - default documented root-image validation path can complete unattended and returns deterministic success/failure.

#### RZ0.5 Hang-Proof Start-Lisp Validation Harness
1. Add process-level timeout smoke:
   - new `doc/wasm/js/start-lisp-noninteractive-smoke.mjs`
   - spawn `node doc/wasm/js/load-image.mjs --mode start-lisp ...` with timeout; fail on hang
2. Validate success path:
   - manifest valid + modules valid + scriptable stdin -> pass
3. Validate failure path:
   - tampered hash or missing module entry -> expected fail with actionable error
4. Add to `doc/wasm/js/all-smoke.mjs`.
5. Exit criteria:
   - unattended CI cannot deadlock silently in root-image `start_lisp` validation.

#### RZ0.6 Persistence Backend Decoupling (Memory-First IFB-Style KV)
1. Define backend contract and runtime selector:
   - Add explicit backend mode: `memory-snapshot` (default), `lmdb`, `idb`.
   - Add canonical selector input for harness/smokes (`--persist-backend` and `CCL_PERSIST_BACKEND`).
   - Define snapshot path input (`--persist-snapshot-file` and `CCL_PERSIST_SNAPSHOT_FILE`).
2. Implement `memory-snapshot` store in persistence service:
   - load snapshot file once at startup into an in-memory KV map (IFB-like key/value model).
   - execute `probe`, `directory`, `open/read/write/seek/truncate`, rename/delete entirely against in-memory state.
   - preserve existing chunk/metadata semantics so higher layers are backend-agnostic.
3. Add dirty-tracking and deterministic flush:
   - set `dirty=true` on any mutating operation that changes logical state.
   - on process exit (`beforeExit`/`exit`/signal handlers where supported), if `dirty`, write full snapshot to temp path and atomically rename.
   - if `dirty=false`, skip write and preserve existing snapshot file timestamp/content.
4. Crash and recovery policy:
   - crash/kill before flush keeps prior snapshot (no partial writes).
   - startup reads latest valid snapshot; malformed snapshot triggers explicit error + optional reset flag.
5. Harness/smoke default migration:
   - `doc/wasm/js/wasm-ui-persist-smoke.mjs` defaults to `memory-snapshot`.
   - `web-ui/tests/browser/harness.mjs` defaults to `memory-snapshot` in unattended mode.
   - LMDB/IDB remain explicit integration modes only.
6. Test additions:
   - load existing snapshot -> state visible before first mutation.
   - mutate -> dirty set -> flush on exit persists state.
   - no mutation -> no flush/write.
   - atomic-write guard: interrupted write does not corrupt previous snapshot.
7. Exit criteria:
   - compiled-Lisp UI persistence path runs unattended in sandbox-oriented flow without host-only permission requirements.
   - LMDB/IDB paths are validated separately as integration lanes.

#### RZ0.7 Documentation Reconciliation
1. Update normative docs:
   - `doc/wasm/image-loader-spec.md`
   - `doc/wasm/build.md`
   - `doc/wasm/roadmap.md`
   - `doc/wasm/porting-status.md`
2. Remove stale statements:
   - unresolved “open question” items that are now implemented
   - legacy loader instructions that conflict with new mode/manifest contract
3. Run contradiction sweep:
   - `rg -n "open question|pending|partial|default|strict|start_lisp|root image" doc/wasm web-ui web-ide`
4. Exit criteria:
   - no doc says blocker is open after implementation and validation passes.

#### RZ0.8 Final Gate and Handoff
1. Required command sequence:
   - `scripts/wasm/compile-wasm-fasls.sh --modules-out doc/wasm/wasm-runtime-modules.json`
   - `scripts/wasm/build-wasm-boot.sh`
   - `node doc/wasm/js/make-real-image.mjs --modules doc/wasm/wasm-runtime-modules.json --output doc/wasm/root.image`
   - `node doc/wasm/js/start-lisp-noninteractive-smoke.mjs`
   - `CCL_PERSIST_BACKEND=memory-snapshot CCL_PERSIST_SNAPSHOT_FILE=.tmp/persist-smoke.snapshot.json node doc/wasm/js/wasm-ui-persist-smoke.mjs`
   - `node doc/wasm/js/all-smoke.mjs`
   - `npm --prefix web-ui test`
   - `make -f scripts/wasm/persist-host.mk persist-host-lmdb` (integration lane)
2. Produce final artifacts:
   - updated runtime bundle triplet (`.json`, `.bin`, `.idx`)
   - `root.image` + manifest
   - persistence snapshot contract doc + fixture snapshot
   - final blocker closure report in `doc/wasm/mvp-unattended-execution-report.md`
3. Exit criteria:
   - blocker removed from roadmap near-term list
   - Phase 8 can proceed to RZ1 without runtime boot ambiguity or host-permission persistence coupling.

## Workstreams

## RZ1: Artifact Contract and Version Policy
### Goal
Define exactly what gets shipped and how versions evolve.

### Tasks
1. Define release artifact set:
   - web UI bundle(s)
   - runtime bridge schemas
   - runtime module manifests
   - docs/runbooks bundle
2. Define semantic version policy and compatibility promises:
   - bridge protocol compatibility
   - snapshot/schema migration compatibility
   - keymap/theme profile compatibility
3. Define release manifest schema including:
   - artifact names
   - checksums
   - schema versions
   - supported browsers/runtime constraints
4. Define deprecation policy for schema and protocol changes.

### Deliverables
- `web-ide/phase-8/release-artifact-contract.md`
- `web-ide/phase-8/versioning-and-compatibility-policy.md`
- Release manifest schema in docs (and test fixtures).

### Exit Criteria
- Artifact contract is unambiguous and complete.
- Version policy is internally consistent with phases 0-7 schemas.

## RZ2: Deterministic Build and Packaging
### Goal
Make release generation repeatable and auditable.

### Tasks
1. Create canonical release build command flow for UI/runtime artifacts.
2. Add checksum generation and validation steps.
3. Add manifest generation from build outputs.
4. Add strict validation for missing/extra artifacts.
5. Add smoke validation against packaged assets before publish.

### Deliverables
- Build/release scripts in `scripts/` and/or `web-ui` packaging workflows.
- Manifest generation + verification tooling.
- CI job definition for release packaging checks.

### Exit Criteria
- Same commit produces identical artifact hashes (within declared tolerances).
- Packaging gate fails fast on incomplete or inconsistent outputs.

## RZ3: Compatibility Matrix and Environment Validation
### Goal
Lock supported environments with explicit test evidence.

### Tasks
1. Define supported browser/runtime matrix and policy:
   - minimum versions
   - unsupported/degraded modes
2. Add compatibility smoke tests for critical workflows:
   - REPL transcript interaction
   - command palette and keyboard flows
   - debugger and inspector baseline loop
3. Add explicit checks for DOM+canvas/WebGL fallback behavior.
4. Document expected behavior under reduced capability (no WebGL, limited storage, etc.).

### Deliverables
- `web-ide/phase-8/compatibility-matrix.md`
- Compatibility acceptance tests in `web-ui/tests/phase-8-*.test.mjs`.
- CI profile for compatibility checks.

### Exit Criteria
- Supported matrix is documented and test-covered.
- Degraded behavior is explicit and non-fatal.

## RZ4: Security and Capability Hardening
### Goal
Ship with conservative defaults and predictable permission boundaries.

### Tasks
1. Audit capability mediation defaults for production posture.
2. Define release defaults for safe mode and privileged operations.
3. Add tests for denied capability paths and safe failure behavior.
4. Validate import/export and runtime payload handling against malformed inputs.
5. Add release checklist items for security-sensitive toggles.
6. Enforce memory-first persistence default and keep host backends (`lmdb`, `idb`)
   opt-in only in integration lanes (`doc/wasm/persistence-dev-environment.md`).

### Deliverables
- Security hardening policy doc in `web-ide/phase-8/security-hardening.md`.
- Hardened defaults in runtime/UI config paths.
- Security regression tests.

### Exit Criteria
- No privileged path bypasses in baseline workflows.
- Security-related failures are explicit and recoverable.

## RZ5: Observability and Diagnostics
### Goal
Provide enough diagnostics to operate and troubleshoot production issues.

### Tasks
1. Define operational event taxonomy for release builds.
2. Standardize diagnostic payload fields:
   - build/version identifiers
   - session/workspace context
   - command/runtime correlation ids
3. Add redaction/sanitization rules for logs and diagnostics.
4. Add test coverage for diagnostic event shape and determinism.
5. Define support bundle format for issue triage.

### Deliverables
- `web-ide/phase-8/observability-contract.md`
- Diagnostic schema fixtures and tests.
- Support bundle extraction and validation workflow.

### Exit Criteria
- Operators can correlate user-visible failures to actionable diagnostics.
- Diagnostics avoid sensitive data leakage by default.

## RZ6: Data Durability, Backup, and Rollback
### Goal
Ensure recoverability across bad deployments and schema transitions.

### Tasks
1. Define backup/export contract for sessions, snapshots, and customization.
2. Add migration rollback strategy for incompatible snapshot/profile imports.
3. Add recovery workflow tests:
   - restore from previous snapshot
   - resume after partial import failure
   - revalidate stale references post-rollback
4. Add release-time backup verification step.

### Deliverables
- `web-ide/phase-8/data-recovery-runbook.md`
- Recovery and rollback acceptance tests.
- Operational backup/restore checklist.

### Exit Criteria
- Recovery procedures are reproducible and tested.
- Rollback does not corrupt persisted user state.

## RZ7: Operator Runbooks and Support Workflow
### Goal
Document execution paths for launch, incident response, and recovery.

### Tasks
1. Write runbooks for:
   - release promotion
   - rollback
   - incident triage
   - data recovery
2. Define on-call/support escalation decision tree.
3. Define severity model and response SLO targets.
4. Add verification drills for top incident classes.

### Deliverables
- `web-ide/phase-8/release-runbook.md`
- `web-ide/phase-8/incident-response-runbook.md`
- `web-ide/phase-8/support-escalation-policy.md`

### Exit Criteria
- A new operator can execute release and rollback by runbook.
- Triage steps are deterministic and role-assigned.

## RZ8: Release Gates and Staged Rollout
### Goal
Create an objective promotion model from candidate to stable.

### Tasks
1. Define release channels:
   - canary
   - release candidate
   - stable
2. Define gate criteria per channel:
   - test pass profiles
   - quality budgets
   - incident thresholds
   - rollback triggers
3. Define rollout telemetry checkpoints and hold points.
4. Add final signoff checklist and ownership mapping.
5. Add post-release review template for continuous hardening.

### Deliverables
- `web-ide/phase-8/release-gates.md`
- Staged rollout checklist.
- Post-release review template.

### Exit Criteria
- Promotion gates are executable and objective.
- Rollback criteria are explicit and pre-approved.

## Milestone Sequence
1. M0: RZ0 complete (WASM blocker closure prerequisite).
2. M1: RZ1 complete (artifact contract and versioning policy).
3. M2: RZ2 complete (deterministic packaging pipeline).
4. M3: RZ3 complete (compatibility matrix and validation).
5. M4: RZ4 complete (security and capability hardening).
6. M5: RZ5 complete (observability and diagnostics contract).
7. M6: RZ6 complete (durability, backup, rollback coverage).
8. M7: RZ7 complete (operator runbooks and support workflow).
9. M8: RZ8 complete (release gates and staged rollout signoff).

## Implementation Strategy
1. Close RZ0 before Phase 8 release work (no packaging hardening on unresolved boot policy).
2. Freeze release artifact and version policy before automation work.
3. Make packaging deterministic before expanding environment compatibility scope.
4. Land security defaults before canary-style rollout logic.
5. Tie diagnostics schema work directly to runbook procedures.
6. Validate rollback and recovery before declaring release readiness.
7. Run full test suite at each milestone boundary and enforce gate ownership.

## Code and Doc Focus Areas
- `scripts/wasm/compile-wasm-fasls.sh`
- `scripts/wasm/pack-inline-bundle-v2.mjs`
- `doc/wasm/js/load-image.mjs`
- `doc/wasm/js/make-real-image.mjs`
- `scripts/wasm/make-real-image.lisp`
- `doc/wasm/js/all-smoke.mjs`
- `doc/wasm/js/wasm-ui-persist-smoke.mjs`
- `doc/wasm/js/persist-service.mjs`
- `doc/wasm/js/microkernel.mjs`
- `web-ui/package.json`
- `web-ui/tests/phase-8-*.test.mjs`
- `web-ui/src/runtime-bridge.mjs`
- `web-ui/src/persistence/serialize.mjs`
- `web-ui/src/persistence/migrate.mjs`
- `web-ui/src/quality-gates.mjs`
- `doc/wasm/persistence-dev-environment.md`
- `scripts/wasm/*`
- `doc/wasm/wasm-runtime-modules.json`
- `web-ide/phase-8/*.md`

## Planned Phase 8 Acceptance Suites
- `web-ui/tests/phase-8-release-artifacts.test.mjs`
- `web-ui/tests/phase-8-compatibility.test.mjs`
- `web-ui/tests/phase-8-security-hardening.test.mjs`
- `web-ui/tests/phase-8-observability.test.mjs`
- `web-ui/tests/phase-8-data-recovery.test.mjs`
- `web-ui/tests/phase-8-rollout-gates.test.mjs`
- `web-ui/tests/phase-8-integration.test.mjs`

## Risks and Mitigations
- Risk: release workflow complexity slows iteration.
  - Mitigation: split fast gate vs full release gate and automate manifest generation.
- Risk: compatibility matrix drifts from real-world support.
  - Mitigation: keep matrix explicit, versioned, and test-backed.
- Risk: insufficient diagnostics during incidents.
  - Mitigation: define mandatory event fields and support bundle format early.
- Risk: rollback paths are documented but unproven.
  - Mitigation: require drill-based verification before stable promotion.
- Risk: flush-on-exit model can lose last mutations on hard crash.
  - Mitigation: atomic temp+rename snapshot writes, explicit manual flush hook for long-running sessions, and startup stale-snapshot warning telemetry.

## Decision Gates (Expected)
1. Release channel policy:
   - Option A (recommended): canary -> release candidate -> stable.
   - Option B: direct stable with emergency rollback.
2. Telemetry posture:
   - Option A (recommended): minimal operational telemetry by default with explicit opt-in for expanded diagnostics.
   - Option B: no telemetry beyond local logs.
3. Compatibility policy strictness:
   - Option A (recommended): explicit minimum browser/runtime versions with degraded-mode policy.
   - Option B: best-effort support without strict matrix gates.
4. Rollback trigger policy:
   - Option A (recommended): automatic rollback threshold for gate-defined regressions.
   - Option B: manual rollback only.

## Phase 8 Signoff Conditions
- M0 through M8 complete.
- Release artifact contract and version policy approved.
- Packaging and manifest gates pass in CI.
- `cd web-ui && npm test` passes with Phase 8 suites integrated.
- Compatibility, security, and recovery gates pass.
- Runbooks and escalation policies are ratified by owners.
