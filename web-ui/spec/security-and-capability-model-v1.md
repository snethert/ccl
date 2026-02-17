# Security and Capability Model v1

Status: Draft  
Version: 1.3.0  
Last updated: 2026-02-17  
Scope: Trust boundaries, strict startup gate, capability mediation, and safe-mode behavior for `web-ui` and runtime bridge surfaces  
Depends on: `web-ui/spec/normative-language-and-conformance-v1.md`, `web-ui/spec/runtime-bridge-envelope-v1.md`, `web-ui/spec/protocol-version-negotiation-v1.md`, `scripts/wasm/lib/startup-gate.mjs`, `scripts/wasm/lib/load-image.mjs`, `web-ui/src/state.mjs`, `web-ui/src/commands.mjs`  
Compatibility: `v1.x` preserves startup-gate check IDs, fail-code mappings, capability command IDs, and safe-mode blocking semantics; incompatible policy changes require `v2`.

## 1. Purpose

This contract defines the production security model for startup validation and command capability mediation.
It is normative for fail-closed startup, capability grants/revocation, safe-mode behavior, and auditability.

## 2. Security Objectives

Implementations <a id="REQ-SECURITY-AND-CAPABILITY-MODEL-V1-F132F3DB6D"></a>MUST enforce all objectives:

1. Fail closed at startup when required platform/runtime guarantees are not met.
2. Prevent privileged command execution without explicit capability grant.
3. Provide immediate global kill-switch behavior via safe mode.
4. Keep capability changes and startup outcomes auditable and deterministic.
5. Avoid silent fallback to weaker transport or privilege semantics.

## 3. Trust Boundaries

| Boundary | Untrusted inputs | Required controls |
|---|---|---|
| Browser/runtime environment -> startup sequence | Platform feature availability, isolation headers, worker capabilities | Startup gate checks `SRG-01..SRG-12` <a id="REQ-SECURITY-AND-CAPABILITY-MODEL-V1-0FB6A398FE"></a>MUST pass before startup continues. |
| Runtime bridge transport -> UI state | Runtime envelope payloads, event frames, command frames | Version/format validation and strict policy from bridge/protocol specs <a id="REQ-SECURITY-AND-CAPABILITY-MODEL-V1-030D362578"></a>MUST run before apply. |
| Command invocation -> state mutation | User/runtime command payloads | Capability check <a id="REQ-SECURITY-AND-CAPABILITY-MODEL-V1-BC814E705C"></a>MUST run before command execution for capability-gated commands. |
| Persistence/remote state -> runtime/editor | Corrupt or incompatible stored objects/records | Persistence corruption/recovery contracts <a id="REQ-SECURITY-AND-CAPABILITY-MODEL-V1-25C39DB79C"></a>MUST gate write enablement. |

## 4. Startup Gate Contract

`runStartupGate()` is the authoritative startup security precondition gate for replacement track `RPL-01`.

Applicability:

1. This startup gate applies only to `full-runtime-v1` deployment (shared-memory runtime with `SharedArrayBuffer`, worker atomics, and WASM threads).
2. Non-SAB/non-thread fallback startup modes are not supported by this contract.

Normative requirements:

1. `full-web-ui-v1` production claims <a id="REQ-SECURITY-AND-CAPABILITY-MODEL-V1-5C624A4C9C"></a>MUST use `full-runtime-v1`.
2. Deployments missing full-runtime prerequisites <a id="REQ-SECURITY-AND-CAPABILITY-MODEL-V1-D7208A3F6B"></a>MUST fail startup and <a id="REQ-SECURITY-AND-CAPABILITY-MODEL-V1-6DC9ED6E3E"></a>MUST NOT silently downgrade transport/capability behavior.
3. Startup mode metadata <a id="REQ-SECURITY-AND-CAPABILITY-MODEL-V1-019AEA6B2C"></a>MUST be recorded in startup diagnostics.
4. Gate mode <a id="REQ-SECURITY-AND-CAPABILITY-MODEL-V1-7C9A47EE32"></a>MUST be strict: `startup_gate_mode="strict"` and `allow_fallback=false`.
5. Check execution <a id="REQ-SECURITY-AND-CAPABILITY-MODEL-V1-1A3FCE4F38"></a>MUST stop at first failure.
6. `load-image.mjs` <a id="REQ-SECURITY-AND-CAPABILITY-MODEL-V1-189559492F"></a>MUST terminate startup on gate failure or malformed summary.

### 4.1 Required Check and Failure Mapping (`full-runtime-v1`)

| Check ID | Canonical failure code | Security condition |
|---|---|---|
| `SRG-01` | `RPL01-E001` | Cross-origin isolation required. |
| `SRG-02` | `RPL01-E002` | `SharedArrayBuffer` availability required. |
| `SRG-03` | `RPL01-E003` | Worker Atomics wait/notify path required. |
| `SRG-04` | `RPL01-E004` | WASM shared-memory/thread capability required. |
| `SRG-05` | `RPL01-E005` | Required worker topology READY handshake required. |
| `SRG-06` | `RPL01-E006` | OPFS directory access in worker required. |
| `SRG-07` | `RPL01-E007` | SyncAccessHandle probe parity required. |
| `SRG-08` | `RPL01-E008` | Hot-path transport must be shared-memory-first. |
| `SRG-09` | `RPL01-E009` | UI bridge hot-path classes must use shared transport. |
| `SRG-10` | `RPL01-E010` | Replacement persistence profile must match storage-v2-opfs. |
| `SRG-11` | `RPL01-E011` | Strict no-fallback startup policy required. |
| `SRG-12` | `RPL01-E012` | Runtime thread capability policy boundary required. |

### 4.2 Startup Diagnostics Records

`STARTUP_GATE_CHECK` records (`schema_version="startup_gate_check_result_v1"`) <a id="REQ-SECURITY-AND-CAPABILITY-MODEL-V1-6EF441591F"></a>MUST include:

1. `run_id`
2. `sequence`
3. `check_id`
4. `required`
5. `status` (`pass|fail`)
6. `fail_code` (`null` on pass)
7. `message`
8. `observed` object
9. `pass_criteria`
10. `contradiction_ids` array
11. `remediation` (`null` on pass)

`STARTUP_GATE_SUMMARY` (`schema_version="startup_gate_summary_v1"`) <a id="REQ-SECURITY-AND-CAPABILITY-MODEL-V1-AA2498D69C"></a>MUST include:

1. `run_id`
2. `replacement_track` (`RPL-01`)
3. `startup_profile` (`full-runtime-v1`)
4. `startup_gate_mode` (`strict`)
5. `allow_fallback` (`false`)
6. `check_order`
7. `checks_executed`
8. `status` (`pass|fail`)
9. `failure_check_id`
10. `failure_code`
11. `message`
12. `contradiction_ids`
13. `remediation`
14. `results_digest`

## 5. Capability State and Policy Model

### 5.1 Canonical Capability State

`state.capabilities` <a id="REQ-SECURITY-AND-CAPABILITY-MODEL-V1-9AAB0604B3"></a>MUST normalize to:

| Field | Type | Rules |
|---|---|---|
| `safeMode` | boolean | Defaults to `false`. |
| `granted` | string array | <a id="REQ-SECURITY-AND-CAPABILITY-MODEL-V1-DC801BAD53"></a>MUST be deduplicated and lexically sorted. |
| `log` | array | Append-only normalized entries with action metadata. |

Capability log entries <a id="REQ-SECURITY-AND-CAPABILITY-MODEL-V1-014C8DFCAC"></a>MUST normalize fields:

1. `id`
2. `action`
3. `capability`
4. `reason`
5. `taskId`
6. `windowId`
7. `commandId`

### 5.2 Request Lifecycle

`state.capabilityRequests` entries <a id="REQ-SECURITY-AND-CAPABILITY-MODEL-V1-4C4392E945"></a>MUST normalize fields:

1. `id`
2. `capability`
3. `reason`
4. `status` (`pending|granted|denied`)
5. `decisionReason`
6. `decidedBy`
7. `taskId`
8. `windowId`
9. `commandId`

`state.capabilityRequestSeq` <a id="REQ-SECURITY-AND-CAPABILITY-MODEL-V1-9D68F0FC89"></a>MUST be monotonic and <a id="REQ-SECURITY-AND-CAPABILITY-MODEL-V1-1CCE8F3008"></a>MUST allocate IDs as `capability-request-<N>`.

### 5.3 Policy Model

`state.capabilityPolicy` <a id="REQ-SECURITY-AND-CAPABILITY-MODEL-V1-6102BA4748"></a>MUST normalize to:

1. `defaultDecision` (`ask|grant|deny`, default `ask`)
2. `rules[]` (`id`, `capability`, `decision`, `reason`)

Rule evaluation <a id="REQ-SECURITY-AND-CAPABILITY-MODEL-V1-13FEE0C70E"></a>MUST be deterministic and first-match:

1. Match explicit capability.
2. Match wildcard `*`.
3. Fall back to `defaultDecision`.

## 6. Command Mediation Contract

Canonical command IDs for security mediation in `v1`:

1. `ui.capability.request`
2. `ui.capability.grant`
3. `ui.capability.revoke`
4. `ui.capability.open-panel`
5. `ui.capability.select`
6. `ui.capability.approve`
7. `ui.capability.deny`
8. `ui.capability.auto-run`
9. `ui.safe-mode.enable`
10. `ui.safe-mode.disable`
11. `ui.dom.escape`

For any command declaring required capability:

1. Safe mode <a id="REQ-SECURITY-AND-CAPABILITY-MODEL-V1-EF6EBD5856"></a>MUST block execution with reason `Safe mode`.
2. Missing grant <a id="REQ-SECURITY-AND-CAPABILITY-MODEL-V1-9EB5A8C57E"></a>MUST block execution with reason `Missing capability: <capability>`.
3. Granted capability in non-safe-mode MAY enable execution.

## 7. Safe Mode and Escape Hatch Rules

1. `setSafeMode(true)` <a id="REQ-SECURITY-AND-CAPABILITY-MODEL-V1-AAB38C8E61"></a>MUST disable all capability-based escapes immediately.
2. `hasCapability()` <a id="REQ-SECURITY-AND-CAPABILITY-MODEL-V1-C63A1CE3FB"></a>MUST return `false` whenever safe mode is enabled.
3. `ui.dom.escape` <a id="REQ-SECURITY-AND-CAPABILITY-MODEL-V1-253B4D916F"></a>MUST remain capability-gated (default capability `dom.escape`).
4. Disabling safe mode <a id="REQ-SECURITY-AND-CAPABILITY-MODEL-V1-557523F7C3"></a>MUST NOT silently auto-grant missing capabilities.

## 8. Determinism and Audit Requirements

1. Capability grant/revoke decisions <a id="REQ-SECURITY-AND-CAPABILITY-MODEL-V1-F4F7653A9E"></a>MUST be deterministic for identical state and policy inputs.
2. Capability log append order <a id="REQ-SECURITY-AND-CAPABILITY-MODEL-V1-D8F3F5F99A"></a>MUST match action order.
3. Auto-run policy <a id="REQ-SECURITY-AND-CAPABILITY-MODEL-V1-2980B029E7"></a>MUST process pending requests in stable list order.
4. Startup summary `results_digest` <a id="REQ-SECURITY-AND-CAPABILITY-MODEL-V1-2D0CF07FEE"></a>MUST match emitted check record set.

## 9. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `security-capability.startup-gate-failed` | One startup-gate check failed (`RPL01-E00x`). | No | Fix environment/policy and restart process. |
| `security-capability.startup-gate-summary-invalid` | Startup summary payload malformed/invalid. | No | Treat as hard failure and investigate startup diagnostics emission. |
| `security-capability.safe-mode-active` | Capability-gated command blocked by safe mode. | Conditional | Disable safe mode only with explicit operator/user action. |
| `security-capability.capability-missing` | Command blocked due to missing capability grant. | Conditional | Request and approve capability, then retry. |
| `security-capability.request-invalid` | Capability request missing required fields. | Conditional | Send valid request payload and retry. |
| `security-capability.request-already-decided` | Decision attempted for non-pending request. | No | Create new request if a new decision cycle is required. |
| `security-capability.policy-normalized` | Invalid policy input normalized to safe default `ask`. | Conditional | Correct policy definitions and rerun auto policy. |
| `security-capability.command-unknown` | Unknown command ID invoked in security flow. | No | Use registered command IDs only. |

## 10. Observability Requirements

Implementations <a id="REQ-SECURITY-AND-CAPABILITY-MODEL-V1-C6CF6670C6"></a>MUST expose enough data to reconstruct security decisions:

1. Startup gate records (`STARTUP_GATE_CHECK`, `STARTUP_GATE_SUMMARY`).
2. Capability request lifecycle state (`pending`, `granted`, `denied`).
3. Safe mode toggles in capability log.
4. Decision actor metadata (`decidedBy`, `commandId`, `taskId`, `windowId`) when available.

## 11. Conformance Fixtures and Pass Criteria

Minimum required evidence:

1. `scripts/wasm/tests/start-lisp-noninteractive-smoke.mjs`
2. `web-ui/tests/capabilities.test.mjs`
3. `web-ui/tests/commands.test.mjs`
4. `web-ui/tests/phase-6-integration.test.mjs`

Pass criteria:

1. Startup failures hard-stop process without fallback.
2. Capability request/grant/deny/safe-mode flows match Sections 5-7.
3. Capability-gated commands enforce exact block reasons for safe mode and missing capability.

## 12. Conformance

An implementation is conformant only if Sections 2-11 are satisfied.
