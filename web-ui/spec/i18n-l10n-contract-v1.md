# I18N/L10N Contract v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-17  
Scope: Internationalization and localization contract for `web-ui` strings and locale-sensitive formatting  
Depends on: `web-ui/spec/keymap-localization-and-ime-policy-v1.md`, `web-ui/ui-doctrine.md`, `web-ui/spec/text-editing-contract-v1.md`  
Compatibility: `v1.x` preserves resource-key model, locale fallback order, and formatter semantics; incompatible localization model changes require `v2`.

## 1. Purpose

This contract defines localization requirements beyond keyboard/IME handling.

## 2. String Externalization

1. User-visible UI strings <a id="REQ-I18N-L10N-CONTRACT-V1-8D270F2713"></a>MUST be referenced by stable resource keys.
2. Hard-coded inline English literals in runtime UI surfaces SHOULD be limited to diagnostics and development-only lanes.
3. Missing localized keys <a id="REQ-I18N-L10N-CONTRACT-V1-B03EFB483C"></a>MUST fall back deterministically to default locale resource.

## 3. Locale Resolution

Resolution order:

1. explicit workspace locale,
2. explicit user locale,
3. runtime/browser locale,
4. default locale (`en-US` in `v1`).

Selected locale <a id="REQ-I18N-L10N-CONTRACT-V1-EB35E2E01E"></a>MUST be included in diagnostics and conformance metadata.

## 4. Locale-Sensitive Formatting

Number/date/time/relative-time formatting <a id="REQ-I18N-L10N-CONTRACT-V1-2A8A9295BE"></a>MUST use locale-aware formatter APIs with deterministic options per field context.

Pluralization <a id="REQ-I18N-L10N-CONTRACT-V1-E6E086C44B"></a>MUST use locale rules (for example CLDR category mapping via platform APIs or equivalent tables).

## 5. Directionality

LTR/RTL handling <a id="REQ-I18N-L10N-CONTRACT-V1-F9A1089438"></a>MUST remain compatible with doctrine requirements and include mirrored iconography where semantics require.

## 6. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `i18n.resource-missing` | Resource key missing in selected locale and fallback locale. | Conditional | Add key mapping or provide safe default string. |
| `i18n.locale-unsupported` | Requested locale is unsupported. | Conditional | Use supported locale or fallback chain. |
| `i18n.format-invalid` | Locale formatter options are invalid for target field. | No | Correct formatting configuration. |
| `i18n.pluralization-missing` | Required plural form missing for key. | Conditional | Add missing plural resource forms. |

## 7. Conformance

An implementation is conformant only if Sections 2-6 are enforced.
