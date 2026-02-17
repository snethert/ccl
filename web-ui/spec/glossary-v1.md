# Web UI Glossary v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-16  
Scope: Canonical definitions for normative `web-ui` specification terms  
Depends on: `web-ui/spec/spec-index-v1.md`, `web-ui/spec/normative-language-and-conformance-v1.md`, `web-ui/DEV-PLAN.md`, `web-ui/FRONT-END-DEV-PLAN.md`  
Compatibility: Existing term meanings are stable across `v1.x`; incompatible redefinitions require `v2`.

## 1. Purpose

This glossary defines normative terms used across `web-ui` specifications.
If a term appears in normative language and is defined here, this definition is authoritative.

## 2. Usage Rules

1. Terms are case-insensitive in prose, but their canonical spelling in this glossary is preferred.
2. Hyphenated machine tokens (for example `required-planned`) <a id="REQ-GLOSSARY-V1-D791361F0E"></a>MUST match canonical form exactly.
3. New normative terms SHOULD be added here in the same change set that introduces them.
4. Synonyms MAY be used in explanatory prose, but normative clauses SHOULD use canonical term names.

## 3. Terms

| Term | Definition |
|---|---|
| artifact | A versioned spec file, schema, or required test/harness path declared by `spec-index-v1.md`. |
| artifact conformance | A verdict that one artifact satisfies all of its `MUST` requirements with linked evidence. |
| backend | A rendering/runtime surface implementation such as DOM, Canvas, or WebGL. |
| backend parity | Required equivalence checks across two or more backend lanes for the same fixture semantics. |
| capability | An explicitly granted permission or feature gate required for behavior that crosses trust boundaries. |
| command | A typed, routable user/system action with stable ID, arguments, and result/error semantics. |
| command routing | Deterministic selection of a command handler based on scope, state, and precedence rules. |
| compatibility statement | The metadata clause that defines backward/forward compatibility expectations for an artifact version. |
| conformance | A pass/fail determination that an implementation or process meets normative spec requirements. |
| conformance matrix | A traceability map from normative requirements to automated fixtures/tests. |
| deterministic | Producing identical outputs and verdicts for identical inputs, ordering, and seed. |
| doctrine | A design-principle document that guides intent; contracts and schemas are authoritative for executable behavior. |
| envelope | The top-level structured payload carrying version, identity, and payload metadata. |
| event log | Ordered event sequence used to replay behavior and validate deterministic state transitions. |
| fixture | A defined input/expected-result case used for automated conformance checks. |
| focus handoff | Transfer of active focus target between scopes, windows, or elements under deterministic rules. |
| full-web-ui-v1 | The union profile requiring all `required` and `required-planned` artifacts from the v1 index. |
| governance-base-v1 | The baseline profile containing spec index, normative-language contract, and glossary artifacts. |
| hit test | Resolution of input coordinates to target identity under defined coordinate and tie-break semantics. |
| lane | An execution dimension such as backend, mode, viewport, locale, or input class. |
| major version | The `vN` segment indicating potentially incompatible artifact semantics. |
| metadata | Required artifact header fields (`Status`, `Version`, `Last updated`, `Scope`, `Depends on`, `Compatibility`). |
| normative | Binding requirement language interpreted using RFC2119/RFC8174 keywords. |
| profile conformance | A verdict that all required artifacts in a named profile are artifact-conformant. |
| protected ref | A reference namespace that requires lease and semantic guard validation before advancement. |
| ref CAS | Compare-and-swap style reference update guarded by expected generation/value checks. |
| refgen | Monotonic reference generation counter used for CAS safety and ordering. |
| release gate | A blocking quality condition that <a id="REQ-GLOSSARY-V1-6D4BA43FC8"></a>MUST pass before release progression. |
| required artifact | Artifact class that <a id="REQ-GLOSSARY-V1-9BFD960AC5"></a>MUST exist and pass conformance for the owning profile claim. |
| required-planned artifact | Artifact class reserved as mandatory but not yet fully authored; blocks final profile/system claims. |
| schema | Machine-validated structural contract for payloads, records, or reports. |
| snapshot | Canonical serialized state representation used for restore, replay checks, and diffing. |
| stable ID | Identifier that remains consistent across deterministic replay and conformance runs for the same entity. |
| system conformance | A verdict that all required profiles for a release target are conformant. |
| tie-break rule | Explicit deterministic ordering rule used when multiple candidates are otherwise valid. |
| traceability | Ability to map each normative requirement to concrete automated evidence. |
| wire format | Byte/field-level interchange contract between producer and consumer endpoints. |

## 4. Conformance

A document set is glossary-conformant only if:

1. Normative terms are used consistently with definitions in Section 3.
2. No artifact introduces conflicting definitions for existing canonical terms.
3. New normative terms are added here before or with their first normative use.
