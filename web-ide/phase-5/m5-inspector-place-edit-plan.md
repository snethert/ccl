# Phase 5 M5 Plan: Inspector Integration and Place Editing

## Document Control
- Status: Complete
- Last Updated: February 8, 2026
- Parent Plan: `web-ide/phase-5/implementation-plan.md`
- Upstream Specs:
  - `web-ide/phase-0/presentation-taxonomy.md`
  - `web-ide/phase-0/typed-command-model.md`
  - `web-ide/phase-0/world-state-and-sessions.md`
  - `web-ide/ide-doctrine.md`
  - `doc/wasm/runtime-bridge.md`

## Objective
Deliver runtime-backed Inspector behavior where inspect, watch, and place-edit workflows are driven by structured runtime payloads, with staged apply and undo that remain auditable in command history and transcript.

## Scope
### In Scope
- Runtime contract and UI handling for `inspector.update` payload variants.
- Runtime-backed `runtime.inspect.presentation` flow with structured type-specific views.
- Runtime place editing lifecycle (`stage`, `apply`, `undo`) with clear edit-group identity.
- Runtime watch synchronization updates after evaluations and mutations.
- Inspector integration tests and smoke coverage.

### Out of Scope
- Background job scheduler and progress surfaces (M6).
- Beginner-mode simplifications and customization settings (Phase 6).
- Full world snapshotting of runtime object graphs (outside Phase 5).

## Baseline and Constraints
1. M1 through M4 are complete, including runtime command transport and debugger integration.
2. Inspector watch and staged edit primitives already exist in UI state but are currently local-first.
3. `runtime.inspect.presentation` exists in the M3 command registry with placeholder behavior.
4. M5 must preserve doctrine constraints:
- Inspector remains the universal pivot.
- Place edits are staged and undoable.
- Mutations are visible as auditable events.

## M5 Decisions (Locked)
1. Keep `inspector.update` as the canonical runtime event kind; use explicit payload variants rather than adding many new event kinds.
2. Keep user-facing UI command ids stable (`ui.inspector.*`) and map to runtime command ids via typed metadata.
3. Runtime remains authoritative for place-edit commit outcomes; UI staged state is a projection of runtime-confirmed edit groups.
4. All place edits must have explicit `editGroupId` and lifecycle status transitions (`staged`, `applied`, `undone`, `failed`).
5. Any stale or missing inspector target degrades to readable fallback, never hard failure.

## Contract Additions

## `inspector.update` Payload Variants
### `type: "snapshot"`
Runtime provides a full inspector snapshot for a target presentation/value.

```json
{
  "type": "snapshot",
  "targetId": "pres-9",
  "targetType": "clos-object",
  "view": {
    "type": "clos-object",
    "summary": "#<FOO ...>",
    "sections": [
      {
        "id": "slots",
        "title": "Slots",
        "rows": [
          {
            "id": "slot-x",
            "label": "X",
            "valueSummary": "3",
            "presentationId": "pres-slot-x",
            "place": {
              "placeId": "pl-slot-x",
              "description": "Slot X",
              "editable": true
            }
          }
        ]
      }
    ]
  },
  "watches": [],
  "stale": false
}
```

### `type: "watch.sync"`
Runtime sends watch value refreshes.

```json
{
  "type": "watch.sync",
  "watches": [
    {
      "id": "watch-1",
      "presentationId": "pres-9",
      "label": "Result",
      "valueSummary": "42",
      "updatedAt": 1738992003000
    }
  ]
}
```

### `type: "edit-group"`
Runtime emits staged/apply/undo lifecycle updates.

```json
{
  "type": "edit-group",
  "editGroup": {
    "id": "edit-12",
    "label": "Set slot X",
    "status": "applied",
    "edits": [
      {
        "placeId": "pl-slot-x",
        "before": "3",
        "after": "4"
      }
    ],
    "updatedAt": 1738992003500
  },
  "audit": {
    "entryText": "Applied edit group edit-12 (Slot X: 3 -> 4)"
  }
}
```

### Invariants
- `type` is required for every `inspector.update`.
- `snapshot` requires `targetId` and `view.type`.
- `edit-group` requires `editGroup.id` and `editGroup.status`.
- `editGroup.status` must be one of `staged`, `applied`, `undone`, `failed`.
- `watch.sync` entries must be id-stable within a workspace session.

## Runtime Command Contracts in M5
1. `runtime.inspect.presentation`
- Args: `presentationId` or equivalent target reference.
- Result: `inspector.update` (`snapshot`) and terminal `command.result`.
2. `runtime.watch.pin`
- Args: watch target metadata.
- Result: `inspector.update` (`watch.sync`) and terminal `command.result`.
3. `runtime.watch.unpin`
- Args: `watchId`.
- Result: `inspector.update` (`watch.sync`) and terminal `command.result`.
4. `runtime.place.stage`
- Args: `placeId`, `after`, optional context.
- Result: `inspector.update` (`edit-group` with `staged`) and terminal `command.result`.
5. `runtime.place.apply`
- Args: `editGroupId`.
- Result: `inspector.update` (`edit-group` with `applied` or `failed`) and terminal response.
6. `runtime.place.undo`
- Args: `editGroupId`.
- Result: `inspector.update` (`edit-group` with `undone` or `failed`) and terminal response.

## Runtime and UI Architecture Changes

## Runtime Side (CL + host)
1. Implement inspector snapshot builder with type-specific sections and place metadata.
2. Implement watch synchronization emitter for post-eval and mutation events.
3. Implement staged place-edit registry in runtime bridge context:
- allocate `editGroupId`
- track status and before/after
- enforce transition validity.
4. Emit transcript-friendly audit metadata for apply/undo outcomes.

## UI Side
1. Extend runtime bridge handling for `inspector.update` variants in `web-ui/src/runtime-bridge.mjs`.
2. Add inspector state upsert helpers in `web-ui/src/state.mjs`:
- target snapshot merge
- watch sync merge
- edit-group lifecycle merge.
3. Route inspector commands through runtime command client while retaining user-facing ids:
- `ui.inspector.watch.pin` -> `runtime.watch.pin`
- `ui.inspector.watch.unpin` -> `runtime.watch.unpin`
- `ui.inspector.edit.stage` -> `runtime.place.stage`
- `ui.inspector.edit.apply` -> `runtime.place.apply`
- `ui.inspector.edit.undo` -> `runtime.place.undo`
4. Keep fallback local behavior only when runtime client is unavailable.

## Work Breakdown

### M5-A: Protocol Freeze for Inspector Payloads
### Tasks
1. Update `doc/wasm/runtime-bridge.md` for `inspector.update` variants and required fields.
2. Define edit-group lifecycle status rules and failure representation.
3. Add correlation notes for inspector command request/terminal handling.

### Deliverables
- Updated protocol docs and payload examples.
- Bridge-fixture tests for variant validation.

### Exit Criteria
- Documentation and runtime bridge strict-kind tests agree on payload variants.

### M5-B: Runtime Inspector Snapshot Encoder
### Tasks
1. Build runtime functions that map values/presentations to structured inspector views.
2. Add place metadata (`placeId`, `editable`, description) where available.
3. Emit `inspector.update` snapshot after inspect command and on explicit refresh.

### Deliverables
- CL inspector snapshot emitter in `level-1/l1-readloop-lds.lisp`.
- Optional helper updates under `lisp-kernel/*` for payload transport if needed.

### Exit Criteria
- Runtime inspect command produces stable, schema-conforming snapshot payloads.

### M5-C: Runtime Place Edit Lifecycle
### Tasks
1. Add runtime commands for `stage`, `apply`, and `undo` with `editGroupId`.
2. Validate place existence/editability and arg shape before stage.
3. Emit edit-group lifecycle updates and terminal responses.
4. Emit audit details suitable for transcript entry generation.

### Deliverables
- Runtime place-edit dispatcher logic.
- Deterministic status transitions and error mapping.

### Exit Criteria
- Stage/apply/undo flows execute end-to-end with explicit lifecycle state.

### M5-D: UI Runtime Inbound Inspector Handlers
### Tasks
1. Add `inspector.update` variant handlers in `web-ui/src/runtime-bridge.mjs`.
2. Merge snapshot/watch/edit-group updates into inspector state structures.
3. Refresh inspector windows deterministically after runtime updates.

### Deliverables
- Runtime bridge inspector handlers.
- State upsert helpers and refresh orchestration.

### Exit Criteria
- Inspector surfaces runtime updates without ad-hoc widget mutation.

### M5-E: Command Routing and History Correlation
### Tasks
1. Mark inspector typed commands as runtime-scoped with runtime command id mappings.
2. Ensure command history status transitions (`pending` -> terminal) remain stable.
3. Correlate runtime terminal responses to existing UI invocation ids.

### Deliverables
- Inspector command metadata updates.
- Runtime command client and command execution path tests for inspector commands.

### Exit Criteria
- Inspector user actions route through runtime and remain replayable/auditable.

### M5-F: Inspector UI Metadata Fidelity
### Tasks
1. Render structured sections per runtime view type.
2. Surface place editability and staged edit statuses clearly.
3. Keep progressive disclosure defaults with explicit “more” expansion.

### Deliverables
- Inspector widget rendering refinements.
- DOM/canvas parity checks for inspector surfaces if style or layout changes.

### Exit Criteria
- Inspector remains minimal by default while exposing complete object/tool context on demand.

### M5-G: Acceptance and Regression Gates
### Tasks
1. Add tests:
- `web-ui/tests/phase-5-runtime-inspector.test.mjs`
- `web-ui/tests/phase-5-runtime-place-edit.test.mjs`
- `web-ui/tests/phase-5-runtime-inspector-integration.test.mjs`
2. Add smoke:
- `doc/wasm/js/runtime-inspector-smoke.mjs`
- include in `doc/wasm/js/all-smoke.mjs`
3. Run validation:
- `cd web-ui && npm test`
- `node doc/wasm/js/all-smoke.mjs`

### Exit Criteria
- New Phase 5 inspector tests pass.
- Existing suites remain green.

## Failure and Recovery Rules
1. Unknown presentation target:
- Runtime returns `command.error` with `phase="dispatch"` and `retryable=false`.
2. Invalid place/edit args:
- Runtime returns `command.error` with `phase="validate"` and diagnostics.
3. Edit apply failure:
- Runtime emits `edit-group` status `failed` and preserves staged edit context.
4. Stale object reference:
- Runtime emits readable fallback snapshot with `stale=true`; UI stays functional.

## Observability
1. Correlation fields:
- `requestId`, `invocationId`, `targetId`, `placeId`, `editGroupId`, `durationMs`.
2. Runtime diagnostics:
- `runtime.log` on snapshot fallback, place validation failure, transition rejection.
3. UI diagnostics:
- runtime-bridge error callbacks for malformed `inspector.update` payloads.

## Risks and Mitigations
1. Risk: runtime/object shape variability causes inspector schema drift.
- Mitigation: normalize runtime snapshot through one adapter path and fixture-test representative types.
2. Risk: edit-group race conditions across repeated apply/undo actions.
- Mitigation: enforce transition FSM and idempotent terminal handling.
3. Risk: command history becomes ambiguous across UI and runtime ids.
- Mitigation: preserve stable UI command ids in history and store runtime command id as metadata.

## Done Definition for M5
1. `inspector.update` payload variants are documented and validated.
2. Runtime-backed inspect command returns structured snapshots with place metadata.
3. Runtime-backed stage/apply/undo place edits work with explicit lifecycle statuses.
4. Inspector command history remains correlated, replayable, and auditable.
5. `cd web-ui && npm test` passes.
6. `node doc/wasm/js/runtime-inspector-smoke.mjs` passes.

## Completion Notes
1. Runtime bridge and state handlers now ingest `inspector.update` variants (`snapshot`, `watch.sync`, `edit-group`) and refresh inspector windows deterministically.
2. Inspector typed commands route through runtime command ids while preserving stable UI command ids for history and replay.
3. Runtime place-edit lifecycle now supports `staged`, `applied`, `undone`, and `failed`, with transcript-auditable update payloads.
4. Acceptance tests landed:
- `web-ui/tests/phase-5-runtime-inspector.test.mjs`
- `web-ui/tests/phase-5-runtime-place-edit.test.mjs`
- `web-ui/tests/phase-5-runtime-inspector-integration.test.mjs`
- `doc/wasm/js/runtime-inspector-smoke.mjs`
- `node doc/wasm/js/all-smoke.mjs` currently fails in `compiler-smoke` (`unexpected ffi-add result: got=0 expected=42`), outside M5 scope.
