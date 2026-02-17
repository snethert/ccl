# Spec Ratification Policy v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-17  
Scope: Ratification workflow and sign-off requirements for normative `web-ui` spec artifacts  
Depends on: `web-ui/spec/spec-index-v1.md`, `web-ui/spec/normative-language-and-conformance-v1.md`, `web-ui/spec/conformance-gate-profiles-v1.md`  
Compatibility: `v1.x` preserves workflow states and minimum sign-off semantics; incompatible workflow changes require `v2`.

## 1. Purpose

This artifact defines the required lifecycle for normative `web-ui` specs.
It makes ratification state transitions explicit and auditable.

## 2. Workflow States

Allowed ratification states:

1. `Draft`
2. `Review`
3. `Approved`
4. `Frozen`

## 3. Required Ratification Record

Each normative spec artifact <a id="REQ-SPEC-RATIFICATION-POLICY-V1-7FDDD717F6"></a>MUST have a ratification record with:

1. `artifact`
2. `version`
3. `state`
4. `owner`
5. `reviewers`
6. `signoff_date`
7. `evidence_refs`
8. `change_summary`

A ratification record <a id="REQ-SPEC-RATIFICATION-POLICY-V1-5AF5436FEF"></a>MUST be updated in the same change set as any state transition.

## 4. State Exit Criteria

## 4.1 `Draft -> Review`

Before entering `Review`, the artifact <a id="REQ-SPEC-RATIFICATION-POLICY-V1-2609DC03ED"></a>MUST satisfy:

1. Required metadata header fields.
2. Stable `REQ-*` anchors for all uppercase `MUST` requirements.
3. Inclusion in `spec-index-v1.md` with a declared class/profile.
4. Entry coverage in `requirements-index-v1.json` and `conformance-evidence-index-v1.json`.

## 4.2 `Review -> Approved`

Before entering `Approved`, the artifact <a id="REQ-SPEC-RATIFICATION-POLICY-V1-19287618D0"></a>MUST satisfy:

1. `gate.conformance.lint.v1` pass.
2. All scope-applicable blocker gates from `conformance-gate-profiles-v1.md` pass.
3. At least one owner sign-off and one independent reviewer sign-off.
4. No unresolved blocker findings for the artifact.

## 4.3 `Approved -> Frozen`

Before entering `Frozen`, the artifact <a id="REQ-SPEC-RATIFICATION-POLICY-V1-BD208AF039"></a>MUST satisfy:

1. At least one release-cycle soak with no blocker conformance regressions.
2. Explicit compatibility statement for next minor version.
3. Migration notes for any deprecations introduced since `Approved`.

## 5. State Mutation Rules

1. State transitions <a id="REQ-SPEC-RATIFICATION-POLICY-V1-1B3C7AE195"></a>MUST follow the allowed order in Section 2.
2. Direct transitions from `Draft` to `Approved` or `Frozen` <a id="REQ-SPEC-RATIFICATION-POLICY-V1-B89A3069BA"></a>MUST NOT be allowed.
3. A `Frozen` artifact <a id="REQ-SPEC-RATIFICATION-POLICY-V1-2D6F38C499"></a>MUST NOT receive normative behavior changes without reopening at `Review` with a version bump.
4. Non-normative clarifications to `Frozen` artifacts MAY remain in `Frozen` when conformance verdicts are unaffected.

## 6. Sign-off Fields

Sign-off entries:

1. `name`
2. `role` (`owner`, `reviewer`, `security`, `operations`, `release`)
3. `decision` (`approve`, `reject`)
4. `timestamp_utc`
5. `notes`

At least one `owner` and one non-owner `reviewer` approval <a id="REQ-SPEC-RATIFICATION-POLICY-V1-2B027FBDAC"></a>MUST be present for `Approved` or `Frozen` states.

## 7. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `ratification.invalid-transition` | Requested state transition is not allowed by Section 5. | No | Use a valid transition path. |
| `ratification.missing-signoff` | Required sign-off fields or decisions are missing. | No | Complete sign-off record and retry transition. |
| `ratification.evidence-missing` | Required gate evidence is absent or failing. | Conditional | Re-run gates and attach passing evidence. |

## 8. Conformance

A ratification workflow is conformant only if it enforces Sections 2-7 for all normative artifacts in `spec-index-v1.md`.
