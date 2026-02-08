# Phase 2 Detailed Plan: Instrument Surfaces

## Document Control
- Status: Complete
- Last Updated: February 8, 2026
- Parent Plan: `web-ide/implementation-plan.md`
- Doctrine Sources:
  - `web-ide/ide-doctrine.md`
  - `web-ui/ui-doctrine.md`
  - `web-ide/phase-0/*.md`
  - `web-ide/phase-1/implementation-plan.md`

## Phase 2 Outcome
Deliver doctrine-aligned instrument surfaces where REPL, Inspector, Debugger, and Problems operate as one cohesive system on top of the completed Phase 1 runtime and persistence contracts.

## Scope
### In Scope
- REPL transcript behavior upgrades on the existing recording model.
- Inspector upgrades as the universal pivot (structured views, watch pinning, safe staged edits).
- Debugger upgrade to restart-first workflows with frame/local inspection.
- Problems queue integration with source/presentation/debugger handoff.
- Cross-instrument interaction closure and acceptance tests.

### Out of Scope
- CL bridge/protocol expansion beyond existing Phase 1 payload contracts (Phase 5).
- Broad visual redesign and token rollout (Phase 3).
- Beginner mode and keymap productization (Phase 6).
- Full worldlet/session product features beyond Phase 1 persistence hooks (Phase 4).

## Baseline
- Phase 1 contracts are complete and tested:
  - deterministic output recording operations
  - typed command execution and history
  - selection action model
  - persistence schema `3` and migration path
  - presentation revalidation hooks on restore/refresh paths
- Current UI has open/refresh command scaffolding for transcript, inspector, debugger, and problems windows.

## Progress Snapshot
- M1 `WS1`: Complete.
- M2 `WS2`: Complete.
- M3 `WS3`: Complete.
- M4 `WS4`: Complete.
- M5 `WS5`: Complete.
- M6 `WS6`: Complete.
- Completed in this pass:
  - Transcript grouping, run collapse, and entry fold controls with action-bar wiring.
  - Inspector pinned watches with refresh-on-entry and persistence.
  - Staged edit groups with apply/undo commands surfaced in Inspector.
  - Debugger restart metadata rendered with typed restart invocation dispatch.
  - Problems queue metadata and deterministic ordering with action-bar handoff.
  - Phase 2 acceptance suites added and wired into `test:sandbox`.

## Phase 2 Success Criteria
- A full happy-path loop works without manual state patching:
  - transcript presentation -> inspector -> watch update after evaluation
- A full recovery loop works without context loss:
  - problem -> debugger -> restart invoke -> transcript update
- A full replay loop remains deterministic:
  - command history entry -> re-execute typed invocation -> equivalent recording output shape
- All new acceptance tests pass with existing `web-ui` suite.

## Workstreams

## WS1: REPL Transcript Instrument Completion
### Goal
Make transcript interaction fully doctrine-compliant: recording-first, presentation-first, and action-complete.

### Tasks
1. Add run-oriented transcript grouping metadata (recording header + entry cluster) while preserving stable entry addressing.
2. Add fold/collapse controls for runs and entries using recording operations, not DOM state.
3. Ensure action bar semantics are consistent for `value`, `command`, and `condition-section` entries.
4. Provide deterministic copy/replay/rerun flows from transcript selection.

### Deliverables
- Updates in `web-ui/src/state.mjs` and `web-ui/src/widgets.mjs`.
- Optional extraction module for transcript item shaping if needed.
- Expanded tests in transcript and integration suites.

### Exit Criteria
- Transcript remains deterministic across refresh and restore.
- Transcript actions dispatch effect handlers with no ad-hoc per-widget logic.

## WS2: Inspector as Universal Pivot
### Goal
Upgrade Inspector from diagnostic listing to operational pivot for typed objects and places.

### Tasks
1. Define type-aware inspector section builders for key presentation types.
2. Add pinned watch model and refresh path after command/recording updates.
3. Implement staged edit workflow for editable places:
  - stage edit
  - apply edit group
  - undo edit group
4. Emit auditable mutation events into transcript/history stream.

### Deliverables
- Inspector model updates in `web-ui/src/state.mjs`.
- Widget render support for staged edit controls in `web-ui/src/widgets.mjs`.
- Tests for watch refresh and staged edit apply/undo behavior.

### Exit Criteria
- Inspector can inspect and act without leaving instrument context.
- Edit-in-place is explicitly staged and reversible.

## WS3: Debugger Restart-First Flow
### Goal
Make debugger the primary recovery surface with clear restart affordances and frame inspection.

### Tasks
1. Extend debugger state model for restart metadata:
  - short label
  - long explanation
  - safety level
  - arg schema
2. Improve restart invocation flow with typed args/defaults and transparent recommendation hints.
3. Add frame and binding interaction hooks:
  - inspect local
  - jump to source
  - open in inspector
4. Track recent evaluation attempts in debugger context for recovery continuity.

### Deliverables
- Updates in `web-ui/src/state.mjs`, `web-ui/src/conditions.mjs`, and command registration paths.
- Debugger interaction tests for restart and frame flows.

### Exit Criteria
- Restart invocation is primary, typed, and auditable.
- Debugger can hand off to source/transcript/inspector without losing context.

## WS4: Problems Queue and Navigation Closure
### Goal
Make problems a reliable queue that routes users directly to action, not just a list of failures.

### Tasks
1. Add queue semantics:
  - severity labels
  - status transitions (`new`, `active`, `resolved`, `suppressed`)
  - deterministic ordering
2. Strengthen problem item metadata and handoff:
  - source location
  - presentation references
  - debugger focus target
3. Ensure queue refresh does not lose selection context unexpectedly.

### Deliverables
- Updates in problem item builders and refresh commands.
- Tests for open/refresh/selection/handoff behavior.

### Exit Criteria
- Problem item can always route to source or debugger with actionable context.
- Queue behavior is deterministic across refresh and persistence round-trip.

## WS5: Cross-Instrument Integration Closure
### Goal
Enforce the doctrine-level loops across instruments as a single runtime behavior.

### Tasks
1. Wire transcript -> inspector -> watch refresh loop.
2. Wire problems -> debugger -> restart -> transcript event loop.
3. Wire command history replay -> transcript + inspector consistency loop.
4. Verify stale presentation revalidation behavior in each loop after restore.

### Deliverables
- Integration harness updates in existing `web-ui` tests.
- New Phase 2 integration acceptance scenarios.

### Exit Criteria
- End-to-end scripted flows are deterministic in fresh and restored sessions.

## WS6: Phase 2 Acceptance and Quality Gates
### Goal
Encode Phase 2 outcomes as automated gates before Phase 3 work begins.

### Tasks
1. Add test suites:
  - `web-ui/tests/phase-2-transcript-inspector.test.mjs`
  - `web-ui/tests/phase-2-debugger.test.mjs`
  - `web-ui/tests/phase-2-problems.test.mjs`
  - `web-ui/tests/phase-2-integration.test.mjs`
2. Add deterministic replay assertions over phase-2 loops.
3. Add snapshot restore assertions for watch/edit/restart context preservation.
4. Wire all suites into `web-ui/package.json` `test:sandbox`.

### Exit Criteria
- All new Phase 2 tests pass.
- Existing `web-ui` tests remain green.

## Milestone Sequence
1. M1: WS1 complete (transcript closure).
2. M2: WS2 complete (inspector pivot behaviors).
3. M3: WS3 complete (debugger restart-first behaviors).
4. M4: WS4 complete (problems queue closure).
5. M5: WS5 complete (cross-instrument loops).
6. M6: WS6 complete (acceptance gates and signoff).

## Implementation Strategy
### Development Pattern
1. Implement one milestone in small patches.
2. Add milestone-specific tests before moving on.
3. Run full `web-ui` test suite after each milestone.
4. Update this plan with progress and completion notes.

### Code Focus Areas
- `web-ui/src/state.mjs`: window models, command wiring, cross-surface flows.
- `web-ui/src/widgets.mjs`: action surfaces, selection behavior, interaction controls.
- `web-ui/src/commands.mjs`: typed command parity and source tracking.
- `web-ui/src/conditions.mjs`: restart metadata normalization.
- `web-ui/src/persistence/*`: snapshot/restore invariants touched by new instrument state.

## Risks and Mitigations
- Risk: instrument behavior diverges into per-window special cases.
- Mitigation: keep command/effect pathways centralized and typed.
- Risk: staged edit model introduces hidden mutable state.
- Mitigation: represent staging explicitly in state and test apply/undo round-trip.
- Risk: debugger/problem loops regress when restore marks stale presentations.
- Mitigation: include restore + revalidation checks in all integration scenarios.
- Risk: test suite growth slows feedback loop.
- Mitigation: keep focused phase-2 suites plus a required full-suite gate.

## Decision Gates (Expected)
These decisions are deferred until their implementing milestone unless blocked earlier.

1. Inspector edit application policy:
- Option A (recommended): staged apply only, no immediate mutation on field edit.
- Option B: optional immediate apply for selected types.

2. Debugger attempt history depth default:
- Option A (recommended): keep last 50 attempts.
- Option B: keep last 100 attempts.

3. Problems dedupe policy:
- Option A (recommended): fingerprint by `kind + message + location`.
- Option B: keep all emissions as distinct rows.

## Phase 2 Signoff Conditions
- M1 through M6 complete.
- `cd web-ui && npm test` passes.
- Phase 2 acceptance suites pass.
- REPL -> Inspector -> Debugger doctrine loop demonstrated through automated tests.
 - Last verified: February 8, 2026 (`npm test` pass).
