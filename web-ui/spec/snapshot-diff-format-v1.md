# Snapshot Diff Format v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-16  
Scope: Canonical diff envelope and operation semantics for deterministic `web-ui` snapshot comparison  
Depends on: `web-ui/spec/snapshot-schema-v1.json`, `web-ui/spec/normative-language-and-conformance-v1.md`, `web-ui/DEV-PLAN.md`  
Compatibility: `v1.x` preserves diff operation semantics and ordering; incompatible operation changes require `v2`.

## 1. Purpose

This contract defines the stable diff format used by golden snapshot tests and replay diagnostics.
It is the normative output model for `ui:diff-snapshots`.

## 2. Diff Envelope

A snapshot diff is a JSON object with these required fields:

| Field | Type | Required | Description |
|---|---|---|---|
| `version` | string | yes | Diff format version. MUST be `1.0.0`. |
| `baseSnapshotHash` | string | yes | `sha256:<64-hex>` hash of canonical base snapshot string. |
| `targetSnapshotHash` | string | yes | `sha256:<64-hex>` hash of canonical target snapshot string. |
| `generatedAt` | integer | yes | Non-negative timestamp in active clock profile units. |
| `stats` | object | yes | Aggregate operation counts. |
| `entries` | array | yes | Ordered diff entries. |

Optional fields:

| Field | Type | Description |
|---|---|---|
| `baseVersion` | string | Snapshot version string for base input. |
| `targetVersion` | string | Snapshot version string for target input. |
| `metadata` | object | Runner-specific diagnostic context. |

## 3. Stats Contract

`stats` MUST include:

1. `added`
2. `removed`
3. `replaced`
4. `moved`
5. `unchanged`
6. `totalCompared`

All stats fields MUST be non-negative integers.

## 4. Diff Entry Contract

Each entry MUST include:

1. `op`: one of `add`, `remove`, `replace`, `move`
2. `path`: RFC6901 JSON Pointer path

Additional required fields by operation:

1. `add`: `value`
2. `remove`: no additional required fields
3. `replace`: `before`, `after`
4. `move`: `from`

Optional fields:

1. `typeHint`: semantic hint (for example `widget`, `task`, `layout-node`)
2. `notes`: human-readable short note

## 5. Path and Identity Rules

1. `path` and `from` MUST use RFC6901 JSON Pointer encoding.
2. Paths MUST resolve against normalized snapshot JSON trees.
3. Node identity MUST prefer stable IDs already present in snapshots; array index movement MUST be represented by `move` when identity is preserved.
4. If identity cannot be preserved deterministically, emit `remove` + `add` instead of `move`.

## 6. Value Normalization Rules

Before diffing, both snapshots MUST be canonicalized:

1. Object keys sorted lexically.
2. No host-specific pointer/address values.
3. No non-JSON values (`undefined`, function, symbol).
4. Numeric values compared as JSON numbers without locale formatting.

Canonicalization MUST be deterministic and consistent with snapshot serialization semantics.

## 7. Deterministic Entry Ordering

Entries MUST be emitted in stable order:

1. Primary key: `path` lexical ascending.
2. Secondary key: operation precedence `remove`, `move`, `replace`, `add`.
3. Tertiary key: operation-specific stable fields (`from`, then serialized value hash).

When two entries remain tied after these keys, emit in deterministic generator traversal order and record tie count in diagnostics.

## 8. Generation Rules

1. Diff engines MUST compare normalized trees only.
2. `replace` MUST be preferred over `remove+add` when path identity is unchanged.
3. `move` MUST be emitted only when stable identity is provably preserved.
4. Engines SHOULD coalesce redundant operations on identical paths within one output.
5. Diff output MUST be replayable to transform base into target deterministically.

## 9. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `snapshot-diff.input.invalid` | Base or target does not validate against snapshot schema. | No | Fix snapshot input. |
| `snapshot-diff.path.invalid` | Generated path is not valid RFC6901 JSON Pointer. | No | Fix diff engine path encoding. |
| `snapshot-diff.op.invalid` | Unsupported or malformed diff operation. | No | Correct operation encoding. |
| `snapshot-diff.nondeterministic` | Re-running diff on identical inputs yields different output. | Conditional | Stabilize normalization/order rules and re-run. |
| `snapshot-diff.transform-failed` | Applying diff does not produce target snapshot. | No | Repair generation logic. |

## 10. Compatibility Policy

1. Minor versions MAY add optional metadata fields.
2. Minor versions MUST NOT change operation semantics or ordering rules.
3. New operation types require major version change.
4. Deprecated fields MUST remain accepted for at least one full minor version overlap.

## 11. Conformance Fixtures and Pass Criteria

Minimum evidence set:

1. `web-ui/tests/basic.test.mjs`
2. `web-ui/tests/layout.test.mjs`
3. `web-ui/tests/browser.test.mjs`

Pass criteria:

1. Diff output for identical input pairs is byte-for-byte stable across runs.
2. Applying produced diff reconstructs target snapshot exactly.
3. Entry ordering and stats are stable for identical input pairs.
4. Invalid input produces one stable failure code from Section 9.

## 12. Conformance

An implementation is conformant only if:

1. It emits envelope, stats, and entries exactly per Sections 2-4.
2. It enforces path/identity and normalization rules from Sections 5-6.
3. It preserves deterministic ordering and generation semantics from Sections 7-8.
4. It implements stable failure behavior from Section 9.
