# Backend Migration Master Plan (ARM Facade -> WASM-Native Backend)

Status: Active  
Owner: Compiler/backend migration track  
Last Updated: 2026-02-10  
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
| BPL-00 | in_progress | P0 | `doc/wasm/backend-tickets/BPL-00-governance-and-baseline-freeze.md` | 2026-02-10 | Fortieth governance cycle is now complete as additive-only maintenance over closed `X-08` and `RPL-06` artifacts, preserving backend Step 3 run-v2 evidence (`bpl09-20260210-040314Z-2084077e`), runtime Step 3 run-v1 evidence (`rpl06-20260210-054023Z-50d752af`), and unified closure review (`x08-closure-20260210-040400Z-2084077e`) without drift. |
| BPL-01 | done | P0 | `doc/wasm/backend-tickets/BPL-01-arm-assumption-inventory.md` | 2026-02-09 | Step 1/2/3 closure complete (16 assumptions; remove=6, compat_layer=7, defer=3) with no new non-speculative matrix dependency rows required. |
| BPL-02 | done | P0 | `doc/wasm/backend-tickets/BPL-02-wasm-native-backend-contract.md` | 2026-02-09 | Step 2 closure complete: `CON-01`..`CON-08` promoted to v1 baseline with explicit `BCL-01`..`BCL-12` coverage evidence. |
| BPL-03 | done | P0 | `doc/wasm/backend-tickets/BPL-03-frame-and-debug-metadata-model.md` | 2026-02-09 | Step 2 closure complete: `FDC-01`..`FDC-10` validated with full `B3*` class coverage and hardened clause language. |
| BPL-04 | done | P0 | `doc/wasm/backend-tickets/BPL-04-numeric-and-math-pipeline-modernization.md` | 2026-02-09 | Step 1/2/3 closed: classification, sequencing, and benchmark/profile gates (`BPL04-G01`..`BPL04-G06`) are now published. |
| BPL-05 | done | P0 | `doc/wasm/backend-tickets/BPL-05-ir-lowering-arm-decoupling.md` | 2026-02-09 | Step 1/2/3 closed with staged slices (`B5S-*`), seam contracts (`B5M-*`), and consumer handoff checklist (`B5H-*`). |
| BPL-06 | done | P0 | `doc/wasm/backend-tickets/BPL-06-dual-path-build-and-diff-harness.md` | 2026-02-09 | Step 1/2/3 are now closed with frozen checkpoints (`BPL06-CP*`), fixture matrix (`BPL06-FX*`), severity/rollback/intake contracts (`BPL06-SEV-*`, `BPL06-RB-*`, `BPL06-INT-*`). |
| BPL-07 | done | P1 | `doc/wasm/backend-tickets/BPL-07-size-and-performance-gates.md` | 2026-02-10 | Step 3 criteria packet (`BPL07-CR01`..`BPL07-CR05`) has remediation run-v2 pass evidence (`bpl06-20260210-005408Z-91fdb0be`, `bpl07-20260210-005408Z-91fdb0be`) with backend preconditions satisfied and unified closure review now advancing `X-07` to `done`. |
| BPL-08 | done | P0 | `doc/wasm/backend-tickets/BPL-08-runtime-alignment-integration.md` | 2026-02-10 | Step 3 closure-readiness packet (`BPL08-CR01`..`BPL08-CR06`) remains immutable and is now consumed by unified closure review (`x07-closure-20260210-024503Z-91fdb0be`) that advances `X-07` to `done`. |
| BPL-09 | done | P0 | `doc/wasm/backend-tickets/BPL-09-cutover-and-arm-retirement.md` | 2026-02-10 | Step 3 signoff packet rows (`BPL09-CR01`..`BPL09-CR06`) now have committed run-v2 evidence (`bpl09-20260210-040314Z-2084077e`) and unified closure-review acceptance (`x08-closure-20260210-040400Z-2084077e`), preserving immutable bundle IDs/frozen `BPL08-CR*` rows while advancing `X-08` to `done`. |

## Ticket Details

### BPL-00 - Governance and Baseline Freeze

- Status: `in_progress`
- Priority: `P0`
- Last Updated: `2026-02-10`
- Subplan: `doc/wasm/backend-tickets/BPL-00-governance-and-baseline-freeze.md`
- Dependencies: none

Notes:

- This plan is now the canonical tracker for backend migration.
- Program-level coordination is anchored in `doc/wasm/wasm-program-board.md`.
- Cross-track dependencies are externalized to `doc/wasm/runtime-backend-dependency-matrix.md`.
- Governance evidence now includes BPL-03 Step 2 closure evidence (`FDC-*` + `B3*` coverage validation) with synchronized updates across matrix/program-board/master/subplan docs.
- Governance sync now includes RPL-03 Step 3 rerun evidence (`doc/wasm/tickets/evidence/rpl-03-step3-rerun-2026-02-09/`) with `status=pass` and closed `X-03`; backend advanced to BPL-07 after BPL-06 closure.
- Governance sync now includes RPL-04 Step 3 rerun evidence (`doc/wasm/tickets/evidence/rpl-04-step3-rerun-2026-02-10/`) with `status=pass`, `x04_step2_ready=true`, and dependency row `X-04` cleared to `done`.
- Governance sync now includes BPL-07 Step 1 baseline publication (`BPL07-BM01`..`BPL07-BM05`) with one-to-one checkpoint coverage over `BPL06-CP01`..`BPL06-CP05`.
- Governance sync now includes BPL-07 Step 2 run-v1 evidence publication (`doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-002604Z-91fdb0be/`) with deterministic row summaries and explicit fail-reason capture.
- Governance sync now includes BPL-07 Step 3 closure-readiness publication (`BPL07-CR01`..`BPL07-CR05`) with deterministic blocker criteria for missing BPL-06 intake artifacts and `BPL07-BM05` perf overrun.
- Governance sync now includes BPL-07 remediation run-v2 evidence (`bpl06-20260210-005408Z-91fdb0be`, `bpl07-20260210-005408Z-91fdb0be`) proving `CR01`..`CR03=pass` and backend readiness for `CR04`/`CR05`.
- Governance sync now includes BPL-08 Step 1 publication (`BPL08-IC01`..`BPL08-IC06`) keyed to frozen runtime/backend evidence bundles.
- Governance sync now includes BPL-08 Step 2 publication (`BPL08-IV01`..`BPL08-IV06`) with deterministic integration validation commands and immutable carry-forward bundle IDs.
- Governance sync now includes BPL-08 Step 3 publication (`BPL08-CR01`..`BPL08-CR06`) keyed to `BPL08-IV*` validation rows and unified closure review acceptance (`x07-closure-20260210-024503Z-91fdb0be`) with `X-07=done`.
- Governance sync now includes BPL-09 Step 1 publication (`BPL09-G01`..`BPL09-G08`, `BPL09-R01`..`BPL09-R06`, `BPL09-E01`..`BPL09-E06`) over frozen BPL-07/BPL-08 closure artifacts and runtime `RPL-09` Step 1 compatibility rows.
- Governance sync now includes BPL-09 Step 2 publication (`BPL09-L01`..`BPL09-L08`, `BPL09-V01`..`BPL09-V14`, `BPL09-I01`..`BPL09-I06`) aligned to runtime `RPL-09` Step 2 contracts and runtime Step 3 run-v1 evidence (`rpl09-20260210-032127Z-2084077e`).
- Governance sync now includes BPL-09 Step 3 signoff packet publication (`BPL09-CR01`..`BPL09-CR06`) with explicit runtime run-v2 (`R9GAP-01`) intake linkage and additive-only `X-08` hard-gate carry-forward posture.
- Governance sync now includes BPL-09 Step 3 run-v2 evidence (`bpl09-20260210-040314Z-2084077e`) and unified `X-08` closure review (`x08-closure-20260210-040400Z-2084077e`) with matrix transition to `X-08=done`.
- Governance sync now includes runtime `RPL-06 Step 3` run-v1 closure evidence (`rpl06-20260210-054023Z-50d752af`) with terminal `storage_v2_sync_step2_summary_v1.status=pass`.
- Fortieth governance maintenance cycle confirms additive-only no-drift synchronization across backend/runtime/program docs while keeping immutable `X-08` and `RPL-06` artifacts unchanged.

Next Step Analysis:

- Immediate Next Step: keep closed Pack D artifacts immutable while runtime/backend governance remains additive-only across the now-closed `RPL-06` sync/merge baseline.
- Why this step now: `X-08` is closed (`done`) and runtime `RPL-06` Step 3 closure evidence is now committed.
- Evidence required to close next step: synchronized docs retain immutable `x08-closure-20260210-040400Z-2084077e` and `bpl09-20260210-040314Z-2084077e` references, preserve frozen `BPL08-CR*`/`BPL09-*` rows, and consume `rpl06-20260210-054023Z-50d752af` without rewrites.

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

- Status: `done`
- Priority: `P0`
- Last Updated: `2026-02-09`
- Subplan: `doc/wasm/backend-tickets/BPL-04-numeric-and-math-pipeline-modernization.md`
- Dependencies: BPL-02

Notes:

- Numeric paths are primary overhead targets for ARM-facade removal.
- Step 1 is now closed with source-anchored family matrix `M4F-01`..`M4F-08` spanning direct-WASM, subprim/provider, and deferred tailcall-adjacent numeric paths.
- Step 1 output includes posture tags (`native_now`, `compat_layer`, `defer`) and benchmark hooks (`fixnum-add` smoke and aggregate smoke lane).
- Family rows are now anchored to contract/debug constraints (`CON-03`, `CON-04`, `CON-05`, `CON-06`, `FDC-10`) and assumption IDs (`ARM-ASSUMP-011`, `ARM-ASSUMP-012`).
- Step 2 is now closed with ordered BPL-05 sequence IDs covering all non-`native_now` families and explicit owner/cutover/evidence definitions.
- Step 3 is now closed with benchmark/profile gate IDs (`BPL04-G01`..`BPL04-G06`) defining commands, thresholds, and fail conditions per sequenced family.

Next Step Analysis:

- Immediate Next Step: maintain BPL-04 as a stable baseline and apply additive-only gate updates when new family slices are introduced.
- Why this step now: BPL-04 exit criteria are satisfied, so ongoing work is baseline maintenance rather than discovery/planning.
- Evidence required to close next step: any new numeric family or sequence row adds incremental `M4F-*`, `BPL04-S2-*`, and `BPL04-G*` IDs without rewriting closed rows.

---

### BPL-05 - IR/Lowering ARM Decoupling

- Status: `done`
- Priority: `P0`
- Last Updated: `2026-02-09`
- Subplan: `doc/wasm/backend-tickets/BPL-05-ir-lowering-arm-decoupling.md`
- Dependencies: BPL-02

Notes:

- Must remove ARM-shaped abstractions from backend lowering and codegen glue.
- Step 1 is now closed with staged decoupling slice map `B5S-01`..`B5S-05`.
- Slice map explicitly consumes BPL-04 sequence/gate outputs (`BPL04-S2-*`, `BPL04-G*`) and defines per-slice rollback seams.
- Assumption coverage now maps through explicit slice lanes (`ARM-ASSUMP-002`, `ARM-ASSUMP-007`, `ARM-ASSUMP-011`, `ARM-ASSUMP-012`, `ARM-ASSUMP-014`, `ARM-ASSUMP-015`).
- Step 2 is now closed with seam contract matrix `B5M-01`..`B5M-05`, including toggles, promotion criteria, rollback command paths, and `BPL06-CP*` checkpoints.
- Step 3 is now closed with consumer handoff checklist `B5H-01`..`B5H-05` across BPL-06/BPL-07/BPL-08 intake gates.

Next Step Analysis:

- Immediate Next Step: maintain BPL-05 as additive-only baseline and require downstream tickets to reference `B5S-*`/`B5M-*`/`B5H-*` IDs directly.
- Why this step now: BPL-05 exit criteria are satisfied, so remaining work is governance maintenance and downstream consumption.
- Evidence required to close next step: downstream subplans cite closed BPL-05 IDs without rewriting established seam/handoff rows.

---

### BPL-06 - Dual-Path Build and Differential Harness

- Status: `done`
- Priority: `P0`
- Last Updated: `2026-02-09`
- Subplan: `doc/wasm/backend-tickets/BPL-06-dual-path-build-and-diff-harness.md`
- Dependencies: BPL-03, BPL-04, BPL-05

Notes:

- Correctness parity is required before default-path cutover.
- Step 1 contract is now published with frozen checkpoint IDs (`BPL06-CP01`..`BPL06-CP05`) and deterministic parity/evidence field requirements (`exit_code`, `fail_markers`, output hashes, rollback command linkage).
- Step 1 now explicitly consumes BPL-05 seam linkage (`B5M-01`..`B5M-05`) and handoff constraints (`B5H-*`) without introducing alias IDs.
- Step 2 is now published with fixture matrix `BPL06-FX01`..`BPL06-FX05`, comparator template `BPL06-CMP-01`, and machine-fillable artifact templates under `doc/wasm/tickets/evidence/bpl-06/templates/`.
- Step 3 is now published with severity classes `BPL06-SEV-01`..`BPL06-SEV-04`, rollback obligations `BPL06-RB-01`..`BPL06-RB-05`, and BPL-07/BPL-08 intake mappings `BPL06-INT-01`..`BPL06-INT-05`.

Next Step Analysis:

- Immediate Next Step: maintain BPL-06 as additive-only baseline and require downstream tickets to consume frozen Step 1/2/3 IDs directly.
- Why this step now: BPL-06 exit criteria are satisfied, so remaining work is governance maintenance and downstream intake.
- Evidence required to close next step: BPL-07/BPL-08 subplans reference `BPL06-CP*`, `BPL06-FX*`, `BPL06-SEV-*`, `BPL06-RB-*`, and `BPL06-INT-*` without alias IDs.

---

### BPL-07 - Size and Performance Gates

- Status: `done`
- Priority: `P1`
- Last Updated: `2026-02-10`
- Subplan: `doc/wasm/backend-tickets/BPL-07-size-and-performance-gates.md`
- Dependencies: BPL-06

Notes:

- Migration must prove net positive impact on runtime cost and artifact shape.
- Step 1 budget and measurement baseline v1 is now published with stable row IDs `BPL07-BM01`..`BPL07-BM05`.
- Step 1 rows consume frozen BPL-06 intake contracts (`BPL06-INT-01`..`BPL06-INT-05`) and preserve rollback/severity linkage (`BPL06-SEV-*`, `BPL06-RB-*`) per checkpoint.
- Deterministic command mapping now exists for all frozen checkpoints (`BPL06-CP01`..`BPL06-CP05`) with explicit evidence paths under `doc/wasm/tickets/evidence/bpl-07/<run_id>/`.
- Step 2 run-v1 evidence is now published at `doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-002604Z-91fdb0be/` with full row coverage and deterministic summaries.
- Step 2 remediation run-v2 evidence is now published at `doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/`, keyed to intake run `bpl06-20260210-005408Z-91fdb0be`.
- `CR01`..`CR03` are now pass; `BPL07-BM05` perf delta is `-0.560224%` (budget max `+1.0%`) with `size_delta_bytes=0`.
- `X-06` is now `done` from runtime `RPL-07 Step 3 run-v2` closure evidence; unified closure review now advances `X-07` to `done`.
- Step 3 closure-readiness criteria remain `BPL07-CR01`..`BPL07-CR05`; backend preconditions are satisfied and unified closure review now marks `X-07` as `done`.

Next Step Analysis:

- Immediate Next Step: keep BPL-07 outputs immutable and consume frozen pass-bundle evidence in `BPL-09` cutover gate drafting.
- Why this step now: BPL-07 exit criteria are fully satisfied and `X-07` is now `done`.
- Evidence required to close next step: downstream `BPL-09` rows cite `BPL07-BM*` and `BPL07-CR*` artifacts without rewriting frozen IDs.

---

### BPL-08 - Runtime Alignment Integration

- Status: `done`
- Priority: `P0`
- Last Updated: `2026-02-10`
- Subplan: `doc/wasm/backend-tickets/BPL-08-runtime-alignment-integration.md`
- Dependencies: BPL-06, RPL-03, RPL-07

Notes:

- Backend and runtime shared-memory/call boundaries must align before cutover.
- Dependency row `X-03` is now `done`: protocol/conformance contracts and Step 3 rerun evidence are committed, so BPL-08 is unblocked from the runtime IPC side.
- BPL-08 Step 1 is now published with integration checkpoint/assertion IDs `BPL08-IC01`..`BPL08-IC06`.
- Step 1 rows are bound to immutable runtime/backend closure bundles (`rpl05-20260210-011240Z-91fdb0be`, `bpl06-20260210-005408Z-91fdb0be`, `bpl07-20260210-005408Z-91fdb0be`) and preserve frozen `BPL06-*`/`BPL07-*` contracts.
- Step 2 deterministic validation packet is now published with `BPL08-IV01`..`BPL08-IV06` command/evidence mappings for all Step 1 checkpoints.
- Step 3 closure-readiness packet is now published with `BPL08-CR01`..`BPL08-CR06` keyed one-to-one to `BPL08-IV01`..`BPL08-IV06`.

Next Step Analysis:

- Immediate Next Step: preserve published Step 3 closure packet as immutable closed baseline input while `BPL-09` cutover planning starts under `X-08`.
- Why this step now: BPL-08 step outputs are complete and unified closure review has now cleared `X-07`.
- Evidence required to close next step: `BPL-09` planning docs consume `BPL08-CR*` rows and immutable bundle IDs without rewrites.

---

### BPL-09 - Cutover and ARM Retirement

- Status: `done`
- Priority: `P0`
- Last Updated: `2026-02-10`
- Subplan: `doc/wasm/backend-tickets/BPL-09-cutover-and-arm-retirement.md`
- Dependencies: BPL-08, RPL-09

Notes:

- Final release must avoid unresolved dependency on ARM-facade behavior.
- Step 1 backend cutover/rollback contract is now published with frozen IDs `BPL09-G01`..`BPL09-G08`, `BPL09-R01`..`BPL09-R06`, and `BPL09-E01`..`BPL09-E06`.
- Step 1 gates are bound to committed backend closure evidence (`BPL08-CR01`..`BPL08-CR06`) plus runtime `RPL-09` contract compatibility and immutable bundle-ID checks.
- Step 2 deterministic rehearsal packet is now published with frozen IDs `BPL09-L01`..`BPL09-L08`, `BPL09-V01`..`BPL09-V14`, and `BPL09-I01`..`BPL09-I06`.
- Step 2 rows preserve immutable bundle IDs and explicit hard-gate carry-forward semantics; committed run-v2 evidence now resolves backend signoff checks with `x08_runtime_r9gap01_status=closed`.
- Step 3 signoff packet rows are now published with frozen IDs `BPL09-CR01`..`BPL09-CR06`, keyed to Step 2 validation/review contracts and runtime run-v2 intake requirements.
- Step 3 run-v2 evidence (`bpl09-20260210-040314Z-2084077e`) and unified closure review (`x08-closure-20260210-040400Z-2084077e`) are now committed, advancing `X-08` to `done`.

Next Step Analysis:

- Immediate Next Step: keep `BPL09-*` rows and committed closure artifacts immutable while closed `RPL-06` sync/merge evidence is consumed as downstream baseline.
- Why this step now: backend cutover closure criteria are satisfied, `X-08` is `done`, and runtime `RPL-06` closure evidence is now committed.
- Evidence required to close next step: downstream updates preserve `bpl09-20260210-040314Z-2084077e`, `x08-closure-20260210-040400Z-2084077e`, immutable bundle IDs, frozen `BPL08-CR*` rows, and `rpl06-20260210-054023Z-50d752af` over published `R6S-*`/`R6T-*`/`R6A-*` and `R6L-*`/`R6V-*` contracts.

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
- 2026-02-09: Synced backend governance notes with `X-03` transition to `in_progress` after RPL-03 Step 1 protocol publication (`IPCP-01`..`IPCP-49`); kept BPL-08 explicitly hard-gated pending Step 2 conformance evidence.
- 2026-02-09: Synced backend governance notes with RPL-03 Step 2 conformance publication (`IPCV-01`..`IPCV-12`, `IPCL-01`..`IPCL-05`) and kept BPL-08 explicitly hard-gated pending Step 3 committed evidence.
- 2026-02-09: Synced backend governance notes with RPL-03 Step 3 run-v1 evidence (status `fail`) and kept BPL-08 explicitly hard-gated pending rerun closure evidence.
- 2026-02-09: Started BPL-04 and closed Step 1 with source-anchored operation-family matrix (`M4F-01`..`M4F-08`); advanced backend immediate next action to BPL-04 Step 2 sequencing.
- 2026-02-09: Closed BPL-04 Step 2 by sequencing non-`native_now` families into ordered BPL-05 slices with explicit cutover triggers/evidence gates; advanced backend immediate next action to BPL-04 Step 3 benchmark alignment.
- 2026-02-09: Closed BPL-04 Step 3 by publishing benchmark/profile gate matrix (`BPL04-G01`..`BPL04-G06`) and advanced backend immediate next action to BPL-05 Step 1 staged decoupling.
- 2026-02-09: Started BPL-05 and closed Step 1 with staged decoupling slice map (`B5S-01`..`B5S-05`); advanced backend immediate next action to BPL-05 Step 2 seam contracts.
- 2026-02-09: Closed BPL-05 Step 2 by publishing seam contract matrix (`B5M-01`..`B5M-05`) and advanced backend immediate next action to BPL-05 Step 3 handoff/gate integration.
- 2026-02-09: Closed BPL-05 Step 3 by publishing consumer handoff checklist (`B5H-01`..`B5H-05`) and advanced backend immediate next action to BPL-06 Step 1 harness contract definition.
- 2026-02-09: Synced backend governance notes with RPL-03 Step 3 rerun evidence (`status=pass`, `x03_clear_ready=true`), closed dependency row `X-03`, and marked BPL-08 runtime-side hard gate as cleared.
- 2026-02-09: Started BPL-06 and closed Step 1 by publishing dual-build checkpoint contracts (`BPL06-CP01`..`BPL06-CP05`) mapped to seam rows (`B5M-01`..`B5M-05`); advanced backend immediate next action to BPL-06 Step 2 fixture/evidence-template publication.
- 2026-02-09: Closed BPL-06 Step 2 by publishing deterministic fixture matrix (`BPL06-FX01`..`BPL06-FX05`) and evidence templates (`backend_diff_case_result_v1`, `backend_diff_checkpoint_summary_v1`); advanced backend immediate next action to BPL-06 Step 3 triage/gate-integration definition.
- 2026-02-09: Closed BPL-06 Step 3 by publishing severity classes (`BPL06-SEV-*`), rollback obligations (`BPL06-RB-*`), and BPL-07/BPL-08 intake mappings (`BPL06-INT-*`); advanced backend immediate next action to BPL-07 Step 1 budget/measurement setup.
- 2026-02-10: Synced backend governance notes with RPL-04 Step 3 rerun closure evidence (`rpl-04-step3-rerun-2026-02-10`), cleared dependency row `X-04`, and retained backend immediate next action on BPL-07 Step 1 budget/measurement setup.
- 2026-02-10: Started BPL-07 and closed Step 1 by publishing budget/measurement baseline rows (`BPL07-BM01`..`BPL07-BM05`) mapped one-to-one to frozen `BPL06-CP01`..`BPL06-CP05`; immediate backend next action advanced to BPL-07 Step 2 run-v1 evidence execution.
- 2026-02-10: Resynced Pack A execution posture to runtime `RPL-05 Step 1` completion + backend continuation on `BPL-07 Step 1` over frozen `BPL06-*` intake artifacts; backend next action remains Step 1 baseline hardening/consumption.
- 2026-02-10: Executed BPL-07 Step 2 run-v1 measurement packet (`bpl07-20260210-002604Z-91fdb0be`) with full `BPL07-BM01`..`BPL07-BM05` evidence publication; next backend action advanced to BPL-07 Step 3 soft-gate readiness definition due missing BPL-06 intake artifacts and `BPL07-BM05` perf overrun.
- 2026-02-10: Closed BPL-07 Step 3 by publishing closure-readiness criteria (`BPL07-CR01`..`BPL07-CR05`) for `X-06`/`X-07`; next backend action is now one remediation execution packet to clear missing intake artifacts and the `BPL07-BM05` perf overrun.
- 2026-02-10: Executed BPL-07 remediation run-v2 (`bpl07-step3-remediation-run-v2`) with intake bundle `bpl06-20260210-005408Z-91fdb0be` and rerun packet `bpl07-20260210-005408Z-91fdb0be`; `CR01`..`CR03` now pass and backend closure readiness for `CR04`/`CR05` is synchronized.
- 2026-02-10: Resynced immediate-next-step wording across backend/master/matrix/board/governance docs to Pack A runtime run-v2 execution while preserving backend run-v2 pass bundle as `X-06`/`X-07` closure-review input.
- 2026-02-10: Started BPL-08 and closed Step 1 by publishing integration checkpoint/assertion baseline (`BPL08-IC01`..`BPL08-IC06`) over frozen runtime/backend closure bundles; advanced backend next action to BPL-08 Step 2 deterministic validation packet definition.
- 2026-02-10: Closed BPL-08 Step 2 by publishing deterministic integration validation packet rows (`BPL08-IV01`..`BPL08-IV06`) and advanced backend next action to BPL-08 Step 3 closure-readiness packet publication while preserving `X-07=open`.
- 2026-02-10: Closed BPL-08 Step 3 by publishing integration closure-readiness rows (`BPL08-CR01`..`BPL08-CR06`) keyed to `BPL08-IV01`..`BPL08-IV06`, preserving immutable bundle IDs and explicit `X-07=open` carry-forward posture.
- 2026-02-10: Completed unified `X-07` closure review (`x07-closure-20260210-024503Z-91fdb0be`), advanced matrix row `X-07` to `done`, promoted `BPL-07`/`BPL-08` to `done`, and shifted immediate backend action to `BPL-09 Step 1` cutover planning.
- 2026-02-10: Started BPL-09 and closed Step 1 by publishing backend cutover/rollback contract rows (`BPL09-G01`..`BPL09-G08`, `BPL09-R01`..`BPL09-R06`, `BPL09-E01`..`BPL09-E06`); shifted immediate backend action to `BPL-09 Step 2` rehearsal packetization.
- 2026-02-10: Closed BPL-09 Step 2 by publishing deterministic rehearsal packet rows (`BPL09-L01`..`BPL09-L08`, `BPL09-V01`..`BPL09-V14`, `BPL09-I01`..`BPL09-I06`); shifted immediate backend action to `BPL-09 Step 3` signoff packetization while runtime executes `RPL-09 Step 3` run-v2 for `R9GAP-01`.
- 2026-02-10: Closed BPL-09 Step 3 by publishing backend signoff packet rows (`BPL09-CR01`..`BPL09-CR06`) keyed to frozen Step 2 contracts with runtime run-v2 intake linkage; immediate cross-track action now focuses on runtime `RPL-09 Step 3` run-v2 closure and joint `X-08` review execution.
- 2026-02-10: Executed backend Step 3 run-v2 evidence packet (`bpl09-20260210-040314Z-2084077e`), committed unified `X-08` closure review (`x08-closure-20260210-040400Z-2084077e`), advanced matrix row `X-08` to `done`, and shifted immediate cross-track action to runtime `RPL-01` contradiction follow-through with additive-only backend governance maintenance.
- 2026-02-10: Decomposed runtime contradiction follow-through into ordered `RPL01-CF-*` tasks and synchronized backend immediate-next-step wording to execute `RPL01-CF-01` first while preserving immutable `X-08` artifacts.
- 2026-02-10: Synced backend immediate-next-step wording after completion of `RPL01-CF-01`..`RPL01-CF-04`; active runtime contradiction task is now `RPL01-CF-05` (`C-02`) with immutable `X-08` artifacts preserved.
- 2026-02-10: Synced backend immediate-next-step wording after completion of `RPL01-CF-05`; active runtime contradiction task is now `RPL01-CF-06` (`C-05`) with immutable `X-08` artifacts preserved.
- 2026-02-10: Synced backend immediate-next-step wording after completion of `RPL01-CF-06`; active runtime contradiction task is now `RPL01-CF-07` (`C-06`) with immutable `X-08` artifacts preserved.
- 2026-02-10: Synced backend immediate-next-step wording after contradiction source rewrites completed through `RPL01-CF-14`; active runtime follow-through is now `RPL01-CF-15` contradiction-closure synchronization with immutable `X-08` artifacts preserved.
- 2026-02-10: Synced backend immediate-next-step wording after contradiction closure sync (`RPL01-CF-15`) completion; active runtime follow-through is now `RPL01-IG-01` startup-gate loader/smoke integration with immutable `X-08` artifacts preserved.
- 2026-02-10: Synced backend immediate-next-step wording after `RPL01-IG-01` completion; active runtime follow-through is now `RPL01-IG-02` startup-gate coverage expansion (`LHI-04`/`LHI-05`/`LHI-06`) with immutable `X-08` artifacts preserved.
- 2026-02-10: Synced backend immediate-next-step wording after `RPL01-IG-02` closure and `RPL-06` Step 1 publication; active runtime action is now `RPL-06` Step 2 validation-lane matrix drafting with immutable `X-08` artifacts preserved.
- 2026-02-10: Synced backend immediate-next-step wording after `RPL-06` Step 2 publication; active runtime action is now `RPL-06` Step 3 evidence execution with immutable `X-08` artifacts preserved.
- 2026-02-10: Synced backend immediate-next-step wording after runtime `RPL-06` Step 3 run-v1 closure evidence (`rpl06-20260210-054023Z-50d752af`); Pack D artifacts remain immutable and cross-track governance is now additive-only maintenance.
- 2026-02-10: Completed fortieth backend governance maintenance cycle by verifying no drift across immutable `X-08`/`RPL-06` run IDs and frozen closure rows in master/subplan/matrix/program docs; immediate action remains additive-only maintenance.
