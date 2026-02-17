# Operational Readiness Review v1

Status: Draft  
Version: 1.1.0  
Last updated: 2026-02-17  
Scope: Release-readiness review for telemetry, rollout/rollback, and incident response obligations  
Depends on: `web-ui/spec/observability-contract-v1.md`, `web-ui/spec/release-compatibility-and-rollout-v1.md`, `web-ui/spec/incident-and-recovery-runbook-v1.md`, `web-ui/spec/security-and-capability-model-v1.md`, `web-ui/spec/conformance-gate-profiles-v1.md`  
Compatibility: Review checklist semantics are stable for `v1.x`; incompatible readiness criteria changes require `v2`.

## 1. Purpose

This review records current operational readiness against production obligations.
It is evidence-oriented and references executable lanes where available.

## 2. Readiness Checklist

| Readiness Area | Requirement | Evidence | Status |
|---|---|---|---|
| Telemetry contract | Required reliability/performance signals are emitted and validated by tests. | `tests/phase-7-performance-budgets.test.mjs`, `tests/phase-7-reliability.test.mjs` | pass |
| Rollout/rollback policy | Compatibility and rollback rules exist and are linked to release policy artifacts. | `web-ui/spec/release-compatibility-and-rollout-v1.md` | pass |
| Incident response | Incident runbook exists with escalation/recovery actions. | `web-ui/spec/incident-and-recovery-runbook-v1.md` | pass |
| Capability enforcement | Capability checks have executable coverage. | `tests/capabilities.test.mjs` | pass |
| Browser render fallback lane | Kernel-free browser render path has executable coverage. | `tests/browser-render-only.test.mjs` | pass |
| Kernel-enabled ops lane | Kernel-on smoke and incident-drill lanes execute in CI-like environment. | Not executable in current environment | pending |

## 3. Claim Scope Verdicts

| Claim scope | Required blocker gates | Current verdict | Blocking gates |
|---|---|---|---|
| `kernel-free-v1` | `ops.gate.fast.v1`, `ops.browser.render-only.v1`, `ops.runtime.bridge.v1` | pass | none |
| `kernel-full-v1` | all `kernel-free-v1` gates plus `ops.browser.kernel-preflight.v1` and kernel-on smoke lanes | blocked | `ops.browser.kernel-preflight.v1`, `ops.browser.kernel-on-smoke.v1` |

## 4. Executed Gate Evidence

| Gate ID | Command | Last run (UTC) | Result |
|---|---|---|---|
| `ops.gate.fast.v1` | `npm run -s test:gate:fast` | 2026-02-17 | pass |
| `ops.browser.render-only.v1` | `npm run -s test:browser:render` | 2026-02-17 | pass |
| `ops.browser.kernel-preflight.v1` | `npm run -s test:browser:kernel-preflight` | 2026-02-17 | fail (missing bundle/image artifacts) |
| `ops.browser.kernel-on-smoke.v1` | `npm run -s test:browser` | 2026-02-17 | fail (kernel assets unavailable) |
| `ops.runtime.bridge.v1` | `node --test tests/bridge-microkernel.test.mjs tests/phase-5-runtime-output.test.mjs tests/phase-5-runtime-command-roundtrip.test.mjs tests/phase-5-runtime-command-dispatch.test.mjs tests/phase-5-runtime-inspector-integration.test.mjs tests/phase-5-runtime-restart-invoke.test.mjs` | 2026-02-17 | pass |

## 5. Readiness Decision

1. `kernel-free-v1` release lanes are operationally ready under current evidence.
2. `kernel-full-v1` operational readiness remains blocked by environment constraints.
3. Kernel-only blocked lanes do not invalidate `kernel-free-v1` claims.

## 6. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `ops-readiness.evidence-failed` | A required gate command failed. | Conditional | Fix failing lane and re-run review. |
| `ops-readiness.evidence-stale` | Evidence is missing or not current for the release cut. | Conditional | Re-run required lanes and refresh timestamps. |
| `ops-readiness.environment-blocked` | Required lane cannot execute in current environment. | Conditional | Move to supported environment or downgrade release claim scope. |
| `ops-readiness.scope-blocked` | A claim scope has one or more failed blocker lanes. | Conditional | Resolve listed blockers for that scope. |

## 7. Conformance

This review is conformant only if:

1. Every checklist row in Section 2 has explicit evidence and status.
2. Section 3 declares verdicts for both `kernel-free-v1` and `kernel-full-v1`.
3. Any `pending` kernel-only status blocks only `kernel-full-v1` unless explicitly promoted.
4. Section 4 gate evidence is current for the release window.
