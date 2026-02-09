# Backend Migration Master Plan (ARM Facade -> WASM-Native Backend)

Status: Active  
Owner: Compiler/backend migration track  
Last Updated: 2026-02-09  
Program Board: `doc/wasm/wasm-program-board.md`

## Purpose

This is the canonical execution and status document for migrating from simulated-ARM backend assumptions to a WASM-native processor/backend model that:

- uses native WASM capabilities as first-class targets,
- removes ARM-model overhead from generated code paths (especially numeric/mathematical operations),
- preserves and improves debuggability under the new frame/metadata model.

This plan is parallel to, not a replacement for, the runtime replacement track.

## Scope

In scope:

- ARM assumption inventory and staged retirement plan.
- WASM-native backend contract (calling, value, memory, arithmetic, and control-flow conventions).
- Frame/debug metadata model for practical debugging after migration.
- Dual-path backend bring-up, differential harnesses, and cutover gates.
- Performance/size validation specific to backend output.

Out of scope:

- Runtime startup capability policy (owned by runtime replacement track).
- Storage V2 semantics and persistence migration.
- UI architecture work not directly affected by backend call/debug model.

## Related Source Documents

- `doc/wasm/ABI.md`
- `doc/wasm/decisions.md`
- `doc/wasm/project-overview.md`
- `doc/wasm/porting-status.md`
- `doc/wasm/runtime-replacement-master-plan.md`
- `doc/wasm/runtime-backend-dependency-matrix.md`

## Status Legend

- `planned`: defined, not started.
- `in_progress`: active implementation.
- `blocked`: cannot continue until dependency/decision is resolved.
- `done`: merged and validated against defined exit criteria.
- `deferred`: intentionally paused and not current execution priority.
- `cancelled`: explicitly removed from scope.

## Update Contract (Required)

On every backend ticket update:

1. Update this document:
   - ticket `Status`,
   - `Last Updated`,
   - `Notes`,
   - `Next Step Analysis`.
2. Update the ticket subplan document referenced by `Subplan`.
3. If cross-track implications changed, update `doc/wasm/runtime-backend-dependency-matrix.md` in the same change.

## Fresh-Context Resume Protocol

When resuming backend work from scratch:

1. Read `Current Baseline Snapshot`.
2. Read `doc/wasm/runtime-backend-dependency-matrix.md` and filter out hard-blocked tickets.
3. Execute only the `Immediate Next Step` under the highest-priority unblocked ticket.
4. At stop, update this plan and the ticket subplan together.

## Current Baseline Snapshot (2026-02-09)

- Current backend lineage still carries ARM-shaped assumptions in multiple paths.
- Runtime replacement track is active and defining secure-only/shared-memory architecture.
- Existing artifact-size and dispatch-hardening pressures make backend overhead reduction a high-value track.
- There is no single consolidated backend migration board yet (this document establishes it).

## Parallelization Model

Parallel execution is expected across these backend lanes:

- Lane B1 (contract): inventory + WASM-native contract + debug model.
- Lane B2 (codegen): math/numeric path and lowering decoupling from ARM assumptions.
- Lane B3 (validation): dual-path differential harness and perf/size gates.
- Lane B4 (integration): runtime alignment and cutover.

Hard gates are tracked in `doc/wasm/runtime-backend-dependency-matrix.md`.

## Ticket Board

| Ticket | Status | Priority | Subplan | Last Updated | Notes |
| --- | --- | --- | --- | --- | --- |
| BPL-00 | in_progress | P0 | `doc/wasm/backend-tickets/BPL-00-governance-and-baseline-freeze.md` | 2026-02-09 | Governance loop remains active after BPL-03 Step 2 closure; `X-02` remains cleared and synchronization stayed in-cycle across matrix/master/subplan docs. |
| BPL-01 | done | P0 | `doc/wasm/backend-tickets/BPL-01-arm-assumption-inventory.md` | 2026-02-09 | Step 1/2/3 closure complete (16 assumptions; remove=6, compat_layer=7, defer=3) with no new non-speculative matrix dependency rows required. |
| BPL-02 | done | P0 | `doc/wasm/backend-tickets/BPL-02-wasm-native-backend-contract.md` | 2026-02-09 | Step 2 closure complete: `CON-01`..`CON-08` promoted to v1 baseline with explicit `BCL-01`..`BCL-12` coverage evidence. |
| BPL-03 | done | P0 | `doc/wasm/backend-tickets/BPL-03-frame-and-debug-metadata-model.md` | 2026-02-09 | Step 2 closure complete: `FDC-01`..`FDC-10` validated with full `B3*` class coverage and hardened clause language. |
| BPL-04 | planned | P0 | `doc/wasm/backend-tickets/BPL-04-numeric-and-math-pipeline-modernization.md` | 2026-02-09 | Remove ARM-shaped math overhead and optimize numeric paths. |
| BPL-05 | planned | P0 | `doc/wasm/backend-tickets/BPL-05-ir-lowering-arm-decoupling.md` | 2026-02-09 | Decouple lowering/codegen from simulated ARM structure. |
| BPL-06 | planned | P0 | `doc/wasm/backend-tickets/BPL-06-dual-path-build-and-diff-harness.md` | 2026-02-09 | Dual-path backend mode and differential correctness harness. |
| BPL-07 | planned | P1 | `doc/wasm/backend-tickets/BPL-07-size-and-performance-gates.md` | 2026-02-09 | Backend-specific perf and artifact-size validation gates. |
| BPL-08 | planned | P0 | `doc/wasm/backend-tickets/BPL-08-runtime-alignment-integration.md` | 2026-02-09 | Align backend call/transport boundaries with runtime replacement architecture. |
| BPL-09 | planned | P0 | `doc/wasm/backend-tickets/BPL-09-cutover-and-arm-retirement.md` | 2026-02-09 | Final cutover and ARM-compat path retirement. |

## Ticket Details

### BPL-00 - Governance and Baseline Freeze

- Status: `in_progress`
- Priority: `P0`
- Last Updated: `2026-02-09`
- Subplan: `doc/wasm/backend-tickets/BPL-00-governance-and-baseline-freeze.md`
- Dependencies: none

Notes:

- This plan is now the canonical tracker for backend migration.
- Program-level coordination is anchored in `doc/wasm/wasm-program-board.md`.
- Cross-track dependencies are externalized to `doc/wasm/runtime-backend-dependency-matrix.md`.
- Governance evidence now includes BPL-03 Step 2 closure evidence (`FDC-*` + `B3*` coverage validation) with synchronized updates across matrix/program-board/master/subplan docs.

Next Step Analysis:

- Immediate Next Step: start BPL-04 Step 1 by classifying math op families and mapping each to WASM-native lowering strategy.
- Why this step now: BPL-03 closure criteria are satisfied, so backend critical-path planning shifts to numeric/mathematical overhead retirement.
- Evidence required to close next step: BPL-04 publishes an operation-family strategy matrix with explicit lowering posture and first benchmark hooks.

---

### BPL-01 - ARM Assumption Inventory

- Status: `done`
- Priority: `P0`
- Last Updated: `2026-02-09`
- Subplan: `doc/wasm/backend-tickets/BPL-01-arm-assumption-inventory.md`
- Dependencies: BPL-00

Notes:

- Step 1 inventory v1 is now committed with source-backed rows spanning ABI/calling, lowering/IR, frame/debug, memory/tagging, and runtime boundary assumptions.
- Rescan refresh added concrete assumptions for WASMENV ARMENV coupling and GC register-root range coupling.
- Current strategy distribution is `remove=6`, `compat_layer=7`, `defer=3`.
- Step 2 closure now includes explicit transition/cutover triggers and sequencing owners for all 10 non-`remove` assumptions.
- Step 3 dependency/risk closure validated all 16 assumptions against BPL-02/BPL-03/BPL-05 slices and confirmed no additional non-speculative matrix rows are required.
- Cross-track sensitive rows now explicitly map to runtime tickets where concrete (`RPL-02`, `RPL-07`) alongside backend tickets.

Next Step Analysis:

- Immediate Next Step: maintain BPL-01 as a baseline artifact and apply delta-only updates when new ARM-shaped assumptions are discovered by downstream tickets.
- Why this step now: inventory and mapping closure criteria are satisfied, so remaining work is governance maintenance rather than baseline discovery.
- Evidence required to close next step: any newly discovered assumption is added with source evidence and synchronized master/matrix impact updates in the same change.

---

### BPL-02 - WASM-Native Backend Contract

- Status: `done`
- Priority: `P0`
- Last Updated: `2026-02-09`
- Subplan: `doc/wasm/backend-tickets/BPL-02-wasm-native-backend-contract.md`
- Dependencies: BPL-01

Notes:

- Contract must be explicit about value model, calling conventions, memory operations, and extension points.
- Step 1 linkage matrix in BPL-02 now references frozen runtime startup checks (`SRG-01`..`SRG-12`) explicitly.
- Step 2 closure output now provides explicit linkage validation from `CON-01`..`CON-08` to `BCL-01`..`BCL-12` with no uncovered rows.
- Cross-track row `X-01` evidence is now satisfied by the BPL-02 linkage table and synchronized matrix update.
- Contract v1 is now frozen as additive-evolution baseline for downstream backend slices.

Next Step Analysis:

- Immediate Next Step: maintain BPL-02 as a contract baseline and apply delta-only additive updates if downstream tickets expose new invariant requirements.
- Why this step now: BPL-02 closure criteria are satisfied, so ongoing work is governance maintenance rather than contract drafting.
- Evidence required to close next step: any new contract requirement is added as new `CON-*` IDs with synchronized `BCL-*` references and master/matrix impact notes.

---

### BPL-03 - Frame and Debug Metadata Model

- Status: `done`
- Priority: `P0`
- Last Updated: `2026-02-09`
- Subplan: `doc/wasm/backend-tickets/BPL-03-frame-and-debug-metadata-model.md`
- Dependencies: BPL-02, RPL-01, RPL-02

Notes:

- Debuggability is a first-class requirement, not a cleanup item.
- Step 1 mapping v1 is now published in BPL-03 with explicit consumption IDs (`B3R-*`, `B3S-*`, `B3L-*`, `B3T-*`, `B3P-*`) across all required RPL-02 ID classes.
- Dependency row `X-02` is now `done` based on explicit RPL-02 Step 3 mapping and synchronized BPL-03 consumption evidence.
- Step 2 closure now validates full `B3*` class coverage across `FDC-01`..`FDC-10` with explicit closure assertions.
- Clause hardening is complete for ownership/no-fallback/transition ambiguity using explicit contract-field requirements.
- Closure re-validation preserved full `B3*` coverage and made lane-class/cutover triggers explicit in `FDC-01`, `FDC-09`, and `FDC-10`.

Next Step Analysis:

- Immediate Next Step: maintain BPL-03 as a baseline artifact and apply additive-only updates when downstream tickets require new frame/debug invariants.
- Why this step now: BPL-03 exit criteria are satisfied, so ongoing work is governance maintenance rather than baseline drafting.
- Evidence required to close next step: any new frame/debug requirement lands as new `FDC-*` IDs with synchronized `B3*` traceability updates.

---

### BPL-04 - Numeric and Math Pipeline Modernization

- Status: `planned`
- Priority: `P0`
- Last Updated: `2026-02-09`
- Subplan: `doc/wasm/backend-tickets/BPL-04-numeric-and-math-pipeline-modernization.md` (pending)
- Dependencies: BPL-02

Notes:

- Numeric paths are primary overhead targets for ARM-facade removal.

Next Step Analysis:

- Immediate Next Step: classify math op families and map each to WASM-native lowering strategy.
- Why this step now: high-performance impact and early architectural validation.
- Evidence required to close next step: per-family lowering matrix and first benchmark gates.

---

### BPL-05 - IR/Lowering ARM Decoupling

- Status: `planned`
- Priority: `P0`
- Last Updated: `2026-02-09`
- Subplan: `doc/wasm/backend-tickets/BPL-05-ir-lowering-arm-decoupling.md` (pending)
- Dependencies: BPL-02

Notes:

- Must remove ARM-shaped abstractions from backend lowering and codegen glue.

Next Step Analysis:

- Immediate Next Step: define staged decoupling plan and migration seams for dual-path operation.
- Why this step now: enables BPL-06 differential testing without destabilizing current functionality.
- Evidence required to close next step: staged migration map with rollback points.

---

### BPL-06 - Dual-Path Build and Differential Harness

- Status: `planned`
- Priority: `P0`
- Last Updated: `2026-02-09`
- Subplan: `doc/wasm/backend-tickets/BPL-06-dual-path-build-and-diff-harness.md` (pending)
- Dependencies: BPL-03, BPL-04, BPL-05

Notes:

- Correctness parity is required before default-path cutover.

Next Step Analysis:

- Immediate Next Step: define dual-build mode and deterministic diff harness contract.
- Why this step now: protects migration from silent semantic drift.
- Evidence required to close next step: harness design plus first parity fixture set.

---

### BPL-07 - Size and Performance Gates

- Status: `planned`
- Priority: `P1`
- Last Updated: `2026-02-09`
- Subplan: `doc/wasm/backend-tickets/BPL-07-size-and-performance-gates.md` (pending)
- Dependencies: BPL-06

Notes:

- Migration must prove net positive impact on runtime cost and artifact shape.

Next Step Analysis:

- Immediate Next Step: define backend performance budget sheet and measurement commands.
- Why this step now: objective gating is required before integration/cutover decisions.
- Evidence required to close next step: budgets committed and command outputs reproducible.

---

### BPL-08 - Runtime Alignment Integration

- Status: `planned`
- Priority: `P0`
- Last Updated: `2026-02-09`
- Subplan: `doc/wasm/backend-tickets/BPL-08-runtime-alignment-integration.md` (pending)
- Dependencies: BPL-06, RPL-03, RPL-07

Notes:

- Backend and runtime shared-memory/call boundaries must align before cutover.

Next Step Analysis:

- Immediate Next Step: define integration checkpoints and ABI compatibility assertions.
- Why this step now: avoids late-stage integration surprises between tracks.
- Evidence required to close next step: alignment matrix with passing checkpoints.

---

### BPL-09 - Cutover and ARM Retirement

- Status: `planned`
- Priority: `P0`
- Last Updated: `2026-02-09`
- Subplan: `doc/wasm/backend-tickets/BPL-09-cutover-and-arm-retirement.md` (pending)
- Dependencies: BPL-08, RPL-09

Notes:

- Final release must avoid unresolved dependency on ARM-facade behavior.

Next Step Analysis:

- Immediate Next Step: define cutover gate and rollback contract for backend default switch.
- Why this step now: cutover expectations must be explicit before late-stage pressure.
- Evidence required to close next step: approved cutover checklist with rollback rehearsals.

## Subplan Registry Sync Rules

- Each ticket subplan must exist at the path listed above.
- Each subplan must include:
  - `Status`,
  - `Last Updated`,
  - `Notes`,
  - `Immediate Next Step`,
  - `Exit Criteria`,
  - `Change Log`.
- If a subplan moves paths, update both the board row and ticket detail block in the same change.

## Ongoing Next-Step Analysis Rules

For every active ticket update, include all three:

1. What changed since the prior update.
2. What single next action will be executed next.
3. What evidence will prove that next action succeeded.

Avoid batching multiple unrelated next actions into one update.

## Change Log

- 2026-02-09: Initial backend migration master plan created with ticket board, detail blocks, and update contract.
- 2026-02-09: Synced BPL-02 planning notes with `X-01` progress after RPL-01 Step 2 froze startup check IDs (`SRG-01`..`SRG-12`).
- 2026-02-09: Advanced BPL-01 to `in_progress` with Step 1 inventory v1 evidence and shifted BPL-00 governance next action to BPL-01 Step 2 strategy closure.
- 2026-02-09: Started BPL-02 with explicit `SRG-01`..`SRG-12` linkage matrix, synchronized `X-01` clearance evidence, and advanced BPL-02 next step to contract invariant drafting.
- 2026-02-09: Synchronized backend plan with `X-02` advancement to `in_progress` after RPL-02 Step 1 publication (`WTOP-*`, `WSEQ-*`, `worker_topology_ready_v1`) and updated BPL-03 dependency/next-step language accordingly.
- 2026-02-09: Refreshed BPL-01 inventory counts after ARM rescan (`16` assumptions) and synchronized BPL-00/BPL-01 governance notes and Step 2 closure evidence expectations.
- 2026-02-09: Marked BPL-01 Step 2 closure complete (10 non-`remove` rows with explicit transition triggers + sequencing owners) and advanced BPL-00/BPL-01 next action to Step 3 dependency/risk closure.
- 2026-02-09: Synchronized backend plan with RPL-02 Step 2 lifecycle evidence in `X-02` (`WLCS-*`, `WLCT-*`, `WLCR-*`, `X02R-04`..`X02R-06`) and updated BPL-03 consumption requirements accordingly.
- 2026-02-09: Closed BPL-01 after Step 3 dependency/risk validation confirmed complete downstream slice coverage and no new non-speculative dependency-matrix rows.
- 2026-02-09: Advanced BPL-02 Step 2 by publishing `CON-01`..`CON-08` draft invariants and shifted BPL-02 immediate action to linkage-coverage closure.
- 2026-02-09: Closed BPL-02 Step 2 with explicit `BCL-01`..`BCL-12` coverage validation and advanced governance next action to BPL-03 `X-02` mapping consumption.
- 2026-02-09: Advanced BPL-03 to `in_progress` after Step 1 published explicit `B3*` consumption mappings, synchronized `X-02` closure, and shifted backend immediate action to BPL-03 Step 2 contract drafting.
- 2026-02-09: Advanced BPL-03 Step 2 by publishing `FDC-01`..`FDC-10` draft invariants and shifted governance focus to Step 2 traceability closure.
- 2026-02-09: Closed BPL-03 Step 2 by validating full `B3*` class coverage across `FDC-01`..`FDC-10`, hardened ambiguous clause language, and advanced backend next action to BPL-04 Step 1.
- 2026-02-09: Re-ran BPL-03 Step 2 closure validation; confirmed unchanged full `B3*` coverage and clarified lane-class/cutover trigger wording in `FDC-01`, `FDC-09`, and `FDC-10`.
