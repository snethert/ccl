# WASM Program Board (Runtime Replacement + Backend Migration)

Status: Active  
Owner: WASM replacement program  
Last Updated: 2026-02-10

## Purpose

This document is the top-level coordination index for the two major parallel tracks:

- Runtime replacement (secure-only runtime architecture and Storage V2 migration).
- ARM-facade retirement via a WASM-native backend migration.

This is intentionally not a megaplan. Execution remains in two track-specific master plans with explicit synchronization gates.

## Canonical Plans

- Runtime track: `doc/wasm/runtime-replacement-master-plan.md`
- Backend track: `doc/wasm/backend-migration-master-plan.md`
- Cross-track matrix: `doc/wasm/runtime-backend-dependency-matrix.md`

## Program Rules

1. Keep runtime and backend tickets independently executable unless a matrix row marks a hard gate.
2. Do not block one track on speculative work from the other track.
3. Every cross-track dependency change must update the dependency matrix in the same change.
4. Cutover work cannot start until both tracks satisfy their cutover preconditions.

## Parallel Execution Lanes

| Lane | Primary Focus | Source of Truth | Can Run Now | Hard-Gated By |
| --- | --- | --- | --- | --- |
| Lane A | Secure runtime gating, worker topology, shared-memory IPC | `doc/wasm/runtime-replacement-master-plan.md` | yes | none |
| Lane B | WASM-native backend contract, frame/debug model, numeric lowering | `doc/wasm/backend-migration-master-plan.md` | yes | none |
| Lane C | Differential harnesses and parity checks | both master plans | yes | contract freeze from Lane A + Lane B |
| Lane D | Cutover and legacy retirement | both master plans | no | completion of Lane A/B/C gates |

## Synchronization Gates

- `SG-1` Contract sync: startup capability checks and backend ABI assumptions are compatible.
- `SG-2` Debug sync: frame and debug metadata model remains actionable under runtime worker model.
- `SG-3` Transport sync: backend call boundary and runtime shared-memory IPC protocol are mutually compatible.
- `SG-4` Parity sync: differential test harness passes correctness and determinism gates.
- `SG-5` Cutover sync: runtime and backend retirement plans are approved together.

## Immediate Next Step

- Action: continue `Pack A` by executing unified `X-07` closure review over committed runtime run-v2 artifacts (`rpl08-20260210-023524Z-91fdb0be`) while carrying immutable backend `BPL-08 Step 3` closure rows as `X-07` review input (`rpl05-20260210-011240Z-91fdb0be`, `bpl06-20260210-005408Z-91fdb0be`, `bpl07-20260210-005408Z-91fdb0be`).
- Why now: runtime Step 3 run-v2 evidence is now committed with full lane pass coverage, `R8GAP-01` closed, and `x07_runtime_ready=true`; remaining work is cross-track closure review, not further runtime remediation.
- Success evidence: synchronized runtime/backend planning docs preserve immutable bundle IDs and backend `BPL08-CR*` rows, carry committed run-v2 artifacts, and publish explicit `X-07` closure-review disposition while keeping secure/no-fallback posture unchanged.

## Change Log

- 2026-02-09: Initial program board created with dual-track structure and synchronization gate model.
- 2026-02-09: Program planning scaffold completed; immediate next action moved to Pack A execution.
- 2026-02-09: Pack A next action advanced to RPL-01 Step 3 and BPL-02 check-ID linkage after RPL-01 Step 2 completion.
- 2026-02-09: Pack A next action advanced to RPL-01 Step 4 after RPL-01 Step 3 diagnostics contract completion.
- 2026-02-09: Pack A next action advanced to RPL-01 Step 5 after RPL-01 Step 4 integration-plan completion.
- 2026-02-09: Pack A next action advanced to RPL-01 Step 6 after RPL-01 Step 5 validation-gate completion.
- 2026-02-09: Pack A next action advanced to post-handoff `X-01` closure plus RPL-02 Step 1 kickoff after RPL-01 Step 6 completion.
- 2026-02-09: Pack A immediate action advanced past `X-01` closure to RPL-02 Step 1 + BPL-01/BPL-02 Step 2 execution.
- 2026-02-09: Pack A immediate action advanced from RPL-02 Step 1 to Step 2 after `X-02` moved to `in_progress` with published `WTOP-*`/`WSEQ-*` readiness evidence.
- 2026-02-09: Pack A immediate action advanced from RPL-02 Step 2 to Step 3 after lifecycle/no-fallback outputs (`WLCS-*`, `WLCT-*`, `WLCR-*`) were published for `X-02` mapping.
- 2026-02-09: Pack A backend focus advanced from BPL-01 Step 3 closure to BPL-02 Step 2 plus BPL-03 drafting after BPL-01 closure evidence was recorded.
- 2026-02-09: Pack A backend focus advanced from BPL-02 Step 2 drafting to BPL-03 mapping consumption after BPL-02 contract closure evidence (`CON-*` to `BCL-*`) was published.
- 2026-02-09: Pack A immediate action advanced past RPL-02 Step 3 after `X-02` closure evidence (`X03M-*` and `B3*` mappings) and now targets RPL-03 Step 1 + BPL-03 Step 2 execution.
- 2026-02-09: Pack A backend focus advanced from BPL-03 Step 2 drafting to Step 2 closure validation after publishing `FDC-01`..`FDC-10` draft invariants.
- 2026-02-09: Pack A backend focus advanced from BPL-03 Step 2 closure validation to BPL-04 Step 1 after BPL-03 Step 2 closure was recorded.
- 2026-02-09: Pack A runtime focus advanced from RPL-03 Step 1 drafting to Step 2 conformance-definition after protocol v1 (`IPCP-01`..`IPCP-49`) publication and `X-03` transition to `in_progress`.
- 2026-02-09: Pack A backend focus advanced from BPL-04 Step 1 to BPL-04 Step 2 after publishing `M4F-01`..`M4F-08` operation-family classification.
- 2026-02-09: Pack A runtime focus advanced from RPL-03 Step 2 conformance-definition to Step 3 committed evidence execution after publishing `IPCV-01`..`IPCV-12` and `IPCL-01`..`IPCL-05`.
- 2026-02-09: Pack A runtime focus advanced from Step 3 initial execution to Step 3 gap-remediation rerun after run-v1 evidence recorded `status=fail` and blocker gaps `IPCGAP-01`..`IPCGAP-04`.
- 2026-02-09: Pack A backend focus advanced from BPL-04 Step 2 sequencing to BPL-04 Step 3 benchmark/profile gate alignment after publishing ordered non-`native_now` family sequence gates (`BPL04-S2-*`).
- 2026-02-09: Pack A backend focus advanced from BPL-04 Step 3 gate alignment to BPL-05 Step 1 staged decoupling after BPL-04 published benchmark/profile gates (`BPL04-G01`..`BPL04-G06`).
- 2026-02-09: Pack A backend focus advanced from BPL-05 Step 1 staging to BPL-05 Step 2 seam contracts after publishing staged decoupling slices (`B5S-01`..`B5S-05`).
- 2026-02-09: Pack A backend focus advanced from BPL-05 Step 2 seam contracts to BPL-05 Step 3 handoff/gate integration after publishing seam matrix (`B5M-01`..`B5M-05`).
- 2026-02-09: Pack A runtime focus advanced past RPL-03 Step 3 rerun after conformance evidence (`status=pass`, `x03_clear_ready=true`) closed hard-gate row `X-03`; immediate runtime action is now RPL-04 Step 1.
- 2026-02-09: Pack A backend focus advanced from BPL-05 Step 3 handoff/gate integration to BPL-06 Step 1 harness contract definition after publishing handoff checklist (`B5H-01`..`B5H-05`).
- 2026-02-09: Pack A backend focus advanced from BPL-06 Step 1 harness contract definition to BPL-06 Step 2 fixture/evidence-template publication after freezing `BPL06-CP01`..`BPL06-CP05`.
- 2026-02-09: Pack A backend focus advanced from BPL-06 Step 2 fixture/evidence-template publication to BPL-06 Step 3 triage/gate-integration definition after publishing fixture matrix (`BPL06-FX01`..`BPL06-FX05`) and template files.
- 2026-02-09: Pack A backend focus advanced from BPL-06 Step 3 triage/gate-integration definition to BPL-07 Step 1 budget/measurement setup after publishing severity/rollback/intake baselines (`BPL06-SEV-*`, `BPL06-RB-*`, `BPL06-INT-*`).
- 2026-02-09: Pack A runtime focus advanced from RPL-04 Step 1 scope publication to RPL-04 Step 2 lane/evidence definition after freezing `R4M-*`, `R4C-*`, and `R4T-*`; immediate backend-parallel focus remains BPL-06 Step 3 intake completion for `X-04` compatibility sync.
- 2026-02-09: Pack A runtime focus advanced from RPL-04 Step 2 lane/evidence definition to RPL-04 Step 3 committed evidence execution after freezing `R4L-*`, `R4V-*`, and `R4I-*`; immediate backend-parallel focus remains BPL-06 Step 3 intake completion for `X-04` compatibility sync.
- 2026-02-09: Pack A runtime focus advanced from RPL-04 Step 3 initial evidence execution to Step 3 gap-remediation rerun after publishing run-v1 evidence and opening blocker gaps `R4GAP-01`..`R4GAP-04`; immediate backend-parallel focus remains BPL-06 Step 3 intake completion for `X-04` compatibility sync.
- 2026-02-09: Pack A immediate action wording resynced with backend governance state: backend-parallel focus is BPL-07 Step 1 budget/measurement setup while `X-04` compatibility intake remains anchored to frozen `BPL06-*` artifacts.
- 2026-02-10: Pack A runtime focus advanced past RPL-04 Step 3 rerun after closure evidence (`rpl-04-step3-rerun-2026-02-10`) reported full `R4V-01`..`R4V-14` assertion pass coverage and closed `R4GAP-01`..`R4GAP-04`; dependency row `X-04` is now clear to `done`.
- 2026-02-10: Pack A immediate action advanced from RPL-04 closure to RPL-05 Step 1 kickoff while backend-parallel focus remains BPL-07 Step 1 budget/measurement setup.
- 2026-02-10: Pack A backend-parallel focus advanced from BPL-07 Step 1 baseline publication to BPL-07 Step 2 run-v1 measurement execution after publishing `BPL07-BM01`..`BPL07-BM05` over frozen `BPL06-*` intake IDs.
- 2026-02-10: Executed RPL-05 Step 1 local-core contract publication (`R5S-*`, `R5T-*`, `R5A-*`) and resynced Pack A wording to `RPL-05 Step 2` with backend continuation on `BPL-07 Step 1` over frozen `BPL06-*` intake artifacts.
- 2026-02-10: Executed RPL-05 Step 2 conformance publication (`R5L-*`, `R5V-*`) and resynced Pack A wording to `RPL-05 Step 3` with backend continuation on `BPL-07 Step 1` over frozen `BPL06-*` intake artifacts.
- 2026-02-10: Executed BPL-07 Step 2 run-v1 measurement packet (`bpl07-20260210-002604Z-91fdb0be`) and advanced Pack A backend-parallel focus to BPL-07 Step 3 readiness after recording intake-artifact gaps and `BPL07-BM05` perf overrun.
- 2026-02-10: Resynced Pack A state after RPL-05 Step 2 publication to keep backend-parallel wording pinned to BPL-07 Step 1 baseline hardening/consumption over frozen `BPL06-*` intake artifacts.
- 2026-02-10: Executed BPL-07 Step 3 by publishing closure-readiness criteria (`BPL07-CR01`..`BPL07-CR05`) and advanced Pack A backend-parallel focus to one remediation execution packet for unresolved `CR01`/`CR03` blockers.
- 2026-02-10: Synced Pack A runtime wording to RPL-05 Step 3 run-v1 evidence (`rpl05-20260210-004335Z-91fdb0be`), opened runtime blocker tracking (`R5GAP-01`..`R5GAP-05`), and advanced immediate runtime action to Step 3 gap-remediation rerun (`run-v2`).
- 2026-02-10: Executed backend remediation run-v2 (`bpl06-20260210-005408Z-91fdb0be`, `bpl07-20260210-005408Z-91fdb0be`) and resynced Pack A immediate action to runtime run-v2 execution plus backend closure-review carry-forward for `X-06`/`X-07`.
- 2026-02-10: Closed RPL-05 Step 3 via run-v2 evidence (`rpl05-20260210-011240Z-91fdb0be`), closed `R5GAP-01`..`R5GAP-05`, synchronized `X-05=done`, and advanced Pack A immediate runtime action to `RPL-07 Step 1` with backend pass bundle carry-forward for `X-06`/`X-07`.
- 2026-02-10: Executed RPL-07 Step 1 by publishing `doc/wasm/tickets/RPL-07-module-environment-sharing.md` with frozen `R7S-*`/`R7R-*`/`R7T-*` IDs, advanced `X-06` to `in_progress`, and shifted Pack A immediate runtime action to `RPL-07 Step 2` while keeping closure-bundle run IDs immutable for `X-06`/`X-07`.
- 2026-02-10: Executed RPL-07 Step 2 by publishing frozen lane/validation/review contracts (`R7L-*`, `R7V-*`, `R7I-*`), preserved immutable closure-bundle IDs in `X-06`/`X-07` review mappings, and shifted Pack A immediate runtime action to `RPL-07 Step 3` evidence execution.
- 2026-02-10: Executed RPL-07 Step 3 run-v1 (`rpl07-20260210-013659Z-91fdb0be`) with committed immutable `X-06`/`X-07` review packets, recorded open blocker `R7GAP-01` (`R7V-06` digest parity drift), and shifted Pack A immediate runtime action to Step 3 run-v2 targeted closure.
- 2026-02-10: Executed RPL-07 Step 3 run-v2 (`rpl07-20260210-014654Z-91fdb0be`) with terminal `module_env_step2_summary_v1.status=pass`, closed `R7GAP-01`, synchronized `X-06=done`, and shifted Pack A immediate runtime action to `RPL-08 Step 1` while preserving immutable `X-07` carry-forward bundle IDs.
- 2026-02-10: Synced Pack A immediate action after backend BPL-08 Step 2 publication (`BPL08-IV01`..`BPL08-IV06`) and advanced backend-parallel focus to BPL-08 Step 3 closure-readiness packetization while runtime continues RPL-08 Step 1.
- 2026-02-10: Synced Pack A immediate action after backend BPL-08 Step 3 publication (`BPL08-CR01`..`BPL08-CR06`) to keep backend closure rows immutable while runtime `RPL-08 Step 1` remains the active `X-07` closure path.
- 2026-02-10: Executed RPL-08 Step 1 by publishing runtime budget/measurement contract IDs (`R8B-*`, `R8M-*`, `R8T-*`, `R8R-*`), advanced Pack A immediate runtime action to `RPL-08 Step 2`, and preserved immutable `X-07` bundle IDs plus backend `BPL08-CR*` carry-forward rows unchanged.
- 2026-02-10: Executed RPL-08 Step 2 by publishing runtime lane/validation/review contract IDs (`R8L-*`, `R8V-*`, `R8I-*`), advanced Pack A immediate runtime action to `RPL-08 Step 3` run-v1 evidence execution, and preserved immutable `X-07` bundle IDs plus backend `BPL08-CR*` carry-forward rows unchanged.
- 2026-02-10: Executed RPL-08 Step 3 run-v1 (`R8V-01`..`R8V-14`) and committed evidence bundle (`rpl08-20260210-022252Z-91fdb0be`) with terminal `artifact_budget_step2_summary_v1.status=pass`; opened blocker `R8GAP-01` for closure-target overruns (`R8B-01`, `R8B-02`, `R8B-05`) and shifted Pack A immediate runtime action to Step 3 run-v2 targeted closure.
- 2026-02-10: Executed RPL-08 Step 3 run-v2 (`R8V-01`..`R8V-14`) and committed evidence bundle (`rpl08-20260210-023524Z-91fdb0be`) with terminal `artifact_budget_step2_summary_v1.status=pass`; closed blocker `R8GAP-01`, recorded `x07_runtime_ready=true`, and shifted Pack A immediate runtime action to unified `X-07` closure review while preserving immutable bundle IDs and backend `BPL08-CR*` carry-forward rows unchanged.
