# BPL-05 - IR/Lowering ARM Decoupling

Status: done  
Priority: P0  
Owner: Compiler/backend migration track  
Last Updated: 2026-02-09  
Parent Plan: `doc/wasm/backend-migration-master-plan.md`

## Scope

In scope:

- Define staged IR/lowering decoupling slices that remove ARM-shaped assumptions from WASM backend codegen.
- Bind each decoupling slice to BPL-04 sequence/gate IDs and BPL-01 assumption anchors.
- Define rollback seams so BPL-06 differential harness can bisect regressions deterministically.

Out of scope:

- Runtime IPC/protocol closure work (`RPL-03` ownership).
- Final cutover policy and legacy retirement (`BPL-09` ownership).
- Size/perf budget signoff (`BPL-07` ownership).

## Dependencies

- BPL-02 contract baseline (`CON-*`).
- BPL-03 frame/debug baseline (`FDC-*`).
- BPL-04 sequence/gate outputs (`BPL04-S2-*`, `BPL04-G*`).
- BPL-01 inventory assumptions (`ARM-ASSUMP-*`).

## Deliverables

1. Step 1 staged decoupling slice map with owner, rollback seam, and evidence gates.
2. Step 2 migration seam contract for dual-path operation and bisectability.
3. Step 3 implementation handoff checklist for BPL-06/BPL-07 consumers.

## Exit Criteria

- All targeted ARM-shaped lowering assumptions are assigned to deterministic decoupling slices.
- Each slice has one owner, explicit rollback seam, and concrete evidence gates.
- Sequence is consumable by BPL-06 diff harness without re-discovery.

## Current Notes

- BPL-04 sequencing/gate outputs are now closed and stable (`BPL04-S2-01`..`BPL04-S2-05`, `BPL04-G01`..`BPL04-G06`).
- High-risk decoupling lanes are callsite normalization, fallback retirement, manifest/entrypoint decoupling, and tail-recursive frame reuse.
- Step 1 staged map is now published below.
- Step 2 seam contract matrix is now published with deterministic toggle/rollback/checkpoint semantics per slice.
- Step 3 consumer handoff checklist is now published for BPL-06/BPL-07/BPL-08 intake.

## Immediate Next Step

- Action: consume BPL-05 closed artifacts in BPL-06 Step 1 dual-build/harness contract definition.
- Why now: Step 1/2/3 planning artifacts are complete, so BPL-05 shifts to baseline maintenance and downstream consumption.
- Success evidence: BPL-06 Step 1 references `B5S-*`/`B5M-*` IDs directly in dual-build and diff-checkpoint contracts.

## Step 1 Output - Staged Decoupling Slice Map (v1)

| slice_id | stage | decoupling objective | primary assumptions targeted | consumes BPL-04 sequence/gates | owner | rollback seam | evidence gates |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B5S-01 | S1 | Normalize compiler numeric callsites away from ARM-shaped subprim coupling in hot arithmetic paths. | `ARM-ASSUMP-002`, `ARM-ASSUMP-007` | `BPL04-S2-01`, `BPL04-S2-02`; `BPL04-G01`, `BPL04-G02` | compiler lowering owner | keep compat callsite path behind dual-path toggle until diff parity passes | `CON-03`, `CON-04`, `BPL04-G01`, `BPL04-G02` |
| B5S-02 | S2 | Retire fixed numeric entrypoint slot assumptions by enforcing manifest-driven lookup in lowering/provider glue. | `ARM-ASSUMP-011`, `ARM-ASSUMP-014` | `BPL04-S2-03`; `BPL04-G03` | module/loader + provider owner | preserve previous slot map as fallback-disabled compat fixture for bisect only | `CON-05`, `CON-03`, `BPL04-G03` |
| B5S-03 | S3 | Narrow low-level division helper compatibility paths and align with no-fallback contract posture. | `ARM-ASSUMP-002`, `ARM-ASSUMP-007` | `BPL04-S2-04`; `BPL04-G04` | subprims/provider owner | retain helper path under explicit compat toggle for regression isolation | `CON-06`, `CON-03`, `BPL04-G04` |
| B5S-04 | S4 | Implement tail-recursive numeric frame-reuse decoupling from `_SPfuncall` wrappers with frame/debug invariants preserved. | `ARM-ASSUMP-012`, `ARM-ASSUMP-009` | `BPL04-S2-05`; `BPL04-G05` | subprims/runtime execution owner | route through compat wrapper path if frame/debug invariant gates fail | `FDC-10`, `FDC-03`, `BPL04-G05` |
| B5S-05 | S5 | Consolidate cross-slice verification and lock additive gate discipline for BPL-06/BPL-07 consumers. | `ARM-ASSUMP-013`, `ARM-ASSUMP-015` | all `BPL04-S2-*`; `BPL04-G06` | backend governance + lowering owner | freeze at last green slice boundary and block further promotion | `BPL04-G06`, `CON-08` |

Step 1 closure assertions:

1. Every decoupling slice is ordered, owner-assigned, and tied to concrete BPL-04 sequence/gate evidence.
2. Rollback seams are explicit per slice and suitable for BPL-06 diff-harness bisect workflows.
3. No slice reopens closed contract/frame semantics; all anchors stay additive (`CON-*`, `FDC-*`, `BPL04-*`).

## Step 2 Output - Dual-Path Seam Contract Matrix (v1)

| seam_id | linked_slice_id | feature toggle contract | default mode | promotion criterion | rollback criterion | rollback command path | BPL-06 checkpoint linkage | evidence anchors |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B5M-01 | `B5S-01` | `WASM_LOWERING_NUMERIC_CALLSITE_MODE={compat,native}` | `compat` | Promote to `native` only after `BPL04-G01` and `BPL04-G02` pass in two consecutive checkpoints and diff harness mismatch rate is zero. | Any regression in aggregate smoke or any diff mismatch in promoted lane. | Set `WASM_LOWERING_NUMERIC_CALLSITE_MODE=compat`; rerun checkpoint lane and record regression artifact. | `BPL06-CP01` numeric-callsite parity checkpoint | `BPL04-G01`, `BPL04-G02`, `CON-03`, `CON-04` |
| B5M-02 | `B5S-02` | `WASM_ENTRYPOINT_LOOKUP_MODE={slot,manifest}` | `slot` | Promote to `manifest` after `BPL04-G03` passes and no manifest/entrypoint mismatch is observed in loader lane. | Any loader/manifest disagreement or slot/manifest map drift in promoted lane. | Set `WASM_ENTRYPOINT_LOOKUP_MODE=slot`; restore previous map fixture for bisect and rerun lane. | `BPL06-CP02` entrypoint-resolution parity checkpoint | `BPL04-G03`, `CON-05`, `CON-03` |
| B5M-03 | `B5S-03` | `WASM_DIV_HELPER_MODE={compat,native}` | `compat` | Promote to `native` after `BPL04-G04` pass and no fallback-policy violations across checkpoint runs. | Any no-fallback violation, helper dispatch regression, or non-zero lane exit post-promotion. | Set `WASM_DIV_HELPER_MODE=compat`; rerun regression lane and preserve failing sample artifact. | `BPL06-CP03` helper-dispatch parity checkpoint | `BPL04-G04`, `CON-06`, `CON-03` |
| B5M-04 | `B5S-04` | `WASM_TAILCALL_NUMERIC_MODE={wrapper,frame_reuse}` | `wrapper` | Promote to `frame_reuse` only after `BPL04-G05` pass with no frame/debug invariant violations. | Any `FDC-10` or `FDC-03` invariant failure, stack-growth regression signal, or non-zero strict lane exit. | Set `WASM_TAILCALL_NUMERIC_MODE=wrapper`; rerun strict + aggregate lanes and attach frame/debug diff output. | `BPL06-CP04` tailcall-frame parity checkpoint | `BPL04-G05`, `FDC-10`, `FDC-03` |
| B5M-05 | `B5S-05` | `WASM_LOWERING_PROMOTION_POLICY={hold,advance}` | `hold` until slice gates pass | Set `advance` only when `BPL04-G06` stays green at every slice boundary and all active seam checkpoints are green. | Any checkpoint regression or unresolved mismatch in any active seam. | Set `WASM_LOWERING_PROMOTION_POLICY=hold`; freeze promotion at last green slice and open remediation task. | `BPL06-CP05` cross-slice governance checkpoint | `BPL04-G06`, `CON-08` |

Step 2 closure assertions:

1. Every slice `B5S-01`..`B5S-05` now maps to exactly one seam contract row (`B5M-01`..`B5M-05`).
2. Every seam row includes explicit toggle, promotion criterion, rollback criterion, and rollback command path.
3. Every seam row is linked to a deterministic BPL-06 checkpoint and concrete evidence anchors.

## Step 3 Output - Consumer Handoff and Gate Integration Checklist (v1)

| handoff_id | consumer ticket | required input artifacts | required owner acceptance criteria | blocking status before consumer start | handoff owner |
| --- | --- | --- | --- | --- | --- |
| B5H-01 | BPL-06 dual-path harness | `B5S-01`..`B5S-05`; `B5M-01`..`B5M-05`; `BPL04-G01`..`BPL04-G06` | BPL-06 must declare diff checkpoints `BPL06-CP01`..`BPL06-CP05` and map each to seam promotion/rollback criteria without aliasing IDs. | hard requirement | backend governance + harness owner |
| B5H-02 | BPL-06 dual-path harness | Rollback command paths from `B5M-*` rows | BPL-06 must include deterministic rollback execution order per seam and one bisect checkpoint artifact per slice boundary. | hard requirement | harness owner |
| B5H-03 | BPL-07 size/perf gates | `BPL04-G*` gate commands; seam promotion criteria from `B5M-*` | BPL-07 must bind performance reporting to seam checkpoints and reject promotion if any required gate is missing or stale. | soft requirement (before signoff) | performance gate owner |
| B5H-04 | BPL-08 runtime alignment integration | `B5M-02` manifest seam contract; `B5M-04` frame/tail seam contract; `CON-05`, `FDC-10` anchors | BPL-08 must assert ABI/manifest compatibility checkpoints that explicitly consume seam IDs and do not reopen closed contract semantics. | soft requirement (before integration merge) | runtime-alignment owner |
| B5H-05 | BPL-06/BPL-07/BPL-08 cross-consumer sync | Closed dependency rows `X-02`, `X-03` evidence posture and immutable ID set (`SRG-*`, `WTOP-*`, `WSEQ-*`, `WLCS-*`, `WLCT-*`, `WLCR-*`, `B3*`, `FDC-*`) | Consumer tickets must preserve frozen IDs and additive-only update policy; any new semantics require additive IDs and synchronized governance updates. | hard requirement | backend governance owner |

Step 3 closure assertions:

1. All required downstream consumers (BPL-06, BPL-07, BPL-08) now have explicit intake artifacts and acceptance criteria.
2. Handoff rows are deterministic and reference only frozen upstream IDs (`B5S-*`, `B5M-*`, `BPL04-G*`, `CON-*`, `FDC-*`).
3. No consumer handoff row introduces speculative dependencies or reopens closed runtime/backend gate evidence.

## Detailed Work Breakdown

### Step 1 - Staged Decoupling Slice Definition

- Status: done
- Notes:
  - Published ordered slices `B5S-01`..`B5S-05` with assumption coverage, owners, rollback seams, and evidence gates.
  - Linked each slice to concrete `BPL04-S2-*` and `BPL04-G*` outputs.
- Next:
  - Freeze slice IDs and stage order while Step 2 seam contracts are authored.

### Step 2 - Dual-Path Migration Seam Contracts

- Status: done
- Notes:
  - Published seam matrix `B5M-01`..`B5M-05` with explicit toggles, promotion criteria, rollback controls, and BPL-06 checkpoint links.
  - Seam contracts now provide deterministic promotion/rollback gates for each decoupling slice.
- Next:
  - Keep seam IDs stable; introduce additive seam rows only if new slices are introduced.

### Step 3 - Handoff and Gate Integration

- Status: done
- Notes:
  - Published consumer handoff checklist `B5H-01`..`B5H-05` with required artifacts and acceptance criteria for BPL-06/BPL-07/BPL-08.
  - Linked BPL-06 checkpoint contracts and downstream gate obligations directly to closed seam/slice artifacts.
- Next:
  - Maintain BPL-05 as additive-only baseline; route new decoupling semantics through new `B5S-*`/`B5M-*`/`B5H-*` IDs.

## Test and Validation Plan

- Slice coverage validation:
  - Verify each `B5S-*` row has assumptions, owner, rollback seam, and evidence gates.
- Anchor integrity validation:
  - Verify all `BPL04-S2-*` and `BPL04-G*` references exist and are stable.
- Governance validation:
  - Verify master-plan immediate-next-step and BPL-05 detail notes match this ticket in the same change.

## Risks and Mitigations

- Risk: decoupling slices overlap and lose bisectability.
  - Mitigation: one objective per slice with explicit rollback seam.
- Risk: slice rollout silently weakens no-fallback contract posture.
  - Mitigation: require `CON-06`/`CON-08` evidence on affected slices before promotion.
- Risk: tail-recursive path changes regress frame/debug behavior.
  - Mitigation: gate S4 on explicit `FDC-10` + `BPL04-G05` evidence.

## Change Log

- 2026-02-09: Initialized BPL-05 and closed Step 1 with staged decoupling slice map (`B5S-01`..`B5S-05`) linked to `BPL04-S2-*` and `BPL04-G*`.
- 2026-02-09: Closed Step 2 by publishing seam contract matrix (`B5M-01`..`B5M-05`) with explicit toggles, promotion criteria, rollback command paths, and BPL-06 checkpoint linkage.
- 2026-02-09: Closed Step 3 by publishing consumer handoff checklist (`B5H-01`..`B5H-05`) for BPL-06/BPL-07/BPL-08 intake and acceptance gating.
