# Phase 5 M4 Plan: Restarts and Debugger Integration

## Document Control
- Status: Complete
- Last Updated: February 8, 2026
- Parent Plan: `web-ide/phase-5/implementation-plan.md`
- Upstream Specs:
  - `web-ide/phase-0/restart-and-condition-contract.md`
  - `web-ide/phase-0/presentation-taxonomy.md`
  - `web-ide/phase-0/typed-command-model.md`
  - `doc/wasm/runtime-bridge.md`
  - `doc/wasm/kernel-request-abi.md`

## Objective
Deliver restart-first debugger runtime integration where conditions, frames, locals, and restart invocations are emitted by runtime and handled by UI as typed presentations with safe, auditable command flow.

## Scope
### In Scope
- Runtime emission of debugger condition snapshots with restart metadata.
- Runtime support for `runtime.restart.invoke` command execution.
- UI ingest of debugger runtime messages into errors/debugger state.
- Debugger rendering of restart safety, recommendation reason, argument schema, preview.
- Typed command history integration for runtime restart invocations.
- Frame and local payload contracts needed for debugger navigation.

### Out of Scope
- Inspector place mutation protocol and staged setf editing (M5).
- Background job scheduling and progress plumbing (M6).
- Full time-travel debugger semantics beyond current transcript history.

## Baseline and Constraints
1. M1 through M3 are complete; typed runtime command dispatch is active.
2. `runtime.restart.invoke` is currently a known command ID in CL dispatcher but intentionally throws "not available until M4".
3. Existing UI debugger command wiring (`ui.debugger.restart.invoke`) works with local runtime output effect stubs and must be upgraded to runtime-backed execution.
4. Runtime bridge already reserves `debugger.restart`; M4 must formalize payload variants to avoid ambiguous handling.

## M4 Decisions (Locked)
1. Keep canonical bridge transport JSON envelopes; no new non-JSON control channel for debugger payloads.
2. Represent debugger state as explicit runtime snapshots rather than piecemeal implicit deltas.
3. Runtime restart invocation returns exactly one terminal `command.result` or `command.error` correlated by `requestId`.
4. Recommendation is runtime-hinted, UI-transparent: reason is always visible and never auto-invoked.
5. Restart arguments remain typed with schema plus generic fallback editor if no `uiHint`.

## Contract Additions

## `debugger.snapshot` (New Kind)
### Purpose
Emit a complete debugger snapshot for a condition context.

### Payload
```json
{
  "errorId": "err-77",
  "taskId": "task-1",
  "condition": {
    "id": "err-77",
    "kind": "error",
    "message": "Division by zero",
    "summary": "Attempted (/ 1 0)",
    "sections": [
      {
        "id": "sec-what",
        "title": "What happened",
        "text": "Attempted to divide by zero.",
        "actions": []
      }
    ]
  },
  "frames": [
    {
      "frameId": "frm-1",
      "label": "FOO",
      "function": "FOO",
      "location": { "file": "src/foo.lisp", "line": 42, "column": 7 },
      "locals": [
        { "bindingId": "bind-1", "name": "X", "valueSummary": "0", "presentationId": "pres-bind-1" }
      ]
    }
  ],
  "restarts": [
    {
      "id": "rst-1",
      "title": "Use Value",
      "description": "Provide a non-zero denominator.",
      "safety": "safe",
      "argSchema": [
        { "name": "value", "type": "number", "required": true, "default": 1, "uiHint": "numeric-input" }
      ],
      "preview": { "text": "Will retry with denominator 1." },
      "recommended": true,
      "recommendedReason": "Most likely successful recovery path."
    }
  ],
  "selectedFrameId": "frm-1"
}
```

### Invariants
- `errorId` is required and stable for the debugger session.
- Every restart includes `id`, `title`, `safety`, and `argSchema` (empty array allowed).
- If `recommended=true`, `recommendedReason` must be non-empty.
- `frames` and `locals` are optional but must be type-stable when present.

## `debugger.restart` (Refined Kind)
### Purpose
Emit targeted restart updates when full snapshot replacement is unnecessary.

### Payload Variants
1. `type: "set"`: set restart list for `errorId`.
2. `type: "invoked"`: confirm invocation outcome metadata for transcript/debugger updates.

### Invariants
- Variant type is mandatory.
- `invoked` payload includes `restartId`, `errorId`, and outcome summary.
- `debugger.restart` never substitutes for terminal command result/error correlation.

## Runtime Command Contracts in M4
1. `runtime.restart.invoke`
- Args: `restartId` (required), `errorId` (required), `args` (optional map).
- Terminal response: `command.result` with structured `restartOutcome`, or `command.error` with condition summary.
2. `runtime.debugger.open`
- Optional command to request latest debugger snapshot for `errorId`.
- Used by debugger panel refresh and explicit reopen flows.
3. `runtime.debugger.frame.select`
- Optional command for frame-focus updates where runtime needs selection context.

## Runtime and UI Architecture Changes

## Runtime Side (CL + host)
1. Add restart adapter functions that normalize `compute-restarts` output to schema.
2. Add debugger snapshot builder for condition, sections, frames, locals, and restarts.
3. Implement `runtime.restart.invoke` dispatcher branch:
- Resolve restart by id against current condition context.
- Validate typed args against restart `argSchema`.
- Invoke restart interactively/non-interactively as appropriate.
- Emit runtime output entries and terminal command response.
4. Emit `debugger.snapshot` when entering break loop and after restart-affecting transitions.

## UI Side
1. Extend runtime message handling in `web-ui/src/runtime-bridge.mjs`:
- Add handlers for `debugger.snapshot` and refined `debugger.restart`.
- Normalize and merge condition/restart/frame payloads into state.
2. Upgrade debugger command wiring:
- Keep `ui.debugger.restart.invoke` as the user-facing command id.
- Mark command metadata as runtime-scoped and dispatch through runtime command client.
- Preserve typed invocation history with pending/succeeded/failed terminal status.
3. Enhance debugger window rendering:
- Safety badges (`safe`, `destructive`, `irreversible`).
- Recommendation reason visibility.
- Argument schema presence and fallback editor affordance.
- Frame rows with source jump affordance and local-value inspect actions.

## Work Breakdown

### M4-A: Protocol Freeze for Debugger Payloads
### Tasks
1. Update `doc/wasm/runtime-bridge.md` with `debugger.snapshot` and refined `debugger.restart` variants.
2. Add strict field requirements for restart recommendation transparency.
3. Add examples for frame/local payloads and restart invocation result metadata.

### Deliverables
- Updated `doc/wasm/runtime-bridge.md`.
- New fixture coverage in `web-ui/tests/phase-5-runtime-bridge.test.mjs`.

### Exit Criteria
- Bridge docs and tests agree on required fields and variants.

### M4-B: CL Restart Snapshot Encoder
### Tasks
1. Add CL helpers to normalize condition reports and restart metadata.
2. Build frame/local extraction helpers with safe fallbacks on unavailable source info.
3. Emit `debugger.snapshot` envelope via existing runtime event emitter.

### Deliverables
- Runtime debugger snapshot encoder in `level-1/l1-readloop-lds.lisp`.
- Optional support helpers in `lisp-kernel/*` if ABI fields are needed.

### Exit Criteria
- Runtime emits deterministic debugger snapshot payloads during break-loop entry.

### M4-C: Runtime Restart Invocation Handler
### Tasks
1. Replace M3 placeholder branch for `runtime.restart.invoke`.
2. Validate restart args using runtime schema rules and coercion guardrails.
3. Emit terminal `command.result`/`command.error` with correlation.
4. Emit transcript output describing restart outcome for auditability.

### Deliverables
- `runtime.restart.invoke` execution path in CL dispatcher.
- Regression-safe error mapping for unknown restart id and invalid arg shapes.

### Exit Criteria
- Restart invocation works from runtime command path and returns one terminal response.

### M4-D: UI Runtime Inbound Debugger Handlers
### Tasks
1. Add `debugger.snapshot` and `debugger.restart` handling to `web-ui/src/runtime-bridge.mjs`.
2. Merge payload into errors/debugger state using existing normalize helpers.
3. Ensure stale/missing frame locals degrade gracefully and remain readable.

### Deliverables
- Extended runtime bridge handlers.
- State merge helpers (new or existing function reuse in `web-ui/src/state.mjs`).

### Exit Criteria
- Runtime debugger messages deterministically update debugger UI state.

### M4-E: Command Routing and History Integration
### Tasks
1. Update debugger restart command metadata to runtime scope.
2. Dispatch through `runtimeCommandClient` while keeping command palette and action bar behavior unchanged.
3. Ensure history entries transition through pending -> terminal state with diagnostics.

### Deliverables
- Command registration and runtime dispatch wiring changes.
- Tests proving command history correlation for restart invocations.

### Exit Criteria
- Debugger restart actions flow through runtime command channel and preserve audit trail.

### M4-F: Debugger UI Metadata Fidelity
### Tasks
1. Render restart safety, argument schema presence, preview text, and recommendation reason.
2. Render frame list and locals with actionable commands (`inspect`, `jump to source` where available).
3. Keep progressive disclosure defaults: summary first, details on demand.

### Deliverables
- Debugger widget updates in `web-ui/src/widgets.mjs` and related state adaptors.
- Snapshot/parity tests for debugger DOM and canvas/WebGL if needed.

### Exit Criteria
- Debugger view visibly reflects runtime metadata and remains calm/minimal by default.

### M4-G: Acceptance and Regression Gates
### Tasks
1. Add tests:
- `web-ui/tests/phase-5-runtime-debugger.test.mjs`
- `web-ui/tests/phase-5-runtime-restart-invoke.test.mjs`
- extend `web-ui/tests/phase-2-debugger.test.mjs` for runtime-backed path.
2. Add smoke scenario:
- runtime emits debugger snapshot.
- UI invokes runtime restart command.
- runtime returns terminal response and transcript update.
3. Run:
- `cd web-ui && npm test`
- `node doc/wasm/js/all-smoke.mjs`

### Exit Criteria
- New Phase 5 debugger/restart tests pass.
- Existing suites remain green.

## Failure and Recovery Rules
1. Unknown restart id:
- Runtime returns `command.error` with `phase="dispatch"` and `retryable=false`.
2. Invalid restart args:
- Runtime returns `command.error` with `phase="validate"` and argument diagnostics.
3. Missing frame metadata:
- UI shows placeholder frame row without source jump, does not fail rendering.
4. Duplicate terminal response:
- UI keeps first terminal event, logs diagnostic in `runtime.log`.

## Observability
1. Correlation fields:
- `requestId`, `invocationId`, `errorId`, `restartId`, `commandId`, `durationMs`.
2. Runtime diagnostics:
- `runtime.log` on restart lookup failure, arg validation failure, frame extraction fallback.
3. UI diagnostics:
- `onError` hooks in runtime bridge for malformed debugger payloads.

## Risks and Mitigations
1. Risk: restart metadata differs across runtime contexts.
- Mitigation: centralize restart normalization and enforce schema-level tests.
2. Risk: frame extraction can be slow or brittle.
- Mitigation: progressive payload policy with optional locals and capped frame depth.
3. Risk: debugger command id churn breaks command history replay.
- Mitigation: keep `ui.debugger.restart.invoke` stable and route runtime behavior via metadata/runtime bridge.

## Done Definition for M4
1. `runtime.restart.invoke` implemented in runtime dispatcher.
2. Runtime emits debugger snapshot payload with restart metadata and optional frames/locals.
3. UI ingests debugger runtime payloads and renders restart metadata correctly.
4. Restart invocations are correlated, recorded, and terminally resolved in command history.
5. `cd web-ui && npm test` passes.
6. `node doc/wasm/js/runtime-debugger-smoke.mjs` passes and `node doc/wasm/js/all-smoke.mjs` passes.

## Completion Summary
1. M4-A complete:
- `doc/wasm/runtime-bridge.md` now defines `debugger.snapshot` and refined `debugger.restart` payload contracts and invariants.
- `web-ui/bridge/runtime.mjs` strict kind set now includes `debugger.snapshot`.
2. M4-B and M4-C complete:
- `level-1/l1-readloop-lds.lisp` now emits debugger snapshots from break-loop error handling and implements runtime handlers for `runtime.restart.invoke` and `runtime.debugger.open`.
- Runtime emits `debugger.restart` invoked updates and terminal command responses.
3. M4-D and M4-F complete:
- `web-ui/src/runtime-bridge.mjs` now handles `debugger.snapshot` and `debugger.restart`.
- `web-ui/src/state.mjs` now upserts runtime debugger snapshots/restart updates and refreshes debugger windows.
- Debugger list item labels and classes now carry recommendation reason, preview text, and arg schema presence metadata.
4. M4-E complete:
- `ui.debugger.restart.invoke` is runtime-scoped and transport-mapped to `runtime.restart.invoke`.
- Runtime command client now supports metadata-based runtime command id overrides.
- Runtime command terminal events now patch existing invocation history entries by invocation id without clobbering UI command ids.
5. M4-G complete:
- Added tests: `web-ui/tests/phase-5-runtime-debugger.test.mjs`, `web-ui/tests/phase-5-runtime-restart-invoke.test.mjs`.
- Added smoke: `doc/wasm/js/runtime-debugger-smoke.mjs` and wired it through `doc/wasm/js/all-smoke.mjs`.
- Validation passed: `cd web-ui && npm test`, `node doc/wasm/js/runtime-debugger-smoke.mjs`, and `node doc/wasm/js/all-smoke.mjs`.
