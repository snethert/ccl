# Startup Symbol Pipeline Spec Addendum (Compromise Track)

This directory captures the missing specification required to implement the
Common Lisp scanner compromise straight through without stop-and-ask pauses.

## Why This Addendum Exists

The implementation plan in
`doc/wasm/startup-symbol-pipeline-implementation-plan.md` is directionally
correct, but several interfaces are still underspecified for an end-to-end code
change.

Current code reality (as of this addendum):
- No host scanner file exists at
  `scripts/wasm/collect-startup-symbol-scope.lisp`.
- No `STARTUP_SYMBOL_PIPELINE`, `STARTUP_SYMBOL_SCOPE_BUILD`, or
  `STARTUP_SYMBOL_RESOLUTION_BUILD` logs exist yet.
- `scripts/wasm/pack-inline-bundle-v2.mjs` currently imports
  `buildStartupBindingMapArtifact` from `doc/wasm/js/startup-binding-map.mjs`
  and builds `startupBindingMap` directly in JS.
- `doc/wasm/js/make-real-image.mjs` still falls back to generating startup map
  in-process from JS scanning when bundle embedding is absent.

## Cross-Cutting Underspec (Must Be Nailed Before Coding Straight Through)

1. Contract ingestion source: scanner currently expected to read
   `bootstrap-l0-contract.mjs`, but this file is JS, not Lisp data.
2. Feature profile semantics: `--feature-profile wasm32-target-v1` has no
   canonical feature list mapping.
3. Reader environment: package/bootstrap prerequisites for safe read-only scan
   are not fully specified.
4. Artifact boundary: unclear whether scope artifact is standalone file only,
   embedded in modules manifest, or both.
5. Resolver authority: unresolved whether resolution is kernel-probe based,
   metadata-resolver based, or hybrid.
6. Startup shadow table ownership: preinstall currently requires
   `startup_shadow_table`; generation source for this in the new flow is not
   explicit.
7. CLI propagation: new startup scope path is not wired through
   `make-real-image.mjs`, `make-real-image.lisp`, compile scripts, and repro.
8. Repro manifest schema: no slot currently records scope artifact path/hash.
9. Determinism vs timestamps: `generated_at_utc` conflicts with byte-identical
   artifact criteria unless explicitly excluded from identity hashing.
10. Literal symbol initializer support: runtime export contract for
    `literal-symbol` / `literal-keyword` is not specified.

## Decision Register (Blocking)

- `D1` Contract source format for scanner input (`.mjs` parse vs generated JSON).
- `D2` Canonical feature set per `feature_profile`.
- `D3` Scope artifact canonical path(s) in compile and repro runs.
- `D4` Whether runtime modules manifest carries `startupSymbolScope` and/or
  `startupBindingMap` during migration.
- `D5` Resolver algorithm and status taxonomy source of truth.
- `D6` Required fields for `startup_symbol_scope_v1` and
  `startup_symbol_resolution_v1` with strict types.
- `D7` Ownership and schema of `startup_shadow_table` in the new flow.
- `D8` Policy for unresolved optional callables and unresolved required
  specials.
- `D9` Kernel export contract for symbol/keyword literal apply.
- `D10` Preinstall budget formula constants.
- `D11` Repro run-manifest schema bump details.
- `D12` Migration window and exact list of legacy flags/functions to remove.

## Document Map

- `step-01-to-04-foundation-spec.md`
- `step-05-to-08-runtime-spec.md`
- `step-09-to-12-validation-cleanup-spec.md`
- `contradiction-ledger.md`
- `spec-closure-v1.md`
- `spec-closure-checklist.md`

Each step section includes:
- immediate implementation problems (what will break first),
- required additional spec to avoid ambiguity,
- recommended default decisions to unblock coding.

Closure workflow:
1. Resolve all items in `contradiction-ledger.md`.
2. Treat `spec-closure-v1.md` as normative implementation contract.
3. Use `spec-closure-checklist.md` as completion gate before coding handoff.
