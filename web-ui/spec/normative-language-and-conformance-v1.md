# Web UI Normative Language and Conformance v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-16  
Scope: Normative keyword interpretation, requirement traceability, conformance claims, and compatibility/deprecation policy for `web-ui` specs  
Depends on: `web-ui/spec/spec-index-v1.md`, `web-ui/spec/glossary-v1.md`, `web-ui/PRODUCTION-SPEC-GAP-REGISTER.md`  
Compatibility: `v1.x` preserves conformance keyword and claim semantics; incompatible changes to claim/evidence rules require `v2`.

## 1. Purpose

This document defines how normative requirements are written, interpreted, and validated across `web-ui` specifications.
It is the authority for making and evaluating conformance claims.

## 2. Normative Keyword Rules

The key words `MUST`, `MUST NOT`, `REQUIRED`, `SHALL`, `SHALL NOT`, `SHOULD`, `SHOULD NOT`, `RECOMMENDED`, `MAY`, and `OPTIONAL` in `web-ui` specs are interpreted as described by RFC 2119 and RFC 8174.

Interpretation rules:

1. Uppercase normative keywords are binding requirements.
2. Lowercase terms (`must`, `should`, `may`) are informational unless explicitly marked normative.
3. If a sentence contains one normative keyword and multiple clauses, all clauses in that sentence are normative unless a clause is explicitly scoped as non-normative.

## 3. Requirement Traceability Rules

1. Every normative artifact <a id="REQ-NORMATIVE-LANGUAGE-AND-CONFORMANCE-V1-D9359BFD45"></a>MUST include a `Conformance` section.
2. Every `MUST` requirement <a id="REQ-NORMATIVE-LANGUAGE-AND-CONFORMANCE-V1-D6D74319FA"></a>MUST be traceable to at least one automated test, fixture, or schema validation check.
3. Requirement-to-evidence links <a id="REQ-NORMATIVE-LANGUAGE-AND-CONFORMANCE-V1-74E9627135"></a>MUST be machine-indexable by path and stable ID.
4. If a requirement cannot yet be automated, it <a id="REQ-NORMATIVE-LANGUAGE-AND-CONFORMANCE-V1-3BCC8A1549"></a>MUST be tagged as `manual-gate` and listed in a blocking gap report.
5. Normative contradictions across artifacts <a id="REQ-NORMATIVE-LANGUAGE-AND-CONFORMANCE-V1-11F1853C4A"></a>MUST be resolved by explicit precedence declaration.

Precedence order:

1. Schema contracts (`*.json`) over prose where field constraints conflict.
2. Specialized contract artifacts over doctrine/planning prose.
3. Newer minor version over older minor version within the same major.

## 4. Artifact Metadata Requirements

Each normative `web-ui/spec/*-vN.*` artifact <a id="REQ-NORMATIVE-LANGUAGE-AND-CONFORMANCE-V1-505B61010E"></a>MUST declare:

1. `Status`
2. `Version`
3. `Last updated`
4. `Scope`
5. `Depends on`
6. `Compatibility`

Missing any required metadata field is a conformance failure for that artifact.

## 5. Conformance Levels

The system supports three conformance levels:

1. `artifact`: one artifact's requirements and evidence pass.
2. `profile`: all artifacts in a named profile from `spec-index-v1.md` pass.
3. `system`: all profiles required for the target release pass.

### 5.1 Artifact Conformance

Artifact conformance requires:

1. Artifact is present at declared path.
2. Artifact metadata is complete and valid.
3. All artifact `MUST` requirements pass with linked evidence.

### 5.2 Profile Conformance

Profile conformance requires:

1. Profile exists in `spec-index-v1.md`.
2. All `required` artifacts in profile are artifact-conformant.
3. No `required-planned` artifact remains unresolved for the claim.

### 5.3 System Conformance

System conformance requires:

1. Required profile set is declared by release policy.
2. Every required profile is conformant.
3. Compatibility and deprecation gates are satisfied.

## 6. Evidence Contract

Evidence <a id="REQ-NORMATIVE-LANGUAGE-AND-CONFORMANCE-V1-F94B4AD8F3"></a>MUST include:

1. Conformance report output path(s).
2. Fixture/test IDs executed.
3. Runner/build identifier and source revision.
4. Environment lane identifiers (backend, mode, viewport, locale where relevant).
5. Deterministic seed where randomization exists.

Evidence MAY be rejected if it cannot be replayed deterministically from captured metadata.

## 7. Determinism Rules

1. Conformance verdicts <a id="REQ-NORMATIVE-LANGUAGE-AND-CONFORMANCE-V1-139E7A7D59"></a>MUST be deterministic for identical inputs and seed.
2. When multiple valid matches exist, tie-break behavior <a id="REQ-NORMATIVE-LANGUAGE-AND-CONFORMANCE-V1-08DBA87D72"></a>MUST be declared and stable.
3. Timestamp-based checks <a id="REQ-NORMATIVE-LANGUAGE-AND-CONFORMANCE-V1-BF5D447F12"></a>MUST use monotonic clocks unless wall-clock behavior is explicitly required.
4. Unordered structures in reports <a id="REQ-NORMATIVE-LANGUAGE-AND-CONFORMANCE-V1-31333C5C08"></a>MUST be canonicalized before comparison.

## 8. Failure Semantics

Conformance systems <a id="REQ-NORMATIVE-LANGUAGE-AND-CONFORMANCE-V1-3B7E0EEF2C"></a>MUST use stable error codes:

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `conformance.artifact-missing` | Required artifact path does not exist. | No | Add the artifact. |
| `conformance.metadata-invalid` | Required metadata fields are missing/invalid. | No | Correct metadata and re-run. |
| `conformance.requirement-unmapped` | Normative requirement has no evidence mapping. | No | Add requirement-to-evidence mapping. |
| `conformance.evidence-missing` | Required evidence record is absent. | No | Produce and attach evidence. |
| `conformance.nondeterministic-result` | Repeated run produced different verdict/output. | Conditional | Stabilize nondeterminism, then re-run. |
| `conformance.profile-blocked` | Profile includes unresolved `required-planned` artifacts. | No | Complete pending required artifacts. |

## 9. Compatibility and Versioning Policy

1. Major version changes (`vN` to `vN+1`) MAY break compatibility and <a id="REQ-NORMATIVE-LANGUAGE-AND-CONFORMANCE-V1-D74259FAF4"></a>MUST provide migration notes.
2. Minor version changes (`x.Y.z`) <a id="REQ-NORMATIVE-LANGUAGE-AND-CONFORMANCE-V1-53A4664A89"></a>MUST be backward compatible for existing artifact IDs and claim semantics.
3. Patch changes (`x.y.Z`) <a id="REQ-NORMATIVE-LANGUAGE-AND-CONFORMANCE-V1-F83D56E970"></a>MUST be non-semantic clarifications or fixes that do not alter conformance verdicts.
4. Removed requirements <a id="REQ-NORMATIVE-LANGUAGE-AND-CONFORMANCE-V1-FDCC5F0483"></a>MUST include explicit deprecation and replacement mapping.
5. Deprecated requirements <a id="REQ-NORMATIVE-LANGUAGE-AND-CONFORMANCE-V1-000D492A27"></a>MUST remain valid for at least one full minor version overlap unless a security-critical exception is declared.

## 10. Change Control

When normative behavior changes:

1. Related artifact version <a id="REQ-NORMATIVE-LANGUAGE-AND-CONFORMANCE-V1-0B7C93C122"></a>MUST be updated.
2. `spec-index-v1.md` <a id="REQ-NORMATIVE-LANGUAGE-AND-CONFORMANCE-V1-DB8A73B9DE"></a>MUST be updated if artifact class, profile membership, or identity changes.
3. `glossary-v1.md` <a id="REQ-NORMATIVE-LANGUAGE-AND-CONFORMANCE-V1-D96AE6972A"></a>MUST be updated when introducing a new normative term.
4. Conformance matrix/fixtures <a id="REQ-NORMATIVE-LANGUAGE-AND-CONFORMANCE-V1-43D27A9C44"></a>MUST be updated in the same change set.

## 11. Conformance

A `web-ui` conformance process is conformant with this document only if:

1. It interprets normative keywords exactly per Section 2.
2. It enforces metadata, traceability, and evidence requirements from Sections 3-6.
3. It applies deterministic evaluation and stable failure semantics from Sections 7-8.
4. It enforces compatibility and change-control obligations from Sections 9-10.
