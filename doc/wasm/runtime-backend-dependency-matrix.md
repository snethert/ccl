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
| X-01 | RPL-01 secure runtime gating | BPL-02 backend contract | soft_gate | BPL-02 drafting may start before RPL-01 completion. | RPL-01 capability check IDs frozen and referenced by BPL-02. | open | Align startup assumptions and backend capability assumptions. |
| X-02 | RPL-02 worker topology | BPL-03 frame/debug model | soft_gate | BPL-03 can draft debug model before worker model finalization. | RPL-02 worker ownership and boundary rules mapped into BPL-03. | open | Prevent debug model mismatch with runtime thread ownership. |
| X-03 | RPL-03 shared-memory IPC core | BPL-08 runtime alignment integration | hard_gate | BPL-08 integration cannot start without RPL-03 protocol v1. | RPL-03 wire protocol + conformance tests committed. | open | Required for backend/runtime call-boundary compatibility. |
| X-04 | RPL-04 runtime/UI shared path | BPL-06 dual-path diff harness | parallel | Diff harness work can proceed independently of UI transport migration. | Shared fixture format compatibility check at integration checkpoint. | open | No direct design block. |
| X-05 | RPL-05 storage V2 local core | BPL-04 numeric pipeline | parallel | Numeric backend work should continue while storage changes land. | None before each track’s own gates. | open | Distinct subsystems. |
| X-06 | RPL-07 module/environment sharing | BPL-07 size/perf gates | soft_gate | BPL-07 benchmarks can start with current packaging. | Final size budget signoff after RPL-07 packaging model freeze. | open | Avoid invalidating size gates due to packaging churn. |
| X-07 | RPL-08 artifact-size validation | BPL-07 size/perf gates | soft_gate | Both tracks can maintain independent interim budgets. | Unified budget sheet approved across both tracks. | open | Converges measurement methodology. |
| X-08 | RPL-09 runtime cutover/removal | BPL-09 backend cutover/retirement | hard_gate | Neither cutover should merge independently. | Joint cutover checklist + rollback rehearsals signed off. | open | Final release gate. |

## Parallel Work Packs

### Pack A (Immediate)

- Runtime: RPL-01 Step 2 onward (capability matrix, diagnostics contract).
- Backend: BPL-01 inventory and BPL-02 contract drafting.
- Constraint: clear `X-01` before contract freeze.

### Pack B (After contract freeze)

- Runtime: RPL-02/RPL-03.
- Backend: BPL-03/BPL-04/BPL-05.
- Constraint: clear `X-02` before BPL-03 finalization; clear `X-03` before BPL-08 start.

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

- Action: use this matrix to drive BPL-01 and RPL-01 Step 2 in parallel under `Pack A`.
- Why now: this is the highest parallelization window with the lowest cross-track blocking risk.
- Success evidence: both tracks show active progress while `X-01` status advances from `open` to `in_progress`.

## Change Log

- 2026-02-09: Initial cross-track dependency matrix created with dependency types and parallel work packs.
