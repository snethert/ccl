# UI Conformance Fixture Catalog v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-16  
Scope: Canonical fixture definitions for visual, motion, parity, and accessibility conformance  
Depends on: `web-ui/spec/ui-conformance-fixtures-v1.json`, `web-ui/spec/ui-conformance-runner-contract-v1.md`, `web-ui/spec/ui-conformance-report-schema-v1.json`
Compatibility: `v1.x` preserves fixture IDs, assertion semantics, and evidence mapping references; incompatible fixture-contract changes require `v2`.
Canonical machine source: `web-ui/spec/ui-conformance-fixtures-v1.json`
Runner semantics: `web-ui/spec/ui-conformance-runner-contract-v1.md`

## 1. Purpose

This catalog defines the fixture-level contract for production UI conformance.
Each fixture has a stable ID, measurable assertions, and required artifacts.

## 2. Conformance Rule

A run is conformant only if:

1. All fixtures with `status=required` execute.
2. Every assertion for those fixtures passes.
3. A report is emitted that validates against `web-ui/spec/ui-conformance-report-schema-v1.json`.
4. Fixture execution semantics conform to `web-ui/spec/ui-conformance-runner-contract-v1.md`.

## 3. Execution Environment

Required environment:

1. Deterministic seed: `ui-conformance-v1`.
2. Viewport lanes:
- `desktop-lg`: `1440x900`, device scale factor `2`, pointer `fine`.
- `tablet`: `1024x768`, device scale factor `2`, pointer `coarse`.
- `mobile`: `390x844`, device scale factor `3`, pointer `coarse`.
3. Modes: dark, light, high-contrast, forced-colors.
4. Backends: dom, canvas, webgl.
5. Monotonic clock and 60 Hz animation-frame scheduling.
6. Coarse-pointer touch targets: effective interactive hit box <a id="REQ-UI-CONFORMANCE-FIXTURE-CATALOG-V1-3CA08F19A1"></a>MUST be `>=44x44` px.

Required annotation:

1. If required fonts are unavailable, run MAY proceed.
2. Report <a id="REQ-UI-CONFORMANCE-FIXTURE-CATALOG-V1-4A8CBA8502"></a>MUST set `env.fontFallback=true`.

## 4. Fixture Classes

1. `visual`: component snapshots and geometry/color checks.
2. `parity`: backend-to-backend equivalence constraints.
3. `motion`: timing and reduced-motion behavior.
4. `a11y`: contrast/focus/non-color/proxy requirements.

## 5. Assertion Semantics

Comparators are normative:

1. `==`: exact equality after normalization.
2. `<=` / `>=`: inclusive numeric thresholds.
3. `stable-hash`: identical hash across repeated runs with same seed.
4. Boolean comparators evaluate strict truth value.

Tolerance:

1. If assertion includes `tolerance`, measured value <a id="REQ-UI-CONFORMANCE-FIXTURE-CATALOG-V1-16A94C3F2E"></a>MUST satisfy comparator after tolerance is applied.
2. If tolerance is omitted, no tolerance is permitted.

Parity pair scoping:

1. Fixtures with `requiredHarness=parity` MAY declare `parityBackendPairs`.
2. When `parityBackendPairs` is declared, runners <a id="REQ-UI-CONFORMANCE-FIXTURE-CATALOG-V1-19EB318DC4"></a>MUST execute only those pairs.
3. Backends listed in `parityBackendPairs` <a id="REQ-UI-CONFORMANCE-FIXTURE-CATALOG-V1-EE70E7C375"></a>MUST be valid members of the fixture's effective backend lanes.

## 6. Required Fixture Set

### Visual

1. `vis.window.baseline.v1`
2. `vis.component.state-matrix.v1`
3. `vis.focus.geometry.v1`
4. `vis.selection.contrast.v1`
5. `vis.disabled-error.legibility.v1`
6. `vis.responsive.touch-targets.v1`

### Parity

1. `parity.dom-canvas.visual.v1`
2. `parity.dom-webgl.visual.v1`

### Motion

1. `motion.class-timing.v1`
2. `motion.reduced-semantic.v1`
3. `motion.interrupt-determinism.v1`
4. `motion.backend-drift.v1`

### Accessibility

1. `a11y.contrast.v1`
2. `a11y.high-contrast.forced-colors.v1`
3. `a11y.focus-visible.v1`
4. `a11y.noncolor-cues.v1`
5. `a11y.proxy-parity.v1`

## 7. Existing Test Binding

The following existing tests are accepted as baseline bindings:

1. `web-ui/tests/phase-3-dom-snapshots.test.mjs`
2. `web-ui/tests/phase-3-renderer-parity.test.mjs`
3. `web-ui/tests/phase-7-keyboard-focus.test.mjs`
4. `web-ui/tests/phase-7-accessibility.test.mjs`
5. `web-ui/tests/theme.test.mjs`
6. `web-ui/tests/phase-7-ui-conformance-fixtures.test.mjs`

Any fixture without an existing binding <a id="REQ-UI-CONFORMANCE-FIXTURE-CATALOG-V1-5F72D98BA2"></a>MUST be implemented before production gate closure.

## 8. Failure Semantics

If any required fixture fails:

1. The run status <a id="REQ-UI-CONFORMANCE-FIXTURE-CATALOG-V1-C7DE5E9C60"></a>MUST be `failed`.
2. Report <a id="REQ-UI-CONFORMANCE-FIXTURE-CATALOG-V1-2A0894A499"></a>MUST include failing fixture ID and assertion IDs.
3. Report <a id="REQ-UI-CONFORMANCE-FIXTURE-CATALOG-V1-9971CFD14F"></a>MUST include deterministic reproduction metadata (`seed`, mode, backend, test path).
4. Production conformance gate <a id="REQ-UI-CONFORMANCE-FIXTURE-CATALOG-V1-8C0D9A4862"></a>MUST block release.

## 9. Change Policy

1. Fixture IDs are stable contract keys and <a id="REQ-UI-CONFORMANCE-FIXTURE-CATALOG-V1-6D7B4E538E"></a>MUST NOT be reused.
2. New fixtures MAY be added in minor versions.
3. Existing fixture semantics MAY only change in major versions.
4. Deprecation <a id="REQ-UI-CONFORMANCE-FIXTURE-CATALOG-V1-5801AF6606"></a>MUST be announced with migration replacement fixture ID.
