# Error Code Registry v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-17  
Scope: Cross-spec error-code naming, namespace ownership, and collision prevention for `web-ui`  
Depends on: `web-ui/spec/normative-language-and-conformance-v1.md`, `web-ui/spec/spec-index-v1.md`  
Compatibility: `v1.x` preserves namespace ownership and naming-family rules; incompatible naming changes require `v2`.

## 1. Purpose

This registry defines canonical error-code naming conventions across `web-ui` specifications.

## 2. Naming Families

`v1` supports one canonical naming family for new specs:

1. dot-separated lowercase namespace + reason: `<namespace>.<reason>`

Legacy uppercase underscore codes MAY remain for backward compatibility but SHOULD include mapped dot-form aliases.

## 3. Namespace Ownership

Namespaces are artifact-owned and <a id="REQ-ERROR-CODE-REGISTRY-V1-CE408497C2"></a>MUST be unique.

Initial registry:

| Namespace | Owning artifact |
|---|---|
| `conformance` | `normative-language-and-conformance-v1.md` |
| `spec-index` | `spec-index-v1.md` |
| `gate-profile` | `conformance-gate-profiles-v1.md` |
| `ratification` | `spec-ratification-policy-v1.md` |
| `ui-tree` | `ui-wire-format-tree-v1.md` |
| `ui-tree-delta` | `ui-wire-format-tree-delta-v1.md` |
| `event-log` | `event-log-ordering-and-clock-rules-v1.md` |
| `undo-redo` | `command-undo-redo-contract-v1.md` |
| `text-edit` | `text-editing-contract-v1.md` |
| `clipboard` | `clipboard-interaction-contract-v1.md` |
| `drag-drop` | `drag-and-drop-interaction-contract-v1.md` |
| `offline` | `offline-and-service-worker-contract-v1.md` |
| `persistence-gc` | `persistence-gc-and-compaction-policy-v1.md` |
| `a11y-proxy` | `non-dom-accessibility-proxy-contract-v1.md` |
| `theme-override` | `theme-override-contract-v1.md` |
| `i18n` | `i18n-l10n-contract-v1.md` |
| `controlled-reader` | `controlled-reader-contract-v1.md` |

## 4. Registry Update Rules

1. New normative artifacts introducing error codes <a id="REQ-ERROR-CODE-REGISTRY-V1-BDC64069B9"></a>MUST register namespace ownership here in the same change set.
2. Renaming an existing namespace requires compatibility mapping and migration notes.
3. Duplicate namespace claims <a id="REQ-ERROR-CODE-REGISTRY-V1-9A8D205E48"></a>MUST be rejected.

## 5. Conformance

A spec set is registry-conformant only if all normative error-code namespaces are registered and collision-free.
