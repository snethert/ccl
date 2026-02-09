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

## Immediate Next Step

- Action: execute BPL-01 Step 1 inventory output and sync both backend master plan and dependency matrix in one change.
- Why now: governance quality is only real after first downstream cycle execution.
- Success evidence: BPL-01 moves to active execution and matrix rows are updated with any discovered dependency impact.

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

- Status: in_progress
- Notes:
  - Awaiting first backend downstream cycle (BPL-01 Step 1 execution).
- Next:
  - Validate process effectiveness during BPL-01 kickoff and adjust only with documented rationale.

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
