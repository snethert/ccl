# Runtime/Backend Dependency Matrix (Parallel Execution Control)

Status: Active  
Owner: WASM replacement program  
Last Updated: 2026-02-09  
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
| X-04 | RPL-04 runtime/UI shared path | BPL-06 dual-path diff harness | parallel | Diff harness work can proceed independently of UI transport migration. | Shared fixture format compatibility check at integration checkpoint. | open | No direct design block. |
| X-05 | RPL-05 storage V2 local core | BPL-04 numeric pipeline | parallel | Numeric backend work should continue while storage changes land. | None before each track’s own gates. | open | Distinct subsystems. |
| X-06 | RPL-07 module/environment sharing | BPL-07 size/perf gates | soft_gate | BPL-07 benchmarks can start with current packaging. | Final size budget signoff after RPL-07 packaging model freeze. | open | Avoid invalidating size gates due to packaging churn. |
| X-07 | RPL-08 artifact-size validation | BPL-07 size/perf gates | soft_gate | Both tracks can maintain independent interim budgets. | Unified budget sheet approved across both tracks. | open | Converges measurement methodology. |
| X-08 | RPL-09 runtime cutover/removal | BPL-09 backend cutover/retirement | hard_gate | Neither cutover should merge independently. | Joint cutover checklist + rollback rehearsals signed off. | open | Final release gate. |

## Parallel Work Packs

### Pack A (Immediate)

- Runtime: RPL-04 Step 1 startup scope for shared bridge-path migration, consuming frozen RPL-03 protocol/conformance outputs.
- Backend: BPL-05 Step 3 consumer handoff/gate integration over closed slice/seam artifacts (`B5S-*`, `B5M-*`).
- Constraint: keep `SRG-*`, `WTOP-*`, `WSEQ-*`, `WLCS-*`, `WLCT-*`, `WLCR-*`, `B3*`, and `FDC-*` identifiers frozen; no fallback semantics may be reintroduced.

### Pack B (After contract freeze)

- Runtime: RPL-04.
- Backend: BPL-03/BPL-04/BPL-05.
- Constraint: keep `X-02` and closed `X-03` evidence stable while BPL-04/BPL-05 implementation planning advances.

### Pack C (Validation-heavy)

- Runtime: RPL-04/RPL-05/RPL-07/RPL-08.
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

- Action: continue `Pack A` by executing RPL-04 Step 1 bridge-path scope definition alongside BPL-05 Step 3 consumer handoff/gate integration.
- Why now: `X-03` is now closed with committed rerun evidence, so the next unblocked cross-track actions are bridge migration scoping and backend consumer handoff contracts.
- Success evidence: RPL-04 Step 1 publishes frozen migration-scope IDs and BPL-05 Step 3 publishes consumer acceptance checklist over `B5S-*`/`B5M-*` artifacts.

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
