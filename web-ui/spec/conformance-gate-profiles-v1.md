# Conformance Gate Profiles v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-17  
Scope: Normative CI gate commands, pass criteria, and blocking severity for claim scopes  
Depends on: `web-ui/spec/normative-language-and-conformance-v1.md`, `web-ui/spec/spec-index-v1.md`, `web-ui/spec/requirements-index-v1.json`, `web-ui/spec/conformance-evidence-index-v1.json`, `web-ui/scripts/lint-conformance.mjs`  
Compatibility: `v1.x` preserves gate IDs, claim scope names, and blocking semantics; incompatible gate model changes require `v2`.

## 1. Purpose

This artifact defines the executable gates used to determine claim-scope conformance.
It provides exact commands, pass criteria, and blocker severity.

## 2. Claim Scopes

Conformance claims are evaluated against these scopes:

1. `kernel-free-v1`
2. `kernel-full-v1`

`kernel-full-v1` is strictly additive over `kernel-free-v1`.

## 3. Gate Catalog

Commands are executed from `web-ui/`.

| Gate ID | Command | Pass criteria | Severity | Scopes |
|---|---|---|---|---|
| `gate.conformance.lint.v1` | `node scripts/lint-conformance.mjs` | Exit code `0` and no linter errors. | `blocker` | `kernel-free-v1`, `kernel-full-v1` |
| `gate.tests.fast.v1` | `npm run -s test:gate:fast` | Exit code `0`. | `blocker` | `kernel-free-v1`, `kernel-full-v1` |
| `gate.runtime.bridge.v1` | `node --test tests/bridge-microkernel.test.mjs tests/phase-5-runtime-output.test.mjs tests/phase-5-runtime-command-roundtrip.test.mjs tests/phase-5-runtime-command-dispatch.test.mjs tests/phase-5-runtime-inspector-integration.test.mjs tests/phase-5-runtime-restart-invoke.test.mjs` | Exit code `0`. | `blocker` | `kernel-free-v1`, `kernel-full-v1` |
| `gate.browser.render-only.v1` | `npm run -s test:browser:render` | Exit code `0`. | `blocker` | `kernel-free-v1`, `kernel-full-v1` |
| `gate.browser.kernel-preflight.v1` | `npm run -s test:browser:kernel-preflight` | Exit code `0` and required kernel assets present. | `blocker` | `kernel-full-v1` |
| `gate.browser.kernel-smoke.v1` | `npm run -s test:browser` | Exit code `0`. | `blocker` | `kernel-full-v1` |

## 4. Claim Evaluation Rules

1. A claim evaluator <a id="REQ-CONFORMANCE-GATE-PROFILES-V1-146A711BBE"></a>MUST run every gate listed for the requested claim scope.
2. A `blocker` gate failure <a id="REQ-CONFORMANCE-GATE-PROFILES-V1-1AA2E59469"></a>MUST mark that claim scope as `blocked`.
3. `kernel-free-v1` verdicts <a id="REQ-CONFORMANCE-GATE-PROFILES-V1-6D978DCAA4"></a>MUST be computed independently of kernel-only gates.
4. Pending or failed kernel-only gates <a id="REQ-CONFORMANCE-GATE-PROFILES-V1-32DA05AABD"></a>MUST block only `kernel-full-v1`, not `kernel-free-v1`.
5. Claim output <a id="REQ-CONFORMANCE-GATE-PROFILES-V1-BFFDC50482"></a>MUST include gate ID, command, result, and timestamp for each executed gate.
6. Claim output <a id="REQ-CONFORMANCE-GATE-PROFILES-V1-462A227637"></a>MUST include blocking failure IDs when verdict is `blocked`.

## 5. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `gate-profile.gate-failed` | A required gate command exited non-zero. | Conditional | Fix the failing gate and rerun claim evaluation. |
| `gate-profile.gate-missing` | A declared gate command is unavailable or invalid. | No | Restore or correct the gate definition. |
| `gate-profile.scope-blocked` | One or more blocker gates failed for a claim scope. | Conditional | Resolve listed blockers and rerun. |

## 6. Conformance

A gate evaluator is conformant only if it executes Section 3 commands exactly, applies Section 4 scope rules, and reports Section 5 failure semantics.
