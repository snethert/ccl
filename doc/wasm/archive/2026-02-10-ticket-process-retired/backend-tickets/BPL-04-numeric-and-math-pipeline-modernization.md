# BPL-04 - Numeric and Math Pipeline Modernization

Status: done  
Priority: P0  
Owner: Compiler/backend migration track  
Last Updated: 2026-02-09  
Parent Plan: `doc/wasm/backend-migration-master-plan.md`

## Scope

In scope:

- Classify numeric/math operation families in current WASM backend lowering.
- Define per-family WASM-native lowering posture (`native_now`, `compat_layer`, `defer`).
- Publish benchmark hooks that can be used by BPL-07 and BPL-09 cutover gates.

Out of scope:

- Full lowering decoupling implementation (BPL-05 ownership).
- Runtime worker/protocol design changes (RPL ownership).
- Cutover policy and retirement execution (BPL-09 ownership).

## Dependencies

- BPL-01 assumption inventory closure (`ARM-ASSUMP-*`).
- BPL-02 contract baseline (`CON-01`..`CON-08`).
- BPL-03 frame/debug baseline (`FDC-01`..`FDC-10`).

## Deliverables

1. Step 1 operation-family strategy matrix with concrete source anchors.
2. Step 2 family sequencing plan with explicit owners and dependency gates.
3. Step 3 benchmark/profile checklist tied to BPL-07 performance gates.
4. Synchronized master/matrix updates when dependency posture changes.

## Exit Criteria

- Every high-volume numeric family has a documented lowering posture and owner.
- No family remains unclassified between direct WASM ops vs subprim/provider path.
- Benchmark hooks are explicit and runnable for at least one fixnum and one aggregate lane.
- Any cross-track dependency change is reflected in matrix/master in the same change.

## Current Notes

- BPL-01 already identified numeric-adjacent migration pressure from fixed entrypoint slots and tailcall wrapper behavior (`ARM-ASSUMP-011`, `ARM-ASSUMP-012`).
- BPL-02 contract baseline already prohibits fallback numeric transport semantics (`CON-06`) and pins manifest/dispatch requirements (`CON-03`, `CON-05`).
- BPL-03 frame/debug baseline constrains numeric-path call boundaries and tail behavior observability (`FDC-03`, `FDC-10`).
- Step 1 classification is now published below with explicit family IDs (`M4F-*`) and benchmark hooks.
- Step 2 sequencing is now published with ordered BPL-05 slices and explicit cutover/evidence gates for all non-`native_now` families.
- Step 3 benchmark/profile gates are now published and aligned to sequenced families for BPL-07 consumption.

## Immediate Next Step

- Action: hand off closed BPL-04 outputs to BPL-05 by mapping sequence IDs (`BPL04-S2-*`) into staged lowering decoupling implementation slices.
- Why now: Step 1/2/3 outputs are now complete and deterministic, so the critical path moves to implementation sequencing in BPL-05.
- Success evidence: BPL-05 publishes staged decoupling slices that consume `BPL04-S2-*` and preserve Step 3 gate semantics.

## Step 1 Output - Numeric Operation Family Strategy Matrix (v1)

| family_id | operation family | representative source anchors | current lowering shape | migration posture | owner | dependency anchors | benchmark hook (initial) | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M4F-01 | fixnum add/sub/mul hot path | `compiler/WASM/wasm2.lisp:149`; `compiler/WASM/wasm2.lisp:185`; `compiler/WASM/wasm2.lisp:245` | direct WASM fixnum ops (`:fixnum-add`, `:fixnum-sub`, `:fixnum-mul`) | native_now | compiler lowering | `CON-04`, `CON-06` | `node doc/wasm/js/fixnum-add-smoke.mjs` | classified |
| M4F-02 | generic integer divide and negate | `compiler/WASM/wasm2.lisp:269`; `compiler/WASM/wasm2.lisp:285` | subprim call path (`.SPbuiltin-div`, `.SPbuiltin-negate`) | compat_layer | compiler lowering + subprims | `CON-03`, `ARM-ASSUMP-002` | `node doc/wasm/js/all-smoke.mjs` | classified |
| M4F-03 | shift and generalized bit arithmetic | `compiler/WASM/wasm2.lisp:309`; `compiler/WASM/wasm2.lisp:450`; `compiler/WASM/wasm2.lisp:474` | mixed: direct fixnum emit + subprim fallback (`.SPbuiltin-ash`) | compat_layer | compiler lowering | `CON-03`, `CON-04`, `ARM-ASSUMP-007` | `node doc/wasm/js/all-smoke.mjs` | classified |
| M4F-04 | short-float arithmetic | `compiler/WASM/wasm2.lisp:615`; `compiler/WASM/wasm2.lisp:625`; `compiler/WASM/wasm2.lisp:635`; `compiler/WASM/wasm2.lisp:645` | direct `f32-*` ops with explicit box/unbox | native_now | compiler lowering | `CON-04` | `node doc/wasm/js/all-smoke.mjs` | classified |
| M4F-05 | float comparison/select materialization | `compiler/WASM/wasm2.lisp:655`; `compiler/WASM/wasm2.lisp:671` | direct float compare op + `:select` to Lisp boolean | native_now | compiler lowering | `CON-04`, `FDC-03` | `node doc/wasm/js/all-smoke.mjs` | classified |
| M4F-06 | width conversion and integer boxing helpers | `lisp-kernel/wasm-subprims-provider.c:4488`; `lisp-kernel/wasm-subprims-provider.c:4503`; `lisp-kernel/wasm-subprims-provider.c:4581` | provider-side subprims (`_SPmakes32`, `_SPmakeu32`, `_SPmakes64`, `_SPmakeu64`) | compat_layer | subprims/provider | `CON-03`, `CON-05`, `ARM-ASSUMP-011` | `node doc/wasm/js/all-smoke.mjs` | classified |
| M4F-07 | low-level division helpers (`u/s div`) | `lisp-kernel/wasm-subprims-provider.c:4667`; `lisp-kernel/wasm-subprims-provider.c:6016`; `lisp-kernel/wasm-subprims-provider.c:6037` | provider-side arithmetic helpers | compat_layer | subprims/provider | `CON-03`, `CON-06` | `node doc/wasm/js/all-smoke.mjs` | classified |
| M4F-08 | tailcall-adjacent numeric recursion behavior | `lisp-kernel/wasm-subprims-provider.c:2083`; `doc/wasm/backend-tickets/BPL-03-frame-and-debug-metadata-model.md:133`; `doc/wasm/backend-tickets/BPL-01-arm-assumption-inventory.md:82` | tail wrappers route through `_SPfuncall` (no frame reuse) | defer | subprims/runtime execution | `FDC-10`, `ARM-ASSUMP-012` | `node doc/wasm/js/all-smoke.mjs` | classified |

Step 1 closure assertions:

1. All identified numeric families are now classified with a migration posture and owner.
2. Each family has concrete source anchors and at least one initial benchmark hook.
3. Non-`native_now` families are explicitly tied to contract/assumption IDs for Step 2 sequencing.

## Step 2 Output - Non-`native_now` Family Sequencing (v1)

| sequence_id | ordered BPL-05 slice | family_id | primary owner | cutover trigger | evidence gates (must all pass) | downstream handoff |
| --- | --- | --- | --- | --- | --- | --- |
| BPL04-S2-01 | S1 - Compiler callsite normalization | `M4F-02` | compiler lowering owner | Generic integer divide/negate lowering no longer emits direct `.SPbuiltin-div`/`.SPbuiltin-negate` callsites from compiler paths that have a WASM-native lowering replacement. | `CON-03` dispatch integrity checks pass; `CON-04` call-boundary checks pass; aggregate smoke lane remains green (`node doc/wasm/js/all-smoke.mjs`). | BPL-05 S2 |
| BPL04-S2-02 | S2 - Shift/bitwise fallback retirement | `M4F-03` | compiler lowering owner | `.SPbuiltin-ash` fallback usage is eliminated or constrained to explicitly-versioned compat path, while direct fixnum bit ops stay default. | `CON-03` and `CON-04` evidence attached; no-fallback posture remains intact per `CON-06`; aggregate smoke lane green. | BPL-05 S3 |
| BPL04-S2-03 | S3 - Width/boxing manifest decoupling | `M4F-06` | subprims/provider owner | Width-conversion helper selection moves to manifest/version contract instead of fixed slot assumptions for replacement lanes. | `CON-05` manifest/version checks pass; `CON-03` mapping checks pass; `ARM-ASSUMP-011` cutover note updated to remove fixed-slot dependency in active lane. | BPL-05 S4 + BPL-08 readiness note |
| BPL04-S2-04 | S4 - Division helper compatibility narrowing | `M4F-07` | subprims/provider owner | Low-level `u/s div` helpers are restricted to compatibility boundary or replaced by validated WASM-native lowering path in hot lanes. | `CON-03` dispatch validation passes; `CON-06` no-fallback transport semantics preserved; aggregate smoke lane green plus any new numeric lane check documented. | BPL-05 S5 |
| BPL04-S2-05 | S5 - Tail-recursive numeric frame reuse cutover | `M4F-08` | subprims/runtime execution owner | Tailcall wrappers no longer route through `_SPfuncall` for target paths and frame reuse semantics are explicit for numeric recursion. | `FDC-10` cutover condition satisfied; frame/debug assertions remain valid (`FDC-03`, `FDC-10`); `ARM-ASSUMP-012` strategy row updated from defer-only to cutover-complete evidence reference. | BPL-05 S6 + BPL-03 additive update |

Step 2 closure assertions:

1. All required non-`native_now` families (`M4F-02`, `M4F-03`, `M4F-06`, `M4F-07`, `M4F-08`) are sequenced with explicit order.
2. Every sequence row names one primary owner and one concrete cutover trigger.
3. Every sequence row includes explicit evidence gates anchored to `CON-*`, `FDC-*`, and/or `ARM-ASSUMP-*` identifiers.

## Step 3 Output - Benchmark and Profile Gates (v1)

| gate_id | linked sequence_id | family scope | metric definition | command lane | pass threshold | fail condition | consumer |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BPL04-G01 | `BPL04-S2-01` | `M4F-02` divide/negate | Integer-divide/negate lane remains functionally correct under normalized compiler callsites. | `node doc/wasm/js/all-smoke.mjs` | Command exits `0`; no FAIL markers; startup/runtime gate summaries remain pass. | Any non-zero exit, FAIL marker, or contract assertion failure in aggregated lane. | BPL-05 S2, BPL-07 |
| BPL04-G02 | `BPL04-S2-02` | `M4F-03` shift/bitwise | Shift/bitwise behavior remains deterministic while `.SPbuiltin-ash` fallback is narrowed. | `node doc/wasm/js/all-smoke.mjs` | Command exits `0`; no fallback-policy failure surfaces; no regressions in aggregate lane output. | Any fallback-policy violation, non-zero exit, or behavioral regression marker. | BPL-05 S3, BPL-07 |
| BPL04-G03 | `BPL04-S2-03` | `M4F-06` width/boxing | Manifest-driven width/boxing helper path preserves replacement-lane correctness. | `node doc/wasm/js/all-smoke.mjs` | Command exits `0`; no manifest/entrypoint mismatch failures. | Any loader/manifest mismatch, non-zero exit, or compatibility-path misroute. | BPL-05 S4, BPL-08, BPL-07 |
| BPL04-G04 | `BPL04-S2-04` | `M4F-07` low-level division helpers | Helper narrowing does not reintroduce no-fallback violations or arithmetic-lane instability. | `node doc/wasm/js/all-smoke.mjs` | Command exits `0`; no no-fallback policy failures; aggregate lane pass. | Any no-fallback breach, non-zero exit, or helper dispatch regression signal. | BPL-05 S5, BPL-07 |
| BPL04-G05 | `BPL04-S2-05` | `M4F-08` tail-recursive numeric paths | Tailcall-adjacent numeric paths preserve frame/debug invariants during frame-reuse cutover. | `node doc/wasm/js/all-smoke.mjs` plus `node doc/wasm/js/start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive` | Both commands exit `0`; no frame/debug contract violations; strict startup lane remains pass. | Any frame/debug invariant violation, stack-growth regression signal, or non-zero exit. | BPL-05 S6, BPL-03, BPL-07 |
| BPL04-G06 | `BPL04-S2-01`..`BPL04-S2-05` | cross-family aggregate | End-to-end post-slice aggregate suite remains green after each applied sequence slice. | `node doc/wasm/js/all-smoke.mjs` (rerun after each slice merge) | Continuous green at each sequence checkpoint. | Any checkpoint regression blocks next slice promotion. | BPL-05 governance, BPL-07 |

Step 3 closure assertions:

1. Every sequenced non-`native_now` family is covered by at least one explicit benchmark/profile gate.
2. All gate rows define command lanes, pass thresholds, and deterministic fail conditions.
3. Gate IDs are stable and consumable by BPL-05 implementation sequencing and BPL-07 reporting.

## Detailed Work Breakdown

### Step 1 - Operation Family Classification

- Status: done
- Notes:
  - Published `M4F-01`..`M4F-08` with direct source anchors, current lowering shape, and migration posture.
  - Captured initial benchmark hooks for fixnum hot path and aggregate smoke lane.
- Next:
  - Freeze family IDs and posture tags while Step 2 sequencing is authored.

### Step 2 - Sequencing and Owner Cutover Plan

- Status: done
- Notes:
  - Published ordered BPL-05 slice sequence for all non-`native_now` families with explicit owners, cutover triggers, and evidence gates.
  - Sequencing explicitly anchors to `CON-03`, `CON-04`, `CON-05`, `CON-06`, `FDC-10`, `ARM-ASSUMP-011`, and `ARM-ASSUMP-012`.
- Next:
  - Keep Step 2 rows stable and route any sequencing changes via additive sequence IDs.

### Step 3 - Benchmark/Gate Alignment

- Status: done
- Notes:
  - Published gate matrix `BPL04-G01`..`BPL04-G06` covering all Step 2 sequence IDs and non-`native_now` families.
  - Added explicit command lanes, pass thresholds, and fail conditions for deterministic checkpoint control.
- Next:
  - Keep gate IDs stable; add new gate rows additively if future families/slices are introduced.

## Test and Validation Plan

- Classification coverage validation:
  - Verify every `M4F-*` row includes source anchors, migration posture, owner, and benchmark hook.
- Contract alignment validation:
  - Verify every non-`native_now` row references at least one `CON-*` or `FDC-*` anchor.
- Resumability validation:
  - Verify row data is sufficient for BPL-05 sequencing without re-discovery.

## Risks and Mitigations

- Risk: numeric families drift across compiler/provider without synchronized ownership.
  - Mitigation: each family row has one primary owner and explicit dependency anchors.
- Risk: benchmark hooks stay too coarse to detect regressions.
  - Mitigation: Step 3 introduces explicit per-family metrics and gate thresholds.
- Risk: tailcall-related numeric regressions remain hidden in aggregate lanes.
  - Mitigation: keep `M4F-08` deferred with explicit `FDC-10` dependency until frame-reuse cutover evidence exists.

## Change Log

- 2026-02-09: Initialized BPL-04 subplan and closed Step 1 with source-anchored numeric operation family matrix (`M4F-01`..`M4F-08`).
- 2026-02-09: Closed Step 2 with ordered BPL-05 sequencing for `M4F-02`, `M4F-03`, `M4F-06`, `M4F-07`, and `M4F-08`, including explicit owners, cutover triggers, and evidence gates.
- 2026-02-09: Closed Step 3 by publishing benchmark/profile gate matrix (`BPL04-G01`..`BPL04-G06`) with explicit lanes, thresholds, and fail conditions tied to `BPL04-S2-*`.
