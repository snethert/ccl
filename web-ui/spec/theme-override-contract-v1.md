# Theme Override Contract v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-17  
Scope: User/workspace visual token overrides and conformance interaction for `web-ui`  
Depends on: `web-ui/spec/ui-visual-tokens-v1.json`, `web-ui/spec/ui-component-visual-contract-v1.md`, `web-ui/spec/ui-conformance-fixtures-v1.json`  
Compatibility: `v1.x` preserves override scopes, merge precedence, and fixture evaluation rules; incompatible override model changes require `v2`.

## 1. Purpose

This contract defines safe customization over canonical visual tokens.

## 2. Override Scopes

Supported scopes:

1. `user`
2. `workspace`

Precedence:

1. base tokens
2. workspace overrides
3. user overrides

Merge order <a id="REQ-THEME-OVERRIDE-CONTRACT-V1-63947C4765"></a>MUST be deterministic and stable.

## 3. Override Schema

Overrides <a id="REQ-THEME-OVERRIDE-CONTRACT-V1-40FD22896D"></a>MUST be object maps keyed by token paths from `ui-visual-tokens-v1.json`.

Rules:

1. Unknown token paths <a id="REQ-THEME-OVERRIDE-CONTRACT-V1-1F1A1363E4"></a>MUST be rejected or ignored by explicit policy (no silent partial parsing ambiguity).
2. Type mismatch overrides <a id="REQ-THEME-OVERRIDE-CONTRACT-V1-69F34DABFE"></a>MUST fail validation.
3. Effective token set <a id="REQ-THEME-OVERRIDE-CONTRACT-V1-5FB2D661A0"></a>MUST remain complete after merge.

## 4. Conformance Interaction

1. Conformance fixtures MAY run against base tokens or effective overridden tokens depending on claim type.
2. Claims using overrides <a id="REQ-THEME-OVERRIDE-CONTRACT-V1-A18CB919C0"></a>MUST record override hash and scope in evidence metadata.
3. Base-token conformance claims <a id="REQ-THEME-OVERRIDE-CONTRACT-V1-E91177A9BD"></a>MUST declare overrides disabled.

## 5. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `theme-override.path-unknown` | Override referenced unknown token path. | No | Use declared token path only. |
| `theme-override.type-invalid` | Override value type mismatched token schema. | No | Correct override value type. |
| `theme-override.merge-invalid` | Effective merged token graph is incomplete/invalid. | Conditional | Fix override set and recompute effective theme. |
| `theme-override.claim-metadata-missing` | Override-aware claim omitted required metadata. | No | Include override scope/hash in evidence. |

## 6. Conformance

An implementation is conformant only if Sections 2-5 are satisfied.
