# Release Compatibility and Rollout v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-17  
Scope: Production release gates, mixed-version compatibility policy, bridge migration waves, and rollback rules for `web-ui` runtime integration  
Depends on: `web-ui/spec/normative-language-and-conformance-v1.md`, `web-ui/spec/protocol-version-negotiation-v1.md`, `web-ui/spec/runtime-bridge-envelope-v1.md`, `web-ui/spec/ui-wire-format-tree-v1.md`, `web-ui/spec/ui-wire-format-events-v1.md`, `web-ui/spec/observability-contract-v1.md`, `scripts/wasm/lib/startup-gate.mjs`, `scripts/wasm/tests/ipc-conformance.mjs`, `scripts/wasm/tests/start-lisp-noninteractive-smoke.mjs`, `web-ui/src/quality-gates.mjs`  
Compatibility: `v1.x` preserves rollout wave IDs (`R4M-*`), validation IDs (`R4V-*`), compatibility IDs (`R4I-*`), and no-silent-fallback policy; incompatible rollout semantics require `v2`.

## 1. Purpose

This contract defines what <a id="REQ-RELEASE-COMPATIBILITY-AND-ROLLOUT-V1-9FDAAC9C99"></a>MUST pass before release promotion and how rollout/rollback decisions are made.
It is normative for startup readiness, bridge compatibility evidence, and mixed-version deployment behavior.

## 2. Release Compatibility Surfaces

A release candidate <a id="REQ-RELEASE-COMPATIBILITY-AND-ROLLOUT-V1-8069C32A6F"></a>MUST declare and validate these surfaces:

| Surface | Required `v1` contract |
|---|---|
| Startup hard-fail gate | `SRG-01..SRG-12` pass with strict mode (`allow_fallback=false`) |
| Kernel/runtime negotiation | ABI/transport/version checks per protocol negotiation contract |
| Runtime envelope and wire formats | Envelope `version=1`, tree/event payload `version=1` |
| IPC conformance lane | `ipc_shared_ring_v1` with `x03_clear_ready=true` |
| Runtime UI bridge conformance lane | `x04_step2_ready=true` and acceptable compatibility set |
| Quality budgets | `QUALITY_GATES_SCHEMA_VERSION="1"` and budget checks passing |

## 3. Mandatory Release Gates

A candidate is promotable only if all gates pass:

1. Startup gate summary status is `pass`.
2. No startup summary malformed payload condition is observed.
3. IPC conformance summary status is `pass` and `x03_clear_ready=true`.
4. Runtime UI bridge step2 summary status is `pass` and `x04_step2_ready=true`.
5. Bridge compatibility result set contains no required `reject` for target rollout scope.
6. Quality-budget evaluation contains zero failed mandatory checks.

## 4. Runtime UI Bridge Rollout Waves

Default rollout order <a id="REQ-RELEASE-COMPATIBILITY-AND-ROLLOUT-V1-5B3EB534AB"></a>MUST be monotonic:

1. `R4M-21` (`R4M-01`, `R4M-02`, `R4M-03`)
2. `R4M-22` (`R4M-04`, `R4M-05`)
3. `R4M-23` (`R4M-06`, `R4M-07`)
4. `R4M-24` (`R4M-08`, `R4M-09`, `R4M-10`, `R4M-11`, `R4M-12`, `R4M-13`)
5. `R4M-25` (all classes, release gate wave)
6. `R4M-26` (all classes, mixed-lane compatibility wave)

Waves <a id="REQ-RELEASE-COMPATIBILITY-AND-ROLLOUT-V1-19DA0DA58E"></a>MUST NOT skip backward unless rollback criteria in Section 7 are met.

## 5. Validation and Compatibility Matrix

Canonical compatibility IDs:

1. `R4I-01`
2. `R4I-02`
3. `R4I-03`
4. `R4I-04`
5. `R4I-05`
6. `R4I-06`

Canonical release validation mapping:

| Validation ID | Scope | Compatibility ID | Expected failure (if negative test) |
|---|---|---|---|
| `R4V-01` | `R4M-21` | `R4I-01` | None |
| `R4V-02` | `R4M-22` | `R4I-02` | None |
| `R4V-03` | `R4M-23` | `R4I-03` | None |
| `R4V-04` | `R4M-24` | `R4I-04` | None |
| `R4V-05` | `R4M-25` | `R4I-05` | None |
| `R4V-06` | `R4M-26` | `R4I-06` | None |
| `R4V-07` | class `R4M-03` | `R4I-05` | `RPL03-E008` |
| `R4V-08` | class `R4M-01` | `R4I-06` | `RPL03-E010` |
| `R4V-09` | class `R4M-05` | `R4I-02` | `RPL03-E002` |
| `R4V-10` | class `R4M-06` | `R4I-03` | `RPL03-E003` |
| `R4V-11` | class `R4M-10` | `R4I-04` | `RPL03-E007` |
| `R4V-12` | class `R4M-03` | `R4I-05` | `RPL03-E008` (forced-fallback assertion) |
| `R4V-13` | `R4M-26` | `R4I-05` | None |
| `R4V-14` | `R4M-26` | `R4I-06` | None |

## 6. Mixed-Version Policy

1. Consumers SHOULD be upgraded before producers enable new features.
2. Major-version mismatch <a id="REQ-RELEASE-COMPATIBILITY-AND-ROLLOUT-V1-BF605C8EDC"></a>MUST fail closed during negotiation.
3. Additive `v1.x` changes MAY proceed only if old consumers degrade safely and compatibility evidence is updated.
4. Any release claiming mixed-version readiness <a id="REQ-RELEASE-COMPATIBILITY-AND-ROLLOUT-V1-94DB16C3DE"></a>MUST include explicit `compatibility_results` evidence for relevant `R4I-*` IDs.

## 7. Rollback Policy

`v1` rollback policy is strict no-silent-fallback:

1. Hot-path fallback <a id="REQ-RELEASE-COMPATIBILITY-AND-ROLLOUT-V1-9885B6EAED"></a>MUST remain blocked (`allow_hotpath_fallback=false`).
2. Any forced fallback scenario <a id="REQ-RELEASE-COMPATIBILITY-AND-ROLLOUT-V1-3B9C0C0F11"></a>MUST emit `runtime_ui_bridge_rollback_record_v1`.
3. Rollback record <a id="REQ-RELEASE-COMPATIBILITY-AND-ROLLOUT-V1-F961B7DE0A"></a>MUST include `rollback_id`, `trigger_class_id`, `trigger_failure_code`, `applied_scope`, and `post_rollback_status`.
4. On rollback trigger, promotion <a id="REQ-RELEASE-COMPATIBILITY-AND-ROLLOUT-V1-07F5A7FE81"></a>MUST stop until a passing rerun is produced for the failed validation scope.

## 8. Canary and Promotion Workflow

Required release workflow:

1. Run startup gate and reject candidate on non-pass or malformed summary.
2. Run IPC conformance and require `x03_clear_ready=true`.
3. Run runtime bridge step2 validation for target wave and require `x04_step2_ready=true`.
4. Evaluate quality budgets and require mandatory checks pass.
5. Promote wave-by-wave in order from Section 4.
6. Freeze or rollback immediately on Section 9 failure codes.
7. Record promotion decision with run IDs and digest evidence.

## 9. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `release-gate.startup-failed` | Startup gate failed (`RPL01-E00x`) or summary malformed. | No | Fix startup preconditions and rerun from cold start. |
| `release-gate.ipc-not-ready` | IPC conformance failed or `x03_clear_ready=false`. | Conditional | Resolve IPC lane issue and rerun conformance. |
| `release-gate.bridge-not-ready` | Runtime bridge step2 failed or `x04_step2_ready=false`. | Conditional | Fix failed validation scope and rerun wave gate. |
| `release-gate.compatibility-reject` | Required compatibility ID reported `reject`. | No | Resolve compatibility mismatch before promotion. |
| `release-gate.quality-budget-failed` | Mandatory quality check failed. | Conditional | Tune/fix implementation and rerun quality evaluation. |
| `release-gate.rollback-triggered` | Rollback record emitted for candidate scope. | No | Stop rollout and execute rollback workflow. |

## 10. Conformance Fixtures and Pass Criteria

Minimum required evidence:

1. `scripts/wasm/tests/start-lisp-noninteractive-smoke.mjs`
2. `scripts/wasm/tests/ipc-conformance.mjs`
3. `web-ui/tests/phase-5-runtime-bridge.test.mjs`
4. `web-ui/tests/phase-5-runtime-command-roundtrip.test.mjs`
5. `web-ui/tests/phase-7-performance-budgets.test.mjs`

Pass criteria:

1. All gates in Sections 3-8 pass for target rollout scope.
2. Validation and compatibility IDs are reported per Section 5.
3. Rollback behavior remains fail-closed with explicit artifacts.

## 11. Conformance

An implementation and release workflow are conformant only if Sections 2-10 are satisfied.
