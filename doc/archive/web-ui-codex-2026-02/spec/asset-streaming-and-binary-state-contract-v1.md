# Asset Streaming and Binary State Contract v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-17  
Scope: Normative separation of structured UI state from binary assets, including streaming/hydration and persistence interaction rules  
Depends on: `web-ui/spec/normative-language-and-conformance-v1.md`, `web-ui/spec/persistence-purpose-and-user-contract-v1.md`, `web-ui/spec/persistence-storage-backend-matrix-v1.md`, `web-ui/spec/persistence-envelope-schema-v1.json`, `web-ui/spec/observability-contract-v1.md`  
Compatibility: `v1.x` preserves asset-lane identifiers, content-addressing semantics, and hydration behavior; incompatible channel model changes require `v2`.

## 1. Purpose

This contract prevents binary-heavy workloads from overloading structured snapshot/state channels.
It is normative for binary asset lanes, content addressing, and non-blocking hydration behavior.

## 2. Channel Separation Model

Required channels:

1. Structured state channel (`state`)
2. Binary asset channel (`asset`)

Separation rules:

1. Structured state snapshots <a id="REQ-ASSET-STREAMING-AND-BINARY-STATE-CONTRACT-V1-1FBBF761C6"></a>MUST reference binary assets by stable asset reference, not inline binary blobs.
2. Binary asset payloads <a id="REQ-ASSET-STREAMING-AND-BINARY-STATE-CONTRACT-V1-E0E88B1ABD"></a>MUST flow through asset channel or approved external storage lane.
3. State channel decode <a id="REQ-ASSET-STREAMING-AND-BINARY-STATE-CONTRACT-V1-787264F8B1"></a>MUST remain valid when assets are temporarily unavailable.

## 3. Asset Identity and Addressing

Identity requirements:

1. Asset records <a id="REQ-ASSET-STREAMING-AND-BINARY-STATE-CONTRACT-V1-05786E95CE"></a>MUST include `asset_id`.
2. Asset records <a id="REQ-ASSET-STREAMING-AND-BINARY-STATE-CONTRACT-V1-CC79BACD67"></a>MUST include `content_hash`.
3. Asset records SHOULD include logical `asset_kind` (image/font/audio/mesh/etc.).
4. Distinct payloads <a id="REQ-ASSET-STREAMING-AND-BINARY-STATE-CONTRACT-V1-97343A4AE5"></a>MUST NOT reuse one `content_hash`.

## 4. Hydration and Load Behavior

Hydration requirements:

1. Asset hydration <a id="REQ-ASSET-STREAMING-AND-BINARY-STATE-CONTRACT-V1-B24D2438DE"></a>MUST be non-blocking relative to control-lane command execution.
2. Missing assets <a id="REQ-ASSET-STREAMING-AND-BINARY-STATE-CONTRACT-V1-68520C895E"></a>MUST resolve to deterministic placeholder behavior until hydration succeeds.
3. Hydration failure <a id="REQ-ASSET-STREAMING-AND-BINARY-STATE-CONTRACT-V1-C0621FE601"></a>MUST emit stable failure code and retain usable structured state.
4. Progressive asset readiness SHOULD be observable by asset status telemetry.

## 5. Snapshot and Replay Semantics

Snapshot behavior:

1. Snapshot contracts <a id="REQ-ASSET-STREAMING-AND-BINARY-STATE-CONTRACT-V1-62F86BCC91"></a>MUST define whether binary assets are embedded, referenced, or omitted.
2. Large binary payloads SHOULD be excluded from frequent structured snapshots by default.
3. Replay engines <a id="REQ-ASSET-STREAMING-AND-BINARY-STATE-CONTRACT-V1-63798CE525"></a>MUST tolerate referenced-asset snapshots by applying deterministic placeholder policy.

## 6. Storage and GC Constraints

Storage rules:

1. Asset garbage collection <a id="REQ-ASSET-STREAMING-AND-BINARY-STATE-CONTRACT-V1-1EAEEE7832"></a>MUST preserve assets reachable from retained refs/snapshots.
2. Asset compaction <a id="REQ-ASSET-STREAMING-AND-BINARY-STATE-CONTRACT-V1-F9230C30F9"></a>MUST NOT rewrite content hash identity.
3. Backend-specific retention limits <a id="REQ-ASSET-STREAMING-AND-BINARY-STATE-CONTRACT-V1-E68C4BCE0B"></a>MUST be declared per storage backend matrix.

## 7. Observability Requirements

Required fields:

1. `asset_id`
2. `content_hash`
3. `asset_kind`
4. `asset_bytes`
5. `hydration_state`
6. `hydration_wait_ms`
7. `asset_stream_rate`

## 8. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `persistence-storage-backend.asset-reference-missing` | Structured state references unknown asset ID/hash. | Conditional | Restore asset record or repair references. |
| `persistence-storage-backend.asset-hydration-failed` | Asset fetch/decode failed during hydration. | Conditional | Retry hydration or provide fallback asset. |
| `persistence-storage-backend.asset-inline-forbidden` | Binary payload was persisted in structured state lane where disallowed. | No | Move payload to asset lane and rewrite snapshot. |
| `persistence-storage-backend.asset-gc-unsafe` | Requested asset GC would remove reachable asset. | No | Recompute reachability and retry GC plan. |

## 9. Conformance Fixtures and Pass Criteria

Minimum required evidence:

1. `web-ui/tests/persistence-asset-lane.test.mjs`
2. `web-ui/tests/persistence-conformance-fixtures.test.mjs`
3. `web-ui/tests/phase-4-restore.test.mjs`

Pass criteria:

1. Structured snapshots remain valid without inline binary payloads.
2. Missing-asset placeholder behavior is deterministic.
3. Asset GC preserves reachability guarantees.

## 10. Conformance

An implementation is conformant only if Sections 2-9 are satisfied.
