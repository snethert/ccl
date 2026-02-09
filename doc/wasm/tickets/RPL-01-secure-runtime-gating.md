# RPL-01 - Secure Runtime Gating

Status: in_progress  
Priority: P0  
Owner: Runtime/WASM replacement track  
Last Updated: 2026-02-09  
Parent Plan: `doc/wasm/runtime-replacement-master-plan.md`

## Scope

In scope:

- Define the MVP secure-only runtime startup contract.
- Specify required runtime capabilities and deterministic startup checks.
- Define explicit failure diagnostics and remediation guidance.
- Reconcile legacy portability-first language in docs with secure-only replacement direction.

Out of scope:

- Shared-memory queue implementation details (RPL-03).
- Storage V2 data model and merge logic (RPL-05/RPL-06).
- Module environment-sharing implementation (RPL-07).

## Dependencies

- RPL-00 governance process in use.

## Deliverables

1. Secure runtime gate matrix with required capabilities and boot checks.
2. Startup failure contract (error codes/messages + remediation mapping).
3. Documentation updates for secure-only MVP support policy and no-fallback behavior.
4. Validation plan for startup gate tests in smoke/harness lanes.

## Exit Criteria

- Required startup checks are defined and mapped to pass/fail behavior.
- Unsupported environments fail explicitly with actionable diagnostics.
- Docs do not simultaneously claim secure-only MVP and portability-first fallback for the same runtime lane.
- Startup gate checks are covered by deterministic validation steps.

## Current Notes

- Step 1 contradiction inventory v1 is now recorded in this ticket with line-level source references and resolution actions.
- Step 2 capability/startup-gate matrix v1 is now defined with frozen check IDs (`SRG-01`..`SRG-12`).
- Step 3 diagnostics contract v1 is now defined with deterministic startup-failure envelope and event semantics.
- Step 4 loader/harness integration plan v1 is now defined with concrete entrypoints and diagnostics surfacing rules.
- Step 5 validation/regression gate matrix v1 is now defined with concrete pass/fail command lanes and evidence assertions.
- Step 6 handoff checklist and closure-readiness assessment v1 is now published (`HND-01`..`HND-06`, `CRA-01`..`CRA-05`).
- Cross-track dependency row `X-01` is now cleared via explicit BPL-02 references to `SRG-01`..`SRG-12`.
- Cross-track dependency row `X-02` is now cleared via RPL-02 Step 3 `X03M-01`..`X03M-05` mappings and BPL-03 `B3*` consumption coverage over frozen worker/lifecycle IDs.
- RPL-03 Step 1 protocol contract is now published (`IPCP-01`..`IPCP-49`) and actively absorbs IPC contradiction classes (`C-01`, `C-03`, `C-04`, `C-08`).
- RPL-03 Step 2 conformance contract is now published (`IPCV-01`..`IPCV-12`, `IPCL-01`..`IPCL-05`) and defines deterministic hard-gate evidence requirements for `X-03`.
- RPL-03 Step 3 rerun evidence is now committed (`doc/wasm/tickets/evidence/rpl-03-step3-rerun-2026-02-09/`) with terminal `status=pass` and `x03_clear_ready=true`; dependency row `X-03` is now `done`.
- Existing docs still include portability-first and single-runner-first assumptions in key places.
- Replacement direction requires secure-only startup posture for shared-memory transport and OPFS/SyncAccessHandle storage.
- CL thread semantics remain deferred, but runtime worker/thread capability is required at startup.

## Immediate Next Step

- Action: continue contradiction remediation flow by landing source-doc text updates for `C-01`, `C-03`, `C-04`, and `C-08` against the now-closed RPL-03 baseline.
- Why now: RPL-03 conformance evidence is now passing and `X-03` is closed, so remaining contradiction follow-through is doc-language reconciliation.
- Success evidence: contradiction rows for `C-01`/`C-03`/`C-04`/`C-08` reference concrete source-doc updates aligned with frozen `IPCP-*`/`IPCV-*` contract language.

## Step 1 Output - Contradiction Inventory (v1)

This table is the active contradiction tracker for RPL-01. Every row must keep `Status` and `Notes` current as remediation work lands.

| ID | Source | Contradiction | Required resolution action | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| C-01 | `doc/wasm/decisions.md:7` | ADR-0001 makes copy-based `kernel_request` responses the required baseline. | Supersede ADR language so shared-memory IPC is normative for hot paths; keep copy/message path only for bootstrap/control/diagnostics. | in_progress | Step 1/2 protocol and conformance clauses now published in RPL-03; upstream ADR text alignment and committed evidence remain. |
| C-02 | `doc/wasm/decisions.md:52` | ADR-0006 defines single-runner portable baseline and deferred shared-heap threading. | Replace with secure-only MVP runtime stance: required worker/thread posture for startup, while CL thread semantics may still be deferred. | open | Handshake with RPL-02 and RPL-03. |
| C-03 | `doc/wasm/kernel-request-abi.md:3` | ABI spec is explicitly copy-based MVP with zero-copy as optional future extension. | Define ABI v2 transport contract where shared-memory channels are primary data-plane/hot-path mechanism. | in_progress | Step 1/2 protocol and conformance clauses now published in RPL-03; ABI-v2 text replacement and committed evidence remain. |
| C-04 | `doc/wasm/js-microkernel-spec.md:14` | Microkernel goals and requirements retain single-thread compatibility/degrade-to-baseline behavior. | Rewrite execution modes to secure-only MVP with required capabilities and explicit unsupported-startup failure contract. | in_progress | No-fallback transport and fail mapping are now explicit in RPL-03 Step 1/2; upstream microkernel text alignment remains. |
| C-05 | `doc/wasm/project-overview.md:69` | Overview frames a portability ladder with message-passing/sandbox baseline and optional shared memory. | Reframe as secure-environment performance-first MVP; move portability/embeddable discussion to future non-MVP notes only. | open | Keep historical context only if clearly marked legacy. |
| C-06 | `doc/wasm/threads.md:7` | Threading doc marks shared-heap mode optional and single-runner as baseline target. | Rewrite to required startup threading/worker topology assumptions for MVP runtime architecture. | open | CL-level thread semantics can still remain out-of-scope for MVP. |
| C-07 | `doc/wasm/yield-resume.md:27` | Yield/resume guidance preserves portable baseline without SAB/Atomics and makes Stage 3 optional. | Re-scope document so secure capability prerequisites are assumed; treat non-secure mode as unsupported in MVP. | open | Keep explicit note if staged internals remain useful. |
| C-08 | `doc/wasm/interrupts.md:9` | Interrupt model centers portable single-runner baseline and optional shared-memory upgrade. | Align interrupt requirements with secure-only startup and required shared-memory runtime posture. | in_progress | Deterministic signaling and startup/lifecycle IPC hooks are now defined in RPL-03 Step 1/2; interrupt doc alignment and committed evidence remain. |
| C-09 | `doc/wasm/ui-bridge-protocol.md:6` | UI bridge protocol assumes transport over copy-based `kernel_request` ABI. | Define shared-memory transport path for UI ingress/egress hot paths; retain message/copy channel only for non-hot/control paths. | open | Primary handoff to RPL-04. |
| C-10 | `doc/wasm/persistence-service-spec.md:7` | Persistence spec is memory-first snapshot + optional host backends, not Storage V2 object/ref model. | Mark this spec legacy for replacement track and author Storage V2 normative local-core contract. | open | Primary handoff to RPL-05. |
| C-11 | `doc/wasm/mvp-unattended-execution-plan.md:54` | MVP unattended plan sets `memory-snapshot` as default persistence lane. | Add explicit replacement-track override note and migration path to Storage V2/secure-runtime gating docs. | open | Keep current lane documented as legacy operational baseline until cutover. |
| C-12 | `doc/wasm/porting-status.md:60` | Current status report treats memory-snapshot persistence as default unattended posture. | Split status into current-lane vs replacement-lane and prevent old default from appearing as future architecture target. | open | Avoid deleting current facts; relabel scope. |
| C-13 | `doc/wasm/roadmap.md:18` | Roadmap defers concurrency and states single-threaded baseline first. | Update roadmap to replacement sequence where secure runtime gating and shared-memory IPC are prerequisite, not optional late-phase work. | open | Coordinate with RPL-00 governance cadence. |
| C-14 | `web-ide/phase-8/implementation-plan.md:46` | Phase 8 plan locks memory-snapshot decoupling/defaults and declares runtime architecture rewrite out-of-scope. | Add replacement-track supersession notes and explicit dependency on runtime replacement milestones before front-end release execution. | open | Keep pre-existing release work as legacy lane, not target architecture. |

## Step 2 Output - Secure Runtime Capability and Startup Gate Matrix (v1)

Check IDs in this table are frozen for RPL-01 Step 2 and are normative inputs for cross-track dependency row `X-01` and BPL-02 contract drafting.

| check_id | capability/assertion | startup probe mechanism | pass criteria | fail code | fail message template | remediation guidance | linked contradiction IDs |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SRG-01 | Startup environment is cross-origin isolated (`globalThis.crossOriginIsolated === true`). | Loader preflight reads `globalThis.crossOriginIsolated` before worker/bootstrap side effects. | Value is `true` and recorded in startup diagnostics. | RPL01-E001 | `[{code}] {check_id} failed: cross-origin isolation is required; observed={observed}.` | Enable COOP/COEP (or equivalent isolation headers), run in top-level isolated context, then restart. | C-02, C-04, C-05, C-06, C-07, C-08, C-13 |
| SRG-02 | `SharedArrayBuffer` constructor/allocation is available. | Preflight checks `typeof SharedArrayBuffer === "function"` and allocates `new SharedArrayBuffer(4096)`. | Constructor exists and allocation succeeds without exception. | RPL01-E002 | `[{code}] {check_id} failed: SharedArrayBuffer unavailable in startup context.` | Fix isolation/policy headers and browser/runtime flags until SAB allocation succeeds. | C-01, C-02, C-03, C-04, C-05, C-06, C-07, C-08, C-09, C-13 |
| SRG-03 | Atomics API and worker blocking wait primitive are usable. | Dedicated worker runs `Atomics.wait` timeout probe on SAB-backed `Int32Array` and returns result token. | Probe returns `timed-out` or `ok` and does not throw. | RPL01-E003 | `[{code}] {check_id} failed: Atomics wait/notify path is not usable in worker context.` | Move blocking waits to workers, verify browser policy for Atomics in isolated context, then rerun startup probe. | C-02, C-04, C-06, C-07, C-08, C-13 |
| SRG-04 | WebAssembly shared memory + threads primitive is available for runtime workers. | Worker validates/instantiates minimal threaded WASM probe module using shared memory import and atomic op. | Probe module validates and instantiates with shared memory enabled. | RPL01-E004 | `[{code}] {check_id} failed: WebAssembly shared memory/thread capability missing.` | Use browser/runtime versions with WASM shared memory threads enabled; keep MVP runtime blocked otherwise. | C-02, C-03, C-04, C-06, C-07, C-08, C-13 |
| SRG-05 | Required runtime worker topology is present at startup (runtime, kernel I/O, storage worker roles). | Startup spawns required worker roles and waits for deterministic `READY` handshake per role. | All required roles acknowledge before `startup_worker_ready_timeout_ms`; no main-thread blocking lane is selected. | RPL01-E005 | `[{code}] {check_id} failed: required worker topology did not initialize (missing={missing_roles}).` | Fix worker boot wiring and role ownership so all required workers come online before runtime entry. | C-02, C-04, C-06, C-07, C-08, C-13 |
| SRG-06 | OPFS is available in storage worker path. | Storage worker calls `navigator.storage.getDirectory()` during startup probe stage. | API returns a `FileSystemDirectoryHandle` without permission-denied failure. | RPL01-E006 | `[{code}] {check_id} failed: OPFS directory handle unavailable for storage worker.` | Run in secure context/browser with OPFS enabled for workers; avoid unsupported embedding modes. | C-10, C-11, C-12, C-14 |
| SRG-07 | SyncAccessHandle worker path is usable for Storage V2 local durability. | Storage worker creates temp OPFS file, opens `createSyncAccessHandle()`, write/read/flush/close probe, then cleanup. | Probe completes with byte parity and no handle lifecycle errors. | RPL01-E007 | `[{code}] {check_id} failed: SyncAccessHandle worker probe failed at {stage}.` | Enable worker SyncAccessHandle support and fix OPFS write permissions before retrying startup. | C-10, C-11, C-12, C-14 |
| SRG-08 | Runtime/kernel hot-path transport profile is shared-memory-first (`shared_ring_v1`), not copy/message baseline. | Startup validates transport policy table and runs shared-ring loopback self-test for required hot-path op classes. | Required hot-path classes route to shared channels; copy/message channels limited to bootstrap/control/diagnostics. | RPL01-E008 | `[{code}] {check_id} failed: hot-path transport policy is not shared-memory-first.` | Update transport routing policy to shared ring channels for hot paths; keep copy lanes control-only. | C-01, C-03, C-04, C-05, C-07, C-08 |
| SRG-09 | Runtime/UI bridge hot-path classes are bound to shared channels. | Startup checks bridge route map and executes shared-channel ingress/egress ping for required class set. | Required UI command/effect/state classes pass shared-channel probe; message lane is control/telemetry only. | RPL01-E009 | `[{code}] {check_id} failed: UI bridge hot-path class {class_id} is not mapped to shared transport.` | Migrate required bridge classes to shared channels and keep message transport for non-hot control traffic only. | C-01, C-03, C-05, C-09 |
| SRG-10 | Replacement lane persistence profile is Storage V2 OPFS-based, not memory-snapshot-default. | Startup validates manifest fields: `replacement_lane=true`, `persistence_backend=storage-v2-opfs`, `legacy_memory_snapshot_default=false`. | All manifest assertions match expected replacement profile and are emitted in startup diagnostics banner. | RPL01-E010 | `[{code}] {check_id} failed: replacement persistence profile mismatch (observed={observed_profile}).` | Switch runtime config to Storage V2 replacement profile; keep memory-snapshot only in explicitly labeled legacy lane. | C-10, C-11, C-12, C-14 |
| SRG-11 | No-silent-fallback policy is enforced for required startup gates. | Startup checks `startup_gate_mode=strict`/`allow_fallback=false`; harness fail-injection verifies abort-on-first-required-failure. | Any required-check failure terminates startup with explicit fail code; no degraded fallback runtime is launched. | RPL01-E011 | `[{code}] {check_id} failed: strict startup gate mode violated (fallback path detected).` | Remove fallback branches from replacement startup path and enforce explicit hard-fail behavior. | C-04, C-05, C-07, C-13 |
| SRG-12 | Runtime thread capability is required now; CL thread semantics remain explicitly deferred. | Startup validates config tuple: `runtime_thread_capability_required=true` and `cl_thread_semantics=deferred`; diagnostics emits both fields. | Runtime capability gates (SRG-01..SRG-05) remain mandatory while CL semantics state is explicitly `deferred`. | RPL01-E012 | `[{code}] {check_id} failed: runtime/CL thread semantics boundary is not explicitly declared.` | Set explicit replacement policy flags so runtime worker/thread requirements are enforced while CL semantics stay deferred. | C-02, C-06, C-13 |

## Step 3 Output - Startup Failure Semantics and Diagnostics Contract (v1)

This section defines the normative machine-readable diagnostics contract for startup gate execution. It applies to all `SRG-01`..`SRG-12` checks and `RPL01-E001`..`RPL01-E012` fail codes.

### Required Startup Gate Execution Semantics

1. Check execution order is fixed and deterministic: `SRG-01` through `SRG-12`.
2. All checks in Step 2 are `required=true` for MVP replacement startup.
3. Startup mode is strict:
   - `startup_gate_mode=strict`
   - `allow_fallback=false`
4. On first required-check failure:
   - emit failing check result record,
   - emit final failure summary record,
   - terminate startup as unsupported environment (no degraded mode).
5. `skip` outcome is invalid for required checks and must be treated as `fail` with `RPL01-E011`.

### Startup Summary Envelope (`startup_gate_summary_v1`)

| field | type | required | constraints / meaning |
| --- | --- | --- | --- |
| `schema_version` | string | yes | Must equal `startup_gate_summary_v1`. |
| `run_id` | string | yes | Stable identifier for one startup attempt. |
| `timestamp_utc` | string | yes | RFC3339 UTC timestamp of summary emission. |
| `replacement_track` | string | yes | Must equal `RPL-01`. |
| `startup_gate_mode` | string | yes | Must equal `strict`. |
| `allow_fallback` | boolean | yes | Must be `false`. |
| `check_order` | array<string> | yes | Must list `SRG-01`..`SRG-12` in execution order. |
| `checks_executed` | integer | yes | Count of emitted check records for this run. |
| `status` | string | yes | `pass` or `fail`. |
| `failure_check_id` | string/null | yes | Failing `SRG-*` ID when `status=fail`; else `null`. |
| `failure_code` | string/null | yes | `RPL01-E*` when `status=fail`; else `null`. |
| `message` | string | yes | Rendered human-readable summary message. |
| `contradiction_ids` | array<string> | yes | Contradiction IDs linked to failing check; empty when pass. |
| `remediation` | string/null | yes | Remediation guidance for failing check; `null` when pass. |
| `results_digest` | string | yes | Deterministic digest over emitted check result records. |

### Per-Check Result Envelope (`startup_gate_check_result_v1`)

| field | type | required | constraints / meaning |
| --- | --- | --- | --- |
| `schema_version` | string | yes | Must equal `startup_gate_check_result_v1`. |
| `run_id` | string | yes | Must match summary `run_id`. |
| `sequence` | integer | yes | 1-based monotonic check index. |
| `check_id` | string | yes | One of `SRG-01`..`SRG-12`. |
| `required` | boolean | yes | Must be `true` for MVP replacement lane. |
| `status` | string | yes | `pass` or `fail` only. |
| `fail_code` | string/null | yes | Required when `status=fail`; else `null`. |
| `message` | string | yes | Rendered from Step 2 fail template (or pass confirmation text). |
| `observed` | object | yes | Check-specific probe facts used to justify pass/fail deterministically. |
| `pass_criteria` | string | yes | Canonical pass assertion text from Step 2 matrix row. |
| `contradiction_ids` | array<string> | yes | Must match linked contradiction IDs from Step 2 matrix row. |
| `remediation` | string/null | yes | Required when `status=fail`; else `null`. |

### Canonical Failure Outcome Contract

| condition | required outcome | machine assertion |
| --- | --- | --- |
| check result with `status=fail` | fail code must be canonical for that check | `fail_code` must equal the Step 2 matrix fail code bound to emitted `check_id` |
| first required-check failure | startup aborts immediately after failure record emission | no check records may be emitted with `sequence` greater than failing check sequence |
| any fallback branch selected | force failure | summary `status=fail` and `failure_code=RPL01-E011` |
| `status=fail` summary | exact check/code linkage | `failure_check_id` and `failure_code` must equal failing check result fields |
| `status=pass` summary | full completion evidence | `checks_executed=12`, `failure_check_id=null`, `failure_code=null` |
| malformed diagnostics payload | treat as startup-gate failure | fail with `RPL01-E011` and include parse/validation reason in `message` |

### Message Rendering Rules (Normative)

1. Failure `message` must include both `fail_code` and `check_id`.
2. Placeholder values in Step 2 fail templates must be substituted from `observed` fields.
3. If a placeholder value is unavailable, renderer must emit literal `unknown` value; omission is not allowed.
4. `remediation` text must be the Step 2 matrix remediation string for the failing check.

### Minimum Harness Assertions

1. Parse emitted check records and summary as JSON objects and validate required fields/types.
2. Assert strict mode invariants: `startup_gate_mode=strict` and `allow_fallback=false`.
3. Assert check order matches `SRG-01`..`SRG-12` prefix until fail (or full sequence on pass).
4. Assert `failure_code`/`failure_check_id` in summary match failing check record exactly.
5. Assert unsupported environment startup returns failure summary and does not continue into runtime startup success path.

## Step 4 Output - Loader/Harness Integration Plan (v1)

Integration IDs in this section are frozen for Step 4 and define where Step 2 checks and Step 3 diagnostics must be surfaced in current startup/test lanes.

| integration_id | lane / entrypoint | integration insertion point | startup gate execution contract | diagnostics surfacing contract | pass assertion | fail assertion | linked checks |
| --- | --- | --- | --- | --- | --- | --- | --- |
| LHI-01 | `doc/wasm/js/load-image.mjs` (`--mode start-lisp`) | Run startup-gate executor after manifest/hash validation and before `runBootstrapContract("pre-start")` / `wasm_ccl_start_lisp`. | Execute required checks in fixed order `SRG-01`..`SRG-12`; strict mode only (`allow_fallback=false`). | Emit one `STARTUP_GATE_CHECK` line per check with `startup_gate_check_result_v1` JSON and one terminal `STARTUP_GATE_SUMMARY` line with `startup_gate_summary_v1` JSON. | Summary `status=pass`, `checks_executed=12`; flow continues into existing bootstrap + entry execution. | Summary `status=fail`; process exits non-zero before bootstrap/entry execution; no fallback branch. | SRG-01..SRG-12 |
| LHI-02 | `doc/wasm/js/load-image.mjs` (`--mode run-toplevel`) | Same insertion point as `LHI-01`, before toplevel entry execution path. | Same fixed-order strict startup-gate run for replacement lane startup. | Same `STARTUP_GATE_CHECK` + `STARTUP_GATE_SUMMARY` emission requirements. | Summary `status=pass`; toplevel path proceeds. | Summary `status=fail`; process exits non-zero before toplevel entry call. | SRG-01..SRG-12 |
| LHI-03 | `doc/wasm/js/start-lisp-noninteractive-smoke.mjs` | In `runNodeCase` result handling, parse child `STARTUP_GATE_SUMMARY` line and assert schema/fields deterministically. | Root strict case must assert pass summary from child loader run; fail-injection case (when enabled) must assert expected fail check/code pair. | Harness must fail on missing/invalid summary payload; string-only assertions are insufficient once gate integration lands. | Strict root case returns PASS with valid pass summary. | Missing/invalid summary or unexpected fail/pass status causes harness FAIL. | SRG-01..SRG-12 |
| LHI-04 | `doc/wasm/js/all-smoke.mjs` | Keep startup-gate authority routed through included `start-lisp-noninteractive-smoke.mjs` entry. | `all-smoke` run is considered startup-gate-integrated only if the noninteractive smoke enforces summary validation. | Preserve child summary lines in smoke output; do not suppress startup-gate records. | `PASS: all wasm smoke tests` implies startup-gate checks passed in included strict lane(s). | Any startup-gate assertion failure in delegated smoke fails aggregate run. | SRG-01..SRG-12 |
| LHI-05 | `doc/wasm/js/wasm-ui-persist-smoke.mjs` | Run startup-gate executor before `wasm_ccl_start_lisp` and before probe/full persistence execution. | Same strict required-check sequence for replacement/root lane execution. | Emit `STARTUP_GATE_SUMMARY` and fail with explicit `FAIL:` output when summary `status=fail`. | Persistence smoke proceeds only after summary `status=pass`. | Startup-gate fail aborts smoke early; compiled entry probes are not attempted. | SRG-01..SRG-12 |
| LHI-06 | `web-ui/tests/browser/harness.mjs` | Execute startup-gate probe before WASM runtime bring-up (`createSharedCclRuntime` / `instantiateWasm`) in harness bootstrap path. | Browser harness must treat required-check failures as hard test failures, not skips. | Surface summary object in test failure output (structured JSON), including `failure_check_id` and `failure_code`. | Harness test lanes continue only on summary `status=pass`. | Required-check fail aborts harness setup and fails the test deterministically. | SRG-01..SRG-12 |

### Diagnostics Surfacing Rules (Normative)

1. Every integrated lane must emit exactly one terminal `STARTUP_GATE_SUMMARY` record per startup attempt.
2. On success, `STARTUP_GATE_SUMMARY` must be emitted after final required check and before runtime success marker logs.
3. On failure, failing `STARTUP_GATE_CHECK` and terminal summary must be emitted before process/test abort.
4. Lanes must not rely on free-form log parsing when structured startup-gate records are available.
5. No lane may continue into runtime bootstrap/entry execution after summary `status=fail`.

### Step 4 Lane Mapping (Execution Ownership)

| lane_id | command / harness | owner path | required summary expectation |
| --- | --- | --- | --- |
| LANE-01 | `node doc/wasm/js/load-image.mjs --mode start-lisp --manifest doc/wasm/root.image.manifest.json --stdin-text "(quit)\n" --close-stdin` | `doc/wasm/js/load-image.mjs` | `status=pass`, `checks_executed=12` |
| LANE-02 | `node doc/wasm/js/start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive` | `doc/wasm/js/start-lisp-noninteractive-smoke.mjs` | strict root case consumes child summary and asserts pass |
| LANE-03 | `node doc/wasm/js/wasm-ui-persist-smoke.mjs --image root --verbose` | `doc/wasm/js/wasm-ui-persist-smoke.mjs` | startup summary pass required before persistence probes |
| LANE-04 | `node doc/wasm/js/all-smoke.mjs` | `doc/wasm/js/all-smoke.mjs` | delegated startup-gate smoke assertions must pass |
| LANE-05 | `web-ui/tests/browser/harness.mjs` browser lane | `web-ui/tests/browser/harness.mjs` | harness bootstrap fails hard on startup summary fail |

## Step 5 Output - Validation and Regression Gates (v1)

Validation IDs in this section are frozen for Step 5 and define deterministic pass/fail command lanes tied to Step 2 checks, Step 3 diagnostics contract, and Step 4 integration points.

### Validation Execution Contract

1. Every validation run must record:
   - command,
   - exit code,
   - emitted `STARTUP_GATE_SUMMARY` payload,
   - pass/fail assertion result.
2. Pass lanes must assert:
   - summary `status=pass`,
   - `checks_executed=12`,
   - strict mode invariants (`startup_gate_mode=strict`, `allow_fallback=false`).
3. Fail lanes must assert:
   - summary `status=fail`,
   - expected `failure_check_id`,
   - expected `failure_code`,
   - no runtime success marker after failure summary.
4. Fail-injection controls are normative for validation lanes:
   - `CCL_STARTUP_GATE_TEST_FAIL_CHECK=<SRG-ID>`
   - `CCL_STARTUP_GATE_TEST_INVALID_SUMMARY=1`
5. If implementation uses different internal knobs, it must provide compatibility wrappers exposing the two controls above for test lanes.

### Validation Matrix

| validation_id | lane_id | objective | command | expected startup summary assertions | expected process assertions | fail-injection control | expected fail mapping | evidence artifact |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| VRG-01 | LANE-01 | Root strict loader startup pass | `node doc/wasm/js/load-image.mjs --mode start-lisp --manifest doc/wasm/root.image.manifest.json --stdin-text "(quit)\n" --close-stdin` | `status=pass`; `checks_executed=12`; strict fields valid | exit code `0`; runtime entry reaches expected success marker | none | n/a | summary JSON + command log |
| VRG-02 | LANE-02 | Noninteractive strict lane pass | `node doc/wasm/js/start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive` | child summary `status=pass`; strict fields valid | exit code `0`; harness PASS marker present | none | n/a | harness output + parsed child summary |
| VRG-03 | LANE-03 | Persistence smoke lane pass after startup gate | `node doc/wasm/js/wasm-ui-persist-smoke.mjs --image root --verbose` | startup summary `status=pass` before persistence probes | exit code `0`; persistence PASS marker present | none | n/a | smoke log with summary ordering |
| VRG-04 | LANE-04 | Aggregate smoke lane preserves startup-gate assertions | `node doc/wasm/js/all-smoke.mjs` | delegated startup summary assertions pass | aggregate PASS marker present | none | n/a | aggregate smoke transcript |
| VRG-05 | LANE-05 | Browser harness startup gate pass | `npm --prefix web-ui run test:sandbox` | browser harness summary `status=pass` on runtime bootstrap path | test command succeeds without startup-gate skip | none | n/a | test report + structured summary capture |
| VRG-06 | LANE-01 | Deterministic fail: cross-origin isolation gate | `CCL_STARTUP_GATE_TEST_FAIL_CHECK=SRG-01 node doc/wasm/js/load-image.mjs --mode start-lisp --manifest doc/wasm/root.image.manifest.json --stdin-text "(quit)\n" --close-stdin` | `status=fail`; `failure_check_id=SRG-01`; `failure_code=RPL01-E001` | non-zero exit; no runtime entry success marker | `CCL_STARTUP_GATE_TEST_FAIL_CHECK=SRG-01` | `SRG-01 -> RPL01-E001` | failure summary JSON + exit code |
| VRG-07 | LANE-01 | Deterministic fail: SyncAccessHandle gate | `CCL_STARTUP_GATE_TEST_FAIL_CHECK=SRG-07 node doc/wasm/js/load-image.mjs --mode start-lisp --manifest doc/wasm/root.image.manifest.json --stdin-text "(quit)\n" --close-stdin` | `status=fail`; `failure_check_id=SRG-07`; `failure_code=RPL01-E007` | non-zero exit; no startup continuation | `CCL_STARTUP_GATE_TEST_FAIL_CHECK=SRG-07` | `SRG-07 -> RPL01-E007` | failure summary JSON + exit code |
| VRG-08 | LANE-01 | Deterministic fail: no-fallback contract enforcement | `CCL_STARTUP_GATE_TEST_FAIL_CHECK=SRG-11 node doc/wasm/js/load-image.mjs --mode start-lisp --manifest doc/wasm/root.image.manifest.json --stdin-text "(quit)\n" --close-stdin` | `status=fail`; `failure_check_id=SRG-11`; `failure_code=RPL01-E011` | non-zero exit; fallback/runtime-degraded path not launched | `CCL_STARTUP_GATE_TEST_FAIL_CHECK=SRG-11` | `SRG-11 -> RPL01-E011` | failure summary JSON + no-fallback assertion log |
| VRG-09 | LANE-02 | Deterministic fail: malformed diagnostics payload handling | `CCL_STARTUP_GATE_TEST_INVALID_SUMMARY=1 node doc/wasm/js/start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive` | summary validation fails with `RPL01-E011` semantics | harness exits non-zero and reports schema/parse failure | `CCL_STARTUP_GATE_TEST_INVALID_SUMMARY=1` | malformed diagnostics -> `RPL01-E011` | harness failure log + parse error detail |
| VRG-10 | LANE-04 | Regression guard: aggregate suite fails when startup gate fails | `CCL_STARTUP_GATE_TEST_FAIL_CHECK=SRG-01 node doc/wasm/js/all-smoke.mjs` | delegated startup summary reports `SRG-01` failure | aggregate command exits non-zero; no false PASS | `CCL_STARTUP_GATE_TEST_FAIL_CHECK=SRG-01` | `SRG-01 -> RPL01-E001` | aggregate failure transcript |

### Required Validation Coverage Assertions

1. At least one pass-case command must execute each lane `LANE-01`..`LANE-05`.
2. At least one fail-case command must assert `RPL01-E001`, `RPL01-E007`, and `RPL01-E011`.
3. Validation runbook must include one malformed-summary failure lane (`VRG-09` class).
4. Validation evidence must preserve emitted summary JSON for machine replay.
5. No validation lane may treat required-gate failure as warning/skip.

## Step 6 Output - Master-Plan Sync and Handoff Package (v1)

This section freezes the Step 2-5 contract bundle for downstream consumption and records closure-readiness checks for RPL-01 handoff.

### Step 6 Handoff Checklist

| handoff_id | artifact bundle | frozen identifiers | downstream consumers | required consumption evidence | status |
| --- | --- | --- | --- | --- | --- |
| HND-01 | Secure runtime capability matrix and fail-code map | `SRG-01`..`SRG-12`, `RPL01-E001`..`RPL01-E012` | BPL-02 (`X-01`), RPL-02, RPL-03 | Consumer docs reference canonical `SRG-*` check IDs (no renamed aliases) and preserve check/code linkage. | ready |
| HND-02 | Startup diagnostics schema contract | `startup_gate_check_result_v1`, `startup_gate_summary_v1` | Loader/smoke/browser harness owners (`LHI-01`..`LHI-06`) | Downstream parsing/assertion logic references schema names and required fields from Step 3. | ready |
| HND-03 | Loader/harness integration map | `LHI-01`..`LHI-06` | Runtime lane implementers and smoke owners | Integration work items cite `LHI-*` insertion points and enforce strict no-fallback surfacing rules. | ready |
| HND-04 | Validation and regression matrix | `VRG-01`..`VRG-10`, `LANE-01`..`LANE-05` | CI/runbook owners, smoke maintainers | Validation runbooks include pass/fail lanes, expected fail-code assertions, and evidence artifact capture. | ready |
| HND-05 | Contradiction routing map | `C-01`..`C-14` | RPL-02/RPL-03/RPL-04/RPL-05/RPL-09 and related doc tracks | Owning tickets reference contradiction IDs they absorb and preserve resolution intent from Step 1. | ready |
| HND-06 | Governance sync proof | Master + subplan synchronized state for Step 2-6 | RPL-00 governance loop, program board maintainers | `RPL-01` notes/next-step state matches runtime master plan in the same update cycle. | done |

### Closure-Readiness Assessment

| assessment_id | criterion | evidence from Step outputs | result | blocking follow-up |
| --- | --- | --- | --- | --- |
| CRA-01 | Deterministic startup-gate contract is complete | Step 2 matrix freezes checks/probes/pass-fail mapping; Step 3 freezes summary/check schemas and first-failure semantics. | pass | none |
| CRA-02 | No-silent-fallback behavior is fully specified | `SRG-11`, `RPL01-E011`, Step 3 fallback-failure rule, and Step 5 fail lanes (`VRG-08`, `VRG-10`) are all aligned. | pass | none |
| CRA-03 | Secure-only MVP scope is explicit and CL thread semantics boundary is preserved | Step 2 `SRG-01`..`SRG-07`, `SRG-12` and related contradiction linkage define required runtime capabilities vs deferred CL semantics. | pass | none |
| CRA-04 | Integration and validation lanes are machine-actionable | Step 4 `LHI-*` insertion points and Step 5 `VRG-*` commands/assertions provide deterministic lane-level evidence requirements. | pass | none |
| CRA-05 | Cross-track contract-consumption gate is complete | BPL-02 now references frozen `SRG-01`..`SRG-12` IDs explicitly and dependency row `X-01` is updated accordingly. | pass | none |

### Step 6 Outcome

1. Step 6 handoff packaging is complete for RPL-01 definition scope.
2. Contract identifiers from Steps 2-5 are now frozen for downstream consumption.
3. `X-01` contract-consumption evidence is now recorded; downstream runtime tickets now own remediation execution.

## Detailed Work Breakdown

### Step 1 - Contradiction Inventory

- Status: done
- Notes:
  - Contradiction inventory v1 is recorded in this document (`C-01` through `C-14`).
  - Each contradiction now has a required resolution action and status marker for resumable execution.
- Next:
  - Keep this table updated as remediation PRs land; mark each item `in_progress` then `done` with evidence notes.

### Step 2 - Required Capability Matrix Definition

- Status: done
- Notes:
  - Step 2 output now defines secure runtime capability/startup gate matrix v1 with frozen check IDs (`SRG-01`..`SRG-12`).
  - Matrix includes machine-actionable probe mechanisms, deterministic pass criteria, fail codes/templates, remediation guidance, and contradiction-ID linkage.
  - Matrix explicitly separates required runtime/thread capability from deferred CL thread semantics.
- Next:
  - Keep `SRG-*` / `RPL01-E*` identifiers frozen while Step 6 handoff and downstream contract work consume them.

### Step 3 - Failure Semantics and Diagnostics

- Status: done
- Notes:
  - Step 3 output now defines startup diagnostics contract v1 (`startup_gate_check_result_v1` and `startup_gate_summary_v1`).
  - Failure semantics are deterministic: fixed check order, first-failure abort, strict no-fallback enforcement.
  - Machine-actionable payload requirements and minimum harness assertions are now explicit.
- Next:
  - Keep diagnostics contract schemas frozen while Step 6 handoff finalizes downstream consumption guidance.

### Step 4 - Loader/Harness Integration Plan

- Status: done
- Notes:
  - Step 4 output now defines concrete integration IDs (`LHI-01`..`LHI-06`) with file-level insertion points.
  - Diagnostics surfacing contract is explicit across loader, smoke, and browser harness lanes.
  - No-silent-fallback behavior is preserved at each integrated entrypoint.
- Next:
  - Keep `LHI-*` identifiers frozen while Step 6 handoff consumes integration contracts in downstream tickets.

### Step 5 - Validation and Regression Gates

- Status: done
- Notes:
  - Step 5 output now defines validation matrix v1 (`VRG-01`..`VRG-10`) with concrete commands and deterministic assertions.
  - Pass/fail lane coverage is explicit across `LANE-01`..`LANE-05`.
  - Fail-injection controls for deterministic unsupported-startup testing are now normative for validation lanes.
- Next:
  - Keep `VRG-*` identifiers frozen while Step 6 handoff artifacts are consumed by downstream contract and runbook work.

### Step 6 - Master-Plan Sync and Handoff

- Status: done
- Notes:
  - Step 6 output now publishes handoff checklist (`HND-01`..`HND-06`) and closure-readiness assessment (`CRA-01`..`CRA-05`).
  - Master/subplan synchronization for Steps 2-6 is now explicitly recorded as part of the handoff package.
  - `X-01` is now cleared based on explicit BPL-02 references to frozen `SRG-*` identifiers.
- Next:
  - Keep frozen startup-gate identifiers stable while downstream runtime tickets consume them (starting with RPL-03 Step 1).

## Test and Validation Plan

- Spec validation:
  - Verify required checks and failure rules are fully enumerated.
- Integration validation:
  - Confirm loader/harness emits defined failure diagnostics when checks fail.
- Regression validation:
  - Confirm supported secure environment still passes startup gates deterministically.

## Risks and Mitigations

- Risk: ambiguous capability requirements cause inconsistent startup behavior.
  - Mitigation: define check IDs, required outcomes, and fixed diagnostics schema.
- Risk: doc contradictions remain and cause implementation drift.
  - Mitigation: maintain explicit contradiction inventory and resolution status.
- Risk: test lanes do not cover unsupported-startup paths.
  - Mitigation: include explicit fail-case tests and expected error assertions.

## Change Log

- 2026-02-09: Initial subplan scaffold created; execution steps and evidence criteria defined.
- 2026-02-09: Step 1 contradiction inventory v1 added (`C-01`..`C-14`); ticket moved to `in_progress`.
- 2026-02-09: Step 2 capability/startup-gate matrix v1 added with frozen check IDs (`SRG-01`..`SRG-12`) and deterministic startup fail-contract fields.
- 2026-02-09: Step 3 diagnostics contract v1 added with strict startup failure semantics and machine-readable summary/check schemas.
- 2026-02-09: Step 4 loader/harness integration plan v1 added with concrete entrypoints, diagnostics surfacing rules, and lane ownership mapping.
- 2026-02-09: Step 5 validation/regression gate matrix v1 added with deterministic command assertions and fail-injection coverage.
- 2026-02-09: Step 6 handoff package v1 added (`HND-01`..`HND-06`, `CRA-01`..`CRA-05`) with synchronized master/subplan state and `X-01` follow-up target.
- 2026-02-09: Post-Step-6 consumption checkpoint completed by clearing `X-01` through explicit BPL-02 `SRG-01`..`SRG-12` linkage evidence.
- 2026-02-09: Advanced contradiction-remediation handoff to RPL-02 Step 3 after Step 2 lifecycle/no-fallback contract publication (`WLCS-*`, `WLCT-*`, `WLCR-*`).
- 2026-02-09: Synced contradiction-remediation handoff past RPL-02 Step 3 by recording `X-02` closure evidence and advancing immediate follow-through to RPL-03 Step 1.
- 2026-02-09: Synced contradiction-remediation tracker with RPL-03 Step 1+Step 2 publication (`IPCP-*`, `IPCV-*`, `IPCL-*`), advanced `C-01`/`C-03`/`C-04`/`C-08` to `in_progress`, and shifted immediate follow-through to RPL-03 Step 3 evidence execution.
- 2026-02-09: Synced contradiction-remediation tracker with RPL-03 Step 3 run-v1 evidence (`status=fail`), kept `C-01`/`C-03`/`C-04`/`C-08` as `in_progress`, and shifted immediate follow-through to Step 3 gap-remediation rerun.
- 2026-02-09: Synced contradiction-remediation tracker with RPL-03 Step 3 rerun evidence (`status=pass`, `x03_clear_ready=true`), kept `C-01`/`C-03`/`C-04`/`C-08` as `in_progress`, and shifted immediate follow-through to upstream doc-text reconciliation.
