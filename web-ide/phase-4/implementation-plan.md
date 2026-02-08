# Phase 4 Detailed Plan: World State and Sessions

## Document Control
- Status: Completed
- Last Updated: February 8, 2026
- Parent Plan: `web-ide/implementation-plan.md`
- Doctrine Sources:
  - `web-ide/ide-doctrine.md`
  - `web-ui/ui-doctrine.md`
  - `web-ide/phase-0/*.md`
  - `web-ide/phase-1/implementation-plan.md`
  - `web-ide/phase-2/implementation-plan.md`
  - `web-ide/phase-3/implementation-plan.md`

## Phase 4 Outcome
Deliver a safe, persistent “world state” for the IDE: workspace snapshots, session restore, and stale presentation revalidation so users can leave and return without losing orientation.

## Scope
### In Scope
- Workspace snapshots for UI state: layout, windows, open instruments, transcript history, command history, watches, and selections.
- Session registry with metadata (name, timestamps, last opened, notes).
- Session restore with presentation revalidation and explicit stale handling.
- World state API and commands to save, restore, rename, and delete sessions.
- Acceptance tests for snapshot/restore determinism.

### Out of Scope
- CL runtime snapshots or full image serialization (Phase 5).
- Beginner mode and customization surfaces (Phase 6).
- Performance budgets and accessibility program (Phase 7).

## Baseline
- Phase 1 persistence schema and migration hooks are implemented.
- Phase 2 instrument state is fully represented in the core state model.
- Phase 3 visual system is stable across DOM and canvas/WebGL.

## Progress Snapshot
- M1 `WS1`: Completed.
- M2 `WS2`: Completed.
- M3 `WS3`: Completed.
- M4 `WS4`: Completed.
- M5 `WS5`: Completed.
- M6 `WS6`: Completed.

## Phase 4 Success Criteria
- Cold start restores a coherent workspace with layout and open instruments intact.
- Stale presentations remain readable and are explicitly marked until revalidated.
- Session restore is deterministic and testable across snapshot/restore cycles.
- Multiple sessions can be created, named, and switched without state corruption.

## Workstreams

## WS1: Snapshot Schema and Storage Model
### Goal
Define a stable, versioned snapshot envelope for world state and sessions.

### Tasks
1. Define session metadata fields:
   - `id`, `name`, `createdAt`, `lastOpenedAt`, `lastSavedAt`, `notes`.
2. Define snapshot payload shape for UI state:
   - workspace layout, windows, widgets, transcript/recording store, command history, watches, selections, focus.
3. Define truncation budgets for transcript and history in snapshots.
4. Update persistence schema version and migration hooks.

### Deliverables
- Updated schema in `web-ui/src/persistence/schema.mjs`.
- Snapshot envelope updates in `web-ui/src/persistence/serialize.mjs`.
- Migration logic in `web-ui/src/persistence/migrate.mjs`.

### Exit Criteria
- Snapshot envelope is versioned and validated by tests.
- Legacy snapshots migrate deterministically.

## WS2: Session Registry and World State API
### Goal
Create APIs to manage sessions and tie them to snapshot storage.

### Tasks
1. Implement a session registry in state with CRUD operations.
2. Add commands for:
   - create session
   - save session
   - rename session
   - delete session
   - open session
3. Record session events in the event log for auditability.
4. Persist session registry alongside snapshots.

### Deliverables
- State updates in `web-ui/src/state.mjs`.
- Command wiring in `web-ui/src/commands.mjs` and `web-ui/src/typed-commands.mjs`.
- Event log entries for session lifecycle events.

### Exit Criteria
- Sessions can be created, renamed, deleted, and reopened.
- Session registry persists across reload.

## WS3: Restore + Revalidation Pipeline
### Goal
Restore sessions with safe stale handling and explicit revalidation controls.

### Tasks
1. Add restore workflow that flags presentations as stale when references cannot be resolved.
2. Add revalidation hooks to attempt resurrection on demand and on refresh.
3. Ensure transcript entries remain readable even when presentations are stale.
4. Add diagnostics for failed revalidation (in inspector or event log).

### Deliverables
- Revalidation logic in `web-ui/src/world-state.mjs`.
- Restore flow updates in `web-ui/src/persistence/serialize.mjs` and `web-ui/src/state.mjs`.
- Tests for stale presentation behavior and revalidation.

### Exit Criteria
- Restore never throws due to stale references.
- Revalidation status is visible and deterministic.

## WS4: Workspace Restore and Layout Integrity
### Goal
Guarantee layout integrity and instrument continuity after restore.

### Tasks
1. Validate layout graph on restore and repair invalid references.
2. Reopen windows and instruments in the last active order.
3. Restore focus and selection context where possible.
4. Keep command history and transcript sequences consistent across restore.

### Deliverables
- Layout repair logic in `web-ui/src/layout.mjs`.
- Restore helpers in `web-ui/src/persistence/serialize.mjs`.
- Tests for layout and window rehydration.

### Exit Criteria
- Restored sessions match pre-save layout and open windows.
- Focus/selection is preserved or explicitly cleared with reason.

## WS5: Session UX Surfaces
### Goal
Provide minimal, doctrine-aligned surfaces to manage sessions.

### Tasks
1. Add a session list window with selection + action bar.
2. Provide commands for quick save/restore from command palette.
3. Add a safe delete flow with confirmation.
4. Add inline metadata editing for session names/notes.

### Deliverables
- New window and widgets in `web-ui/src/state.mjs` and `web-ui/src/widgets.mjs`.
- Command palette integration and typed command entries.
- Tests for session UI behavior and command wiring.

### Exit Criteria
- Session operations are accessible without leaving the main workflow.
- No session action requires manual state edits.

## WS6: Phase 4 Acceptance and Quality Gates
### Goal
Codify world-state stability as automated gates.

### Tasks
1. Add Phase 4 tests:
   - snapshot/restore determinism
   - stale presentation safety
   - session registry CRUD
   - layout rehydration integrity
2. Wire tests into `web-ui/package.json` `test:sandbox`.
3. Add at least one integration test covering:
   - save -> reload -> restore -> revalidate -> transcript/inspector continuity.

### Deliverables
- `web-ui/tests/phase-4-world-state.test.mjs`
- `web-ui/tests/phase-4-sessions.test.mjs`
- `web-ui/tests/phase-4-restore.test.mjs`

### Exit Criteria
- Phase 4 acceptance suites pass.
- Existing `web-ui` suites remain green.

## Milestone Sequence
1. M1: WS1 complete (snapshot schema and migrations).
2. M2: WS2 complete (session registry + commands).
3. M3: WS3 complete (restore + revalidation).
4. M4: WS4 complete (layout integrity + focus/selection restore).
5. M5: WS5 complete (session UX surfaces).
6. M6: WS6 complete (acceptance gates and signoff).

## Implementation Strategy
1. Extend persistence schema first, then registry and restore pipeline.
2. Add revalidation behavior before session UI to avoid hidden failure modes.
3. Add tests alongside each milestone and run full suite after each milestone.
4. Update this plan with progress and completion notes after each milestone.

## Completion Notes
- Implemented session registry and CRUD operations in `web-ui/src/state.mjs`, including session list surfaces and command outputs.
- Persistence schema bumped to `4` with migration support and session-aware snapshots.
- Restore flow supports layout repair and stale presentation marking via `web-ui/src/layout.mjs` and `web-ui/src/persistence/serialize.mjs`.
- Persistence manager now saves, restores, and deletes sessions.
- Phase 4 tests added and wired into `web-ui/package.json`.
- World state logic lives in persistence/state modules; no separate `world-state.mjs` yet.

## Code Focus Areas
- `web-ui/src/persistence/schema.mjs`
- `web-ui/src/persistence/serialize.mjs`
- `web-ui/src/persistence/migrate.mjs`
- `web-ui/src/persistence/manager.mjs`
- `web-ui/src/state.mjs`
- `web-ui/src/layout.mjs`
- `web-ui/src/index.mjs`
- `web-ui/src/command-effects.mjs`

## Risks and Mitigations
- Risk: snapshot bloat makes restore slow.
  - Mitigation: strict truncation budgets and lazy revalidation.
- Risk: stale presentations confuse users.
  - Mitigation: explicit stale markers and revalidate actions.
- Risk: layout restore produces invalid graphs.
  - Mitigation: repair invalid references and log corrections.
- Risk: session registry corruption.
  - Mitigation: schema versioning and migration tests.

## Decision Gates (Expected)
1. Snapshot retention policy:
- Option A (recommended): keep last 10 sessions, evict oldest on save.
- Option B: keep last N per workspace with size-based eviction.

2. Transcript truncation budget:
- Option A (recommended): keep last 5,000 entries per session.
- Option B: keep last 2,000 entries per session.

3. Revalidation strategy:
- Option A (recommended): mark stale on restore, revalidate on demand.
- Option B: attempt revalidate during restore with timeouts.

4. Session metadata visibility:
- Option A (recommended): show name + last opened only.
- Option B: show name + timestamps + note preview.

## Phase 4 Signoff Conditions
- M1 through M6 complete.
- `cd web-ui && npm test` passes.
- Phase 4 acceptance suites pass.
- Restore flow demonstrates layout, transcript, and inspector continuity.
