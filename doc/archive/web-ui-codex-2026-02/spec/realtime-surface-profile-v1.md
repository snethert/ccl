# Realtime Surface Profile v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-17  
Scope: Normative workload profiles, realtime input/tick constraints, and drift budgets for high-frequency interactive surfaces  
Depends on: `web-ui/spec/normative-language-and-conformance-v1.md`, `web-ui/spec/scale-test-profile-v1.md`, `web-ui/spec/event-log-ordering-and-clock-rules-v1.md`, `web-ui/spec/input-backpressure-and-coalescing-contract-v1.md`, `web-ui/spec/perf-telemetry-sampling-policy-v1.md`  
Compatibility: `v1.x` preserves workload profile IDs and drift metric semantics; incompatible profile-class or timing model changes require `v2`.

## 1. Purpose

This contract defines profile-level behavior for high-frequency app classes including game-like surfaces.
It is normative for workload classification, timing constraints, and lossy-lane determinism limits.

## 2. Workload Profiles

Required profile IDs:

1. `tooling-interactive-v1`
2. `canvas-heavy-v1`
3. `realtime-v1`

Profile declarations <a id="REQ-REALTIME-SURFACE-PROFILE-V1-13309E0E7B"></a>MUST include:

1. `profile_id`
2. `loss_policy`
3. `coalescing_policy`
4. `clock_profile`
5. `drift_budget_ms`
6. `required_capability_bits`

## 3. Realtime Input Requirements

For `realtime-v1`:

1. High-rate input lanes <a id="REQ-REALTIME-SURFACE-PROFILE-V1-C3C3864601"></a>MUST support latest-state delivery semantics for eligible event classes.
2. Structural input events <a id="REQ-REALTIME-SURFACE-PROFILE-V1-DCFD7EDD2E"></a>MUST remain strictly ordered and lossless.
3. Pointer-lock or relative-delta input support MAY be profile-gated but <a id="REQ-REALTIME-SURFACE-PROFILE-V1-C839EC3CFD"></a>MUST be explicitly negotiated when enabled.
4. Gamepad snapshots MAY be sampled/quantized, but sampling cadence <a id="REQ-REALTIME-SURFACE-PROFILE-V1-84BF0A1F2B"></a>MUST be declared in profile metadata.

## 4. Tick and Clock Model

Clock requirements:

1. Realtime profile <a id="REQ-REALTIME-SURFACE-PROFILE-V1-C50287076A"></a>MUST declare one clock profile (`monotonic-ms-v1` or `realtime-tick-v1`).
2. Simulation tick cadence SHOULD be fixed-step or bounded-jitter variable-step by explicit profile setting.
3. Drift between declared tick schedule and observed execution <a id="REQ-REALTIME-SURFACE-PROFILE-V1-BABC857DB4"></a>MUST be measured and recorded.
4. UI command-turn work <a id="REQ-REALTIME-SURFACE-PROFILE-V1-8643B64BAC"></a>MUST NOT silently redefine realtime tick boundaries.

## 5. Drift and Degradation Policy

Degradation behavior:

1. If drift exceeds profile budget, runtime SHOULD degrade non-critical telemetry/background lanes first.
2. If drift remains above hard budget, runtime <a id="REQ-REALTIME-SURFACE-PROFILE-V1-34EC57B7A6"></a>MUST emit explicit realtime-degraded state.
3. Degraded state transitions <a id="REQ-REALTIME-SURFACE-PROFILE-V1-416FE9276C"></a>MUST be reversible and observable.

## 6. Replay and Lossy Determinism

Realtime profiles remain replay-auditable only if:

1. Loss markers are recorded for coalesced/dropped high-rate events.
2. Representative-event tie-break remains deterministic.
3. Structural event order remains strict.

## 7. Observability Requirements

Required fields:

1. `workload_profile_id`
2. `tick_target_ms`
3. `tick_observed_ms`
4. `tick_drift_ms`
5. `realtime_degraded`
6. `input_loss_count`
7. `input_coalesced_count`

## 8. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `scale-profile.profile-unknown` | Requested workload profile is not supported. | No | Select a supported profile ID. |
| `scale-profile.realtime-capability-missing` | Realtime profile requested without required negotiated capabilities. | No | Negotiate required capabilities or use non-realtime profile. |
| `scale-profile.tick-drift-budget-exceeded` | Observed drift exceeded realtime profile hard budget. | Conditional | Reduce workload, tune scheduler, or adjust approved budget. |
| `scale-profile.loss-marker-missing` | Lossy high-rate lane operated without required replay loss markers. | No | Fix instrumentation and regenerate traces. |

## 9. Conformance Fixtures and Pass Criteria

Minimum required evidence:

1. `web-ui/tests/realtime-input-codec.test.mjs`
2. `web-ui/tests/realtime-clock-profile.test.mjs`
3. `web-ui/tests/replay-lossy-lane-determinism.test.mjs`

Pass criteria:

1. Profile negotiation and fallback behavior are deterministic.
2. Drift budgets are enforced with explicit degraded-state signaling.
3. Lossy-lane replay remains deterministic for fixed fixture inputs.

## 10. Conformance

An implementation is conformant only if Sections 2-9 are satisfied.
