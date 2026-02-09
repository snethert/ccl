# BPL-00 - Governance and Baseline Freeze

Status: in_progress  
Priority: P0  
Owner: Compiler/backend migration track  
Last Updated: 2026-02-09  
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

## Immediate Next Step

- Action: continue governance-compliant execution by advancing BPL-06 Step 2 fixture/evidence-template publication and keeping matrix/master/subplan updates synchronized in-cycle.
- Why now: BPL-06 Step 1 checkpoint contracts are frozen, so deterministic execution readiness now depends on synchronized fixture/evidence publication.
- Success evidence: BPL-06 Step 2 status/notes and matrix/master/program-board references remain synchronized while `BPL06-CP*` and `B5M-*` identifiers stay frozen.

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
- Next:
  - Maintain the same synchronization discipline for BPL-06 Step 2 and subsequent dependency-row updates.

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
