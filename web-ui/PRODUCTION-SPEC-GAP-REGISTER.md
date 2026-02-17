# Web UI Production Spec Gap Register

Status: Draft  
Scope: `web-ui` only (explicitly excludes `web-ide` behavior details)

## Purpose

This document converts current `web-ui` planning/doctrine material into a strict production-spec gap register.
It answers one question: what artifacts are still required before a separate implementation team can build a production system without relying on ad hoc interpretation.

## Rigor Scale

- `R0` Vision-only: directional intent, not directly implementable.
- `R1` Plan-level: phase goals and milestones, limited normative detail.
- `R2` Partially normative: some contracts and invariants defined, not end-to-end.
- `R3` Production-ready: complete normative contracts, failure semantics, compatibility rules, and test gates.

## Section Gap Matrix

| Section | Current Rigor | Blocking Gaps | Required Artifacts (must exist) |
|---|---|---|---|
| `web-ui/ui-doctrine.md` | R3 | Doctrine contracts, conformance fixtures, and runner/report artifacts now exist; remaining risk is sustained visual/accessibility parity drift in implementation | 1. `web-ui/spec/ui-visual-tokens-v1.json` 2. `web-ui/spec/ui-component-visual-contract-v1.md` 3. `web-ui/spec/ui-motion-contract-v1.md` 4. `web-ui/spec/ui-accessibility-visual-map-v1.md` |
| `web-ui/DEV-PLAN.md` high-level phases | R3 | Governance baseline and phase-level contracts now exist through persistence conformance promotion; remaining risk is sustained implementation parity and release discipline | 1. `web-ui/spec/spec-index-v1.md` 2. `web-ui/spec/normative-language-and-conformance-v1.md` 3. `web-ui/spec/glossary-v1.md` |
| `web-ui/DEV-PLAN.md` Phase 0 detailed | R3 | Canonical event/snapshot schemas and ordering/diff contracts now exist; ongoing execution quality is tracked by conformance evidence | 1. `web-ui/spec/event-log-schema-v1.json` 2. `web-ui/spec/event-log-ordering-and-clock-rules-v1.md` 3. `web-ui/spec/snapshot-schema-v1.json` 4. `web-ui/spec/snapshot-diff-format-v1.md` |
| `web-ui/DEV-PLAN.md` Phase 1 detailed | R3 | Canonical state, command, routing, and focus/selection contracts now exist; remaining blockers move to later phases | 1. `web-ui/spec/ui-state-schema-v1.json` 2. `web-ui/spec/command-schema-v1.json` 3. `web-ui/spec/command-routing-algorithm-v1.md` 4. `web-ui/spec/focus-and-selection-contract-v1.md` |
| `web-ui/DEV-PLAN.md` Phase 2-6 | R3 | Renderer/backend lifecycle, invalidation, hit-test, and failure contracts are now formalized; remaining risk is implementation parity depth tracked by conformance fixtures | 1. `web-ui/spec/renderer-backend-contract-v1.md` 2. `web-ui/spec/dom-backend-contract-v1.md` 3. `web-ui/spec/canvas-backend-contract-v1.md` 4. `web-ui/spec/webgl-backend-contract-v1.md` |
| `web-ui/DEV-PLAN.md` Phase 7 (persistence) | R3 | Core contracts plus P0/P1 failure-matrix fixture coverage are now in required conformance lanes; remaining risk is long-run operational parity beyond deterministic fixture envelopes | 1. `web-ui/spec/persistence-purpose-and-user-contract-v1.md` 2. `web-ui/spec/persistence-semantic-profile-v1.md` 3. `web-ui/spec/persistence-semantic-merge-contract-v1.md` 4. `web-ui/spec/persistence-ref-update-protocol-v1.md` 5. `web-ui/spec/persistence-lease-protocol-v1.md` 6. `web-ui/spec/persistence-sync-and-conflict-protocol-v1.md` 7. `web-ui/spec/persistence-storage-backend-matrix-v1.md` 8. `web-ui/spec/persistence-envelope-schema-v1.json` 9. `web-ui/spec/persistence-migration-policy-v1.md` 10. `web-ui/spec/persistence-corruption-recovery-v1.md` 11. `web-ui/spec/persistence-remote-wire-contract-v1.md` 12. `web-ui/spec/persistence-failure-mode-matrix-v1.md` 13. `web-ui/spec/persistence-conformance-fixtures-v1.json` 14. `web-ui/tests/persistence-fault-harness.mjs` 15. `web-ui/tests/persistence-conformance-fixtures.test.mjs` |
| `web-ui/DEV-PLAN.md` Phase 8 (performance/scale) | R3 | Production SLOs, telemetry sampling policy, and scale acceptance profile are now specified; remaining risk is sustained implementation tuning against these gates | 1. `web-ui/spec/performance-slo-and-budgets-v1.md` 2. `web-ui/spec/perf-telemetry-sampling-policy-v1.md` 3. `web-ui/spec/scale-test-profile-v1.md` |
| `web-ui/DEV-PLAN.md` Phase 9 (command surface) | R3 | Keybinding precedence/conflict handling and locale/IME behavior are now formalized; remaining risk is sustained implementation parity against the new conformance gates | 1. `web-ui/spec/keybinding-resolution-contract-v1.md` 2. `web-ui/spec/keymap-localization-and-ime-policy-v1.md` |
| `web-ui/DEV-PLAN.md` Phase 10 track | R3 | Location-provider abstraction, stepper session lifecycle, and breakpoint policy/degradation behavior are now formalized; remaining risk is implementation parity for full stepper command/event coverage | 1. `web-ui/spec/debug-location-provider-contract-v1.md` 2. `web-ui/spec/debugger-stepper-session-contract-v1.md` 3. `web-ui/spec/debugger-breakpoint-policy-contract-v1.md` |
| `web-ui/FRONT-END-DEV-PLAN.md` bridge phases | R3 | Runtime envelope, tree/events wire formats, and compatibility negotiation/deprecation policy are now centralized under versioned bridge specs; remaining risk is sustained mixed-version soak validation in implementation lanes | 1. `web-ui/spec/runtime-bridge-envelope-v1.md` 2. `web-ui/spec/ui-wire-format-tree-v1.md` 3. `web-ui/spec/ui-wire-format-events-v1.md` 4. `web-ui/spec/protocol-version-negotiation-v1.md` |
| System-level production concerns (cross-cutting) | R3 | Security/capability, observability, release compatibility, and incident runbook contracts now exist; remaining risk is sustained implementation parity and operations drill coverage | 1. `web-ui/spec/security-and-capability-model-v1.md` 2. `web-ui/spec/observability-contract-v1.md` 3. `web-ui/spec/release-compatibility-and-rollout-v1.md` 4. `web-ui/spec/incident-and-recovery-runbook-v1.md` |

## Artifact Requirements (Definition of "Done")

Every required artifact above must satisfy all of the following:

1. Normative language:
- Uses RFC2119 terms (`MUST`, `SHOULD`, `MAY`) and a conformance section.

2. Versioning:
- Has explicit `version`, `status`, `last-updated`, and compatibility statement.

3. Data contracts:
- Defines complete field-level schema with required/optional/nullability/default rules.

4. Failure semantics:
- Enumerates error codes, retryability, and caller obligations.

5. Determinism:
- States deterministic behavior requirements and tie-break rules where ambiguity exists.

6. Security:
- Defines trust boundaries, input validation, and capability checks.

7. Observability:
- Defines required logs/metrics/traces and stable IDs for correlation.

8. Testability:
- Includes conformance test vectors/fixtures and pass criteria.

9. Compatibility:
- Defines backward/forward compatibility behavior and deprecation timelines.

10. Operational readiness:
- Defines rollout strategy, rollback conditions, and incident-handling hooks.

## Per-Section Checklist

### A. UI Doctrine to Production Visual Spec

- [ ] Token schema (`color`, `spacing`, `radius`, `typography`, `motion`, `elevation`) is numeric and complete.
- [ ] Component visual states are specified (`rest`, `hover`, `focus`, `active`, `disabled`, `error`).
- [ ] Contrast, focus ring, reduced-motion behavior are specified with objective thresholds.
- [ ] Backend parity requirements for DOM/canvas/WebGL are enumerated with acceptable variance limits.

### B. Core State + Commands

- [ ] State schema covers every persisted and runtime-only node with IDs and lifecycle.
- [ ] Command schema includes argument typing/defaulting/validation and effect classes.
- [ ] Routing precedence and tie-breakers are fully deterministic and specified.
- [ ] Command failure model includes user-visible vs silent failures and retry rules.

### C. Event Log + Replay + Snapshot

- [ ] Event envelope schema is frozen with ordering and monotonicity rules.
- [ ] Replay semantics define exact ordering, idempotency, and partial replay behavior.
- [ ] Snapshot schema includes compatibility/migration and stale-reference handling.
- [ ] Golden fixture format and diff semantics are versioned and documented.

### D. Renderer + Backends

- [ ] Backend interface includes lifecycle, invalidation model, text measurement semantics.
- [ ] Hit-test contract includes coordinate spaces, transforms, and ambiguous-hit tie-breakers.
- [ ] Render failure behavior is defined (fallback, quarantine, recovery).
- [ ] Accessibility behavior for non-DOM surfaces is defined (proxy strategy and guarantees).

### E. Persistence

- [ ] User-facing storage contract is explicit: filesystem mental model, non-goals, trust invariants, and file primacy are normative.
- [ ] Persistence profile contract is explicit: `file-primacy-v1` default, `semantic-canonical-v1` opt-in, no silent transitions, and mixed-profile compatibility gates.
- [ ] Semantic merge contract is explicit for profile-enabled lanes: controlled-reader requirements, deterministic 3-way rules, conflict taxonomy, and `MergeRecord` audit semantics.
- [ ] Ref-update protocol defines object-before-ref durability ordering, single-ref CAS (`refgen`), multi-ref atomic updates, and startup recovery scanner behavior.
- [ ] Ref updates support semantic guard preconditions (`requires_base_commit_id`, unresolved-conflict gate, lease epoch/finalization gates) with stable failure codes.
- [ ] Lease protocol defines acquire/renew/takeover rules, writer-token/epoch checks, and storage-layer write gating.
- [ ] Sync/conflict protocol defines push/pull closure rules, verification, divergence refs (`incoming/...`), conflict taxonomy, explicit merge-candidate-first workflow, and merge acceptance records (`MergeRecord` or equivalent).
- [ ] Remote wire contract defines exact endpoints, payload shapes, compatibility negotiation, and stable error/status mapping.
- [ ] Envelope and payload schemas are versioned and migration-safe.
- [ ] Corruption detection and repair/abort policy is specified.
- [ ] Failure-mode matrix enumerates crash points, lease races, and sync partition/retry outcomes with fixture IDs and coverage status.
- [ ] Conformance fixtures and fault-injection harness cover crash points, lease races, and sync partition/retry with deterministic replay.
- [ ] Session restore semantics define stale object handling and partial restore behavior.
- [ ] Storage backend matrix includes guarantees, limitations, and fallback order.

### F. Performance + Scale

- [ ] SLOs defined for interactive latency, render budget, and memory growth.
- [ ] Measurement methodology and sampling policy are documented.
- [ ] Load/scale test profiles and acceptance thresholds are fixed.
- [ ] Regression policy defines block/allow thresholds and exception workflow.

### G. Runtime Bridge + Wire Protocol

- [ ] Runtime envelope contract is centralized and versioned.
- [ ] Tree/event binary formats are fully specified byte-for-byte.
- [ ] Protocol negotiation and feature flags are specified.
- [ ] Compatibility and deprecation policy is explicit for producers/consumers.

### H. Security + Operations

- [ ] Threat model and trust boundaries are documented.
- [ ] Capability model defines grants, revocation, persistence, and audit semantics.
- [ ] Observability contract defines required telemetry and PII constraints.
- [ ] Rollout/canary/rollback and incident runbook are documented and tested.

## Final Production Gate (Auto-derived)

This section is generated by `web-ui/scripts/generate-production-gate-status.mjs`.
Manual checkbox edits are non-authoritative and must not be used for release decisions.

<!-- AUTO-GENERATED-GATE-STATUS:START -->
Generated at: 2026-02-17T02:17:01.848Z (UTC)

| Signal | Value |
|---|---:|
| Requirements indexed | 1022 |
| Evidence mappings | 1022 |
| Requirement artifacts | 48 |
| Unmapped requirements | 0 |
| Stale evidence entries | 0 |

| Gate ID | Claim scopes | Severity | Result | Duration (s) | Command |
|---|---|---|---|---:|---|
| `gate.conformance.lint.v1` | `kernel-free-v1`, `kernel-full-v1` | `blocker` | `pass` | 0.20 | `node scripts/lint-conformance.mjs --json` |
| `gate.tests.fast.v1` | `kernel-free-v1`, `kernel-full-v1` | `blocker` | `pass` | 0.63 | `npm run -s test:gate:fast` |
| `gate.runtime.bridge.v1` | `kernel-free-v1`, `kernel-full-v1` | `blocker` | `pass` | 0.44 | `node --test tests/bridge-microkernel.test.mjs tests/phase-5-runtime-output.test.mjs tests/phase-5-runtime-command-roundtrip.test.mjs tests/phase-5-runtime-command-dispatch.test.mjs tests/phase-5-runtime-inspector-integration.test.mjs tests/phase-5-runtime-restart-invoke.test.mjs` |
| `gate.browser.render-only.v1` | `kernel-free-v1`, `kernel-full-v1` | `blocker` | `pass` | 1.81 | `npm run -s test:browser:render` |
| `gate.browser.kernel-preflight.v1` | `kernel-full-v1` | `blocker` | `fail` | 0.39 | `npm run -s test:browser:kernel-preflight` |
| `gate.browser.kernel-smoke.v1` | `kernel-full-v1` | `blocker` | `fail` | 1.46 | `npm run -s test:browser` |

| Claim scope | Verdict | Blocking failures |
|---|---|---|
| `kernel-free-v1` | `pass` | none |
| `kernel-full-v1` | `blocked` | `gate.browser.kernel-preflight.v1`, `gate.browser.kernel-smoke.v1` |
<!-- AUTO-GENERATED-GATE-STATUS:END -->

## Progress Notes

- 2026-02-17: Added kernel-on browser harness preflight and path hardening:
- `web-ui/scripts/browser-kernel-preflight.mjs`
- `web-ui/tests/browser-runner.mjs` (`/scripts` and `/build` static path routing)
- `web-ui/tests/browser/harness.mjs` (kernel asset candidate-path fallback + diagnostics)
- Current preflight result: missing `wasm-ui-modules.json` and boot image artifacts block kernel-on browser lane.
- 2026-02-17: Added top-level production evidence artifacts and promoted final-gate conformance-matrix existence:
- `web-ui/spec/web-ui-conformance-matrix-v1.md`
- `web-ui/spec/protocol-compatibility-report-v1.md`
- `web-ui/spec/operational-readiness-review-v1.md`
- 2026-02-17: Promoted persistence P1 failure-matrix scenarios to required coverage and advanced Phase 7 to `R3`:
- `web-ui/spec/persistence-conformance-fixtures-v1.json` (v1.1.0; promoted former `pending.*` scenarios to required IDs)
- `web-ui/spec/persistence-failure-mode-matrix-v1.md` (v1.1.0; P0/P1 rows now covered)
- `web-ui/tests/persistence-conformance-fixtures.test.mjs` (full-run and promoted-P1 required assertions)
- 2026-02-17: Promoted UI doctrine row to `R3` after conformance fixture/runner validation:
- `web-ui/tests/phase-3-ui-doctrine.test.mjs`
- `web-ui/tests/phase-7-ui-conformance-fixtures.test.mjs`
- `web-ui/tests/phase-7-conformance-runner.test.mjs`
- 2026-02-17: Added Security + Operations production contracts:
- `web-ui/spec/security-and-capability-model-v1.md`
- `web-ui/spec/observability-contract-v1.md`
- `web-ui/spec/release-compatibility-and-rollout-v1.md`
- `web-ui/spec/incident-and-recovery-runbook-v1.md`
- 2026-02-17: Added runtime bridge and wire-format production contracts:
- `web-ui/spec/runtime-bridge-envelope-v1.md`
- `web-ui/spec/ui-wire-format-tree-v1.md`
- `web-ui/spec/ui-wire-format-events-v1.md`
- `web-ui/spec/protocol-version-negotiation-v1.md`
- 2026-02-16: Added persistence purpose and user-contract spec:
- `web-ui/spec/persistence-purpose-and-user-contract-v1.md`
- 2026-02-16: Added persistence profile and semantic merge contracts:
- `web-ui/spec/persistence-semantic-profile-v1.md`
- `web-ui/spec/persistence-semantic-merge-contract-v1.md`
- 2026-02-16: Added persistence protocol scaffolding:
- `web-ui/spec/persistence-ref-update-protocol-v1.md`
- `web-ui/spec/persistence-lease-protocol-v1.md`
- `web-ui/spec/persistence-sync-and-conflict-protocol-v1.md`
- `web-ui/spec/persistence-storage-backend-matrix-v1.md`
- 2026-02-16: Added persistence envelope schema and protected-ref guard hardening:
- `web-ui/spec/persistence-envelope-schema-v1.json`
- `web-ui/spec/persistence-ref-update-protocol-v1.md` (v1.1.0 protected-ref guard requirements)
- `web-ui/spec/persistence-sync-and-conflict-protocol-v1.md` (v1.1.0 guarded protected-ref fast-forward)
- `web-ui/spec/persistence-lease-protocol-v1.md` (v1.1.0 guard + lease epoch coupling)
- `web-ui/spec/persistence-storage-backend-matrix-v1.md` (envelope validation requirement before protected ref advancement)
- 2026-02-16: Added persistence migration and corruption recovery contracts:
- `web-ui/spec/persistence-migration-policy-v1.md`
- `web-ui/spec/persistence-corruption-recovery-v1.md`
- 2026-02-16: Added persistence remote wire contract and failure-mode matrix:
- `web-ui/spec/persistence-remote-wire-contract-v1.md`
- `web-ui/spec/persistence-failure-mode-matrix-v1.md`
- 2026-02-16: Added persistence conformance fixture set and deterministic fault harness scaffold:
- `web-ui/spec/persistence-conformance-fixtures-v1.json`
- `web-ui/tests/persistence-fault-harness.mjs`
- `web-ui/tests/persistence-conformance-fixtures.test.mjs`
- 2026-02-16: Added P1 failure-matrix fixture scaffolds and harness expectation support:
- `web-ui/spec/persistence-conformance-fixtures-v1.json` (new `pending.*` P1 scenarios from failure matrix)
- `web-ui/tests/persistence-fault-harness.mjs` (remote incoming-ref prefix expectation)
- `web-ui/tests/persistence-conformance-fixtures.test.mjs` (P1 scaffold presence assertions)
- 2026-02-16: Created first-pass UI doctrine production artifacts:
- `web-ui/spec/ui-visual-tokens-v1.json`
- `web-ui/spec/ui-component-visual-contract-v1.md`
- `web-ui/spec/ui-motion-contract-v1.md`
- `web-ui/spec/ui-accessibility-visual-map-v1.md`
- 2026-02-16: Added doctrine conformance scaffolding:
- `web-ui/spec/ui-conformance-fixtures-v1.json`
- `web-ui/spec/ui-conformance-fixture-catalog-v1.md`
- `web-ui/spec/ui-conformance-matrix-v1.md`
- `web-ui/spec/ui-conformance-report-schema-v1.json`
- 2026-02-16: Added baseline accessibility audit:
- `web-ui/spec/ui-accessibility-baseline-audit-v1.md`
- Baseline blockers identified and remediated: `border/surface` contrast (dark/light), `warning/surface` in light mode.
- Remediation adopted in theme tokens and guarded by test coverage in `web-ui/tests/theme.test.mjs`.
- 2026-02-16: Added web-ui governance baseline artifacts:
- `web-ui/spec/spec-index-v1.md`
- `web-ui/spec/normative-language-and-conformance-v1.md`
- `web-ui/spec/glossary-v1.md`
- 2026-02-16: Added Phase 0 canonical event/snapshot artifacts:
- `web-ui/spec/event-log-schema-v1.json`
- `web-ui/spec/event-log-ordering-and-clock-rules-v1.md`
- `web-ui/spec/snapshot-schema-v1.json`
- `web-ui/spec/snapshot-diff-format-v1.md`
- 2026-02-16: Added Phase 1 core model and command artifacts:
- `web-ui/spec/ui-state-schema-v1.json`
- `web-ui/spec/command-schema-v1.json`
- `web-ui/spec/command-routing-algorithm-v1.md`
- `web-ui/spec/focus-and-selection-contract-v1.md`
- 2026-02-16: Added Phase 2-6 renderer/backend contracts:
- `web-ui/spec/renderer-backend-contract-v1.md`
- `web-ui/spec/dom-backend-contract-v1.md`
- `web-ui/spec/canvas-backend-contract-v1.md`
- `web-ui/spec/webgl-backend-contract-v1.md`
- 2026-02-16: Added Phase 8 performance and scale contracts:
- `web-ui/spec/performance-slo-and-budgets-v1.md`
- `web-ui/spec/perf-telemetry-sampling-policy-v1.md`
- `web-ui/spec/scale-test-profile-v1.md`
- 2026-02-16: Added Phase 9 command-surface contracts:
- `web-ui/spec/keybinding-resolution-contract-v1.md`
- `web-ui/spec/keymap-localization-and-ime-policy-v1.md`
- 2026-02-16: Added Phase 10 debugger contracts:
- `web-ui/spec/debug-location-provider-contract-v1.md`
- `web-ui/spec/debugger-stepper-session-contract-v1.md`
- `web-ui/spec/debugger-breakpoint-policy-contract-v1.md`

## Recommended Ownership Model

- Spec editor: `web-ui` owner (single accountable reviewer for consistency).
- Contract owners:
- Runtime bridge contracts: kernel/bridge owner.
- UI state and command contracts: UI core owner.
- Persistence and migration: storage owner.
- Performance and scale: runtime performance owner.
- Security/capabilities: platform security owner.

## Update Rule

Any change to `web-ui/DEV-PLAN.md`, `web-ui/FRONT-END-DEV-PLAN.md`, or runtime UI ABI references must update this register in the same PR.
