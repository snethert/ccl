# UI Accessibility Visual Map v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-16  
Scope: Visual accessibility conformance for `web-ui`  
Depends on: `web-ui/spec/ui-visual-tokens-v1.json`, `web-ui/spec/ui-component-visual-contract-v1.md`, `web-ui/spec/ui-motion-contract-v1.md`

## 1. Purpose

This document maps visual requirements to measurable accessibility criteria.
It is the normative reference for visual accessibility acceptance in `web-ui`.

## 2. Conformance Baseline

Target baseline:

- WCAG 2.2 Level AA for visual criteria applicable to UI components.

A build is conformant only if all criteria in this document pass for dark, light, high-contrast, and forced-colors modes.

## 3. Contrast and Visual Thresholds

Text contrast:

1. Normal text (below 24 px regular / 19 px bold) <a id="REQ-UI-ACCESSIBILITY-VISUAL-MAP-V1-DEDEAC160F"></a>MUST meet >= 4.5:1.
2. Large text (>= 24 px regular or >= 19 px bold) <a id="REQ-UI-ACCESSIBILITY-VISUAL-MAP-V1-47DB518BA5"></a>MUST meet >= 3:1.

Non-text contrast:

1. Visual boundaries for controls, icons, focus indicators, and selected rows <a id="REQ-UI-ACCESSIBILITY-VISUAL-MAP-V1-FBF58BF46B"></a>MUST meet >= 3:1 against adjacent colors.

Focus visibility:

1. Focus indicator <a id="REQ-UI-ACCESSIBILITY-VISUAL-MAP-V1-83E0AD02AD"></a>MUST be present for keyboard focusable controls.
2. Focus indicator width <a id="REQ-UI-ACCESSIBILITY-VISUAL-MAP-V1-7E0E8EB642"></a>MUST be >= 2 px.
3. Focus indicator contrast against adjacent colors <a id="REQ-UI-ACCESSIBILITY-VISUAL-MAP-V1-213CDF6BE8"></a>MUST be >= 3:1.
4. Focus indicator <a id="REQ-UI-ACCESSIBILITY-VISUAL-MAP-V1-399068F5AA"></a>MUST remain visible in dark, light, high-contrast, and forced-colors modes.

Color dependency:

1. Color <a id="REQ-UI-ACCESSIBILITY-VISUAL-MAP-V1-6B2BB3CEA4"></a>MUST NOT be the sole channel for critical state (`error`, `warning`, `selected`, `recommended`).
2. At least one non-color cue <a id="REQ-UI-ACCESSIBILITY-VISUAL-MAP-V1-C33B2354B8"></a>MUST exist (iconography, border pattern, label text, or structural marker).

## 4. Motion Accessibility Mapping

1. Reduced-motion setting <a id="REQ-UI-ACCESSIBILITY-VISUAL-MAP-V1-A7EE61D39A"></a>MUST disable transform/position animations.
2. Reduced-motion mode <a id="REQ-UI-ACCESSIBILITY-VISUAL-MAP-V1-E3120BE0A9"></a>MUST preserve semantic state transitions using non-motion cues.
3. Motion suppression <a id="REQ-UI-ACCESSIBILITY-VISUAL-MAP-V1-6BF28F9B48"></a>MUST NOT remove focus, selection, or error feedback.

## 5. Component Accessibility Visual Map

| Component | State | Required visual cue(s) | Minimum measurable requirement |
|---|---|---|---|
| Window | Focused | Distinct focus edge/ring | >= 3:1 non-text contrast vs surrounding surface |
| Button | Focused | Focus ring or equivalent | Ring >= 2 px and >= 3:1 contrast |
| Button | Disabled | Non-interactive appearance without unreadability | Label contrast remains >= 4.5:1 (normal text) |
| Text input | Error | Error-highlighted boundary + non-color cue | Boundary >= 3:1 and companion text/icon present |
| List row | Selected | Selection fill + selection text color | Selected text >= 4.5:1 vs selected fill |
| Restart row | Safety levels | Border/status marker + label | Distinguishable without hue interpretation alone |
| Problems row | Warning/Error/Info | Severity marker + readable text | Marker >= 3:1, text >= 4.5:1 |

## 6. Canvas/WebGL Accessibility Parity

For non-DOM surfaces:

1. A semantic accessibility proxy <a id="REQ-UI-ACCESSIBILITY-VISUAL-MAP-V1-F4AAF49919"></a>MUST exist for keyboard focus and screen-reader mapping.
2. Proxy focus location <a id="REQ-UI-ACCESSIBILITY-VISUAL-MAP-V1-04A956DBCF"></a>MUST match rendered target bounds within +/- 1 px.
3. Proxy state (`selected`, `error`, `disabled`) <a id="REQ-UI-ACCESSIBILITY-VISUAL-MAP-V1-BB6E48B70A"></a>MUST mirror rendered state exactly.
4. Loss of proxy synchronization <a id="REQ-UI-ACCESSIBILITY-VISUAL-MAP-V1-4A105DC72D"></a>MUST be treated as a conformance failure.

## 7. Failure Semantics

If any criterion fails:

1. The UI <a id="REQ-UI-ACCESSIBILITY-VISUAL-MAP-V1-84F3AF8A02"></a>MUST degrade to a safer accessible fallback presentation.
2. The conformance run <a id="REQ-UI-ACCESSIBILITY-VISUAL-MAP-V1-50C17E7A21"></a>MUST fail with criterion ID and component/state context.
3. A structured diagnostic event <a id="REQ-UI-ACCESSIBILITY-VISUAL-MAP-V1-88BAC24C65"></a>MUST be emitted for telemetry correlation.

## 8. Required Test Artifacts

1. Contrast audit fixture for all core components in dark, light, high-contrast, and forced-colors modes.
2. Keyboard focus traversal fixture with focus-indicator assertions.
3. Reduced-motion fixture proving semantic parity with motion enabled.
4. Canvas/WebGL accessibility-proxy parity fixture.
5. Severity-state fixture proving non-color redundancy for errors/warnings/safety levels.
6. High-contrast/forced-colors fixture proving focus and non-text boundary visibility.

## 9. Conformance IDs

The following IDs <a id="REQ-UI-ACCESSIBILITY-VISUAL-MAP-V1-5335D696DE"></a>MUST be used in accessibility reports:

- `a11y-text-contrast-aa`
- `a11y-nontext-contrast`
- `a11y-hc-text-contrast-aa`
- `a11y-forced-colors-focus-contrast`
- `a11y-focus-visible`
- `a11y-noncolor-state-cue`
- `a11y-reduced-motion-semantic-parity`
- `a11y-canvas-webgl-proxy-parity`

Canonical fixture IDs and assertion definitions are in:
- `web-ui/spec/ui-conformance-fixtures-v1.json`
- `web-ui/spec/ui-conformance-fixture-catalog-v1.md`
- `web-ui/spec/ui-conformance-matrix-v1.md`
- `web-ui/spec/ui-conformance-report-schema-v1.json`

Current baseline measurement record:
- `web-ui/spec/ui-accessibility-baseline-audit-v1.md`
