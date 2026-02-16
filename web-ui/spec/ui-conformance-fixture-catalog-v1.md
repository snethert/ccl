# UI Conformance Fixture Catalog v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-16  
Scope: Canonical fixture definitions for visual, motion, parity, and accessibility conformance  
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
6. Coarse-pointer touch targets: effective interactive hit box MUST be `>=44x44` px.

Required annotation:

1. If required fonts are unavailable, run MAY proceed.
2. Report MUST set `env.fontFallback=true`.

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

1. If assertion includes `tolerance`, measured value MUST satisfy comparator after tolerance is applied.
2. If tolerance is omitted, no tolerance is permitted.

Parity pair scoping:

1. Fixtures with `requiredHarness=parity` MAY declare `parityBackendPairs`.
2. When `parityBackendPairs` is declared, runners MUST execute only those pairs.
3. Backends listed in `parityBackendPairs` MUST be valid members of the fixture's effective backend lanes.

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

Any fixture without an existing binding MUST be implemented before production gate closure.

## 8. Failure Semantics

If any required fixture fails:

1. The run status MUST be `failed`.
2. Report MUST include failing fixture ID and assertion IDs.
3. Report MUST include deterministic reproduction metadata (`seed`, mode, backend, test path).
4. Production conformance gate MUST block release.

## 9. Change Policy

1. Fixture IDs are stable contract keys and MUST NOT be reused.
2. New fixtures MAY be added in minor versions.
3. Existing fixture semantics MAY only change in major versions.
4. Deprecation MUST be announced with migration replacement fixture ID.
