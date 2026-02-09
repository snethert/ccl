# RPL-00 - Governance and Baseline Freeze

Status: in_progress  
Priority: P0  
Owner: Runtime/WASM replacement track  
Last Updated: 2026-02-09  
Parent Plan: `doc/wasm/runtime-replacement-master-plan.md`

## Scope

In scope:

- Establish the replacement-track operating model and update discipline.
- Freeze and memorialize current baseline status references used by all downstream tickets.
- Define required sync behavior between ticket subplans and the master plan.
- Define fresh-context resume workflow and handoff rules.

Out of scope:

- Implementing runtime architecture changes directly (covered by RPL-01+).
- Storage V2 implementation details (covered by RPL-05+).
- Shared-memory protocol implementation details (covered by RPL-03).

## Dependencies

- None.

## Deliverables

1. Canonical replacement master plan with ticket board and per-ticket detail blocks.
2. Ticket subplan template and subplan directory conventions.
3. Governance checklist for update cadence, sync rules, and resume protocol.

## Exit Criteria

- RPL-00 and RPL-01 subplans exist and are linked from the master plan.
- Master plan contains no "subplan not yet authored" note for RPL-00 and RPL-01.
- Update and resume rules are documented and executable without additional context.
- At least one downstream ticket update follows the documented sync process.

## Current Notes

- Master plan is present at `doc/wasm/runtime-replacement-master-plan.md`.
- Ticket template and folder sync rules are present under `doc/wasm/tickets/`.
- Baseline runtime status and artifact-size facts are captured in the master plan snapshot.
- First downstream execution cycle has now started through RPL-01 Step 1 updates with synchronized master/subplan edits.

## Immediate Next Step

- Action: continue the governance-compliant downstream update loop by executing RPL-01 Step 2 and syncing both docs in one change.
- Why now: first-cycle validation has occurred; repeatable cadence now needs confirmation on the next ticket step.
- Success evidence: RPL-01 Step 2 status/notes/evidence are reflected consistently in both subplan and master plan.

## Detailed Work Breakdown

### Step 1 - Baseline Snapshot Freeze

- Status: done
- Notes:
  - Baseline docs and current state references are captured in the master plan.
  - Current architecture mismatches against target direction are recorded.
- Next:
  - Keep baseline snapshot current only when materially relevant to active ticket decisions.

### Step 2 - Governance Rules and Update Contract

- Status: done
- Notes:
  - Master plan includes required update contract and resume protocol.
  - Sync rules explicitly require updating both master and subplan docs together.
- Next:
  - Apply this process on each ticket update without exception.

### Step 3 - Subplan Framework Availability

- Status: done
- Notes:
  - Subplan template and README naming/sync conventions are in place.
- Next:
  - Scaffold subplans for upcoming P0 tickets as they move into active work.

### Step 4 - Dependency and Priority Flow Validation

- Status: done
- Notes:
  - Ticket dependencies and priorities are defined in the master plan.
  - First downstream ticket execution has been performed via RPL-01 Step 1 with synchronized updates.
- Next:
  - Reassess only if RPL-01 Step 2 uncovers ordering problems.

### Step 5 - Governance Completion Check

- Status: in_progress
- Notes:
  - One downstream ticket cycle has now been completed using the required sync process.
- Next:
  - Decide whether to close or keep RPL-00 active after one additional downstream cycle (RPL-01 Step 2).

## Test and Validation Plan

- Documentation integrity:
  - Confirm all referenced subplan paths exist.
  - Confirm RPL-00 and RPL-01 master-plan blocks match subplan status and notes.
- Process validation:
  - Perform one downstream update and verify master + subplan were both updated.
- Resume validation:
  - Use the resume protocol to identify and execute the next action without extra context.

## Risks and Mitigations

- Risk: ticket docs diverge from the master plan.
  - Mitigation: enforce dual-update rule on every ticket change.
- Risk: stale "next step" text blocks resumption.
  - Mitigation: require a single concrete next action and evidence marker in every update.
- Risk: governance overhead slows execution.
  - Mitigation: keep updates concise and focused on status/notes/next evidence.

## Change Log

- 2026-02-09: Initial subplan scaffold created and aligned with master-plan governance rules.
- 2026-02-09: First downstream governance cycle started through RPL-01 Step 1; immediate next action moved to RPL-01 Step 2 sync loop.
