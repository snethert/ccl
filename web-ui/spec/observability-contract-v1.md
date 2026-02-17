# Observability Contract v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-17  
Scope: Normative logs, metrics, summaries, and correlation requirements for startup, runtime bridge, IPC lanes, and `web-ui` quality gates  
Depends on: `web-ui/spec/normative-language-and-conformance-v1.md`, `web-ui/spec/perf-telemetry-sampling-policy-v1.md`, `web-ui/spec/performance-slo-and-budgets-v1.md`, `web-ui/spec/runtime-bridge-envelope-v1.md`, `web-ui/spec/protocol-version-negotiation-v1.md`, `scripts/wasm/lib/startup-gate.mjs`, `scripts/wasm/tests/ipc-conformance.mjs`, `web-ui/src/quality-gates.mjs`, `web-ui/src/renderer.mjs`, `scripts/wasm/lib/microkernel.mjs`  
Compatibility: `v1.x` preserves telemetry schema IDs, lane names, and required correlation fields; incompatible schema changes require `v2`.

## 1. Purpose

This contract defines the production observability surface for `web-ui` and runtime bridge operations.
It is normative for event schemas, sampling/retention behavior, correlation IDs, and diagnostics required for release and incident workflows.

## 2. Telemetry Planes and Schema IDs

| Plane | Required schema/version IDs |
|---|---|
| Startup gate | `startup_gate_check_result_v1`, `startup_gate_summary_v1` |
| IPC readiness and channel flow | `ipc_protocol_ready_v1`, `ipc_channel_event_v1`, `ipc_channel_summary_v1`, `ipc_conformance_summary_v1` |
| Runtime UI bridge migration/compatibility | `runtime_ui_bridge_route_event_v1`, `runtime_ui_bridge_backpressure_event_v1`, `runtime_ui_bridge_lane_summary_v1`, `runtime_ui_bridge_migration_summary_v1`, `runtime_ui_bridge_rollback_record_v1`, `runtime_ui_bridge_step2_summary_v1` |
| UI quality telemetry | `QUALITY_GATES_SCHEMA_VERSION = "1"` |

## 3. Required Records

## 3.1 Startup Gate Records

`STARTUP_GATE_CHECK` and `STARTUP_GATE_SUMMARY` records <a id="REQ-OBSERVABILITY-CONTRACT-V1-102D23A0AA"></a>MUST be emitted for startup-gate runs.

Minimum required check fields:

1. `run_id`
2. `sequence`
3. `check_id`
4. `status`
5. `fail_code`
6. `observed`
7. `contradiction_ids`

Minimum required summary fields:

1. `run_id`
2. `replacement_track`
3. `status`
4. `failure_check_id`
5. `failure_code`
6. `results_digest`

## 3.2 IPC and Runtime Bridge Records

`ipc-conformance` emissions <a id="REQ-OBSERVABILITY-CONTRACT-V1-28986137F5"></a>MUST include run-level readiness and per-channel/per-class outcomes.

Minimum required fields for all IPC/bridge records:

1. `schema_version`
2. `run_id`
3. `status`
4. `allow_hotpath_fallback`

Additional required fields by record type:

1. `ipc_protocol_ready_v1`: `lane_class`, `protocol_id`, `channel_bindings`, `startup_sequence_refs`, `failure_code`.
2. `ipc_channel_event_v1`: `channel_id`, `event_type`, `sequence_no`, `occupancy`, `failure_code`, `transition_id`.
3. `ipc_channel_summary_v1`: `channel_id`, `events_emitted`, `first_failure_code`, `results_digest`.
4. `ipc_conformance_summary_v1`: `lane_id`, `conformance_ids`, `passed_ids`, `failed_ids`, `x03_clear_ready`, `lane_results_digest`.
5. `runtime_ui_bridge_route_event_v1`: `class_id`, `direction`, `selected_lane`, `sequence_no`, `failure_code`, `fallback_attempted`.
6. `runtime_ui_bridge_backpressure_event_v1`: `class_id`, `wait_state`, `wait_ms`, `timeout_ms`, `failure_code`.
7. `runtime_ui_bridge_lane_summary_v1`: `class_id`, `hot_path_class`, `first_failure_code`, `results_digest`.
8. `runtime_ui_bridge_migration_summary_v1`: `wave_id`, `executed_class_ids`, `policy_failures`, `x04_ready`.
9. `runtime_ui_bridge_rollback_record_v1`: `rollback_id`, `trigger_class_id`, `trigger_failure_code`, `applied_scope`, `post_rollback_status`.
10. `runtime_ui_bridge_step2_summary_v1`: `executed_validation_ids`, `compatibility_results`, `x04_step2_ready`, `first_failure_code`, `results_digest`.

## 3.3 UI Quality Collector Records

`createQualityCollector()` <a id="REQ-OBSERVABILITY-CONTRACT-V1-B17101086B"></a>MUST expose schema version `1` and these lanes:

1. `uiTurns`
2. `renders`
3. `virtualization`
4. `transcript`
5. `reliability`

Collector snapshots <a id="REQ-OBSERVABILITY-CONTRACT-V1-00E627099D"></a>MUST include:

1. `schemaVersion`
2. `budgets`
3. `limits`
4. `samples`
5. `counters`

Renderer integrations <a id="REQ-OBSERVABILITY-CONTRACT-V1-851A64496B"></a>MUST emit render samples containing:

1. `surface`
2. `backend`
3. `operation`
4. `fullRedraw`
5. `dirtyHintCount`
6. `dirtyRectCount`
7. `drawnNodeCount`
8. `totalNodeCount`
9. `durationMs`
10. `ts`

## 3.4 Microkernel Debug State

Debug snapshots (`api._debug`) <a id="REQ-OBSERVABILITY-CONTRACT-V1-089666CB62"></a>MUST include:

1. `runtimeCommand` (`transport`, `fallbackAllowed`)
2. `runtimeEvent` (`transport`, `fallbackAllowed`, `dropped`)
3. Pending request lane sets (`pendingUiPolls`, `pendingRuntimeCommandPolls`)

## 4. Correlation Contract

Telemetry producers <a id="REQ-OBSERVABILITY-CONTRACT-V1-FFD5573814"></a>MUST preserve stable correlation fields across records:

1. `run_id` for one logical startup/conformance run.
2. `lane_id` for lane-level execution partitioning.
3. `class_id` and `wave_id` for runtime bridge rollout traces.
4. `compatibility_id` entries in `compatibility_results`.
5. `sequence_no` and `correlation_id` for channel/class event ordering.

## 5. Sampling, Retention, and Evaluation

Collector retention <a id="REQ-OBSERVABILITY-CONTRACT-V1-A933B819C3"></a>MUST follow bounded defaults:

1. `uiTurns=512`
2. `renders=1024`
3. `virtualization=1024`
4. `transcript=128`
5. `reliability=256`

Evaluation checks <a id="REQ-OBSERVABILITY-CONTRACT-V1-F88435CFC6"></a>MUST remain stable for:

1. `ui-turn-p95`
2. `ui-turn-p99`
3. `render-no-full-redraw-with-dirty-hints`
4. `virtualization-visible-window-bounds`
5. `transcript-supported-scale`
6. `reliability-unhandled-runtime-faults`
7. `reliability-deterministic-replay`

## 6. Privacy and Redaction Rules

1. Telemetry <a id="REQ-OBSERVABILITY-CONTRACT-V1-B39F96F56B"></a>MUST be treated as diagnostic data, not a user-data source of truth.
2. Export paths SHOULD redact or hash payload fields that may contain user-authored text (`runtime.output` payload text, free-form error details).
3. Implementations <a id="REQ-OBSERVABILITY-CONTRACT-V1-39E277FEFF"></a>MUST avoid retaining live host object references in telemetry payloads.
4. JSON-clone fallback behavior for details fields <a id="REQ-OBSERVABILITY-CONTRACT-V1-2165E557A0"></a>MUST be non-throwing.

## 7. Determinism Rules

1. Emission order <a id="REQ-OBSERVABILITY-CONTRACT-V1-C034DF3CDE"></a>MUST be stable for identical execution order.
2. Digest fields (`results_digest`, `lane_results_digest`) <a id="REQ-OBSERVABILITY-CONTRACT-V1-22D178D656"></a>MUST be reproducible from the emitted record set.
3. Counter growth <a id="REQ-OBSERVABILITY-CONTRACT-V1-DE95993AF3"></a>MUST be monotonic even when samples are trimmed by retention limits.

## 8. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `observability.schema-missing` | Required telemetry schema ID is absent. | No | Restore required telemetry producer before claim/release. |
| `observability.correlation-missing` | Required run/lane/class correlation field missing. | No | Fix producer field mapping and rerun diagnostics. |
| `observability.digest-mismatch` | Digest does not match emitted records. | No | Treat telemetry as invalid; recompute after fixing producer order/content. |
| `observability.lane-nonconformant` | Required quality lane missing or malformed. | Conditional | Reconnect lane instrumentation and rerun tests. |
| `observability.export-redaction-missing` | Sensitive fields exported without policy controls. | No | Apply redaction policy before external export. |

## 9. Conformance Fixtures and Pass Criteria

Minimum required evidence:

1. `scripts/wasm/tests/start-lisp-noninteractive-smoke.mjs`
2. `scripts/wasm/tests/ipc-conformance.mjs`
3. `web-ui/tests/phase-7-performance-budgets.test.mjs`
4. `web-ui/tests/phase-7-reliability.test.mjs`
5. `web-ui/tests/phase-7-integration.test.mjs`

Pass criteria:

1. Required schema IDs and required fields from Sections 2-4 are present.
2. Collector sampling/retention/evaluation behavior matches Section 5.
3. Deterministic digests and ordering invariants hold.

## 10. Conformance

An implementation is conformant only if Sections 2-9 are satisfied.
