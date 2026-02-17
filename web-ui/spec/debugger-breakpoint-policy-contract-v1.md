# Debugger Breakpoint Policy Contract v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-16  
Scope: Breakpoint anchor semantics, policy evaluation rules, lifecycle events, and degradation behavior for `web-ui` debugger integrations  
Depends on: `web-ui/spec/normative-language-and-conformance-v1.md`, `web-ui/spec/command-schema-v1.json`, `web-ui/spec/debug-location-provider-contract-v1.md`, `web-ui/spec/debugger-stepper-session-contract-v1.md`, `web-ui/DEV-PLAN.md`, `web-ide/phase-9/debugger-stepper-spec.md`  
Compatibility: `v1.x` preserves anchor-kind vocabulary, policy modes, resolution/error taxonomy, and lifecycle event fields; incompatible behavior changes require `v2`.

## 1. Purpose

This contract defines canonical breakpoint policy behavior for source-facing debugger flows.
It standardizes breakpoint creation, normalization, enablement, conditional evaluation, and lifecycle event semantics.

## 2. Canonical Breakpoint Model

## 2.1 Breakpoint Record

Canonical record fields:

1. `breakpointId`
2. `sourceRef`
3. `sourceRevision`
4. `mappingEpoch`
5. `anchorKind` (`entry|exit`)
6. `requestedAnchor`
7. `resolvedAnchor`
8. `enabled`
9. `policy`
10. `actions`
11. `resolution:{status,reason}`

## 2.2 Anchor Kinds

Closed-set source-surface anchor kinds:

1. `entry` (before expression evaluation)
2. `exit` (after expression evaluation)

Rules:

1. UI placement on opening-parenthesis intent <a id="REQ-DEBUGGER-BREAKPOINT-POLICY-CONTRACT-V1-63D9CC8C8A"></a>MUST map to `entry`.
2. UI placement on closing-parenthesis intent <a id="REQ-DEBUGGER-BREAKPOINT-POLICY-CONTRACT-V1-6CC83394DA"></a>MUST map to `exit`.
3. Exit-bound stops <a id="REQ-DEBUGGER-BREAKPOINT-POLICY-CONTRACT-V1-FD12027E9C"></a>MUST carry `returnValues` in stop payloads.

## 2.3 Policy Modes

Closed-set policy modes:

1. `always`
2. `once`
3. `conditional`
4. `hit-count`

Required policy fields:

1. `always`: no extra fields.
2. `once`: no extra fields.
3. `conditional`: `condition` expression payload.
4. `hit-count`: `hitCount` target and runtime `currentHits`.

## 3. Breakpoint Lifecycle Commands

Required command IDs:

1. `runtime.debugger.breakpoint.upsert`
2. `runtime.debugger.breakpoint.delete`
3. `runtime.debugger.breakpoint.enable`
4. `runtime.debugger.breakpoint.disable`

## 3.1 Upsert Contract

Input:

1. `sourceRef`
2. `sourceRevision`
3. `requestedAnchor`
4. `policy`
5. `enabled`

Success output:

1. `breakpointId`
2. `resolvedAnchor`
3. `resolution:{status,reason}`
4. `mappingEpoch`

Rules:

1. Upsert <a id="REQ-DEBUGGER-BREAKPOINT-POLICY-CONTRACT-V1-95B8DBD1D7"></a>MUST be idempotent for same canonical breakpoint identity tuple when no policy change exists.
2. Requested anchor MAY degrade to nearest valid anchor only with explicit resolution reason.
3. Revision mismatch <a id="REQ-DEBUGGER-BREAKPOINT-POLICY-CONTRACT-V1-5D50111A4D"></a>MUST fail with typed stale-revision error.

## 3.2 Delete/Enable/Disable Contract

1. `delete` <a id="REQ-DEBUGGER-BREAKPOINT-POLICY-CONTRACT-V1-63C7E1A2BC"></a>MUST deterministically remove the target breakpoint ID or return typed invalid-breakpoint error.
2. `enable`/`disable` <a id="REQ-DEBUGGER-BREAKPOINT-POLICY-CONTRACT-V1-5AB565444D"></a>MUST only toggle state and <a id="REQ-DEBUGGER-BREAKPOINT-POLICY-CONTRACT-V1-017C1E3714"></a>MUST preserve anchor/policy fields.
3. Missing breakpoint IDs <a id="REQ-DEBUGGER-BREAKPOINT-POLICY-CONTRACT-V1-B875FB5E81"></a>MUST not silently no-op in strict mode.

## 4. Breakpoint Lifecycle Events

Required event kinds:

1. `debugger.breakpoint.updated`
2. `debugger.breakpoint.deleted`

## 4.1 `debugger.breakpoint.updated`

Minimum required fields:

1. `breakpointId`
2. `sourceRef`
3. `sourceRevision`
4. `mappingEpoch`
5. `requestedAnchor`
6. `resolvedAnchor`
7. `resolution:{status,reason}`

## 4.2 `debugger.breakpoint.deleted`

Minimum required fields:

1. `breakpointId`

Rules:

1. For fixed command/event stream, update/delete ordering <a id="REQ-DEBUGGER-BREAKPOINT-POLICY-CONTRACT-V1-7E98066733"></a>MUST be deterministic.
2. Delete events for already-deleted IDs MAY be ignored only if replay semantics remain deterministic and auditable.

## 5. Policy Evaluation Semantics

## 5.1 Hit and Once Semantics

1. `always`: breakpoint fires on each matched hit.
2. `once`: first matched hit fires and breakpoint auto-disables atomically in the same state transition.
3. `hit-count`: breakpoint fires only when configured count condition is met.

## 5.2 Conditional Semantics

1. Condition evaluation runs in debugger-safe evaluation context.
2. Condition evaluation errors <a id="REQ-DEBUGGER-BREAKPOINT-POLICY-CONTRACT-V1-C51D803944"></a>MUST emit typed diagnostics.
3. Default condition-error policy is `break-on-error=true` unless runtime policy explicitly overrides.

## 5.3 Action Ordering

After breakpoint hit decision is true, actions <a id="REQ-DEBUGGER-BREAKPOINT-POLICY-CONTRACT-V1-68D37B6868"></a>MUST run in deterministic order:

1. evaluate side-effect-safe probes (if allowed by policy),
2. collect pinned values,
3. emit inspect-locals payload lanes.

## 6. Resolution and Degradation Rules

1. `resolution.status` <a id="REQ-DEBUGGER-BREAKPOINT-POLICY-CONTRACT-V1-8967103032"></a>MUST be one of:
- `resolved`
- `degraded`
- `rejected`
2. `resolved` requires exact or equivalent target anchor fidelity.
3. `degraded` requires explicit `resolution.reason`.
4. `rejected` <a id="REQ-DEBUGGER-BREAKPOINT-POLICY-CONTRACT-V1-9FFCBEEA9F"></a>MUST return a typed failure code and no breakpoint mutation.

## 7. Determinism and Tie-Break Rules

1. Anchor normalization <a id="REQ-DEBUGGER-BREAKPOINT-POLICY-CONTRACT-V1-5D501E2DD7"></a>MUST be deterministic for fixed provider snapshot and request payload.
2. Ambiguous candidate selection <a id="REQ-DEBUGGER-BREAKPOINT-POLICY-CONTRACT-V1-1D819B3BFB"></a>MUST use stable tie-break defined by location-provider contract.
3. Policy counter updates (`currentHits`) <a id="REQ-DEBUGGER-BREAKPOINT-POLICY-CONTRACT-V1-80F0CF54C6"></a>MUST be monotonic and replay-stable.
4. Auto-disable transitions (`once`) <a id="REQ-DEBUGGER-BREAKPOINT-POLICY-CONTRACT-V1-D6E4EE9BC8"></a>MUST be explicit in recorded event stream.

## 8. Security and Safety Requirements

1. Breakpoint mutation commands <a id="REQ-DEBUGGER-BREAKPOINT-POLICY-CONTRACT-V1-BA23FD5043"></a>MUST be capability-gated.
2. Conditional expressions <a id="REQ-DEBUGGER-BREAKPOINT-POLICY-CONTRACT-V1-BA9222DC39"></a>MUST execute in bounded runtime context.
3. Policy actions <a id="REQ-DEBUGGER-BREAKPOINT-POLICY-CONTRACT-V1-2DF6772E27"></a>MUST not perform implicit mutating writes unless explicitly configured and auditable.
4. Breakpoint payloads from UI/runtime <a id="REQ-DEBUGGER-BREAKPOINT-POLICY-CONTRACT-V1-E2A2CB014D"></a>MUST be validated as untrusted input.

## 9. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `debugger-breakpoint.invalid-breakpoint` | Breakpoint ID or payload shape invalid. | Conditional | Correct payload or target breakpoint ID. |
| `debugger-breakpoint.stale-source-revision` | Breakpoint request uses stale `sourceRevision`. | Conditional | Refresh revision/handshake and retry. |
| `debugger-breakpoint.mapping-unavailable` | Requested source anchor cannot be resolved with current mapping data. | Conditional | Refresh mappings or choose fallback lane. |
| `debugger-breakpoint.ambiguous-anchor` | Multiple candidate anchors require explicit disambiguation. | Conditional | Provide explicit candidate/slide selection and retry. |
| `debugger-breakpoint.condition-eval-failed` | Conditional expression evaluation failed. | Conditional | Inspect diagnostics; adjust condition or policy. |
| `debugger-breakpoint.unsupported-operation` | Runtime does not support requested breakpoint command. | No | Degrade UI affordance or enable compatible runtime profile. |
| `debugger-breakpoint.state-conflict` | Breakpoint mutation conflicts with current debugger session state. | Conditional | Refresh session snapshot and re-issue mutation. |

## 10. Conformance Fixtures and Pass Criteria

Minimum required evidence:

1. `web-ui/tests/phase-5-runtime-bridge.test.mjs`
2. `web-ui/tests/phase-5-runtime-command-dispatch.test.mjs`
3. `web-ui/tests/phase-5-runtime-output.test.mjs`

Phase 10 breakpoint fixture set (required for full breakpoint claims):

1. entry-anchor placement fixture.
2. exit-anchor placement with return-values stop fixture.
3. once-policy auto-disable fixture.
4. conditional-policy error/diagnostic fixture.
5. hit-count deterministic progression fixture.
6. upsert degradation-ack fixture (`resolution.reason`).

Pass criteria:

1. Lifecycle commands and events maintain deterministic ordering and identity.
2. Policy outcomes are replay-stable for fixed input stream.
3. Degradation and failure paths surface explicit typed reasons.

## 11. Conformance

An implementation is conformant only if Sections 2-10 are satisfied.
