# Persistence Ref Update Protocol v1

Status: Draft  
Version: 1.1.0  
Last updated: 2026-02-16  
Scope: Atomic ref movement, write ordering, and crash recovery for persistent workspace refs  
Depends on: `web-ui/spec/persistence-purpose-and-user-contract-v1.md`, `web-ui/spec/persistence-envelope-schema-v1.json`
Compatibility: `v1.x` preserves normative requirements and failure semantics; incompatible changes require `v2`.

## 1. Purpose

This protocol defines normative state transitions for moving persistence refs without half-state exposure.

The protocol <a id="REQ-PERSISTENCE-REF-UPDATE-PROTOCOL-V1-8F36519EBF"></a>MUST guarantee:

1. Ref moves are atomic.
2. Refs never point to incomplete commit closures.
3. Multi-file edits become one snapshot root before ref advancement.
4. Crash recovery resolves each ref to one complete commit state.

## 2. Terminology

1. `object_id`: content address of an immutable object.
2. `snapshot_id`: `object_id` of a snapshot object.
3. `commit_id`: `object_id` of a commit object.
4. `ref`: mutable pointer to `commit_id`.
5. `refgen`: monotonically increasing generation value used for CAS.
6. `protected ref`: a ref namespace that <a id="REQ-PERSISTENCE-REF-UPDATE-PROTOCOL-V1-7C3FCF6AE8"></a>MUST enforce lease + semantic guard checks before advancement.

Protected refs <a id="REQ-PERSISTENCE-REF-UPDATE-PROTOCOL-V1-C50F0718D6"></a>MUST include `workspace/main` and MAY include additional policy-mapped namespaces.

## 3. Persistent Records

### 3.1 Immutable Snapshot

Required fields:

1. `root_tree_id`
2. `created_at`
3. `author_session_id`
4. `metadata` (optional, bounded)

### 3.2 Immutable Commit

Required fields:

1. `snapshot_id`
2. `parents[]`
3. `created_at`
4. `author_session_id`

Optional fields:

1. `message`
2. `ref_intent` (informational only)
3. `finalized` (boolean, defaults `true`)
4. `candidate_of` (`{local_commit_id, incoming_commit_id, base_commit_id}`; required when `finalized=false`)

Rule:

1. Commits with `finalized=false` <a id="REQ-PERSISTENCE-REF-UPDATE-PROTOCOL-V1-299BD14077"></a>MUST NOT be treated as runnable history for build/compile/export unless explicitly requested.

### 3.3 Mutable Ref Record

Required fields:

1. `ref_name`
2. `current_commit_id`
3. `refgen`
4. `updated_at`

Optional fields:

1. `previous_commit_id`
2. `last_writer_token`

## 4. Write Ordering (Hard Invariant)

Refs <a id="REQ-PERSISTENCE-REF-UPDATE-PROTOCOL-V1-5B50A0D77C"></a>MUST NOT be updated until all referenced immutable objects are durably committed.

For IndexedDB:

1. Object writes <a id="REQ-PERSISTENCE-REF-UPDATE-PROTOCOL-V1-D05BC334E4"></a>MUST commit first in object-store transaction(s).
2. Ref updates <a id="REQ-PERSISTENCE-REF-UPDATE-PROTOCOL-V1-7CF1DEE72F"></a>MUST commit after object durability in metadata transaction(s).
3. Object writes and ref updates SHOULD NOT share one transaction boundary.

## 5. Single-Ref CAS Advance

Operation:

`advance_ref(ref_name, expected_refgen, new_commit_id, writer_token?, semantic_guard?)`

### 5.1 Semantic Guard

`semantic_guard` is REQUIRED for protected refs and OPTIONAL for unprotected refs.

Supported guard clauses:

1. `requires_current_commit_id`
2. `requires_base_commit_id`
3. `requires_no_unresolved_conflicts`
4. `requires_lease_epoch`
5. `requires_finalized`
6. `requires_profile_id`

If present, all guard clauses <a id="REQ-PERSISTENCE-REF-UPDATE-PROTOCOL-V1-29A802C441"></a>MUST pass before the CAS write step.

For protected refs, `semantic_guard` <a id="REQ-PERSISTENCE-REF-UPDATE-PROTOCOL-V1-2A8202EF7C"></a>MUST include:

1. `requires_current_commit_id`
2. `requires_no_unresolved_conflicts=true`
3. `requires_lease_epoch`
4. `requires_finalized=true`

For protected ref merge finalization writes, `requires_base_commit_id` <a id="REQ-PERSISTENCE-REF-UPDATE-PROTOCOL-V1-5E8604DB24"></a>MUST also be present.

The request/record shape for guarded ref advances <a id="REQ-PERSISTENCE-REF-UPDATE-PROTOCOL-V1-2EFD38EBC7"></a>MUST conform to `web-ui/spec/persistence-envelope-schema-v1.json` (`ref_advance_request` envelope).

Required steps:

1. Validate `new_commit_id` exists and is readable.
2. Begin metadata transaction.
3. Read current ref record.
4. If target ref is protected and `semantic_guard` is missing, reject with `ERR_SEMANTIC_GUARD_REQUIRED`.
5. If target ref is protected and required guard clauses are absent/invalid, reject with `ERR_SEMANTIC_GUARD_REQUIRED`.
6. Evaluate `semantic_guard` predicates against current metadata/runtime state.
7. Reject with `ERR_REFGEN_MISMATCH` if `refgen != expected_refgen`.
8. Write updated ref:
   `previous_commit_id := current_commit_id`
   `current_commit_id := new_commit_id`
   `refgen := refgen + 1`
   `updated_at := now`
   `last_writer_token := writer_token`
9. Commit metadata transaction.

Crash safety:

1. Crash before commit leaves ref unchanged.
2. Crash after commit leaves ref pointing to complete commit closure.

## 6. Multi-Ref Atomic Advance

If one user operation <a id="REQ-PERSISTENCE-REF-UPDATE-PROTOCOL-V1-4D77F0009A"></a>MUST move multiple refs together, implementations <a id="REQ-PERSISTENCE-REF-UPDATE-PROTOCOL-V1-42A40C26B7"></a>MUST use a single atomic metadata transaction for all moves.

Optional audit/journal:

1. Immutable `RefTxn` object MAY record intended moves.
2. Mutable `reftxn/<txn_id>` marker MAY track `prepared | committed | aborted`.

### 6.1 Required Behavior

1. Validate all destination commits before applying any move.
2. All CAS checks for the set <a id="REQ-PERSISTENCE-REF-UPDATE-PROTOCOL-V1-09088BF293"></a>MUST pass before any ref update is committed.
3. If any check fails, no ref move in the set may commit.
4. Recovery scanner for incomplete/`prepared` txn markers SHOULD run at startup.

### 6.2 Recovery Scanner

For each `prepared` txn marker:

1. If all refs already match intended values, mark committed.
2. If no refs changed, mark aborted or preserve as unresolved for UI.
3. If divergence is detected, do not guess; emit explicit recovery diagnostics.

## 7. Save Operations

### 7.1 Authoritative User Save

Required sequence:

1. Load current workspace snapshot.
2. Apply path/file edits to produce new tree closure.
3. Write changed blobs/trees.
4. Write new snapshot.
5. Write new commit with parent(s).
6. CAS advance `workspace/main`.

### 7.2 Autosave

Autosave <a id="REQ-PERSISTENCE-REF-UPDATE-PROTOCOL-V1-07E440E10F"></a>MUST:

1. Follow same object/snapshot/commit ordering.
2. Advance `autosave/latest` only.
3. Never advance `workspace/main`.
4. Remain non-destructive to user-save history.
5. Enforce reader-stable boundary policy before snapshot commit.

Reader-stable boundary policy:

1. Autosave <a id="REQ-PERSISTENCE-REF-UPDATE-PROTOCOL-V1-9C83A8B093"></a>MUST NOT create a semantically different program by truncation unless `prefix_autosave_enabled` is explicitly active.
2. If current buffer/projection state is unreadable under active reader policy, autosave SHOULD skip that document and emit a marker.
3. If `prefix_autosave_enabled` policy is active, autosave MAY persist readable prefix only.
4. Prefix autosave payloads <a id="REQ-PERSISTENCE-REF-UPDATE-PROTOCOL-V1-6ED6E1A46E"></a>MUST include explicit boundary metadata and `autosave_prefix=true`.
5. Prefix autosave results <a id="REQ-PERSISTENCE-REF-UPDATE-PROTOCOL-V1-0C5323DFF1"></a>MUST NOT be treated as authoritative user-save equivalent.

## 8. Error Codes

Implementations <a id="REQ-PERSISTENCE-REF-UPDATE-PROTOCOL-V1-D8EABD0D3B"></a>MUST expose stable error categories:

1. `ERR_REFGEN_MISMATCH`
2. `ERR_COMMIT_MISSING`
3. `ERR_COMMIT_UNREADABLE`
4. `ERR_SEMANTIC_GUARD_REQUIRED`
5. `ERR_SEMANTIC_GUARD_FAILED`
6. `ERR_UNRESOLVED_CONFLICTS`
7. `ERR_FINALIZATION_REQUIRED`
8. `ERR_LEASE_REQUIRED`
9. `ERR_REF_TXN_ABORTED`
10. `ERR_METADATA_TXN_FAILED`
11. `ERR_OBJECT_TXN_FAILED`

## 9. Observability

Ref updates <a id="REQ-PERSISTENCE-REF-UPDATE-PROTOCOL-V1-1BC7043815"></a>MUST emit structured events including:

1. `ref_name`
2. `from_commit_id`
3. `to_commit_id`
4. `expected_refgen`
5. `result_refgen`
6. `writer_token` (if available)
7. `semantic_guard` (if provided)
8. `result` (`ok` or error code)

## 10. Conformance

An implementation is conformant only if:

1. Write ordering invariant in section 4 always holds.
2. CAS and semantic guard semantics are strictly enforced.
3. Multi-ref operations are atomic at metadata transaction boundary.
4. Crash simulation never yields half-advanced refs.
5. Autosave never mutates `workspace/main`.
6. Reader-stability autosave policy is deterministic and auditable.
7. Protected refs cannot be advanced without required semantic guard clauses and lease-linked validation.
