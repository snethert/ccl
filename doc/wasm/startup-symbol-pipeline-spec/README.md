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

## Decision Register (Locked For Execution)

The decision register is now fixed and must not be reopened during normal
implementation flow. Authoritative mapping:

- `D1` Contract source format -> `spec-closure-v1.md` Section `4`.
- `D2` Feature profile mapping -> `spec-closure-v1.md` Section `5`.
- `D3` Scope artifact canonical paths -> `spec-closure-v1.md` Section `2.2`.
- `D4` Migration manifest/embedding policy -> `spec-closure-v1.md` Section `14`.
- `D5` Resolver authority model -> `spec-closure-v1.md` Section `7`.
- `D6` Scope/resolution strict schemas -> `spec-closure-v1.md` Section `3`.
- `D7` Shadow table ownership/schema -> `spec-closure-v1.md` Section `8`.
- `D8` Required/optional unresolved policy -> `spec-closure-v1.md` Section `8`.
- `D9` Symbol/keyword initializer contract -> `spec-closure-v1.md` Section `9`.
- `D10` Preinstall budget constants -> `spec-closure-v1.md` Section `15`.
- `D11` Repro manifest coverage -> `spec-closure-v1.md` Section `12`.
- `D12` Migration horizon/removal policy -> `spec-closure-v1.md` Section `14`.

Execution linkage:
- Microsteps and gates: `startup-symbol-pipeline-implementation-plan.md`
  Section `19`.
- Copy/paste commands per microstep:
  `startup-symbol-pipeline-implementation-plan.md` Section `22`.
- Contradiction closure status: `contradiction-ledger.md`.

## Closure Status Snapshot (2026-02-14)

- Decision Register (Locked For Execution) remains authoritative and unchanged.
- Gate status pointer:
  - `G-01` through `G-11` are tracked in
    `spec-closure-checklist.md` Section `I`.
  - `G-11` is marked passed; `G-12` is still pending evidence-bundle closure.
- Evidence pointers:
  - `startup-symbol-pipeline-implementation-plan.md` Section `22` cards
    `M-061`..`M-065`.
  - `contradiction-ledger.md` Closure Board execution snapshot.

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
1. Treat `spec-closure-v1.md` as normative implementation contract.
2. Execute the microstep ledger (`M-*`, `G-*`) in implementation plan
   Section `19`.
3. Mark contradiction implementations closed in `contradiction-ledger.md`.
4. Use `spec-closure-checklist.md` gate list as handoff control surface.
