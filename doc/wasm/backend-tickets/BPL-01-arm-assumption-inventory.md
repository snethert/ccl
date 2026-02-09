# BPL-01 - ARM Assumption Inventory

Status: planned  
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

## Immediate Next Step

- Action: produce inventory v1 with at least initial coverage for ABI/calling, arithmetic lowering, frame/debug handling, and memory/tagging assumptions.
- Why now: backend contract and numeric modernization tickets depend on this inventory.
- Success evidence: inventory section committed in this ticket and linked from backend master plan.

## Detailed Work Breakdown

### Step 1 - Source Sweep and Assumption Capture

- Status: planned
- Notes:
  - Sweep target docs and backend code paths for explicit/implicit ARM assumptions.
- Next:
  - Build initial row set with file references and assumption summary.

### Step 2 - Strategy Classification

- Status: planned
- Notes:
  - Classify each assumption by migration strategy.
- Next:
  - Tag each row with `remove`, `compat_layer`, or `defer` and rationale.

### Step 3 - Dependency and Risk Mapping

- Status: planned
- Notes:
  - Map assumption clusters to downstream BPL tickets and cross-track matrix rows.
- Next:
  - Add owner, dependency, and risk fields to each row.

### Step 4 - Master Plan and Matrix Sync

- Status: planned
- Notes:
  - Subplan results must be reflected in backend master plan and dependency matrix.
- Next:
  - Update BPL-01 block and any affected `X-*` rows in one change.

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
