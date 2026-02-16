# Persistence Corruption Recovery v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-16  
Scope: Detection, containment, and recovery policy for persistence corruption and incomplete state  
Depends on: `web-ui/spec/persistence-purpose-and-user-contract-v1.md`, `web-ui/spec/persistence-ref-update-protocol-v1.md`, `web-ui/spec/persistence-lease-protocol-v1.md`, `web-ui/spec/persistence-sync-and-conflict-protocol-v1.md`, `web-ui/spec/persistence-storage-backend-matrix-v1.md`, `web-ui/spec/persistence-envelope-schema-v1.json`, `web-ui/spec/persistence-migration-policy-v1.md`

## 1. Purpose

This policy defines how the system detects corruption and recovers without violating data-safety guarantees.

The recovery system MUST guarantee:

1. No silent data destruction.
2. No ref advancement onto unreadable or unverified commit closures.
3. Deterministic handling for each corruption class.
4. Clear degraded-mode behavior when automatic repair cannot complete.

## 2. Recovery Principles

All recovery actions MUST follow:

1. Preserve authored data first.
2. Prefer repair by content-address verification and fetch by hash.
3. Quarantine ambiguous/corrupt artifacts instead of guessing.
4. Keep ref semantics explicit and auditable.
5. Require explicit operator/user action when deterministic recovery is unavailable.

## 3. Corruption Taxonomy

Corruption classes:

1. `missing-object`: referenced object id not present locally.
2. `hash-mismatch`: stored bytes do not hash to declared object id.
3. `envelope-invalid`: object or mutable record fails envelope/schema validation.
4. `closure-incomplete`: commit exists but transitive closure is incomplete.
5. `ref-dangling`: ref points to missing/unreadable commit.
6. `metadata-divergence`: metadata state contradicts atomicity invariants.
7. `chunk-manifest-invalid`: chunk list is missing chunks, misordered, or byte totals mismatch.
8. `lease-anomaly`: lease record violates monotonic epoch/token rules.
9. `sync-state-corrupt`: sync markers/reference metadata malformed or contradictory.
10. `unknown-corruption`: any unclassified persistent-state anomaly.

## 4. Detection Points

Detection MUST run at:

1. Startup integrity scan.
2. Pre-ref-advance validation.
3. Sync ingest validation.
4. Object read path (on-demand).
5. Optional background scrubber.

Detection MUST use deterministic checks:

1. hash verification
2. envelope/schema validation
3. closure reachability checks
4. ref-target readability checks
5. transaction marker invariants (`reftxn`/migration state)

## 5. Startup Integrity Scan

On startup, system MUST execute:

1. Enumerate protected refs and critical operational refs.
2. For each ref head, verify commit readability and minimal closure (`commit`, `snapshot`, immediate roots/doc map).
3. Validate mutable records used for coordination (`refs`, `leases`, migration markers, unresolved conflicts).
4. Reconcile incomplete prepared transaction markers deterministically.
5. Produce workspace health status and diagnostics.

Workspace health status values:

1. `healthy`
2. `degraded-repairing`
3. `degraded-readonly`
4. `degraded-export-only`

If startup scan cannot establish safe write semantics, workspace MUST enter `degraded-readonly` or stricter.

## 6. Runtime Integrity Checks

Before any protected ref move, implementation MUST confirm:

1. destination commit is readable and closure-complete for required scope,
2. destination commit envelope validates,
3. destination commit meets `finalized` policy,
4. no unresolved conflicts block policy,
5. lease/guard state remains valid.

On any runtime integrity failure, write MUST fail with stable error code and no partial mutation.

## 7. Recovery Actions by Corruption Class

### 7.1 Missing Object or Incomplete Closure

Required actions:

1. Attempt fetch by object id from configured remotes.
2. Re-verify hashes and envelope validity after fetch.
3. If closure becomes complete, continue operation.
4. If not recoverable, keep ref unchanged and mark workspace degraded.

### 7.2 Hash Mismatch

Required actions:

1. Quarantine local object bytes immediately.
2. Attempt remote refetch by object id.
3. If refetch verifies, replace quarantined object and continue.
4. If refetch unavailable or fails verification, fail operation and keep degraded status.

### 7.3 Envelope Invalid

Required actions:

1. Reject object/record as unreadable.
2. Attempt deterministic migration/normalization only if policy explicitly allows and source bytes are otherwise intact.
3. If normalization is not defined, quarantine and fail affected operation.

### 7.4 Dangling Ref

Required actions:

1. Attempt recovery from `previous_commit_id` when available and readable.
2. If previous is valid, offer explicit repair action to repoint ref.
3. If both current and previous are unreadable, do not guess; move to `degraded-export-only` and require operator action.

### 7.5 Metadata Divergence

Required actions:

1. Freeze protected writes.
2. Run deterministic reconciliation for known markers (`reftxn`, migration states).
3. If reconciliation cannot prove correctness, require operator intervention.

### 7.6 Lease Anomaly

Required actions:

1. Reject protected writes with lease errors.
2. Force explicit reacquire with epoch increment.
3. Log anomaly as potential split-brain risk.

## 8. Quarantine Policy

Quarantine store MUST preserve suspect bytes and metadata for forensics.

Required fields for each quarantine record:

1. `quarantine_id`
2. `workspace_id`
3. `object_or_record_key`
4. `detected_at`
5. `corruption_class`
6. `original_hash` (if known)
7. `detector`
8. `linked_operation_id`

Quarantine retention MUST outlive immediate recovery attempts and support incident analysis.

## 9. Degraded Mode Policy

Allowed degraded modes:

1. `degraded-repairing`: reads allowed, writes gated by recovery subsystem.
2. `degraded-readonly`: writes blocked; inspection and export allowed.
3. `degraded-export-only`: interactive edits blocked; explicit export/recovery workflows only.

Mode transitions MUST be explicit, logged, and user-visible.

The system MUST NOT claim durability when operating in an ephemeral fallback backend during degraded recovery.

## 10. User-Facing Contract During Recovery

User-facing requirements:

1. Explain current health mode and what operations are blocked.
2. Provide explicit recover/inspect/export actions.
3. Never silently rewrite user files to mask corruption.
4. Preserve clear ownership of any repair action that changes refs.

If save is blocked due to integrity risk, UI MUST provide non-destructive export path.

## 11. Remote-Assisted Repair Rules

When remote is available, repair-by-hash SHOULD be primary.

Rules:

1. Only accept fetched objects that hash-validate and schema-validate.
2. Never trust remote ref movement as proof of local integrity.
3. Do not auto-advance protected refs during repair unless guarded policy explicitly allows and all preconditions pass.

## 12. Recovery Interaction with Migration and GC

Recovery and migration MUST interlock safely:

1. Migration MUST pause when corruption status is unresolved.
2. GC MUST not reclaim suspect or pre-repair objects needed for rollback/forensics.
3. Recovery actions that create new commits/refs MUST comply with protected-ref guards.

## 13. Error Codes

Implementations MUST expose stable corruption/recovery errors:

1. `ERR_CORRUPTION_MISSING_OBJECT`
2. `ERR_CORRUPTION_HASH_MISMATCH`
3. `ERR_CORRUPTION_ENVELOPE_INVALID`
4. `ERR_CORRUPTION_CLOSURE_INCOMPLETE`
5. `ERR_CORRUPTION_DANGLING_REF`
6. `ERR_CORRUPTION_METADATA_DIVERGENCE`
7. `ERR_CORRUPTION_CHUNK_MANIFEST_INVALID`
8. `ERR_CORRUPTION_LEASE_ANOMALY`
9. `ERR_RECOVERY_REMOTE_UNAVAILABLE`
10. `ERR_RECOVERY_FETCH_FAILED`
11. `ERR_RECOVERY_REPAIR_UNSAFE`
12. `ERR_RECOVERY_MANUAL_ACTION_REQUIRED`
13. `ERR_RECOVERY_DEGRADED_MODE_ACTIVE`

## 14. Observability and Incident Artifacts

Recovery telemetry MUST include:

1. `incident_id`
2. `workspace_id`
3. `corruption_class`
4. `detector`
5. `affected_refs`
6. `affected_object_ids`
7. `repair_action`
8. `result`
9. `mode_transition`
10. `duration_ms`
11. `error_code`

Each incident MUST produce a compact incident record suitable for operator review and automated alerting.

## 15. Conformance Tests

An implementation is conformant only if it passes all:

1. Missing-object startup recovery with successful remote fetch.
2. Missing-object startup recovery without remote fetch (enters degraded mode deterministically).
3. Hash-mismatch quarantine and refetch path.
4. Envelope-invalid object rejection path.
5. Dangling-ref recovery to previous commit when valid.
6. Metadata-divergence freeze-write path.
7. Lease-anomaly split-brain prevention path.
8. Crash during recovery action with no half-applied ref state.
9. User-save blocked under unsafe state still provides export path.

## 16. Operational Guidance

Recommended operator playbook order:

1. Confirm corruption class from diagnostics.
2. Attempt deterministic automatic repair path.
3. If repair fails, keep workspace read-only and export immediately.
4. Execute explicit ref repair/rollback if and only if preconditions are provable.
5. Close incident only after follow-up integrity scan reports `healthy`.
