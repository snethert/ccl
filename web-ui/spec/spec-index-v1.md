# Web UI Spec Index v1

Status: Draft  
Version: 1.2.0  
Last updated: 2026-02-17  
Scope: Canonical registry of `web-ui` normative specification artifacts and conformance profiles  
Depends on: `web-ui/PRODUCTION-SPEC-GAP-REGISTER.md`  
Compatibility: `v1.x` preserves artifact identity, profile names, and claim scope names; removing or renaming required artifacts requires `v2`.

## 1. Purpose

This document is the canonical index for production `web-ui` specification artifacts.
It defines artifact classes, conformance profiles, and profile-to-artifact requirements.

### 1.1 Governance Bootstrap Order

To avoid governance bootstrapping ambiguity, initialization order is:

1. `spec-index-v1.md` (artifact registry root)
2. `glossary-v1.md` (canonical terms)
3. `normative-language-and-conformance-v1.md` (keyword and evidence process)
4. Remaining profile artifacts

## 2. Artifact Classes

Each artifact in this index has one class:

1. `required`: <a id="REQ-SPEC-INDEX-V1-D2389F924A"></a>MUST exist and <a id="REQ-SPEC-INDEX-V1-ACB4251149"></a>MUST be implemented for its profile claim.
2. `required-planned`: Reserved required artifact that is not fully authored yet; implementations <a id="REQ-SPEC-INDEX-V1-7371640C49"></a>MUST report this profile as incomplete.
3. `informational`: Non-gating material that MAY support implementation and review.

## 3. Profile Model

Conformance profiles are cumulative unless explicitly marked otherwise.

1. `governance-base-v1`
2. `ui-visual-v1`
3. `persistence-v1`
4. `runtime-bridge-v1`
5. `full-web-ui-v1`

`full-web-ui-v1` is the union of all `required` and `required-planned` artifacts in this index.

### 3.1 Claim Scope Model

Claims are evaluated against this scope:

1. `full-runtime-v1`

Scope rule:

1. `full-runtime-v1` requires all blocker gates, including kernel-enabled lanes.

## 4. Canonical Artifact Registry

### 4.1 Governance Base (`governance-base-v1`)

| Artifact | Class | Notes |
|---|---|---|
| `web-ui/spec/spec-index-v1.md` | `required` | This index. |
| `web-ui/spec/normative-language-and-conformance-v1.md` | `required` | RFC2119 interpretation and conformance claim model. |
| `web-ui/spec/glossary-v1.md` | `required` | Canonical terminology. |
| `web-ui/spec/spec-ratification-policy-v1.md` | `required` | Spec lifecycle states and sign-off workflow. |
| `web-ui/spec/conformance-gate-profiles-v1.md` | `required` | Claim-scope gate commands and blocker semantics. |
| `web-ui/spec/error-code-registry-v1.md` | `required` | Cross-spec error-code namespace and naming registry. |

### 4.2 UI Visual Doctrine Contracts (`ui-visual-v1`)

| Artifact | Class | Notes |
|---|---|---|
| `web-ui/spec/ui-visual-tokens-v1.json` | `required` | Token source of truth. |
| `web-ui/spec/ui-component-visual-contract-v1.md` | `required` | Component state visuals and variance limits. |
| `web-ui/spec/ui-motion-contract-v1.md` | `required` | Motion categories and reduced-motion behavior. |
| `web-ui/spec/ui-accessibility-visual-map-v1.md` | `required` | Visual accessibility criteria. |
| `web-ui/spec/ui-conformance-fixtures-v1.json` | `required` | Machine fixture source. |
| `web-ui/spec/ui-conformance-fixture-catalog-v1.md` | `required` | Human-readable fixture catalog. |
| `web-ui/spec/ui-conformance-runner-contract-v1.md` | `required` | Runner behavior contract. |
| `web-ui/spec/ui-conformance-matrix-v1.md` | `required` | Requirement-to-fixture mapping. |
| `web-ui/spec/ui-conformance-report-schema-v1.json` | `required` | Report schema contract. |
| `web-ui/spec/theme-override-contract-v1.md` | `required` | User/workspace theme override behavior. |
| `web-ui/spec/non-dom-accessibility-proxy-contract-v1.md` | `required` | Canvas/WebGL accessibility proxy contract. |
| `web-ui/spec/ui-accessibility-baseline-audit-v1.md` | `informational` | Baseline audit and remediation notes. |

### 4.3 Core Model, Events, Commands (`full-web-ui-v1`)

| Artifact | Class | Notes |
|---|---|---|
| `web-ui/spec/event-log-schema-v1.json` | `required` | Event envelope and payload schemas. |
| `web-ui/spec/event-log-ordering-and-clock-rules-v1.md` | `required` | Ordering and monotonic clock rules. |
| `web-ui/spec/snapshot-schema-v1.json` | `required` | Snapshot contract. |
| `web-ui/spec/snapshot-diff-format-v1.md` | `required` | Stable diff and golden format. |
| `web-ui/spec/ui-state-schema-v1.json` | `required` | State graph schema. |
| `web-ui/spec/command-schema-v1.json` | `required` | Command registry and invocation schema. |
| `web-ui/spec/command-routing-algorithm-v1.md` | `required` | Deterministic routing rules. |
| `web-ui/spec/command-undo-redo-contract-v1.md` | `required` | Undo/redo transaction and reversibility rules. |
| `web-ui/spec/focus-and-selection-contract-v1.md` | `required` | Focus/selection lifecycle rules. |

### 4.4 Render Backends (`full-web-ui-v1`)

| Artifact | Class | Notes |
|---|---|---|
| `web-ui/spec/renderer-backend-contract-v1.md` | `required` | Common backend lifecycle. |
| `web-ui/spec/dom-backend-contract-v1.md` | `required` | DOM-specific contract. |
| `web-ui/spec/canvas-backend-contract-v1.md` | `required` | Canvas-specific contract. |
| `web-ui/spec/webgl-backend-contract-v1.md` | `required` | WebGL-specific contract. |

### 4.5 Persistence (`persistence-v1`)

| Artifact | Class | Notes |
|---|---|---|
| `web-ui/spec/persistence-purpose-and-user-contract-v1.md` | `required` | User-facing storage model. |
| `web-ui/spec/persistence-semantic-profile-v1.md` | `required` | Profile and gating semantics. |
| `web-ui/spec/controlled-reader-contract-v1.md` | `required` | Deterministic controlled-reader profile contract. |
| `web-ui/spec/persistence-semantic-merge-contract-v1.md` | `required` | Deterministic semantic merge rules. |
| `web-ui/spec/persistence-ref-update-protocol-v1.md` | `required` | CAS/ref advancement protocol. |
| `web-ui/spec/persistence-lease-protocol-v1.md` | `required` | Writer lease semantics. |
| `web-ui/spec/persistence-sync-and-conflict-protocol-v1.md` | `required` | Sync and divergence policy. |
| `web-ui/spec/persistence-storage-backend-matrix-v1.md` | `required` | Storage guarantees and fallback order. |
| `web-ui/spec/persistence-envelope-schema-v1.json` | `required` | Persistence envelope schema. |
| `web-ui/spec/persistence-migration-policy-v1.md` | `required` | Migration and compatibility policy. |
| `web-ui/spec/persistence-corruption-recovery-v1.md` | `required` | Corruption detection/recovery behavior. |
| `web-ui/spec/persistence-remote-wire-contract-v1.md` | `required` | Remote wire API contract. |
| `web-ui/spec/persistence-failure-mode-matrix-v1.md` | `required` | Crash/race/partition matrix. |
| `web-ui/spec/persistence-gc-and-compaction-policy-v1.md` | `required` | Reachability, retention, and compaction policy. |
| `web-ui/spec/persistence-conformance-fixtures-v1.json` | `required` | Persistence fixtures source. |
| `web-ui/tests/persistence-fault-harness.mjs` | `required` | Deterministic fault harness. |
| `web-ui/tests/persistence-conformance-fixtures.test.mjs` | `required` | Fixture conformance tests. |

### 4.6 Performance and Scale (`full-web-ui-v1`)

| Artifact | Class | Notes |
|---|---|---|
| `web-ui/spec/performance-slo-and-budgets-v1.md` | `required` | Interactive/perf SLOs and budgets. |
| `web-ui/spec/perf-telemetry-sampling-policy-v1.md` | `required` | Sampling and measurement policy. |
| `web-ui/spec/scale-test-profile-v1.md` | `required` | Scale test profile and gates. |

### 4.7 Command Surface and Debugger (`full-web-ui-v1`)

| Artifact | Class | Notes |
|---|---|---|
| `web-ui/spec/keybinding-resolution-contract-v1.md` | `required` | Keybinding precedence and conflicts. |
| `web-ui/spec/keymap-localization-and-ime-policy-v1.md` | `required` | Locale and IME behavior. |
| `web-ui/spec/i18n-l10n-contract-v1.md` | `required` | UI string externalization and locale formatting rules. |
| `web-ui/spec/text-editing-contract-v1.md` | `required` | Cursor/selection/IME editing model across backends. |
| `web-ui/spec/clipboard-interaction-contract-v1.md` | `required` | Clipboard command and sanitization behavior. |
| `web-ui/spec/drag-and-drop-interaction-contract-v1.md` | `required` | Drag source/target and drop negotiation protocol. |
| `web-ui/spec/ui-interaction-window-management-contract-v1.md` | `required` | Window focus/stacking/resize governance. |
| `web-ui/spec/debug-location-provider-contract-v1.md` | `required` | Source mapping abstraction contract. |
| `web-ui/spec/debugger-stepper-session-contract-v1.md` | `required` | Stepper session lifecycle rules. |
| `web-ui/spec/debugger-breakpoint-policy-contract-v1.md` | `required` | Breakpoint policy and degradation behavior. |

### 4.8 Runtime Bridge (`runtime-bridge-v1`)

| Artifact | Class | Notes |
|---|---|---|
| `web-ui/spec/runtime-bridge-envelope-v1.md` | `required` | Runtime bridge envelope contract. |
| `web-ui/spec/ui-wire-format-tree-v1.md` | `required` | Tree payload wire format. |
| `web-ui/spec/ui-wire-format-tree-delta-v1.md` | `required` | Incremental tree patch wire format. |
| `web-ui/spec/ui-wire-format-events-v1.md` | `required` | Event payload wire format. |
| `web-ui/spec/protocol-version-negotiation-v1.md` | `required` | Negotiation/deprecation policy. |

### 4.9 Security and Operations (`full-web-ui-v1`)

| Artifact | Class | Notes |
|---|---|---|
| `web-ui/spec/security-and-capability-model-v1.md` | `required` | Trust boundary and capability policy. |
| `web-ui/spec/offline-and-service-worker-contract-v1.md` | `required` | Offline bootstrap and asset caching strategy. |
| `web-ui/spec/observability-contract-v1.md` | `required` | Logs/metrics/traces contract. |
| `web-ui/spec/release-compatibility-and-rollout-v1.md` | `required` | Rollout/rollback policy. |
| `web-ui/spec/incident-and-recovery-runbook-v1.md` | `required` | Operational incident playbook. |

### 4.10 Production Evidence and Readiness (`full-web-ui-v1`)

| Artifact | Class | Notes |
|---|---|---|
| `web-ui/spec/web-ui-conformance-matrix-v1.md` | `required` | System-level requirement-to-evidence mapping. |
| `web-ui/spec/requirements-index-v1.json` | `required` | Machine-readable requirement registry. |
| `web-ui/spec/conformance-evidence-index-v1.json` | `required` | Machine-readable requirement-to-evidence registry. |
| `web-ui/spec/protocol-compatibility-report-v1.md` | `required` | Executable compatibility and mixed-version evidence. |
| `web-ui/spec/operational-readiness-review-v1.md` | `required` | Release readiness evidence and gate status. |

## 5. Conformance Claim Rules

1. A profile claim <a id="REQ-SPEC-INDEX-V1-9D76F7F4B3"></a>MUST list the exact profile name, claim scope, and artifact version set.
2. A profile claim <a id="REQ-SPEC-INDEX-V1-E63FD82BFB"></a>MUST fail if any profile artifact is absent or marked non-conformant.
3. A profile claim <a id="REQ-SPEC-INDEX-V1-8A84C4E043"></a>MUST include evidence links to at least one automated fixture or test per `required` artifact.
4. `required-planned` artifacts block final profile conformance and <a id="REQ-SPEC-INDEX-V1-44EDF71EF6"></a>MUST be reported as open gaps.
5. Any failing blocker lane <a id="REQ-SPEC-INDEX-V1-6FA1AE70CC"></a>MUST block `full-runtime-v1` claims.
6. Partial claims MAY be made for subset profiles (`governance-base-v1`, `ui-visual-v1`, `persistence-v1`, `runtime-bridge-v1`).

## 6. Determinism and Tie-Break Baseline

1. Conformance tooling <a id="REQ-SPEC-INDEX-V1-70850753C4"></a>MUST evaluate artifacts and profiles in deterministic lexical order by artifact path.
2. Duplicate artifact declarations <a id="REQ-SPEC-INDEX-V1-2AC094D916"></a>MUST be rejected.
3. Profile expansion order <a id="REQ-SPEC-INDEX-V1-A2532F083F"></a>MUST be deterministic and stable across runs.

## 7. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `spec-index.artifact-missing` | Required artifact path is absent. | No | Add or restore artifact before claim. |
| `spec-index.class-invalid` | Artifact class is unknown or invalid. | No | Correct index metadata. |
| `spec-index.profile-unknown` | Claim references unknown profile. | No | Use a declared profile name. |
| `spec-index.evidence-missing` | Required profile claim lacks traceable test evidence. | No | Provide fixture/test evidence mapping. |
| `spec-index.profile-blocked-by-planned` | Claim includes `required-planned` artifacts. | No | Complete planned required artifacts first. |

## 8. Conformance

An implementation or release process is conformant with this index only if all conditions hold:

1. This artifact and the governance-base artifacts exist and validate as current major version (`v1`).
2. Every published profile claim expands deterministically to this index's artifact set.
3. No claim labeled complete includes any unresolved `required-planned` artifact.
4. Every required artifact in a completed claim has linked automated evidence.
