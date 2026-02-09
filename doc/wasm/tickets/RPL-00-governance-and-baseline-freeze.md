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
- Eleventh downstream execution cycle is now complete through RPL-02 Step 3 cross-track mapping publication with synchronized ticket/master/matrix edits and `X-02` closure.

## Immediate Next Step

- Action: continue the governance-compliant downstream update loop by executing RPL-03 Step 1 and syncing runtime master + dependency matrix in one change.
- Why now: `X-02` is cleared, so the next governance-critical dependency checkpoint is protocol progress on `X-03`.
- Success evidence: RPL-03 Step 1 status/notes and `X-03` evidence requirements are reflected consistently across subplan/master/matrix docs.

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
  - Downstream execution has now been repeated through RPL-02 Step 3 with synchronized updates.
- Next:
  - No ordering issues were observed through RPL-02 Step 3; reassess only if RPL-03 Step 1 sync uncovers regressions.

### Step 5 - Governance Completion Check

- Status: in_progress
- Notes:
  - Eleven downstream ticket cycles have now been completed using the required sync process.
  - RPL-02 Step 3 mapping evidence is now synchronized across runtime/backend planning docs and dependency row `X-02` is cleared.
- Next:
  - Reassess closure after one additional downstream cycle (RPL-03 Step 1) verifies smooth post-`X-02` protocol-handoff execution.

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
- 2026-02-09: Second downstream governance cycle completed through RPL-01 Step 2; immediate next action moved to RPL-01 Step 3 sync loop.
- 2026-02-09: Third downstream governance cycle completed through RPL-01 Step 3; immediate next action moved to RPL-01 Step 4 sync loop.
- 2026-02-09: Fourth downstream governance cycle completed through RPL-01 Step 4; immediate next action moved to RPL-01 Step 5 sync loop.
- 2026-02-09: Fifth downstream governance cycle completed through RPL-01 Step 5; immediate next action moved to RPL-01 Step 6 sync loop.
- 2026-02-09: Sixth downstream governance cycle completed through RPL-01 Step 6; immediate next action moved to post-handoff `X-01` closure sync.
- 2026-02-09: Seventh downstream governance cycle completed through post-handoff `X-01` closure; immediate next action moved to RPL-02 Step 1 sync loop.
- 2026-02-09: Eighth and ninth downstream governance cycles completed through RPL-02 Step 1 publication and `X-02` advancement to `in_progress`.
- 2026-02-09: Tenth downstream governance cycle completed through RPL-02 Step 2 lifecycle/no-fallback contract publication and synchronized master/matrix notes.
- 2026-02-09: Eleventh downstream governance cycle completed through RPL-02 Step 3 mapping publication and synchronized `X-02` closure across subplan/master/matrix docs.
