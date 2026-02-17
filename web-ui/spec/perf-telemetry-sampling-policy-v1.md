# Performance Telemetry Sampling Policy v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-16  
Scope: Normative sampling, normalization, retention, and export policy for `web-ui` quality telemetry  
Depends on: `web-ui/spec/normative-language-and-conformance-v1.md`, `web-ui/src/quality-gates.mjs`, `web-ui/spec/performance-slo-and-budgets-v1.md`  
Compatibility: `v1.x` preserves sample lane names, field normalization, and retention defaults; incompatible telemetry schema changes require `v2`.

## 1. Purpose

This contract defines how `web-ui` quality telemetry is sampled, normalized, retained, and evaluated.
It is normative for the `createQualityCollector` integration used by runtime, renderer, widgets, and reliability lanes.

## 2. Telemetry Schema Version

1. Collector schema version <a id="REQ-PERF-TELEMETRY-SAMPLING-POLICY-V1-FC91C57E25"></a>MUST be `1`.
2. Snapshot/export payloads <a id="REQ-PERF-TELEMETRY-SAMPLING-POLICY-V1-BD59487C13"></a>MUST carry this version.

## 3. Sample Lanes

The collector <a id="REQ-PERF-TELEMETRY-SAMPLING-POLICY-V1-E65C1833EA"></a>MUST provide these lanes:

1. `uiTurns`
2. `renders`
3. `virtualization`
4. `transcript`
5. `reliability`

## 4. Sampling Model

1. Sampling is event-driven and append-only per lane.
2. `v1` sampling mode is full sampling (no probabilistic down-sampling).
3. Every valid `record*` call <a id="REQ-PERF-TELEMETRY-SAMPLING-POLICY-V1-9027197F05"></a>MUST increment its lane counter.
4. Samples <a id="REQ-PERF-TELEMETRY-SAMPLING-POLICY-V1-CD06DF3A88"></a>MUST be normalized before insertion.

## 5. Timestamp Policy

For each sample:

1. If sample includes finite `ts`, that value <a id="REQ-PERF-TELEMETRY-SAMPLING-POLICY-V1-9F7FF0101F"></a>MUST be used.
2. Otherwise collector <a id="REQ-PERF-TELEMETRY-SAMPLING-POLICY-V1-82D8D53022"></a>MUST use `now()` when supplied.
3. If no `now()` is supplied, collector <a id="REQ-PERF-TELEMETRY-SAMPLING-POLICY-V1-4013DA473B"></a>MUST use `Date.now()`.

## 6. Normalization Rules by Lane

## 6.1 `uiTurns`

Normalized fields:

1. `turnId` (string or null)
2. `phase` (string or null)
3. `yielded` (boolean)
4. `commitPolicy` (string or null)
5. `signalCount` (non-negative integer)
6. `durationMs` (non-negative number or null)
7. `ts` (finite number)

## 6.2 `renders`

Normalized fields:

1. `surface` (string; default `unknown`)
2. `backend` (string; default `unknown`)
3. `operation` (string or null)
4. `fullRedraw` (boolean)
5. `dirtyHintCount` (non-negative integer)
6. `dirtyRectCount` (non-negative integer)
7. `drawnNodeCount` (non-negative integer)
8. `totalNodeCount` (non-negative integer)
9. `durationMs` (non-negative number or null)
10. `ts` (finite number)

## 6.3 `virtualization`

Normalized fields:

1. `widgetKind` (string; default `unknown`)
2. `widgetId` (string or null)
3. `totalCount` (non-negative integer)
4. `visibleCount` (non-negative integer)
5. `start` (non-negative integer)
6. `end` (non-negative integer)
7. `expectedMaxVisible` (non-negative integer)
8. `rowHeight` (number or null)
9. `viewportHeight` (number or null)
10. `overscan` (non-negative integer)
11. `ts` (finite number)

## 6.4 `transcript`

Normalized fields:

1. `entryCount` (non-negative integer)
2. `recordingCount` (non-negative integer)
3. `truncatedEntries` (non-negative integer)
4. `mode` (string; default `unknown`)
5. `ts` (finite number)

## 6.5 `reliability`

Normalized fields:

1. `kind` (string; default `unknown`)
2. `deterministic` (boolean or null)
3. `handled` (boolean or null)
4. `message` (string or null)
5. `details` (JSON-cloned object)
6. `ts` (finite number)

## 7. Retention Policy

Collectors <a id="REQ-PERF-TELEMETRY-SAMPLING-POLICY-V1-EA32F3AE22"></a>MUST apply bounded retention per lane.

Default limits:

1. `uiTurns=512`
2. `renders=1024`
3. `virtualization=1024`
4. `transcript=128`
5. `reliability=256`

Rules:

1. Limits <a id="REQ-PERF-TELEMETRY-SAMPLING-POLICY-V1-6D92BCB3BD"></a>MUST be positive integers.
2. On overflow, oldest entries <a id="REQ-PERF-TELEMETRY-SAMPLING-POLICY-V1-7AC7C016B7"></a>MUST be dropped first.
3. Counter totals <a id="REQ-PERF-TELEMETRY-SAMPLING-POLICY-V1-EE4F7D4E53"></a>MUST continue increasing even when sample arrays are trimmed.

## 8. Source Emission Requirements

The following emitters <a id="REQ-PERF-TELEMETRY-SAMPLING-POLICY-V1-D2EC4DC462"></a>MUST remain wired in `v1`:

1. UI turn lifecycle (`beginUiTurn`, `advanceUiTurn`, `yieldUiTurn`, `endUiTurn`) -> `uiTurns`.
2. Root renderer and backend render operations -> `renders`.
3. Virtual list/tree/table render paths -> `virtualization`.
4. Transcript scale/truncation checks -> `transcript`.
5. Runtime bridge and replay reliability hooks -> `reliability`.

## 9. Snapshot and Reset Policy

1. `snapshot()` <a id="REQ-PERF-TELEMETRY-SAMPLING-POLICY-V1-3BDD5B37DA"></a>MUST return a deep-cloned telemetry structure.
2. Snapshot <a id="REQ-PERF-TELEMETRY-SAMPLING-POLICY-V1-FA5B252DBF"></a>MUST be side-effect free.
3. `reset()` <a id="REQ-PERF-TELEMETRY-SAMPLING-POLICY-V1-7651EA768A"></a>MUST clear all lane samples and counters.

## 10. Determinism and Tie-Break Rules

1. Append order <a id="REQ-PERF-TELEMETRY-SAMPLING-POLICY-V1-75752FEA97"></a>MUST reflect call order.
2. Retention trimming <a id="REQ-PERF-TELEMETRY-SAMPLING-POLICY-V1-93617123DA"></a>MUST preserve newest `N` samples deterministically.
3. Normalization of invalid numeric values <a id="REQ-PERF-TELEMETRY-SAMPLING-POLICY-V1-BC5EC22B96"></a>MUST converge to deterministic fallback values.

## 11. Security and Privacy Requirements

1. Telemetry details <a id="REQ-PERF-TELEMETRY-SAMPLING-POLICY-V1-74C0CAB918"></a>MUST be treated as diagnostic data and SHOULD avoid sensitive payload leakage.
2. Collector integrations <a id="REQ-PERF-TELEMETRY-SAMPLING-POLICY-V1-7E6BE74503"></a>MUST avoid embedding raw host object references in samples.
3. JSON clone fallback behavior for details <a id="REQ-PERF-TELEMETRY-SAMPLING-POLICY-V1-A210537CCF"></a>MUST avoid throwing into caller paths.

## 12. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `perf-telemetry.invalid-sample` | Sample payload cannot be normalized safely. | Conditional | Correct sample shape and retry. |
| `perf-telemetry.limit-invalid` | Retention limit override is invalid. | No | Provide positive integer limits. |
| `perf-telemetry.snapshot-failed` | Snapshot cloning failed unexpectedly. | Conditional | Reduce unsupported payload shapes in details field. |
| `perf-telemetry.emitter-missing` | Required source lane is not emitting expected samples. | Conditional | Reconnect instrumentation hook and re-run fixtures. |

## 13. Conformance Fixtures and Pass Criteria

Minimum required evidence:

1. `web-ui/tests/phase-7-performance-budgets.test.mjs`
2. `web-ui/tests/phase-7-integration.test.mjs`
3. `web-ui/tests/phase-7-reliability.test.mjs`
4. `web-ui/tests/widgets-virtualization.test.mjs`

Pass criteria:

1. Collector snapshots include all lanes and counters.
2. Retention trimming and counter behavior are deterministic.
3. Normalized sample fields match Section 6 contracts.
4. Source hooks from Section 8 produce non-empty samples in integration flow.

## 14. Conformance

An implementation is conformant only if Sections 2-13 are satisfied.
