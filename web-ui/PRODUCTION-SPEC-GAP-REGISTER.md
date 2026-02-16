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
| `web-ui/ui-doctrine.md` | R2 (draft contracts created) | Draft contracts exist but still need conformance fixtures and review closure before R3 | 1. `web-ui/spec/ui-visual-tokens-v1.json` 2. `web-ui/spec/ui-component-visual-contract-v1.md` 3. `web-ui/spec/ui-motion-contract-v1.md` 4. `web-ui/spec/ui-accessibility-visual-map-v1.md` |
| `web-ui/DEV-PLAN.md` high-level phases | R2 | Governance baseline now exists; remaining blockers are phase-level schemas/contracts still pending in later rows | 1. `web-ui/spec/spec-index-v1.md` 2. `web-ui/spec/normative-language-and-conformance-v1.md` 3. `web-ui/spec/glossary-v1.md` |
| `web-ui/DEV-PLAN.md` Phase 0 detailed | R3 | Canonical event/snapshot schemas and ordering/diff contracts now exist; ongoing execution quality is tracked by conformance evidence | 1. `web-ui/spec/event-log-schema-v1.json` 2. `web-ui/spec/event-log-ordering-and-clock-rules-v1.md` 3. `web-ui/spec/snapshot-schema-v1.json` 4. `web-ui/spec/snapshot-diff-format-v1.md` |
| `web-ui/DEV-PLAN.md` Phase 1 detailed | R2 | State graph and command model are not frozen as normative schemas/algorithms | 1. `web-ui/spec/ui-state-schema-v1.json` 2. `web-ui/spec/command-schema-v1.json` 3. `web-ui/spec/command-routing-algorithm-v1.md` 4. `web-ui/spec/focus-and-selection-contract-v1.md` |
| `web-ui/DEV-PLAN.md` Phase 2-6 | R1-R2 | Renderer/backend contracts not fully formalized: lifecycle, invalidation, hit-test semantics, failure behavior | 1. `web-ui/spec/renderer-backend-contract-v1.md` 2. `web-ui/spec/dom-backend-contract-v1.md` 3. `web-ui/spec/canvas-backend-contract-v1.md` 4. `web-ui/spec/webgl-backend-contract-v1.md` |
| `web-ui/DEV-PLAN.md` Phase 7 (persistence) | R2 | Core contracts now exist; remaining blockers are broad conformance/fault-injection coverage depth and implementation closure | 1. `web-ui/spec/persistence-purpose-and-user-contract-v1.md` 2. `web-ui/spec/persistence-semantic-profile-v1.md` 3. `web-ui/spec/persistence-semantic-merge-contract-v1.md` 4. `web-ui/spec/persistence-ref-update-protocol-v1.md` 5. `web-ui/spec/persistence-lease-protocol-v1.md` 6. `web-ui/spec/persistence-sync-and-conflict-protocol-v1.md` 7. `web-ui/spec/persistence-storage-backend-matrix-v1.md` 8. `web-ui/spec/persistence-envelope-schema-v1.json` 9. `web-ui/spec/persistence-migration-policy-v1.md` 10. `web-ui/spec/persistence-corruption-recovery-v1.md` 11. `web-ui/spec/persistence-remote-wire-contract-v1.md` 12. `web-ui/spec/persistence-failure-mode-matrix-v1.md` 13. `web-ui/spec/persistence-conformance-fixtures-v1.json` 14. `web-ui/tests/persistence-fault-harness.mjs` 15. `web-ui/tests/persistence-conformance-fixtures.test.mjs` |
| `web-ui/DEV-PLAN.md` Phase 8 (performance/scale) | R1-R2 | Budget goals exist but no production SLOs, sampling policy, regression policy, or capacity model | 1. `web-ui/spec/performance-slo-and-budgets-v1.md` 2. `web-ui/spec/perf-telemetry-sampling-policy-v1.md` 3. `web-ui/spec/scale-test-profile-v1.md` |
| `web-ui/DEV-PLAN.md` Phase 9 (command surface) | R2 | Keybinding precedence and conflict resolution need explicit normative conflict handling and locale rules | 1. `web-ui/spec/keybinding-resolution-contract-v1.md` 2. `web-ui/spec/keymap-localization-and-ime-policy-v1.md` |
| `web-ui/DEV-PLAN.md` Phase 10 track | R2 for mini-contract, R1 overall | Strong command/event mini-contract exists, but source mapping mechanism is deferred; end-to-end stop mapping unresolved | 1. `web-ui/spec/debug-location-provider-contract-v1.md` 2. `web-ui/spec/debugger-stepper-session-contract-v1.md` 3. `web-ui/spec/debugger-breakpoint-policy-contract-v1.md` |
| `web-ui/FRONT-END-DEV-PLAN.md` bridge phases | R1-R2 | ABI/wire format is referenced but not centralized under one versioned compatibility policy with negotiation/deprecation rules | 1. `web-ui/spec/runtime-bridge-envelope-v1.md` 2. `web-ui/spec/ui-wire-format-tree-v1.md` 3. `web-ui/spec/ui-wire-format-events-v1.md` 4. `web-ui/spec/protocol-version-negotiation-v1.md` |
| System-level production concerns (cross-cutting) | R0-R1 | Missing explicit security model, observability contract, release policy, operational runbooks | 1. `web-ui/spec/security-and-capability-model-v1.md` 2. `web-ui/spec/observability-contract-v1.md` 3. `web-ui/spec/release-compatibility-and-rollout-v1.md` 4. `web-ui/spec/incident-and-recovery-runbook-v1.md` |

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

## Final Production Gate

`web-ui` is considered production-spec complete only when all conditions are true:

- [ ] Every artifact listed in Section Gap Matrix exists.
- [ ] Every artifact meets Definition of Done.
- [ ] Every checklist item in sections A-H is checked.
- [ ] A conformance matrix exists linking each requirement to at least one automated test fixture.
- [ ] A compatibility report demonstrates version negotiation and mixed-version behavior.
- [ ] An operational readiness review confirms telemetry, rollout, rollback, and incident handling.

## Progress Notes

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
