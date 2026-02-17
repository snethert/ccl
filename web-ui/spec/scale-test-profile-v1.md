# Scale Test Profile v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-16  
Scope: Normative scale/performance test profile, fixture lanes, and acceptance gates for `web-ui` large-data and stress scenarios  
Depends on: `web-ui/spec/performance-slo-and-budgets-v1.md`, `web-ui/spec/perf-telemetry-sampling-policy-v1.md`, `web-ui/spec/normative-language-and-conformance-v1.md`  
Compatibility: `v1.x` preserves profile lane names and acceptance gates; incompatible lane/gate model changes require `v2`.

## 1. Purpose

This contract defines the production scale test profile for `web-ui`.
It specifies mandatory scale lanes, execution rules, and pass/fail criteria.

## 2. Profile Identifier

Canonical profile ID: `web-ui-scale-v1`.

A scale conformance claim <a id="REQ-SCALE-TEST-PROFILE-V1-96FF7BB35A"></a>MUST reference this exact profile ID.

## 3. Required Scale Lanes

A conformant run <a id="REQ-SCALE-TEST-PROFILE-V1-EE6FF5BF64"></a>MUST execute all lanes:

1. `transcript-10k-lane`
2. `virtualization-window-lane`
3. `dirty-redraw-lane`
4. `quality-gate-integration-lane`
5. `reliability-replay-lane`

## 4. Lane Definitions

## 4.1 `transcript-10k-lane`

Purpose: verify transcript behavior at 10k-entry scale.

Required checks:

1. Transcript window limit behavior remains deterministic.
2. Snapshot truncation and restore round-trip remain deterministic.
3. Scale gate supports at least `10000` entries.

Primary evidence:

1. `web-ui/tests/phase-7-transcript-scale.test.mjs`

## 4.2 `virtualization-window-lane`

Purpose: verify virtual list/tree/table visible-window bounds.

Required checks:

1. Visible range start/end and total counts are deterministic.
2. Visible row count does not exceed expected bound.
3. Virtual spacers and row positioning remain deterministic.

Primary evidence:

1. `web-ui/tests/widgets-virtualization.test.mjs`
2. `web-ui/tests/phase-7-integration.test.mjs`

## 4.3 `dirty-redraw-lane`

Purpose: verify bounded redraw behavior under dirty hints.

Required checks:

1. Canvas dirty rects clear/draw only intersecting regions.
2. WebGL clipped redraw path preserves deterministic coverage.
3. Full redraw with dirty hints is flagged by quality gate.

Primary evidence:

1. `web-ui/tests/canvas-dirty-rects.test.mjs`
2. `web-ui/tests/phase-7-performance-budgets.test.mjs`
3. `web-ui/tests/phase-3-renderer-parity.test.mjs`

## 4.4 `quality-gate-integration-lane`

Purpose: validate integrated SLO evaluation over representative interaction flow.

Required checks:

1. UI-turn, render, virtualization, transcript, and reliability sample lanes are all populated.
2. Evaluation report contains all mandatory gate IDs.
3. Report passes for nominal representative flow.

Primary evidence:

1. `web-ui/tests/phase-7-integration.test.mjs`
2. `web-ui/tests/phase-7-performance-budgets.test.mjs`

## 4.5 `reliability-replay-lane`

Purpose: validate deterministic replay and degraded runtime fault handling.

Required checks:

1. Repeated replay runs produce stable outputs.
2. Nondeterministic replay is detected by reliability gate.
3. Malformed runtime messages degrade safely without unhandled exceptions.

Primary evidence:

1. `web-ui/tests/phase-7-reliability.test.mjs`

## 5. Execution Methodology

1. Runs <a id="REQ-SCALE-TEST-PROFILE-V1-FAB35A06AE"></a>MUST execute with deterministic seed/time controls where harnesses support them.
2. Lane order <a id="REQ-SCALE-TEST-PROFILE-V1-651DBF138E"></a>MUST be deterministic and stable:
- `transcript-10k-lane`
- `virtualization-window-lane`
- `dirty-redraw-lane`
- `quality-gate-integration-lane`
- `reliability-replay-lane`
3. Repeated runs with identical inputs <a id="REQ-SCALE-TEST-PROFILE-V1-0A897FEE7D"></a>MUST produce identical pass/fail verdicts.
4. Any skipped lane <a id="REQ-SCALE-TEST-PROFILE-V1-D07B300862"></a>MUST fail overall profile conformance.

## 6. Acceptance Gates

The profile <a id="REQ-SCALE-TEST-PROFILE-V1-C8EE2465B7"></a>MUST enforce all mandatory gate IDs from `performance-slo-and-budgets-v1.md`:

1. `ui-turn-p95`
2. `ui-turn-p99`
3. `render-no-full-redraw-with-dirty-hints`
4. `virtualization-visible-window-bounds`
5. `transcript-supported-scale`
6. `reliability-unhandled-runtime-faults`
7. `reliability-deterministic-replay`

Profile verdict <a id="REQ-SCALE-TEST-PROFILE-V1-147AAC93A7"></a>MUST be `pass` only when:

1. Every required lane in Section 3 passes.
2. Every mandatory gate in Section 6 passes.

## 7. Report Contract

Scale profile report <a id="REQ-SCALE-TEST-PROFILE-V1-C7823C99AF"></a>MUST include:

1. `profileId`
2. `schemaVersion`
3. `laneResults[]`
4. `budgetReport`
5. `startedAt`
6. `endedAt`
7. `sourceRevision`

Each `laneResults[]` entry <a id="REQ-SCALE-TEST-PROFILE-V1-A576ED4EF1"></a>MUST include:

1. `laneId`
2. `ok`
3. `checks[]`
4. `artifacts[]`

## 8. Determinism and Tie-Break Rules

1. Lane verdict precedence is deterministic: first failing lane in Section 5 order anchors top-level failure reason.
2. Budget check ordering <a id="REQ-SCALE-TEST-PROFILE-V1-CD9D868319"></a>MUST follow Section 6 ordering.
3. Transcript and virtualization list ordering <a id="REQ-SCALE-TEST-PROFILE-V1-D7FE85B858"></a>MUST remain stable across runs.

## 9. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `scale-profile.lane-missing` | Required scale lane did not execute. | No | Execute all required lanes. |
| `scale-profile.lane-failed` | One or more lane checks failed. | Conditional | Investigate failing lane checks and re-run. |
| `scale-profile.budget-failed` | Mandatory SLO budget check failed. | Conditional | Optimize behavior or adjust approved budget policy. |
| `scale-profile.report-invalid` | Scale report missing required contract fields. | No | Regenerate report with required fields. |
| `scale-profile.nondeterministic-run` | Repeated run produced divergent verdicts/artifacts. | Conditional | Remove nondeterministic factors and re-run. |

## 10. Conformance Fixtures and Pass Criteria

Minimum required evidence:

1. `web-ui/tests/phase-7-transcript-scale.test.mjs`
2. `web-ui/tests/widgets-virtualization.test.mjs`
3. `web-ui/tests/canvas-dirty-rects.test.mjs`
4. `web-ui/tests/phase-7-performance-budgets.test.mjs`
5. `web-ui/tests/phase-7-integration.test.mjs`
6. `web-ui/tests/phase-7-reliability.test.mjs`

Pass criteria:

1. All required lanes execute and pass.
2. Mandatory budget checks pass.
3. Repeated run determinism checks pass.

## 11. Conformance

An implementation is conformant only if Sections 3-10 are satisfied.
