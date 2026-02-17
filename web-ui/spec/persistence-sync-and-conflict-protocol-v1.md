# Persistence Sync and Conflict Protocol v1

Status: Draft  
Version: 1.1.0  
Last updated: 2026-02-16  
Scope: Local-first sync, divergence representation, and conflict resolution workflow  
Depends on: `web-ui/spec/persistence-ref-update-protocol-v1.md`, `web-ui/spec/persistence-lease-protocol-v1.md`, `web-ui/spec/persistence-purpose-and-user-contract-v1.md`, `web-ui/spec/persistence-envelope-schema-v1.json`
Compatibility: `v1.x` preserves normative requirements and failure semantics; incompatible changes require `v2`.

## 1. Purpose

This protocol defines deterministic sync behavior that preserves local-first semantics and user trust.

The protocol <a id="REQ-PERSISTENCE-SYNC-AND-CONFLICT-PROTOCOL-V1-C694C0A253"></a>MUST guarantee:

1. Local editing and saves never block on network availability.
2. Sync transfers objects and refs; it does not rewrite authored files in place.
3. Divergence is represented by refs, not conflict filenames.
4. Remote object integrity is verified by content address before adoption.
5. Protected refs are advanced only through guarded ref-CAS semantics.

## 2. Remote Capability Model

Required remote primitives:

1. `has_object(object_id) -> bool`
2. `put_object(object_id, bytes)` (idempotent)
3. `get_object(object_id) -> bytes`
4. `get_ref(ref_name) -> {commit_id, refgen}`
5. `cas_ref(ref_name, expected_refgen, new_commit_id)`

Optional:

1. Lease operations for cross-device writer coordination.

## 3. Local Sync Metadata

Implementations SHOULD persist:

1. `sync/remote/<remote_id>/last_seen_refgen/<ref_name>`
2. `sync/remote/<remote_id>/last_pulled_commit/<ref_name>`
3. `sync/remote/<remote_id>/last_pushed_commit/<ref_name>`

## 4. Push Protocol

Operation:

`push(remote_id, ref_name)`

Required steps:

1. Read local `ref_name`.
2. Compute required object closure for destination commit.
3. Upload missing remote objects.
4. Read remote ref state.
5. If remote ref is ancestor of local commit, CAS advance remote ref.
6. If equal, no-op.
7. If divergence, do not force update; create explicit divergence record/ref.
8. Persist local sync status.

## 5. Pull Protocol

Operation:

`pull(remote_id, ref_name)`

Required steps:

1. Read remote ref state.
2. Fetch and verify missing object closure by hash.
3. Compare remote commit with local `ref_name`.
4. If local is ancestor:
   for unprotected refs, fast-forward local ref;
   for protected refs, fast-forward only via `advance_ref` with required protected-ref semantic guard and policy gate.
5. If equal, no-op.
6. If divergence, create `incoming/<remote_id>/<ref_name>/<timestamp>` ref.
7. Do not auto-advance `workspace/main` on divergence.
8. Persist sync status.

Protected-ref fast-forward guard requirements:

1. Guard shape <a id="REQ-PERSISTENCE-SYNC-AND-CONFLICT-PROTOCOL-V1-E26FD77433"></a>MUST conform to `web-ui/spec/persistence-envelope-schema-v1.json` (`ref_advance_request` with `protected_ref=true`).
2. Guard <a id="REQ-PERSISTENCE-SYNC-AND-CONFLICT-PROTOCOL-V1-48747B36D9"></a>MUST include `requires_current_commit_id`, `requires_no_unresolved_conflicts=true`, `requires_lease_epoch`, and `requires_finalized=true`.
3. Fast-forward <a id="REQ-PERSISTENCE-SYNC-AND-CONFLICT-PROTOCOL-V1-ED48F9EF47"></a>MUST be blocked if commit is `finalized=false` or local conflict state is unresolved.

## 6. Verification Rules

Every received object <a id="REQ-PERSISTENCE-SYNC-AND-CONFLICT-PROTOCOL-V1-618AB47347"></a>MUST pass:

1. Hash check (`hash(bytes) == object_id`).
2. Type envelope validation.
3. Schema/version parse sanity checks.

Failure <a id="REQ-PERSISTENCE-SYNC-AND-CONFLICT-PROTOCOL-V1-80DA116895"></a>MUST reject object and preserve existing local ref state.

## 7. Background Sync Policy

Background sync MAY:

1. Upload/download immutable objects.
2. Sync autosave/session refs per policy.

Background sync <a id="REQ-PERSISTENCE-SYNC-AND-CONFLICT-PROTOCOL-V1-B70549144B"></a>MUST NOT:

1. Advance `workspace/main` unless explicit fast-forward-only policy allows it.
2. Advance to commits flagged non-finalized by policy.
3. Resolve divergence silently.
4. Fast-forward `workspace/main` onto commits with unresolved `ConflictRecord` state.
5. Advance protected refs without protected-ref semantic guard validation.

## 8. Conflict Representation

Conflict exists when local and incoming commits are not ancestor-related.

Required representation:

1. Local authoritative ref (`workspace/main`).
2. Incoming candidate ref(s), for example `incoming/<remote>/<ref>/<id>`.
3. Derived `ConflictRecord` with:
   `conflict_id`,
   `base_commit_id` (required for semantic merge),
   `local_commit_id`,
   `incoming_commit_id`,
   `created_at`,
   `status`,
   `resolution_commit_id` (when resolved),
   `doc_conflicts[]`.

### 8.1 Conflict Taxonomy

Each `doc_conflicts[]` entry SHOULD include typed `form_conflicts[]` (or file-hunk equivalents when semantic context is unavailable).

Supported conflict types:

1. `same-form-edited`
2. `delete-vs-edit`
3. `insert-collision`
4. `rename-identity`
5. `macro-dependent`
6. `projection-only`

Each conflict entry SHOULD include:

1. `form_id` or equivalent stable target id (if known),
2. `local_change_ref`,
3. `incoming_change_ref`,
4. `auto_resolvable`,
5. `auto_resolution_reason`.

## 9. Conflict Resolution Workflow

Supported user actions SHOULD include:

1. Inspect incoming snapshot read-only.
2. Fast-forward if safe.
3. Resolve conflict explicitly.

Hard gate:

1. `workspace/main` <a id="REQ-PERSISTENCE-SYNC-AND-CONFLICT-PROTOCOL-V1-76E3DF9FFA"></a>MUST NOT advance directly from divergence detection.
2. Resolution <a id="REQ-PERSISTENCE-SYNC-AND-CONFLICT-PROTOCOL-V1-4CB332CD82"></a>MUST proceed through explicit merge-candidate workflow or explicit user-selected non-merge action.
3. Background workers <a id="REQ-PERSISTENCE-SYNC-AND-CONFLICT-PROTOCOL-V1-9903009124"></a>MUST NOT bypass this gate.

Manual-merge baseline:

1. Create merge-candidate snapshot/commit/ref with:
   `intent=merge`, `finalized=false`, `candidate_of={base_commit_id, local_commit_id, incoming_commit_id}`.
2. Resolve in normal file editor workflow.
3. Produce explicit merge commit.
4. CAS advance `workspace/main` only on explicit finish.

### 9.1 Merge Base Requirement

For semantic conflict workflows:

1. `base_commit_id` <a id="REQ-PERSISTENCE-SYNC-AND-CONFLICT-PROTOCOL-V1-65CD958850"></a>MUST be computed before structural or semantic merge.
2. If base cannot be established, system <a id="REQ-PERSISTENCE-SYNC-AND-CONFLICT-PROTOCOL-V1-14D8F61270"></a>MUST fall back to explicit non-semantic resolution paths.

### 9.2 MergeRecord

When merge is accepted, implementations SHOULD write immutable `MergeRecord`:

1. `base_commit_id`
2. `local_commit_id`
3. `incoming_commit_id`
4. `doc_resolutions[]`
5. `form_resolutions[]` with outcome classes:
   `kept_local | kept_incoming | merged_structurally | manual_edit`
6. `tool_version`
7. `created_at`

Accepted merge commit SHOULD reference `merge_record_id`.

## 10. Safe Auto-Merge Policy (Optional)

If enabled, auto-merge <a id="REQ-PERSISTENCE-SYNC-AND-CONFLICT-PROTOCOL-V1-CC1790EF78"></a>MUST remain narrow:

1. Disjoint file edits only, or
2. Pure additive changes with no overlapping mutations.

Auto-merge <a id="REQ-PERSISTENCE-SYNC-AND-CONFLICT-PROTOCOL-V1-9DE63A0822"></a>MUST stage result in merge-candidate ref first.
Auto-merge <a id="REQ-PERSISTENCE-SYNC-AND-CONFLICT-PROTOCOL-V1-8D14700015"></a>MUST require explicit user acceptance before `workspace/main` advancement.
Auto-merge <a id="REQ-PERSISTENCE-SYNC-AND-CONFLICT-PROTOCOL-V1-16D68025AD"></a>MUST NOT silently rewrite `workspace/main`.

## 11. Error Codes

Implementations <a id="REQ-PERSISTENCE-SYNC-AND-CONFLICT-PROTOCOL-V1-EA45DE537F"></a>MUST expose:

1. `ERR_SYNC_NETWORK`
2. `ERR_SYNC_OBJECT_MISSING`
3. `ERR_SYNC_OBJECT_HASH_MISMATCH`
4. `ERR_SYNC_REF_CAS_MISMATCH`
5. `ERR_SYNC_DIVERGENCE`
6. `ERR_SYNC_POLICY_BLOCKED`
7. `ERR_CONFLICT_UNRESOLVED`
8. `ERR_MERGE_BASE_UNAVAILABLE`
9. `ERR_MERGE_ACCEPTANCE_REQUIRED`
10. `ERR_SYNC_PROTECTED_REF_GUARD_REQUIRED`

## 12. Observability

Sync events <a id="REQ-PERSISTENCE-SYNC-AND-CONFLICT-PROTOCOL-V1-B29C3BD50C"></a>MUST include:

1. `remote_id`
2. `ref_name`
3. `direction` (`push` or `pull`)
4. `source_commit_id`
5. `target_commit_id`
6. `result` (`ok`, `no-op`, `diverged`, `failed`)
7. `error_code` (when failed)
8. `conflict_id` (when divergence/resolution paths apply)
9. `merge_candidate_ref` (when created)

## 13. Conformance

An implementation is conformant only if:

1. Local save path is independent from network state.
2. Push/pull preserve hash integrity validation.
3. Divergence creates explicit incoming/conflict state.
4. No silent `workspace/main` mutation occurs under divergence.
5. Merge-candidate-first gate is enforced for divergence resolution.
6. Conflict completion requires deterministic rule or explicit user action.
7. Accepted merge decisions are auditable through `MergeRecord` or equivalent metadata.
