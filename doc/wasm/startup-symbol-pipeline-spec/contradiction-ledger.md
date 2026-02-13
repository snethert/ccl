# Contradiction Ledger (Execution Closure Track)

This ledger maps each known contradiction to:
- one authoritative decision,
- exact implementation microsteps/gates from
  `doc/wasm/startup-symbol-pipeline-implementation-plan.md`,
- objective closure evidence commands.

Status legend:
- `Decision`: `locked|open`
- `Implementation`: `pending|in-progress|closed`

## C-001 Plan Ordering Contradiction

- Contradiction:
  - plan says schema lock before scanner implementation,
  - sequence wording previously implied scanner-first implementation.
- Decision: `locked`
  - language freeze first, schema lock second, scanner implementation third.
- Implementation: `pending`
- Required microsteps:
  - `M-001` to `M-011`, then `M-012` onward.
- Closure evidence:
  - verify sequence in plan Section `15` and Track A in Section `19`,
  - verify gate history contains `G-01` pass before `G-02`, and `G-02` pass
    before `G-03`.

## C-002 Architecture Contradiction (Compromise vs Build Docs)

- Contradiction:
  - compromise says Common Lisp scanner owns scope production,
  - older docs state JS map builder is sole producer.
- Decision: `locked`
  - scanner produces scope artifact; Node consumes artifacts.
- Implementation: `pending`
- Required microsteps:
  - `M-064`, `M-065`, `M-067`.
- Closure evidence:
  - `rg -n "sole producer of startup bindings" doc/wasm/build.md`
    returns no active contradictory claim,
  - build docs include artifact-first scanner ownership statement.

## C-003 Runtime Behavior Contradiction (Consumer-Only vs Fallback Generation)

- Contradiction:
  - runtime should consume artifacts only,
  - runtime currently can generate fallback map if embedded artifact missing.
- Decision: `locked`
  - active mode hard-fails on missing required startup symbol scope artifact.
- Implementation: `pending`
- Required microsteps:
  - `M-002`, `M-022`, `M-026`, `M-033`, `M-060`.
- Closure evidence:
  - `rg -n "startup-symbol-scope-missing|buildStartupBindingMapArtifact" doc/wasm/js/make-real-image.mjs`,
  - focused lane run fails with explicit missing-artifact reason when scope
    argument is omitted.

## C-004 Packaging Contradiction (No JS Parser Path vs Pack-Time JS Production)

- Contradiction:
  - no second parser semantics path is allowed,
  - pack step currently builds startup map via JS source-based path.
- Decision: `locked`
  - pack stage may attach/copy prebuilt artifacts only.
- Implementation: `pending`
- Required microsteps:
  - `M-033`, `M-034`, `M-061`, `M-063`.
- Closure evidence:
  - `rg -n "buildStartupBindingMapArtifact|scan.*lisp" scripts/wasm/pack-inline-bundle-v2.mjs`
    shows no active JS source-scan path.

## C-005 Compaction Pass Contradiction (Legacy Field Preservation)

- Contradiction:
  - compaction currently preserves legacy startup map fields blindly.
- Decision: `locked`
  - migration policy explicitly controls preserve/reject behavior and prevents
    semantic reintroduction.
- Implementation: `pending`
- Required microsteps:
  - `M-036`, `M-061`, `M-063`.
- Closure evidence:
  - compacted manifest behavior is documented and tested under one active
    semantics path,
  - grep assertions confirm no path rehydrates JS-scanned semantics.

## C-006 CLI Contract Contradiction (Planned Flags vs Actual Parsers)

- Contradiction:
  - plan commands require `--startup-symbol-scope`,
  - current wrappers/parsers do not fully support forwarding.
- Decision: `locked`
  - add and wire `--startup-symbol-scope`,
    `--startup-symbol-resolution-out`, `--startup-symbol-contract`.
- Implementation: `pending`
- Required microsteps:
  - `M-022`, `M-023`, `M-049` to `M-052`.
- Closure evidence:
  - `node doc/wasm/js/make-real-image.mjs --help` shows options,
  - wrapper invocation forwards all three options end-to-end.

## C-007 Repro Flow Contradiction (Scanner-First vs Step Graph)

- Contradiction:
  - repro path must generate scope artifact before make-root-image,
  - current graph does not enforce this.
- Decision: `locked`
  - add scanner step before make-root-image and fail fast on scanner error.
- Implementation: `pending`
- Required microsteps:
  - `M-023`, `M-024`, `M-054`, `M-055`, `M-056`.
- Closure evidence:
  - repro step logs show scanner step ordering,
  - repro manifest contains scope artifact hash fields.

## C-008 Diagnostic Expectations Contradiction

- Contradiction:
  - scanner runs outside make-real-image,
  - yet make-real-image logs are expected to include scope evidence line.
- Decision: `locked`
  - make-real-image emits relay summary line
    `STARTUP_SYMBOL_SCOPE_BUILD` with artifact metadata/hash only.
- Implementation: `pending`
- Required microsteps:
  - `M-001`, `M-017`, `M-030`, `M-052`.
- Closure evidence:
  - focused lane logs include:
    - `STARTUP_SYMBOL_PIPELINE`,
    - `STARTUP_SYMBOL_SCOPE_BUILD` relay,
    - `STARTUP_SYMBOL_RESOLUTION_BUILD`.

## C-009 Dual-Semantics Policy Contradiction

- Contradiction:
  - temporary compatibility can become indefinite if not bounded.
- Decision: `locked`
  - compatibility may switch artifact source only and expires by explicit
    criteria.
- Implementation: `pending`
- Required microsteps:
  - `M-003`, `M-037`, `M-059`, `M-062`, `M-063`.
- Closure evidence:
  - docs include expiry criterion,
  - grep assertions confirm one active semantics path after cleanup.

## C-010 Contract Ownership Contradiction

- Contradiction:
  - scanner in Lisp cannot robustly parse JS contract source as canonical input.
- Decision: `locked`
  - pipeline generates `bootstrap-l0-contract.v1.json` sidecar before scanner.
- Implementation: `pending`
- Required microsteps:
  - `M-013`, `M-020`, `M-021` (`M-021.1`..`M-021.4`), `M-025`.
- Closure evidence:
  - scanner invocation includes `--contract-json` and required scanner flags,
  - compile script ordering proves
    `compile -> contract sidecar -> scanner -> bundle/image handoff`,
  - scanner missing-script guard fails fast with explicit missing-path error.

## C-011 Root Manifest Extensibility Contradiction

- Contradiction:
  - root manifest schema currently restrictive; startup artifacts need audit
    recording.
- Decision: `locked`
  - startup scope/resolution artifacts are required in repro manifest; root
    manifest remains unchanged in migration cut unless schema bump is explicit.
- Implementation: `pending`
- Required microsteps:
  - `M-024`, `M-056`, `M-057`, `M-058`.
- Closure evidence:
  - repro manifest entries include path/bytes/sha256 for startup artifacts.

## C-012 Resolver Authority Contradiction

- Contradiction:
  - current logic split across metadata and probe paths without canonical model.
- Decision: `locked`
  - staged hybrid resolver is the single authority model.
- Implementation: `pending`
- Required microsteps:
  - `M-026` to `M-032`, `M-053`.
- Closure evidence:
  - resolution artifact records status taxonomy and `resolver_source`,
  - focused lane logs and tests align with the same taxonomy.

## Closure Board

- [ ] C-001 implementation closed
- [ ] C-002 implementation closed
- [ ] C-003 implementation closed
- [ ] C-004 implementation closed
- [ ] C-005 implementation closed
- [ ] C-006 implementation closed
- [ ] C-007 implementation closed
- [ ] C-008 implementation closed
- [ ] C-009 implementation closed
- [ ] C-010 implementation closed
- [ ] C-011 implementation closed
- [ ] C-012 implementation closed
