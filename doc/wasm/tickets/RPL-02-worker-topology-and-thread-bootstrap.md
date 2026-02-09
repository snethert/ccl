# RPL-02 - Worker Topology and Thread Bootstrap

Status: done  
Priority: P0  
Owner: Runtime/WASM replacement track  
Last Updated: 2026-02-09  
Parent Plan: `doc/wasm/runtime-replacement-master-plan.md`

## Scope

In scope:

- Define required worker roles for replacement-lane startup.
- Define startup sequencing and deterministic readiness checks for worker bring-up.
- Define ownership boundaries needed by runtime execution and debug/frame model consumers.
- Produce `X-02` readiness inputs for BPL-03 frame/debug contract drafting.

Out of scope:

- Shared-memory wire protocol details (RPL-03).
- Full CL thread semantics implementation (remains deferred).
- Backend frame/debug contract design itself (BPL-03 ownership).

## Dependencies

- RPL-01 startup gate and diagnostics contracts (`SRG-*`, `RPL01-E*`, `LHI-*`, `VRG-*`).
- RPL-00 governance update discipline.

## Deliverables

1. Worker-role topology table with deterministic ownership boundaries.
2. Startup sequence and readiness contract for worker bring-up.
3. Machine-actionable topology readiness artifact schema for test/harness lanes.
4. `X-02` readiness package linking topology outputs into BPL-03 inputs.

## Exit Criteria

- Required worker roles are explicitly defined per startup lane class.
- Worker ownership boundaries are explicit enough to constrain BPL-03 debug/frame modeling.
- Startup sequencing rules are deterministic and no-fallback compliant.
- `X-02` notes are updated with concrete RPL-02 topology evidence and clear follow-up conditions.

## Current Notes

- Step 1 topology output v1 is now defined with frozen role IDs (`WTOP-01`..`WTOP-05`) and startup-sequence IDs (`WSEQ-01`..`WSEQ-06`).
- Step 2 lifecycle/failure-state contract v1 is now defined with frozen state/transition/policy IDs (`WLCS-01`..`WLCS-06`, `WLCT-01`..`WLCT-11`, `WLCR-01`..`WLCR-05`).
- Step 3 cross-track mapping output v1 is now published and consumed in BPL-03 via explicit backend mapping IDs (`B3R-*`, `B3S-*`, `B3L-*`, `B3T-*`, `B3P-*`).
- Topology contract preserves secure-only startup posture and explicit no-silent-fallback behavior.
- Runtime worker/thread capability remains required at startup, while CL thread semantics remain deferred.
- `X-02` readiness package now includes Step 1 topology/readiness evidence and Step 2 lifecycle/restart policy evidence for BPL-03 consumption.
- Dependency row `X-02` clear criteria are now satisfied through explicit BPL-03 consumption mapping coverage for all required RPL-02 ID classes.

## Immediate Next Step

- Action: hand off to RPL-03 Step 1 (shared-memory IPC core contract) with RPL-02 IDs frozen and downstream-consumed.
- Why now: Step 1/2/3 outputs are complete and synchronized, so the next runtime critical path is IPC protocol definition.
- Success evidence: RPL-03 subplan publishes protocol v1 IDs without reopening `WTOP-*`/`WSEQ-*`/`WLCS-*`/`WLCT-*`/`WLCR-*` semantics.

## Step 1 Output - Worker Topology Definition (v1)

Role IDs in this section are frozen for Step 1 and are normative inputs for dependency row `X-02`.

| topology_id | role | execution context | mandatory ownership boundary | readiness probe / handshake | failure condition | linked startup gates | linked contradiction IDs |
| --- | --- | --- | --- | --- | --- | --- | --- |
| WTOP-01 | Startup Orchestrator | host control thread (loader/harness bootstrap context) | Runs startup-gate executor and worker launch orchestration only; must not run runtime execution loop or blocking Atomics waits. | Emits `ROLE_READY` after strict startup gate pass and launch-plan initialization. | Any fallback-to-main-thread runtime execution or missing orchestrator ready event. | SRG-01, SRG-03, SRG-05, SRG-11 | C-02, C-04, C-06, C-13 |
| WTOP-02 | Runtime Execution Worker | dedicated runtime worker thread | Owns `wasm_ccl_start_lisp`/runtime entry execution and runtime-side scheduler state; host thread must not assume execution ownership. | Worker sends deterministic `RUNTIME_READY` handshake with role/version metadata. | Missing handshake before timeout or execution ownership leak to non-runtime role. | SRG-04, SRG-05, SRG-12 | C-02, C-04, C-06, C-08, C-13 |
| WTOP-03 | Kernel/IPC Service Worker | dedicated kernel I/O worker thread | Owns shared-channel ingress/egress arbitration and runtime boundary call servicing for hot paths. | Sends `KERNEL_IO_READY` after shared-channel self-check bootstrap. | Shared-channel lane unavailable or kernel service not ready before runtime bootstrap gate. | SRG-03, SRG-05, SRG-08 | C-01, C-03, C-04, C-08 |
| WTOP-04 | Storage Durability Worker | dedicated storage worker thread | Owns OPFS + SyncAccessHandle operations and persistence metadata mutation boundaries. | Sends `STORAGE_READY` after OPFS directory + SyncAccessHandle probes complete. | OPFS/SyncAccessHandle probe failure or storage role not ready before runtime entry. | SRG-06, SRG-07, SRG-10 | C-10, C-11, C-12, C-14 |
| WTOP-05 | UI Bridge Mediation Worker | dedicated bridge worker thread (UI-capable lanes only) | Owns runtime/UI shared-channel mediation for hot-path class routing in browser-capable lanes. | Sends `UI_BRIDGE_READY` when required shared-channel route classes are initialized. | UI-capable lane selected but bridge role not ready before UI bootstrap. | SRG-05, SRG-09 | C-05, C-09, C-13 |

### Required Role Set by Lane Class

| lane_class | required topology IDs | startup invariant |
| --- | --- | --- |
| `headless_runtime` | WTOP-01, WTOP-02, WTOP-03, WTOP-04 | Startup must fail if any required role is missing; no degraded mode allowed. |
| `ui_runtime` | WTOP-01, WTOP-02, WTOP-03, WTOP-04, WTOP-05 | Same strict fail semantics; UI lane cannot run without bridge mediation role. |

## Step 1 Output - Startup Sequence and Readiness Contract (v1)

Sequence IDs in this section are frozen for Step 1 and define deterministic worker bring-up order.

| sequence_id | phase | required operation | pass assertion | fail assertion |
| --- | --- | --- | --- | --- |
| WSEQ-01 | strict preflight | Run RPL-01 startup gate checks in fixed order before spawning runtime roles. | Startup summary `status=pass` and strict fields valid. | Any required-check fail aborts startup before worker launch continuation. |
| WSEQ-02 | storage bring-up | Launch WTOP-04 and complete OPFS/SyncAccessHandle readiness handshake. | `STORAGE_READY` received with probe metadata. | Missing/failed readiness triggers hard fail (`RPL01-E005`/linked gate code). |
| WSEQ-03 | kernel bring-up | Launch WTOP-03 and initialize shared-channel service boundary. | `KERNEL_IO_READY` received before runtime worker activation. | Missing readiness or transport init failure triggers hard fail. |
| WSEQ-04 | runtime bring-up | Launch WTOP-02 and verify runtime execution ownership claim. | `RUNTIME_READY` received and ownership boundary validated. | Runtime role not ready/ownership ambiguity triggers hard fail. |
| WSEQ-05 | lane-conditional bridge bring-up | For `ui_runtime`, launch WTOP-05 and verify required shared class routes. | `UI_BRIDGE_READY` received for UI-capable lane. | UI lane without bridge readiness triggers hard fail. |
| WSEQ-06 | topology commit | Emit topology readiness artifact and continue bootstrap only on `status=pass`. | Exactly one `worker_topology_ready_v1` terminal artifact emitted with full required role set. | Missing/invalid artifact or `status=fail` aborts startup continuation. |

### Topology Readiness Artifact (`worker_topology_ready_v1`)

| field | type | required | constraints / meaning |
| --- | --- | --- | --- |
| `schema_version` | string | yes | Must equal `worker_topology_ready_v1`. |
| `run_id` | string | yes | Startup attempt identifier; must align with startup-gate run. |
| `lane_class` | string | yes | `headless_runtime` or `ui_runtime`. |
| `required_roles` | array<string> | yes | Must exactly match required topology IDs for selected lane class. |
| `ready_roles` | array<string> | yes | Role IDs that completed readiness handshakes in observed order. |
| `startup_mode` | string | yes | Must equal `strict`. |
| `allow_fallback` | boolean | yes | Must be `false`. |
| `status` | string | yes | `pass` or `fail`. |
| `failure_role_id` | string/null | yes | Failed/missing role ID when `status=fail`; else `null`. |
| `failure_code` | string/null | yes | `RPL01-E005` or linked startup-gate failure code when `status=fail`; else `null`. |
| `message` | string | yes | Deterministic summary text describing topology outcome. |

## Step 2 Output - Worker Lifecycle and Failure-State Contract (v1)

Identifiers in this section are frozen for Step 2 and are normative inputs for dependency row `X-02`.

### Lifecycle State Model (Normative)

| lifecycle_state_id | state | entry condition | allowed exits | strict invariant |
| --- | --- | --- | --- | --- |
| WLCS-01 | `START_PENDING` | Role is required for selected lane class and has not been launched. | `WLCT-01`, `WLCT-10` | Required roles must not be skipped; lane must fail rather than omit role startup. |
| WLCS-02 | `STARTING` | Role launch issued; readiness handshake awaited. | `WLCT-02`, `WLCT-03`, `WLCT-10` | Startup timer and ownership checks are mandatory; no silent retries or fallback lanes. |
| WLCS-03 | `READY` | Readiness handshake passed and ownership boundary validated. | `WLCT-04`, `WLCT-09`, `WLCT-10`, `WLCT-11` | Role remains the sole owner of its boundary; ownership drift is fatal. |
| WLCS-04 | `DEGRADED` | Health watchdog or boundary probe indicates role health risk. | `WLCT-05`, `WLCT-06`, `WLCT-09`, `WLCT-10` | Degraded mode is transient only; must deterministically escalate to restart or fatal. |
| WLCS-05 | `RESTARTING` | Deterministic in-place restart attempt is active for a restartable role. | `WLCT-07`, `WLCT-08`, `WLCT-09`, `WLCT-10` | Restart occurs on same role identity only; no role substitution or lane downgrade. |
| WLCS-06 | `FATAL` | Terminal failure triggered by startup/runtime policy breach. | none | Terminal state; startup/runtime session must abort with `allow_fallback=false`. |

### Deterministic Transition Contract

| transition_id | from | to | trigger | deterministic guard | required action | failure-code semantics |
| --- | --- | --- | --- | --- | --- | --- |
| WLCT-01 | `START_PENDING` | `STARTING` | Role slot reached in fixed startup sequence (`WSEQ-*`). | Role ID is required for lane class and has no prior launch attempt. | Launch role worker and arm startup timeout from `WLCR-*`. | n/a |
| WLCT-02 | `STARTING` | `READY` | Readiness handshake received and parsed. | Handshake arrives before `startup_timeout_ms`; ownership probe passes. | Emit lifecycle pass event and continue startup sequence. | n/a |
| WLCT-03 | `STARTING` | `FATAL` | Startup handshake timeout or invalid payload. | `elapsed_ms > startup_timeout_ms` OR schema/role/version mismatch. | Abort startup immediately (first-failure semantics). | Must emit `RPL01-E005` with `WLCF-01` or `WLCF-02`. |
| WLCT-04 | `READY` | `DEGRADED` | Health watchdog breach detected. | `health_timeout_ms` exceeded or required probe misses threshold. | Emit degraded event and evaluate restart eligibility deterministically. | Emit `RPL02-L003` with `WLCF-03`. |
| WLCT-05 | `DEGRADED` | `RESTARTING` | Restart path selected. | `restart_attempt < restart_budget` for role per `WLCR-*`. | Restart same role ID; increment attempt counter. | n/a |
| WLCT-06 | `DEGRADED` | `FATAL` | Restart is disallowed or exhausted. | `restart_budget = 0` OR `restart_attempt >= restart_budget`. | Terminate lane/session; do not downgrade capabilities or topology. | Emit `RPL02-L004` with `WLCF-04`. |
| WLCT-07 | `RESTARTING` | `READY` | Replacement instance handshake passes. | Handshake + ownership probe pass within `restart_timeout_ms`. | Emit restart-success event and clear degraded condition. | n/a |
| WLCT-08 | `RESTARTING` | `FATAL` | Restart handshake timeout/failure. | Timeout or handshake invalid after bounded restart attempt. | Terminate lane/session immediately. | Emit `RPL02-L001` or `RPL02-L002`. |
| WLCT-09 | `READY`/`DEGRADED`/`RESTARTING` | `FATAL` | Ownership-boundary violation. | Runtime detects execution/service/storage/bridge ownership outside `WTOP-*` boundaries. | Immediate fatal termination; restart not permitted. | Emit `RPL02-L005` with `WLCF-05` (`RPL01-E005` if during startup window). |
| WLCT-10 | any non-`FATAL` | `FATAL` | Fallback policy violation. | Any attempt to switch to main-thread execution, lane downgrade, or legacy copy-path substitution. | Immediate policy-fail termination. | Emit `RPL02-L006` with `WLCF-06` (`RPL01-E005` if during startup window). |
| WLCT-11 | `READY` | `FATAL` | Lane-role invariant breach. | Required role set no longer matches selected lane class. | Abort lane/session; require clean restart. | Emit `RPL02-L007` with `WLCF-07` (`RPL01-E005` if during startup window). |

### Role-Level Restart/Fatal Policy (Normative)

| role_policy_id | topology_id | lane applicability | startup_timeout_ms | health_timeout_ms | restart_budget | restart_timeout_ms | deterministic fatal rule | linked contradictions |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WLCR-01 | WTOP-01 | `headless_runtime`, `ui_runtime` | 1200 | 1200 | 0 | n/a | Any degraded or ownership/fallback breach escalates directly to `WLCS-06`. | C-02, C-04, C-06, C-13 |
| WLCR-02 | WTOP-02 | `headless_runtime`, `ui_runtime` | 4000 | 1500 | 0 | n/a | Runtime execution ownership breaches or health failure are terminal; no restart substitution is allowed. | C-02, C-04, C-06, C-08, C-13 |
| WLCR-03 | WTOP-03 | `headless_runtime`, `ui_runtime` | 2500 | 1500 | 1 | 2000 | Exactly one restart attempt permitted; any second failure escalates to fatal. | C-01, C-03, C-04, C-08 |
| WLCR-04 | WTOP-04 | `headless_runtime`, `ui_runtime` | 5000 | 2000 | 0 | n/a | Storage durability failures are terminal; no in-memory or non-OPFS fallback allowed. | C-10, C-11, C-12, C-14 |
| WLCR-05 | WTOP-05 | `ui_runtime` only | 2500 | 1500 | 1 | 2000 | One restart attempt allowed in UI lane; lane mismatch or repeat failure is fatal. | C-05, C-09, C-13 |

### Failure Reason and Code Mapping

| failure_reason_id | condition | startup-window code | post-startup code | mandated response |
| --- | --- | --- | --- | --- |
| WLCF-01 | Startup/restart readiness timeout | `RPL01-E005` | `RPL02-L001` | Escalate to `WLCS-06`; abort lane/session with no fallback. |
| WLCF-02 | Invalid readiness handshake payload | `RPL01-E005` | `RPL02-L002` | Escalate to `WLCS-06`; abort lane/session with no fallback. |
| WLCF-03 | Health watchdog timeout/probe stall | n/a | `RPL02-L003` | Enter degraded then follow `WLCT-05`/`WLCT-06` deterministically. |
| WLCF-04 | Restart budget exhausted | n/a | `RPL02-L004` | Escalate to `WLCS-06`; no additional restart attempts. |
| WLCF-05 | Ownership boundary violation | `RPL01-E005` | `RPL02-L005` | Immediate fatal termination; restart not allowed. |
| WLCF-06 | No-fallback policy violation | `RPL01-E005` | `RPL02-L006` | Immediate fatal termination; treat as policy error. |
| WLCF-07 | Lane-role invariant mismatch | `RPL01-E005` | `RPL02-L007` | Immediate fatal termination; require clean startup retry. |

### Lifecycle Telemetry Artifacts

`worker_lifecycle_event_v1` (per-transition event) and `worker_lifecycle_summary_v1` (single terminal summary) are required for deterministic test-lane assertions.

| field | type | required | constraints / meaning |
| --- | --- | --- | --- |
| `schema_version` | string | yes | `worker_lifecycle_event_v1` or `worker_lifecycle_summary_v1`. |
| `run_id` | string | yes | Must match startup/topology run identifiers. |
| `lane_class` | string | yes | `headless_runtime` or `ui_runtime`. |
| `role_id` | string/null | yes | Required for event records; `null` only for terminal summary. |
| `transition_id` | string/null | yes | Required for events (`WLCT-*`); summary uses `null`. |
| `from_state` | string/null | yes | Required for events; summary uses `null`. |
| `to_state` | string/null | yes | Required for events; summary uses `null`. |
| `failure_reason_id` | string/null | yes | `WLCF-*` when failing transition/summary exists; else `null`. |
| `failure_code` | string/null | yes | `RPL01-E005` or `RPL02-L00*` when failing; else `null`. |
| `restart_attempt` | integer | yes | Monotonic per role; `0` when no restart attempted. |
| `restart_budget` | integer | yes | Must match role policy from `WLCR-*`. |
| `allow_fallback` | boolean | yes | Must always be `false`. |
| `terminal` | boolean | yes | `true` only for fatal transition events and terminal summary. |
| `status` | string | yes | `pass`/`fail` for summary; event records use `transition`. |
| `message` | string | yes | Deterministic, machine-parseable outcome text. |

## Step 3 Output - BPL-03 Consumption Mapping (v1)

Step 3 closure is satisfied by the explicit BPL-03 mapping package in `doc/wasm/backend-tickets/BPL-03-frame-and-debug-metadata-model.md`.

| mapping_class_id | RPL-02 runtime IDs consumed | BPL-03 consumption IDs | evidence location | closure assertion |
| --- | --- | --- | --- | --- |
| X03M-01 | `WTOP-01`..`WTOP-05` | `B3R-01`..`B3R-05` | BPL-03 Step 1 \"Worker Role Boundary Consumption\" table | All required worker role boundaries are explicitly consumed by frame/debug ownership rules. |
| X03M-02 | `WSEQ-01`..`WSEQ-06` | `B3S-01`..`B3S-06` | BPL-03 Step 1 \"Startup Sequence Consumption\" table | Startup-order constraints are explicitly consumed as frame/debug capture gates. |
| X03M-03 | `WLCS-01`..`WLCS-06` | `B3L-01`..`B3L-06` | BPL-03 Step 1 \"Lifecycle State Consumption\" table | Lifecycle-state semantics are explicitly consumed as frame/debug validity-state rules. |
| X03M-04 | `WLCT-01`..`WLCT-11` | `B3T-01`..`B3T-11` | BPL-03 Step 1 \"Lifecycle Transition Consumption\" table | Transition semantics are explicitly consumed as deterministic frame/debug transition hooks. |
| X03M-05 | `WLCR-01`..`WLCR-05` | `B3P-01`..`B3P-05` | BPL-03 Step 1 \"Role Policy Consumption\" table | Role-level restart/fatal policies are explicitly consumed as debug-policy boundary rules. |

Step 3 normative closure checks:

1. All required RPL-02 ID classes are explicitly consumed by BPL-03 mapping IDs.
2. Mapping rows include deterministic rules plus machine-test assertions.
3. No alias/rename drift was introduced for frozen RPL-02 identifiers.

## Step 1/Step 2 Output - `X-02` Readiness Package (v2)

| readiness_id | output supplied for BPL-03 | evidence location | clear-condition relevance |
| --- | --- | --- | --- |
| X02R-01 | Worker ownership boundary map for runtime/kernel/storage/bridge roles | `WTOP-01`..`WTOP-05` table in this ticket | Supplies required ownership/role boundaries for BPL-03 frame/debug mapping. |
| X02R-02 | Deterministic startup ordering and lane-class role requirements | `WSEQ-01`..`WSEQ-06` + lane-class table in this ticket | Constrains when debug/frame capture points can be validly assumed. |
| X02R-03 | Machine-actionable topology readiness artifact schema | `worker_topology_ready_v1` field table | Enables deterministic harness assertions around topology availability for BPL-03 consumers. |
| X02R-04 | Deterministic lifecycle state machine and transition contract | `WLCS-01`..`WLCS-06` and `WLCT-01`..`WLCT-11` in this ticket | Constrains role-state evolution and failure escalation used by BPL-03 frame/debug assumptions. |
| X02R-05 | Role-level restart/fatal policy under strict no-fallback semantics | `WLCR-01`..`WLCR-05` and `WLCF-01`..`WLCF-07` in this ticket | Provides machine-actionable role failure behavior for debug boundary mapping. |
| X02R-06 | Lifecycle event/summary telemetry schema for deterministic harness checks | `worker_lifecycle_event_v1` and `worker_lifecycle_summary_v1` field table | Enables test-lane validation that lifecycle behavior matches runtime/frame modeling assumptions. |
| X02R-07 | Explicit BPL-03 consumption mapping package | `X03M-01`..`X03M-05` in this ticket and `B3R-*`/`B3S-*`/`B3L-*`/`B3T-*`/`B3P-*` tables in BPL-03 ticket | Provides direct proof that all required runtime IDs are consumed by BPL-03 frame/debug modeling artifacts. |

`X-02` clear criteria are now satisfied: BPL-03 now explicitly maps Step 1 and Step 2 outputs into frame/debug boundary rules.

## Detailed Work Breakdown

### Step 1 - Worker Topology Definition

- Status: done
- Notes:
  - Step 1 output now defines role topology (`WTOP-01`..`WTOP-05`) with explicit ownership boundaries.
  - Startup sequence (`WSEQ-01`..`WSEQ-06`) and topology readiness artifact schema are now frozen.
  - `X-02` readiness package is now published for BPL-03 consumption.
- Next:
  - Keep `WTOP-*` and `WSEQ-*` identifiers frozen for downstream consumers.

### Step 2 - Worker Lifecycle and Failure-State Contract

- Status: done
- Notes:
  - Step 2 output now defines lifecycle state IDs (`WLCS-*`) and deterministic transition IDs (`WLCT-*`).
  - Role restart/fatal policies (`WLCR-*`) and failure-code mappings (`WLCF-*`, `RPL02-L00*`) are now frozen.
  - Startup-window failures remain aligned with first-failure semantics through `RPL01-E005`.
- Next:
  - Keep lifecycle IDs frozen for downstream consumers.

### Step 3 - Cross-Track Mapping and Sync

- Status: done
- Notes:
  - Explicit BPL-03 consumption mapping is now published and synchronized (`X03M-01`..`X03M-05`, `B3R-*`/`B3S-*`/`B3L-*`/`B3T-*`/`B3P-*`).
  - Dependency row `X-02` clear evidence is now complete and can be marked `done`.
- Next:
  - Handoff complete; maintain frozen IDs and apply additive-only changes if future revisions are required.

## Test and Validation Plan

- Topology validation:
  - Verify lane-class role requirements are complete and deterministic.
- Readiness validation:
  - Verify `worker_topology_ready_v1` schema is sufficient for machine assertions.
- Lifecycle validation:
  - Verify transition traces (`WLCT-*`) and failure-code emissions (`RPL01-E005`, `RPL02-L00*`) are deterministic per `WLCR-*` budgets.
- Cross-track validation:
  - Verify dependency matrix `X-02` notes reference Step 1 + Step 2 outputs and explicit BPL-03 consumption mappings (`B3R-*`/`B3S-*`/`B3L-*`/`B3T-*`/`B3P-*`).

## Risks and Mitigations

- Risk: ambiguous role ownership causes execution/debug boundary drift.
  - Mitigation: freeze role IDs with explicit ownership and startup handshake requirements.
- Risk: lifecycle semantics diverge from strict startup policy.
  - Mitigation: require Step 2 transitions to preserve `allow_fallback=false`.
- Risk: `X-02` appears complete without BPL-03 consumption.
  - Mitigation: preserve explicit mapping evidence links in both RPL-02 and BPL-03 tickets and keep IDs frozen.

## Change Log

- 2026-02-09: Initial RPL-02 subplan created with Step 1 worker-topology output (`WTOP-01`..`WTOP-05`, `WSEQ-01`..`WSEQ-06`) and `X-02` readiness package.
- 2026-02-09: Synced Step 1 readiness publication into dependency-matrix state by advancing `X-02` to `in_progress` and keeping Step 2 lifecycle contract as the single immediate next action.
- 2026-02-09: Executed Step 2 by publishing deterministic lifecycle/failure-state contract (`WLCS-*`, `WLCT-*`, `WLCR-*`, `WLCF-*`) with strict no-fallback enforcement and Step 3 cross-track mapping as the next action.
- 2026-02-09: Executed Step 3 by publishing explicit BPL-03 consumption mapping (`X03M-*` -> `B3*`) for `WTOP-*`, `WSEQ-*`, `WLCS-*`, `WLCT-*`, and `WLCR-*`, satisfying `X-02` clear evidence.
