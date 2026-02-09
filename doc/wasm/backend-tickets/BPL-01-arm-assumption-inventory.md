# BPL-01 - ARM Assumption Inventory

Status: done  
Priority: P0  
Owner: Compiler/backend migration track  
Last Updated: 2026-02-09  
Parent Plan: `doc/wasm/backend-migration-master-plan.md`

## Scope

In scope:

- Identify and catalog ARM-shaped assumptions across compiler/backend and runtime-call boundaries.
- Classify each assumption by migration strategy (remove, emulate temporarily, or defer).
- Produce a dependency map for BPL-02/BPL-04/BPL-05 planning.

Out of scope:

- Implementing new WASM-native lowering.
- Changing runtime transport/storage architecture directly.

## Dependencies

- BPL-00 governance process in use.

## Deliverables

1. ARM assumption inventory table with source references.
2. Strategy classification per assumption (`remove`, `compat_layer`, `defer`).
3. Risk and owner tagging for each assumption cluster.
4. Cross-track impact notes for dependency matrix updates.

## Exit Criteria

- Inventory covers compiler/backend and boundary ABI assumptions relevant to migration.
- Each row has a migration strategy and owner field.
- Blocking assumptions for BPL-02 are explicitly identified.
- Cross-track impacts are reflected in dependency matrix rows if needed.

## Current Notes

- Baseline still includes ARM-shaped assumptions that are not yet centrally cataloged.
- Runtime replacement is active in parallel; assumption inventory must stay compatible with secure-only runtime direction.
- Step 1 source sweep completed with ARM assumption inventory v1 captured below.
- Rescan pass (backend/runtime boundary focused) added concrete ARMENV/register-root assumptions and strengthened source references for entry index and subprim-table assumptions.
- Step 2 strategy closure is now complete for all non-`remove` assumptions with explicit transition/cutover triggers and sequencing owners.
- Step 3 dependency/risk closure is now complete across all 16 assumptions; no additional dependency-matrix rows were required.

## Immediate Next Step

- Action: keep BPL-01 in maintenance mode by enforcing delta-only inventory updates whenever new ARM-shaped assumptions are discovered during BPL-02/BPL-03/BPL-05 execution.
- Why now: Step 1/2/3/4 exit criteria are satisfied, so ongoing value is resumability discipline rather than additional baseline analysis.
- Success evidence: any newly discovered assumption lands as a source-backed row plus synchronized master/matrix updates in the same change.

## Detailed Work Breakdown

### Step 1 - Source Sweep and Assumption Capture

- Status: done
- Notes:
  - Completed source sweep across canonical docs, compiler/WASM sources, and wasm/provider kernel paths.
  - Assumption inventory v1 now includes source-backed rows with strategy tags, owners, and downstream mapping.
  - Rescan evidence added for `lib/wasmenv.lisp` ARMENV coupling and GC root-scanning register-range assumptions (`ARM-ASSUMP-015`, `ARM-ASSUMP-016`).
- Next:
  - Hand off to Step 2 for strategy finalization and sequencing closure.

### Step 1 Output - ARM Assumption Inventory (v1)

| assumption_id | source file:line | assumption summary | impact area | migration strategy | owner | downstream ticket mapping | risk note | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ARM-ASSUMP-001 | `compiler/WASM/wasm-arch.lisp:12`; `compiler/WASM/wasm-arch.lisp:41` | WASM target arch is instantiated by directly importing ARM arch and cloning ARM target fields/tags. | memory/tagging | remove | backend architecture | BPL-02, BPL-05 | Hidden ARM constants can survive contract freeze and leak into WASM-native invariants. | captured_v1 |
| ARM-ASSUMP-002 | `compiler/WASM/wasm-arch.lisp:30`; `compiler/WASM/wasm-arch.lisp:37`; `lisp-kernel/wasm-subprims-map.h:5`; `doc/wasm/ABI.md:11` | Subprim identity/order is tied to ARM `sptab` ordering and carried into WASM table mapping. | ABI/calling | compat_layer | backend contract + subprims interface | BPL-02, BPL-05, BPL-08 | Compiler/provider table-order skew can misdispatch subprims without obvious compile-time failures. | captured_v1 |
| ARM-ASSUMP-003 | `lisp-kernel/platform-wasm32.h:40`; `lisp-kernel/arm-constants.h:19`; `lisp-kernel/arm-constants.h:39` | wasm32 platform still imports ARM register naming (`arg_z`..`Rfn`, `nargs=imm2`) as canonical execution contract. | ABI/calling | compat_layer | kernel/runtime boundary | BPL-02, BPL-05, BPL-08 | Register-model refactors span compiler IR, subprims, GC, and call helpers simultaneously. | captured_v1 |
| ARM-ASSUMP-004 | `lisp-kernel/arm-constants.h:99`; `lisp-kernel/wasm-gc.c:1025` | GC relocation/bit math retains little-endian ARM assumptions in forwarding logic. | memory/tagging | remove | GC/runtime internals | BPL-05 | Incorrect mark/forward behavior is possible once layout stops matching ARM-derived bit expectations. | captured_v1 |
| ARM-ASSUMP-005 | `compiler/WASM/wasm2.lisp:1371`; `lisp-kernel/platform-wasm32.h:42` | Frame/debug context is placeholder-only (`%current-frame-ptr` returns NIL; trap context is stubbed). | frame/debug | defer | debug/frame model | BPL-03, RPL-02 | Debugger/backtrace fidelity remains constrained until a non-stub frame model is finalized. | captured_v1 |
| ARM-ASSUMP-006 | `lisp-kernel/platform-wasm32.h:74`; `doc/wasm/ABI.md:67` | Runtime relies on implicit global current-TCR access rather than explicit per-call context threading. | runtime boundary | compat_layer | runtime boundary | BPL-02, BPL-08, RPL-02 | Worker-topology evolution can expose TCR aliasing/race hazards across runner boundaries. | captured_v1 |
| ARM-ASSUMP-007 | `doc/wasm/ABI.md:128`; `lisp-kernel/wasm-subprims-provider.c:1532` | Function call ABI mirrors ARM-style top-3 arg register sync from VSP (`arg_z/arg_y/arg_x`). | ABI/calling | remove | backend contract | BPL-02, BPL-05 | Register-sync shims add overhead and preserve ARM call-shape constraints in generated code. | captured_v1 |
| ARM-ASSUMP-008 | `compiler/WASM/wasm2.lisp:4506`; `compiler/WASM/wasm2.lisp:4604`; `doc/wasm/ABI.md:100` | No-spill subprim allowlist hardcodes ARM-era VSP-sensitive control-flow subprims. | lowering/IR | compat_layer | lowering/codegen | BPL-05, BPL-03 | Missing allowlist updates can invalidate GC-root spill discipline in hard-to-reproduce paths. | captured_v1 |
| ARM-ASSUMP-009 | `doc/wasm/decisions.md:94`; `lisp-kernel/wasm-subprims-provider.c:5402` | PROGV save/restore uses VSP sentinel chain as temporary substitute for ARM TSP-frame semantics. | frame/debug | defer | runtime semantics | BPL-03, BPL-05 | Unwind/debug behavior remains special-cased until stack model convergence is defined. | captured_v1 |
| ARM-ASSUMP-010 | `lisp-kernel/wasm-subprims-provider.c:195`; `lisp-kernel/wasm-subprims-provider.c:5481` | `_SPprogvrestore` cleanup entry uses hardcoded subprim index `114` from static map ordering. | lowering/IR | remove | subprims provider | BPL-02, BPL-05 | Subprim-map edits can silently break unwind-protect cleanup dispatch. | captured_v1 |
| ARM-ASSUMP-011 | `compiler/WASM/wasm2.lisp:4764`; `compiler/WASM/wasm2.lisp:3792`; `lisp-kernel/wasm-kernel-stubs.c:207`; `doc/wasm/ABI.md:138` | Entrypoint indices are fixed numeric slots (200-series stubs + generic allocation from 300). | ABI/calling | compat_layer | module/loader contract | BPL-02, BPL-04, BPL-05, RPL-07 | Static slot allocation risks collisions during module packaging/link evolution. | captured_v1 |
| ARM-ASSUMP-012 | `lisp-kernel/wasm-subprims-provider.c:2083` | Tailcall/jump subprims currently wrap `_SPfuncall` without tail-frame reuse. | frame/debug | defer | subprims/runtime execution | BPL-03, BPL-04 | Stack growth and frame-shape drift can mask true tailcall behavior during parity checks. | captured_v1 |
| ARM-ASSUMP-013 | `compiler/WASM/wasm2.lisp:6830`; `compiler/WASM/wasm2.lisp:3368` | Codegen still emits against raw `arm::*` constants (`illegal-marker`, `subtag-mask`, etc.). | lowering/IR | remove | lowering/codegen | BPL-05, BPL-02 | Residual ARM constants obstruct backend contract normalization and testable invariants. | captured_v1 |
| ARM-ASSUMP-014 | `lisp-kernel/arm-constants.h:349`; `lisp-kernel/thread_manager.c:1821`; `lisp-kernel/wasm-subprims.c:53` | TCR keeps fixed `sptab[256]` and wasm init fills index table with fixed cardinality assumptions. | runtime boundary | compat_layer | kernel/runtime boundary | BPL-02, BPL-08 | Fixed table shape constrains subprim evolution and multi-version compatibility. | captured_v1 |
| ARM-ASSUMP-015 | `lib/wasmenv.lisp:3`; `lib/wasmenv.lisp:7`; `lib/wasmenv.lisp:16`; `lib/wasmenv.lisp:31` | WASM backend environment still depends on `ARMENV` and ARM register masks for arg/temp/node register classes. | lowering/IR | remove | lowering/codegen | BPL-05, BPL-02 | WASM-native register/local modeling is constrained by inherited ARM register-class assumptions in backend setup. | captured_v1 |
| ARM-ASSUMP-016 | `lisp-kernel/wasm-gc.c:945`; `lisp-kernel/wasm-gc.c:955`; `lisp-kernel/wasm-gc.c:1238`; `lisp-kernel/wasm-gc.c:1242` | GC mark/forward paths assume Lisp roots occupy a contiguous ARM register index range (`arg_z..Rfn`) in exception contexts. | memory/tagging | compat_layer | GC/runtime internals | BPL-05, BPL-08, RPL-02 | Register-file reshaping can create silent root under/over-marking unless GC root enumeration is decoupled from ARM index ordering. | captured_v1 |

### Step 2 - Strategy Classification

- Status: done
- Notes:
  - Initial strategy tags are complete across all 16 v1 rows (`remove`, `compat_layer`, `defer`).
  - Strategy closure is complete for all 10 non-`remove` rows (`compat_layer` + `defer`) with explicit transition/cutover triggers and sequencing owners.
- Next:
  - Hand off to Step 3 for dependency/risk closure validation against active BPL/RPL sequencing.

### Step 2 Output - Strategy Closure (non-`remove` rows)

| assumption_id | migration strategy | transition/cutover trigger | sequencing owner | sequencing order |
| --- | --- | --- | --- | --- |
| ARM-ASSUMP-002 | compat_layer | BPL-02 publishes subprim contract invariants (non-address dispatch + provider/compiler map integrity), then BPL-05 removes order-coupled lowering assumptions, with final BPL-08 runtime/provider conformance proving stable dispatch under reordered fixture maps. | BPL-02 backend contract owner (primary), BPL-08 runtime-alignment owner (cutover gate) | BPL-02 -> BPL-05 -> BPL-08 |
| ARM-ASSUMP-003 | compat_layer | BPL-02 defines neutral WASM register/context ABI names and compatibility aliases; BPL-05 migrates lowering/codegen references off ARM register symbols; BPL-08 removes compatibility alias requirement after provider + GC parity validation. | kernel/runtime boundary owner | BPL-02 -> BPL-05 -> BPL-08 |
| ARM-ASSUMP-005 | defer | RPL-02 worker ownership/lifecycle contract is frozen and consumed by BPL-03 frame/debug metadata model; cutover occurs when `%current-frame-ptr`/trap-context stubs are replaced and debug/backtrace smoke passes under worker topology constraints. | BPL-03 debug/frame model owner (primary), RPL-02 worker-topology owner (input gate) | RPL-02 -> BPL-03 |
| ARM-ASSUMP-006 | compat_layer | RPL-02 lifecycle contract plus BPL-08 runtime-boundary API provides explicit context threading; BPL-02 contract language marks implicit global TCR lookup as compatibility-only; cutover removes implicit global access path after worker-boundary tests pass. | runtime boundary owner | RPL-02 -> BPL-02 -> BPL-08 |
| ARM-ASSUMP-008 | compat_layer | BPL-05 replaces static no-spill allowlist with metadata-driven spill policy; BPL-03 validates frame/GC-root safety rules; cutover occurs when catch/throw/unwind diff fixtures pass without allowlist-only protections. | lowering/codegen owner | BPL-05 -> BPL-03 -> BPL-06 parity gate |
| ARM-ASSUMP-009 | defer | BPL-03 decides long-term unwind/binding frame model and BPL-05 implements it; cutover occurs when PROGV sentinel path is disabled behind parity tests for unwind/debug behavior. | runtime semantics owner | BPL-03 -> BPL-05 |
| ARM-ASSUMP-011 | compat_layer | BPL-02 defines symbolic entrypoint manifest contract; RPL-07 module packaging freeze provides stable loader/link semantics; cutover removes fixed `200/201/202` slot assumptions from compiler/kernel glue after integration fixtures pass. | module/loader contract owner (primary), RPL-07 module-sharing owner (packaging gate) | BPL-02 -> RPL-07 -> BPL-08 |
| ARM-ASSUMP-012 | defer | BPL-03 frame model defines tail-frame invariants and BPL-04 performance gates include tail-recursive stack behavior; cutover occurs when tailcall/jump subprims reuse frames and stack-growth regression gates pass. | subprims/runtime execution owner | BPL-03 -> BPL-04 |
| ARM-ASSUMP-014 | compat_layer | BPL-02 defines variable subprim-table cardinality/version contract; BPL-08 adds runtime/provider version handshake; cutover occurs when fixed `sptab[256]` assumptions are removed from initialization/copy paths. | kernel/runtime boundary owner | BPL-02 -> BPL-08 |
| ARM-ASSUMP-016 | compat_layer | BPL-05 introduces explicit root-register descriptor consumed by GC; BPL-08 runtime alignment exports canonical descriptor to runtime code; cutover removes contiguous `arg_z..Rfn` root-range loops after altered-layout root-mark tests pass. | GC/runtime internals owner | BPL-05 -> BPL-08 |

### Step 3 - Dependency and Risk Mapping

- Status: done
- Notes:
  - Dependency/risk mapping is now validated for all 16 assumptions against active BPL-02/BPL-03/BPL-05 execution slices.
  - Existing cross-track posture remains sufficient (`X-02` soft-gate for frame/debug and worker-boundary-sensitive assumptions); no additional matrix row was evidenced.
  - Step 2 transition triggers and sequencing owners are now verified as consistent with downstream ticket sequencing.
- Next:
  - Preserve mapping integrity as downstream tickets execute; reopen Step 3 only if concrete dependency posture changes.

### Step 3 Output - Dependency/Risk Closure Validation

| assumption_id | primary downstream slice(s) | dependency validation result | cross-track posture | closure status |
| --- | --- | --- | --- | --- |
| ARM-ASSUMP-001 | BPL-02, BPL-05 | Contract + lowering slices already cover target-arch constant retirement. | backend-only | validated_step3 |
| ARM-ASSUMP-002 | BPL-02, BPL-05, BPL-08 | Sequencing aligns with subprim contract first, lowering decoupling second, runtime integration third. | backend-only | validated_step3 |
| ARM-ASSUMP-003 | BPL-02, BPL-05, BPL-08 | ABI naming/alias strategy and lowering decoupling sequence is internally coherent. | backend-only | validated_step3 |
| ARM-ASSUMP-004 | BPL-05 | Memory/tagging cleanup is fully owned by lowering/runtime-internal backend path. | backend-only | validated_step3 |
| ARM-ASSUMP-005 | BPL-03 | Frame/debug completion explicitly depends on published RPL-02 topology/lifecycle artifacts. | soft_gate (`X-02`) | validated_step3 |
| ARM-ASSUMP-006 | BPL-02, BPL-08 | Runtime-boundary contract path is coherent; worker ownership semantics remain sourced through RPL-02 evidence. | soft_gate (`X-02`) | validated_step3 |
| ARM-ASSUMP-007 | BPL-02, BPL-05 | Calling invariant retirement is covered by contract + lowering slices without additional gates. | backend-only | validated_step3 |
| ARM-ASSUMP-008 | BPL-05, BPL-03 | Spill-policy migration and frame-safety validation sequence is coherent for staged rollout. | soft_gate (`X-02` via BPL-03 finalization) | validated_step3 |
| ARM-ASSUMP-009 | BPL-03, BPL-05 | Deferred PROGV model convergence remains sequenced through frame model then lowering/runtime execution updates. | soft_gate (`X-02`) | validated_step3 |
| ARM-ASSUMP-010 | BPL-02, BPL-05 | Cleanup-entry hard-index risk remains fully within backend contract/lowering slices. | backend-only | validated_step3 |
| ARM-ASSUMP-011 | BPL-02, BPL-04, BPL-05, BPL-08 | Entrypoint slot retirement sequence remains coherent; existing ticket-level RPL-07 linkage does not yet require new matrix gating evidence. | parallel (ticket-level with RPL-07) | validated_step3 |
| ARM-ASSUMP-012 | BPL-03, BPL-04 | Tail-frame semantics remain correctly sequenced through frame-model definition and numeric/perf verification lanes. | soft_gate (`X-02` via BPL-03 finalization) | validated_step3 |
| ARM-ASSUMP-013 | BPL-05, BPL-02 | Raw ARM constant retirement is fully covered by lowering decoupling and contract normalization slices. | backend-only | validated_step3 |
| ARM-ASSUMP-014 | BPL-02, BPL-08 | Subprim-table cardinality/version handshake remains an internal backend/runtime-alignment sequence with no new cross-track gate evidence. | backend-only | validated_step3 |
| ARM-ASSUMP-015 | BPL-05, BPL-02 | WASMENV/ARMENV decoupling remains fully inside backend contract + lowering tracks. | backend-only | validated_step3 |
| ARM-ASSUMP-016 | BPL-05, BPL-08 | GC root descriptor migration sequence is coherent and remains tied to worker-sensitive frame/runtime boundary evidence already tracked in `X-02`. | soft_gate (`X-02`) | validated_step3 |

### Step 4 - Master Plan and Matrix Sync

- Status: done
- Notes:
  - BPL-01 Step 1 output is now synchronized in `doc/wasm/backend-migration-master-plan.md` and `doc/wasm/runtime-backend-dependency-matrix.md`.
- Next:
  - Keep this sync discipline enforced for every subsequent BPL-01 update cycle.

## Test and Validation Plan

- Spec validation:
  - Ensure inventory has concrete source references and strategy tags.
- Consistency validation:
  - Ensure all blocker assumptions map to at least one downstream ticket.
- Cross-track validation:
  - Ensure matrix rows are updated when dependency posture changes.

## Risks and Mitigations

- Risk: inventory misses hidden assumptions and causes late regressions.
  - Mitigation: track unresolved "unknown" areas explicitly and force follow-up rows.
- Risk: strategy tags become aspirational instead of actionable.
  - Mitigation: require owner and downstream ticket mapping for each row.
- Risk: cross-track side effects are not documented.
  - Mitigation: enforce matrix update in same change when impacts are discovered.

## Change Log

- 2026-02-09: Initial BPL-01 subplan created with inventory-first execution plan.
- 2026-02-09: Step 1 completed with ARM assumption inventory v1 (source-backed rows, strategy tags, owners, and downstream mappings); Step 2/3 moved to in_progress and Step 4 sync marked done.
- 2026-02-09: Rescan pass added `ARM-ASSUMP-015` and `ARM-ASSUMP-016` and strengthened source evidence for `ARM-ASSUMP-002`, `ARM-ASSUMP-011`, and `ARM-ASSUMP-014`.
- 2026-02-09: Completed Step 2 closure for all 10 non-`remove` rows by adding explicit transition/cutover triggers and sequencing owners; advanced immediate focus to Step 3 dependency/risk closure validation.
- 2026-02-09: Completed Step 3 closure for all 16 assumptions with downstream slice validation and explicit cross-track posture checks; confirmed no new non-speculative dependency-matrix rows were required.
