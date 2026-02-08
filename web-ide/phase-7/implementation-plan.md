# Phase 7 Detailed Plan: Quality Gates and Hardening

## Document Control
- Status: Complete
- Last Updated: February 8, 2026
- Parent Plan: `web-ide/implementation-plan.md`
- Doctrine Sources:
  - `web-ide/ide-doctrine.md`
  - `web-ui/ui-doctrine.md`
  - `web-ide/phase-0/`
  - `web-ide/phase-1/implementation-plan.md`
  - `web-ide/phase-2/implementation-plan.md`
  - `web-ide/phase-3/implementation-plan.md`
  - `web-ide/phase-4/implementation-plan.md`
  - `web-ide/phase-5/implementation-plan.md`
  - `web-ide/phase-6/implementation-plan.md`

## Phase 7 Outcome
Convert the current feature-complete IDE into a release-grade system with explicit, enforced quality gates for performance, accessibility, and reliability.

## Scope
### In Scope
- Performance budget definitions and automatic enforcement for render/update paths.
- Transcript and recording scale budgets with deterministic behavior under load.
- Accessibility hardening for mixed DOM and canvas/WebGL surfaces.
- Keyboard-only interaction coverage for core workflows.
- Reliability hardening through deterministic replay and malformed-input resilience.
- CI/test gate wiring for quality thresholds.

### Out of Scope
- New major product capabilities (new instruments, major protocol families).
- Multi-user collaboration and cloud sync.
- Large visual redesigns outside doctrine compliance fixes.
- Browser support expansion beyond current supported matrix.

## Baseline
- Phases 0-6 are complete.
- Runtime bridge and typed command dispatch are operational.
- Customization and Beginner Mode are in place.
- Existing tests in `web-ui` are broad and currently green.

## Progress Snapshot
- M1 `QZ1`: Complete.
- M2 `QZ2`: Complete.
- M3 `QZ3`: Complete.
- M4 `QZ4`: Complete.
- M5 `QZ5`: Complete.
- M6 `QZ6`: Complete.
- M7 `QZ7`: Complete.

## Completion Record
- Added quality instrumentation subsystem and budget evaluator:
  - `web-ui/src/quality-gates.mjs`
  - integrated in `web-ui/src/state.mjs`, `web-ui/src/renderer.mjs`, `web-ui/src/widgets.mjs`, `web-ui/backends/canvas/renderer.mjs`, `web-ui/backends/webgl/renderer.mjs`, and `web-ui/src/runtime-bridge.mjs`.
- Added and wired acceptance suites:
  - `web-ui/tests/phase-7-performance-budgets.test.mjs`
  - `web-ui/tests/phase-7-transcript-scale.test.mjs`
  - `web-ui/tests/phase-7-keyboard-focus.test.mjs`
  - `web-ui/tests/phase-7-accessibility.test.mjs`
  - `web-ui/tests/phase-7-reliability.test.mjs`
  - `web-ui/tests/phase-7-integration.test.mjs`
- Added CI-oriented test scripts in `web-ui/package.json`:
  - `test:phase7`
  - `test:gate:fast`
  - `test:gate:full`
- Validation run:
  - `cd web-ui && npm run test:phase7` passed.
  - `cd web-ui && npm test` passed.

## Success Criteria
- Quality budgets are explicit, versioned, and test-enforced.
- Regressions against budgets fail CI deterministically.
- Core workflows remain keyboard-complete and screen-reader-comprehensible.
- High-volume transcript/session workflows remain responsive and recoverable.
- Reliability tests prove deterministic replay and safe degradation paths.

## Quality Budget Contract
1. UI turn budget:
- `ui.turn` p95 <= 16 ms for standard interactions in test harness.
- `ui.turn` p99 <= 32 ms for standard interactions in test harness.

2. Render budget:
- No full-surface redraw when dirty-rect hints are present and valid.
- Virtualized widgets render only visible + overscan rows.

3. Scale budget:
- Recording store supports >= 10,000 transcript entries with bounded memory growth via truncation policy.
- Snapshot/restore remains deterministic with recording truncation metadata.

4. Accessibility budget:
- 100% keyboard reachability for command palette, transcript, inspector, debugger, problems, and session/task lists.
- Canvas/WebGL widgets provide valid accessible fallback metadata (`role`, labels, focus behavior).

5. Reliability budget:
- Replay determinism must hold across repeated runs of the same event stream.
- Runtime malformed payload handling must degrade safely without unhandled exceptions.

## Workstreams

## QZ1: Budget Contracts and Instrumentation Foundation
### Goal
Define measurable quality contracts and collect the metrics needed to enforce them.

### Tasks
1. Define metric schema for turn timing, render work, and list virtualization behavior.
2. Add lightweight instrumentation hooks in:
   - state transition points
   - renderer update loop
   - canvas/WebGL draw paths
3. Ensure instrumentation can be enabled in tests without changing runtime semantics.
4. Record quality metrics in deterministic, test-readable structures.

### Deliverables
- Metric schema and helper module in `web-ui/src/`.
- Instrumentation hook integration in:
  - `web-ui/src/state.mjs`
  - `web-ui/src/renderer.mjs`
  - `web-ui/src/widgets.mjs`
  - `web-ui/backends/canvas/*.mjs`
  - `web-ui/backends/webgl/*.mjs`
- Baseline metric fixtures and assertions in `web-ui/tests/`.

### Exit Criteria
- Metrics are emitted with stable structure.
- Instrumentation overhead stays low and does not alter behavior.

## QZ2: Render Path and Interaction Budget Enforcement
### Goal
Enforce predictable render cost across DOM/canvas/WebGL backends.

### Tasks
1. Harden dirty-rect behavior and reject unnecessary full clears.
2. Tighten measurement cache behavior for repeated text/layout requests.
3. Enforce bounded draw-list behavior in WebGL path.
4. Add assertions for command-palette and list refresh render churn.
5. Add per-surface “budget exceeded” diagnostics in test mode.

### Deliverables
- Render budget assertions in:
  - `web-ui/tests/canvas-dirty-rects.test.mjs`
  - `web-ui/tests/widgets-dirty-rects.test.mjs`
  - `web-ui/tests/webgl-draw-list.test.mjs`
  - `web-ui/tests/ui-turn.test.mjs`
- Optional perf diagnostics surfaced in test artifacts.

### Exit Criteria
- Budget assertions are deterministic in CI.
- No regressions in functional rendering tests.

## QZ3: Transcript/Recording Scale Hardening
### Goal
Prove transcript and recording subsystems remain stable at realistic high volume.

### Tasks
1. Add synthetic high-volume transcript fixtures (10k+ entries).
2. Verify fold/copy/replay operations remain correct under scale.
3. Enforce recording truncation behavior and metadata integrity.
4. Validate snapshot/restore determinism under truncation.
5. Add integration flow: high-volume replay -> save -> restore -> continue.

### Deliverables
- Scale and truncation tests in new Phase 7 suites.
- Updated persistence and recording invariants if needed.

### Exit Criteria
- High-volume tests pass without timeouts or memory blowups in CI.
- Deterministic replay behavior remains intact.

## QZ4: Keyboard Completeness and Focus Reliability
### Goal
Guarantee keyboard-only operation for core instruments and robust focus semantics.

### Tasks
1. Define keyboard coverage matrix for core windows/surfaces.
2. Add coverage tests for open/navigate/execute/dismiss loops.
3. Harden focus history and focus reconciliation under rapid command sequences.
4. Validate no keyboard traps in command surfaces and list widgets.
5. Verify behavior under Beginner Mode and profile-switched keymaps.

### Deliverables
- Keyboard flow tests in new Phase 7 suites.
- Focus/fallback assertions in existing focus and command UI tests.

### Exit Criteria
- Coverage matrix passes for all required instrument workflows.
- Focus state remains valid and recoverable through rapid transitions.

## QZ5: Accessibility Semantics and Assistive Compatibility
### Goal
Bring mixed rendering surfaces to doctrine-aligned accessibility quality.

### Tasks
1. Audit widget semantics for roles, labels, and hidden-state behavior.
2. Ensure canvas/WebGL surfaces expose consistent fallback accessibility props.
3. Add reduced-motion coverage to ensure semantic clarity with motion disabled.
4. Add browser-harness checks for accessibility-critical DOM attributes.
5. Verify contrast and typography token constraints for readability.

### Deliverables
- Accessibility assertions in:
  - `web-ui/tests/widgets-command.test.mjs`
  - `web-ui/tests/browser.test.mjs`
  - new Phase 7 accessibility suites
- Documentation updates for required accessibility contracts.

### Exit Criteria
- Accessibility gates pass in sandbox and browser harness modes.
- Reduced-motion and keyboard pathways remain equivalent in semantics.

## QZ6: Reliability and Fault-Tolerance Gates
### Goal
Prevent runtime/input faults from breaking flow or corrupting state.

### Tasks
1. Expand malformed runtime message tests (shape/version/type errors).
2. Add command fuzz cases for argument coercion/validation paths.
3. Strengthen replay determinism checks across repeated seeds/runs.
4. Validate session restore recovery with stale presentation references and partial payloads.
5. Add explicit assertions for safe failure surfaces (error objects, not crashes).

### Deliverables
- Reliability suites in new Phase 7 tests.
- Bridge/codec/state guardrail improvements where tests expose gaps.

### Exit Criteria
- No unhandled exceptions in malformed-input suites.
- Determinism and restore resilience tests pass.

## QZ7: CI Integration and Release Gate Definition
### Goal
Turn quality checks into required release gates.

### Tasks
1. Add explicit Phase 7 test entrypoints in `web-ui/package.json`.
2. Group tests into fast gate vs full gate profiles.
3. Ensure quality gate failures produce actionable diagnostics.
4. Define release checklist using objective pass/fail conditions.
5. Update top-level planning docs with completion/signoff process.

### Deliverables
- Updated test scripts in `web-ui/package.json`.
- Phase 7 signoff checklist in planning docs.
- CI-ready test command matrix.

### Exit Criteria
- Phase 7 suites run in CI profile without manual intervention.
- Release checklist is executable and objective.

## Milestone Sequence
1. M1: QZ1 complete (contracts and instrumentation).
2. M2: QZ2 complete (render budget enforcement).
3. M3: QZ3 complete (transcript scale hardening).
4. M4: QZ4 complete (keyboard/focus hardening).
5. M5: QZ5 complete (accessibility hardening).
6. M6: QZ6 complete (reliability/fault tolerance gates).
7. M7: QZ7 complete (CI/release gate integration and signoff).

## Implementation Strategy
1. Define and instrument budgets first; optimize only after measurement exists.
2. Keep functional behavior stable while adding quality gates.
3. Prefer deterministic structural assertions over wall-clock-only tests where possible.
4. Land each milestone with tests first or in the same change.
5. Run full `web-ui` test suite at every milestone boundary.

## Code Focus Areas
- `web-ui/src/state.mjs`
- `web-ui/src/renderer.mjs`
- `web-ui/src/widgets.mjs`
- `web-ui/src/runtime-bridge.mjs`
- `web-ui/src/persistence/serialize.mjs`
- `web-ui/backends/canvas/*.mjs`
- `web-ui/backends/webgl/*.mjs`
- `web-ui/tests/ui-turn.test.mjs`
- `web-ui/tests/widgets-virtualization.test.mjs`
- `web-ui/tests/canvas-dirty-rects.test.mjs`
- `web-ui/tests/webgl-draw-list.test.mjs`
- `web-ui/tests/browser.test.mjs`
- `web-ui/tests/phase-7-*.test.mjs`

## Phase 7 Acceptance Suites
- `web-ui/tests/phase-7-performance-budgets.test.mjs`
- `web-ui/tests/phase-7-transcript-scale.test.mjs`
- `web-ui/tests/phase-7-keyboard-focus.test.mjs`
- `web-ui/tests/phase-7-accessibility.test.mjs`
- `web-ui/tests/phase-7-reliability.test.mjs`
- `web-ui/tests/phase-7-integration.test.mjs`

## Risks and Mitigations
- Risk: timing-based tests are flaky across environments.
  - Mitigation: prefer operation-count and structural gates; keep timing thresholds coarse and environment-normalized.
- Risk: performance instrumentation distorts behavior.
  - Mitigation: test-mode toggles and low-overhead counters only.
- Risk: accessibility fixes regress custom-rendered surfaces.
  - Mitigation: browser-harness and widget-level semantic assertions.
- Risk: stricter gates slow feature delivery.
  - Mitigation: separate fast gate and full gate profiles with clear ownership.

## Decision Gates (Resolved)
1. Budget strictness:
   - Selected: Option A (fail on exceedance for agreed p95/p99 limits).
2. Performance gate style:
   - Selected: Option A (hybrid structural + timing gates).
3. Accessibility release gate:
   - Selected: Option A (blocking for core workflows in the sandbox gate).
4. CI profile split:
   - Selected: Option A (`test:gate:fast` and `test:gate:full`).

## Phase 7 Signoff Conditions
- M1 through M7 complete.
- `cd web-ui && npm test` passes.
- All `phase-7-*` acceptance suites pass.
- Budget and accessibility gates are integrated into standard CI flows.
- Release checklist is ratified and repeatable.
