# Controlled Reader Contract v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-17  
Scope: Deterministic controlled-reader profile for semantic merge and persistence lanes  
Depends on: `web-ui/spec/persistence-semantic-profile-v1.md`, `web-ui/spec/persistence-semantic-merge-contract-v1.md`  
Compatibility: `v1.x` preserves reader policy knobs, normalized AST lanes, and stable form identity rules; incompatible reader behavior changes require `v2`.

## 1. Purpose

This contract defines a deterministic, policy-bound reader for Lisp source processing.

## 2. Reader Profile Surface

Reader profile <a id="REQ-CONTROLLED-READER-CONTRACT-V1-E4AE040377"></a>MUST declare:

1. readtable policy,
2. package policy,
3. feature conditional policy,
4. read-time evaluation policy,
5. circular structure policy,
6. trivia preservation mode.

## 3. Deterministic Parse Output

For fixed input bytes and profile:

1. parse result <a id="REQ-CONTROLLED-READER-CONTRACT-V1-5C37D8C777"></a>MUST be deterministic,
2. diagnostics <a id="REQ-CONTROLLED-READER-CONTRACT-V1-4FD8C342DF"></a>MUST be deterministic,
3. form identity assignment <a id="REQ-CONTROLLED-READER-CONTRACT-V1-8FE0A52B91"></a>MUST be deterministic.

Output record shape includes:

1. normalized AST (`FormGraph`),
2. stable form IDs,
3. token/trivia map,
4. diagnostics and policy decisions.

## 4. Policy Rules

1. `#.` is forbidden by default; enabling it requires explicit sandbox policy and audit record.
2. `#+` and `#-` conditionals must be either preserved as explicit conditional nodes or treated as opaque text regions by profile.
3. Readtable mutations <a id="REQ-CONTROLLED-READER-CONTRACT-V1-26F19B9EBE"></a>MUST be scoped and recorded as first-class policy events.
4. Circular reader constructs (`#n=`, `#n#`) must be either rejected or canonicalized by declared policy.

## 5. Error and Recovery

Malformed forms should produce recoverable diagnostics where policy allows, but parse recovery <a id="REQ-CONTROLLED-READER-CONTRACT-V1-DF2DAA541C"></a>MUST NOT invent non-deterministic form identities.

## 6. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `controlled-reader.policy-invalid` | Reader profile configuration invalid/incomplete. | No | Provide complete valid profile. |
| `controlled-reader.readtime-eval-blocked` | `#.` encountered while policy forbids evaluation. | No | Adjust source or enable audited sandbox policy. |
| `controlled-reader.conditional-unsupported` | Conditional feature form cannot be interpreted under profile. | Conditional | Change profile mode or treat region as opaque text. |
| `controlled-reader.identity-unstable` | Form identity assignment cannot be made deterministic. | No | Reconfigure reader policy and retry parse. |

## 7. Conformance

An implementation is conformant only if Sections 2-6 are enforced.
