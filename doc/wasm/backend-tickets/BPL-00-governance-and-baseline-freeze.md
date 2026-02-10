# BPL-00 - Governance and Baseline Freeze

Status: in_progress  
Priority: P0  
Owner: Compiler/backend migration track  
Last Updated: 2026-02-10  
Parent Plan: `doc/wasm/backend-migration-master-plan.md`

## Scope

In scope:

- Establish backend migration execution rules and doc-sync discipline.
- Freeze baseline backend assumptions and known migration pressures.
- Define cross-track update behavior with runtime replacement docs.

Out of scope:

- Implementing backend migration features directly (BPL-01+).
- Runtime architecture implementation details (RPL tickets).

## Dependencies

- None.

## Deliverables

1. Backend migration master plan with ticket board and detail blocks.
2. Backend ticket subplan folder conventions.
3. Cross-track update linkage to runtime/backend dependency matrix.

## Exit Criteria

- Backend master plan exists and is linked from the program board.
- BPL-00 and BPL-01 subplans exist and are linked from the master plan.
- Cross-track sync behavior is documented and executable.
- At least one downstream backend ticket update follows the documented process.

## Current Notes

- Backend master plan has been created at `doc/wasm/backend-migration-master-plan.md`.
- Cross-track dependency matrix has been created at `doc/wasm/runtime-backend-dependency-matrix.md`.
- Backend ticket directory conventions now exist under `doc/wasm/backend-tickets/`.
- BPL-03 Step 1 mapping output is now published with explicit `B3*` consumption IDs.
- Dependency row `X-02` is now cleared and synchronized across backend/runtime master plans, matrix, and active ticket subplans.
- BPL-06 Step 1 checkpoint contract is now published with frozen `BPL06-CP01`..`BPL06-CP05` IDs and synchronized master/matrix/program-board notes.
- BPL-06 Step 2 fixture matrix/templates are now published (`BPL06-FX01`..`BPL06-FX05`; `backend_diff_case_result_v1`; `backend_diff_checkpoint_summary_v1`) with synchronized master/matrix/program-board notes.
- BPL-06 Step 3 triage/intake outputs are now published (`BPL06-SEV-*`, `BPL06-RB-*`, `BPL06-INT-*`) with synchronized master/matrix/program-board notes.
- RPL-04 Step 3 rerun evidence is now published (`rpl-04-step3-rerun-2026-02-10`) with `status=pass`, `x04_step2_ready=true`; dependency row `X-04` is synchronized to `done`.
- BPL-07 Step 1 baseline is now published with row IDs `BPL07-BM01`..`BPL07-BM05` mapped one-to-one to frozen `BPL06-CP01`..`BPL06-CP05`.
- BPL-07 Step 2 run-v1 evidence is now published at `doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-002604Z-91fdb0be/` with deterministic row summaries.
- BPL-07 Step 3 closure-readiness criteria are now published (`BPL07-CR01`..`BPL07-CR05`) with explicit blocker mapping for missing BPL-06 intake artifacts and `BPL07-BM05` perf overrun.
- BPL-07 remediation run-v2 is now committed with concrete run IDs `bpl06-20260210-005408Z-91fdb0be` and `bpl07-20260210-005408Z-91fdb0be`; criteria `CR01`..`CR03` are now pass and backend preconditions for `CR04`/`CR05` are satisfied.
- BPL-08 Step 1 integration baseline is now published (`BPL08-IC01`..`BPL08-IC06`) with immutable runtime/backend closure-bundle references.
- BPL-08 Step 2 deterministic validation packet is now published (`BPL08-IV01`..`BPL08-IV06`) with concrete command/evidence mappings keyed to Step 1 checkpoints.
- BPL-08 Step 3 integration closure-readiness packet is now published (`BPL08-CR01`..`BPL08-CR06`) keyed to `BPL08-IV*`, preserving immutable bundle IDs and explicit `X-07=open` carry-forward posture.

## Immediate Next Step

- Action: continue `Pack A` by carrying published BPL-08 Step 3 closure rows as immutable backend signoff input while runtime executes `RPL-08 Step 1` unified budget-contract work.
- Why now: backend closure packetization is complete and only runtime-side unified budget approval remains for `X-07`.
- Success evidence: synchronized matrix/master/board/BPL-00/BPL-07/BPL-08 wording preserves `BPL08-CR*`, immutable bundle IDs, and explicit `X-07=open` carry-forward posture.

## Detailed Work Breakdown

### Step 1 - Baseline Freeze

- Status: done
- Notes:
  - Baseline assumptions and migration pressure are captured in backend master plan snapshot.
- Next:
  - Keep snapshot updates limited to materially relevant architecture changes.

### Step 2 - Governance Rules and Sync Contract

- Status: done
- Notes:
  - Update contract and cross-track sync rule are documented.
- Next:
  - Enforce dual-update behavior for all backend ticket updates.

### Step 3 - Subplan Framework Availability

- Status: done
- Notes:
  - Backend subplan folder and naming rules are in place.
- Next:
  - Add new BPL ticket subplans as they move into active work.

### Step 4 - First Downstream Cycle Validation

- Status: done
- Notes:
  - Multiple downstream backend cycles have been executed with synchronized master/subplan/matrix updates.
  - `X-02` dependency closure was completed in-cycle during BPL-03 Step 1 mapping publication.
  - BPL-06 Step 1 checkpoint-contract publication was synchronized in-cycle across subplan/master/matrix/program-board docs.
  - BPL-06 Step 2 fixture/template publication was synchronized in-cycle across subplan/master/matrix/program-board docs.
  - BPL-06 Step 3 triage/intake publication was synchronized in-cycle across subplan/master/matrix/program-board docs.
- Next:
  - Maintain the same synchronization discipline for BPL-07 closure-review handoff and subsequent dependency-row updates.

## Test and Validation Plan

- Documentation integrity:
  - Confirm referenced subplan paths exist.
  - Confirm BPL-00/BPL-01 status sync with backend master plan.
- Process validation:
  - Perform one downstream backend update and verify dual-update behavior.
- Cross-track validation:
  - Confirm any matrix-affecting changes are updated in dependency matrix.

## Risks and Mitigations

- Risk: backend and runtime docs drift on shared assumptions.
  - Mitigation: require dependency matrix update whenever cross-track impact changes.
- Risk: migration work begins without concrete assumption inventory.
  - Mitigation: prioritize BPL-01 before feature implementation tickets.
- Risk: governance overhead reduces delivery speed.
  - Mitigation: keep updates concise and evidence-driven.

## Change Log

- 2026-02-09: Initial BPL-00 subplan created with governance and baseline-freeze workflow.
- 2026-02-09: Synced governance state after BPL-03 Step 1 mapping publication and `X-02` closure; advanced immediate next action to BPL-03 Step 2 contract drafting.
- 2026-02-09: Synced governance state after BPL-06 Step 1 checkpoint-contract publication; advanced immediate next action to BPL-06 Step 2 fixture/evidence-template publication.
- 2026-02-09: Synced governance state after BPL-06 Step 2 fixture/template publication; advanced immediate next action to BPL-06 Step 3 triage/gate-integration definition.
- 2026-02-09: Synced governance state after BPL-06 Step 3 triage/intake publication; advanced immediate next action to BPL-07 Step 1 budget/measurement definition.
- 2026-02-10: Synced governance state after RPL-04 Step 3 rerun closure evidence; dependency row `X-04` is now `done` and backend immediate next action remains BPL-07 Step 1 budget/measurement definition.
- 2026-02-10: Synced governance state after BPL-07 Step 1 publication (`BPL07-BM01`..`BPL07-BM05`); immediate next action advanced to BPL-07 Step 2 run-v1 measurement evidence execution.
- 2026-02-10: Resynced governance state after RPL-05 Step 1 publication to keep Pack A backend wording on BPL-07 Step 1 continuation over frozen `BPL06-*` intake artifacts.
- 2026-02-10: Synced governance state after BPL-07 Step 2 run-v1 evidence publication (`bpl07-20260210-002604Z-91fdb0be`); immediate next action advanced to BPL-07 Step 3 closure-readiness criteria for `X-06`/`X-07` blockers.
- 2026-02-10: Synced governance state after BPL-07 Step 3 criteria publication (`BPL07-CR01`..`BPL07-CR05`); immediate next action advanced to one closure-remediation execution packet for unresolved `CR01`/`CR03` blockers.
- 2026-02-10: Synced governance state after BPL-07 remediation run-v2 (`bpl06-20260210-005408Z-91fdb0be`, `bpl07-20260210-005408Z-91fdb0be`); immediate next action advanced to matrix-level `X-06`/`X-07` closure-review handoff pending runtime-side signoff evidence.
- 2026-02-10: Resynced immediate-next-step wording to Pack A runtime run-v2 execution while preserving backend remediation pass bundle as closure-review input for `X-06`/`X-07`.
- 2026-02-10: Synced governance state after BPL-08 Step 1 publication (`BPL08-IC01`..`BPL08-IC06`); immediate next action advanced to BPL-08 Step 2 deterministic validation packet definition in parallel with RPL-08 Step 1.
- 2026-02-10: Synced governance state after BPL-08 Step 2 publication (`BPL08-IV01`..`BPL08-IV06`); immediate next action advanced to BPL-08 Step 3 closure-readiness packet publication in parallel with RPL-08 Step 1.
- 2026-02-10: Synced governance state after BPL-08 Step 3 publication (`BPL08-CR01`..`BPL08-CR06`); immediate next action now preserves backend closure packet carry-forward while `X-07` remains open for runtime unified budget signoff.
