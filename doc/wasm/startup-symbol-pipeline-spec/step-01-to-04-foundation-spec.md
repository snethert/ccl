# Step 01-04 Foundation Spec (Parser Switch + Artifact Production)

This document specifies immediate blockers and required missing detail for the
first four execution steps.

## Step 01: Switch Parser Implementation Language To Common Lisp First

### Immediate Problems

1. `startup-binding-map.mjs` currently combines two concerns:
- source scanning/parsing of Lisp files, and
- startup map construction.

2. `pack-inline-bundle-v2.mjs` imports
`buildStartupBindingMapArtifact` from `startup-binding-map.mjs` and runs it
while packaging modules. If scanner logic is removed naively, pack breaks.

3. `make-real-image.mjs` still performs in-process map generation when
`compiledModulesBundle.startupBindingMap` is absent, so parser fallback still
exists in runtime path.

### Required Additional Spec

- `S1.1` Runtime parser policy: define whether runtime is hard-fail when scope
  artifact is missing (recommended: yes, hard-fail).
- `S1.2` Transitional API contract for `startup-binding-map.mjs` exports during
  migration, so pack/runtime import surfaces do not break.
- `S1.3` Manifest compatibility policy: whether old bundles containing
  `startupBindingMap` remain accepted until cleanup.

### Recommended Defaults To Unblock

- Keep `startup-binding-map.mjs` export names stable but remove scanner usage
  from active path.
- Make `make-real-image.mjs` require scope artifact via arg/manifest and fail
  with machine-readable reason `startup-symbol-scope-missing`.
- Keep read-only acceptance of legacy embedded `startupBindingMap` for one
  migration window, but do not generate it from JS source scan anymore.

## Step 02: Finalize Schemas And Determinism Contracts

### Immediate Problems

1. `startup_symbol_scope_v1` and `startup_symbol_resolution_v1` are named in the
plan but not yet fully typed.

2. Determinism is currently underspecified for time fields and hashing.
`generated_at_utc` makes raw byte-level stability impossible unless explicitly
excluded from identity criteria.

3. `startup_shadow_table` is currently mandatory for preinstall planning in
`make-real-image.mjs`; ownership in the new pipeline is unclear.

### Required Additional Spec

- `S2.1` Complete JSON field-level schema with required/optional, type,
  cardinality, and sort order for each artifact.
- `S2.2` Identity hash definition (exact canonicalization and excluded fields).
- `S2.3` Explicit producer of `startup_shadow_table` in the new flow and whether
  schema version remains `startup_shadow_table_v1`.
- `S2.4` Compatibility rules for schema bumps (consumer behavior on newer minor
  fields vs unknown major versions).

### Recommended Defaults To Unblock

- Canonical hash input excludes `generated_at_utc`; include all semantic fields.
- Scope/resolution artifacts sorted lexicographically by key and emitted as
  canonical JSON (`UTF-8`, no trailing spaces, newline-terminated).
- Preserve `startup_shadow_table_v1` shape for the first migration cut so
  preinstall logic does not need simultaneous redesign.

## Step 03: Implement Common Lisp Scanner + Tests

### Immediate Problems

1. Contract data source mismatch: scanner is in Lisp but required contract lives
   in `bootstrap-l0-contract.mjs` (JS object), which is not a robust scanner
   input format.

2. Reader environment risks:
- missing packages during read,
- reader conditionals requiring feature list parity,
- dangerous reader-eval if not forced off.

3. Role extraction still has ambiguity (e.g. macro wrappers, nested forms,
   function designator aliases, quoted lambdas).

4. No defined test harness command contract exists yet.

### Required Additional Spec

- `S3.1` Contract ingestion format: either
  - generated JSON sidecar from JS contract, or
  - duplicated Lisp contract file (avoid dual truth).

- `S3.2` `feature_profile` mapping table:
  - `wasm32-target-v1` -> exact feature symbols list used for `#+` / `#-`.

- `S3.3` Reader failure policy table:
  - parse error classification codes,
  - whether to continue file scan after form failure,
  - how line/column provenance is derived.

- `S3.4` Role extraction grammar:
  - exact recognized defining forms,
  - call-head detection rules,
  - what is ignored intentionally.

- `S3.5` CLI and exit contract:
  - required args (`--repo-root`, `--out`, `--feature-profile`, contract path),
  - stdout diagnostics format,
  - exit codes and reason payload schema.

### Recommended Defaults To Unblock

- Generate contract JSON once in compile pipeline and pass its path to scanner.
- Scanner runs with `*read-eval*` bound `nil`, custom safe readtable, and
  continues per-file after recoverable read errors while recording exclusions.
- Add deterministic fixture suite under
  `scripts/wasm/tests/startup-symbol-scope-fixtures/` with golden JSON outputs.

## Step 04: Integrate Scanner Into Compile/Repro Pipeline

### Immediate Problems

1. `compile-wasm-fasls.sh` and `repro-startup-pipeline.sh` do not generate scope
   artifact or pass scope path forward.

2. `make-real-image.lisp` wrapper does not support forwarding
   `--startup-symbol-scope` to Node helper.

3. `pack-inline-bundle-v2.mjs` currently builds map artifact directly from JS
   scanner code path.

4. Repro manifest artifact hash list does not include scope artifact outputs.

### Required Additional Spec

- `S4.1` Canonical artifact locations:
  - compile flow path,
  - repro run path,
  - temp path policy.

- `S4.2` CLI propagation contract:
  - new flags for `compile-wasm-fasls.sh`, `make-real-image.mjs`, and
    `make-real-image.lisp`.

- `S4.3` Bundle embedding policy:
  - whether to embed `startupSymbolScope` and/or generated map into
    `wasm-runtime-modules.json`.

- `S4.4` Repro manifest schema update:
  - add artifact entries for scope file and optional resolution artifact.

### Recommended Defaults To Unblock

- Add scanner run right after `compile-runtime-modules` step in repro and before
  `make-root-image`.
- Add `--startup-symbol-scope PATH` option to Node + Lisp wrapper.
- Add scope artifact hash to run manifest artifact set.
- Keep packaging independent of scanner internals: pack script should only copy
  prebuilt startup artifacts, not parse Lisp source.
