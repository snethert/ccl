# Step 05-08 Runtime Spec (Resolver, Map, Apply, Preinstall)

This document covers the runtime-facing half of the pipeline.

## Step 05: Implement Resolver + Resolution Artifact

### Immediate Problems

1. Existing resolution logic is fragmented:
- pre-toplevel designator gate uses `bootstrapFunctionResolver` metadata,
- apply path uses kernel probe APIs (`wasm_probe_symbol*`) during apply.

2. No single canonical resolver output artifact exists yet.

3. Required-class classification is currently distributed across map/apply logic,
   not centralized.

### Required Additional Spec

- `S5.1` Resolver authority model:
  - kernel probe only,
  - metadata only,
  - or staged hybrid (recommended).

- `S5.2` Resolver execution point:
  - exact point in `make-real-image.mjs` boot sequence,
  - guarantees about export availability.

- `S5.3` Required-class mapping table:
  - how `contract.requiredCallables`, `requiredSpecialVariables`, and scope
    roles map to `required_class`.

- `S5.4` Status and reason taxonomy:
  - exhaustive set for `resolved`, `unresolved`, `probe-error`,
    `invalid-input`.

- `S5.5` Deterministic unresolved policy:
  - whether unresolved optional entries remain in map as deferred.

### Recommended Defaults To Unblock

- Use staged hybrid resolver:
  - stage A: metadata/entry index availability,
  - stage B: kernel probe at apply-time readiness.
- Emit `startup_symbol_resolution_v1` before map synthesis.
- Keep unresolved optionals as deferred map entries; hard-fail unresolved
  required entries pre-gate.

## Step 06: Refactor Binding Map Generation To Scope+Resolution Inputs

### Immediate Problems

1. `buildStartupBindingMapArtifact` currently depends on JS source scans and
   runtime function metadata directly.

2. Contract-required const-pool function augmentation currently mutates map
   artifact post-build; this creates ordering complexity for new resolver flow.

3. `startup_shadow_table` and closure const-pool ownership are critical to
   preinstall and deferred apply but not explicitly re-specified in the new
   source+resolution model.

### Required Additional Spec

- `S6.1` Input contract for map builder:
  - required shape of scope artifact,
  - required shape of resolution artifact,
  - optional compiled module metadata.

- `S6.2` Entry synthesis matrix:
  - `(role set, required_class, resolution status)` ->
    `target_cell`, `binding_class`, `availability`, `initializer.kind`.

- `S6.3` Anchor policy:
  - how definition anchors (`definition.entry_index`, `definition.const_index`)
    are produced and carried forward for deferred const-pool assists.

- `S6.4` Duplicate/merge policy:
  - multiple provenance records for same symbol key,
  - conflicting roles across files.

- `S6.5` Shadow table ownership:
  - exact algorithm producing `preinstall_const_pool_entries` and closure lists.

### Recommended Defaults To Unblock

- Keep current map schema (`startup_binding_map_v1`) and shadow-table fields in
  migration cut; change producer inputs only.
- Build map from artifacts only; forbid direct source scan calls in map builder.
- Run contract const-pool augmentation as a deterministic sub-pass in map build,
  then recompute shadow table once.

## Step 07: Apply Initializer Expansion (`literal-symbol`, `literal-keyword`)

### Immediate Problems

1. Apply path currently supports `literal-fixnum`, `literal-nil`, and
   `entry-function` only.

2. Kernel export support for setting symbol-valued vcells is not guaranteed by
   current required export checks.

3. Semantics for package-qualified symbol literals are not defined if target
   symbol/package is absent at apply time.

### Required Additional Spec

- `S7.1` Runtime ABI for symbol literal set:
  - required kernel exports and argument shapes,
  - whether keyword literals are intern-only or direct object refs.

- `S7.2` Fallback behavior when ABI is unavailable:
  - hard fail for required,
  - defer for optional, or
  - disallow initializer kind in map build.

- `S7.3` Validation semantics:
  - post-apply probe checks for symbol literal values,
  - nil/non-nil requirement behavior.

### Recommended Defaults To Unblock

- Gate new initializer kinds behind explicit export checks.
- If exports missing:
  - required binding -> fail with reason `missing-kernel-export`,
  - optional binding -> emit deferred with reason `initializer-kind-not-supported`.
- Keep package+symbol exact probe policy; no package-agnostic fallback.

## Step 08: Preinstall Bound And Memory Guardrails

### Immediate Problems

1. Current preinstall uses artifact `startup_shadow_table` with strict existence
   checks but no quantitative budget guard.

2. No fixed formula constants are specified for allowed margin.

3. No explicit coupling between preinstall summary and memory regression checks.

### Required Additional Spec

- `S8.1` Budget formula constants:
  - fixed margin,
  - optional per-lane overrides,
  - fail reason payload shape.

- `S8.2` Summary telemetry contract:
  - budget inputs,
  - observed counts,
  - overrun deltas.

- `S8.3` Relationship to boundary requirements:
  - ensure strict budget does not prune required const pools.

### Recommended Defaults To Unblock

- Add `STARTUP_BINDING_MAP_PREINSTALL` fields:
  - `budget.max_preinstall`, `budget.required_roots`,
    `budget.required_anchors`, `budget.fixed_margin`, `budget.over_by`.
- Enforce fail only when over budget after confirming all required roots are
  present.
- Keep memory signature grep checks as final validation gate, not build-time
  heuristic.
