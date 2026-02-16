# Persistence Lease Protocol v1

Status: Draft  
Version: 1.1.0  
Last updated: 2026-02-16  
Scope: Writer coordination and lease-gated ref updates for workspace persistence  
Depends on: `web-ui/spec/persistence-ref-update-protocol-v1.md`, `web-ui/spec/persistence-purpose-and-user-contract-v1.md`, `web-ui/spec/persistence-envelope-schema-v1.json`

## 1. Purpose

This protocol defines deterministic single-writer coordination for protected refs.

The protocol MUST:

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

## 3. Timing Parameters

Implementations MUST publish concrete values:

1. `LEASE_TTL_MS`
2. `HEARTBEAT_MS`
3. `SUSPEND_GRACE_MS`

Values SHOULD satisfy:

1. `HEARTBEAT_MS < LEASE_TTL_MS`
2. `SUSPEND_GRACE_MS >= LEASE_TTL_MS`

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
2. Losers MUST observe mismatch and downgrade to non-writer mode.

## 5. Renew Lease

Operation:

`renew_lease(workspace_id, writer_token, epoch)`

Required steps:

1. Begin metadata transaction.
2. Read lease.
3. Reject with `ERR_LEASE_LOST` if token or epoch mismatches.
4. Update `last_heartbeat_at` and `expires_at := now + LEASE_TTL_MS`.
5. Commit.

On renew failure, caller MUST immediately drop write capability.

## 6. Release Lease

Explicit release is optional but recommended.

If supported:

1. `release_lease` MUST verify token/epoch before clearing or replacing.
2. Releasing stale ownership MUST fail with `ERR_LEASE_LOST`.

## 7. Write Gating

Every protected ref move MUST verify:

1. Lease exists for target protected namespace.
2. `writer_token` matches.
3. `epoch` matches.
4. Lease is unexpired under active policy.
5. Protected-ref semantic guard is present and valid per `web-ui/spec/persistence-envelope-schema-v1.json` (`ref_advance_request` with `protected_ref=true`).
6. Guard includes `requires_lease_epoch` matching the lease epoch used for write authorization.

Failure MUST reject write with `ERR_LEASE_REQUIRED`, `ERR_LEASE_LOST`, or `ERR_SEMANTIC_GUARD_REQUIRED`.

## 8. Secondary Tab/Client Behavior

Default behavior for non-lease-holder instances:

1. Read-only `workspace/main`.
2. May fork `session/<id>` ref and write there if policy allows.
3. May request/takeover via explicit UI/policy pathway.

## 9. Error Codes

Implementations MUST expose:

1. `ERR_LEASE_HELD`
2. `ERR_LEASE_LOST`
3. `ERR_LEASE_REQUIRED`
4. `ERR_TAKEOVER_NOT_ALLOWED`
5. `ERR_LEASE_TXN_FAILED`
6. `ERR_SEMANTIC_GUARD_REQUIRED`

## 10. Observability

Lease operations MUST emit structured diagnostics:

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
