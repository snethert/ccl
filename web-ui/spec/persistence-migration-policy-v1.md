# Persistence Migration Policy v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-16  
Scope: Deterministic migration policy for persistence schemas, profiles, and backend transitions  
Depends on: `web-ui/spec/persistence-purpose-and-user-contract-v1.md`, `web-ui/spec/persistence-semantic-profile-v1.md`, `web-ui/spec/persistence-ref-update-protocol-v1.md`, `web-ui/spec/persistence-sync-and-conflict-protocol-v1.md`, `web-ui/spec/persistence-storage-backend-matrix-v1.md`, `web-ui/spec/persistence-envelope-schema-v1.json`

## 1. Purpose

This policy defines how persistence data is migrated without violating durability, determinism, or user trust guarantees.

The migration system <a id="REQ-PERSISTENCE-MIGRATION-POLICY-V1-0CCE6BB38C"></a>MUST guarantee:

1. No protected ref points to a partial or unreadable commit closure.
2. No silent profile/schema transition occurs.
3. Migration is crash-safe, resumable, and auditable.
4. Rollback is explicit, deterministic, and non-destructive.

## 2. Non-Goals

This policy does not define:

1. A requirement to mutate immutable objects in place.
2. Best-effort heuristics that guess intended state after ambiguous corruption.
3. Automatic cross-profile merge of incompatible semantic models.
4. Remote-side implementation internals beyond wire-visible compatibility behavior.

## 3. Hard Invariants

Migration <a id="REQ-PERSISTENCE-MIGRATION-POLICY-V1-603BA5854D"></a>MUST preserve all of the following:

1. Immutable objects are never rewritten in place.
2. Protected refs are advanced only by guarded CAS (`requires_current_commit_id`, `requires_no_unresolved_conflicts=true`, `requires_lease_epoch`, `requires_finalized=true`).
3. Object closure durability is achieved before any ref cutover.
4. Crash at any point yields one of two states: pre-cutover refs unchanged, or post-cutover refs fully committed.
5. Any migration side effect is attributable to a migration record with stable id.
6. Migration cannot silently replace `file-primacy-v1` with `semantic-canonical-v1`.

## 4. Migration Dimensions

Supported migration classes:

1. Envelope migration: format changes covered by `persistence-envelope-schema-v1.json` versioning.
2. Object schema migration: payload-level schema version changes (for `commit`, `snapshot`, `doc`, `form_graph`, `form_node`, metadata records).
3. Profile migration: `file-primacy-v1` <-> `semantic-canonical-v1` transitions.
4. Backend migration: storage lane changes (`indexeddb`, `opfs+idb`, `memory-snapshot`, integration lanes).
5. Policy migration: reader/profile policy identifiers that affect canonical encoding or semantic behavior.

Each migration execution <a id="REQ-PERSISTENCE-MIGRATION-POLICY-V1-81D1B2793F"></a>MUST declare one migration class and MAY include additional linked classes when coupled transitions are unavoidable.

## 5. Migration Record

Each migration operation <a id="REQ-PERSISTENCE-MIGRATION-POLICY-V1-12DC6401FC"></a>MUST persist a mutable migration record:

Key:

`migration/<workspace_id>/<migration_id>`

Required fields:

1. `migration_id`
2. `workspace_id`
3. `migration_class`
4. `from_version` and `to_version` (or profile/backend ids)
5. `state`
6. `created_at`
7. `updated_at`
8. `initiator_session_id`
9. `pre_migration_ref_state` (map `ref_name -> {commit_id, refgen}`)
10. `target_refs`
11. `plan_hash`
12. `result` (`committed | aborted | failed | rolled_back`)

Optional fields:

1. `estimated_object_count`
2. `estimated_bytes`
3. `rewritten_object_count`
4. `rewritten_bytes`
5. `cutover_commit_map` (`old_commit_id -> new_commit_id`)
6. `error_code`
7. `error_detail`
8. `rollback_of_migration_id`

Migration records <a id="REQ-PERSISTENCE-MIGRATION-POLICY-V1-F716AD92FC"></a>MUST be retained until at least one successful post-migration health window completes.

## 6. Migration State Machine

Allowed states:

1. `planned`
2. `validating`
3. `prepared`
4. `rewriting`
5. `cutover_ready`
6. `committed`
7. `aborted`
8. `failed`
9. `rolling_back`
10. `rolled_back`

Allowed transitions:

1. `planned -> validating`
2. `validating -> prepared | aborted | failed`
3. `prepared -> rewriting | aborted | failed`
4. `rewriting -> cutover_ready | failed`
5. `cutover_ready -> committed | failed`
6. `failed -> rolling_back | aborted`
7. `rolling_back -> rolled_back | failed`

Any transition not listed above <a id="REQ-PERSISTENCE-MIGRATION-POLICY-V1-56B4207AB2"></a>MUST be rejected with `ERR_MIGRATION_STATE_INVALID`.

## 7. Preflight Validation

Before entering `prepared`, the implementation <a id="REQ-PERSISTENCE-MIGRATION-POLICY-V1-9FB2161555"></a>MUST perform all checks:

1. Acquire lease for all target protected ref namespaces.
2. Verify no unresolved conflict records exist for protected refs to be cut over.
3. Verify current protected ref heads match expected `pre_migration_ref_state`.
4. Validate profile compatibility against local runtime capabilities and sync compatibility policy.
5. Validate that source objects referenced by target refs are readable and hash-valid.
6. Estimate closure size and quota headroom.
7. Validate that destination schema/profile/backend is supported by the running build.

If any check fails, migration <a id="REQ-PERSISTENCE-MIGRATION-POLICY-V1-69366AF1E1"></a>MUST end in `aborted` or `failed` with explicit error code.

## 8. Migration Execution Modes

### 8.1 Lazy Upgrade Mode

Lazy mode MAY be used when migration is backward compatible at read time.

Rules:

1. Source objects remain canonical until rewritten by normal save flow.
2. Reads apply deterministic in-memory normalization only.
3. Writes emit objects in target schema/profile.
4. Protected refs are not bulk-cutover in lazy mode.

### 8.2 Eager Rewrite Mode

Eager mode <a id="REQ-PERSISTENCE-MIGRATION-POLICY-V1-B838CC8CBA"></a>MUST be used when backward-compatible reads are impossible or unsafe.

Required algorithm:

1. Enter `prepared` with pinned `pre_migration_ref_state`.
2. Enumerate full reachable closure from targeted ref heads.
3. Deterministically transform each object payload to target schema/profile.
4. Validate transformed envelopes against `persistence-envelope-schema-v1.json`.
5. Compute and verify target object ids from canonical encoding.
6. Persist transformed objects durably.
7. Build migrated head commits/snapshots as needed.
8. Enter `cutover_ready` only when full target closure is durable.
9. Advance protected refs via guarded CAS with mandatory protected-ref guard clauses.
10. Mark migration `committed` only after all target ref moves succeed.

If any step fails before step 9, refs <a id="REQ-PERSISTENCE-MIGRATION-POLICY-V1-B9028EEB64"></a>MUST remain unchanged.

## 9. Cutover Rules

Cutover (protected ref advancement) <a id="REQ-PERSISTENCE-MIGRATION-POLICY-V1-A8FB607DEA"></a>MUST satisfy:

1. `requires_current_commit_id` equals pre-migration ref head commit.
2. `requires_no_unresolved_conflicts=true`.
3. `requires_lease_epoch` equals active lease epoch.
4. `requires_finalized=true` for destination commits.
5. `requires_base_commit_id` for merge-finalization related cutovers.

Cutover of multiple protected refs for one migration <a id="REQ-PERSISTENCE-MIGRATION-POLICY-V1-63123342F0"></a>MUST use one metadata transaction when platform supports it.

## 10. Rollback Policy

Rollback is a first-class migration operation.

Rules:

1. Rollback <a id="REQ-PERSISTENCE-MIGRATION-POLICY-V1-102A153492"></a>MUST use pinned `pre_migration_ref_state` from migration record.
2. Rollback <a id="REQ-PERSISTENCE-MIGRATION-POLICY-V1-5AE1822BE4"></a>MUST use guarded CAS semantics identical to forward cutover.
3. Rollback <a id="REQ-PERSISTENCE-MIGRATION-POLICY-V1-C3610C38B0"></a>MUST NOT delete migrated objects immediately.
4. Rollback result <a id="REQ-PERSISTENCE-MIGRATION-POLICY-V1-4A5741F966"></a>MUST be recorded as `rolled_back` or `failed`.

The system <a id="REQ-PERSISTENCE-MIGRATION-POLICY-V1-8E5B3CAF44"></a>MUST NOT auto-rollback without an auditable policy trigger.

## 11. Mixed-Version and Mixed-Profile Behavior

Rules for interoperability:

1. Sync handshake <a id="REQ-PERSISTENCE-MIGRATION-POLICY-V1-846CC02DD9"></a>MUST exchange profile id and minimum readable schema versions.
2. If remote compatibility cannot be guaranteed, protected refs <a id="REQ-PERSISTENCE-MIGRATION-POLICY-V1-7C70BD6488"></a>MUST NOT auto-advance.
3. Mixed-profile collaboration <a id="REQ-PERSISTENCE-MIGRATION-POLICY-V1-D373F60D67"></a>MUST use explicit compatibility mode or fail fast with a stable error.
4. Migration <a id="REQ-PERSISTENCE-MIGRATION-POLICY-V1-503D8EE301"></a>MUST NOT conceal incompatible semantic-canonical payloads behind file-primacy labels.

## 12. Quota, Retention, and GC

Migration <a id="REQ-PERSISTENCE-MIGRATION-POLICY-V1-5AF7754D1E"></a>MUST integrate with quota/GC controls:

1. Pre-migration closures <a id="REQ-PERSISTENCE-MIGRATION-POLICY-V1-DCFB360CEE"></a>MUST be pinned until migration health window completes.
2. Post-migration GC <a id="REQ-PERSISTENCE-MIGRATION-POLICY-V1-BC248D3365"></a>MUST keep both pre- and post-cutover closures until rollback window expires.
3. On quota pressure during migration, system <a id="REQ-PERSISTENCE-MIGRATION-POLICY-V1-92B02EC59A"></a>MUST stop autosave first, then evict derived data, then pause migration before risking authored data.
4. Migration <a id="REQ-PERSISTENCE-MIGRATION-POLICY-V1-EB34A5F831"></a>MUST never reclaim data required for deterministic rollback within retention window.

## 13. Failure Semantics and Error Codes

Implementations <a id="REQ-PERSISTENCE-MIGRATION-POLICY-V1-87D9E0DC71"></a>MUST expose stable migration errors:

1. `ERR_MIGRATION_UNSUPPORTED`
2. `ERR_MIGRATION_STATE_INVALID`
3. `ERR_MIGRATION_PRECHECK_FAILED`
4. `ERR_MIGRATION_PROFILE_INCOMPATIBLE`
5. `ERR_MIGRATION_SOURCE_OBJECT_MISSING`
6. `ERR_MIGRATION_SOURCE_OBJECT_CORRUPT`
7. `ERR_MIGRATION_TARGET_ENCODING_INVALID`
8. `ERR_MIGRATION_QUOTA_EXCEEDED`
9. `ERR_MIGRATION_LEASE_REQUIRED`
10. `ERR_MIGRATION_CONFLICT_UNRESOLVED`
11. `ERR_MIGRATION_REF_CAS_FAILED`
12. `ERR_MIGRATION_ROLLBACK_REQUIRED`
13. `ERR_MIGRATION_ROLLBACK_FAILED`

Each error <a id="REQ-PERSISTENCE-MIGRATION-POLICY-V1-B632FEC1CF"></a>MUST define caller action as one of:

1. retry safe
2. retry after operator action
3. manual recovery required
4. abort required

## 14. Observability and Audit

Migration events <a id="REQ-PERSISTENCE-MIGRATION-POLICY-V1-6E9D52FE36"></a>MUST include:

1. `migration_id`
2. `workspace_id`
3. `migration_class`
4. `state_from`
5. `state_to`
6. `plan_hash`
7. `target_refs`
8. `rewritten_object_count`
9. `rewritten_bytes`
10. `duration_ms`
11. `result`
12. `error_code` (if any)

Migration event streams <a id="REQ-PERSISTENCE-MIGRATION-POLICY-V1-E9833AA94F"></a>MUST support reconstruction of exact state transitions for post-incident analysis.

## 15. Conformance Tests

An implementation is conformant only if it passes at minimum:

1. Determinism replay test: identical source closure and policy produce byte-identical target object ids.
2. Crash fault-injection tests at each state boundary (`prepared`, `rewriting`, `cutover_ready`, cutover transaction).
3. Lease race test during cutover.
4. Protected-ref guard omission test (must fail).
5. Rollback correctness test (restores pinned pre-migration ref heads exactly).
6. Mixed-profile handshake rejection test for incompatible lanes.
7. Quota-pressure migration pause test preserving authored data invariants.

## 16. Operational Rollout Guidance

Recommended rollout sequence:

1. Shadow-mode planning and dry-run only.
2. Canary eager rewrite on non-critical workspaces.
3. Incremental rollout with automatic stop conditions on migration failure threshold.
4. Default enablement after conformance and incident-drill signoff.

Stop conditions <a id="REQ-PERSISTENCE-MIGRATION-POLICY-V1-748F5859D2"></a>MUST include:

1. repeated `ERR_MIGRATION_REF_CAS_FAILED`
2. repeated `ERR_MIGRATION_SOURCE_OBJECT_CORRUPT`
3. rollback failure rate above policy threshold
4. unresolved degraded mode after migration
