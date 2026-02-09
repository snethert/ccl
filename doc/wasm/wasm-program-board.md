# WASM Program Board (Runtime Replacement + Backend Migration)

Status: Active  
Owner: WASM replacement program  
Last Updated: 2026-02-09

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

- Action: continue `Pack A` by executing RPL-03 Step 1 shared-memory IPC contract drafting alongside BPL-04 Step 1 operation-family classification.
- Why now: `X-02` remains cleared and BPL-03 Step 2 is now closed, so the shared critical path is `X-03` protocol readiness plus backend numeric-strategy definition.
- Success evidence: RPL-03 Step 1 publishes protocol v1 IDs/tests and BPL-04 Step 1 publishes math-operation family matrix with WASM-native lowering posture.

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
