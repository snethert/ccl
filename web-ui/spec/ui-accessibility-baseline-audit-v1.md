# UI Accessibility Baseline Audit v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-16  
Scope: Baseline contrast audit of current theme token values  
Depends on: `web-ui/spec/ui-visual-tokens-v1.json`, `web-ui/spec/ui-accessibility-visual-map-v1.md`
Compatibility: `v1.x` preserves normative requirements and failure semantics; incompatible changes require `v2`.

## 1. Purpose

This audit records measured baseline contrast ratios for current dark/light theme tokens.
It is a factual reference for production-gate readiness and remediation planning.

## 2. Measurement Method

Method:

1. Contrast ratios computed using WCAG relative luminance formula.
2. Color inputs sourced from current token values in `web-ui/src/theme.mjs`.
3. Pairs measured in dark and light modes separately.

Threshold mapping:

1. Text pairs must satisfy >= 4.5:1 (normal text) unless explicitly large-text-only.
2. Non-text boundaries/focus indicators must satisfy >= 3:1.

## 3. Historical Baseline Snapshot (Pre-Remediation)

This section is retained for traceability and represents measurements captured before adopted token remediation.

### Dark Mode

| Pair | Ratio | Threshold | Pass |
|---|---:|---:|---|
| `textPrimary/bg` | 15.29 | 4.5 | Yes |
| `textSecondary/bg` | 9.44 | 4.5 | Yes |
| `textMuted/bg` | 5.43 | 4.5 | Yes |
| `textPrimary/surface` | 14.06 | 4.5 | Yes |
| `selectionText/selection` | 8.57 | 4.5 | Yes |
| `focus/surface` | 10.13 | 3.0 | Yes |
| `border/surface` | 1.20 | 3.0 | No |
| `error/surface` | 5.76 | 4.5 | Yes |
| `warning/surface` | 9.27 | 4.5 | Yes |
| `success/surface` | 8.99 | 4.5 | Yes |

### Light Mode

| Pair | Ratio | Threshold | Pass |
|---|---:|---:|---|
| `textPrimary/bg` | 15.96 | 4.5 | Yes |
| `textSecondary/bg` | 8.93 | 4.5 | Yes |
| `textMuted/bg` | 5.27 | 4.5 | Yes |
| `textPrimary/surface` | 17.40 | 4.5 | Yes |
| `selectionText/selection` | 13.60 | 4.5 | Yes |
| `focus/surface` | 4.97 | 3.0 | Yes |
| `border/surface` | 1.45 | 3.0 | No |
| `error/surface` | 5.27 | 4.5 | Yes |
| `warning/surface` | 4.09 | 4.5 | No |
| `success/surface` | 5.33 | 4.5 | Yes |

## 4. Pre-Remediation Blockers (Historical)

The following blockers were identified relative to `ui-accessibility-visual-map-v1.md` before remediation:

1. `border/surface` contrast fails in dark and light modes.
2. `warning/surface` fails normal-text threshold in light mode.

## 5. Remediation Decision (Adopted)

Applied:

1. Updated dark `border` token.
2. Updated light `border` token.
3. Updated light `warning` token.
4. Updated `slate-dark` preset border token for non-text contrast parity.
5. Added regression test: `web-ui/tests/theme.test.mjs` (`theme tokens satisfy baseline accessibility contrast thresholds`).

## 6. Adopted Token Remediation Values

These values satisfy the stated thresholds while staying close to prior values:

| Token | Previous | Adopted | Target Pair | Measured Ratio |
|---|---|---|---|---:|
| dark `border` | `#2a2a2a` | `#676767` | `border/surface` (`#1b1b1b`) | 3.05 |
| light `border` | `#d6d6d6` | `#949494` | `border/surface` (`#ffffff`) | 3.03 |
| light `warning` | `#b96a10` | `#af640f` | `warning/surface` (`#ffffff`) | 4.51 |
| `slate-dark` `border` | `#293240` | `#566886` | `border/surface` (`#171d24`) | 3.01 |

## 7. Post-Remediation Verification (Current)

Current baseline snapshot (after adopted token values):

| Pair | Ratio | Threshold | Pass |
|---|---:|---:|---|
| dark `textPrimary/bg` | 15.29 | 4.5 | Yes |
| light `textPrimary/bg` | 15.96 | 4.5 | Yes |
| dark `selectionText/selection` | 8.57 | 4.5 | Yes |
| light `selectionText/selection` | 13.60 | 4.5 | Yes |
| dark `border/surface` | 3.05 | 3.0 | Yes |
| light `border/surface` | 3.03 | 3.0 | Yes |
| light `warning/surface` | 4.51 | 4.5 | Yes |

Current status summary:

1. Previously failing pairs now meet their required thresholds.
2. Token-level contrast regression checks are enforced in `web-ui/tests/theme.test.mjs`.
3. High-contrast and forced-colors lane thresholds are asserted in `web-ui/tests/phase-7-ui-conformance-fixtures.test.mjs`.

Open follow-up:

1. Add explicit contrast fixture implementation for `a11y.contrast.v1` in the conformance runner.
