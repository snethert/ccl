# RPL Unattended Execution Playbook

Status: Active  
Owner: Runtime/WASM replacement track  
Last Updated: 2026-02-10  
Parent Plan: `doc/wasm/runtime-replacement-master-plan.md`

## Purpose

Define a deterministic operating protocol that lets an agent continue runtime
replacement work for long unattended stretches without reopening closed baselines
by accident or losing synchronization across runtime planning docs.

## Operator Overrides (Active 2026-02-10)

These user-directed constraints override default cadence:

1. Do not create git commits unless explicitly required for safe fallback.
2. Update at most one document per execution cycle.
3. Record any deferred cross-document synchronization in a merge queue for
   end-merge reconciliation.

## Canonical Inputs

Read these before starting any unattended block:

1. `doc/wasm/runtime-replacement-master-plan.md`
2. `doc/wasm/tickets/RPL-00-governance-and-baseline-freeze.md`
3. `doc/wasm/runtime-backend-dependency-matrix.md`
4. `doc/wasm/wasm-program-board.md`
5. Active ticket subplan (`doc/wasm/tickets/RPL-*.md`)

## Autonomy Boundaries

- Runtime/project docs are active update surfaces.
- Backend docs (`BPL-*`) are frozen by default after `X-08=done`.
- Do not reopen backend scope unless runtime changes require a dependency-row
  transition in `doc/wasm/runtime-backend-dependency-matrix.md`.
- Do not mutate committed evidence bundles; publish new additive evidence
  directories instead.

## Unattended Entry Checklist

1. Confirm current active ticket state from the runtime master ticket board.
2. Confirm no hard dependency blocks the active ticket.
3. Confirm `Immediate Next Step` sync state is valid for active mode:
   - standard mode: master plan and ticket subplan match;
   - single-document override mode: any mismatch is represented by an explicit
     deferred queue item.
4. Confirm the expected evidence location and validation lanes for the step.
5. Record the exact action to execute next (single action, no batching).
6. Declare one cycle goal sentence that is testable by explicit evidence.

## Current Cycle Goal Contract (Required)

Before each cycle starts, define one goal sentence in this form:

- `<ticket/doc>: <single action> -> <success evidence>`

Rules:

1. Exactly one action verb (`publish`, `validate`, `sync`, `rerun`, `close`).
2. Exactly one primary evidence target (file path, bundle path, or terminal
   summary check ID).
3. No conjunctions (`and`, `then`, `also`); split multi-action work into later
   cycles.

## Ticket Selection Algorithm (Deterministic)

Apply in this order:

1. Select the highest-priority ticket with `Status=in_progress` and no unmet
   hard dependency.
2. If none are `in_progress`, select the highest-priority `planned` ticket with
   no unmet hard dependency and move it to `in_progress`.
3. If all tickets are `done`, execute a governance cycle under `RPL-00`:
   - run contradiction scan and drift checks,
   - identify runtime-side reopen candidate (if any),
   - otherwise keep additive-only maintenance mode.

Tie-breaker: lower ticket number wins (`RPL-01` before `RPL-06`).

## Cycle Mode (Single-Document Override)

Use this as the active cycle mode unless explicitly changed:

1. Select one target document for the cycle.
2. Apply all cycle updates only to that document.
3. For every additional document that would normally be updated, append a
   deferred sync item to `Pending End-Merge Queue`.
4. Reconcile deferred items in end-merge passes as needed.

## One-Cycle Execution Loop

1. Select one target document for this cycle.
2. Execute one scoped action from `Immediate Next Step`.
3. Run the required validation commands for that action.
4. Publish additive evidence artifact(s) if validation was executed.
5. Update only the selected target document.
6. Queue all deferred cross-document updates in `Pending End-Merge Queue`.
7. Set a new single next action with explicit success evidence.

## Required Sync Set Per Runtime Ticket Update

Standard mode (default architecture):

1. Active ticket subplan (`doc/wasm/tickets/RPL-*.md`)
2. Runtime master (`doc/wasm/runtime-replacement-master-plan.md`)

Conditionally update:

1. `doc/wasm/runtime-backend-dependency-matrix.md`
   - Required when dependency-row status/type/notes change.
2. `doc/wasm/wasm-program-board.md`
   - Required when immediate program action or lane posture changes.
3. `doc/wasm/tickets/RPL-00-governance-and-baseline-freeze.md`
   - Required for governance-cycle progression and synchronization evidence.

Single-document override mode (active):

1. Edit exactly one document in the cycle.
2. Do not perform same-cycle multi-doc sync edits.
3. Add deferred sync items to `Pending End-Merge Queue` with target paths and
   merge conditions.

## Deferred Sync Item Contract

When single-document mode defers required sync updates, add one queue item per
deferred target document with all fields:

1. Queue ID (`YYYY-MM-DD-Q<nn>`).
2. Source document updated in-cycle.
3. Target document deferred.
4. Required update payload (status/notes/next-step/dependency-lane/etc.).
5. Merge condition that allows safe reconciliation.
6. State (`open`, `merged`, `cancelled`) with date.

Queue behavior:

- Never close a cycle with an implied deferred update; every skipped target must
  have an explicit queue item.
- Keep closed items for traceability; append state transitions additively.

## Done-Ticket Reopen Protocol

Reopen only when all are true:

1. New runtime work is required that cannot be represented as additive
   governance maintenance.
2. Existing ticket scope already owns the required behavior.
3. A new concrete action and evidence contract can be defined.

Required reopen edits:

1. Change ticket `Status` from `done` to `in_progress`.
2. Add a reopen note with trigger, owner, and date.
3. Add/extend step rows for the new work slice.
4. Define deterministic validation IDs/commands for the reopened slice.
5. Synchronize reopen state using active mode:
   - standard mode: mirror status/notes/next-step changes in runtime master in
     the same change;
   - single-document override mode: apply one doc change and queue deferred
     sync item(s) for the skipped required target(s).

## Evidence and Artifact Conventions

- Evidence root: `doc/wasm/tickets/evidence/`
- Directory pattern:
  - `rpl-<ticket>-step<step>-YYYY-MM-DD/<run-id>/`
- `run-id` pattern:
  - `rpl<ticket>-YYYYMMDD-HHMMSSZ-<shortsha>`
- Keep prior bundles immutable; publish reruns as new sibling directories.

Minimum bundle contents for command-driven validation:

1. `run_id.txt`
2. `run-status.tsv`
3. `logs/<validation-id>.log`
4. terminal summary JSON for the step contract

## Validation Policy

- Never mark a step complete without either:
  - passing command evidence, or
  - explicit blocker record with failure evidence.
- If environment limits prevent a required lane (for example browser runners),
  capture the exact failure reason and keep the step `in_progress`.
- Prefer existing ticket-defined validation IDs over ad hoc commands.

## Blocker and Gap Handling

When a required validation fails:

1. Open/update a gap ID in the active ticket (`<ticket>GAP-*`).
2. Capture command, failure signature, and impacted IDs.
3. Set next action to focused gap remediation and rerun.
4. Do not advance dependency-row state until gap closure evidence is published.

## Stop Conditions for Long Unattended Blocks

Stop only after all are true:

1. Active step action is complete for this cycle.
2. Sync state is complete for the active mode:
   - standard mode: required sync set updated in-cycle;
   - single-document mode: deferred queue items recorded for every skipped sync
     target.
3. Next single action is defined with success evidence.
4. Any blockers are explicitly recorded with gap IDs.

## Pending End-Merge Queue

Deferred cross-document merges while single-document mode is active.

- Entry template:
  - `ID | source -> target | payload | merge-condition | state@date`
- `2026-02-10-Q1`: none currently queued after policy update cycle.

## Change Log

- 2026-02-10: Clarified cycle-goal contract, deferred-sync queue item schema,
  and stop-condition semantics so single-document mode can run unattended
  without implicit sync assumptions.
- 2026-02-10: Added active operator overrides for no-commit-by-default and
  single-document cycle mode with deferred end-merge queue tracking.
- 2026-02-10: Initial playbook published; made deterministic ticket selection,
  reopen protocol, evidence conventions, and sync rules explicit for long
  unattended runtime execution.
