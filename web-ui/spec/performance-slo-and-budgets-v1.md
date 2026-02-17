# Performance SLO and Budgets v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-16  
Scope: Normative performance/reliability service-level objectives and budget gates for `web-ui` quality evaluation  
Depends on: `web-ui/spec/normative-language-and-conformance-v1.md`, `web-ui/src/quality-gates.mjs`, `web-ui/spec/perf-telemetry-sampling-policy-v1.md`  
Compatibility: `v1.x` preserves budget field names, gate IDs, and percentile semantics; incompatible gate semantics require `v2`.

## 1. Purpose

This contract defines canonical performance and reliability budgets for `web-ui`.
It is normative for quality gate evaluation and release pass/fail decisions.

## 2. Budget Groups and Defaults

The default budget profile (`quality-budgets-default-v1`) is:

| Group | Field | Default |
|---|---|---|
| `uiTurn` | `p95Ms` | `16` |
| `uiTurn` | `p99Ms` | `32` |
| `render` | `forbidFullRedrawWithDirtyHints` | `true` |
| `virtualization` | `enforceVisibleWindowBounds` | `true` |
| `transcript` | `minSupportedEntries` | `10000` |
| `reliability` | `maxUnhandledRuntimeFaults` | `0` |
| `reliability` | `requireDeterministicReplay` | `true` |

## 3. Budget Override Rules

Budget overrides <a id="REQ-PERFORMANCE-SLO-AND-BUDGETS-V1-A74FD9CBCA"></a>MUST be applied field-by-field to defaults.

Rules:

1. Unknown override fields <a id="REQ-PERFORMANCE-SLO-AND-BUDGETS-V1-8E95539B8B"></a>MUST be ignored.
2. Numeric overrides <a id="REQ-PERFORMANCE-SLO-AND-BUDGETS-V1-AAC59C89A8"></a>MUST be clamped to non-negative values where applicable.
3. Boolean overrides <a id="REQ-PERFORMANCE-SLO-AND-BUDGETS-V1-61BB08C59F"></a>MUST preserve explicit true/false values.
4. Missing groups in overrides <a id="REQ-PERFORMANCE-SLO-AND-BUDGETS-V1-91C8C4BA1F"></a>MUST retain default values.

## 4. Gate Evaluation Model

Budget evaluation produces a deterministic report with:

1. `ok`
2. `checks[]`
3. `failedChecks[]`
4. `summary` (`totalChecks`, `passedChecks`, `failedChecks`)

Each check <a id="REQ-PERFORMANCE-SLO-AND-BUDGETS-V1-6B024310E0"></a>MUST include:

1. `id`
2. `ok`
3. `actual`
4. `expected`
5. `details`

## 5. Normative Gate IDs and Semantics

The following gate IDs are mandatory in `v1`:

1. `ui-turn-p95`
2. `ui-turn-p99`
3. `render-no-full-redraw-with-dirty-hints`
4. `virtualization-visible-window-bounds`
5. `transcript-supported-scale`
6. `reliability-unhandled-runtime-faults`
7. `reliability-deterministic-replay`

### 5.1 UI Turn Percentiles

1. UI turn percentiles <a id="REQ-PERFORMANCE-SLO-AND-BUDGETS-V1-D761175AC6"></a>MUST use nearest-rank percentile over recorded non-negative `durationMs` values.
2. Empty sample sets <a id="REQ-PERFORMANCE-SLO-AND-BUDGETS-V1-F720154BB3"></a>MUST not fail percentile checks.
3. `ui-turn-p95` <a id="REQ-PERFORMANCE-SLO-AND-BUDGETS-V1-C58D11C2FE"></a>MUST pass when `p95 <= uiTurn.p95Ms`.
4. `ui-turn-p99` <a id="REQ-PERFORMANCE-SLO-AND-BUDGETS-V1-8AE0810792"></a>MUST pass when `p99 <= uiTurn.p99Ms`.

### 5.2 Render Dirty-Redraw Policy

1. A render violation is any sample with `dirtyHintCount > 0` and `fullRedraw = true`.
2. `render-no-full-redraw-with-dirty-hints` <a id="REQ-PERFORMANCE-SLO-AND-BUDGETS-V1-4ECE06F96E"></a>MUST fail when violations exist and gate is enabled.

### 5.3 Virtualization Window Bounds

1. A virtualization violation is any sample with `visibleCount > expectedMaxVisible` when enforcement is enabled.
2. Missing/non-finite `expectedMaxVisible` <a id="REQ-PERFORMANCE-SLO-AND-BUDGETS-V1-7D8DB93F72"></a>MUST be treated as non-actionable for this gate.

### 5.4 Transcript Scale Support

1. `transcript-supported-scale` <a id="REQ-PERFORMANCE-SLO-AND-BUDGETS-V1-76AEA4ACDF"></a>MUST evaluate the maximum observed `entryCount` across transcript samples.
2. Gate <a id="REQ-PERFORMANCE-SLO-AND-BUDGETS-V1-3CA1BB63B2"></a>MUST pass when `maxEntryCount >= transcript.minSupportedEntries`.
3. Empty transcript samples <a id="REQ-PERFORMANCE-SLO-AND-BUDGETS-V1-4EF3B4DBA8"></a>MUST not fail this gate.

### 5.5 Reliability Gates

1. `reliability-unhandled-runtime-faults` <a id="REQ-PERFORMANCE-SLO-AND-BUDGETS-V1-A50E785A90"></a>MUST compare runtime fault sample count against `maxUnhandledRuntimeFaults`.
2. `reliability-deterministic-replay` <a id="REQ-PERFORMANCE-SLO-AND-BUDGETS-V1-3E4E9EE5B2"></a>MUST fail when any replay-run sample reports `deterministic=false` and enforcement is enabled.

## 6. Release Policy Requirements

1. Production promotion <a id="REQ-PERFORMANCE-SLO-AND-BUDGETS-V1-D5BFA8D813"></a>MUST require all mandatory gate IDs to pass.
2. Any failed mandatory gate <a id="REQ-PERFORMANCE-SLO-AND-BUDGETS-V1-3776F2BCF8"></a>MUST block release unless an explicit waiver exists.
3. Waivers <a id="REQ-PERFORMANCE-SLO-AND-BUDGETS-V1-E9A002462D"></a>MUST include gate ID, rationale, owner, and expiry date.
4. Waivers <a id="REQ-PERFORMANCE-SLO-AND-BUDGETS-V1-BAECA2D21B"></a>MUST be versioned and auditable.

## 7. Determinism and Tie-Break Rules

1. Gate evaluation order <a id="REQ-PERFORMANCE-SLO-AND-BUDGETS-V1-E8F7D3E2B4"></a>MUST be stable and match Section 5 order.
2. Percentile calculation <a id="REQ-PERFORMANCE-SLO-AND-BUDGETS-V1-7254A90232"></a>MUST be deterministic for identical sample arrays.
3. Check IDs <a id="REQ-PERFORMANCE-SLO-AND-BUDGETS-V1-F860B79B92"></a>MUST remain stable across `v1.x`.

## 8. Compatibility and Deprecation

1. New gate IDs in `v1.x` MAY be added only as non-breaking additions.
2. Existing gate IDs <a id="REQ-PERFORMANCE-SLO-AND-BUDGETS-V1-EC19373EE9"></a>MUST NOT be renamed or removed in `v1.x`.
3. Changing percentile algorithm or required gate semantics requires `v2`.

## 9. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `performance-budget.check-failed` | At least one mandatory gate failed. | Conditional | Address failing checks or apply time-bound waiver. |
| `performance-budget.invalid-override` | Override payload has invalid field types/values. | No | Correct override schema and retry. |
| `performance-budget.percentile-input-invalid` | Percentile source data is malformed. | Conditional | Fix telemetry input normalization and re-evaluate. |
| `performance-budget.report-incomplete` | Required gate IDs absent from report. | No | Regenerate report with full gate set. |

## 10. Conformance Fixtures and Pass Criteria

Minimum required evidence:

1. `web-ui/tests/phase-7-performance-budgets.test.mjs`
2. `web-ui/tests/phase-7-integration.test.mjs`
3. `web-ui/tests/phase-7-reliability.test.mjs`

Pass criteria:

1. Pass/fail coverage proves every mandatory gate ID in Section 5.
2. Percentile and reliability checks are deterministic across repeated runs.
3. Gate report shape and IDs remain stable.

## 11. Conformance

An implementation is conformant only if all conditions hold:

1. Default and override behavior matches Sections 2-3.
2. Mandatory gate IDs and semantics match Section 5.
3. Determinism and release policy obligations match Sections 6-7.
