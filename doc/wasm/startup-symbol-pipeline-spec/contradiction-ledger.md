# Contradiction Ledger (Round 2 Introspection)

This ledger captures explicit contradictions between plan statements, current
code behavior, and existing documentation.

## C-001 Plan Ordering Contradiction

- Source A: `doc/wasm/startup-symbol-pipeline-implementation-plan.md:52`
  states `Schema before scanner`.
- Source B: `doc/wasm/startup-symbol-pipeline-implementation-plan.md:886`
  states parser-language switch is step 1, before schema implementation.

Impact:
- Execution order is ambiguous and can produce rework if scanner output fields
  are implemented before schema lock.

Spec closure required:
- Distinguish `language freeze` from `scanner implementation`.
- Keep scanner implementation after schema lock, even if language decision is
  made first.

## C-002 Architecture Contradiction (Compromise vs Build Docs)

- Compromise says Common Lisp scanner is sole parser path and Node is consumer.
- `doc/wasm/build.md:427` says
  `doc/wasm/js/startup-binding-map.mjs` is sole producer of startup bindings.

Impact:
- Team can implement opposite architectures while both appear documented.

Spec closure required:
- Replace JS-producer statements with scanner-producer ownership.

## C-003 Runtime Behavior Contradiction (Node Consumer-Only vs Fallback Generation)

- Compromise requires `make-real-image.mjs` consumer/resolver/apply-only.
- `doc/wasm/js/make-real-image.mjs:554` still generates startup binding map via
  `buildStartupBindingMapArtifact(...)` if embedded map missing.

Impact:
- Runtime still contains source-derived generation path.

Spec closure required:
- Runtime must hard-fail on missing prebuilt scope/map artifacts.

## C-004 Packaging Contradiction (No JS Parser Path vs Pack-Time JS Production)

- Compromise disallows second JS parser semantics path.
- `scripts/wasm/pack-inline-bundle-v2.mjs:327` builds startup map via
  `buildStartupBindingMapArtifact` from JS.

Impact:
- Even if runtime is fixed, packaging still emits JS-derived semantics.

Spec closure required:
- Pack stage must copy/attach prebuilt artifacts only; no source scan in pack.

## C-005 Compaction Pass Contradiction (Legacy Field Preservation)

- `scripts/wasm/compact-runtime-modules.mjs:763` blindly preserves
  `startupBindingMap` if present.

Impact:
- Old JS-produced map persists through compacted manifests, reintroducing dual
  semantics across build products.

Spec closure required:
- Explicit migration rule for preserving/rejecting legacy embedded maps.

## C-006 CLI Contract Contradiction (Planned Flag vs Actual Parser)

- Plan validation commands use `--startup-symbol-scope`.
- `doc/wasm/js/make-real-image.mjs:129` parseArgs has no such option.
- `scripts/wasm/make-real-image.lisp:62` also has no forwarding support.

Impact:
- Validation commands in plan are non-executable today.

Spec closure required:
- Add and document new CLI options end-to-end.

## C-007 Repro Flow Contradiction (Scanner-First vs Step Graph)

- Plan requires scanner artifact generation before image build.
- `scripts/wasm/repro-startup-pipeline.sh:476-488` runs compile -> build boot ->
  make image without scanner step.

Impact:
- Repro path can never satisfy compromise policy.

Spec closure required:
- Insert scanner step and artifact hash capture before `make-root-image`.

## C-008 Diagnostic Expectations Contradiction

- Plan expects `STARTUP_SYMBOL_SCOPE_BUILD` evidence in make-real-image logs
  (`...implementation-plan.md:704`).
- Compromise caveat says scanner is not run in make-real-image.

Impact:
- Either log grep command is wrong, or make-real-image must echo scope metadata.

Spec closure required:
- Clarify whether make-real-image emits a relay summary for prebuilt scope
  artifact (recommended: yes, relay-only, no scan).

## C-009 Dual-Semantics Policy Contradiction

- Plan states no dual parser path in final design.
- Plan also allows temporary compatibility branch and temporary legacy override
  env without strict semantic boundaries.

Impact:
- Teams may keep alternate parser semantics under temporary flags indefinitely.

Spec closure required:
- Compatibility path may switch artifact source only, never parser algorithm.
- Add removal deadline criteria.

## C-010 Contract Ownership Contradiction

- Scanner step references consuming bootstrap contract in JS file path
  (`bootstrap-l0-contract.mjs`) directly.
- Scanner is Common Lisp and requires deterministic parse-friendly input.

Impact:
- Cross-language parsing becomes undefined or brittle.

Spec closure required:
- Introduce canonical generated contract JSON consumed by scanner.

## C-011 Root Manifest Extensibility Contradiction

- Need to record new startup scope/resolution artifacts for auditability.
- `doc/wasm/root-image-manifest.schema.json` has
  `artifacts.additionalProperties: false`.

Impact:
- Cannot add startup artifacts to root manifest without schema update.

Spec closure required:
- Decide whether startup artifacts belong in root manifest, repro manifest, or
  both; update schema and smoke checks consistently.

## C-012 Resolver Authority Contradiction

- Current resolver pathways split between metadata resolver and kernel probe.
- Plan defines new resolution artifact but not canonical authority model.

Impact:
- Different engineers can produce incompatible status results.

Spec closure required:
- Define staged resolver model and precedence rules.
