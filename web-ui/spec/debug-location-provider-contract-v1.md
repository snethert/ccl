# Debug Location Provider Contract v1

Status: Draft  
Version: 1.1.0  
Last updated: 2026-02-17  
Scope: Abstract source-location resolution contract for debugger stops, editor anchors, and breakpoint normalization in `web-ui` runtime integrations  
Depends on: `web-ui/spec/normative-language-and-conformance-v1.md`, `web-ui/spec/command-schema-v1.json`, `web-ui/spec/ui-state-schema-v1.json`, `web-ui/DEV-PLAN.md`, `web-ide/phase-9/debugger-stepper-spec.md`  
Compatibility: `v1.x` preserves provider operation names, required location fields, stale-revision behavior, and mapping-epoch monotonicity; incompatible changes require `v2`.

## 1. Purpose

This contract defines the abstract `LocationProvider` interface used by debugger and breakpoint flows.
It standardizes how runtime execution points and editor selections are mapped to canonical source locations, without requiring any specific compiler metadata encoding.

## 2. Canonical Terms

## 2.1 Identity and Revision Lanes

1. `sourceRef`: stable source identity token.
2. `sourceRevision`: opaque source revision token supplied by editor/runtime.
3. `mappingEpoch`: non-negative integer mapping generation for a `sourceRef`, monotonically increasing.

## 2.2 Anchor and Location Lanes

Closed-set `anchorKind` values:

1. `entry`
2. `exit`
3. `either` (request-only)
4. `internal`
5. `unknown`

Canonical resolved location shape:

1. `sourceRef`
2. `sourceRevision`
3. `mappingEpoch`
4. `formId` (nullable)
5. `anchorKind`
6. `line`
7. `column`
8. `charStart`
9. `charEnd`

## 2.3 Selection Input

Selection ranges are half-open intervals:

1. `start` (inclusive, non-negative integer)
2. `end` (exclusive, integer where `end >= start`)

## 3. Provider Operations

`v1` defines an abstract provider with these operations.

## 3.1 `sourceHandshake`

Input:

1. `sourceRef`
2. `sourceRevision`
3. `contentHash`

Output:

1. `accepted` (boolean)
2. `latestRevision`
3. `mappingEpoch`

Rules:

1. Accepted handshake <a id="REQ-DEBUG-LOCATION-PROVIDER-CONTRACT-V1-B78006EB97"></a>MUST bind `(sourceRef, sourceRevision)` to a deterministic mapping snapshot.
2. Rejected handshake <a id="REQ-DEBUG-LOCATION-PROVIDER-CONTRACT-V1-B46A376FBB"></a>MUST include a typed error code.

## 3.2 `resolveAnchor`

Input:

1. `sourceRef`
2. `sourceRevision`
3. `selection:{start,end}`
4. `preferredAnchorKind` (`entry|exit|either`)

Output on success:

1. `resolved` (true)
2. `anchor:{formId,anchorKind,line,column,charStart,charEnd}`
3. `mappingEpoch`

Rules:

1. Resolver <a id="REQ-DEBUG-LOCATION-PROVIDER-CONTRACT-V1-01CAEB1020"></a>MUST fail on stale revision mismatch.
2. Resolver <a id="REQ-DEBUG-LOCATION-PROVIDER-CONTRACT-V1-6BEF338D9F"></a>MUST return deterministic anchor for fixed input and provider snapshot.
3. Resolver <a id="REQ-DEBUG-LOCATION-PROVIDER-CONTRACT-V1-2409303031"></a>MUST return typed ambiguity/no-anchor failures instead of silent fallback.

## 3.3 `resolveExecutionPoint`

Input may include runtime execution descriptors such as:

1. `stopId`
2. `frameId`
3. runtime-side execution pointer token(s)

Output:

1. canonical location (Section 2.2), or
2. `slideGroup:{id,candidates[]|null}` when multiple valid candidates exist.

Rules:

1. Candidate ordering <a id="REQ-DEBUG-LOCATION-PROVIDER-CONTRACT-V1-DA7A51877F"></a>MUST be deterministic.
2. Candidate entries <a id="REQ-DEBUG-LOCATION-PROVIDER-CONTRACT-V1-0FDDE677AF"></a>MUST each include canonical location fields.

## 3.4 `resolveBreakpointAnchor`

Input:

1. `sourceRef`
2. `sourceRevision`
3. `requestedAnchor`
4. `policy`
5. `enabled`

Output:

1. `resolvedAnchor`
2. `resolution:{status,reason}`
3. `mappingEpoch`

Rules:

1. Resolution <a id="REQ-DEBUG-LOCATION-PROVIDER-CONTRACT-V1-983B24A95A"></a>MUST preserve explicit entry vs exit intent whenever possible.
2. Degraded/adjusted anchors <a id="REQ-DEBUG-LOCATION-PROVIDER-CONTRACT-V1-B4873DE185"></a>MUST return explicit reason.

## 4. Runtime Command/Event Integration

The provider contract binds directly to Phase 10 command/event lanes:

1. `runtime.editor.source.handshake` -> `sourceHandshake`.
2. `runtime.editor.anchor.resolve` -> `resolveAnchor`.
3. `runtime.debugger.breakpoint.upsert` -> `resolveBreakpointAnchor`.
4. `debugger.stop` location payloads -> `resolveExecutionPoint` output.
5. `debugger.mapping.invalidated` and `debugger.mapping.refreshed` <a id="REQ-DEBUG-LOCATION-PROVIDER-CONTRACT-V1-2186192DCB"></a>MUST carry provider epoch/revision context.

## 5. Determinism and Tie-Break Rules

1. For fixed `(sourceRef, sourceRevision, selection, preferredAnchorKind, mappingEpoch)`, `resolveAnchor` <a id="REQ-DEBUG-LOCATION-PROVIDER-CONTRACT-V1-084CC5E110"></a>MUST be deterministic.
2. Ambiguous candidates <a id="REQ-DEBUG-LOCATION-PROVIDER-CONTRACT-V1-8CEEE281C4"></a>MUST use stable tie-break:
- lowest `charStart`,
- then lowest span length (`charEnd-charStart`),
- then lexical `formId` (nullable treated as empty).
3. `mappingEpoch` <a id="REQ-DEBUG-LOCATION-PROVIDER-CONTRACT-V1-6D7F1C8227"></a>MUST be monotonic per `sourceRef`.
4. Revision mismatch <a id="REQ-DEBUG-LOCATION-PROVIDER-CONTRACT-V1-3D7C143F13"></a>MUST NOT silently remap to another revision.

## 6. Compatibility and Metadata Envelope Boundary

`v1` interoperable envelope (`DebugMetadataEnvelopeV1`) fields:

1. `envelopeVersion` (integer, `1`)
2. `sourceRef` (string)
3. `sourceRevision` (string)
4. `mappingEpoch` (non-negative integer)
5. `entries` (array)

`entries[]` minimum fields:

1. `runtimeToken` (string)
2. `anchorKind` (`entry|exit|internal|unknown`)
3. `line` (1-based integer)
4. `column` (1-based integer)
5. `charStart` (non-negative integer)
6. `charEnd` (integer, `>= charStart`)
7. `formId` (nullable string)

Envelope rules:

1. Providers <a id="REQ-DEBUG-LOCATION-PROVIDER-CONTRACT-V1-F0BA0999EB"></a>MUST accept this minimum envelope shape for import/refresh operations.
2. Providers <a id="REQ-DEBUG-LOCATION-PROVIDER-CONTRACT-V1-E0BFBC4963"></a>MUST reject envelopes with invalid required fields using typed validation errors.
3. `resolveExecutionPoint` <a id="REQ-DEBUG-LOCATION-PROVIDER-CONTRACT-V1-90F39409E4"></a>MUST be computable from `runtimeToken` plus envelope entries without implementation-specific hidden fields.
4. Unknown extension fields MAY be preserved but <a id="REQ-DEBUG-LOCATION-PROVIDER-CONTRACT-V1-067D828C12"></a>MUST NOT alter Section 5 determinism/tie-break behavior.
5. Any provider implementation MAY keep richer internal metadata, but wire-visible behavior <a id="REQ-DEBUG-LOCATION-PROVIDER-CONTRACT-V1-AE52DA5FDC"></a>MUST remain compatible with this envelope.
6. Changing required envelope fields or deterministic rules requires `v2`.

## 7. Security and Validation Requirements

1. `sourceRef`, `sourceRevision`, selection offsets, and anchors <a id="REQ-DEBUG-LOCATION-PROVIDER-CONTRACT-V1-6E8E5FA9FA"></a>MUST be validated as untrusted input.
2. Provider operations <a id="REQ-DEBUG-LOCATION-PROVIDER-CONTRACT-V1-08510C0410"></a>MUST be side-effect free with respect to runtime evaluation state.
3. Provider outputs <a id="REQ-DEBUG-LOCATION-PROVIDER-CONTRACT-V1-D763468324"></a>MUST not leak raw process addresses or architecture-specific pointers.
4. Content-hash and revision checks SHOULD be used to prevent stale or cross-buffer mis-resolution.

## 8. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `debug-location-provider.unknown-source` | `sourceRef` is not registered/known to provider. | Conditional | Send `sourceHandshake` first or re-register source. |
| `debug-location-provider.stale-source-revision` | Requested revision does not match provider-known latest revision. | Conditional | Refresh revision/handshake and retry. |
| `debug-location-provider.mapping-unavailable` | No mapping data exists for requested source/revision. | Conditional | Trigger mapping refresh/recompile and retry. |
| `debug-location-provider.ambiguous-anchor` | Multiple valid anchors and deterministic tie-break not permitted for request mode. | Conditional | Request explicit disambiguation or slide-candidate selection. |
| `debug-location-provider.no-anchor-at-selection` | Selection range has no valid resolvable anchor. | Conditional | Adjust selection or fallback to nearest valid region. |
| `debug-location-provider.invalid-selection-range` | Selection offsets are malformed/out-of-range. | No | Fix `start/end` offsets before retry. |
| `debug-location-provider.invalid-breakpoint` | Requested breakpoint anchor/policy cannot be normalized safely. | Conditional | Correct anchor/policy and retry upsert. |

## 9. Conformance Fixtures and Pass Criteria

Minimum required evidence:

1. `web-ui/tests/phase-5-runtime-debugger.test.mjs`
2. `web-ui/tests/phase-5-runtime-bridge.test.mjs`
3. `web-ui/tests/phase-5-runtime-output.test.mjs`

Phase 10 required fixture set (must exist for full provider claims):

1. `editor-anchor-resolve` determinism fixture.
2. stale revision handshake/rejection fixture.
3. breakpoint upsert resolution/degradation fixture.
4. stop-to-editor projection with slide candidates fixture.

Pass criteria:

1. Location and revision fields remain stable across replay.
2. Mismatch and ambiguity paths return typed failures.
3. Mapping epoch behavior is monotonic and observable in command/event payloads.

## 10. Conformance

An implementation is conformant only if Sections 2-9 are satisfied.
