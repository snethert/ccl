# UI Conformance Matrix v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-16  
Scope: Requirement-to-fixture traceability for doctrine production contracts  
Depends on: `web-ui/spec/ui-conformance-fixtures-v1.json`, `web-ui/spec/ui-conformance-fixture-catalog-v1.md`, `web-ui/spec/ui-conformance-runner-contract-v1.md`
Compatibility: `v1.x` preserves requirement-to-fixture mapping IDs and traceability semantics; incompatible mapping-model changes require `v2`.
Fixture source: `web-ui/spec/ui-conformance-fixtures-v1.json`

## 1. Purpose

This matrix provides strict traceability from contract clauses to conformance fixtures.
Every normative clause listed here <a id="REQ-UI-CONFORMANCE-MATRIX-V1-52EAAFB445"></a>MUST map to at least one required fixture.

## 2. Traceability Table

| Contract Clause | Requirement Summary | Fixture IDs |
|---|---|---|
| `ui-component-visual-contract-v1.md#2` | Geometry/color/focus tolerances plus responsive/touch constraints | `vis.window.baseline.v1`, `vis.focus.geometry.v1`, `vis.responsive.touch-targets.v1`, `parity.dom-canvas.visual.v1`, `parity.dom-webgl.visual.v1` |
| `ui-component-visual-contract-v1.md#3` | Semantic token mapping only | `vis.window.baseline.v1`, `vis.component.state-matrix.v1` |
| `ui-component-visual-contract-v1.md#4.1` | Window geometry and focus behavior | `vis.window.baseline.v1`, `vis.focus.geometry.v1` |
| `ui-component-visual-contract-v1.md#4.2` | Button state semantics and legibility | `vis.component.state-matrix.v1`, `vis.disabled-error.legibility.v1`, `vis.responsive.touch-targets.v1` |
| `ui-component-visual-contract-v1.md#4.3` | Input focus/error semantics | `vis.component.state-matrix.v1`, `vis.disabled-error.legibility.v1`, `vis.responsive.touch-targets.v1` |
| `ui-component-visual-contract-v1.md#4.4` | List/tree selected/focus/error semantics | `vis.component.state-matrix.v1`, `vis.selection.contrast.v1`, `vis.responsive.touch-targets.v1` |
| `ui-component-visual-contract-v1.md#4.5` | Tab state semantics | `vis.component.state-matrix.v1`, `vis.responsive.touch-targets.v1` |
| `ui-component-visual-contract-v1.md#5.1` | DOM/Canvas parity | `parity.dom-canvas.visual.v1` |
| `ui-component-visual-contract-v1.md#5.2` | DOM/WebGL parity | `parity.dom-webgl.visual.v1` |
| `ui-component-visual-contract-v1.md#5.3` | Canvas/WebGL parity expectations | `parity.dom-webgl.visual.v1`, `a11y.proxy-parity.v1` |
| `ui-component-visual-contract-v1.md#6` | Degradation and diagnostics on unsupported effects | `motion.backend-drift.v1`, `a11y.proxy-parity.v1` |
| `ui-motion-contract-v1.md#3` | Approved transition classes only | `motion.class-timing.v1` |
| `ui-motion-contract-v1.md#4` | Duration/curve constraints | `motion.class-timing.v1` |
| `ui-motion-contract-v1.md#5` | Reduced-motion behavior | `motion.reduced-semantic.v1` |
| `ui-motion-contract-v1.md#6` | Interaction safety and interruption semantics | `motion.interrupt-determinism.v1` |
| `ui-motion-contract-v1.md#7` | Cross-backend motion parity | `motion.backend-drift.v1` |
| `ui-motion-contract-v1.md#8` | Motion failure semantics and diagnostics | `motion.interrupt-determinism.v1`, `motion.backend-drift.v1` |
| `ui-accessibility-visual-map-v1.md#2` | WCAG 2.2 AA baseline across all required color modes | `a11y.contrast.v1`, `a11y.high-contrast.forced-colors.v1`, `a11y.focus-visible.v1` |
| `ui-accessibility-visual-map-v1.md#3` | Contrast/focus/non-color thresholds | `a11y.contrast.v1`, `a11y.high-contrast.forced-colors.v1`, `a11y.focus-visible.v1`, `a11y.noncolor-cues.v1` |
| `ui-accessibility-visual-map-v1.md#4` | Reduced-motion accessibility mapping | `motion.reduced-semantic.v1` |
| `ui-accessibility-visual-map-v1.md#5` | Component-level accessibility cues | `a11y.noncolor-cues.v1`, `vis.disabled-error.legibility.v1` |
| `ui-accessibility-visual-map-v1.md#6` | Canvas/WebGL accessibility-proxy parity | `a11y.proxy-parity.v1` |
| `ui-accessibility-visual-map-v1.md#7` | Accessibility failure semantics | `a11y.contrast.v1`, `a11y.proxy-parity.v1` |
| `ui-conformance-runner-contract-v1.md#3` | Deterministic lane expansion and execution profile adherence | `all required fixture IDs` |
| `ui-conformance-runner-contract-v1.md#4` | Harness-specific execution semantics (`snapshot`, `geometry`, `contrast`, `parity`, `timing`, `replay`, `keyboard`) | `all required fixture IDs` |
| `ui-conformance-runner-contract-v1.md#7` | Report emission and schema-valid assertion output | `all required fixture IDs` |

## 3. Completion Rule

The matrix is complete only when:

1. Every fixture ID in this table has a bound automated test implementation.
2. Every bound test emits data that can populate `ui-conformance-report-schema-v1.json`.
3. No normative clause in referenced contracts is left unmapped.

## 4. Change Policy

1. Matrix updates are required whenever a referenced contract adds or removes normative clauses.
2. Matrix updates are required whenever fixture IDs are added, removed, or deprecated.
