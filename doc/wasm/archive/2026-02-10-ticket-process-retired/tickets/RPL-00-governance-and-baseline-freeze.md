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
4. Unattended runtime execution playbook with deterministic reopen/sync/evidence rules.
5. RPL documentation completeness audit with remediations.

## Exit Criteria

- RPL-00 and RPL-01 subplans exist and are linked from the master plan.
- Master plan contains no "subplan not yet authored" note for RPL-00 and RPL-01.
- Update and resume rules are documented and executable without additional context.
- At least one downstream ticket update follows the documented sync process.
- Long-run unattended execution protocol is documented as a single canonical runtime reference.
- Ticket template requirements enforce deterministic command/evidence details for future tickets.

## Current Notes

- Master plan is present at `doc/wasm/runtime-replacement-master-plan.md`.
- Ticket template and folder sync rules are present under `doc/wasm/tickets/`.
- Baseline runtime status and artifact-size facts are captured in the master plan snapshot.
- Fortieth downstream execution cycle is now complete as additive-only maintenance over immutable `X-08` and `RPL-06` artifacts while preserving backend Step 3 run-v2 evidence (`bpl09-20260210-040314Z-2084077e`) plus unified `X-08` closure review (`x08-closure-20260210-040400Z-2084077e`) and runtime Step 3 run-v1 evidence (`rpl06-20260210-054023Z-50d752af`) without drift.
- Backend migration closure scope is complete (`BPL-01`..`BPL-10`, `X-08=done`), so backend docs are now frozen by default while runtime/project docs carry active updates.
- Unattended runtime execution playbook is now published at `doc/wasm/rpl-unattended-execution-playbook.md`.
- RPL documentation completeness audit is now published at `doc/wasm/rpl-doc-completeness-audit-2026-02-10.md`.

## Immediate Next Step

- Action: execute the first post-audit unattended runtime cycle using the playbook and keep backend docs frozen unless backend scope is explicitly reopened.
- Why now: structural ticket completeness is in place; remaining risk is operational drift during long unattended execution.
- Success evidence: one runtime governance cycle is published with single-action execution, mode-complete sync state (same-change updates in standard mode or explicit deferred queue coverage in single-document override mode), and explicit evidence mapping under the new protocol.

## Unattended Execution Packet (Required)

- Primary lane: runtime governance synchronization (`RPL-00` + runtime master, optional matrix/program updates).
- Preconditions:
  - `doc/wasm/rpl-unattended-execution-playbook.md` is treated as authoritative protocol.
  - Active runtime state is read from `doc/wasm/runtime-replacement-master-plan.md` ticket board.
- Deterministic validation commands/IDs:
  - `rg -n \"rpl-unattended-execution-playbook|rpl-doc-completeness-audit-2026-02-10\" doc/wasm/runtime-replacement-master-plan.md doc/wasm/tickets/RPL-00-governance-and-baseline-freeze.md doc/wasm/tickets/README.md`
  - `rg -n \"## Unattended Execution Packet \\(Required\\)|## Done-Ticket Reopen Contract\" doc/wasm/tickets/TICKET-SUBPLAN-TEMPLATE.md`
- Expected evidence output paths:
  - Doc-diff evidence showing required sync completion for the active mode:
    - standard mode: same-change update touching `RPL-00` + runtime master (and matrix/program when required);
    - single-document override mode: one-doc change plus explicit deferred queue items for skipped sync targets.
- Terminal summary artifact/check:
  - Runtime governance update includes one single-action next step with explicit success evidence.
- Blocker/gap handling rule:
  - Record governance blocker in `Current Notes` and keep `Status=in_progress` until sync set is complete.

## Done-Ticket Reopen Contract

- Reopen trigger(s):
  - New runtime work requires changes that cannot be represented as additive governance-only maintenance.
  - Work clearly belongs to the existing ticket scope.
- Required status transition:
  - Set ticket `Status` from `done` to `in_progress` with dated reopen note and new step slice.
- Required sync update set:
  - `doc/wasm/tickets/<ticket>.md`
  - `doc/wasm/runtime-replacement-master-plan.md`
  - `doc/wasm/runtime-backend-dependency-matrix.md` and `doc/wasm/wasm-program-board.md` if dependency semantics change.

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
  - Sync rules are now mode-aware: standard mode requires same-change master+subplan updates, while single-document override mode requires explicit deferred queue coverage for skipped required targets.
- Next:
  - Apply mode-aware sync completion process on each ticket update without exception.

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
  - Downstream execution has now been repeated through unified `X-07` closure review with synchronized updates, closed runtime blocker `R8GAP-01`, and immutable bundle carry-forward preserved across committed review artifacts.
- Next:
  - Runtime ordering remains stable; keep `X-06`/`X-07`/`X-08` closed and preserve cutover artifacts while runtime contradiction follow-through proceeds.

### Step 5 - Governance Completion Check

- Status: done
- Notes:
  - Forty downstream ticket cycles have now been completed using the required sync process.
  - Unified closure reviews for `X-07` and `X-08` are synchronized across runtime/backend planning docs while dependency rows `X-04`, `X-05`, `X-06`, `X-07`, and `X-08` are `done`.
- Next:
  - Maintain governance as additive-only sync discipline for subsequent runtime/backend ticket cycles.

### Step 6 - Unattended Execution Hardening

- Status: done
- Notes:
  - Published `doc/wasm/rpl-unattended-execution-playbook.md` with deterministic ticket selection, reopen protocol, evidence conventions, blocker handling, and required sync set.
  - Published `doc/wasm/rpl-doc-completeness-audit-2026-02-10.md` to record structural pass results and operational remediations.
  - Updated ticket template and ticket README so future runtime tickets stay unattended-operable by default.
- Next:
  - Execute governance cycles against the playbook and refine additively if new unattended failure classes appear.

## Test and Validation Plan

- Documentation integrity:
  - Confirm all referenced subplan paths exist.
  - Confirm RPL-00 and RPL-01 master-plan blocks match subplan status and notes.
- Process validation:
  - Perform one downstream update and verify sync completion for the active mode.
- Resume validation:
  - Use the resume protocol to identify and execute the next action without extra context.
- Unattended protocol validation:
  - Verify `doc/wasm/tickets/TICKET-SUBPLAN-TEMPLATE.md` includes deterministic execution packet fields.
  - Verify runtime master references `doc/wasm/rpl-unattended-execution-playbook.md` as normative protocol.

## Risks and Mitigations

- Risk: ticket docs diverge from the master plan.
  - Mitigation: enforce mode-aware sync completion on every ticket change (same-change dual update in standard mode or explicit deferred queue coverage in single-document override mode).
- Risk: stale "next step" text blocks resumption.
  - Mitigation: require a single concrete next action and evidence marker in every update.
- Risk: governance overhead slows execution.
  - Mitigation: keep updates concise and focused on status/notes/next evidence.
- Risk: long unattended runs reopen closed tickets inconsistently.
  - Mitigation: require explicit done-ticket reopen criteria and mirrored status/evidence updates in master + subplan.

## Change Log

- 2026-02-10: Aligned RPL-00 governance success/evidence/validation language
  with playbook single-document override semantics and mode-aware sync
  completion.
- 2026-02-10: Published unattended execution hardening artifacts (`rpl-unattended-execution-playbook`, completeness audit) and extended runtime ticket template requirements for long autonomous cycles.
- 2026-02-10: Added post-closure governance note that backend migration docs are frozen by default after full BPL closure and active status flow continues in runtime/project docs.
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
- 2026-02-10: Thirty-third downstream governance cycle completed through unified `X-07` closure review (`x07-closure-20260210-024503Z-91fdb0be`) with synchronized runtime/master/matrix/board/governance status, dependency row `X-07` advanced to `done`, immutable bundle IDs preserved, and immediate next action shifted to `RPL-09 Step 1`.
- 2026-02-10: Thirty-fourth downstream governance cycle completed through `RPL-09 Step 1` publication (`R9G-01`..`R9G-08`, `R9R-01`..`R9R-06`, `R9E-01`..`R9E-06`) with synchronized runtime/master/matrix/board/governance updates and immediate next action shifted to `RPL-09 Step 2`.
- 2026-02-10: Resynced governance wording after backend `BPL-09 Step 1` publication (`BPL09-G*`, `BPL09-R*`, `BPL09-E*`) so immediate cross-track action is runtime/backend parallel `Step 2` rehearsal packet definition under active `X-08`.
- 2026-02-10: Thirty-fifth downstream governance cycle completed through `RPL-09 Step 2` publication (`R9L-01`..`R9L-08`, `R9V-01`..`R9V-14`, `R9I-01`..`R9I-06`) with synchronized runtime/master/matrix/board/governance updates and immediate next action shifted to runtime `RPL-09 Step 3` run-v1 evidence while backend continues `BPL-09 Step 2`.
- 2026-02-10: Thirty-sixth downstream governance cycle completed through `RPL-09 Step 3` run-v1 evidence publication (`rpl09-20260210-032127Z-2084077e`) with synchronized runtime/master/matrix/board/governance updates, terminal runtime summary pass (`x08_runtime_step2_ready=true`), and open blocker `R9GAP-01` while backend `BPL-09 Step 2` remains pending.
- 2026-02-10: Resynced governance wording after backend `BPL-09 Step 2` publication (`BPL09-L*`, `BPL09-V*`, `BPL09-I*`) so immediate cross-track action is runtime `RPL-09 Step 3` run-v2 closure of `R9GAP-01` in parallel with backend Step 3 signoff packet publication.
- 2026-02-10: Resynced governance wording after backend `BPL-09 Step 3` publication (`BPL09-CR01`..`BPL09-CR06`) so immediate cross-track action is runtime run-v2 closure of `R9GAP-01` plus joint `X-08` review execution over published signoff rows.
- 2026-02-10: Thirty-seventh downstream governance cycle completed through `RPL-09 Step 3` run-v2 closure evidence publication (`rpl09-20260210-034952Z-2084077e`) with synchronized runtime/master/matrix/board/governance updates, closed `R9GAP-01`, committed `x08_joint_intake_review_v1.status=pass`, and immediate next action shifted to final joint `X-08` closure-review dossier assembly.
- 2026-02-10: Thirty-eighth downstream governance cycle completed through backend Step 3 run-v2 evidence (`bpl09-20260210-040314Z-2084077e`) and unified `X-08` closure review (`x08-closure-20260210-040400Z-2084077e`) with synchronized runtime/master/matrix/board/governance updates, row `X-08` advanced to `done`, and immediate next action shifted to runtime `RPL-01` contradiction follow-through.
- 2026-02-10: Decomposed runtime contradiction follow-through into ordered `RPL01-CF-*` tasks and advanced the immediate governance action to `RPL01-CF-01` (`C-01`) while preserving immutable `X-08` artifacts.
- 2026-02-10: Completed contradiction queue block `RPL01-CF-01`..`RPL01-CF-04` and advanced immediate governance action to `RPL01-CF-05` (`C-02`) while preserving immutable `X-08` artifacts.
- 2026-02-10: Completed `RPL01-CF-05` (`C-02`) and advanced immediate governance action to `RPL01-CF-06` (`C-05`) while preserving immutable `X-08` artifacts.
- 2026-02-10: Completed `RPL01-CF-06` (`C-05`) and advanced immediate governance action to `RPL01-CF-07` (`C-06`) while preserving immutable `X-08` artifacts.
- 2026-02-10: Completed contradiction queue block `RPL01-CF-07`..`RPL01-CF-14` (`C-06`..`C-14`) and advanced immediate governance action to `RPL01-CF-15` contradiction-closure synchronization while preserving immutable `X-08` artifacts.
- 2026-02-10: Completed `RPL01-CF-15` contradiction-closure synchronization and advanced immediate governance action to `RPL01-IG-01` startup-gate loader/smoke integration while preserving immutable `X-08` artifacts.
- 2026-02-10: Completed `RPL01-IG-01` startup-gate loader/smoke integration (`LHI-01`/`LHI-02`/`LHI-03`) and advanced immediate governance action to `RPL01-IG-02` (`LHI-04`/`LHI-05`/`LHI-06`) while preserving immutable `X-08` artifacts.
- 2026-02-10: Completed `RPL01-IG-02` browser-lane closure and published `RPL-06` Step 1 sync/merge contract (`R6S-*`, `R6T-*`, `R6A-*`); immediate governance action now advances to `RPL-06` Step 2 lane/validation matrix drafting while preserving immutable `X-08` artifacts.
- 2026-02-10: Published `RPL-06` Step 2 lane/validation matrix (`R6L-*`, `R6V-*`) and terminal schema `storage_v2_sync_step2_summary_v1`; immediate governance action now advances to `RPL-06` Step 3 evidence execution while preserving immutable `X-08` artifacts.
- 2026-02-10: Thirty-ninth downstream governance cycle completed through `RPL-06` Step 3 run-v1 closure evidence (`rpl06-20260210-054023Z-50d752af`) with synchronized runtime/backend governance wording and immutable `X-08` artifact preservation.
- 2026-02-10: Fortieth downstream governance cycle completed as additive-only maintenance by validating no drift across immutable `X-08`/`RPL-06` artifacts and synchronized runtime/backend/program governance wording.
