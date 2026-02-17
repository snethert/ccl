# Input Backpressure and Coalescing Contract v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-17  
Scope: Normative queue bounds, coalescing policy, and producer backpressure behavior for high-rate UI input lanes  
Depends on: `web-ui/spec/normative-language-and-conformance-v1.md`, `web-ui/spec/ui-wire-format-events-v1.md`, `web-ui/spec/protocol-version-negotiation-v1.md`, `web-ui/spec/observability-contract-v1.md`, `web-ui/bridge/ui-bridge.mjs`, `web-ui/bridge/codec.mjs`  
Compatibility: `v1.x` preserves profile IDs, queue-bound semantics, and coalescing-class behavior; incompatible policy changes require `v2`.

## 1. Purpose

This contract defines bounded behavior for high-rate input sources (pointer move, wheel, hover/drag streams).
It is normative for producer saturation behavior and deterministic coalescing.

## 2. Profiles and Inputs

Defined input queue profiles:

1. `input-bounded-default-v1`
2. `input-bounded-canvas-heavy-v1`
3. `input-bounded-realtime-v1`

Each profile <a id="REQ-INPUT-BACKPRESSURE-AND-COALESCING-CONTRACT-V1-01E69A8752"></a>MUST define:

1. `inputQueueMaxEvents`
2. `inputQueueMaxBytes`
3. `inputBackpressureHighWatermark`
4. `inputBackpressureLowWatermark`
5. `inputCoalescingMode`
6. `allowStructuralDrop` (`false` for all `v1` default profiles)

## 3. Queue Bound Semantics

Queue producers <a id="REQ-INPUT-BACKPRESSURE-AND-COALESCING-CONTRACT-V1-121BDE9A0B"></a>MUST enforce both event-count and byte-size bounds before enqueue.

Rules:

1. Enqueue attempts <a id="REQ-INPUT-BACKPRESSURE-AND-COALESCING-CONTRACT-V1-1179911820"></a>MUST evaluate bound checks before mutating queue state.
2. If enqueue exceeds bounds, producer <a id="REQ-INPUT-BACKPRESSURE-AND-COALESCING-CONTRACT-V1-36505B9F39"></a>MUST attempt deterministic coalescing for eligible high-rate classes.
3. If coalescing cannot satisfy bounds, producer <a id="REQ-INPUT-BACKPRESSURE-AND-COALESCING-CONTRACT-V1-07CC1B7F5F"></a>MUST apply deterministic drop policy to newest eligible high-rate event.
4. Structural events <a id="REQ-INPUT-BACKPRESSURE-AND-COALESCING-CONTRACT-V1-CB6CD479A6"></a>MUST NOT be dropped unless explicit degraded-mode policy is active and logged.
5. Producers <a id="REQ-INPUT-BACKPRESSURE-AND-COALESCING-CONTRACT-V1-23A8A1C137"></a>MUST keep queue order for retained events.

## 4. Coalescing Classes and Determinism

Coalescing eligibility:

1. `pointermove`: eligible
2. `wheel`: eligible
3. Structural events (`down/up/enter/leave/cancel`, key transitions, focus/blur, text/composition): ineligible

Coalescing rules:

1. Representative-event selection <a id="REQ-INPUT-BACKPRESSURE-AND-COALESCING-CONTRACT-V1-A335FC77ED"></a>MUST be latest-by-queue-order within one coalescing key.
2. Coalescing key for pointer move <a id="REQ-INPUT-BACKPRESSURE-AND-COALESCING-CONTRACT-V1-6D6C661DAC"></a>MUST include `pointer_id`, `target_id`, `window_id`, and `drag_session_id`.
3. Coalescing key for wheel <a id="REQ-INPUT-BACKPRESSURE-AND-COALESCING-CONTRACT-V1-492428BA03"></a>MUST include `target_id`, `window_id`, `delta_mode`, and `modifiers`.
4. Coalesced and dropped counts <a id="REQ-INPUT-BACKPRESSURE-AND-COALESCING-CONTRACT-V1-E082F2BCD2"></a>MUST be emitted as telemetry.

## 5. Backpressure State Machine

Producers <a id="REQ-INPUT-BACKPRESSURE-AND-COALESCING-CONTRACT-V1-F0234081A5"></a>MUST implement two-threshold backpressure:

1. Enter backpressure mode when queue depth or bytes meet/exceed high watermark.
2. Exit backpressure mode only when both depth and bytes are below low watermark.
3. While in backpressure mode, producer <a id="REQ-INPUT-BACKPRESSURE-AND-COALESCING-CONTRACT-V1-B14F82370C"></a>MUST prioritize coalescing over raw enqueue for eligible classes.
4. Backpressure transitions <a id="REQ-INPUT-BACKPRESSURE-AND-COALESCING-CONTRACT-V1-306BB1843D"></a>MUST emit one telemetry record per transition edge.

## 6. Poll and Overflow Behavior

Poll/overflow integration:

1. Queue saturation handling <a id="REQ-INPUT-BACKPRESSURE-AND-COALESCING-CONTRACT-V1-CC67419C2D"></a>MUST remain producer-local and <a id="REQ-INPUT-BACKPRESSURE-AND-COALESCING-CONTRACT-V1-52BABAE7E8"></a>MUST NOT change binary event record layout.
2. First-record `maxBytes` overflow on selection <a id="REQ-INPUT-BACKPRESSURE-AND-COALESCING-CONTRACT-V1-11B07416BE"></a>MUST continue to map to `E2BIG`.
3. Producer-side coalescing/drop overflow <a id="REQ-INPUT-BACKPRESSURE-AND-COALESCING-CONTRACT-V1-5E7336B8FB"></a>MUST map to stable telemetry codes and counters, not undefined silent behavior.

## 7. Replay and Audit Requirements

Lossy/coalesced lanes remain replay-auditable only if:

1. Coalescing representative-event choice is deterministic.
2. Loss markers (`coalesced_count`, `dropped_count`) are recorded.
3. Structural events preserve strict relative order.

## 8. Observability Requirements

At minimum, producers <a id="REQ-INPUT-BACKPRESSURE-AND-COALESCING-CONTRACT-V1-1FFD702546"></a>MUST emit:

1. `ui_input_queue_depth`
2. `ui_input_queue_bytes`
3. `ui_input_events_coalesced`
4. `ui_input_events_dropped`
5. `input_queue_profile_id`
6. `backpressure_state`

## 9. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `ui-events.input-overflow` | Producer queue bounds were exceeded and profile overflow policy applied. | Yes | Reduce producer pressure or negotiate larger bounded profile. |
| `ui-events.backpressure` | Producer entered saturation backpressure mode. | Yes | Drain queue and inspect saturation telemetry. |
| `ui-events.coalescing-policy-invalid` | Selected coalescing mode lacks valid class/key definitions. | No | Fix profile configuration and restart producer. |
| `ui-events.structural-drop-forbidden` | Producer attempted to drop structural event under non-degraded profile. | No | Correct producer policy; structural events are not droppable in this profile. |

## 10. Conformance Fixtures and Pass Criteria

Minimum required evidence:

1. `web-ui/tests/bridge-input-flood.test.mjs`
2. `web-ui/tests/bridge-coalescing-determinism.test.mjs`
3. `web-ui/tests/ui-poll-backpressure.test.mjs`

Pass criteria:

1. Queue bounds are never exceeded without deterministic overflow handling.
2. Coalescing representative-event selection is stable across repeated runs.
3. Structural events are not dropped in non-degraded profiles.

## 11. Conformance

An implementation is conformant only if Sections 2-10 are satisfied.
