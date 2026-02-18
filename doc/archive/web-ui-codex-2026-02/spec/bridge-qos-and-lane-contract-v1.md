# Bridge QoS and Lane Contract v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-17  
Scope: Normative lane taxonomy, backpressure boundaries, and starvation constraints for runtime bridge traffic  
Depends on: `web-ui/spec/normative-language-and-conformance-v1.md`, `web-ui/spec/runtime-bridge-envelope-v1.md`, `web-ui/spec/protocol-version-negotiation-v1.md`, `web-ui/spec/observability-contract-v1.md`  
Compatibility: `v1.x` preserves lane-class IDs and starvation semantics; incompatible scheduler or lane-model changes require `v2`.

## 1. Purpose

This contract defines quality-of-service behavior for bridge traffic under contention.
It is normative for lane classes, admission order, and starvation prevention.

## 2. Lane Classes

Required lane classes:

1. `control`
2. `interaction`
3. `telemetry`

Optional lane classes:

1. `asset`
2. `background`

Lane class meaning:

1. `control` carries command/result/error and critical focus/selection commits.
2. `interaction` carries high-rate input streams.
3. `telemetry` carries logs/progress/diagnostics/output.
4. `asset` carries binary hydration/streaming traffic when enabled.
5. `background` carries non-latency-critical tasks.

## 3. Scheduling and Admission Rules

Bridge schedulers <a id="REQ-BRIDGE-QOS-AND-LANE-CONTRACT-V1-C021EA74BA"></a>MUST satisfy:

1. Control-lane starvation freedom under sustained non-control load.
2. Deterministic lane selection for fixed queue state and profile.
3. Bounded interaction-lane admission under telemetry flood.

Required scheduling invariants:

1. Control lane <a id="REQ-BRIDGE-QOS-AND-LANE-CONTRACT-V1-864460302C"></a>MUST receive service at least once per scheduler round when non-empty.
2. Telemetry lane <a id="REQ-BRIDGE-QOS-AND-LANE-CONTRACT-V1-6B9A7DEBE7"></a>MUST yield to control lane under shared budget exhaustion.
3. Interaction lane SHOULD use profile-gated coalescing before displacing control traffic.

## 4. Backpressure by Lane

Lane-local backpressure:

1. Each lane <a id="REQ-BRIDGE-QOS-AND-LANE-CONTRACT-V1-9B103C524A"></a>MUST define independent queue depth and byte budgets.
2. Backpressure state <a id="REQ-BRIDGE-QOS-AND-LANE-CONTRACT-V1-A68BD9E590"></a>MUST be computed per lane and recorded with lane ID.
3. Backpressure in one lane <a id="REQ-BRIDGE-QOS-AND-LANE-CONTRACT-V1-8A4061E003"></a>MUST NOT implicitly drop messages from another lane.

Cross-lane pressure handling:

1. Overflow in telemetry lane MAY degrade telemetry payload retention.
2. Overflow in interaction lane MAY coalesce eligible high-rate events.
3. Overflow in control lane <a id="REQ-BRIDGE-QOS-AND-LANE-CONTRACT-V1-A8559617EF"></a>MUST fail admission with stable reject code; silent drop is forbidden.

## 5. Starvation and Latency Targets

Required contention behavior:

1. Control-lane p95 queue wait under synthetic mixed-lane flood SHOULD remain within configured QoS budget.
2. Repeated contention fixtures <a id="REQ-BRIDGE-QOS-AND-LANE-CONTRACT-V1-50080916B5"></a>MUST produce consistent lane-service ordering for equal timestamps and queue state.
3. Scheduler tie-break <a id="REQ-BRIDGE-QOS-AND-LANE-CONTRACT-V1-461BEF18BF"></a>MUST use stable lane priority then FIFO within lane.

## 6. Observability Requirements

Bridge telemetry <a id="REQ-BRIDGE-QOS-AND-LANE-CONTRACT-V1-39367FE9D6"></a>MUST include:

1. `lane_id`
2. `lane_queue_depth`
3. `lane_queue_bytes`
4. `lane_wait_ms`
5. `lane_backpressure_state`
6. `lane_dropped_count`
7. `lane_coalesced_count`

## 7. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `runtime-envelope.lane-unknown` | Message references unknown lane class. | No | Use one of the negotiated lane IDs. |
| `runtime-envelope.lane-overflow` | Lane queue exceeded admitted bounds. | Conditional | Back off producer or increase approved lane budget. |
| `runtime-envelope.lane-starvation` | Scheduler violated starvation guarantee for required lane class. | No | Fix scheduler policy before release. |
| `runtime-envelope.control-drop-forbidden` | Control message would be dropped under saturation. | No | Reject admission with explicit code instead of dropping. |

## 8. Conformance Fixtures and Pass Criteria

Minimum required evidence:

1. `web-ui/tests/runtime-lane-contention.test.mjs`
2. `web-ui/tests/runtime-command-admission.test.mjs`
3. `scripts/wasm/tests/ipc-conformance.mjs`

Pass criteria:

1. Control lane is not starved in mixed-lane stress runs.
2. Lane-local backpressure counters and states are present and consistent.
3. Scheduler tie-break behavior is deterministic.

## 9. Conformance

An implementation is conformant only if Sections 2-8 are satisfied.
