# Conformance Gate Profiles v1

Status: Draft  
Version: 1.2.0  
Last updated: 2026-02-17  
Scope: Normative CI gate commands, pass criteria, and blocking severity for claim scopes  
Depends on: `web-ui/spec/normative-language-and-conformance-v1.md`, `web-ui/spec/spec-index-v1.md`, `web-ui/spec/requirements-index-v1.json`, `web-ui/spec/conformance-evidence-index-v1.json`, `web-ui/scripts/lint-conformance.mjs`  
Compatibility: `v1.x` preserves active gate IDs, claim scope name, and blocking semantics; `v1.2+` adds planned extension gate IDs without changing active blocker execution.

## 1. Purpose

This artifact defines the executable gates used to determine claim-scope conformance.
It provides exact commands, pass criteria, and blocker severity.

## 2. Claim Scopes

Conformance claims are evaluated against this scope:

1. `full-runtime-v1`

## 3. Active Gate Catalog (Blocking)

Commands are executed from `web-ui/`.

| Gate ID | Command | Pass criteria | Timeout (s) | Severity | Scopes |
|---|---|---|---|---|---|
| `gate.conformance.lint.v1` | `node scripts/lint-conformance.mjs --json` | Exit code `0` and no linter errors. | `60` | `blocker` | `full-runtime-v1` |
| `gate.tests.fast.v1` | `npm run -s test:gate:fast` | Exit code `0`. | `300` | `blocker` | `full-runtime-v1` |
| `gate.runtime.bridge.v1` | `node --test tests/bridge-microkernel.test.mjs tests/phase-5-runtime-output.test.mjs tests/phase-5-runtime-command-roundtrip.test.mjs tests/phase-5-runtime-command-dispatch.test.mjs tests/phase-5-runtime-inspector-integration.test.mjs tests/phase-5-runtime-restart-invoke.test.mjs` | Exit code `0`. | `300` | `blocker` | `full-runtime-v1` |
| `gate.browser.render-only.v1` | `npm run -s test:browser:render` | Exit code `0`. | `420` | `blocker` | `full-runtime-v1` |
| `gate.browser.kernel-preflight.v1` | `npm run -s test:browser:kernel-preflight` | Exit code `0` and required kernel assets present. | `180` | `blocker` | `full-runtime-v1` |
| `gate.browser.kernel-smoke.v1` | `npm run -s test:browser` | Exit code `0`. | `600` | `blocker` | `full-runtime-v1` |

## 3.1 Planned Extension Gates (Non-blocking)

These gates remain staged design artifacts and are not blockers for baseline `full-runtime-v1` claims.

| Gate ID | Command | Planned pass criteria | Timeout (s) | Severity | Scopes |
|---|---|---|---|---|---|
| `gate.runtime.input-flood.v1` | `node --test tests/bridge-input-flood.test.mjs tests/bridge-coalescing-determinism.test.mjs tests/ui-poll-backpressure.test.mjs` | Bounded-input and coalescing profile assertions hold for extension lanes. | `300` | `planned` | `full-runtime-v1` |
| `gate.runtime.qos-contention.v1` | `node --test tests/runtime-lane-contention.test.mjs tests/runtime-command-admission.test.mjs` | No starvation violations on control lanes under mixed workload fixtures. | `300` | `planned` | `full-runtime-v1` |
| `gate.runtime.realtime-profile.v1` | `node --test tests/realtime-input-codec.test.mjs tests/realtime-clock-profile.test.mjs` | Realtime profile drift and replay checks pass. | `300` | `planned` | `full-runtime-v1` |

## 4. Claim Evaluation Rules

1. A claim evaluator <a id="REQ-CONFORMANCE-GATE-PROFILES-V1-8B5BC9D3F0"></a>MUST run every gate listed in Section 3 for the requested claim scope.
2. A `blocker` gate failure <a id="REQ-CONFORMANCE-GATE-PROFILES-V1-1AA2E59469"></a>MUST mark that claim scope as `blocked`.
3. Claim output <a id="REQ-CONFORMANCE-GATE-PROFILES-V1-1B3EDE0EC1"></a>MUST include gate ID, command, result, and timestamp for each executed gate.
4. Claim output <a id="REQ-CONFORMANCE-GATE-PROFILES-V1-30280B963E"></a>MUST include blocking failure IDs when verdict is `blocked`.
5. Gate execution <a id="REQ-CONFORMANCE-GATE-PROFILES-V1-E1935EE821"></a>MUST terminate a gate as failed when its timeout budget is exceeded.
6. Gate runner <a id="REQ-CONFORMANCE-GATE-PROFILES-V1-A5F07A4223"></a>MUST record timeout vs. non-timeout failure cause in claim output.
7. Planned extension gates in Section 3.1 <a id="REQ-CONFORMANCE-GATE-PROFILES-V1-21BFB885B5"></a>MUST NOT be reported as blocker verdict inputs for baseline `full-runtime-v1` claims.

## 5. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `gate-profile.gate-failed` | A required gate command exited non-zero. | Conditional | Fix the failing gate and rerun claim evaluation. |
| `gate-profile.gate-missing` | A declared gate command is unavailable or invalid. | No | Restore or correct the gate definition. |
| `gate-profile.scope-blocked` | One or more blocker gates failed for a claim scope. | Conditional | Resolve listed blockers and rerun. |
| `gate-profile.gate-timeout` | A gate exceeded its configured timeout. | Conditional | Optimize/fix hang and rerun the timed-out gate. |

## 6. Conformance

A gate evaluator is conformant only if it executes Section 3 commands exactly, applies Section 4 scope rules, and reports Section 5 failure semantics.
