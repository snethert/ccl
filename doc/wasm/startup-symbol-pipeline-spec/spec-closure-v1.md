# Spec Closure v1 (Normative)

This document closes all known specification gaps for implementing the Common
Lisp scanner compromise straight through to completion.

Normative language uses MUST/SHOULD/MAY.

## 1. Scope And Non-Goals

1. The scanner implementation language MUST be Common Lisp.
2. Node code MUST NOT parse Lisp source files for startup symbol scope.
3. `make-real-image.mjs` MUST remain consumer/resolver/apply only.
4. Startup orchestration and diagnostics MAY remain in Node.
5. Kernel gate semantics and required fasload ordering are out of scope.

## 2. Artifact Model

### 2.1 Canonical Artifacts

1. Scope artifact: `startup_symbol_scope_v1`.
2. Resolution artifact: `startup_symbol_resolution_v1`.
3. Binding artifact: existing `startup_binding_map_v1` (migration-preserved).
4. Shadow table artifact: existing `startup_shadow_table_v1`
   (migration-preserved).

### 2.2 Artifact Locations

1. Compile default scope path:
   `doc/wasm/startup-symbol-scope.source_scope_v1.json`.
2. Repro run scope path:
   `doc/wasm/repro/startup-pipeline-<run-id>/artifacts/startup-symbol-scope.source_scope_v1.json`.
3. Optional resolution artifact path:
   `doc/wasm/repro/startup-pipeline-<run-id>/artifacts/startup-symbol-resolution.source_scope_v1.json`.

## 3. Schema Definitions

These required fields are locked for `startup_symbol_scope_v1` and
`startup_symbol_resolution_v1`. Any add/remove/rename/type change requires a
schema version bump and synchronized producer/consumer updates.

### 3.1 `startup_symbol_scope_v1`

Required top-level fields:
1. `schema_version` string, exact `startup_symbol_scope_v1`.
2. `generator_version` string.
3. `inputs` object.
4. `symbols` array.
5. `counts` object.

`inputs` required fields:
1. `repo_root` string.
2. `scan_roots` array of strings.
3. `files_scanned_total` integer >= 0.
4. `files_scanned_l0` integer >= 0.
5. `files_scanned_l1` integer >= 0.
6. `contract_hash` lowercase hex sha256 string.
7. `source_hash` lowercase hex sha256 string.
8. `generated_at_utc` RFC3339 UTC string.
9. `feature_profile` string.
10. `feature_set` array of strings, sorted.
11. `scanner_script_hash` lowercase hex sha256 string.
12. `host_ccl_version` string.

`symbols[]` required fields:
1. `key` string `PACKAGE::SYMBOL`.
2. `package_name` uppercase string.
3. `symbol_name` uppercase string.
4. `roles` non-empty array of strings, sorted unique.
5. `bindable` boolean.
6. `provenance` array sorted by `(file,line,column,role,form)`.

`provenance[]` required fields:
1. `source_kind` enum: `level0|level1|contract`.
2. `file` string repo-relative posix path.
3. `line` integer >= 1.
4. `column` integer >= 1 or null.
5. `role` string.
6. `form` string.
7. `reader_condition` string or null.

`counts` required fields:
1. `symbols_total` integer >= 0.
2. `bindable_total` integer >= 0.
3. `by_role` object integer values >= 0.
4. `by_package` object integer values >= 0.
5. `excluded_uninterned_total` integer >= 0.
6. `excluded_unsupported_reader_total` integer >= 0.
7. `excluded_by_reason` object integer values >= 0.

### 3.2 `startup_symbol_resolution_v1`

Required top-level fields:
1. `schema_version` string, exact `startup_symbol_resolution_v1`.
2. `generator_version` string.
3. `inputs_hash` lowercase hex sha256 string.
4. `symbols` array.
5. `counts` object.
6. `duration_ms` integer >= 0.

`symbols[]` required fields:
1. `key` string.
2. `status` enum: `resolved|unresolved|probe-error|invalid-input`.
3. `symbol_raw` string hex or null.
4. `probe_status` integer or null.
5. `probe_status_name` string or null.
6. `fcell_raw` string hex or null.
7. `fentry` integer >= 0 or null.
8. `vcell_raw` string hex or null.
9. `vcell_bound` boolean.
10. `required_class` enum:
   `required-callable|required-special|optional|none`.
11. `reason` string or null.
12. `resolver_source` enum: `metadata|kernel-probe|hybrid`.

`counts` required fields:
1. `total` integer >= 0.
2. `resolved` integer >= 0.
3. `unresolved` integer >= 0.
4. `probe_error` integer >= 0.
5. `invalid_input` integer >= 0.
6. `function_capable` integer >= 0.
7. `vcell_bound` integer >= 0.
8. `required_unresolved` integer >= 0.
9. `optional_unresolved` integer >= 0.

### 3.3 Schema Validation Failure Reasons (Locked)

1. Missing required scope artifact file MUST fail with
   `startup-symbol-scope-missing`.
2. Missing required field in `startup_symbol_scope_v1` (top-level or nested)
   MUST fail with `startup-symbol-scope-missing-required-field`.
3. Invalid `startup_symbol_scope_v1` schema (including wrong
   `schema_version`, wrong type, or invalid enum/value constraint) MUST fail
   with `startup-symbol-scope-invalid-schema`.
4. Missing required field in `startup_symbol_resolution_v1` (top-level or
   nested) MUST fail with
   `startup-symbol-resolution-missing-required-field`.
5. Invalid `startup_symbol_resolution_v1` schema (including wrong
   `schema_version`, wrong type, or invalid enum/value constraint) MUST fail
   with `startup-symbol-resolution-invalid-schema`.

### 3.4 Deterministic Canonicalization

1. JSON encoding MUST be UTF-8, no BOM, newline-terminated.
2. Object keys MUST be emitted in lexicographic order.
3. Arrays with semantic order constraints MUST be sorted deterministically.
4. Identity hash MUST exclude `generated_at_utc` only.
5. Paths in artifacts MUST be repo-relative posix style.

## 4. Contract Ingestion

1. Scanner MUST NOT parse `bootstrap-l0-contract.mjs` directly.
2. Pipeline MUST generate a canonical contract JSON sidecar:
   `doc/wasm/bootstrap-l0-contract.v1.json`.
3. Sidecar generation MUST run before scanner.
4. Sidecar schema MUST include required callables/specials/const pools exactly.

## 5. Feature Profiles

1. Scanner MUST require `--feature-profile`.
2. `wasm32-target-v1` MUST map to explicit ordered feature list stored in
   scanner source and emitted in artifact `inputs.feature_set`.
3. Unknown feature profiles MUST fail with reason
   `unknown-feature-profile`.

## 6. Scanner Reader Environment

1. Scanner MUST bind `*read-eval*` to `nil`.
2. Scanner MUST use deterministic file traversal order.
3. Scanner MUST record parse failures with reason codes and continue scanning
   remaining files unless fatal IO error occurs.
4. Package resolution policy:
- For `in-package`, scanner MUST update current package context.
- For package-qualified symbols that fail due to missing package,
  scanner MUST record exclusion reason `missing-package-during-read`.
5. Unsupported reader dispatch MUST be recorded as exclusion and not silently
   dropped.

## 7. Resolver Authority Model

1. Resolver mode MUST be hybrid:
- Stage A metadata resolution to candidate entry indices.
- Stage B kernel probe verification at apply-time.
2. `required_class` mapping MUST be deterministic:
- Contract required callable -> `required-callable`.
- Contract required special variable -> `required-special`.
- Any other bindable symbol -> `optional`.
- Non-bindable -> `none`.

## 8. Map Synthesis Contract

1. Map builder input MUST be scope + resolution artifacts.
2. Map builder MUST NOT invoke source scanning.
3. Map schema remains `startup_binding_map_v1` in migration cut.
4. `startup_shadow_table_v1` MUST continue to include:
- `preinstall_const_pool_entries`,
- `binding_entry_count`,
- `entry_backed_binding_count`.
5. Entry synthesis matrix MUST be deterministic:
- callable + resolved fentry -> `fcell`, `function`, `entry-backed`,
  `initializer.kind=entry-function`.
- required special + bound literal -> `vcell`, `special-variable`, `literal`.
- required special unresolved -> fail pre-gate path.
- optional unresolved -> deferred with explicit reason.

## 9. Apply Initializer Contract

Supported initializer kinds after migration:
1. `literal-fixnum`.
2. `literal-nil`.
3. `entry-function`.
4. `literal-symbol`.
5. `literal-keyword`.

Rules:
1. If required kernel export missing for initializer kind, required entries MUST
   fail with reason `missing-kernel-export`.
2. Optional entries MAY be deferred with reason
   `initializer-kind-not-supported`.
3. Apply MUST use exact package+name probing only.

## 10. CLI Contracts

### 10.1 New CLI Arguments

`doc/wasm/js/make-real-image.mjs` MUST accept:
1. `--startup-symbol-scope PATH` (required unless embedded scope artifact
   exists and policy allows it).
2. `--startup-symbol-resolution-out PATH` (optional diagnostic output).
3. `--startup-symbol-contract PATH` (optional override; default canonical path).

`scripts/wasm/make-real-image.lisp` MUST forward:
1. `--startup-symbol-scope`.
2. `--startup-symbol-resolution-out`.
3. `--startup-symbol-contract`.

`scripts/wasm/compile-wasm-fasls.sh` SHOULD accept:
1. `--startup-symbol-scope-out PATH`.
2. `--startup-symbol-contract-out PATH`.

### 10.2 Missing Artifact And Scope Schema Behavior

1. Missing required scope artifact MUST fail fast with
   `startup-symbol-scope-missing`.
2. Missing required scope schema field MUST fail fast with
   `startup-symbol-scope-missing-required-field`.
3. Invalid scope schema MUST fail fast with
   `startup-symbol-scope-invalid-schema`.

## 11. Diagnostics Contract

Required diagnostics and schema versions:
1. `STARTUP_SYMBOL_PIPELINE` -> `startup_symbol_pipeline_v1`.
2. `STARTUP_SYMBOL_SCOPE_BUILD` -> `startup_symbol_scope_build_v1`.
3. `STARTUP_SYMBOL_RESOLUTION_BUILD` ->
   `startup_symbol_resolution_build_v1`.
4. Existing `STARTUP_BINDING_MAP_*` lines remain unchanged in migration cut.

If scanner runs outside make-real-image:
1. make-real-image MUST emit relay line
   `STARTUP_SYMBOL_SCOPE_BUILD` with source metadata and hash, not scanner logs.

## 12. Repro Pipeline Contract

1. Repro step order MUST include
   `collect-startup-symbol-scope` before `make-root-image`.
2. Run manifest MUST include scope artifact path/bytes/sha256.
3. Run manifest SHOULD include resolution artifact path/bytes/sha256 when
   emitted.
4. Scanner step failure MUST terminate pipeline.

## 13. Root Manifest Contract

1. Root manifest schema remains v1 unless expanded intentionally.
2. Startup scope/resolution artifacts MUST be recorded in repro run manifest.
3. Root image manifest MAY remain limited to runtime artifacts unless
   schemaVersion is bumped and smoke checks are updated together.

## 14. Compatibility And Migration

1. Compatibility window MAY accept embedded legacy `startupBindingMap` for read
   only.
2. No code path MAY generate startup map by scanning Lisp in JS.
3. Legacy emit-all-functions environment toggles MUST be removed by cleanup
   completion.
4. Compatibility branch expiry criterion:
- two consecutive passing repro runs (smoke and top4488),
- no unresolved required symbols,
- no memory failure signatures.

## 15. Failure Reason Catalog (Minimum Required)

Schema validation reasons:
1. `startup-symbol-scope-missing`.
2. `startup-symbol-scope-missing-required-field`.
3. `startup-symbol-scope-invalid-schema`.
4. `startup-symbol-resolution-missing-required-field`.
5. `startup-symbol-resolution-invalid-schema`.

Scope stage reasons:
1. `unknown-feature-profile`.
2. `missing-contract-json`.
3. `reader-parse-error`.
4. `unsupported-reader-dispatch`.
5. `missing-package-during-read`.
6. `io-error`.

Resolver stage reasons:
1. `symbol-missing`.
2. `package-missing`.
3. `ambiguous-metadata-resolution`.
4. `invalid-symbol-name`.
5. `probe-status-not-ok`.

Apply stage reasons:
1. `required-symbol-unresolved`.
2. `required-non-nil-initializer-unavailable`.
3. `missing-kernel-export`.
4. `initializer-kind-unsupported-at-apply`.
5. `initializer-invalid-entry-index`.
6. `initializer-invalid-fixnum`.

Preinstall stage reasons:
1. `startup-shadow-table-missing`.
2. `startup-shadow-table-empty-preinstall-entries`.
3. `startup-shadow-table-missing-contract-root-entries`.
4. `preinstall-budget-exceeded`.

## 16. Validation Assertions (Normative)

Both smoke and top4488 lanes MUST satisfy:
1. `STARTUP_SYMBOL_PIPELINE` present and mode is `source_scope_v1`.
2. `STARTUP_SYMBOL_SCOPE_BUILD` present (scanner or relay).
3. `STARTUP_SYMBOL_RESOLUTION_BUILD` present.
4. `STARTUP_BINDING_MAP_APPLY.status == pass`.
5. `L0_BOOTSTRAP_CONTRACT.status == pass`.
6. No required-fasload omission failure reason.
7. No `WASM misc_alloc: reserve failed`.
8. No `wasm_memory_grow_and_relocate failed`.

## 17. Handoff Completion Criteria

Implementation is handoff-complete only when:
1. All contradictions in `contradiction-ledger.md` are resolved in code/docs.
2. All required schemas/CLI/diagnostics in this document are implemented.
3. Repro manifest includes startup artifact hashes.
4. Legacy JS source scan path is absent from active execution.
