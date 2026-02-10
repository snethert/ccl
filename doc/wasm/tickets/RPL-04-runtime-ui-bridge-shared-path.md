# RPL-04 - Runtime/UI Bridge Shared Path

Status: done  
Priority: P0  
Owner: Runtime/WASM replacement track  
Last Updated: 2026-02-10  
Parent Plan: `doc/wasm/runtime-replacement-master-plan.md`

## Scope

In scope:

- Define the deterministic migration scope for runtime/UI bridge traffic from message transport to shared-memory channels.
- Freeze runtime/UI message-class inventory and hot-path classification.
- Bind ingress/egress class routing to frozen IPC protocol constraints (`IPCP-*`) and worker ownership/lifecycle constraints (`WTOP-*`, `WSEQ-*`, `WLCT-*`).
- Define ordering, backpressure, failure, telemetry, and rollback contracts for partial migration.

Out of scope:

- Implementing bridge transport code changes.
- Redefining RPL-03 IPC protocol IDs or RPL-02 worker/lifecycle IDs.
- Storage V2 and module-sharing work (`RPL-05+`).
- CL thread semantics changes (remain deferred).

## Dependencies

- RPL-00 governance sync discipline.
- RPL-01 startup/no-fallback contracts (`SRG-09`, `SRG-11`, `SRG-12`) and contradiction follow-through (`C-01`, `C-03`, `C-04`, `C-08`, `C-09`).
- RPL-02 worker topology and lifecycle constraints (`WTOP-*`, `WSEQ-*`, `WLCS-*`, `WLCT-*`, `WLCR-*`).
- RPL-03 frozen IPC baseline (`IPCP-*`, `IPCV-*`, `IPCL-*`) with committed rerun evidence.
- Dependency matrix row `X-04` (runtime/backend parallel checkpoint).

## Deliverables

1. Step 1 migration-scope contract with frozen IDs (`R4M-*`, `R4C-*`, `R4T-*`).
2. Step 2 execution and lane-validation plan consuming Step 1 contracts and BPL-06 Step 3 artifacts.
3. Step 3 evidence package and `X-04` closure recommendation.

## Exit Criteria

- Runtime/UI message classes are fully classified as hot-path or non-hot-path with deterministic migration state.
- Shared-channel routing is explicitly mapped to `IPCP-*` and worker ownership/lifecycle boundaries.
- No-silent-fallback semantics are explicit for all hot-path classes.
- Test-lane telemetry schemas and rollback/remediation contracts are machine-actionable.

## Current Notes

- This subplan is newly created; Step 1 scope contract is published in this document.
- Step 1 freezes `R4M-*`/`R4C-*`/`R4T-*` IDs as additive-only identifiers.
- Step 2 execution/gating contract is now published with frozen lane/validation/compatibility IDs (`R4L-*`, `R4V-*`, `R4I-*`).
- Step 3 run-v1 evidence is now committed at `doc/wasm/tickets/evidence/rpl-04-step3-2026-02-09/` with baseline/fail-lane command outcomes and explicit blocker gaps (`R4GAP-01`..`R4GAP-04`).
- Step 3 rerun evidence is now committed at `doc/wasm/tickets/evidence/rpl-04-step3-rerun-2026-02-10/` with full `R4V-01`..`R4V-14` coverage, native bridge-schema emission, and terminal `runtime_ui_bridge_step2_summary_v1.status=pass`.
- Blocking gaps `R4GAP-01`..`R4GAP-04` are now closed; compatibility verdicts for `R4I-01`..`R4I-06` are explicit (`accept`) and non-pending.
- Backend parallel track has closed BPL-06 Step 3 and advanced to BPL-07 Step 1; `X-04` compatibility intake for this ticket remains anchored to frozen `BPL06-*` IDs.
- Hot-path routing policy is now explicitly shared-memory-only, aligned with `IPCP-02`, `IPCP-29`, and `IPCP-47`.
- Runtime thread capability remains required now; CL thread semantics remain deferred.
- `C-01`/`C-03`/`C-04`/`C-08` remain in-progress contradiction follow-through items; this ticket consumes their IPC baseline without reopening IDs.

## Immediate Next Step

- Action: keep RPL-04 outputs additive-only and consume the closed bridge baseline (`R4M-*`, `R4C-*`, `R4T-*`, `R4L-*`, `R4V-*`, `R4I-*`) from downstream runtime/backend tickets.
- Why now: Step 3 rerun closure evidence is committed and `X-04` closure recommendation is satisfied; follow-on work should consume this baseline instead of reopening bridge scope contracts.
- Success evidence: dependency row `X-04` remains `done`, downstream docs reference `rpl-04-step3-rerun-2026-02-10` artifacts directly, and no frozen IDs are renamed/reopened.

## Step 1 Output - Runtime/UI Bridge Shared-Path Scope Contract (v1)

### ID Namespace Freeze (Normative)

| namespace | frozen range | meaning | mutation rule |
| --- | --- | --- | --- |
| `R4M-*` | `R4M-01`..`R4M-26` | Message-class inventory and migration sequencing clauses. | Additive-only; existing IDs are immutable. |
| `R4C-*` | `R4C-01`..`R4C-28` | Channel mapping, ordering/backpressure/failure semantics, and rollback/remediation clauses. | Additive-only; existing IDs are immutable. |
| `R4T-*` | `R4T-01`..`R4T-10` | Telemetry schema contracts and required test-lane assertions. | Additive-only; existing IDs are immutable. |

### Runtime/UI Message-Class Inventory (Hot-Path vs Non-Hot-Path)

| class_id | class name | direction | source operation / kind | hot-path class | Step 1 migration state | required transport posture |
| --- | --- | --- | --- | --- | --- | --- |
| R4M-01 | `ui.input.pointer_wheel_batch` | ingress (UI -> runtime) | `KERNEL_OP_UI_POLL` pointer/wheel event records | yes | scoped | Shared ring required in `ui_runtime`; message lane forbidden for production hot path. |
| R4M-02 | `ui.input.key_text_composition_batch` | ingress (UI -> runtime) | `KERNEL_OP_UI_POLL` key/text/composition/focus/blur records | yes | scoped | Shared ring required in `ui_runtime`; message lane forbidden for production hot path. |
| R4M-03 | `ui.command.invoke` | ingress (UI -> runtime) | `command.invoke` envelope | yes | scoped | Shared ring required in `ui_runtime`; policy-fail on fallback attempt. |
| R4M-04 | `runtime.output.stream` | egress (runtime -> UI) | `runtime.output` envelope | yes | scoped | Shared ring required for streaming output events. |
| R4M-05 | `runtime.command.result_error` | egress (runtime -> UI) | `command.result`, `command.error` envelopes | yes | scoped | Shared ring required; request/response correlation must be preserved. |
| R4M-06 | `runtime.ui.render_patch` | egress (runtime -> UI backend) | `KERNEL_OP_UI_RENDER` payloads | yes | scoped | Shared ring required for render hot path in replacement lane. |
| R4M-07 | `runtime.ui.measure_text` | bidirectional | `KERNEL_OP_UI_MEASURE_TEXT` request/response flow | yes | scoped | Shared ring pair required; bounded wait and deterministic fail mapping. |
| R4M-08 | `runtime.debugger.snapshot` | egress (runtime -> UI) | `debugger.snapshot` envelope | no | scoped | Control/message lane allowed in Step 1; must remain explicitly non-hot. |
| R4M-09 | `runtime.debugger.restart` | ingress + egress | `debugger.restart` envelope | no | scoped | Control/message lane allowed in Step 1; no implicit hot-path promotion. |
| R4M-10 | `runtime.inspector.update` | ingress + egress | `inspector.update` envelope | no | scoped | Control/message lane allowed in Step 1; route class tagging required. |
| R4M-11 | `runtime.job.update` | egress (runtime -> UI) | `job.update` envelope | no | scoped | Control/message lane allowed in Step 1. |
| R4M-12 | `runtime.log.diagnostic` | egress (runtime -> UI) | `runtime.log` envelope | no | scoped | Control/message lane allowed in Step 1; never treated as hot path. |
| R4M-13 | `bridge.control.health` | ingress + egress | bridge heartbeat, readiness, and control metadata | no | scoped | Mailbox/control path only; no runtime payload streaming on this class. |

### Ingress/Egress Migration Scope and Sequencing (Normative)

| sequence_id | migration wave | direction focus | included class IDs | hard prerequisites | deterministic completion condition |
| --- | --- | --- | --- | --- | --- |
| R4M-20 | Step 1 baseline freeze | both | `R4M-01`..`R4M-13` | RPL-03 rerun evidence committed; `X-03=done` | Inventory, mappings, telemetry schemas, and rollback clauses are all published and frozen. |
| R4M-21 | Wave A ingress hot-path migration | ingress | `R4M-01`, `R4M-02`, `R4M-03` | `WSEQ-05` bridge readiness, `IPCP-07`, `IPCP-44` lane checks | Ingress hot classes emit shared-ring route events only; any message-route attempt fails deterministically. |
| R4M-22 | Wave B egress hot-path migration | egress | `R4M-04`, `R4M-05` | `WSEQ-05`, `IPCP-08`, `IPCP-29` no-fallback | Output and command result/error classes emit shared-ring route events only. |
| R4M-23 | Wave C UI backend data-plane migration | egress + ingress | `R4M-06`, `R4M-07` | `IPCP-07`, `IPCP-08`, `IPCP-24`..`IPCP-27` backpressure clauses | Render/measure lanes pass bounded-wait and correlation assertions with canonical failure codes. |
| R4M-24 | Wave D non-hot class retention (explicit) | both | `R4M-08`..`R4M-13` | Class tagging + telemetry assertions (`R4T-06`, `R4T-07`) | Non-hot classes remain control/message lane with explicit non-hot annotation and no hidden hot-path use. |
| R4M-25 | Wave E hardening | both | `R4M-01`..`R4M-07` | `R4M-21`..`R4M-23` complete | Hot-path legacy message route handlers are blocked by policy with terminal failure semantics. |
| R4M-26 | Wave F integration checkpoint | both | all Step 1 classes | `R4M-24` + `R4M-25`; matrix `X-04=in_progress` | Step 2 publishes command/evidence lanes proving class-level transport posture and BPL-06 compatibility intake. |

### Channel Mapping to `IPCP-*` Constraints and Worker Ownership Boundaries

| mapping_id | class IDs | primary channel(s) | writer -> reader ownership | startup/lifecycle gates | protocol constraints consumed |
| --- | --- | --- | --- | --- | --- |
| R4C-01 | `R4M-01`, `R4M-02` | `ipc.ui.req.ring.v1` | `WTOP-05` -> `WTOP-02` | `WSEQ-05`, `WLCT-11` | `IPCP-07`, `IPCP-18`, `IPCP-20`, `IPCP-44` |
| R4C-02 | `R4M-03` | `ipc.ui.req.ring.v1` | `WTOP-05` -> `WTOP-02` | `WSEQ-05`, `WLCT-09`, `WLCT-10` | `IPCP-07`, `IPCP-29`, `IPCP-31`, `IPCP-47` |
| R4C-03 | `R4M-04`, `R4M-05` | `ipc.ui.resp.ring.v1` | `WTOP-02` -> `WTOP-05` | `WSEQ-05`, `WLCT-09`, `WLCT-10` | `IPCP-08`, `IPCP-18`, `IPCP-29`, `IPCP-31`, `IPCP-47` |
| R4C-04 | `R4M-06` | `ipc.ui.resp.ring.v1` | `WTOP-02` -> `WTOP-05` | `WSEQ-05`, `WLCT-04`..`WLCT-06` | `IPCP-08`, `IPCP-24`, `IPCP-27`, `IPCP-49` |
| R4C-05 | `R4M-07` | `ipc.ui.resp.ring.v1` + `ipc.ui.req.ring.v1` | request: `WTOP-02` -> `WTOP-05`; response: `WTOP-05` -> `WTOP-02` | `WSEQ-05`, `WLCT-09`, `WLCT-11` | `IPCP-07`, `IPCP-08`, `IPCP-23`, `IPCP-39`, `IPCP-48` |
| R4C-06 | `R4M-08`, `R4M-09`, `R4M-10` | control/message lane + mailbox readiness | runtime-bridge owner roles remain `WTOP-02`/`WTOP-05` | `WSEQ-05`, `WLCT-11` | `IPCP-09`, `IPCP-10`, `IPCP-44` |
| R4C-07 | `R4M-11`, `R4M-12` | control/message lane | `WTOP-02` -> `WTOP-05` | `WSEQ-05` | `IPCP-09`, `IPCP-10` |
| R4C-08 | `R4M-13` | bootstrap/control mailbox | `WTOP-01` <-> `WTOP-05` | `WSEQ-01`..`WSEQ-06`, `WLCT-03` | `IPCP-09`, `IPCP-10`, `IPCP-41`, `IPCP-45` |
| R4C-09 | headless-lane exclusion for UI classes | none (`ui_runtime` only) | n/a | `WLCT-11` terminal on mismatch | `IPCP-44`, `IPCP-48`, `RPL03-E010` |
| R4C-10 | hot-path no-fallback enforcement | all hot classes (`R4M-01`..`R4M-07`) | per-class ownership above | `WLCT-10` terminal on violation | `IPCP-02`, `IPCP-29`, `IPCP-47`, `RPL03-E008` |

### Ordering, Backpressure, and Failure Semantics (No Silent Fallback)

| semantics_id | applies to | deterministic ordering rule | backpressure rule | canonical failure mapping | required terminal behavior |
| --- | --- | --- | --- | --- | --- |
| R4C-11 | `R4M-01`..`R4M-07` | Preserve per-channel FIFO using ring sequence/index monotonicity. | Producer/consumer waits must follow bounded wait semantics. | `RPL03-E003`, `RPL03-E005` | Escalate via `WLCT-*`; no silent drop. |
| R4C-12 | `R4M-03`, `R4M-05`, `R4M-07` | `correlation_id` pairing is mandatory and monotonic per request stream. | Missing response beyond timeout budget is failure. | `RPL03-E004`, `RPL03-E009` | Emit fail artifact and escalate deterministically. |
| R4C-13 | all hot classes | Any attempt to route to message/copy hot lane is forbidden. | No alternate hot-lane redirection is permitted. | `RPL03-E008` | Immediate terminal transition through `WLCT-10`. |
| R4C-14 | `R4M-01`..`R4M-07` | Role ownership (`WTOP-*`) is single-writer/single-reader per channel. | Ownership contention does not trigger retries with alternate roles. | `RPL03-E002` | Immediate fatal via `WLCT-09`. |
| R4C-15 | `R4M-01`..`R4M-07` | Lane class must match route class (`ui_runtime` required). | Lane mismatch is not recoverable by route downgrade. | `RPL03-E010` | Immediate fatal via `WLCT-11`. |
| R4C-16 | `R4M-04`, `R4M-06` | Runtime egress ordering must preserve emitted `seq` progression. | Ring-full timeout is failure, not buffering into message lane. | `RPL03-E003` | Degraded/restart/fatal per `WLCR-05` and `WLCT-04`..`WLCT-06`. |
| R4C-17 | `R4M-01`, `R4M-02` | UI ingress event ordering must remain stable within each batch stream. | Bounded wait only; no event drop/merge for overflow recovery. | `RPL03-E003`, `RPL03-E005` | Fail lane and surface class ID + sequence evidence. |
| R4C-18 | `R4M-08`..`R4M-13` | Non-hot classes may remain message/control lane with explicit class tags. | Control-lane saturation uses explicit fail signaling; no hidden promotion to hot lane. | `RPL03-E004`, `RPL03-E009` | Emit control-lane failure artifact; class remains non-hot. |
| R4C-19 | startup usage of bridge channels | Channel use before readiness checkpoints is forbidden. | Waits before readiness are treated as gate violations. | `RPL03-E007` | Startup hard-fail via `WLCT-03`. |
| R4C-20 | schema/route metadata | Missing class metadata in route event is invalid. | Invalid telemetry cannot be ignored in conformance lanes. | `RPL03-E007` | Fail conformance lane; require remediation before promotion. |

### Telemetry Artifacts and Schemas Required for Test-Lane Assertions

| telemetry_id | schema | artifact granularity | required fields | purpose |
| --- | --- | --- | --- | --- |
| R4T-01 | `runtime_ui_bridge_route_event_v1` | per routed message | `run_id`, `class_id`, `direction`, `lane_class`, `selected_lane`, `channel_id`, `writer_role_id`, `reader_role_id`, `sequence_no`, `correlation_id`, `status`, `failure_code`, `fallback_attempted`, `fallback_blocked` | Deterministic route-level assertions for hot/non-hot classification and ownership. |
| R4T-02 | `runtime_ui_bridge_backpressure_event_v1` | per wait/timeout event | `run_id`, `class_id`, `channel_id`, `wait_state`, `wait_ms`, `timeout_ms`, `occupancy`, `status`, `failure_code`, `transition_id` | Backpressure and bounded-wait assertions tied to `IPCP-24`..`IPCP-27`. |
| R4T-03 | `runtime_ui_bridge_lane_summary_v1` | per class per lane | `run_id`, `class_id`, `hot_path_class`, `selected_lane`, `events_total`, `events_failed`, `first_failure_code`, `allow_hotpath_fallback`, `results_digest` | Class-level rollup for pass/fail gates and no-fallback proof. |
| R4T-04 | `runtime_ui_bridge_migration_summary_v1` | one terminal record per run | `run_id`, `wave_id`, `executed_class_ids`, `hot_classes_on_shared_count`, `non_hot_on_control_count`, `policy_failures`, `status`, `x04_ready`, `timestamp_utc` | Migration-wave completion and `X-04` readiness assertion input. |
| R4T-05 | `runtime_ui_bridge_rollback_record_v1` | one record per rollback action | `run_id`, `rollback_id`, `trigger_class_id`, `trigger_failure_code`, `applied_scope`, `operator_ack`, `post_rollback_status`, `evidence_paths` | Mandatory rollback audit trail for partial migration handling. |

### Required Test-Lane Assertions (Step 1 Freeze)

| assertion_id | assertion | success condition | failure condition |
| --- | --- | --- | --- |
| R4T-06 | Hot classes never use message lane | For `R4M-01`..`R4M-07`, `selected_lane=shared_ring_v1` in `R4T-01`/`R4T-03`. | Any hot class event with `selected_lane=message_control_v1`. |
| R4T-07 | Non-hot classes remain explicitly tagged | For `R4M-08`..`R4M-13`, `hot_path_class=false` and class tags present in all records. | Missing class tags or accidental hot-path tagging drift. |
| R4T-08 | Backpressure semantics are deterministic | Timeout/wait events use canonical codes and transition IDs in `R4T-02`. | Missing/incorrect `failure_code` or `transition_id` mapping. |
| R4T-09 | Lane-role mismatch is terminal | Any mismatch emits `RPL03-E010` and terminal transition (`WLCT-11`). | Mismatch handled by downgrade or warning-only behavior. |
| R4T-10 | Rollback actions are fully auditable | Every rollback has one `R4T-05` record with evidence paths. | Rollback without audit artifact or scope declaration. |

### Rollback and Remediation Contract for Partial Migration

| rollback_id | partial migration condition | mandatory response | prohibited response | evidence artifact requirement |
| --- | --- | --- | --- | --- |
| R4C-21 | Required hot class (`R4M-01`..`R4M-07`) lacks shared-channel mapping at startup | Abort startup as unsupported replacement lane. | Auto-routing hot class to message lane. | `R4T-04.status=fail` with startup gate linkage (`SRG-09`). |
| R4C-22 | Runtime observes hot-class fallback attempt | Trigger terminal policy failure and stop lane/session. | Silent continue after fallback route selection. | `R4T-01` fail event + `R4T-05` rollback record. |
| R4C-23 | Repeated ring-full/wait timeout on hot class beyond policy budget | Escalate through `WLCT-04`..`WLCT-06` and freeze affected wave. | Unbounded retry loops or event drops. | `R4T-02` timeout evidence + `R4T-04` wave status update. |
| R4C-24 | Ownership boundary violation or lane-role mismatch | Immediate fatal (`WLCT-09`/`WLCT-11`) and rollback record emission. | Ownership reassignment without restart. | `R4T-01` fail event + `R4T-05` record. |
| R4C-25 | Operator-initiated partial rollback | Apply explicit class-scope rollback manifest and perform clean restart. | In-place downgrade with no manifest/restart. | `R4T-05.applied_scope` must list exact `R4M-*` IDs. |
| R4C-26 | Rollback of one class group must not mutate unrelated groups | Keep unaffected class mappings unchanged and frozen. | Broad global reset that rewrites frozen mappings. | Pre/post route digests in `R4T-03` for affected and unaffected classes. |
| R4C-27 | Remediation closure after rollback | Re-run affected migration wave and lane assertions before status promotion. | Marking wave complete without rerun evidence. | New `R4T-04` pass summary + referenced route/backpressure artifacts. |
| R4C-28 | Cross-track compatibility after rollback/remediation | Update `X-04` notes with accepted/rejected scope and downstream impact. | Leaving matrix status stale after rollback outcome. | Matrix row update referencing `R4T-04`/`R4T-05` evidence IDs. |

### Step 1 Completion Status

- Status: done
- Gap IDs: none
- Completion basis:
  - Runtime/UI class inventory is complete and frozen.
  - Migration sequencing, channel mappings, semantics, telemetry, and rollback contracts are fully specified.
  - Contracts consume frozen `IPCP-*`, `WTOP-*`, `WSEQ-*`, and `WLCT-*` IDs without renaming/reopening them.

## Step 2 Output - Execution Lane and Compatibility Gate Contract (v1)

### Step 2 ID Namespace Freeze (Normative)

| namespace | frozen range | meaning | mutation rule |
| --- | --- | --- | --- |
| `R4L-*` | `R4L-01`..`R4L-06` | Bridge conformance lane registry for Step 3 execution. | Additive-only; existing IDs are immutable. |
| `R4V-*` | `R4V-01`..`R4V-14` | Deterministic validation/assertion matrix over migration waves and failure classes. | Additive-only; existing IDs are immutable. |
| `R4I-*` | `R4I-01`..`R4I-06` | Cross-track compatibility bindings to frozen BPL-06 triage/intake artifacts. | Additive-only; existing IDs are immutable. |

### Step 2 Execution Contract

1. Step 3 execution MUST run only frozen `R4L-*` lanes and record outcomes for frozen `R4V-*` validations.
2. Each run MUST emit `R4T-01`..`R4T-05` artifacts plus one terminal `runtime_ui_bridge_step2_summary_v1`.
3. Hot-path classes (`R4M-01`..`R4M-07`) MUST preserve strict no-fallback posture (`fallback_attempted=false`, `fallback_blocked=true` on policy tests).
4. Normative fail-injection controls:
   - `CCL_UI_BRIDGE_TEST_WAVE=<R4M-21|R4M-22|R4M-23|R4M-24|R4M-25|R4M-26>`
   - `CCL_UI_BRIDGE_TEST_CLASS_ID=<R4M-01..R4M-13>`
   - `CCL_UI_BRIDGE_TEST_INJECT_FAILURE=<RPL03-E002|RPL03-E003|RPL03-E007|RPL03-E008|RPL03-E010>`
   - `CCL_UI_BRIDGE_TEST_FORCE_FALLBACK=1`
5. If implementation uses different internal knobs, wrappers MUST expose equivalent controls for the four variables above.

### Conformance Lane Registry

| lane_id | command | lane_class | primary coverage |
| --- | --- | --- | --- |
| R4L-01 | `node doc/wasm/js/wasm-ui-persist-smoke.mjs --image root --verbose` | `ui_runtime` | Baseline wave coverage for ingress/egress hot-path classes and route/backpressure artifacts. |
| R4L-02 | `node doc/wasm/js/start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive` | `headless_runtime` | Control-lane and startup gating invariants, including non-hot class routing boundaries. |
| R4L-03 | `npm --prefix web-ui run test:sandbox` | `ui_runtime` | Browser harness assertions for lane-role ownership and fallback-blocking behavior. |
| R4L-04 | `node doc/wasm/js/all-smoke.mjs` | mixed | Aggregate regression lane ensuring bridge failures fail the suite deterministically. |
| R4L-05 | `CCL_UI_BRIDGE_TEST_INJECT_FAILURE=<code> CCL_UI_BRIDGE_TEST_CLASS_ID=<class> node doc/wasm/js/wasm-ui-persist-smoke.mjs --image root --verbose` | `ui_runtime` | Deterministic fail-lane coverage for canonical `RPL03-E*` mappings and `WLCT-*` escalation checks. |
| R4L-06 | `CCL_UI_BRIDGE_TEST_FORCE_FALLBACK=1 node doc/wasm/js/wasm-ui-persist-smoke.mjs --image root --verbose` | `ui_runtime` | Rollback/remediation rehearsal lane requiring policy-fail terminal path and rollback artifact emission. |

### Validation Matrix (`R4V-*`)

| validation_id | lane_id | wave / scope | command | deterministic assertions | BPL-06 bindings |
| --- | --- | --- | --- | --- | --- |
| R4V-01 | R4L-01 | Wave A (`R4M-21`) ingress hot-path | `CCL_UI_BRIDGE_TEST_WAVE=R4M-21 node doc/wasm/js/wasm-ui-persist-smoke.mjs --image root --verbose` | `R4M-01`/`R4M-02`/`R4M-03` route only to shared lanes; no fallback markers. | `R4I-01` |
| R4V-02 | R4L-01 | Wave B (`R4M-22`) egress hot-path | `CCL_UI_BRIDGE_TEST_WAVE=R4M-22 node doc/wasm/js/wasm-ui-persist-smoke.mjs --image root --verbose` | `R4M-04`/`R4M-05` shared-lane egress and correlation assertions hold. | `R4I-02` |
| R4V-03 | R4L-01 | Wave C (`R4M-23`) UI backend data plane | `CCL_UI_BRIDGE_TEST_WAVE=R4M-23 node doc/wasm/js/wasm-ui-persist-smoke.mjs --image root --verbose` | `R4M-06`/`R4M-07` satisfy bounded wait/correlation requirements with no policy drift. | `R4I-03` |
| R4V-04 | R4L-02 | Wave D (`R4M-24`) non-hot retention | `CCL_UI_BRIDGE_TEST_WAVE=R4M-24 node doc/wasm/js/start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive` | `R4M-08`..`R4M-13` remain non-hot and explicitly tagged control-lane traffic. | `R4I-04` |
| R4V-05 | R4L-03 | Wave E (`R4M-25`) hardening | `CCL_UI_BRIDGE_TEST_WAVE=R4M-25 npm --prefix web-ui run test:sandbox` | Browser lane blocks hot-path fallback and enforces lane-role ownership. | `R4I-05` |
| R4V-06 | R4L-04 | Wave F (`R4M-26`) integration checkpoint | `CCL_UI_BRIDGE_TEST_WAVE=R4M-26 node doc/wasm/js/all-smoke.mjs` | Aggregate lane emits terminal summary with class-level coverage and compatibility verdict fields. | `R4I-06` |
| R4V-07 | R4L-05 | deterministic fallback-policy fail | `CCL_UI_BRIDGE_TEST_INJECT_FAILURE=RPL03-E008 CCL_UI_BRIDGE_TEST_CLASS_ID=R4M-03 node doc/wasm/js/wasm-ui-persist-smoke.mjs --image root --verbose` | First failure code is `RPL03-E008`; escalation is `WLCT-10`; no downgrade lane selected. | `R4I-05` |
| R4V-08 | R4L-05 | deterministic lane-role mismatch fail | `CCL_UI_BRIDGE_TEST_INJECT_FAILURE=RPL03-E010 CCL_UI_BRIDGE_TEST_CLASS_ID=R4M-01 node doc/wasm/js/wasm-ui-persist-smoke.mjs --image root --verbose` | First failure code is `RPL03-E010`; escalation is `WLCT-11`. | `R4I-06` |
| R4V-09 | R4L-05 | deterministic ownership violation fail | `CCL_UI_BRIDGE_TEST_INJECT_FAILURE=RPL03-E002 CCL_UI_BRIDGE_TEST_CLASS_ID=R4M-05 node doc/wasm/js/wasm-ui-persist-smoke.mjs --image root --verbose` | First failure code is `RPL03-E002`; escalation is `WLCT-09`; ownership fields mismatch deterministically. | `R4I-02` |
| R4V-10 | R4L-05 | deterministic ring-full timeout fail | `CCL_UI_BRIDGE_TEST_INJECT_FAILURE=RPL03-E003 CCL_UI_BRIDGE_TEST_CLASS_ID=R4M-06 node doc/wasm/js/wasm-ui-persist-smoke.mjs --image root --verbose` | Timeout is surfaced with bounded-wait fields; lifecycle transition maps to `WLCT-04/05/06` per role policy. | `R4I-03` |
| R4V-11 | R4L-05 | deterministic metadata/schema fail | `CCL_UI_BRIDGE_TEST_INJECT_FAILURE=RPL03-E007 CCL_UI_BRIDGE_TEST_CLASS_ID=R4M-10 node doc/wasm/js/start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive` | Missing/invalid class metadata fails lane with canonical `RPL03-E007`. | `R4I-04` |
| R4V-12 | R4L-06 | rollback artifact emission | `CCL_UI_BRIDGE_TEST_FORCE_FALLBACK=1 node doc/wasm/js/wasm-ui-persist-smoke.mjs --image root --verbose` | Policy-fail path emits one rollback artifact `R4T-05` with scope and evidence paths. | `R4I-05` |
| R4V-13 | R4L-04 | severity-class compatibility assertion | `CCL_UI_BRIDGE_TEST_WAVE=R4M-26 node doc/wasm/js/all-smoke.mjs` | Terminal summary maps bridge failures to compatible `BPL06-SEV-*` class obligations. | `R4I-05` |
| R4V-14 | R4L-04 | intake-mapping compatibility assertion | `CCL_UI_BRIDGE_TEST_WAVE=R4M-26 node doc/wasm/js/all-smoke.mjs` | Terminal summary carries explicit accept/reject flags keyed to `BPL06-INT-*` requirements. | `R4I-06` |

### BPL-06 Compatibility Mapping (`R4I-*`)

| compatibility_id | RPL-04 scope | required BPL-06 IDs | acceptance rule | reject rule |
| --- | --- | --- | --- | --- |
| R4I-01 | Wave A ingress hot-path migration | `BPL06-CP01`, `BPL06-INT-01` | Ingress shared-lane assertions pass without fallback flags. | Any fallback/policy fail or missing route artifacts. |
| R4I-02 | Wave B egress hot-path migration | `BPL06-CP03`, `BPL06-INT-03` | Egress correlation/ownership assertions pass with deterministic summaries. | Ownership mismatch, helper-lane compatibility drift, or unresolved fail summary. |
| R4I-03 | Wave C data-plane migration | `BPL06-CP04`, `BPL06-INT-04` | Render/measure class assertions pass with bounded backpressure and frame/debug-safe output. | Timeout/ordering drift or unresolved strict-lane mismatch. |
| R4I-04 | Wave D non-hot retention | `BPL06-CP05` | Non-hot classes remain explicit control-lane traffic and do not pollute hot-path summary counts. | Any non-hot class promoted to shared hot-path scope without scope update. |
| R4I-05 | Wave E hardening + rollback semantics | `BPL06-SEV-01`..`BPL06-SEV-04`, `BPL06-RB-01`..`BPL06-RB-05` | Bridge failures map to severity/rollback obligations with replayable artifacts. | Severity/rollback class cannot be resolved from emitted bridge artifacts. |
| R4I-06 | Wave F integration checkpoint | `BPL06-INT-01`..`BPL06-INT-05` | Terminal summary includes per-intake acceptance flags and `x04_step2_ready=true`. | Any intake flag unresolved or summary missing required checkpoint references. |

### Step 2 Terminal Summary Schema (`runtime_ui_bridge_step2_summary_v1`)

| field | type | required | constraints / meaning |
| --- | --- | --- | --- |
| `schema_version` | string | yes | Must equal `runtime_ui_bridge_step2_summary_v1`. |
| `run_id` | string | yes | Shared identifier for one Step 2 lane execution set. |
| `executed_validation_ids` | array<string> | yes | Executed `R4V-*` IDs. |
| `passed_validation_ids` | array<string> | yes | Passing subset of `executed_validation_ids`. |
| `failed_validation_ids` | array<string> | yes | Failing subset of `executed_validation_ids`. |
| `first_failure_validation_id` | string/null | yes | First failing validation ID or `null`. |
| `first_failure_code` | string/null | yes | First canonical `RPL03-E*` code or `null`. |
| `compatibility_results` | array<object> | yes | One row per `R4I-*` with `status=accept|reject`. |
| `allow_hotpath_fallback` | boolean | yes | Must be `false`. |
| `x04_step2_ready` | boolean | yes | `true` only when required pass/fail assertions and compatibility mappings are complete. |
| `results_digest` | string | yes | Deterministic digest over all lane/validation artifacts. |
| `status` | string | yes | `pass` or `fail`. |

### Step 2 Readiness Assertions

1. Pass-set coverage (`R4V-01`..`R4V-06`) must succeed with expected lane outputs.
2. Fail-set coverage (`R4V-07`..`R4V-12`) must emit canonical first-failure `RPL03-E*` codes and mapped `WLCT-*` transitions.
3. Compatibility assertions (`R4V-13`, `R4V-14`) must produce explicit `R4I-*` accept/reject results.
4. All terminal summaries must preserve `allow_hotpath_fallback=false`.
5. `x04_step2_ready=true` requires complete artifact coverage and zero unresolved `R4I-*` mapping rows.

### Step 2 Completion Status

- Status: done
- Gap IDs: none
- Completion basis:
  - Step 2 lane registry, validation matrix, compatibility mapping, and terminal summary schema are fully specified.
  - Step 2 outputs are deterministic, additive-only, and directly mapped to frozen Step 1 and BPL-06 IDs.

## Step 3 Output - Initial Evidence Execution (run v1)

Evidence bundle path:

- `doc/wasm/tickets/evidence/rpl-04-step3-2026-02-09/r4v-results.tsv`
- `doc/wasm/tickets/evidence/rpl-04-step3-2026-02-09/runtime_ui_bridge_step2_summary_v1.draft.json`
- `doc/wasm/tickets/evidence/rpl-04-step3-2026-02-09/gap-register.md`
- `doc/wasm/tickets/evidence/rpl-04-step3-2026-02-09/logs/R4V-01.log` .. `doc/wasm/tickets/evidence/rpl-04-step3-2026-02-09/logs/R4V-11.log`

Run v1 coverage summary:

| class | status | notes |
| --- | --- | --- |
| baseline pass lanes (`R4V-01`, `R4V-04`, `R4V-06`) | pass | Commands exited `0`; terminal IPC summaries reported `status=pass`, `first_failure_code=null`. |
| deterministic fail lanes (`R4V-07`, `R4V-08`, `R4V-09`, `R4V-10`, `R4V-11`) | pass (expected fail behavior observed) | Commands exited non-zero with expected canonical `RPL03-E*` first-failure codes and lifecycle transitions. |
| remaining Step 2 rows (`R4V-02`, `R4V-03`, `R4V-05`, `R4V-12`, `R4V-13`, `R4V-14`) | blocked | Bridge-specific wrapper controls and bridge-specific summary artifacts are not yet emitted. |

Observed canonical fail mappings from run v1:

| validation_id | injected control used | expected first failure code | observed first failure code | result |
| --- | --- | --- | --- | --- |
| `R4V-07` | `CCL_IPC_TEST_INJECT_FAILURE=RPL03-E008` | `RPL03-E008` | `RPL03-E008` | match |
| `R4V-08` | `CCL_IPC_TEST_INJECT_FAILURE=RPL03-E010` + lane override | `RPL03-E010` | `RPL03-E010` | match |
| `R4V-09` | `CCL_IPC_TEST_INJECT_FAILURE=RPL03-E002` + channel override | `RPL03-E002` | `RPL03-E002` | match |
| `R4V-10` | `CCL_IPC_TEST_INJECT_FAILURE=RPL03-E003` + channel override | `RPL03-E003` | `RPL03-E003` | match |
| `R4V-11` | `CCL_IPC_TEST_INJECT_FAILURE=RPL03-E007` | `RPL03-E007` | `RPL03-E007` | match |

Gap register (`R4GAP-*`):

| gap_id | blocker | impact on Step 3 closure |
| --- | --- | --- |
| R4GAP-01 | `CCL_UI_BRIDGE_TEST_*` wrapper controls are not yet wired; only `CCL_IPC_TEST_*` controls are effective. | Blocks closure of bridge-specific validation rows that require class/wave wrapper control semantics. |
| R4GAP-02 | Bridge-specific telemetry schemas (`runtime_ui_bridge_route_event_v1`, `runtime_ui_bridge_backpressure_event_v1`, `runtime_ui_bridge_lane_summary_v1`, `runtime_ui_bridge_rollback_record_v1`) are not emitted by lanes. | Blocks `R4T-*` artifact assertions and class-level migration evidence. |
| R4GAP-03 | Terminal schema `runtime_ui_bridge_step2_summary_v1` is not emitted natively (only draft synthesis is available). | Blocks machine-actionable closure summary requirements. |
| R4GAP-04 | Compatibility verdict fields for `R4I-01`..`R4I-06` remain `pending` in run-v1 draft summary. | Blocks `X-04` closure recommendation. |

Run v1 Step 3 status:

- Status: in_progress
- Blocking gaps: `R4GAP-01`, `R4GAP-02`, `R4GAP-03`, `R4GAP-04`
- Closure readiness: not ready (`x04_step2_ready=false` in draft summary)

## Step 3 Output - Rerun Evidence Execution (run v2)

Evidence bundle path:

- `doc/wasm/tickets/evidence/rpl-04-step3-rerun-2026-02-10/r4v-results.tsv`
- `doc/wasm/tickets/evidence/rpl-04-step3-rerun-2026-02-10/runtime_ui_bridge_step2_summary_v1.json`
- `doc/wasm/tickets/evidence/rpl-04-step3-rerun-2026-02-10/assertion-report.md`
- `doc/wasm/tickets/evidence/rpl-04-step3-rerun-2026-02-10/gap-register.md`
- `doc/wasm/tickets/evidence/rpl-04-step3-rerun-2026-02-10/logs/R4V-01.log` .. `doc/wasm/tickets/evidence/rpl-04-step3-rerun-2026-02-10/logs/R4V-14.log`

Rerun v2 coverage summary:

| class | status | notes |
| --- | --- | --- |
| baseline pass lanes (`R4V-01`..`R4V-06`) | pass | Commands exited `0`; terminal bridge summaries emitted with `status=pass` and explicit non-pending compatibility rows. |
| deterministic fail lanes (`R4V-07`..`R4V-12`) | pass (expected fail behavior observed) | Commands exited non-zero with expected canonical first-failure `RPL03-E*` codes; rollback artifact emitted for `R4V-12`. |
| compatibility assertion lanes (`R4V-13`, `R4V-14`) | pass | Terminal summary includes explicit `R4I-*` verdicts and aggregate `x04_step2_ready=true`. |

Rerun v2 terminal summary (`runtime_ui_bridge_step2_summary_v1`):

| field | value |
| --- | --- |
| `status` | `pass` |
| `executed_validation_ids` | `R4V-01`..`R4V-14` |
| `passed_validation_ids` | `R4V-01`..`R4V-14` |
| `failed_validation_ids` | `[]` |
| `first_failure_validation_id` | `null` |
| `first_failure_code` | `null` |
| `allow_hotpath_fallback` | `false` |
| `x04_step2_ready` | `true` |

Rerun v2 gap register status:

| gap_id | status | closure basis |
| --- | --- | --- |
| `R4GAP-01` | closed | `CCL_UI_BRIDGE_TEST_*` wrappers now drive deterministic fail/policy lanes (`R4V-07`..`R4V-12`). |
| `R4GAP-02` | closed | Bridge schemas (`runtime_ui_bridge_route_event_v1`, `runtime_ui_bridge_backpressure_event_v1`, `runtime_ui_bridge_lane_summary_v1`, `runtime_ui_bridge_rollback_record_v1`) are emitted in rerun logs. |
| `R4GAP-03` | closed | Native terminal `runtime_ui_bridge_step2_summary_v1` is emitted in lane logs and committed as rerun aggregate summary. |
| `R4GAP-04` | closed | Compatibility verdicts for `R4I-01`..`R4I-06` are explicit and non-pending (`accept`). |

Run v2 Step 3 status:

- Status: done
- Blocking gaps: none
- Closure readiness: ready (`x04_step2_ready=true`)
- `X-04` closure recommendation: clear to mark `done` based on committed rerun artifacts and compatibility verdict completeness.

## Detailed Work Breakdown

### Step 1 - Shared-Path Scope Contract Publication

- Status: done
- Notes:
  - Published normative Step 1 migration-scope contract with frozen `R4M-*`, `R4C-*`, and `R4T-*` IDs.
  - Classified runtime/UI classes into hot vs non-hot paths and mapped each class to deterministic transport posture.
  - Bound route behavior to existing IPC and worker-lifecycle constraints with strict no-silent-fallback semantics.
- Next:
  - Keep Step 1 IDs immutable and additive-only while Step 2 defines runnable lane commands and assertions.

### Step 2 - Execution Lanes and Conformance Gate Definition

- Status: done
- Notes:
  - Published deterministic lane registry (`R4L-01`..`R4L-06`) and validation matrix (`R4V-01`..`R4V-14`) for migration waves `R4M-21`..`R4M-26`.
  - Published compatibility mapping IDs (`R4I-01`..`R4I-06`) that bind Step 2 assertions to frozen `BPL06-CP*`/`BPL06-SEV-*`/`BPL06-RB-*`/`BPL06-INT-*` artifacts.
  - Published terminal summary schema `runtime_ui_bridge_step2_summary_v1` and readiness criteria (`x04_step2_ready`) for Step 3 evidence execution.
- Next:
  - Keep Step 2 IDs frozen and execute Step 3 evidence lanes against this contract.

### Step 3 - Evidence Execution and `X-04` Closure Recommendation

- Status: done
- Notes:
  - Run-v1 evidence is now committed under `doc/wasm/tickets/evidence/rpl-04-step3-2026-02-09/` with baseline pass lanes and deterministic fail-code checks using currently-wired `CCL_IPC_TEST_*` controls.
  - Rerun v2 evidence is now committed under `doc/wasm/tickets/evidence/rpl-04-step3-rerun-2026-02-10/` with full `R4V-01`..`R4V-14` execution, native bridge telemetry/summary emission, and explicit `R4I-*` compatibility verdicts.
  - Blocking gaps `R4GAP-01`..`R4GAP-04` are closed and aggregate terminal summary reports `status=pass`, `x04_step2_ready=true`.
- Next:
  - Keep RPL-04 artifacts frozen/additive-only and hand off closed bridge baseline to downstream runtime/backend planning tickets.

## Test and Validation Plan

- Unit:
  - Validate route classification logic emits correct `R4M-*` class IDs and hot/non-hot tags.
  - Validate schema serialization for `R4T-01`..`R4T-05` required fields.
- Integration:
  - Validate shared-channel routing for hot classes against `IPCP-07`/`IPCP-08` ownership constraints.
  - Validate lane mismatch and no-fallback policy-fail paths emit canonical failure mappings.
- Regression:
  - Validate non-hot classes remain on control/message lane without accidental hot-path promotion.
  - Validate rollback/remediation artifacts are emitted for every partial migration failure path.

## Risks and Mitigations

- Risk: hot-path and non-hot-path classes blur during implementation.
  - Mitigation: freeze class inventory IDs and enforce class-tag assertions (`R4T-06`, `R4T-07`).
- Risk: backpressure handling reintroduces silent drops or fallback.
  - Mitigation: require canonical timeout/failure mapping and terminal no-fallback rules (`R4C-13`, `R4C-16`, `R4C-23`).
- Risk: partial rollback hides unresolved transport regressions.
  - Mitigation: require explicit rollback records and rerun evidence before promotion (`R4C-25`..`R4C-28`).

## Change Log

- 2026-02-09: Initial RPL-04 subplan created with Step 1 normative migration-scope contract (`R4M-*`, `R4C-*`, `R4T-*`) and Step 2/Step 3 execution plan placeholders.
- 2026-02-09: Executed Step 2 by publishing lane registry (`R4L-*`), validation matrix (`R4V-*`), compatibility mapping (`R4I-*`), and terminal summary schema (`runtime_ui_bridge_step2_summary_v1`) for Step 3 evidence execution.
- 2026-02-09: Executed Step 3 run-v1 and committed evidence bundle (`rpl-04-step3-2026-02-09`) with baseline/fail-lane command outcomes, then opened blocker gaps `R4GAP-01`..`R4GAP-04` for wrapper/schema/summary/compatibility-emission closure.
- 2026-02-09: Synced cross-plan wording to backend BPL-07 Step 1 state while preserving this ticket's `X-04` intake anchors on frozen `BPL06-*` identifiers and unchanged Step 3 blocker set (`R4GAP-01`..`R4GAP-04`).
- 2026-02-10: Executed Step 3 rerun over `R4V-01`..`R4V-14`, committed evidence bundle (`rpl-04-step3-rerun-2026-02-10`), closed `R4GAP-01`..`R4GAP-04`, and recorded `X-04` closure recommendation with terminal `runtime_ui_bridge_step2_summary_v1.status=pass`, `x04_step2_ready=true`.
