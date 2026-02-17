# Web UI Scaling Review Patch Map

Date: 2026-02-17  
Input review: `web-ui/DESIGN-REVIEW-SCALING-AND-REALTIME-2026-02-17.md`  
Goal: map `SR-*` concerns to exact spec patch points and conformance deltas

## Scope

This is a design patch map, not an implementation checklist.

It defines:

1. Which existing spec files should be patched.
2. Where to patch them (exact section-level insertion points).
3. Which new spec files should be introduced where existing surfaces are insufficient.
4. Which tests/gates should be extended.

## Patch Strategy

1. Patch existing specs first where semantics already belong.
2. Add new specs only for cross-cutting models that do not fit current contracts.
3. Keep `v1.x` compatibility unless a behavior is explicitly profile-gated.
4. Introduce capability-gated lanes for high-rate/realtime behavior.

## SR-to-Spec Patch Matrix

| SR ID | Primary patch files | Exact patch points | Required additions | Test/gate delta |
|---|---|---|---|---|
| `SR-01` Unbounded input queue | `web-ui/spec/ui-wire-format-events-v1.md`, `web-ui/spec/protocol-version-negotiation-v1.md`, `web-ui/spec/performance-slo-and-budgets-v1.md` | 1) Insert new section after `Section 6. Selection and Poll Semantics` in `ui-wire-format-events-v1.md`. 2) Insert capability bits in `Section 2. Versioned Surfaces in Scope` and `Section 3. Required Handshake Sequence` in `protocol-version-negotiation-v1.md`. 3) Insert new gate IDs in `Section 5. Normative Gate IDs and Semantics` in `performance-slo-and-budgets-v1.md`. | Queue depth/bytes limits, overflow policy, mandatory producer behavior under saturation, `ui-events.input-overflow` failure code, handshake bit for bounded input profile. | Add `web-ui/tests/bridge-input-flood.test.mjs`; include in `gate.tests.fast.v1` via package test target. |
| `SR-02` No coalescing policy | `web-ui/spec/ui-wire-format-events-v1.md`, `web-ui/spec/event-log-ordering-and-clock-rules-v1.md` | 1) Insert new subsection after `Section 5.9 Unknown Type Fallback` in `ui-wire-format-events-v1.md`. 2) Insert coalesced-event replay rules after `Section 6. Partial Replay Rules` in `event-log-ordering-and-clock-rules-v1.md`. | Normative coalescing classes (`pointermove`, `wheel`), non-coalescable structural events, tie-break rules for replayability, observability annotations for coalesced/dropped counts. | Add `web-ui/tests/bridge-coalescing-determinism.test.mjs`; add to replay harness tests. |
| `SR-03` No lane-level QoS | `web-ui/spec/runtime-bridge-envelope-v1.md`, `web-ui/spec/protocol-version-negotiation-v1.md`, `web-ui/spec/observability-contract-v1.md` | 1) Add lane taxonomy after `Section 5. Transport Binding` in `runtime-bridge-envelope-v1.md`. 2) Add QoS negotiation fields in `Section 6. Pending and Backpressure Negotiation` in `protocol-version-negotiation-v1.md`. 3) Extend required record fields in `Section 3.2 IPC and Runtime Bridge Records` in `observability-contract-v1.md`. | `control/interaction/telemetry` lane classes, starvation constraints, backpressure signaling by class, lane saturation metrics. | Extend `scripts/wasm/tests/ipc-conformance.mjs` with lane starvation scenario; add a runtime bridge contention test under `web-ui/tests`. |
| `SR-04` No app/plugin isolation | `web-ui/spec/security-and-capability-model-v1.md`, `web-ui/spec/ui-state-schema-v1.json` | 1) Add tenant model section after `Section 5. Capability State and Policy Model` in `security-and-capability-model-v1.md`. 2) Add `tenants` and `tenantPolicies` lanes under root properties in `ui-state-schema-v1.json`. | Per-app quotas (CPU, queue bytes, command inflight, persistence rate), app-level circuit breaker states, audit fields per tenant action. | Add `web-ui/tests/tenant-quota-policy.test.mjs`; add to fast gate. |
| `SR-05` Hit-test cost on high-rate paths | `web-ui/spec/renderer-backend-contract-v1.md`, `web-ui/spec/perf-telemetry-sampling-policy-v1.md` | 1) Add high-rate hit-test budget clauses after `Section 7. Hit-Test Semantics` in `renderer-backend-contract-v1.md`. 2) Add required hit-test telemetry fields in `Section 6.2 renders` in `perf-telemetry-sampling-policy-v1.md`. | Bounded hit-test work per frame, optional cached-target rules for move sequences, required timing fields (`hitTestMs`, `hitTestCount`). | Add `web-ui/tests/hit-test-load-profile.test.mjs`; extend performance budget tests to assert hit-test limits. |
| `SR-06` UI producer backpressure undefined | `web-ui/spec/ui-wire-format-events-v1.md`, `web-ui/spec/runtime-bridge-envelope-v1.md` | 1) Extend `Section 6. Selection and Poll Semantics` and `Section 9. Failure Semantics` in `ui-wire-format-events-v1.md`. 2) Extend `Section 8. Failure Semantics` in `runtime-bridge-envelope-v1.md`. | Explicit producer obligations for full queues, retry/backoff guidance, stable `EWOULDBLOCK`/overflow mapping by lane class. | Add `web-ui/tests/ui-poll-backpressure.test.mjs`. |
| `SR-07` No command admission control | `web-ui/spec/runtime-bridge-envelope-v1.md`, `web-ui/spec/command-routing-algorithm-v1.md`, `web-ui/spec/security-and-capability-model-v1.md` | 1) Add command queue contract after `Section 5. Transport Binding` in `runtime-bridge-envelope-v1.md`. 2) Extend `Section 7. Execution Algorithm` in `command-routing-algorithm-v1.md` with admission failure path. 3) Add policy fields under capability model for command queue caps. | Max in-flight limits, deterministic reject codes, per-scope queue partitioning, cancellation semantics. | Add `web-ui/tests/runtime-command-admission.test.mjs`. |
| `SR-08` No workload classes | `web-ui/spec/protocol-version-negotiation-v1.md`, `web-ui/spec/scale-test-profile-v1.md` | 1) Add workload profile negotiation in `Section 3. Required Handshake Sequence` in `protocol-version-negotiation-v1.md`. 2) Add profile lanes in `Section 3. Required Scale Lanes` in `scale-test-profile-v1.md`. | `tooling-interactive-v1`, `canvas-heavy-v1`, `realtime-v1` profiles with allowed loss/coalescing semantics. | Add scale profile fixtures for each workload class. |
| `SR-09` Monolithic state/persistence risk | `web-ui/spec/persistence-purpose-and-user-contract-v1.md`, `web-ui/spec/persistence-storage-backend-matrix-v1.md` | 1) Add structured-state vs binary-asset separation after core model section in `persistence-purpose-and-user-contract-v1.md`. 2) Add asset lane guarantees and limits in backend matrix. | Asset channel contract, content-addressed blobs, non-blocking asset hydration policies, snapshot exclusion rules for large binaries. | Add `web-ui/tests/persistence-asset-lane.test.mjs`. |
| `SR-10` Global-first capability model | `web-ui/spec/security-and-capability-model-v1.md`, `web-ui/spec/observability-contract-v1.md` | 1) Extend capability model with tenant-scoped grants after `Section 5`. 2) Add per-tenant telemetry fields in `Section 4. Correlation Contract` in `observability-contract-v1.md`. | Tenant-scoped grants/revokes, emergency kill semantics, actor provenance per tenant decision. | Extend `web-ui/tests/capabilities.test.mjs` with tenant scope matrix. |
| `SR-11` Determinism vs lossy lanes | `web-ui/spec/event-log-ordering-and-clock-rules-v1.md`, `web-ui/spec/ui-wire-format-events-v1.md` | 1) Add “lossy lane determinism” subsection after `Section 8. Determinism and Tie-Break Rules` in event-log contract. 2) Add event metadata requirements in events contract. | Replay-stable coalescing IDs, deterministic selection of representative event in collapsed windows, explicit loss markers. | Add `web-ui/tests/replay-lossy-lane-determinism.test.mjs`. |
| `SR-12` Missing game/realtime input taxonomy | `web-ui/spec/ui-wire-format-events-v1.md`, `web-ui/spec/protocol-version-negotiation-v1.md` | 1) Extend `Section 5.2 Event Type IDs` with gated extensions. 2) Extend handshake section with capability bits for pointer-lock/gamepad lanes. | New event families (pointer-lock delta, gamepad snapshot), gated by capability bits, fallback behavior when unavailable. | Add `web-ui/tests/realtime-input-codec.test.mjs`. |
| `SR-13` Missing audio/realtime clock model | `web-ui/spec/event-log-ordering-and-clock-rules-v1.md`, `web-ui/spec/perf-telemetry-sampling-policy-v1.md` | 1) Add clock profile for realtime tick alignment after `Section 3. Clock Profiles`. 2) Add telemetry fields for realtime loop drift in sampling policy. | `realtime-tick-v1` clock profile, tick/frame drift metrics, simulation vs UI turn timing boundaries. | Add `web-ui/tests/realtime-clock-profile.test.mjs`. |
| `SR-14` Protocol evolution pressure | `web-ui/spec/protocol-version-negotiation-v1.md`, `web-ui/spec/spec-ratification-policy-v1.md` | 1) Add extension registry process in `Section 7. Deprecation Policy` and mixed-version policy in `Section 8`. 2) Add mandatory extension-review gate in ratification policy. | Profile/extension registry for high-rate and realtime lanes, stricter cross-version soak requirements before enabling new kinds/types. | Extend conformance lint to require extension registry entries for new kind/type IDs. |

## New Specs Required (Cross-Cutting Gaps)

Add these files under `web-ui/spec/`:

1. `input-backpressure-and-coalescing-contract-v1.md`
2. `bridge-qos-and-lane-contract-v1.md`
3. `app-tenant-isolation-and-quotas-contract-v1.md`
4. `realtime-surface-profile-v1.md`
5. `asset-streaming-and-binary-state-contract-v1.md`

Suggested `spec-index-v1.md` placement:

1. Core transport/protocol group:
   1. `bridge-qos-and-lane-contract-v1.md`
   2. `input-backpressure-and-coalescing-contract-v1.md`
2. Security/operations group:
   1. `app-tenant-isolation-and-quotas-contract-v1.md`
3. Performance/scale group:
   1. `realtime-surface-profile-v1.md`
4. Persistence/storage group:
   1. `asset-streaming-and-binary-state-contract-v1.md`

## Gate Profile Patches

Patch `web-ui/spec/conformance-gate-profiles-v1.md`:

1. Insert new gate row after `gate.runtime.bridge.v1`:
   1. `gate.runtime.input-flood.v1` -> pointer/hover/drag saturation + coalescing determinism tests.
2. Insert new gate row after `gate.tests.fast.v1`:
   1. `gate.runtime.qos-contention.v1` -> multi-lane starvation and admission control tests.
3. Insert new gate row after `gate.browser.render-only.v1`:
   1. `gate.runtime.realtime-profile.v1` -> realtime profile replay and drift checks.

## Observability Patch Points

Patch `web-ui/spec/observability-contract-v1.md`:

1. Extend `Section 3.2 IPC and Runtime Bridge Records` with:
   1. `ui_input_queue_depth`
   2. `ui_input_queue_bytes`
   3. `ui_input_events_coalesced`
   4. `ui_input_events_dropped`
   5. `runtime_command_inflight`
   6. Per-lane saturation counters
2. Extend `Section 4. Correlation Contract` with `tenant_id` and `workload_profile_id`.

## Implementation Touchpoints (Non-Normative)

Primary code files likely affected once spec patches are accepted:

1. `web-ui/bridge/ui-bridge.mjs`
2. `web-ui/bridge/codec.mjs`
3. `scripts/wasm/lib/microkernel.mjs`
4. `web-ui/src/runtime-command-client.mjs`
5. `web-ui/src/quality-gates.mjs`
6. `web-ui/src/state.mjs`

## Sequencing Recommendation

1. Land `SR-01/SR-02/SR-06` first (input flood safety).
2. Then land `SR-03/SR-07/SR-08` (QoS + workload profiles).
3. Then land `SR-04/SR-10` (tenant isolation/capability scope).
4. Then land `SR-09/SR-11/SR-12/SR-13/SR-14` (asset split + realtime evolution guardrails).

This sequence minimizes risk of early protocol churn.

