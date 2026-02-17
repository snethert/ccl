# Web UI Development Plan

Status: Draft

## Design Review Integration Register (2026-02-17)

This register maps all items from `web-ui/DESIGN-REVIEW-2026-02-16.md` into plan-owned artifacts and phases.

| Review ID | Plan integration target | Tracking artifacts |
|---|---|---|
| `C-1` | Front-end deployment policy and startup gating scoped to full-runtime only | `web-ui/FRONT-END-DEV-PLAN.md`, `web-ui/spec/security-and-capability-model-v1.md` |
| `C-2` | Runtime bridge wire format expansion | `web-ui/spec/ui-wire-format-tree-v1.md`, `web-ui/spec/protocol-version-negotiation-v1.md` |
| `C-3` | Core command model completion | `web-ui/spec/command-undo-redo-contract-v1.md` |
| `C-4` | Governance precedence cleanup | `web-ui/spec/glossary-v1.md`, `web-ui/spec/normative-language-and-conformance-v1.md` |
| `S-1` | Cross-backend text-editing parity | `web-ui/spec/text-editing-contract-v1.md` |
| `S-2` | Clipboard subsystem contract with required multi-item history | `web-ui/spec/clipboard-interaction-contract-v1.md` |
| `S-3` | Drag/drop interaction protocol | `web-ui/spec/drag-and-drop-interaction-contract-v1.md` |
| `S-4` | Persistence retention/compaction planning | `web-ui/spec/persistence-gc-and-compaction-policy-v1.md` |
| `S-5` | Offline/service-worker loading strategy | `web-ui/spec/offline-and-service-worker-contract-v1.md` |
| `S-6` | Incremental tree wire updates for scale lanes | `web-ui/spec/ui-wire-format-tree-delta-v1.md`, `web-ui/spec/performance-slo-and-budgets-v1.md` |
| `M-1` | Non-DOM accessibility plan formalization | `web-ui/spec/non-dom-accessibility-proxy-contract-v1.md` |
| `M-2` | Multi-runner debugger planning lane | `web-ui/spec/debugger-stepper-session-contract-v1.md` |
| `M-3` | Theme customization planning lane | `web-ui/spec/theme-override-contract-v1.md` |
| `M-4` | Internationalization planning lane | `web-ui/spec/i18n-l10n-contract-v1.md` |
| `M-5` | Event log retention/rotation planning | `web-ui/spec/event-log-ordering-and-clock-rules-v1.md` |
| `M-6` | Lease scope/clock assumptions planning | `web-ui/spec/persistence-lease-protocol-v1.md` |
| `M-7` | Controlled-reader planning dependency | `web-ui/spec/controlled-reader-contract-v1.md` |
| `G-1` | Spec index profile registration | `web-ui/spec/spec-index-v1.md` |
| `G-2` | Draft-stage gate evaluation policy | `web-ui/spec/spec-ratification-policy-v1.md`, `web-ui/PRODUCTION-SPEC-GAP-REGISTER.md` |
| `G-3` | Glossary term governance updates | `web-ui/spec/glossary-v1.md` |
| `G-4` | Gate timeout planning constraints | `web-ui/spec/conformance-gate-profiles-v1.md` |
| `G-5` | Governance bootstrap ordering | `web-ui/spec/spec-index-v1.md` |
| `G-6` | Cross-spec error code governance | `web-ui/spec/error-code-registry-v1.md` |

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
- Clipboard manager with multi-item history and deterministic history paste selection.

Exit criteria:
- Palette lists commands deterministically and supports filtering.
- Keybinding viewer lists bindings across scopes.
- Key resolution trace is testable and deterministic.
- Clipboard history capture/paste commands are deterministic across replay and backend lanes.

### Phase 10: Stepper and Breakpoint UX
Goals:
- Expression-precise breakpoint placement in source-facing surfaces.
- Entry/exit breakpoints with explicit break-on-return behavior and return-value presentation.
- Dual-lane stepping controls (source lane and low-level lane) with explicit handoff.
- Slide-point controls for ambiguous source-correlated stop locations.
- Debugger-integrated stepper panel with frame stepping and in-step REPL shell.

Exit criteria:
- Users can place entry/exit breakpoints from editor surfaces and inspect policy metadata.
- Closing-paren break-on-return behavior is represented in UI state and command flows.
- Stepper interactions replay deterministically from event logs.
- Debugger and transcript remain coherent during stepping sessions.

Decision boundary (deferred):
- Source-map/debug-metadata representation is intentionally tabled for the next design step.
- Phase 10 locks UI/state/command behavior first, then binds to finalized runtime metadata.

## Kernel/Compiler/GC Dependency Register (Authoritative)

This section is the canonical tracking surface for non-UI implementation work required by `web-ui` and `web-ide`.

Tracking policy:
- Future kernel/compiler/GC dependencies discovered in any planning or status doc must be added here.
- Phase planning may remain distributed, but dependency status for non-UI work is tracked here.
- Replacement of legacy runtime pathways is allowed when required for protocol determinism and debugger correctness.

### Source scan basis (2026-02-16)
- `web-ui/FRONT-END-DEV-PLAN.md`
- `web-ide/ide-doctrine.md`
- `web-ide/phase-5/implementation-plan.md`
- `web-ide/phase-5/m3-typed-command-dispatch-plan.md`
- `web-ide/phase-5/m4-restarts-debugger-plan.md`
- `web-ide/phase-5/m5-inspector-place-edit-plan.md`
- `web-ide/phase-9/implementation-plan.md`
- `web-ide/phase-9/debugger-stepper-spec.md`
- `doc/wasm/*.md` documents referenced by the above plans (scanned for existing required modifications; not edited here)

### Dependency register

| ID | Area | Required modifications | Status | Source provenance |
|---|---|---|---|---|
| KCG-01 | Kernel transport | Maintain/extend runtime command queue opcode path (`KERNEL_OP_RUNTIME_COMMAND_POLL`) and host wrappers for deterministic poll/dequeue semantics and backpressure handling. | Complete baseline; ongoing extension required | `web-ide/phase-5/m3-typed-command-dispatch-plan.md`, `web-ide/phase-5/implementation-plan.md` |
| KCG-02 | Kernel transport | Maintain/extend runtime event transport (`KERNEL_OP_RUNTIME_EVENT`) so debugger/inspector/stepper payloads remain typed and versioned end-to-end. | Complete baseline; stepper extensions pending | `web-ide/phase-5/implementation-plan.md`, `web-ide/phase-9/debugger-stepper-spec.md` |
| KCG-03 | Compiler + kernel + GC | Preserve const-pool install/materialization path, including GC root retention for pooled objects, symbol interning stability, and function identity resolution. | Complete baseline; regression-sensitive | `web-ui/FRONT-END-DEV-PLAN.md` |
| KCG-04 | Compiler + GC safety | Keep `external-call` lowering and spill/restore GC-safety rules in the WASM backend explicit and tested for UI/runtime call paths. | Complete baseline; regression-sensitive | `web-ui/FRONT-END-DEV-PLAN.md` |
| KCG-05 | Runtime debugger | Replace current restart-only/empty-frame debugger snapshot behavior with full frame/scope/binding payloads per Phase 9 schema. | Planned (required for Phase 10) | `web-ide/phase-9/debugger-stepper-spec.md`, `web-ide/phase-9/implementation-plan.md` |
| KCG-06 | Runtime stepper | Implement runtime debugger step commands/events (`runtime.debugger.step.*`, breakpoint lifecycle commands, stop/resume/session updates). | Planned (required for Phase 10) | `web-ide/phase-9/debugger-stepper-spec.md` |
| KCG-07 | Runtime frame model | Implement frame operations against runtime-owned simulated stack model; do not depend on architecture-fragile host backtrace/apply-in-frame pathways. | Planned (required for Phase 10) | `web-ide/phase-9/debugger-stepper-spec.md` |
| KCG-08 | Compiler metadata | Define compiler emission contract for expression anchor metadata (entry/exit, return sites, slide-point candidates) behind the deferred `LocationProvider` abstraction. | Deferred decision gate (DM1) | `web-ide/ide-doctrine.md`, `web-ide/phase-9/implementation-plan.md`, `web-ide/phase-9/debugger-stepper-spec.md` |
| KCG-09 | GC + identity | Provide GC-safe stable identity tokens/handles for debugger/inspector/watch references so UI never depends on raw movable addresses. | Planned; cross-image behavior deferred | `web-ide/ide-doctrine.md`, `web-ide/phase-9/debugger-stepper-spec.md` |
| KCG-10 | Runtime safety hooks | Add/maintain bounded evaluation and policy hooks for conditional breakpoints and probe actions (error policy, safety classification, auditability). | Planned (required for Phase 10) | `web-ide/phase-9/debugger-stepper-spec.md` |
| KCG-11 | Runtime persistence boundary | Enforce handle revalidation rules for persisted UI state touching runtime objects (watches/inspector/debugger pointers) to avoid stale-handle corruption after GC/runtime reload. | Planned | `web-ide/ide-doctrine.md`, `web-ide/implementation-plan.md`, `web-ui/FRONT-END-DEV-PLAN.md` |
| KCG-12 | Kernel UI ABI | Keep/complete kernel ABI and host helper support for Lisp-authoritative UI opcodes (`UI_POLL`, `UI_RENDER`, `UI_MEASURE_TEXT`) and nonblocking yield semantics. | Partial (WASM bridge path complete; Lisp-authoritative path still staged) | `web-ui/FRONT-END-DEV-PLAN.md` |
| KCG-13 | Kernel persistence lane | Keep/complete kernel_request-backed persistence transport for Lisp UI snapshots, including deterministic restore behavior for inspector/debugger window state. | Partial | `web-ui/FRONT-END-DEV-PLAN.md` |
| KCG-14 | Editor anchor resolver | Add compiler/runtime hook to resolve cursor/selection to canonical expression anchor (`sourceRef`, `formId`, `anchorKind=entry|exit`) and return deterministic failures for unmappable regions. | Planned (required for seamless editor breakpoint UX) | `web-ide/phase-9/implementation-plan.md`, `web-ide/phase-9/debugger-stepper-spec.md` |
| KCG-15 | Stop-to-editor mapping | Add runtime event fields/hook path for stop-location projection back into editor (reveal location, highlight span, slide-group candidate set). | Planned | `web-ide/phase-9/debugger-stepper-spec.md`, `web-ide/ide-doctrine.md` |
| KCG-16 | Breakpoint resolution ACK | Add runtime breakpoint upsert response contract that returns normalized/resolved anchor, validity, and degradation reason when source placement is ambiguous or stale. | Planned | `web-ide/phase-9/debugger-stepper-spec.md` |
| KCG-17 | Source revision handshake | Add source revision/hash handshake in breakpoint/stop payloads so editor can detect stale mappings after edits and trigger re-resolution instead of mis-highlighting. | Planned | `web-ide/ide-doctrine.md`, `web-ide/phase-9/debugger-stepper-spec.md` |
| KCG-18 | Edit invalidation + metadata refresh | Add runtime/compiler hooks to invalidate and refresh debug-location metadata after defun/file recompiles without requiring full runtime reset. | Planned; depends on DM1 metadata work | `web-ide/phase-9/implementation-plan.md`, `web-ide/phase-9/debugger-stepper-spec.md` |
| KCG-19 | Editor-initiated frame eval | Keep/extend `runtime.debugger.eval.in-frame` and binding-set pathways so editor actions (eval selection, set local) run against selected frame with audit metadata. | Planned (partial baseline exists) | `web-ide/phase-9/debugger-stepper-spec.md`, `web-ide/phase-5/implementation-plan.md` |
| KCG-20 | Jump-to-source provenance | Add stable definition/source provenance hooks in runtime payloads so debugger frame rows and inspector values can always resolve to editor targets (or explicit “unavailable”). | Planned | `web-ide/ide-doctrine.md`, `web-ide/phase-5/m4-restarts-debugger-plan.md`, `web-ide/phase-9/debugger-stepper-spec.md` |

### Editor hook runtime command/event mini-contract (normative, Phase 10)

This contract makes `KCG-14..KCG-20` implementable without ambiguity.

Protocol baseline:
- Use runtime bridge envelope v1 (`requestId`, `invocationId`, `commandId`, `args`, `context`, terminal `command.result|command.error`).
- All mapping-bearing payloads include `sourceRef`, `sourceRevision`, and `mappingEpoch`.

Required commands:

| Command ID | Purpose | Required args | Terminal success payload | Required error codes |
|---|---|---|---|---|
| `runtime.editor.source.handshake` | Register/confirm editor buffer revision for mapping correctness. | `sourceRef`, `sourceRevision`, `contentHash` | `accepted`, `latestRevision`, `mappingEpoch` | `unknown-source`, `invalid-args` |
| `runtime.editor.anchor.resolve` | Resolve cursor/selection to canonical expression anchor. | `sourceRef`, `sourceRevision`, `selection:{start,end}`, `preferredAnchorKind:entry|exit|either` | `resolved:true`, `anchor:{formId,anchorKind,line,column,charStart,charEnd}`, `mappingEpoch` | `stale-source-revision`, `mapping-unavailable`, `ambiguous-anchor`, `no-anchor-at-selection` |
| `runtime.debugger.breakpoint.upsert` | Upsert breakpoint using editor-provided anchor intent. | `sourceRef`, `sourceRevision`, `requestedAnchor`, `policy`, `enabled` | `breakpointId`, `resolvedAnchor`, `resolution:{status,reason}`, `mappingEpoch` | `stale-source-revision`, `invalid-breakpoint`, `mapping-unavailable` |
| `runtime.debugger.breakpoint.delete` | Remove breakpoint by id. | `breakpointId` | `deleted:true`, `breakpointId` | `invalid-breakpoint` |
| `runtime.debugger.eval.in-frame` | Evaluate editor form/selection in selected frame context. | `frameId`, `sourceRef`, `sourceRevision`, `form` | `valueRefs`, `effects`, `auditId` | `invalid-frame`, `unsupported-operation`, `stale-source-revision` |
| `runtime.debugger.binding.set` | Set arg/local value from editor action in selected frame. | `frameId`, `bindingId`, `newValueForm` | `updated:true`, `bindingId`, `valueRef`, `auditId` | `invalid-frame`, `invalid-binding`, `unsupported-operation` |

Required events:

| Event kind | Required fields | Notes |
|---|---|---|
| `debugger.stop` | `stopId`, `frameId`, `reason`, `location:{sourceRef,sourceRevision,mappingEpoch,formId,anchorKind,line,column,charStart,charEnd}`, `slideGroup:{id,candidates[]|null}`, `returnValues` | Drives reveal/highlight and slide-point navigation (`KCG-15`). |
| `debugger.breakpoint.updated` | `breakpointId`, `sourceRef`, `sourceRevision`, `mappingEpoch`, `requestedAnchor`, `resolvedAnchor`, `resolution:{status,reason}` | Carries normalization/degradation ACK (`KCG-16`). |
| `debugger.breakpoint.deleted` | `breakpointId` | Deterministic breakpoint lifecycle event. |
| `debugger.mapping.invalidated` | `sourceRef`, `invalidatedRevision`, `reason`, `mappingEpoch` | Emitted after edits/recompile invalidate prior mappings (`KCG-17`, `KCG-18`). |
| `debugger.mapping.refreshed` | `sourceRef`, `sourceRevision`, `mappingEpoch`, `coverageSummary` | Signals editor can clear stale mapping warnings. |
| `debugger.frame.selected` | `frameId`, `sourceProvenance:{sourceRef|nil,definitionRef|nil,resolvable:boolean}` | Supports jump-to-source provenance (`KCG-20`). |
| `debugger.eval.result` | `frameId`, `auditId`, `valueRefs`, `sourceRef`, `sourceRevision` | Audit-linked editor eval feedback (`KCG-19`). |

Determinism and safety rules:
- Anchor resolution must be deterministic for a fixed `(sourceRef, sourceRevision, selection, preferredAnchorKind, mappingEpoch)`.
- Ambiguous anchor selection must use a stable tie-break rule and return `resolution.reason`.
- `sourceRevision` mismatch must never silently remap; runtime returns `stale-source-revision` or emits `debugger.mapping.invalidated`.
- Mapping epoch is monotonic per `sourceRef`; all stop and breakpoint events carry the epoch used for resolution.
- All editor-initiated eval/mutation commands emit auditable terminal payloads with `auditId`.

Phase 10 test gate additions:
- `editor-anchor-resolve` round-trip determinism fixture.
- stale revision handshake fixture (`source.handshake` + stale command rejection).
- breakpoint upsert normalization fixture (entry/exit + degradation reason).
- stop-to-editor projection fixture (reveal/highlight/slide candidates).
- edit-invalidate-refresh fixture (invalidate then remap without runtime reset).

### Immediate tracking rules for future work
- Any PR that changes `lisp-kernel/*`, `compiler/*`, `level-1/*`, `xdump/*`, or WASM microkernel/runtime bridge ABI must update this register.
- For each new dependency, add: scope, required modifications, status, and source provenance.
- When a dependency is completed, keep the row and mark it complete (do not delete history).

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
- Added IME/dead-key/mobile keyboard coverage to the headless browser harness (composition cancel/multi-step, selection persistence).
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
- Added DOM escape command logging with inspector visibility (capability-gated).
- Added capability mediation request queue, policy evaluation, mediation panel UI, and tests.

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

### Phase 10 Planned Track (Stepper and Breakpoint UX)
- Authoritative spec: `web-ide/phase-9/debugger-stepper-spec.md`.
- Add typed command IDs for stepping and breakpoint operations (`step.into`, `step.over`, `step.out`, `continue`, breakpoint policy updates).
- Add state model support for breakpoint anchors (`entry` and `exit`), policy, hit counts, and enablement.
- Add source-surface interactions for opening-paren (`entry`) and closing-paren (`exit`) placement.
- Add debugger stepper shell with frame-local stepping controls and in-step REPL panel.
- Add slide-point navigation controls and deterministic selection behavior.
- Extend runtime bridge adapters for stepper snapshots and breakpoint updates.
- Add event-log/replay fixtures covering full step session flows.
- Add unit/integration suites for editor->debugger->transcript step/breakpoint round trips.
- Permit replacement of legacy debugger bridge/state paths when required for protocol determinism and parity.
- Keep source-map/debug-metadata mechanism deferred; use fixture-backed mappings until next-step design is finalized.
