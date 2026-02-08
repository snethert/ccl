# Phase 1 Detailed Plan: Core State and Persistence

## Document Control
- Status: In Progress
- Last Updated: February 8, 2026
- Parent Plan: `web-ide/implementation-plan.md`
- Doctrine Sources:
  - `web-ide/ide-doctrine.md`
  - `web-ui/ui-doctrine.md`
  - `web-ide/phase-0/*.md`

## Phase 1 Outcome
Deliver a doctrine-aligned runtime core where output recordings, typed commands, presentations, selection actions, and persisted workspace state behave deterministically and survive restore/migration.

## Scope
### In Scope
- Output recording subsystem hardening and doctrine-level invariants.
- Presentation taxonomy enforcement in state and transcript flows.
- Typed command execution, DWIM defaults, structured history, and replay hooks.
- Persistence schema/migrations for Phase 1 state.
- Acceptance and regression test wiring.

### Out of Scope
- Full instrument UX polish (Phase 2+).
- Runtime CL protocol completion (Phase 5).
- Beginner mode and keybinding productization (Phase 6).
- Visual redesign work beyond existing doctrine compliance scaffolding (Phase 3).

## Baseline (Already Implemented)
- `recordings.mjs`, `typed-commands.mjs`, `presentation-taxonomy.mjs`, `selection-actions.mjs`, `world-state.mjs`, `conditions.mjs`.
- Command effect dispatch and bridge wiring (`command-effects.mjs`, `bridge/command-effects.mjs`).
- Snapshot sanitize/restore and migrations through schema `3`.
- Phase 0 spec/runtime tests and broad `web-ui` test harness are green.

## Progress Snapshot
- M1 `WS1`: Complete (recording invariants, input-kind normalization, anchor validation, deterministic recording bounds).
- M2 `WS2`: Complete (presentation metadata degradation policy at ingress and transcript-derived typing tests).
- M3 `WS3`: In Progress (typed command execution integrated in registry; widget dispatch now appends structured invocations to command history for typed commands).
- M4 `WS4`: In Progress (schema bumped to `3`, migration `2 -> 3`, snapshot truncation budgets and markers implemented).
- M6 `WS6`: In Progress (Phase 1 runtime/persistence/integration acceptance tests added and wired into `test:sandbox`).

## Workstreams

## WS1: Output Recording Hardening
### Goal
Make recordings a strict, deterministic system of record with stable anchors and validated provenance.

### Tasks
1. Enforce strict recording invariants:
- `appendEntry` requires existing `recordingId`.
- recording `entryIds`, `seqStart`, `seqEnd` are updated deterministically.
- duplicate and out-of-order sequence behavior is explicit.
2. Normalize input kinds to Phase 0 decisions:
- support `form`, `file`, `command`.
- preserve compatibility with existing entries.
3. Strengthen anchor behavior:
- canonicalize `range/path`.
- reject anchor references to unknown entries.
4. Add transcript budget policy hooks for persistence:
- retain latest entries by count and byte budget markers.

### Deliverables
- Updated `web-ui/src/recordings.mjs`.
- Integration updates in `web-ui/src/state.mjs`.
- Extended recording tests and replay determinism tests.

### Exit Criteria
- All recording operations are deterministic across re-render and restore.
- Replay/copy operations are recording-targeted and DOM-independent.

## WS2: Presentation Taxonomy Enforcement
### Goal
Ensure every presentation-backed interaction is type-valid, metadata-complete, and action-resolvable.

### Tasks
1. Enforce required metadata on `addPresentation` and transcript-derived presentations.
2. Define fallback policy for missing metadata:
- degrade to `value` with explicit reason metadata.
3. Tighten transcript item typing:
- consistent mapping from entry kind, presentation id, and recording context.
4. Expand selection action computation tests for mixed-type selections and priority ordering from Phase 0 decisions.

### Deliverables
- Updates in `web-ui/src/state.mjs`, `web-ui/src/presentation-taxonomy.mjs`, `web-ui/src/selection-actions.mjs`.
- New/updated tests for metadata validation and selection action ordering.

### Exit Criteria
- No action bar command is emitted without a valid mapped action type.
- Presentation metadata is validated at ingress points.

## WS3: Typed Command Runtime Integration
### Goal
Make typed commands the default command execution path for replayability and DWIM clarity.

### Tasks
1. Introduce typed command registration path in command registry:
- support typed arg schema alongside existing command shape.
2. Route command palette execution through typed invocation materialization when schema exists.
3. Persist structured invocation records:
- include args, inferred defaults source, result summary, and execution source.
4. Add explicit default preview contract:
- execution context includes inferred defaults before run.
5. Ensure replay commands use typed invocation data where available.

### Deliverables
- Updates in `web-ui/src/commands.mjs`, `web-ui/src/state.mjs`, `web-ui/src/typed-commands.mjs`.
- Command history normalization updates and tests.

### Exit Criteria
- Typed commands can run from mouse, keybinding, and palette with equivalent results.
- Do-again / do-again-with-args uses structured invocation objects, not string reconstruction.

## WS4: Persistence and Migration Completion
### Goal
Persist the full Phase 1 state contract and guarantee migration safety.

### Tasks
1. Extend snapshot schema to include finalized Phase 1 fields (if needed) and bump schema version only when contract changes.
2. Add migration path from schema `2` to new version if fields/shape change.
3. Implement transcript truncation policy in snapshot creation:
- default max 5,000 entries or 20 MB payload with truncation marker.
4. Validate restore semantics:
- stale presentations remain readable.
- selection/focus normalized.
- task/window integrity preserved.
5. Add compatibility fixtures for schema `0`, `1`, `2`, and latest.

### Deliverables
- Updates in `web-ui/src/persistence/schema.mjs`, `web-ui/src/persistence/migrate.mjs`, `web-ui/src/persistence/serialize.mjs`.
- Migration fixtures and tests.

### Exit Criteria
- Snapshot round-trip is deterministic for canonical fixtures.
- Legacy snapshots migrate to latest schema without data loss in supported fields.

## WS5: Integration Windows and Interaction Closure
### Goal
Close the loop across transcript, command history, debugger/problem actions, and effect dispatch.

### Tasks
1. Transcript window:
- verify selection action bar semantics for command/value/condition entries.
- ensure replay/clipboard outputs are effect-dispatched.
2. Command history window:
- execute typed invocations and preserve defaults metadata.
3. Problems/debugger integration:
- confirm action command payloads reference typed/presentation objects consistently.
4. World state hooks:
- stale marking and revalidation invoked during restore and refresh.

### Deliverables
- Updates in `web-ui/src/state.mjs`, `web-ui/src/widgets.mjs`, `web-ui/src/world-state.mjs`.
- Integration tests spanning transcript -> command -> effect -> persistence.

### Exit Criteria
- End-to-end state flow is deterministic across a scripted replay scenario.

## WS6: Quality Gates and Acceptance Suite
### Goal
Codify Phase 1 acceptance into automated tests that prevent regression.

### Tasks
1. Add Phase 1 acceptance test file set:
- `phase-1-runtime.test.mjs`
- `phase-1-persistence.test.mjs`
- `phase-1-integration.test.mjs`
2. Add replay harness scenario:
- serialize state, restore, replay last recording, compare normalized outputs.
3. Add schema/migration golden fixtures.
4. Wire all tests into `test:sandbox`.

### Exit Criteria
- Acceptance tests pass in local CI command path.
- No existing tests regress.

## Milestone Sequence
1. M1: WS1 complete (recording invariants and transcript determinism).
2. M2: WS2 complete (presentation enforcement and action semantics).
3. M3: WS3 complete (typed command integration and command history fidelity).
4. M4: WS4 complete (persistence/migration and restore guarantees).
5. M5: WS5 complete (cross-window integration closure).
6. M6: WS6 complete (acceptance suite, signoff artifacts).

## Test Strategy
### Mandatory Command
- `cd web-ui && npm test`

### Required Coverage
- Unit: recordings, typed commands, taxonomy validation, migration helpers.
- Integration: transcript actions and command effects, command history replay.
- Persistence: round-trip determinism and legacy migration fixtures.

### Phase 1 Signoff Conditions
- All Phase 1 tests pass.
- All existing tests pass.
- Command/replay/persistence deterministic checks pass.
- Schema and migration documentation updated.

## Risks and Mitigations
- Risk: schema churn during active implementation.
- Mitigation: gate schema bumps through migration fixture updates and explicit changelog in tests.
- Risk: divergence between simple command path and typed path.
- Mitigation: typed path becomes canonical when schema exists; add parity tests.
- Risk: transcript growth affects snapshot size/perf.
- Mitigation: enforce truncation budgets and markers during snapshot creation.
- Risk: presentation metadata gaps at runtime boundaries.
- Mitigation: validate at ingress and auto-degrade with explicit reasons.

## Execution Protocol
1. Implement milestone in small, reviewable patches.
2. Run full `web-ui` tests after each patch set.
3. Update this document with milestone status and completion date.
4. Do not start Phase 2 until M6 signoff is complete.
