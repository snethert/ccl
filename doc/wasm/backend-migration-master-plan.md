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
| BPL-00 | in_progress | P0 | `doc/wasm/backend-tickets/BPL-00-governance-and-baseline-freeze.md` | 2026-02-09 | Track governance scaffolded; baseline freeze and sync rules established. |
| BPL-01 | planned | P0 | `doc/wasm/backend-tickets/BPL-01-arm-assumption-inventory.md` | 2026-02-09 | Inventory ARM-coupled assumptions and classify removal strategy. |
| BPL-02 | planned | P0 | `doc/wasm/backend-tickets/BPL-02-wasm-native-backend-contract.md` | 2026-02-09 | Define normative WASM-native backend contract and compatibility envelope. |
| BPL-03 | planned | P0 | `doc/wasm/backend-tickets/BPL-03-frame-and-debug-metadata-model.md` | 2026-02-09 | Preserve debuggability under new backend/frame model. |
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

Next Step Analysis:

- Immediate Next Step: execute BPL-01 Step 1 to produce ARM assumption inventory v1.
- Why this step now: no backend contract can be credible without a concrete assumption inventory.
- Evidence required to close next step: inventory table with source references and removal strategy class.

---

### BPL-01 - ARM Assumption Inventory

- Status: `planned`
- Priority: `P0`
- Last Updated: `2026-02-09`
- Subplan: `doc/wasm/backend-tickets/BPL-01-arm-assumption-inventory.md`
- Dependencies: BPL-00

Notes:

- Must identify where ARM-model assumptions currently leak into ABI, lowering, and runtime interactions.

Next Step Analysis:

- Immediate Next Step: produce an assumption matrix with owner, impact, and migration path tags.
- Why this step now: BPL-02/BPL-04/BPL-05 all depend on this inventory.
- Evidence required to close next step: inventory published and linked from this plan.

---

### BPL-02 - WASM-Native Backend Contract

- Status: `planned`
- Priority: `P0`
- Last Updated: `2026-02-09`
- Subplan: `doc/wasm/backend-tickets/BPL-02-wasm-native-backend-contract.md` (pending)
- Dependencies: BPL-01

Notes:

- Contract must be explicit about value model, calling conventions, memory operations, and extension points.

Next Step Analysis:

- Immediate Next Step: draft contract v1 with normative invariants and evolution policy.
- Why this step now: parallel implementation branches need stable boundaries.
- Evidence required to close next step: contract v1 approved and referenced by downstream tickets.

---

### BPL-03 - Frame and Debug Metadata Model

- Status: `planned`
- Priority: `P0`
- Last Updated: `2026-02-09`
- Subplan: `doc/wasm/backend-tickets/BPL-03-frame-and-debug-metadata-model.md` (pending)
- Dependencies: BPL-02, RPL-01

Notes:

- Debuggability is a first-class requirement, not a cleanup item.

Next Step Analysis:

- Immediate Next Step: define frame map and debug metadata contract compatible with runtime worker/thread model.
- Why this step now: prevents performance-driven changes from removing observability.
- Evidence required to close next step: debug contract doc + initial validation checklist.

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
