# Implementation Plan: Browser-First CL IDE

## Scope
This plan turns `web-ide/ide-doctrine.md` and `web-ui/ui-doctrine.md` into an implementable, testable system.
Interaction semantics come from the IDE Doctrine. Visual form and motion come from the UI Doctrine.

## Assumptions (Locked)
1. Hybrid rendering is the default.
2. Text-heavy surfaces use the DOM backend for IME, selection, clipboard, and accessibility.
3. Canvas/WebGL views are used for high-density visualizations and custom widgets.
4. All backends consume shared theme tokens and spacing metrics so the UI reads as one instrument.
5. DOM usage does not imply OS-native styling; the UI Doctrine still governs visual form.

## Constraints
- OS-neutral visual language.
- Dark mode is first-class.
- No regression in input fidelity (IME, selection, clipboard, a11y).
- Output recordings are deterministic and replayable.

## Phase 0: Decision Spikes and Spec Freeze
Outcome: The architecture is locked before significant implementation.
Status: Complete (February 8, 2026).
All Phase 0 open questions are resolved to explicit defaults in the spec set.

1. Editor runtime decision spike.
- Evaluate CodeMirror vs Monaco vs custom editor.
- Success criteria: IME correctness, multi-cursor, performance on large buffers, a11y support.
- Deliverable: Decision memo with tradeoffs and final choice.

2. Output recording schema spec.
- Define recording entries, stable anchors, provenance fields, and operations.
- Deliverable: JSON schema and reference examples.

3. Presentation taxonomy spec.
- Define types: command, frame, binding, place, definition, doc, condition-report section, value.
- Deliverable: Type list, required metadata, and default actions.

4. Typed command model spec.
- Define argument schema, defaulting rules, DWIM resolution, and serialization.
- Deliverable: Command object schema and history format.

Exit criteria:
- All four documents approved.
- Schema versions allocated.

## Phase 1: Core State and Persistence
Outcome: The runtime state model supports the doctrine.
Status: Complete (February 8, 2026).
Detailed execution plan: `web-ide/phase-1/implementation-plan.md`.

1. Output recording subsystem.
- Add `recordings` and `transcript` to state.
- Add stable anchor allocation and provenance tracking.
- Add recording operations: append, fold, replay, copy-as-form.

2. Presentation system upgrade.
- Extend `presentation` records with taxonomy and metadata.
- Add translation hooks for presentation-driven commands.

3. Typed command system.
- Implement command objects with argument schemas.
- Structured, replayable command history.
- DWIM default resolution in context.

4. Persistence and migrations.
- Persist recordings, command history, selections, and watches.
- Add migrations for legacy snapshots.

Exit criteria:
- Round-trip serialization tests pass.
- Deterministic recording replay verified.

## Phase 2: Instrument Surfaces
Outcome: Core instruments match the doctrine in behavior.
Status: Complete (February 8, 2026).
Detailed execution plan: `web-ide/phase-2/implementation-plan.md`.

1. REPL with output recording.
- Transcript is a first-class artifact.
- Clickable presentations with stable anchors.
- Copy and replay act on recordings, not DOM nodes.

2. Inspector as a pivot.
- Type-aware views.
- Pinned watches.
- Safe edit-in-place with staged apply/undo.

3. Debugger panel.
- Restart metadata (label, description, safety, args).
- Stack frames navigable.
- Locals inspectable as presentations.

4. Problems panel.
- Errors and warnings as a navigable queue.
- Entries link to source and presentations.

Exit criteria:
- Full REPL -> Inspector -> Debugger loop demonstrated.
- Transcript and restarts are stable across re-render.

## Phase 3: UI Doctrine Implementation
Outcome: Visual system matches `web-ui/ui-doctrine.md`.
Status: Complete (February 8, 2026).
Detailed execution plan: `web-ide/phase-3/implementation-plan.md`.

1. Theme tokens.
- Color, typography, spacing, elevation, motion tokens.
- Shared across DOM and canvas/WebGL.

2. Typography-first hierarchy.
- Define font stacks and scale.
- Enforce text-first UI semantics.

3. Motion semantics.
- Standard transitions and suppression for accessibility.

4. Dark mode.
- Separate palettes, not inverted values.

Exit criteria:
- At least two instruments fully match doctrine in light and dark modes.
- Motion can be suppressed globally without loss of meaning.

## Phase 4: World State and Sessions
Outcome: Persistent workspace state and psychological safety.
Status: Complete (February 8, 2026).
Detailed execution plan: `web-ide/phase-4/implementation-plan.md`.

1. Workspace snapshots.
- Persist UI layout, transcript, history, watches, and inspector pins.

2. Session restore and revalidation.
- Restore stale presentations as readable.
- Rebind when possible.

Exit criteria:
- Cold start restores a coherent workspace.
- Stale references are safe and explicit.

## Phase 5: Runtime Integration (CL)
Outcome: End-to-end CL integration with presentations and restarts.
Status: In Progress, M4 complete and M5 next (February 8, 2026).
Detailed execution plan: `web-ide/phase-5/implementation-plan.md`.
M3 detail plan: `web-ide/phase-5/m3-typed-command-dispatch-plan.md`.
M4 detail plan: `web-ide/phase-5/m4-restarts-debugger-plan.md`.

1. Bridge protocol.
- Output recording payloads with presentation metadata.
- Command dispatch from UI to runtime.

2. Restart integration.
- Restart metadata and argument schemas.
- Suggested restarts with transparent reasoning.

3. Inspector integration.
- Type-aware inspectors and place editing.

4. Background jobs.
- Compilation, indexing, linting without UI stalls.

Exit criteria:
- Live evaluation produces structured recordings and presentations.
- Restarts are actionable with metadata.

## Phase 6: Customization and Beginner Mode
Outcome: Configurability without fragmentation.

1. Theming controls.
- Token overrides and presets.

2. Keybindings.
- Per-pane keymaps and conflict resolution.

3. Beginner mode.
- Same command system, reduced surface, inline explanations.

Exit criteria:
- Beginner mode toggles without loss of state.
- Keymap export/import works.

## Phase 7: Quality Gates
Outcome: Reliability at scale.

1. Performance budgets.
- Render time targets and transcript size limits.

2. Accessibility.
- Screen reader semantics for presentations.
- Full keyboard coverage.

3. Testing.
- Unit tests for recordings and command replay.
- Integration tests for REPL/Inspector/Debugger workflows.

Exit criteria:
- Performance benchmarks hit targets.
- A11y checklist passes.

## Risks and Mitigations
- Canvas-only editor risk: mitigated by DOM backend for text surfaces.
- Schema churn: freeze in Phase 0, enforce migration discipline.
- Theme drift: enforce token-only styling across renderers.

## Immediate Next Step
Execute M5 `RT5` from `web-ide/phase-5/implementation-plan.md`: land inspector runtime payloads and staged place-edit apply/undo integration.
