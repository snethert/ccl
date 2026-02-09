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

- Action: execute `Pack A` in parallel by running RPL-01 Step 2 and BPL-01 Step 1.
- Why now: planning scaffolds are now in place and this is the highest-throughput low-risk parallel window.
- Success evidence: RPL-01 capability matrix draft exists, BPL-01 assumption inventory v1 exists, and `X-01` moves to `in_progress`.

## Change Log

- 2026-02-09: Initial program board created with dual-track structure and synchronization gate model.
- 2026-02-09: Program planning scaffold completed; immediate next action moved to Pack A execution.
