# Persistence Migration Policy v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-16  
Scope: Deterministic migration policy for persistence schemas, profiles, and backend transitions  
Depends on: `web-ui/spec/persistence-purpose-and-user-contract-v1.md`, `web-ui/spec/persistence-semantic-profile-v1.md`, `web-ui/spec/persistence-ref-update-protocol-v1.md`, `web-ui/spec/persistence-sync-and-conflict-protocol-v1.md`, `web-ui/spec/persistence-storage-backend-matrix-v1.md`, `web-ui/spec/persistence-envelope-schema-v1.json`

## 1. Purpose

This policy defines how persistence data is migrated without violating durability, determinism, or user trust guarantees.

The migration system MUST guarantee:

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

Migration MUST preserve all of the following:

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

Each migration execution MUST declare one migration class and MAY include additional linked classes when coupled transitions are unavoidable.

## 5. Migration Record

Each migration operation MUST persist a mutable migration record:

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

Migration records MUST be retained until at least one successful post-migration health window completes.

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

Any transition not listed above MUST be rejected with `ERR_MIGRATION_STATE_INVALID`.

## 7. Preflight Validation

Before entering `prepared`, the implementation MUST perform all checks:

1. Acquire lease for all target protected ref namespaces.
2. Verify no unresolved conflict records exist for protected refs to be cut over.
3. Verify current protected ref heads match expected `pre_migration_ref_state`.
4. Validate profile compatibility against local runtime capabilities and sync compatibility policy.
5. Validate that source objects referenced by target refs are readable and hash-valid.
6. Estimate closure size and quota headroom.
7. Validate that destination schema/profile/backend is supported by the running build.

If any check fails, migration MUST end in `aborted` or `failed` with explicit error code.

## 8. Migration Execution Modes

### 8.1 Lazy Upgrade Mode

Lazy mode MAY be used when migration is backward compatible at read time.

Rules:

1. Source objects remain canonical until rewritten by normal save flow.
2. Reads apply deterministic in-memory normalization only.
3. Writes emit objects in target schema/profile.
4. Protected refs are not bulk-cutover in lazy mode.

### 8.2 Eager Rewrite Mode

Eager mode MUST be used when backward-compatible reads are impossible or unsafe.

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

If any step fails before step 9, refs MUST remain unchanged.

## 9. Cutover Rules

Cutover (protected ref advancement) MUST satisfy:

1. `requires_current_commit_id` equals pre-migration ref head commit.
2. `requires_no_unresolved_conflicts=true`.
3. `requires_lease_epoch` equals active lease epoch.
4. `requires_finalized=true` for destination commits.
5. `requires_base_commit_id` for merge-finalization related cutovers.

Cutover of multiple protected refs for one migration MUST use one metadata transaction when platform supports it.

## 10. Rollback Policy

Rollback is a first-class migration operation.

Rules:

1. Rollback MUST use pinned `pre_migration_ref_state` from migration record.
2. Rollback MUST use guarded CAS semantics identical to forward cutover.
3. Rollback MUST NOT delete migrated objects immediately.
4. Rollback result MUST be recorded as `rolled_back` or `failed`.

The system MUST NOT auto-rollback without an auditable policy trigger.

## 11. Mixed-Version and Mixed-Profile Behavior

Rules for interoperability:

1. Sync handshake MUST exchange profile id and minimum readable schema versions.
2. If remote compatibility cannot be guaranteed, protected refs MUST NOT auto-advance.
3. Mixed-profile collaboration MUST use explicit compatibility mode or fail fast with a stable error.
4. Migration MUST NOT conceal incompatible semantic-canonical payloads behind file-primacy labels.

## 12. Quota, Retention, and GC

Migration MUST integrate with quota/GC controls:

1. Pre-migration closures MUST be pinned until migration health window completes.
2. Post-migration GC MUST keep both pre- and post-cutover closures until rollback window expires.
3. On quota pressure during migration, system MUST stop autosave first, then evict derived data, then pause migration before risking authored data.
4. Migration MUST never reclaim data required for deterministic rollback within retention window.

## 13. Failure Semantics and Error Codes

Implementations MUST expose stable migration errors:

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

Each error MUST define caller action as one of:

1. retry safe
2. retry after operator action
3. manual recovery required
4. abort required

## 14. Observability and Audit

Migration events MUST include:

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

Migration event streams MUST support reconstruction of exact state transitions for post-incident analysis.

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

Stop conditions MUST include:

1. repeated `ERR_MIGRATION_REF_CAS_FAILED`
2. repeated `ERR_MIGRATION_SOURCE_OBJECT_CORRUPT`
3. rollback failure rate above policy threshold
4. unresolved degraded mode after migration
