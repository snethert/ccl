# Phase 5 Detailed Plan: Runtime Integration (CL)

## Document Control
- Status: In Progress
- Last Updated: February 8, 2026
- Parent Plan: `web-ide/implementation-plan.md`
- Doctrine Sources: `web-ide/ide-doctrine.md`, `web-ui/ui-doctrine.md`, `web-ide/phase-0/*.md`, `web-ide/phase-1/implementation-plan.md`, `web-ide/phase-2/implementation-plan.md`, `web-ide/phase-3/implementation-plan.md`, `web-ide/phase-4/implementation-plan.md`.

## Phase 5 Outcome
Deliver a live CL runtime integration where evaluations, restarts, inspector data, and background jobs flow through the same presentation and typed command system as the UI.

## Scope
### In Scope
- Bridge protocol for runtime to UI messaging and command dispatch.
- Output recording payloads emitted by the runtime with presentation metadata.
- Restart metadata and argument schemas mapped into debugger UI.
- Inspector payloads and place editing (setf) support with safe staging.
- Background jobs for compile, index, lint, and their progress updates.
- Runtime error and condition reporting with condition-report sections.

### Out of Scope
- Full image snapshotting and world persistence of the runtime.
- Beginner mode and customization surfaces.
- Performance budgets and accessibility program.
- Remote multi-user or collaborative sessions.

## Baseline
- Output recording, presentation taxonomy, and typed command model are stable in UI.
- World state and sessions are persisted with deterministic restore.
- UI instruments are doctrine aligned across DOM and canvas/WebGL backends.

## Progress Snapshot
- M1 `RT1`: Completed.
- M2 `RT2`: Completed.
- M3 `RT3`: Planned.
- M4 `RT4`: Planned.
- M5 `RT5`: Planned.
- M6 `RT6`: Planned.
- M7 `RT7`: Planned.

## Phase 5 Success Criteria
- Live evaluation produces structured recordings with presentation metadata.
- Runtime errors surface as condition-report sections with actionable links.
- Restart metadata is rich, safe, and consistently actionable.
- Inspector can request structured views and edit places with staged apply.
- Background jobs do not block UI and report progress reliably.

## Workstreams

## RT1: Bridge Protocol and Transport
### Goal
Define and implement a stable runtime bridge for events and command dispatch.

### Tasks
1. Define a versioned envelope for runtime messages with `jobId`, `streamId`, `seq`, `ts`, `kind`, and `payload`.
2. Define request and response shapes for typed command dispatch and errors.
3. Define event kinds for output recording entries, restarts, inspector data, and job updates.
4. Implement encode and decode utilities with validation and error reporting.

### Deliverables
- Protocol schema and examples in `doc/wasm/runtime-bridge.md`.
- Runtime bridge codec in `web-ui/bridge/runtime.mjs`.
- Tests for protocol validation and deterministic decoding.

### Exit Criteria
- UI can accept a deterministic event stream from a mock runtime.
- Protocol errors are surfaced without corrupting UI state.

## RT2: Runtime Output Recording
### Goal
Emit output recordings from the runtime that match the UI recording model.

### Tasks
1. Map runtime output channels to recording kinds and stream ids.
2. Emit presentation metadata for values, frames, bindings, places, definitions, and doc.
3. Attach provenance fields for job and evaluation context.
4. Ensure output recording anchors are stable and linkable.

### Deliverables
- Runtime encoder for recording entries and anchors.
- UI integration that ingests runtime recording entries.
- Tests that replay runtime output deterministically into transcript.

### Exit Criteria
- Transcript renders runtime output with stable presentations.

## RT3: Typed Command Dispatch and Results
### Goal
Route typed commands from UI to runtime and back with structured results.

### Tasks
1. Define command invocation payloads with typed args, defaults, and context.
2. Implement runtime command handlers for core verbs.
3. Define result payloads for values, errors, and presentation references.
4. Capture command history with provenance for re-run and audit.

### Deliverables
- Runtime command dispatcher and registry.
- UI bridge that dispatches to runtime and normalizes results.
- Tests for round trip commands and structured history.

### Exit Criteria
- Command palette and action bar can invoke runtime actions deterministically.

## RT4: Restarts and Debugger Integration
### Goal
Surface restarts with rich metadata and safe interaction in the debugger.

### Tasks
1. Map runtime restarts to the restart presentation schema with safety and args.
2. Provide stack frames and locals as presentations with source links.
3. Define restart preview metadata where possible.
4. Ensure restart selection records typed invocation history.

### Deliverables
- Runtime restart payload encoder.
- UI debugger integration for restart metadata and actions.
- Tests for restart listing and restart command execution.

### Exit Criteria
- Debugger restarts are actionable with metadata and history.

## RT5: Inspector Integration and Place Editing
### Goal
Expose structured inspector views and allow safe edits of places.

### Tasks
1. Define inspector query and response protocol with type specific views.
2. Represent places with metadata that supports safe edits and undo.
3. Implement staged edit apply and rollback in runtime.
4. Emit transcript events for state mutations triggered from inspector.

### Deliverables
- Runtime inspector endpoint and place edit handlers.
- UI inspector integration for structured views and edits.
- Tests for staged edits and audit trail entries.

### Exit Criteria
- Inspector edits are safe, reversible, and auditable.

## RT6: Background Jobs and Progress
### Goal
Run compilation, indexing, and linting without blocking the UI.

### Tasks
1. Define job lifecycle events: queued, started, progress, completed, failed.
2. Implement runtime job scheduler with cancellation.
3. Emit job events and map to UI status surfaces.
4. Ensure job output is linked to transcript entries.

### Deliverables
- Runtime job API and event stream.
- UI job tracking and progress presentation.
- Tests for job lifecycle events and cancellation.

### Exit Criteria
- Background jobs report progress and do not block UI interaction.

## RT7: Phase 5 Acceptance and Quality Gates
### Goal
Codify runtime integration stability with automated gates.

### Tasks
1. Add Phase 5 tests for bridge protocol validation, runtime output recording ingest, typed command round trip, and restart and inspector payload handling.
2. Add at least one integration test for evaluate -> transcript -> inspector -> edit -> re-evaluate.
3. Wire tests into `web-ui/package.json` `test:sandbox`.

### Deliverables
- `web-ui/tests/phase-5-runtime-bridge.test.mjs`
- `web-ui/tests/phase-5-runtime-output.test.mjs`
- `web-ui/tests/phase-5-runtime-integration.test.mjs`

### Exit Criteria
- Phase 5 acceptance suites pass.
- Existing `web-ui` suites remain green.

## Milestone Sequence
1. M1: RT1 complete (bridge protocol and transport).
2. M2: RT2 complete (runtime output recording).
3. M3: RT3 complete (typed command dispatch and results).
4. M4: RT4 complete (restarts and debugger integration).
5. M5: RT5 complete (inspector integration and places).
6. M6: RT6 complete (background jobs and progress).
7. M7: RT7 complete (acceptance gates and signoff).

## Implementation Strategy
1. Lock protocol schema and add codec tests first.
2. Integrate output recording before command dispatch so transcript stays authoritative.
3. Add restarts and inspector after command dispatch is stable.
4. Build job handling last to avoid mixing transport and scheduling complexity.

## Progress Notes
- M1 complete: protocol schema documented and runtime bridge codec added with tests.
- M2 complete: UI runtime output ingest added; JS microkernel emits `runtime.output` for stdout and stderr; `KERNEL_OP_RUNTIME_EVENT` added for structured runtime payloads; CL emits `runtime.output` envelopes via `kernel_request` with recording entries.

## Code Focus Areas
- `doc/wasm/runtime-bridge.md`
- `web-ui/bridge/runtime.mjs`
- `web-ui/src/command-effects.mjs`
- `web-ui/src/recordings.mjs`
- `web-ui/src/presentation-taxonomy.mjs`
- `web-ui/src/typed-commands.mjs`
- `web-ui/src/runtime-bridge.mjs`
- `lisp-kernel/*`
- `scripts/wasm/*`
- `doc/wasm/*`

## Risks and Mitigations
- Risk: protocol mismatch between runtime and UI causes silent failures.
Mitigation: strict schema validation and error surfaces in the transcript.
- Risk: restart metadata is incomplete or inconsistent across runtime paths.
Mitigation: provide a default restart adapter and validation rules.
- Risk: inspector edits mutate state without traceability.
Mitigation: record all edits as transcript entries with provenance.
- Risk: background jobs flood the UI with events.
Mitigation: throttle progress events and batch transcript updates.

## Decision Gates (Resolved)
1. Transport mechanism for runtime bridge: Option A, structured JSON messages over postMessage or websocket.
2. Restart argument encoding: Option A, fully typed argument schema with defaults and validators.
3. Inspector view encoding: Option A, structured JSON views with typed fields and actions.
4. Job scheduling model: Option A, runtime controlled queue with UI requests.

## Phase 5 Signoff Conditions
- M1 through M7 complete.
- `cd web-ui && npm test` passes.
- End to end evaluate -> inspect -> restart -> transcript flow verified.
