# Persistence Lease Protocol v1

Status: Draft  
Version: 1.2.0  
Last updated: 2026-02-17  
Scope: Writer coordination and lease-gated ref updates for workspace persistence  
Depends on: `web-ui/spec/persistence-ref-update-protocol-v1.md`, `web-ui/spec/persistence-purpose-and-user-contract-v1.md`, `web-ui/spec/persistence-envelope-schema-v1.json`

## 1. Purpose

This protocol defines deterministic single-writer coordination for protected refs.

The protocol <a id="REQ-PERSISTENCE-LEASE-PROTOCOL-V1-7F2FBD2C30"></a>MUST:

1. Prevent concurrent writers from advancing the same protected ref namespace.
2. Detect dead/suspended writers.
3. Support deterministic takeover under explicit policy.
4. Enforce write gates in storage semantics, not UI logic alone.

## 2. Lease Record

Mutable key:

`lease/workspace/<workspace_id>/main`

Required fields:

1. `lease_id`
2. `owner_instance_id`
3. `writer_token`
4. `epoch`
5. `expires_at`
6. `last_heartbeat_at`
7. `capabilities` (`write`, `ref_names` or prefix set)

## 3. Timing and Retry Constants (`v1` Frozen)

Implementations <a id="REQ-PERSISTENCE-LEASE-PROTOCOL-V1-0037B84F09"></a>MUST use these constants exactly:

1. `LEASE_TTL_MS = 15000`
2. `HEARTBEAT_MS = 5000`
3. `SUSPEND_GRACE_MS = 30000`
4. `CLOCK_SKEW_TOLERANCE_MS = 1000`

Validation rules:

1. Renewal validity window <a id="REQ-PERSISTENCE-LEASE-PROTOCOL-V1-C015A73B6F"></a>MUST treat lease-expired only when `now > expires_at + CLOCK_SKEW_TOLERANCE_MS`.
2. Takeover eligibility <a id="REQ-PERSISTENCE-LEASE-PROTOCOL-V1-1C86BC3DBC"></a>MUST require `now >= expires_at + SUSPEND_GRACE_MS + CLOCK_SKEW_TOLERANCE_MS` unless user-confirmed takeover is explicit.

Retry policy (frozen for `v1`):

1. Acquire retry delays <a id="REQ-PERSISTENCE-LEASE-PROTOCOL-V1-98F02A9B05"></a>MUST be `[250, 500, 1000, 2000, 4000, 4000]` ms.
2. Renew retry delays <a id="REQ-PERSISTENCE-LEASE-PROTOCOL-V1-10E9023706"></a>MUST be `[250, 500, 1000]` ms.
3. Retry jitter <a id="REQ-PERSISTENCE-LEASE-PROTOCOL-V1-5669C857B7"></a>MUST be deterministic per `workspace_id` and attempt index (stable hash mod `100ms`).
4. Exhausting renew retries <a id="REQ-PERSISTENCE-LEASE-PROTOCOL-V1-CD4311E77D"></a>MUST immediately transition to `ERR_LEASE_LOST`.

## 4. Acquire Lease

Operation:

`acquire_lease(workspace_id, mode)`

Modes:

1. `normal`
2. `takeover`

### 4.1 Normal Acquire

Required steps:

1. Begin metadata transaction.
2. Read existing lease.
3. If unexpired lease exists, reject with `ERR_LEASE_HELD`.
4. Else write new lease with fresh token and `epoch := prior_epoch + 1`.
5. Set `expires_at := now + LEASE_TTL_MS`.
6. Commit transaction.

### 4.2 Takeover Acquire

Allowed only when policy allows one:

1. `now >= expires_at + SUSPEND_GRACE_MS`, or
2. explicit user-confirmed takeover.

Tie-break rule:

1. Competing acquires resolve by metadata transaction commit order.
2. Losers <a id="REQ-PERSISTENCE-LEASE-PROTOCOL-V1-022C861162"></a>MUST observe mismatch and downgrade to non-writer mode.

## 5. Renew Lease

Operation:

`renew_lease(workspace_id, writer_token, epoch)`

Required steps:

1. Begin metadata transaction.
2. Read lease.
3. Reject with `ERR_LEASE_LOST` if token or epoch mismatches.
4. Update `last_heartbeat_at` and `expires_at := now + LEASE_TTL_MS`.
5. Commit.

On renew failure, caller <a id="REQ-PERSISTENCE-LEASE-PROTOCOL-V1-BD22259EF1"></a>MUST immediately drop write capability.

## 6. Release Lease

Explicit release is optional but recommended.

If supported:

1. `release_lease` <a id="REQ-PERSISTENCE-LEASE-PROTOCOL-V1-886F4B1A2B"></a>MUST verify token/epoch before clearing or replacing.
2. Releasing stale ownership <a id="REQ-PERSISTENCE-LEASE-PROTOCOL-V1-EDA044A9EB"></a>MUST fail with `ERR_LEASE_LOST`.

## 7. Write Gating

Every protected ref move <a id="REQ-PERSISTENCE-LEASE-PROTOCOL-V1-3F4EDC793A"></a>MUST verify:

1. Lease exists for target protected namespace.
2. `writer_token` matches.
3. `epoch` matches.
4. Lease is unexpired under active policy.
5. Protected-ref semantic guard is present and valid per `web-ui/spec/persistence-envelope-schema-v1.json` (`ref_advance_request` with `protected_ref=true`).
6. Guard includes `requires_lease_epoch` matching the lease epoch used for write authorization.

Failure <a id="REQ-PERSISTENCE-LEASE-PROTOCOL-V1-636C441479"></a>MUST reject write with `ERR_LEASE_REQUIRED`, `ERR_LEASE_LOST`, or `ERR_SEMANTIC_GUARD_REQUIRED`.

## 8. Secondary Tab/Client Behavior

Default behavior for non-lease-holder instances:

1. Read-only `workspace/main`.
2. May fork `session/<id>` ref and write there if policy allows.
3. May request/takeover via explicit UI/policy pathway.

## 9. Error Codes

Implementations <a id="REQ-PERSISTENCE-LEASE-PROTOCOL-V1-D2D9B04736"></a>MUST expose:

1. `ERR_LEASE_HELD`
2. `ERR_LEASE_LOST`
3. `ERR_LEASE_REQUIRED`
4. `ERR_TAKEOVER_NOT_ALLOWED`
5. `ERR_LEASE_TXN_FAILED`
6. `ERR_SEMANTIC_GUARD_REQUIRED`

## 10. Observability

Lease operations <a id="REQ-PERSISTENCE-LEASE-PROTOCOL-V1-6950C1C05F"></a>MUST emit structured diagnostics:

1. `workspace_id`
2. `owner_instance_id`
3. `writer_token` (redacted where required)
4. `epoch`
5. `mode`
6. `result` (`acquired`, `renewed`, `lost`, `rejected`)
7. `reason` (error code)

## 11. Conformance

An implementation is conformant only if:

1. Protected ref writes cannot bypass lease validation.
2. Competing writers cannot both hold valid write authority.
3. Renew loss always causes immediate write drop.
4. Takeover policy is deterministic and auditable.
