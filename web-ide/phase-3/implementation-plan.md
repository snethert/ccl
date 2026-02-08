# Phase 3 Detailed Plan: UI Doctrine Implementation

## Document Control
- Status: Planned
- Last Updated: February 8, 2026
- Parent Plan: `web-ide/implementation-plan.md`
- Doctrine Sources:
- `web-ui/ui-doctrine.md`
- `web-ide/ide-doctrine.md`
- `web-ide/phase-0/*.md`
- `web-ide/phase-2/implementation-plan.md`

## Phase 3 Outcome
Deliver a visual system that matches `web-ui/ui-doctrine.md` across DOM and canvas/WebGL surfaces, with shared tokens, typography-first hierarchy, motion semantics, and light/dark parity.

## Scope
### In Scope
- Theme token system expansion and light/dark palettes.
- DOM stylesheet for widget classes and instrument shells.
- Typography scale, density rules, and layout rhythm.
- Motion semantics and reduced-motion behavior.
- Visual polish for core instruments (Transcript, Inspector, Debugger, Problems).
- Renderer parity for DOM and canvas/WebGL (shared tokens and behaviors).
- Visual acceptance gates tied to the UI Doctrine.

### Out of Scope
- New instrument behaviors or CL runtime protocol expansion (Phase 5).
- Beginner mode, keymap productization, or full customization UI (Phase 6).
- New windowing features or layout model changes (Phase 4).
- Performance budgets and large-scale a11y program (Phase 7).

## Baseline
- Phase 2 instrument behaviors are complete and tested.
- `web-ui/src/theme.mjs` provides a minimal token set and dark mode default.
- DOM widgets expose stable class names but are not doctrine-styled.
- Canvas/WebGL renderers do not yet consume theme tokens uniformly.

## Progress Snapshot
- M1 `WS1`: Planned.
- M2 `WS2`: Planned.
- M3 `WS3`: Planned.
- M4 `WS4`: Planned.
- M5 `WS5`: Planned.
- M6 `WS6`: Planned.
- M7 `WS7`: Planned.

## Phase 3 Success Criteria
- Theme tokens are single-source of truth for DOM and canvas/WebGL.
- Light and dark mode palettes are distinct and doctrine-compliant.
- Two instruments meet doctrine targets in both modes.
- Motion can be globally suppressed without loss of meaning.
- Visual acceptance tests pass with the existing `web-ui` suite.

## Workstreams

## WS1: Token System and Theme Infrastructure
### Goal
Expand the token model and ensure it drives DOM and renderer output.

### Tasks
1. Expand token schema to include borders, focus rings, state colors, and typography scale.
2. Define light mode palette and accent rules.
3. Add token to CSS variable mapping for DOM backends.
4. Add token to renderer mapping for canvas/WebGL surfaces.
5. Expose runtime hooks to apply theme mode changes across backends.

### Deliverables
- `web-ui/src/theme.mjs` expanded token schema and normalization.
- DOM backend theme injection and CSS variable binding.
- Canvas/WebGL renderer theme application helpers.
- Tests for token normalization and mode switching.

### Exit Criteria
- Switching `theme.mode` updates DOM variables and renderer styles deterministically.
- Token coverage is sufficient for component skins without per-widget ad hoc styling.

## WS2: DOM Stylesheet and Component Skins
### Goal
Implement doctrine-aligned styling for widget classes in DOM surfaces.

### Tasks
1. Create a base stylesheet for `ui-window`, `ui-widget`, and list/table primitives.
2. Define selection, hover, disabled, and focus states from tokens.
3. Style action bars and command surfaces as coherent instrument controls.
4. Ensure spacing and grouping follow the density doctrine.

### Deliverables
- `web-ui/styles/ui.css` (or equivalent) with token-backed variables.
- DOM backend hooks to attach the stylesheet.
- Visual smoke test fixtures for DOM output.

### Exit Criteria
- DOM widgets read as a coherent instrument and honor spacing and elevation rules.

## WS3: Typography and Density System
### Goal
Make typography the primary structural tool and lock spacing rhythm.

### Tasks
1. Choose body and monospace stacks aligned to the doctrine.
2. Define a typographic scale, line heights, and glyph metrics.
3. Align list row heights and grid spacing to the token system.
4. Ensure canvas text measurement uses the same tokenized font stack.

### Deliverables
- Token updates for font stack, size scale, line height.
- Updated text measurement defaults in DOM and canvas backends.
- Tests verifying consistent measurement defaults.

### Exit Criteria
- Typography and spacing are consistent across DOM and canvas output.

## WS4: Motion Semantics and Reduced Motion
### Goal
Encode doctrine-level motion semantics in the UI system.

### Tasks
1. Define motion tokens for durations and easing curves.
2. Apply transitions to window, list selection, and action surfaces.
3. Implement reduced-motion handling in DOM and renderer flows.
4. Ensure motion never blocks interaction and can be suppressed globally.

### Deliverables
- Motion tokens in theme and CSS.
- Motion suppression rules for DOM and canvas/WebGL.
- Tests that verify `motion.reduced` disables animations.

### Exit Criteria
- Motion explains state change without distracting or blocking.

## WS5: Instrument Visual Pass
### Goal
Bring core instruments to doctrine compliance in both modes.

### Tasks
1. Transcript shell and run grouping visuals.
2. Inspector layout, watch list, and staged edit indicators.
3. Debugger restart list with safety and recommendation cues.
4. Problems queue with severity tags and status indicators.

### Deliverables
- Instrument-specific CSS classes and layout rules.
- Token-driven color and typography usage for these panels.
- Updated smoke test snapshots for these instruments.

### Exit Criteria
- Transcript and Inspector match doctrine in both light and dark modes.

## WS6: Canvas and WebGL Theme Parity
### Goal
Ensure non-DOM surfaces read like the same instrument.

### Tasks
1. Add theme inputs to canvas and WebGL renderers.
2. Standardize background, selection, and text colors from tokens.
3. Align canvas text metrics with DOM typography tokens.

### Deliverables
- Renderer theme application helpers and tests.
- Updated canvas/WebGL snapshot tests.

### Exit Criteria
- Canvas and WebGL scenes match DOM color and typography cues.

## WS7: Phase 3 Acceptance and Quality Gates
### Goal
Encode doctrine compliance as automated gates.

### Tasks
1. Add Phase 3 acceptance suite for theme tokens and mode switching.
2. Add DOM snapshot tests for two instruments in light and dark mode.
3. Add renderer parity tests for canvas and WebGL.
4. Wire suites into `web-ui/package.json` `test:sandbox`.

### Deliverables
- `web-ui/tests/phase-3-ui-doctrine.test.mjs` and related fixtures.
- Updated `web-ui/tests/theme.test.mjs` coverage.
- Browser harness snapshots if needed.

### Exit Criteria
- Phase 3 suites pass and existing tests remain green.

## Milestone Sequence
1. M1: WS1 complete (token system and theme infrastructure).
2. M2: WS2 complete (DOM base styles and component skins).
3. M3: WS3 complete (typography and density system).
4. M4: WS4 complete (motion semantics and reduced motion).
5. M5: WS5 complete (instrument visual pass).
6. M6: WS6 complete (canvas/WebGL parity).
7. M7: WS7 complete (acceptance gates and signoff).

## Implementation Strategy
1. Extend tokens first, then apply to DOM styles, then renderer parity.
2. Style two instruments end-to-end before moving to the rest.
3. Add tests alongside each workstream and run full `web-ui` suite after each milestone.
4. Update this plan with progress and completion notes after each milestone.

## Code Focus Areas
- `web-ui/src/theme.mjs`
- `web-ui/backends/dom/renderer.mjs`
- `web-ui/backends/canvas/renderer.mjs`
- `web-ui/backends/webgl/renderer.mjs`
- `web-ui/src/widgets.mjs`
- `web-ui/styles/*`

## Risks and Mitigations
- Risk: token expansion causes divergence between DOM and renderer.
- Mitigation: enforce single token source and add parity tests.
- Risk: font stack availability across platforms.
- Mitigation: provide fallbacks and document required assets.
- Risk: motion degrades performance on large surfaces.
- Mitigation: keep transitions small and disable on reduced motion.
- Risk: visual changes break usability for dense workflows.
- Mitigation: keep density presets minimal and validate with instrument tests.

## Decision Gates (Expected)
1. Typography stacks and licensing.
2. Light mode palette and accent policy.
3. Motion easing curve and default durations.
4. Density preset strategy (single default vs compact/comfortable).

## Phase 3 Signoff Conditions
- M1 through M7 complete.
- `cd web-ui && npm test` passes.
- Phase 3 acceptance suites pass.
- Two instruments fully match UI Doctrine in light and dark modes.
