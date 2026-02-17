# Event Log Ordering and Clock Rules v1

Status: Draft  
Version: 1.1.0  
Last updated: 2026-02-16  
Scope: Deterministic ordering, clock semantics, replay rules, and failure behavior for `web-ui` event logs  
Depends on: `web-ui/spec/event-log-schema-v1.json`, `web-ui/spec/normative-language-and-conformance-v1.md`, `web-ui/DEV-PLAN.md`  
Compatibility: `v1.x` preserves ordering and clock semantics; `v1.1+` adds retention and rotation policy without changing replay order semantics.

## 1. Purpose

This contract defines deterministic ordering and clock semantics for replayable `web-ui` event logs.
It is normative for event recording, validation, replay, and partial replay.

## 2. Event Order Model

Event order is defined by `seq` (sequence number) in `event-log-schema-v1.json`.

Rules:

1. `seq` <a id="REQ-EVENT-LOG-ORDERING-AND-CLOCK-RULES-V1-8BE29DF4B0"></a>MUST be an integer in `[0, 2^53-1]`.
2. `seq` <a id="REQ-EVENT-LOG-ORDERING-AND-CLOCK-RULES-V1-95ECA7D3EF"></a>MUST be unique within a log.
3. `seq` <a id="REQ-EVENT-LOG-ORDERING-AND-CLOCK-RULES-V1-AB3771014E"></a>MUST increase strictly by position in `events[]`.
4. Replayers <a id="REQ-EVENT-LOG-ORDERING-AND-CLOCK-RULES-V1-D4B403F665"></a>MUST treat `seq` as authoritative order, not array insertion time, wall clock, or host callback order.
5. Logs with duplicate or non-increasing `seq` <a id="REQ-EVENT-LOG-ORDERING-AND-CLOCK-RULES-V1-219E67EF13"></a>MUST be rejected as invalid.

## 3. Timestamp and Clock Semantics

### 3.1 Clock Profiles

`clockProfile` has two normative values:

1. `monotonic-ms-v1`
2. `logical-step-v1`

### 3.2 `monotonic-ms-v1`

1. `ts` values, when present, <a id="REQ-EVENT-LOG-ORDERING-AND-CLOCK-RULES-V1-363C6915EB"></a>MUST be non-negative integer milliseconds from a monotonic source.
2. `ts` <a id="REQ-EVENT-LOG-ORDERING-AND-CLOCK-RULES-V1-F20CE56A9A"></a>MUST be non-decreasing with increasing `seq`.
3. `ts` MAY have equal adjacent values when events occur within the same clock tick.
4. Wall-clock time <a id="REQ-EVENT-LOG-ORDERING-AND-CLOCK-RULES-V1-E5DA3F02C7"></a>MUST NOT be used to reorder events.

### 3.3 `logical-step-v1`

1. `ts` MAY be omitted.
2. If `ts` is present, it <a id="REQ-EVENT-LOG-ORDERING-AND-CLOCK-RULES-V1-FF74F32BE6"></a>MUST be non-decreasing integer logical time.
3. Determinism depends on `seq`; `ts` is diagnostic in this profile.

### 3.4 Missing `ts`

1. Writers SHOULD include `ts` for `monotonic-ms-v1`.
2. For synthetic deterministic harness logs, `ts` MAY be omitted when `clockProfile=logical-step-v1`.
3. Legacy `version="0"` logs MAY omit `ts`.

## 4. Canonical Event Families

Canonical families are:

1. `command`
2. `focus`
3. `pointer`
4. `keyboard`
5. `layout`
6. `job`
7. `snapshot`

Additional namespaced families (for example `recording:*`, `ui:*`, `runtime:*`) MAY be used if they satisfy schema and determinism constraints.

## 5. Replay Semantics

1. Replay engines <a id="REQ-EVENT-LOG-ORDERING-AND-CLOCK-RULES-V1-CE9A7DF2C6"></a>MUST validate log schema before execution.
2. Replay engines <a id="REQ-EVENT-LOG-ORDERING-AND-CLOCK-RULES-V1-113605FA68"></a>MUST process non-`snapshot` events in increasing `seq`.
3. `snapshot` events <a id="REQ-EVENT-LOG-ORDERING-AND-CLOCK-RULES-V1-DE4DE6A4A4"></a>MUST capture post-state after all prior non-`snapshot` events have applied.
4. Replay engines <a id="REQ-EVENT-LOG-ORDERING-AND-CLOCK-RULES-V1-2A590AFBB1"></a>MUST fail deterministic runs when unknown event types are encountered unless an explicit extension handler is installed.
5. Extension handlers <a id="REQ-EVENT-LOG-ORDERING-AND-CLOCK-RULES-V1-A169011002"></a>MUST be deterministic for fixed `(state, event, handler-config)`.

## 6. Partial Replay Rules

Partial replay over `[startSeq, endSeq]` is inclusive.

Rules:

1. Events with `seq < startSeq` <a id="REQ-EVENT-LOG-ORDERING-AND-CLOCK-RULES-V1-50D1D090AB"></a>MUST be excluded.
2. Events with `seq > endSeq` <a id="REQ-EVENT-LOG-ORDERING-AND-CLOCK-RULES-V1-0E99DDDBEF"></a>MUST be excluded.
3. If `startSeq > endSeq`, replay request <a id="REQ-EVENT-LOG-ORDERING-AND-CLOCK-RULES-V1-7A6D1142BB"></a>MUST fail.
4. If requested `startSeq` does not exist, the engine MAY start at the first event with `seq > startSeq` only when explicitly configured; otherwise it <a id="REQ-EVENT-LOG-ORDERING-AND-CLOCK-RULES-V1-700BD21460"></a>MUST fail.
5. Partial replay mode <a id="REQ-EVENT-LOG-ORDERING-AND-CLOCK-RULES-V1-492B28CA1E"></a>MUST be recorded in diagnostics/report output.

## 7. Retention and Rotation Policy

Default retention profile (`event-log-retention-v1`):

1. `max_events = 10000`
2. `max_bytes = 33554432` (32 MiB serialized envelope budget)
3. Rotation policy `ring-buffer-drop-oldest`
4. Snapshot cadence hint: at least one checkpoint per 512 non-snapshot events

Retention rules:

1. Implementations <a id="REQ-EVENT-LOG-ORDERING-AND-CLOCK-RULES-V1-EECDC72672"></a>MUST enforce both `max_events` and `max_bytes` bounds.
2. When limits are exceeded, rotation <a id="REQ-EVENT-LOG-ORDERING-AND-CLOCK-RULES-V1-8CEF9316EC"></a>MUST evict oldest events first while preserving strict `seq` ordering of retained entries.
3. Rotation <a id="REQ-EVENT-LOG-ORDERING-AND-CLOCK-RULES-V1-9ABFFADCCB"></a>MUST emit diagnostics with pre/post ranges (`firstSeq`, `lastSeq`, `evictedCount`, `evictedBytes`).
4. Retention enforcement <a id="REQ-EVENT-LOG-ORDERING-AND-CLOCK-RULES-V1-318080297D"></a>MUST NOT block command execution; on retention failure, recording degrades with explicit error code.
5. Retained logs <a id="REQ-EVENT-LOG-ORDERING-AND-CLOCK-RULES-V1-5CAE86BF08"></a>MUST remain schema-valid and replayable.

## 8. Determinism and Tie-Break Rules

1. There is no legal tie for `seq`; ties are invalid.
2. For merged multi-source logs, implementations <a id="REQ-EVENT-LOG-ORDERING-AND-CLOCK-RULES-V1-13DFC97A87"></a>MUST normalize into one strictly increasing `seq` stream before replay.
3. If merge requires deterministic tie-breaking, source order <a id="REQ-EVENT-LOG-ORDERING-AND-CLOCK-RULES-V1-18F26A803C"></a>MUST be fixed by stable source ID lexical order before reassignment.
4. Randomized handlers <a id="REQ-EVENT-LOG-ORDERING-AND-CLOCK-RULES-V1-16A23C6078"></a>MUST be seeded; seed value <a id="REQ-EVENT-LOG-ORDERING-AND-CLOCK-RULES-V1-621F56AD31"></a>MUST be recorded in the log envelope or replay report.

## 9. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `event-log.seq.invalid` | `seq` missing, non-integer, negative, or out of range. | No | Regenerate/repair log. |
| `event-log.seq.non-monotonic` | `seq` not strictly increasing. | No | Reorder/rebuild log deterministically. |
| `event-log.seq.duplicate` | Duplicate `seq` value detected. | No | Resolve duplicate at source. |
| `event-log.ts.invalid` | `ts` violates active `clockProfile` constraints. | Conditional | Fix timestamp source/profile mapping. |
| `event-log.type.unsupported` | Event type has no handler in strict replay mode. | Conditional | Install deterministic handler or remove event. |
| `event-log.partial-range.invalid` | Partial replay range is invalid. | No | Correct range request. |
| `event-log.retention-config-invalid` | Retention max values are missing/invalid. | No | Provide valid retention limits and restart recorder. |
| `event-log.retention-write-failed` | Rotation/retention could not persist bounded log state. | Conditional | Repair storage and retry recorder initialization. |

## 10. Compatibility and Migration

1. `version="0"` logs MAY be imported.
2. Importers SHOULD normalize imported logs to `version="1.0.0"` before persistence.
3. Normalization <a id="REQ-EVENT-LOG-ORDERING-AND-CLOCK-RULES-V1-D40F67CE39"></a>MUST preserve `seq` order and event payload semantics.
4. Importers <a id="REQ-EVENT-LOG-ORDERING-AND-CLOCK-RULES-V1-347CB07CAD"></a>MUST NOT invent synthetic `seq` gaps or reorder payload effects.

## 11. Conformance Fixtures and Pass Criteria

Minimum required conformance evidence:

1. `web-ui/tests/basic.test.mjs`: deterministic replay with stable snapshot output.
2. `web-ui/tests/layout.test.mjs`: deterministic snapshot stability under layout mutations.
3. `web-ui/tests/event-log-buffer.test.mjs`: deterministic sequence retention behavior in ring-buffer mode.
4. `web-ui/tests/recordings.test.mjs`: monotonic sequence enforcement in recording streams.

Pass criteria:

1. Re-running each fixture with identical inputs yields identical snapshot strings and replay outcomes.
2. No fixture may pass with non-monotonic or duplicate `seq` input.
3. Any schema violation <a id="REQ-EVENT-LOG-ORDERING-AND-CLOCK-RULES-V1-751B8FFB3C"></a>MUST surface one stable failure code from Section 8.

## 12. Conformance

An implementation is conformant only if:

1. Event ordering is enforced exactly as specified in Section 2.
2. Clock semantics are enforced per Section 3.
3. Replay and partial replay behavior satisfy Sections 5-6.
4. Determinism and failure semantics satisfy Sections 7-8.
