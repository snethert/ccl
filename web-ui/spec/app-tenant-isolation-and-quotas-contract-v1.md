# App Tenant Isolation and Quotas Contract v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-17  
Scope: Normative app/tenant resource isolation, quota enforcement, and circuit-breaker behavior for multi-app `web-ui` deployments  
Depends on: `web-ui/spec/normative-language-and-conformance-v1.md`, `web-ui/spec/security-and-capability-model-v1.md`, `web-ui/spec/observability-contract-v1.md`, `web-ui/spec/bridge-qos-and-lane-contract-v1.md`, `web-ui/spec/persistence-purpose-and-user-contract-v1.md`  
Compatibility: `v1.x` preserves tenant identifiers, quota dimensions, and enforcement semantics; incompatible tenant model changes require `v2`.

## 1. Purpose

This contract defines how multiple apps/extensions share one runtime without unbounded interference.
It is normative for per-tenant budgets, enforcement states, and emergency controls.

## 2. Tenant Identity Model

Required fields:

1. `tenant_id` (stable runtime/session identity)
2. `tenant_class` (`trusted`, `workspace`, `extension`, `untrusted`)
3. `tenant_policy_id` (resolved quota/capability policy)

Identity rules:

1. Every command, input lane binding, and persistence write <a id="REQ-APP-TENANT-ISOLATION-AND-QUOTAS-CONTRACT-V1-0EAAD95D26"></a>MUST resolve to one `tenant_id`.
2. Missing tenant identity <a id="REQ-APP-TENANT-ISOLATION-AND-QUOTAS-CONTRACT-V1-53FE4D40AD"></a>MUST fail closed for mutating operations.
3. Tenant identity changes during a session <a id="REQ-APP-TENANT-ISOLATION-AND-QUOTAS-CONTRACT-V1-429281B18E"></a>MUST be auditable and explicit.

## 3. Quota Dimensions

Each tenant policy <a id="REQ-APP-TENANT-ISOLATION-AND-QUOTAS-CONTRACT-V1-433E1065A6"></a>MUST define at least:

1. `cpu_budget_ms_per_window`
2. `queue_max_bytes`
3. `queue_max_events`
4. `runtime_command_inflight_max`
5. `persistence_write_rate_max`
6. `asset_stream_rate_max` (if asset lane enabled)

Quota defaults MAY differ by `tenant_class`.

## 4. Enforcement States

Tenant enforcement states:

1. `normal`
2. `throttled`
3. `paused`
4. `killed`

State machine rules:

1. Quota violations SHOULD move tenant from `normal` to `throttled`.
2. Sustained or repeated critical violations <a id="REQ-APP-TENANT-ISOLATION-AND-QUOTAS-CONTRACT-V1-740D6304A2"></a>MUST allow transition to `paused` or `killed`.
3. `killed` tenants <a id="REQ-APP-TENANT-ISOLATION-AND-QUOTAS-CONTRACT-V1-4DD5DDF1E2"></a>MUST NOT submit new commands or enqueue new events until explicit recovery action.
4. State transitions <a id="REQ-APP-TENANT-ISOLATION-AND-QUOTAS-CONTRACT-V1-66F57E719A"></a>MUST emit auditable telemetry with policy and actor provenance.

## 5. Capability Scope and Kill Controls

Capability requirements:

1. Grant/revoke decisions <a id="REQ-APP-TENANT-ISOLATION-AND-QUOTAS-CONTRACT-V1-764CB3F93D"></a>MUST be tenant-scoped by default.
2. Global grants <a id="REQ-APP-TENANT-ISOLATION-AND-QUOTAS-CONTRACT-V1-DF1AB1416C"></a>MUST be explicit and auditable exceptions.
3. Emergency kill <a id="REQ-APP-TENANT-ISOLATION-AND-QUOTAS-CONTRACT-V1-69B64AE30A"></a>MUST isolate one tenant without requiring full-runtime restart.
4. Tenant recovery SHOULD preserve unaffected tenants and control-plane continuity.

## 6. Persistence and Asset Isolation

Isolation requirements:

1. Tenant write activity <a id="REQ-APP-TENANT-ISOLATION-AND-QUOTAS-CONTRACT-V1-5554011232"></a>MUST respect per-tenant persistence rate budget.
2. One tenant <a id="REQ-APP-TENANT-ISOLATION-AND-QUOTAS-CONTRACT-V1-D8FB1536F7"></a>MUST NOT block unrelated tenant read access during over-budget write throttling.
3. Asset/blob namespaces SHOULD include tenant partition keys for isolation and cleanup.

## 7. Observability Requirements

Required fields for tenant-enforced records:

1. `tenant_id`
2. `tenant_policy_id`
3. `quota_dimension`
4. `quota_limit`
5. `quota_observed`
6. `enforcement_state`
7. `enforcement_action`
8. `actor_id`

## 8. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `security-capability.tenant-missing` | Mutating operation lacked tenant identity binding. | No | Attach valid tenant identity and retry. |
| `security-capability.tenant-quota-exceeded` | Tenant exceeded enforced quota dimension. | Conditional | Back off workload or request policy change. |
| `security-capability.tenant-paused` | Tenant is paused by quota or policy controls. | Conditional | Await resume or resolve policy violation. |
| `security-capability.tenant-killed` | Tenant was terminated by enforcement policy. | No | Perform explicit tenant recovery flow. |

## 9. Conformance Fixtures and Pass Criteria

Minimum required evidence:

1. `web-ui/tests/tenant-quota-policy.test.mjs`
2. `web-ui/tests/capabilities.test.mjs`
3. `web-ui/tests/runtime-command-admission.test.mjs`

Pass criteria:

1. Per-tenant quotas are enforced deterministically.
2. One tenant cannot starve unrelated tenants on control lanes.
3. Kill/pause/resume transitions are auditable and reproducible.

## 10. Conformance

An implementation is conformant only if Sections 2-9 are satisfied.
