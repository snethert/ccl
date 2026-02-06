# Web UI Development Plan

Status: Draft

## Staged Plan (High Level)

### Phase 0: Test Harness First
Goals:
- Deterministic event log format for pointer, keyboard, focus, layout, and command events.
- UI tree snapshot serializer with stable output.
- Test runner that can execute in headless browser and node.

Exit criteria:
- A trivial UI tree can be rendered, serialized, and compared in tests.
- Event logs can be replayed deterministically with identical snapshots.

### Phase 1: Core Model and Command System
Goals:
- Task, window, command, focus, and selection state models.
- Central command dispatch with enablement reasons.
- Focus history and deterministic transitions.

Exit criteria:
- Command routing precedence is deterministic under test.
- Focus history replay produces identical results for a fixed event log.

### Phase 2: DOM Backend and Diff/Patch Rendering
Goals:
- Backend interface for render, `measureText`, `hitTest`, `invalidate`, `captureEvents` (DOM backends may use callback-based invalidation).
- DOM renderer with stable keys and incremental patching.
- Basic widgets (button, label, text input, list) with command wiring.
- DOM nodes carry stable IDs via data attributes for hit testing and instrumentation.

Exit criteria:
- DOM snapshots are stable across runs.
- Diff/patch passes all structural update tests.
- Backend interface checks pass in the browser harness.

### Phase 3: Layout and Focus Determinism
Goals:
- Split panes, tabs, docking layout model with persistence hooks.
- Explicit focus manager and reconciliation with DOM focus.

Exit criteria:
- Layout drift tests pass for recorded sequences.
- Focus transitions are reproducible under stress tests.

### Phase 4: Inspectability and Debugger UX
Goals:
- System state inspector window.
- Debugger window shell with restart list.

Exit criteria:
- Errors open debugger windows without breaking layout.
- Inspector shows full task/window/command/focus state.

### Phase 5: Canvas Backend
Goals:
- Canvas view with stable IDs, hit-testing, and text measurement.
- Draw list and dirty-node invalidation.

Exit criteria:
- Canvas hit-test fixtures pass deterministically.
- Canvas views participate in focus and command routing.

### Phase 6: WebGL Backend
Goals:
- Minimal WebGL renderer for a small scene subset.
- Shared hit-testing path consistent with Canvas.

Exit criteria:
- WebGL rendering and hit tests match Canvas behavior.

### Phase 7: Persistence and Migration
Goals:
- Layout and task serialization with schema versioning.
- Migration hooks and reversible upgrades where possible.

Exit criteria:
- Serialize/restore equivalence tests pass across versions.

### Phase 8: Performance and Scale
Goals:
- Virtualized list/tree/table widgets.
- Renderer batching and dirty-rect updates.

Exit criteria:
- 10k row lists remain interactive.
- Typical diagrams/timelines meet frame budget targets.

### Phase 9: Command Surface and Keybinding UX
Goals:
- Command palette with filterable command list.
- Keybinding viewer with scope-aware listings.
- Inspectable keybinding resolution trace.

Exit criteria:
- Palette lists commands deterministically and supports filtering.
- Keybinding viewer lists bindings across scopes.
- Key resolution trace is testable and deterministic.

## Phase 0 Detailed Plan (Test Harness First)

### Objectives
- Establish deterministic test execution across node and headless browser.
- Define event log, snapshot, and replay formats before any renderer exists.
- Make it possible to validate core invariants without a UI backend.

### Deliverables
- Event log schema for pointer, keyboard, command, focus, layout, and job events.
- Snapshot serializer for UI state, focus history, command enablement, and selection.
- Deterministic replay harness that replays event logs against a pure state model.
- Headless browser runner for DOM and canvas tests, gated behind the same log format.
- Golden test fixtures for core invariants and regression detection.

### Work Breakdown

1. Define the event log schema.
- Event envelope with monotonic sequence number, timestamp, type, target ID, and payload.
- Canonical types: `command`, `focus`, `pointer`, `keyboard`, `layout`, `job`, `snapshot`.
- Strict validation rules and schema versioning.

2. Define the snapshot format.
- Stable ordering for tasks, windows, widgets, and command registry entries.
- Explicit capture of focus target, focus history, selection, and enabled/disabled reasons.
- Serialization that avoids nondeterministic fields or runtime addresses.

3. Build the replay harness.
- Pure state transition runner that consumes event logs and produces snapshots.
- Deterministic error capture with restart metadata when applicable.
- Support for replaying partial logs to isolate regressions.

4. Implement the test runner.
- Node-based runner for state-only tests.
- Headless browser runner for DOM/Canvas tests using the same event log format.
- Golden snapshot comparison with diffs that highlight structural changes.

5. Create baseline fixtures.
- Small UI tree with known IDs and deterministic ordering.
- Known focus sequence and command enablement states.
- Layout mutation fixture with expected serialization.

6. Establish determinism rules.
- All timers and randomness must be seeded and controllable.
- Async events must be timestamped and ordered by the log, not wall time.
- Font metrics and text measurement must be mocked or fixed for snapshot tests.

### Phase 0 APIs to Define
- `ui:record-event`, `ui:replay-events`
- `ui:serialize-state`, `ui:serialize-focus`, `ui:serialize-commands`
- `ui:diff-snapshots`

### Future Pain Points to Anticipate Now
- Nondeterminism from timers, randomness, or asynchronous event ordering.
- Snapshot churn due to unstable IDs or ordering.
- Cross-platform font metric differences in DOM/canvas snapshots.
- Brittle golden tests without clear diff tooling.
- Mixing side effects into command execution without an event log boundary.

### Phase 0 Exit Criteria
- A minimal state graph can be serialized and compared in golden tests.
- Event logs replay to identical snapshots across multiple runs.
- Headless browser tests run and can validate DOM or canvas outputs deterministically.

### Phase 0 Progress
- Implemented event log schema and validator.
- Implemented snapshot serializer and diff helper.
- Implemented deterministic replay harness with validation.
- Added baseline fixtures and tests for focus, command enablement, layout, and selection.
- Added headless browser harness (Playwright-backed) for DOM and canvas checks.
- Added a local web-ui dev dependency for Playwright to enable headless runs.
- Headless harness skips on launch failure unless `WEB_UI_STRICT_BROWSER_TESTS=1` is set.

## Phase 1 Detailed Plan (Core Model and Command System)

### Objectives
- Define the authoritative UI state graph.
- Implement deterministic command routing and enablement.
- Implement explicit focus state and focus history.
- Build first-class selection and activation semantics.
- Establish testable invariants without any renderer dependency.

### Deliverables
- UI state data model.
- Command registry and dispatcher.
- Focus manager with reason codes.
- Selection model with stable IDs.
- Deterministic event log replay harness for commands and focus.
- Unit and integration tests for routing and focus history.

### Work Breakdown

1. Define the core state graph.
- Structures for workspace, task, window, and widget nodes.
- Stable IDs for tasks, windows, widgets, and presentations.
- Serialization-friendly shapes without DOM references.

2. Define the command system.
- Command object: ID, doc, enablement predicate, exec function.
- Command registry with namespace rules and versioning strategy.
- Command context object with accessors to current task/window/selection.

3. Implement deterministic command routing.
- Explicit routing precedence: global, task, context, widget.
- Conflict handling and deterministic tie-breaking rules.
- Command enablement with structured reasons.

4. Implement focus state and history.
- Single authoritative focus target at all times.
- Reason codes for focus changes.
- History ring buffer with deterministic replay.

5. Implement selection model.
- Selection as a first-class object with stable IDs.
- Selection updates only through commands.
- Selection observers for command enablement.

6. Build event log and replay.
- Event log schema for command invocations and focus changes.
- Replay driver that mutates state without any rendering.
- Snapshot serializer for state and focus history.

7. Tests.
- Command routing precedence tests.
- Enablement reason tests.
- Focus history determinism tests.
- Selection update tests.

### Phase 1 APIs to Define
- `ui:define-command` or `ui:defcommand`
- `ui:command-enabled-p`
- `ui:execute-command`
- `ui:current-task`, `ui:current-window`, `ui:selection`
- `ui:focus-target`, `ui:focus-history`

### Future Pain Points to Anticipate Now
- Command context drift: commands may read stale selection or focus if state updates are not ordered.
- Event ordering: asynchronous input can reorder command effects unless log order is authoritative.
- ID stability: stable keys are needed before rendering is implemented.
- Global mutable state: avoid hidden globals that cannot be serialized.
- Enablement reason explosion: use structured reasons to avoid string-only semantics.
- Hard-to-replay commands: keep side effects explicit and isolate them from the core state.
- Testing without a renderer: ensure state transitions do not depend on DOM signals.
- Performance cost of history: cap history size and provide pruning rules.

### Phase 1 Exit Criteria
- All command routes are deterministic under replay.
- Focus history matches across multiple replays with identical inputs.
- Command enablement reasons are inspectable and stable.
- State can be serialized without renderer or DOM references.

### Phase 1 Progress
- Implemented initial state graph utilities and focus helpers.
- Added task navigation commands and a task list window for switching/archiving tasks.

### Phase 2 Progress
- Implemented DOM backend primitives: `measureText`, `hitTest`, `captureEvents`, `invalidate` with browser harness checks.
- Implemented DOM renderer diff/patch with keyed updates and structural regression tests.
- Implemented baseline widgets (button, label, text input, list) with command wiring and snapshots.
- Added list widget smoke test and wired into WASM smoke runner.

### Phase 3 Progress
- Added deterministic layout model with split/tabs/dock nodes and mutation helpers.
- Added layout drift tests and updated layout snapshot fixtures.
- Added focus reconciliation helper and browser harness check.
- Added layout/focus smoke test and wired into WASM smoke runner.
- Added layout command registrations and command tests for split/tabs/dock/active-tab.
- Added focus reconciliation deferral during composition events.

### Phase 4 Progress
- Added event log ring buffer and deterministic recording in replay harness.
- Added UI turn event logging and replay handlers for deterministic turn traces.
- Added inspector and debugger window shells with coalesced error handling.
- Added reason object tracking for focus and disablement.
- Added explicit UI turn model with signal queue, yield handling, and inspector visibility.
- Added inspector/debugger tests and smoke tests wired into WASM smoke runner.
- Added presentation translator registry and inspector presentation listing.
- Implemented command registry, key binding, and deterministic routing.
- Added unit tests for routing precedence and focus history.
- Added context helpers and a module index for consistent imports.
- Expanded state model to cover workspace, widgets, presentations, and ID counters.
- Added state graph unit tests for task/window/widget wiring.
- Added capability gating state with safe mode commands and inspector coverage.

### Phase 5 Progress
- Added canvas scene normalization, draw traversal, and hit-testing helpers.
- Added canvas backend with text measurement cache, animation-frame invalidation, and dirty-rect redraws with draw culling.
- Added canvas-view widget with command dispatch via hit testing.
- Updated DOM backend to handle canvas render hooks.
- Added unit tests for canvas scene building, hit testing, and measure cache behavior.
- Extended widget snapshots and command wiring tests for canvas views.
- Added accessibility proxy defaults for canvas/webgl views (non-accessible by default, explicit labels/roles when enabled).
- Extended browser harness to validate canvas backend hit testing and canvas-view commands.
- Added web-ui canvas smoke test and wired it into the WASM smoke runner.

### Phase 6 Progress
- Added WebGL backend with minimal rect renderer, dirty-rect scissoring, and hit-testing via shared scene.
- Added WebGL draw-list builder with deterministic color parsing.
- Added webgl-view widget with command dispatch via hit testing.
- Extended browser harness to validate WebGL rendering, hit testing, and widget command dispatch.
- Added WebGL unit tests and smoke test wired into the WASM smoke runner.

### Phase 7 Progress
- Added persistence module with versioned snapshot envelopes and migration support.
- Implemented IndexedDB and in-memory persistence stores.
- Added persistence manager with debounce, flush, and restore flows.
- Added serialization sanitization to strip non-serializable values.
- Added best-effort focus/selection persistence with restore validation.
- Documented non-persistence of presentations and runtime command handlers.
- Added persistence unit tests, browser harness check, and WASM smoke test.

### Phase 8 Progress
- Added renderer batching via scheduled root flushes.
- Added virtualized list/tree/table widgets with stable data attributes and spacer layouts.
- Extended canvas/webgl widgets to accept dirty-rect hints for fine-grained redraws.
- Added unit tests for batching, virtualization, and dirty-rect forwarding.
- Extended browser harness coverage for virtualized widgets.
- Added virtual widget WASM smoke test and wired it into the smoke runner.

### Phase 9 Progress
- Added command palette and keybinding viewer window builders.
- Added keybinding resolution trace helper.
- Added unit tests and a WASM smoke test for command palette and keybinding viewer.
- Added palette selection state helpers and selected-item execution metadata.
- Added command palette command registrations for filter/navigation/execute.
- Added default palette keybindings (ArrowUp/ArrowDown/Enter) for task scope.
- Added open/close commands for command palette and keybinding viewer windows.
- Added keybinding trace panel and context/widget scope coverage in command UI tests.
- Added default open/dismiss keybindings for command palette and keybinding viewer.
- Added command routing tests for configurable context/widget precedence.
- Added deeper keybinding trace coverage with skipped-after-match entries.
