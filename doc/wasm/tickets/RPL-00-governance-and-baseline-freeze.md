# RPL-00 - Governance and Baseline Freeze

Status: in_progress  
Priority: P0  
Owner: Runtime/WASM replacement track  
Last Updated: 2026-02-10  
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
- Thirty-second downstream execution cycle is now complete through RPL-08 Step 3 run-v2 evidence publication (`rpl08-20260210-023524Z-91fdb0be`) with synchronized ticket/master/matrix/board/governance edits, preserved immutable `X-07` review packet bundle IDs, unchanged backend `BPL08-CR*` carry-forward rows, and closed runtime blocker `R8GAP-01`.

## Immediate Next Step

- Action: continue the governance-compliant downstream update loop by syncing unified `X-07` closure review over committed runtime run-v2 evidence while preserving immutable closure-bundle carry-forward (`rpl05-20260210-011240Z-91fdb0be`, `bpl06-20260210-005408Z-91fdb0be`, `bpl07-20260210-005408Z-91fdb0be`) across review notes.
- Why now: RPL-08 Step 3 run-v2 evidence is committed with `x07_runtime_ready=true` and `R8GAP-01` closed; remaining work is cross-track closure disposition.
- Success evidence: synchronized runtime/master/matrix/board/governance docs carry run-v2 evidence (`rpl08-20260210-023524Z-91fdb0be`), preserve immutable bundle IDs and backend `BPL08-CR*` rows, and publish explicit `X-07` closure-review disposition without reopening gaps.

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
  - Downstream execution has now been repeated through RPL-08 Step 3 run-v2 evidence publication with synchronized updates, closed runtime blocker `R8GAP-01`, and immutable closure-bundle carry-forward into committed `X-07` review packets.
- Next:
  - Runtime ordering remains stable; maintain `X-06=done` and carry `X-07` forward while unified closure review consumes committed Step 3 run-v2 evidence.

### Step 5 - Governance Completion Check

- Status: done
- Notes:
  - Thirty-two downstream ticket cycles have now been completed using the required sync process.
  - RPL-08 Step 3 run-v2 evidence publication and immutable closure-bundle carry-forward are synchronized across runtime/backend planning docs while dependency rows `X-04`, `X-05`, and `X-06` are `done`, `R8GAP-01` is closed, and `X-07` remains in-progress pending unified closure review.
- Next:
  - Maintain governance as additive-only sync discipline for subsequent runtime/backend ticket cycles.

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
- 2026-02-09: Twelfth downstream governance cycle completed through RPL-03 Step 1 protocol publication and synchronized `X-03` advancement to `in_progress`.
- 2026-02-09: Thirteenth downstream governance cycle completed through RPL-03 Step 2 conformance-contract publication and synchronized runtime/master/matrix/board next-step state.
- 2026-02-09: Fourteenth downstream governance cycle completed through RPL-03 Step 3 run-v1 evidence publication (failing assertions) and synchronized rerun-focused next-step state across runtime/master/matrix/board docs.
- 2026-02-09: Fifteenth downstream governance cycle completed through RPL-03 Step 3 rerun evidence publication (`status=pass`, `x03_clear_ready=true`) and synchronized `X-03` closure across runtime/master/matrix/board docs.
- 2026-02-09: Sixteenth downstream governance cycle completed through RPL-04 Step 1 scope-contract publication (`R4M-*`, `R4C-*`, `R4T-*`) with synchronized runtime/master/matrix/board status and `X-04` advancement to `in_progress`.
- 2026-02-09: Seventeenth downstream governance cycle completed through RPL-04 Step 2 execution/gating publication (`R4L-*`, `R4V-*`, `R4I-*`) with synchronized runtime/master/matrix/board status and active `X-04` compatibility gating.
- 2026-02-09: Eighteenth downstream governance cycle completed through RPL-04 Step 3 run-v1 evidence publication (`rpl-04-step3-2026-02-09`) with synchronized runtime/master/matrix/board status and blocker gaps `R4GAP-01`..`R4GAP-04`.
- 2026-02-09: Nineteenth downstream governance cycle completed through Pack A cross-plan wording sync to `RPL-04 Step 3` + `BPL-07 Step 1` while preserving frozen `BPL06-*` intake anchors and active `X-04` blocker tracking.
- 2026-02-10: Twentieth downstream governance cycle completed through RPL-04 Step 3 rerun closure evidence publication (`rpl-04-step3-rerun-2026-02-10`) with synchronized runtime/master/matrix/board status and `X-04` transition to `done`.
- 2026-02-10: Twenty-first downstream governance cycle completed through RPL-05 Step 1 publication (`R5S-*`, `R5T-*`, `R5A-*`) with synchronized runtime/master/matrix/board status and Pack A backend wording held on BPL-07 Step 1 over frozen `BPL06-*` intake artifacts.
- 2026-02-10: Twenty-second downstream governance cycle completed through RPL-05 Step 2 publication (`R5L-*`, `R5V-*`) with synchronized runtime/master/matrix/board status and Pack A backend wording held on BPL-07 Step 1 over frozen `BPL06-*` intake artifacts.
- 2026-02-10: Resynced governance wording after backend BPL-07 Step 3 publication (`BPL07-CR01`..`BPL07-CR05`) by moving Pack A backend language to closure-remediation execution (`CR01`..`CR03`) over frozen `BPL06-*` intake artifacts.
- 2026-02-10: Twenty-third downstream governance cycle completed through RPL-05 Step 3 run-v1 evidence publication (`rpl05-20260210-004335Z-91fdb0be`) with synchronized runtime/master/matrix/board/governance status and explicit `R5GAP-01`..`R5GAP-05` blocker tracking.
- 2026-02-10: Twenty-fourth downstream governance cycle completed through RPL-05 Step 3 run-v2 closure evidence publication (`rpl05-20260210-011240Z-91fdb0be`) with synchronized runtime/master/matrix/board/governance status, closed `R5GAP-01`..`R5GAP-05`, and `X-05` transition to `done`.
- 2026-02-10: Twenty-fifth downstream governance cycle completed through RPL-07 Step 1 publication (`R7S-*`, `R7R-*`, `R7T-*`) with synchronized runtime/master/matrix/board/governance status, immutable closure-bundle carry-forward, and `X-06` transition to `in_progress`.
- 2026-02-10: Twenty-sixth downstream governance cycle completed through RPL-07 Step 2 publication (`R7L-*`, `R7V-*`, `R7I-*`) with synchronized runtime/master/matrix/board/governance status, immutable closure-bundle carry-forward, and Pack A runtime next action moved to `RPL-07 Step 3`.
- 2026-02-10: Twenty-seventh downstream governance cycle completed through RPL-07 Step 3 run-v1 evidence publication (`rpl07-20260210-013659Z-91fdb0be`) with synchronized runtime/master/matrix/board/governance status, immutable `X-06`/`X-07` review packet bundle IDs preserved, and blocker `R7GAP-01` opened for Step 3 run-v2 closure.
- 2026-02-10: Twenty-eighth downstream governance cycle completed through RPL-07 Step 3 run-v2 closure evidence publication (`rpl07-20260210-014654Z-91fdb0be`) with synchronized runtime/master/matrix/board/governance status, `R7GAP-01` closure, `X-06` transition to `done`, and immutable `X-06`/`X-07` review packet bundle IDs preserved.
- 2026-02-10: Twenty-ninth downstream governance cycle completed through RPL-08 Step 1 contract publication (`R8B-*`, `R8M-*`, `R8T-*`, `R8R-*`) with synchronized runtime/master/matrix/board/governance status, `X-07` transition to `in_progress`, immutable bundle IDs preserved, and backend `BPL08-CR*` carry-forward rows unchanged.
- 2026-02-10: Thirtieth downstream governance cycle completed through RPL-08 Step 2 contract publication (`R8L-*`, `R8V-*`, `R8I-*`) with synchronized runtime/master/matrix/board/governance status, `X-07` remaining `in_progress`, immutable bundle IDs preserved, and backend `BPL08-CR*` carry-forward rows unchanged.
- 2026-02-10: Thirty-first downstream governance cycle completed through RPL-08 Step 3 run-v1 evidence publication (`rpl08-20260210-022252Z-91fdb0be`) with synchronized runtime/master/matrix/board/governance status, terminal `artifact_budget_step2_summary_v1.status=pass`, open blocker `R8GAP-01`, immutable bundle IDs preserved, and backend `BPL08-CR*` carry-forward rows unchanged.
- 2026-02-10: Thirty-second downstream governance cycle completed through RPL-08 Step 3 run-v2 evidence publication (`rpl08-20260210-023524Z-91fdb0be`) with synchronized runtime/master/matrix/board/governance status, terminal `artifact_budget_step2_summary_v1.status=pass`, closed blocker `R8GAP-01`, immutable bundle IDs preserved, and backend `BPL08-CR*` carry-forward rows unchanged.
