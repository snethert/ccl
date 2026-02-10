# Runtime/Backend Dependency Matrix (Parallel Execution Control)

Status: Active  
Owner: WASM replacement program  
Last Updated: 2026-02-10  
Program Board: `doc/wasm/wasm-program-board.md`

## Purpose

This document defines cross-track dependencies between:

- runtime replacement tickets (`RPL-*`) and
- backend migration tickets (`BPL-*`).

It is the authoritative source for deciding which tasks can run in parallel and which require explicit synchronization.

## Dependency Types

- `parallel`: both tickets can execute independently; sync only at milestones.
- `soft_gate`: work can proceed in parallel, but output cannot be finalized until upstream evidence exists.
- `hard_gate`: downstream work must not start or merge until upstream evidence exists.

## Matrix

| ID | Runtime Ticket | Backend Ticket | Type | Parallel Rule | Required Evidence to Clear | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| X-01 | RPL-01 secure runtime gating | BPL-02 backend contract | soft_gate | BPL-02 drafting may start before RPL-01 completion. | RPL-01 capability check IDs frozen and referenced by BPL-02. | done | BPL-02 Step 1 linkage matrix references `SRG-01`..`SRG-12` explicitly (`BCL-01`..`BCL-12`), and Step 2 closure validated `CON-01`..`CON-08` coverage across all `BCL-*` rows. |
| X-02 | RPL-02 worker topology | BPL-03 frame/debug model | soft_gate | BPL-03 can draft debug model before worker model finalization. | RPL-02 worker ownership and lifecycle boundary rules mapped into BPL-03. | done | RPL-02 Step 3 published explicit cross-track mapping classes (`X03M-01`..`X03M-05`) that bind `WTOP-01`..`WTOP-05`, `WSEQ-01`..`WSEQ-06`, `WLCS-01`..`WLCS-06`, `WLCT-01`..`WLCT-11`, and `WLCR-01`..`WLCR-05` to BPL-03 consumption IDs (`B3R-*`, `B3S-*`, `B3L-*`, `B3T-*`, `B3P-*`). BPL-03 Step 1 mapping tables now include deterministic rules plus test-lane assertions per row, satisfying `X-02` clear evidence; BPL-01 Step 3 closure evidence for worker-sensitive assumptions (`ARM-ASSUMP-005`, `ARM-ASSUMP-006`, `ARM-ASSUMP-016`) remains unchanged. |
| X-03 | RPL-03 shared-memory IPC core | BPL-08 runtime alignment integration | hard_gate | BPL-08 integration cannot start without RPL-03 protocol v1. | RPL-03 wire protocol + conformance tests committed. | done | RPL-03 Step 3 rerun evidence is committed at `doc/wasm/tickets/evidence/rpl-03-step3-rerun-2026-02-09/` with terminal `ipc_conformance_summary_v1.status=pass` and `x03_clear_ready=true`; blocker gaps `IPCGAP-01`..`IPCGAP-04` are closed. |
| X-04 | RPL-04 runtime/UI shared path | BPL-06 dual-path diff harness | parallel | Diff harness work can proceed independently of UI transport migration. | Shared fixture format compatibility check at integration checkpoint. | done | RPL-04 Step 3 rerun evidence is committed (`doc/wasm/tickets/evidence/rpl-04-step3-rerun-2026-02-10/`) with full `R4V-01`..`R4V-14` coverage, closed blocker gaps `R4GAP-01`..`R4GAP-04`, and aggregate terminal `runtime_ui_bridge_step2_summary_v1.status=pass` (`x04_step2_ready=true`). Backend remediation run-v2 now records `CR01`..`CR03=pass` (`bpl06-20260210-005408Z-91fdb0be`, `bpl07-20260210-005408Z-91fdb0be`), so this row remains stable with no additional backend blocker semantics. |
| X-05 | RPL-05 storage V2 local core | BPL-04 numeric pipeline | parallel | Numeric backend work should continue while storage changes land. | None before each track’s own gates. | done | RPL-05 Step 3 run-v2 closure evidence is now committed (`doc/wasm/tickets/evidence/rpl-05-step3-2026-02-10/rpl05-20260210-011240Z-91fdb0be/`) with full `R5V-01`..`R5V-14` coverage, terminal `storage_v2_local_step2_summary_v1.status=pass`, `x05_step2_ready=true`, and explicit closure of `R5GAP-01`..`R5GAP-05`. |
| X-06 | RPL-07 module/environment sharing | BPL-07 size/perf gates | soft_gate | BPL-07 benchmarks can start with current packaging. | Final size budget signoff after RPL-07 packaging model freeze. | done | RPL-07 Step 3 run-v2 closure evidence is now committed (`doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/`) with full `R7V-01`..`R7V-14` command execution coverage, terminal `module_env_step2_summary_v1.status=pass` (`x06_step2_ready=true`), closed `R7GAP-01`, and committed `X-06`/`X-07` review packet artifacts preserving immutable bundle IDs (`rpl05-20260210-011240Z-91fdb0be`, `bpl06-20260210-005408Z-91fdb0be`, `bpl07-20260210-005408Z-91fdb0be`). |
| X-07 | RPL-08 artifact-size validation | BPL-07 size/perf gates | soft_gate | Both tracks can maintain independent interim budgets. | Unified budget sheet approved across both tracks. | in_progress | BPL-07 remediation run-v2 remains pass (`BPL07-BM05 perf_delta_pct=-0.560224%`, `<= +1.0%`) with backend preconditions for `CR05` satisfied; BPL-08 Step 3 closure rows (`BPL08-CR01`..`BPL08-CR06`) remain immutable carry-forward input, and runtime RPL-08 Step 3 run-v2 evidence is now committed (`rpl08-20260210-023524Z-91fdb0be`) with full `R8V-01`..`R8V-14` assertion pass coverage, terminal `artifact_budget_step2_summary_v1.status=pass`, `x07_runtime_ready=true`, and closed blocker `R8GAP-01`. |
| X-08 | RPL-09 runtime cutover/removal | BPL-09 backend cutover/retirement | hard_gate | Neither cutover should merge independently. | Joint cutover checklist + rollback rehearsals signed off. | open | Final release gate. |

## Parallel Work Packs

### Pack A (Immediate)

- Runtime: execute unified `X-07` closure review using committed run-v2 artifacts (`rpl08-20260210-023524Z-91fdb0be`) plus frozen Step 1/Step 2 contract IDs (`R8B-*`, `R8M-*`, `R8T-*`, `R8R-*`, `R8L-*`, `R8V-*`, `R8I-*`), closed `RPL-07` artifacts, and immutable closure bundles (`rpl05-20260210-011240Z-91fdb0be`, `bpl06-20260210-005408Z-91fdb0be`, `bpl07-20260210-005408Z-91fdb0be`) as `X-07` carry-forward inputs.
- Backend: `BPL-08 Step 3` closure-readiness packet is now published (`BPL08-CR01`..`BPL08-CR06`) over committed pass bundles (`bpl06-20260210-005408Z-91fdb0be`, `bpl07-20260210-005408Z-91fdb0be`); maintain this packet as immutable carry-forward input while runtime evidence is finalized.
- Constraint: keep `SRG-*`, `WTOP-*`, `WSEQ-*`, `WLCS-*`, `WLCT-*`, `WLCR-*`, `B3*`, and `FDC-*` identifiers frozen; no fallback semantics may be reintroduced.

### Pack B (After contract freeze)

- Runtime: RPL-06.
- Backend: BPL-03/BPL-04/BPL-05.
- Constraint: keep `X-02` and closed `X-03` evidence stable while BPL-04/BPL-05 implementation planning advances.

### Pack C (Validation-heavy)

- Runtime: RPL-07/RPL-08.
- Backend: BPL-06/BPL-07.
- Constraint: clear `X-06` and `X-07` before final budget signoff.

### Pack D (Cutover)

- Runtime: RPL-09.
- Backend: BPL-09.
- Constraint: clear `X-08` before release cutover.

## Update Rules

1. Any change to a dependency row must update both affected master plans in the same change.
2. `Status` for each row must be one of `open`, `in_progress`, `done`, `cancelled`.
3. `Required Evidence to Clear` must stay concrete and testable; avoid vague language.

## Immediate Next Step

- Action: continue `Pack A` by executing unified `X-07` closure review over committed runtime run-v2 evidence and immutable backend `BPL-08 Step 3` closure rows.
- Why now: runtime Step 3 run-v2 is committed (`rpl08-20260210-023524Z-91fdb0be`) with `R8GAP-01` closed and `x07_runtime_ready=true`; remaining work is cross-track closure decisioning.
- Success evidence: synchronized runtime/backend planning docs preserve immutable bundle IDs and backend `BPL08-CR*` rows, carry committed run-v2 artifacts, and publish explicit `X-07` closure-review disposition without reopening runtime gaps.

## Change Log

- 2026-02-09: Initial cross-track dependency matrix created with dependency types and parallel work packs.
- 2026-02-09: Updated `X-01` to `in_progress` after RPL-01 Step 2 froze startup check IDs (`SRG-01`..`SRG-12`).
- 2026-02-09: Updated Pack A immediate action to include RPL-01 Step 4 after Step 3 diagnostics contract completion.
- 2026-02-09: Updated Pack A immediate action to include RPL-01 Step 5 after Step 4 integration-plan completion.
- 2026-02-09: Updated Pack A immediate action to include RPL-01 Step 6 after Step 5 validation-gate completion.
- 2026-02-09: Updated Pack A immediate action to post-handoff `X-01` closure and RPL-02 Step 1 kickoff after Step 6 completion.
- 2026-02-09: Updated `X-01`/`X-02` notes with BPL-01 inventory v1 evidence and moved Pack A backend focus from Step 1 capture to Step 2 strategy closure.
- 2026-02-09: Cleared `X-01` as `done` after BPL-02 published explicit `SRG-01`..`SRG-12` linkage (`BCL-01`..`BCL-12`) and advanced Pack A focus to RPL-02/BPL-02 Step 2 outputs.
- 2026-02-09: Advanced `X-02` to `in_progress` after RPL-02 Step 1 published `WTOP-01`..`WTOP-05`, `WSEQ-01`..`WSEQ-06`, and `worker_topology_ready_v1`; moved Pack A runtime focus to RPL-02 Step 2 lifecycle contract work.
- 2026-02-09: Refreshed `X-02` notes with BPL-01 rescan evidence for worker-sensitive ARM assumptions (`ARM-ASSUMP-005`, `ARM-ASSUMP-006`, `ARM-ASSUMP-016`).
- 2026-02-09: Updated Pack A backend focus from BPL-01 Step 2 to BPL-01 Step 3 after Step 2 closure completed for all non-`remove` assumptions.
- 2026-02-09: Synced RPL-02 Step 2 completion by adding lifecycle evidence (`WLCS-*`, `WLCT-*`, `WLCR-*`, `X02R-04`..`X02R-06`) to `X-02` and moving Pack A runtime focus to RPL-02 Step 3 mapping work.
- 2026-02-09: Synced BPL-01 Step 3 closure by updating `X-02` notes (no new non-speculative dependency rows) and moving Pack A backend focus to BPL-02 Step 2 plus BPL-03 drafting.
- 2026-02-09: Synced BPL-02 Step 2 closure by updating `X-01` notes with `CON`/`BCL` coverage evidence and moving Pack A backend focus fully to BPL-03 mapping consumption.
- 2026-02-09: Cleared `X-02` as `done` after RPL-02 Step 3 published `X03M-01`..`X03M-05` and BPL-03 Step 1 mapped all required runtime ID classes through explicit `B3*` consumption tables.
- 2026-02-09: Updated Pack A backend focus from BPL-03 Step 2 drafting to Step 2 closure validation after publishing `FDC-01`..`FDC-10` draft invariants.
- 2026-02-09: Updated Pack A backend focus from BPL-03 Step 2 closure validation to BPL-04 Step 1 classification after BPL-03 Step 2 was marked done.
- 2026-02-09: Advanced `X-03` to `in_progress` after RPL-03 Step 1 published shared-memory IPC protocol v1 (`IPCP-01`..`IPCP-49`); Pack A runtime focus now shifts to Step 2 conformance evidence (`IPCV-*`) required to clear the hard gate.
- 2026-02-09: Advanced Pack A backend focus from BPL-04 Step 1 to BPL-04 Step 2 after Step 1 published `M4F-01`..`M4F-08` operation-family classification.
- 2026-02-09: Published RPL-03 Step 2 conformance contract (`IPCV-01`..`IPCV-12`, `IPCL-01`..`IPCL-05`, `ipc_conformance_summary_v1`) and advanced Pack A runtime focus to Step 3 committed evidence execution for `X-03` closure.
- 2026-02-09: Executed RPL-03 Step 3 run-v1 (`IPCV-01`..`IPCV-12`) and committed evidence bundle with `status=fail`; Pack A runtime focus now shifts to closing `IPCGAP-01`..`IPCGAP-04` and rerunning conformance for `X-03` closure.
- 2026-02-09: Advanced Pack A backend focus from BPL-04 Step 2 sequencing to BPL-04 Step 3 benchmark/profile gate alignment after publishing ordered non-`native_now` family sequence gates (`BPL04-S2-*`).
- 2026-02-09: Advanced Pack A backend focus from BPL-04 Step 3 gate alignment to BPL-05 Step 1 staged decoupling after BPL-04 published `BPL04-G01`..`BPL04-G06`.
- 2026-02-09: Advanced Pack A backend focus from BPL-05 Step 1 staging to BPL-05 Step 2 seam contracts after publishing staged decoupling slices (`B5S-01`..`B5S-05`).
- 2026-02-09: Advanced Pack A backend focus from BPL-05 Step 2 seam contracts to BPL-05 Step 3 handoff/gate integration after publishing seam matrix (`B5M-01`..`B5M-05`).
- 2026-02-09: Closed `X-03` after RPL-03 Step 3 rerun evidence (`doc/wasm/tickets/evidence/rpl-03-step3-rerun-2026-02-09/`) reported `status=pass`, `x03_clear_ready=true`, and explicit closure of `IPCGAP-01`..`IPCGAP-04`.
- 2026-02-09: Advanced Pack A backend focus from BPL-05 Step 3 handoff/gate integration to BPL-06 Step 1 harness contract definition after publishing handoff checklist (`B5H-01`..`B5H-05`).
- 2026-02-09: Advanced Pack A backend focus from BPL-06 Step 1 harness contract definition to BPL-06 Step 2 fixture/evidence-template publication after freezing `BPL06-CP01`..`BPL06-CP05` checkpoint contracts.
- 2026-02-09: Advanced Pack A backend focus from BPL-06 Step 2 fixture/evidence-template publication to BPL-06 Step 3 triage/gate-integration definition after publishing fixture matrix (`BPL06-FX01`..`BPL06-FX05`) and template files.
- 2026-02-09: Advanced Pack A backend focus from BPL-06 Step 3 triage/gate-integration to BPL-07 Step 1 budget/measurement setup after publishing severity/rollback/intake baselines (`BPL06-SEV-*`, `BPL06-RB-*`, `BPL06-INT-*`).
- 2026-02-09: Published RPL-04 Step 1 scope contract (`R4M-*`, `R4C-*`, `R4T-*`), advanced `X-04` to `in_progress`, and synchronized Pack A immediate action to RPL-04 Step 2 plus BPL-06 Step 3 compatibility intake completion.
- 2026-02-09: Published RPL-04 Step 2 execution/gating contract (`R4L-*`, `R4V-*`, `R4I-*`) and synchronized Pack A immediate action to RPL-04 Step 3 committed evidence runs plus BPL-06 Step 3 compatibility intake completion.
- 2026-02-09: Published RPL-04 Step 3 run-v1 evidence (`rpl-04-step3-2026-02-09`) and synchronized Pack A immediate action to Step 3 gap-remediation rerun after opening blocker gaps `R4GAP-01`..`R4GAP-04`.
- 2026-02-09: Resynced Pack A backend-parallel wording to BPL-07 Step 1 (BPL-06 already closed) while keeping `X-04` `in_progress` and frozen `BPL06-*` intake contracts as compatibility baseline.
- 2026-02-10: Closed `X-04` after RPL-04 Step 3 rerun evidence (`doc/wasm/tickets/evidence/rpl-04-step3-rerun-2026-02-10/`) reported full `R4V-01`..`R4V-14` assertion pass coverage, terminal `runtime_ui_bridge_step2_summary_v1.status=pass`, and explicit closure of `R4GAP-01`..`R4GAP-04`.
- 2026-02-10: Advanced Pack A runtime focus from closed RPL-04 bridge migration to RPL-05 Step 1 local-core schema/transaction definition while backend remains on BPL-07 Step 1.
- 2026-02-10: Synced BPL-07 Step 1 publication (`BPL07-BM01`..`BPL07-BM05`) by advancing Pack A backend focus to BPL-07 Step 2 run-v1 measurement execution and refreshing `X-04`/`X-06`/`X-07` notes without changing dependency semantics.
- 2026-02-10: Executed RPL-05 Step 1 publication (`R5S-*`, `R5T-*`, `R5A-*`) and resynced Pack A to runtime `RPL-05 Step 2` plus backend continuation on `BPL-07 Step 1`, preserving frozen `BPL06-*` intake references.
- 2026-02-10: Executed BPL-07 Step 2 run-v1 measurement packet (`bpl07-20260210-002604Z-91fdb0be`) and advanced Pack A backend focus to BPL-07 Step 3 readiness; `X-06`/`X-07` notes now record intake-artifact-missing blockers plus `BPL07-BM05` perf overrun.
- 2026-02-10: Executed RPL-05 Step 2 publication (`R5L-*`, `R5V-*`) and resynced Pack A to runtime `RPL-05 Step 3` plus backend continuation on `BPL-07 Step 1`, with `X-05` advanced to `in_progress` and frozen `BPL06-*` intake references preserved.
- 2026-02-10: Published BPL-07 Step 3 closure-readiness criteria (`BPL07-CR01`..`BPL07-CR05`), updated `X-06`/`X-07` notes to criteria-backed blocker language, and advanced Pack A backend focus to one closure-remediation execution packet (`CR01`..`CR03`).
- 2026-02-10: Synced `X-05` and Pack A runtime wording to RPL-05 Step 3 run-v1 evidence (`rpl05-20260210-004335Z-91fdb0be`), recording blocker gaps `R5GAP-01`..`R5GAP-05` and advancing immediate runtime action to Step 3 gap-remediation rerun (`run-v2`).
- 2026-02-10: Executed backend remediation run-v2 (`bpl06-20260210-005408Z-91fdb0be`, `bpl07-20260210-005408Z-91fdb0be`) and updated `X-06`/`X-07` notes to backend-ready posture (`CR01`..`CR03=pass`) while keeping runtime-side signoff evidence as the only remaining closure condition.
- 2026-02-10: Executed RPL-05 Step 3 run-v2 (`rpl05-20260210-011240Z-91fdb0be`), closed `R5GAP-01`..`R5GAP-05`, advanced `X-05` to `done`, and shifted Pack A runtime focus to `RPL-07 Step 1` with backend pass bundle carry-forward for `X-06`/`X-07`.
- 2026-02-10: Executed RPL-07 Step 1 by publishing frozen module-environment sharing contract IDs (`R7S-*`, `R7R-*`, `R7T-*`), advanced `X-06` to `in_progress`, and shifted Pack A runtime focus to `RPL-07 Step 2` while preserving immutable closure-bundle carry-forward for `X-06`/`X-07`.
- 2026-02-10: Executed RPL-07 Step 2 by publishing frozen lane/validation/review contracts (`R7L-*`, `R7V-*`, `R7I-*`), preserved immutable closure-bundle IDs in `X-06`/`X-07` review mappings, and shifted Pack A runtime focus to `RPL-07 Step 3` evidence execution.
- 2026-02-10: Executed RPL-07 Step 3 run-v1 (`rpl07-20260210-013659Z-91fdb0be`) with committed `X-06`/`X-07` review packets preserving immutable bundle IDs; recorded open blocker `R7GAP-01` (`R7V-06` digest parity drift) and shifted Pack A runtime focus to Step 3 run-v2 targeted closure.
- 2026-02-10: Executed RPL-07 Step 3 run-v2 (`rpl07-20260210-014654Z-91fdb0be`) with terminal `module_env_step2_summary_v1.status=pass`, closed `R7GAP-01`, advanced `X-06` to `done`, and shifted Pack A runtime focus to `RPL-08 Step 1` while preserving immutable `X-07` carry-forward bundle IDs.
- 2026-02-10: Synced Pack A backend-parallel wording after BPL-08 Step 2 publication (`BPL08-IV01`..`BPL08-IV06`) and advanced backend next action to BPL-08 Step 3 closure-readiness packetization while preserving immutable `X-07` carry-forward bundles.
- 2026-02-10: Synced matrix state after BPL-08 Step 3 publication (`BPL08-CR01`..`BPL08-CR06`) by preserving explicit `X-07=open` carry-forward posture and immutable bundle IDs while runtime `RPL-08 Step 1` remains the active closure path.
- 2026-02-10: Executed RPL-08 Step 1 by publishing frozen runtime budget/measurement contract IDs (`R8B-*`, `R8M-*`, `R8T-*`, `R8R-*`), advanced `X-07` to `in_progress`, and shifted Pack A runtime focus to `RPL-08 Step 2` while preserving immutable bundle IDs and backend `BPL08-CR*` carry-forward rows unchanged.
- 2026-02-10: Executed RPL-08 Step 2 by publishing frozen runtime lane/validation/review contract IDs (`R8L-*`, `R8V-*`, `R8I-*`), kept `X-07` at `in_progress`, and shifted Pack A runtime focus to `RPL-08 Step 3` run-v1 evidence execution while preserving immutable bundle IDs and backend `BPL08-CR*` carry-forward rows unchanged.
- 2026-02-10: Executed RPL-08 Step 3 run-v1 (`R8V-01`..`R8V-14`) with committed evidence bundle (`rpl08-20260210-022252Z-91fdb0be`), terminal `artifact_budget_step2_summary_v1.status=pass`, open blocker `R8GAP-01` for `R8B-01`/`R8B-02`/`R8B-05` closure-target overruns, and shifted Pack A runtime focus to Step 3 run-v2 targeted closure while preserving immutable bundle IDs and backend `BPL08-CR*` carry-forward rows unchanged.
- 2026-02-10: Executed RPL-08 Step 3 run-v2 (`R8V-01`..`R8V-14`) with committed evidence bundle (`rpl08-20260210-023524Z-91fdb0be`), terminal `artifact_budget_step2_summary_v1.status=pass`, closed `R8GAP-01`, recorded `x07_runtime_ready=true`, and shifted Pack A runtime focus from rerun remediation to unified `X-07` closure review while preserving immutable bundle IDs and backend `BPL08-CR*` carry-forward rows unchanged.
