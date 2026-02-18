# Incident and Recovery Runbook v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-17  
Scope: Operational incident detection, triage, containment, rollback, and recovery for startup gate, runtime bridge, capability mediation, and persistence safety states  
Depends on: `web-ui/spec/normative-language-and-conformance-v1.md`, `web-ui/spec/security-and-capability-model-v1.md`, `web-ui/spec/observability-contract-v1.md`, `web-ui/spec/release-compatibility-and-rollout-v1.md`, `web-ui/spec/persistence-corruption-recovery-v1.md`, `scripts/wasm/lib/startup-gate.mjs`, `scripts/wasm/lib/load-image.mjs`, `scripts/wasm/tests/ipc-conformance.mjs`, `scripts/wasm/tests/start-lisp-noninteractive-smoke.mjs`, `web-ui/src/state.mjs`  
Compatibility: `v1.x` preserves incident class IDs, strict fail-closed response model, and degraded-mode escalation semantics; incompatible runbook state-machine changes require `v2`.

## 1. Purpose

This runbook defines deterministic operational response for production incidents.
It is normative for incident intake, triage order, containment actions, and recovery exit criteria.

## 2. Incident Classes

| Class ID | Trigger signals | Default severity |
|---|---|---|
| `INC-STARTUP-GATE` | `STARTUP_GATE_SUMMARY.status=fail` with `RPL01-E001..RPL01-E012` | Critical |
| `INC-STARTUP-DIAGNOSTICS` | Malformed startup summary (`invalid_summary`) | Critical |
| `INC-IPC-LANE` | `ipc_conformance_summary_v1.status=fail` or `x03_clear_ready=false` | High |
| `INC-BRIDGE-COMPAT` | `runtime_ui_bridge_step2_summary_v1.status=fail` or `x04_step2_ready=false` | High |
| `INC-BRIDGE-ROLLBACK` | `runtime_ui_bridge_rollback_record_v1` emitted | High |
| `INC-CAPABILITY-MEDIATION` | Safe-mode/capability denial blocks required operation unexpectedly | Medium |
| `INC-PERSISTENCE-INTEGRITY` | Corruption or degraded persistence mode entered | Critical |

## 3. Intake and Evidence Collection

For every incident, responders <a id="REQ-INCIDENT-AND-RECOVERY-RUNBOOK-V1-C141694F93"></a>MUST capture:

1. `incident_id` (new unique ID)
2. `run_id` (startup/IPC/bridge correlation ID)
3. First failure code and first failing artifact
4. Latest startup summary and relevant check records
5. Latest IPC/bridge summaries and rollback records
6. Current capability state (`safeMode`, granted set, pending requests) when relevant
7. Current persistence health mode when relevant

## 4. Deterministic Triage Order

Responders <a id="REQ-INCIDENT-AND-RECOVERY-RUNBOOK-V1-602F0EADFC"></a>MUST evaluate in this order:

1. Startup gate integrity (`INC-STARTUP-GATE`, `INC-STARTUP-DIAGNOSTICS`)
2. IPC readiness (`INC-IPC-LANE`)
3. Runtime bridge compatibility/rollback (`INC-BRIDGE-COMPAT`, `INC-BRIDGE-ROLLBACK`)
4. Capability mediation state (`INC-CAPABILITY-MEDIATION`)
5. Persistence integrity and degraded mode (`INC-PERSISTENCE-INTEGRITY`)

Lower-priority classes <a id="REQ-INCIDENT-AND-RECOVERY-RUNBOOK-V1-1C80037C7C"></a>MUST NOT be resolved before unresolved higher-priority blockers.

## 5. Incident Runbooks by Class

## 5.1 `INC-STARTUP-GATE`

1. Extract failing `check_id`, `fail_code`, and `remediation`.
2. Stop startup promotion immediately (no fallback path allowed).
3. Apply environment/config fix matching failing check.
4. Re-run startup gate from cold process start.
5. Close incident only on clean `status=pass`.

## 5.2 `INC-STARTUP-DIAGNOSTICS`

1. Treat malformed startup summary as equivalent to startup failure.
2. Block release/startup progression.
3. Repair diagnostics emission path.
4. Verify one valid summary line and deterministic digest before reopening rollout.

## 5.3 `INC-IPC-LANE`

1. Capture `ipc_protocol_ready_v1`, `ipc_channel_event_v1`, and `ipc_channel_summary_v1`.
2. Identify first failing channel and `failure_code`.
3. Keep rollout blocked until `ipc_conformance_summary_v1.x03_clear_ready=true`.
4. Re-run conformance for same lane scope after fix.

## 5.4 `INC-BRIDGE-COMPAT` and `INC-BRIDGE-ROLLBACK`

1. Capture `runtime_ui_bridge_step2_summary_v1` and any rollback record.
2. If rollback record exists, freeze promotion for `applied_scope`.
3. Do not enable hot-path fallback; policy remains fail-closed.
4. Rerun affected validation (`R4V-*`) and required compatibility IDs (`R4I-*`).
5. Resume rollout only after passing `x04_step2_ready=true` with no rollback record.

## 5.5 `INC-CAPABILITY-MEDIATION`

1. Inspect `safeMode`, granted capability set, and pending request queue.
2. If safe mode is enabled unexpectedly, treat as containment-on and investigate cause before disabling.
3. Apply explicit request/grant/deny actions and preserve audit log.
4. Validate command enablement reasons (`Safe mode`, `Missing capability: <capability>`).

## 5.6 `INC-PERSISTENCE-INTEGRITY`

1. Follow persistence corruption-recovery taxonomy and class-specific actions.
2. Escalate mode as needed: `degraded-repairing` -> `degraded-readonly` -> `degraded-export-only`.
3. Keep writes blocked until integrity preconditions are re-established.
4. Preserve quarantine artifacts for forensic analysis.

## 6. Recovery State Machine

Operational mode transitions <a id="REQ-INCIDENT-AND-RECOVERY-RUNBOOK-V1-1B8282AE02"></a>MUST be explicit and logged:

1. `healthy` -> `degraded-repairing` when deterministic repair begins
2. `degraded-repairing` -> `healthy` on verified repair success
3. `degraded-repairing` -> `degraded-readonly` if safe write semantics cannot be proven
4. `degraded-readonly` -> `degraded-export-only` when neither repair nor safe local writes are possible

Silent transition back to `healthy` is forbidden.

## 7. Incident Record Contract

Each incident <a id="REQ-INCIDENT-AND-RECOVERY-RUNBOOK-V1-90BD20B55F"></a>MUST produce a structured record with:

1. `incident_id`
2. `run_id`
3. `class_id`
4. `severity`
5. `status` (`open|contained|resolved`)
6. `first_failure_code`
7. `first_failure_artifact`
8. `affected_scope` (`wave_id`, `lane_id`, `workspace_id`, or equivalent)
9. `containment_actions`
10. `recovery_actions`
11. `post_recovery_validation`
12. `opened_at`
13. `resolved_at`

## 8. Exit Criteria

An incident MAY close only when all conditions hold:

1. Blocking checks for incident class now pass.
2. Required conformance artifacts are re-emitted and valid.
3. No degraded mode remains active unless explicitly accepted by policy.
4. Post-incident validation rerun is attached to incident record.

## 9. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `incident.blocked-by-startup-gate` | Startup gate failed or summary malformed. | No | Fix startup prerequisites and rerun from cold start. |
| `incident.blocked-by-ipc` | IPC readiness gate failed. | Conditional | Repair lane/channel failure and rerun conformance. |
| `incident.blocked-by-bridge` | Bridge compatibility/step2 gate failed. | Conditional | Repair failing validation scope and rerun. |
| `incident.rollback-active` | Rollback record emitted for scope. | No | Keep scope frozen until explicit recovery validation passes. |
| `incident.capability-state-invalid` | Capability mediation state cannot satisfy required operation. | Conditional | Resolve safe-mode or capability request/grant flow. |
| `incident.persistence-degraded` | Persistence integrity risk requires degraded mode. | No | Complete corruption recovery workflow before write re-enable. |

## 10. Conformance Fixtures and Pass Criteria

Minimum required evidence:

1. `scripts/wasm/tests/start-lisp-noninteractive-smoke.mjs`
2. `scripts/wasm/tests/ipc-conformance.mjs`
3. `web-ui/tests/capabilities.test.mjs`
4. `web-ui/tests/persistence-conformance-fixtures.test.mjs`
5. `web-ui/tests/phase-7-reliability.test.mjs`

Pass criteria:

1. Incident classes route to deterministic runbook branches.
2. Failures trigger containment actions with no silent fallback.
3. Recovery closure requires explicit post-fix validation evidence.

## 11. Conformance

An operations process is conformant only if Sections 2-10 are satisfied.
