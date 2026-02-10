# RPL-05 - Storage V2 Local Core

Status: done  
Priority: P0  
Owner: Runtime/WASM replacement track  
Last Updated: 2026-02-10  
Parent Plan: `doc/wasm/runtime-replacement-master-plan.md`

## Scope

In scope:

- Define the Storage V2 local-core schema contract for immutable objects plus mutable refs/leases.
- Freeze deterministic local transaction boundaries, CAS rules, and crash-recovery semantics.
- Bind storage ownership and lifecycle behavior to frozen worker topology/lifecycle contracts (`WTOP-*`, `WSEQ-*`, `WLCT-*`).
- Define no-silent-fallback failure semantics for replacement-lane storage (legacy memory-snapshot is not a replacement fallback).

Out of scope:

- Remote synchronization and merge finalization workflow (RPL-06).
- Runtime/UI shared-path transport migration (RPL-04).
- Backend size/perf measurement execution (BPL-07).
- CL thread semantics implementation details (remain deferred).

## Dependencies

- RPL-00 governance loop and same-cycle sync discipline.
- RPL-01 startup/security profile and contradiction follow-through (`SRG-06`, `SRG-07`, `SRG-10`, `SRG-11`, `SRG-12`, `C-10`, `C-11`, `C-12`).
- RPL-02 worker ownership/lifecycle constraints (`WTOP-02`, `WTOP-04`, `WSEQ-02`, `WSEQ-06`, `WLCT-03`, `WLCT-09`).
- RPL-03 shared-memory channel/failure baseline for runtime<->storage requests (`IPCP-05`, `IPCP-06`, `IPCP-24`, `IPCP-31`, `IPCP-33`, `IPCP-37`).
- RPL-04 closed bridge baseline consumption contract (`R4M-*`, `R4C-*`, `R4T-*`, `R4L-*`, `R4V-*`, `R4I-*`) as additive-only input.
- Dependency matrix row `X-05` (parallel runtime/backend execution).

## Deliverables

1. Step 1 local-core schema and transaction-boundary contract with frozen IDs (`R5S-*`, `R5T-*`, `R5A-*`).
2. Step 2 local conformance lane and validation matrix consuming Step 1 contract.
3. Step 3 committed evidence bundle and synchronized `X-05` progress notes.

## Exit Criteria

- Immutable object, mutable ref, and lease schemas are fully defined with deterministic key/version rules.
- Transaction boundaries are explicit, atomic, crash-safe, and mapped to canonical failure codes.
- Replacement lane forbids silent fallback to legacy memory-snapshot storage behavior.
- Test-lane telemetry artifacts and assertion requirements are machine-actionable.

## Current Notes

- This subplan is newly authored; Step 1 contract is published in this document.
- Step 1 freezes local-core IDs as additive-only (`R5S-*`, `R5T-*`, `R5A-*`).
- Step 2 execution/gating contract is now published with frozen conformance lane and validation IDs (`R5L-*`, `R5V-*`).
- Step 3 run-v1 evidence is now committed at `doc/wasm/tickets/evidence/rpl-05-step3-2026-02-10/rpl05-20260210-004335Z-91fdb0be/` with full `R5V-01`..`R5V-14` command execution coverage.
- Step 3 run-v2 evidence is now committed at `doc/wasm/tickets/evidence/rpl-05-step3-2026-02-10/rpl05-20260210-011240Z-91fdb0be/` with full `R5V-01`..`R5V-14` command execution coverage.
- Run-v2 reports `storage_v2_local_step2_summary_v1.status=pass`, `x05_step2_ready=true`, and explicit closure of `R5GAP-01`..`R5GAP-05`.
- Step 1 consumes frozen runtime baseline IDs without renaming/reopening upstream contracts.
- Storage worker capability requirements remain explicit and secure-only (`SRG-06`, `SRG-07`, `SRG-10`, `SRG-11`).
- Runtime thread capability remains required now; CL thread semantics remain deferred.
- Pack A backend state is now closure-review carry-forward with committed remediation pass bundle (`bpl06-20260210-005408Z-91fdb0be`, `bpl07-20260210-005408Z-91fdb0be`) over frozen `BPL06-*` intake artifacts.

## Immediate Next Step

- Action: keep `R5S-*`/`R5T-*`/`R5A-*`/`R5L-*`/`R5V-*` namespaces frozen and consume closed RPL-05 evidence in downstream runtime planning (`X-05` closure + Pack A runtime focus transition).
- Why now: Step 3 closure criteria are now satisfied, so further progress should consume this baseline instead of mutating its contract.
- Success evidence: runtime master/matrix/board/governance docs mark `X-05` as `done`, reference run-v2 closure evidence, and point the next runtime Pack A action at downstream open gates.

## Step 1 Output - Storage V2 Local Core Schema and Transaction Contract (v1)

### ID Namespace Freeze (Normative)

| namespace | frozen range | meaning | mutation rule |
| --- | --- | --- | --- |
| `R5S-*` | `R5S-01`..`R5S-32` | Local data schema, keyspace, and versioning rules. | Additive-only; existing IDs are immutable. |
| `R5T-*` | `R5T-01`..`R5T-30` | Transaction boundaries, failure semantics, ownership, and rollback/remediation clauses. | Additive-only; existing IDs are immutable. |
| `R5A-*` | `R5A-01`..`R5A-12` | Telemetry schema contracts and required test-lane assertions. | Additive-only; existing IDs are immutable. |

### Local Data Record Inventory

| schema_id | record | key format | required fields | deterministic invariants | owner role |
| --- | --- | --- | --- | --- | --- |
| R5S-01 | `object_manifest_v1` | `obj/<object_id>` | `object_id`, `content_hash`, `byte_length`, `chunk_count`, `chunk_size`, `created_at_ms`, `writer_txn_id` | `object_id` and `content_hash` are immutable after commit. | `WTOP-04` |
| R5S-02 | `object_chunk_v1` | `obj/<object_id>/chunk/<index>` | `object_id`, `chunk_index`, `chunk_hash`, `chunk_bytes`, `writer_txn_id` | `chunk_index` is contiguous from `0..chunk_count-1`; hash must match bytes. | `WTOP-04` |
| R5S-03 | `ref_record_v1` | `ref/<namespace>/<ref_name>` | `namespace`, `ref_name`, `target_object_id`, `version_u64`, `updated_at_ms`, `updated_by` | `version_u64` increments exactly `+1` on successful CAS update. | `WTOP-04` |
| R5S-04 | `lease_record_v1` | `lease/<namespace>/<ref_name>/<holder_id>` | `namespace`, `ref_name`, `holder_id`, `lease_token`, `lease_epoch`, `expires_at_ms`, `state` | At most one `state=active` lease per `(namespace, ref_name)`. | `WTOP-04` |
| R5S-05 | `txn_intent_v1` | `txn/<txn_id>/intent` | `txn_id`, `op_type`, `started_at_ms`, `actor_role`, `write_set_digest`, `preconditions` | Every mutating txn writes intent before any data mutation. | `WTOP-04` |
| R5S-06 | `txn_commit_v1` | `txn/<txn_id>/commit` | `txn_id`, `committed_at_ms`, `result`, `applied_keys`, `result_digest` | Commit record is append-only and written once per txn. | `WTOP-04` |
| R5S-07 | `gc_tombstone_v1` | `gc/tombstone/<object_id>` | `object_id`, `replaced_by`, `tombstoned_at_ms`, `reason_code` | Tombstone creation requires prior successful ref transition off object. | `WTOP-04` |
| R5S-08 | `namespace_root_v1` | `namespace/<namespace>/root` | `namespace`, `root_ref`, `root_version`, `updated_at_ms` | Root pointer transitions must use the same CAS rules as `ref_record_v1`. | `WTOP-04` |
| R5S-09 | `local_clock_anchor_v1` | `meta/clock` | `last_monotonic_ms`, `last_wall_ms`, `updated_at_ms` | Clock anchor must be monotonic for tx ordering fields. | `WTOP-04` |
| R5S-10 | `storage_profile_guard_v1` | `meta/profile` | `replacement_lane`, `persistence_backend`, `legacy_memory_snapshot_default`, `allow_fallback` | Must match `replacement_lane=true`, `persistence_backend=storage-v2-opfs`, `allow_fallback=false`. | `WTOP-04` |

### Keyspace and Versioning Rules

| schema_id | keyspace clause | required rule | prohibited behavior |
| --- | --- | --- | --- |
| R5S-11 | object identity | `object_id` is lowercase hex SHA-256 digest over canonical object bytes. | Re-keying committed object IDs. |
| R5S-12 | object chunking | `chunk_size` is fixed per object manifest and immutable after commit. | Mixed chunk-size values within one object. |
| R5S-13 | ref namespace | `namespace` and `ref_name` are normalized UTF-8 and case-sensitive. | Case-folded alias lookups in replacement lane. |
| R5S-14 | ref versioning | `version_u64` starts at `1` and increments by one on successful CAS only. | Non-CAS overwrite of ref target/version. |
| R5S-15 | lease epoching | `lease_epoch` increments per holder refresh and invalidates prior tokens. | Reusing stale `lease_token` after epoch advance. |
| R5S-16 | txn identity | `txn_id` is unique per process epoch and includes lane prefix `rpl05-local-`. | Reusing committed `txn_id`. |
| R5S-17 | profile guard | `storage_profile_guard_v1` must be loaded and validated before local writes. | Starting replacement lane with legacy memory-snapshot profile. |
| R5S-18 | legacy key exclusion | Keys with legacy prefix `snapshot/` are read-only diagnostic artifacts in replacement lane. | Writing new mutable state under `snapshot/` keyspace. |
| R5S-19 | metadata digests | `write_set_digest` and `result_digest` are SHA-256 over sorted key/value tuple bytes. | Non-deterministic digest input ordering. |
| R5S-20 | timestamp fields | `*_at_ms` fields must be monotonic per local clock anchor (`R5S-09`). | Backward timestamp movement within one process epoch. |

### Transaction Boundary Contract

| txn_id | operation | preconditions | atomic write set | commit success condition | canonical failures |
| --- | --- | --- | --- | --- | --- |
| R5T-01 | `PUT_OBJECT` | Object ID absent; all chunk hashes verify before intent commit. | `R5S-05` intent, `R5S-01` manifest, `R5S-02` chunks, `R5S-06` commit | Manifest + all chunks + commit record are present with matching digest. | `RPL05-E001`, `RPL05-E002`, `RPL05-E006` |
| R5T-02 | `PUT_OBJECT_IDEMPOTENT` | Existing object ID allowed only if manifest/chunks are byte-identical. | `R5S-05` intent, optional `R5S-06` commit | Existing object digest matches requested payload exactly. | `RPL05-E001`, `RPL05-E002` |
| R5T-03 | `REF_CAS_SET` | Expected `ref_version` and optional expected target match current record. | `R5S-05` intent, `R5S-03` ref update, `R5S-06` commit | Ref version increments once and target points to committed object ID. | `RPL05-E003`, `RPL05-E006` |
| R5T-04 | `REF_CAS_DELETE` | Ref exists and expected `ref_version` matches. | `R5S-05` intent, tombstone marker, `R5S-06` commit | Ref marked deleted with monotonic version increment. | `RPL05-E003`, `RPL05-E006` |
| R5T-05 | `LEASE_ACQUIRE` | No active conflicting lease for `(namespace, ref_name)`. | `R5S-05` intent, `R5S-04` lease create, `R5S-06` commit | One active lease exists for holder and token/epoch are recorded. | `RPL05-E004`, `RPL05-E005`, `RPL05-E006` |
| R5T-06 | `LEASE_RENEW` | Active lease exists for holder with matching token and unexpired epoch. | `R5S-05` intent, `R5S-04` lease update, `R5S-06` commit | `expires_at_ms` extends forward and `lease_epoch` increments. | `RPL05-E004`, `RPL05-E005`, `RPL05-E006` |
| R5T-07 | `LEASE_RELEASE` | Active lease exists for holder/token pair. | `R5S-05` intent, `R5S-04` lease state transition, `R5S-06` commit | Lease transitions to `released` and is excluded from active-lock checks. | `RPL05-E004`, `RPL05-E006` |
| R5T-08 | `NAMESPACE_ROOT_SET` | Expected root version matches current namespace root. | `R5S-05` intent, `R5S-08` root update, `R5S-06` commit | Root pointer + version advance atomically with commit digest. | `RPL05-E003`, `RPL05-E006` |
| R5T-09 | `BATCH_REF_UPDATE` | Every row precondition validates before first mutable write. | Single txn intent, N ref records, optional lease updates, one commit | All row updates commit or none commit (all-or-abort). | `RPL05-E003`, `RPL05-E006`, `RPL05-E010` |
| R5T-10 | `GC_MARK_TOMBSTONE` | Object not targeted by any live ref/lease view at evaluation point. | `R5S-05` intent, `R5S-07` tombstone, `R5S-06` commit | Tombstone exists with deterministic `replaced_by`/`reason_code`. | `RPL05-E003`, `RPL05-E006` |
| R5T-11 | `RECOVERY_REPLAY` | Journal scan starts from last fully committed txn boundary. | replayed intents/commits only; no synthetic writes outside replay rules | Replay reaches fixed point with no dangling intent without commit decision. | `RPL05-E006`, `RPL05-E009` |
| R5T-12 | `PROFILE_GUARD_CHECK` | `R5S-10` loaded and validated before any mutating operation. | none (read-only gate) | All replacement-lane profile fields match expected values. | `RPL05-E007`, `RPL05-E008` |

### Canonical Failure Codes (Normative)

| failure_code | condition | message template | mandatory remediation |
| --- | --- | --- | --- |
| RPL05-E001 | schema/field validation failure | `[{code}] local schema violation for {record_type} at {key}.` | Reject txn, emit validation artifact, fix schema producer. |
| RPL05-E002 | object hash/chunk integrity mismatch | `[{code}] object integrity mismatch for {object_id} at chunk {chunk_index}.` | Abort txn; do not commit manifest/chunks. |
| RPL05-E003 | CAS precondition mismatch | `[{code}] CAS mismatch for {record_key}: expected={expected} observed={observed}.` | Abort txn; caller must reread and retry with explicit intent. |
| RPL05-E004 | lease ownership/token mismatch | `[{code}] lease ownership mismatch for {namespace}/{ref_name}.` | Abort lease mutation; require holder/token reconciliation. |
| RPL05-E005 | lease expired or invalid epoch | `[{code}] lease expired for {namespace}/{ref_name} at epoch {lease_epoch}.` | Reject operation; acquire fresh lease before retry. |
| RPL05-E006 | journal intent/commit inconsistency | `[{code}] journal consistency violation for txn {txn_id}.` | Enter recovery path; block new writes until consistency restored. |
| RPL05-E007 | forbidden legacy fallback detected | `[{code}] replacement lane attempted legacy fallback path ({path}).` | Hard fail operation; preserve `allow_fallback=false`. |
| RPL05-E008 | lifecycle/startup gate violation | `[{code}] storage lifecycle gate violated at {checkpoint_id}.` | Abort startup/runtime lane per `WLCT-*` escalation contract. |
| RPL05-E009 | durability/flush failure | `[{code}] durability commit failed at stage {stage} for txn {txn_id}.` | Mark lane fail; require recovery replay before accepting writes. |
| RPL05-E010 | unknown/unsupported transaction opcode | `[{code}] unsupported txn opcode {op_type}.` | Reject request deterministically; no implicit compatibility mode. |

### No-Silent-Fallback and Lifecycle Semantics

| semantics_id | scope | required behavior | prohibited behavior | escalation binding |
| --- | --- | --- | --- | --- |
| R5T-13 | replacement lane profile | Enforce `R5S-10` guard before any local mutating operation. | Continuing with legacy memory-snapshot profile. | `RPL05-E007` -> `WLCT-10` |
| R5T-14 | local writes | Every mutating op must write intent then commit (`R5S-05` then `R5S-06`). | Direct mutation without journal envelope. | `RPL05-E006` -> `WLCT-09` |
| R5T-15 | lease-protected ref mutation | `REF_CAS_SET/DELETE` with lease policy enabled requires valid active lease. | Lease bypass on protected refs. | `RPL05-E004` / `RPL05-E005` |
| R5T-16 | durability failure | Flush/commit failure blocks new writes until recovery completes. | Accepting new writes after unresolved durability error. | `RPL05-E009` |
| R5T-17 | gate ordering | Storage local-core write path starts only after `WSEQ-02` and `WSEQ-06` readiness checkpoints. | Early writes before storage role readiness. | `RPL05-E008` -> `WLCT-03` |
| R5T-18 | unsupported opcodes | Reject unknown opcodes deterministically. | Dynamic fallback to legacy opcode handlers. | `RPL05-E010` |
| R5T-19 | object immutability | Committed object payloads are immutable and addressable only by content hash. | In-place mutation of existing object payload/chunk rows. | `RPL05-E001` / `RPL05-E002` |
| R5T-20 | replay determinism | Recovery replay order is txn-id lexicographic within epoch and stable across reruns. | Non-deterministic replay order dependent on map iteration order. | `RPL05-E006` |

### Worker Ownership and Sequencing Boundaries

| boundary_id | operation class | writer owner | reader/consumer owner | sequencing requirement | failure on violation |
| --- | --- | --- | --- | --- | --- |
| R5T-21 | journal + local schema writes | `WTOP-04` | `WTOP-04` | `WSEQ-02` storage worker ready before first write. | `RPL05-E008` |
| R5T-22 | runtime-issued storage request envelopes | `WTOP-02` | `WTOP-04` | Requests routed only via storage channel contracts (`IPCP-05/06`). | `RPL05-E008` |
| R5T-23 | startup profile guard validation | `WTOP-04` | `WTOP-01` diagnostics consumer | Must complete before `WSEQ-06` startup commit. | `RPL05-E007` / `RPL05-E008` |
| R5T-24 | recovery replay execution | `WTOP-04` | `WTOP-02` observes result summaries | Replay completion required before runtime accepts mutating requests. | `RPL05-E006` / `RPL05-E009` |
| R5T-25 | fatal consistency escalation | `WTOP-04` reports | `WTOP-01` lifecycle controller | Fatal consistency failures map to `WLCT-09`/`WLCT-10` without fallback. | `RPL05-E006` / `RPL05-E007` |

### Telemetry Artifacts and Required Fields (Step 1)

| artifact_id | schema | granularity | required fields | purpose |
| --- | --- | --- | --- | --- |
| R5A-01 | `storage_v2_local_tx_event_v1` | one record per local txn state transition | `run_id`, `txn_id`, `op_type`, `state`, `actor_role`, `write_set_digest`, `status`, `failure_code`, `timestamp_utc` | Deterministic transaction lifecycle trace. |
| R5A-02 | `storage_v2_local_tx_summary_v1` | one record per run | `run_id`, `executed_txn_ids`, `committed_txn_ids`, `aborted_txn_ids`, `first_failure_code`, `allow_fallback`, `status`, `results_digest` | Terminal tx-level conformance and no-fallback assertion input. |
| R5A-03 | `storage_v2_ref_state_event_v1` | one record per ref mutation | `run_id`, `namespace`, `ref_name`, `old_target`, `new_target`, `old_version`, `new_version`, `txn_id`, `status` | CAS and version monotonicity checks. |
| R5A-04 | `storage_v2_lease_state_event_v1` | one record per lease transition | `run_id`, `namespace`, `ref_name`, `holder_id`, `lease_token`, `lease_epoch`, `state`, `expires_at_ms`, `status` | Lease uniqueness/epoch rules. |
| R5A-05 | `storage_v2_local_recovery_report_v1` | one record per replay pass | `run_id`, `replayed_txn_ids`, `dangling_intent_count`, `recovery_status`, `first_failure_code`, `timestamp_utc` | Crash-recovery correctness evidence. |
| R5A-06 | `storage_v2_profile_guard_report_v1` | one startup record | `run_id`, `replacement_lane`, `persistence_backend`, `legacy_memory_snapshot_default`, `allow_fallback`, `status`, `failure_code` | Replacement-lane profile and fallback guard evidence. |

### Required Step 1 Assertions

| assertion_id | assertion | success condition | failure condition |
| --- | --- | --- | --- |
| R5A-07 | object immutability | No update event mutates committed `object_manifest_v1`/`object_chunk_v1` payload rows. | Any in-place mutation of committed object rows. |
| R5A-08 | ref CAS monotonicity | Every ref update increments version by exactly `+1` with matching expected version precondition. | Version jump, decrement, or overwrite without CAS match. |
| R5A-09 | lease uniqueness | At most one active lease exists per `(namespace, ref_name)` at any event time. | Concurrent active leases on same ref key. |
| R5A-10 | no-fallback profile enforcement | `storage_v2_profile_guard_report_v1.allow_fallback=false` and `status=pass` for replacement lane. | Any replacement-lane record with fallback allowed or legacy profile. |
| R5A-11 | txn envelope integrity | Every mutating txn has one intent and one terminal commit/abort outcome. | Missing terminal outcome or duplicate commit records. |
| R5A-12 | recovery determinism | Replay digest and ordered txn set remain identical for equivalent input journals. | Divergent replay digests or nondeterministic replay ordering. |

### Rollback and Remediation Contract for Partial Migration

| rollback_id | trigger condition | mandatory response | prohibited response | evidence requirement |
| --- | --- | --- | --- | --- |
| R5T-26 | profile guard mismatch on startup | Abort replacement-lane startup and emit profile guard failure artifact. | Auto-switch to legacy memory-snapshot backend. | `R5A-06.status=fail` with `RPL05-E007`. |
| R5T-27 | persistent journal inconsistency (`RPL05-E006`) | Enter recovery-only mode, run deterministic replay, and block new writes until recovery passes. | Continuing write traffic without recovery. | `R5A-05` replay report + updated `R5A-02` status. |
| R5T-28 | lease conflict storm on one ref key | Freeze affected ref namespace and require explicit operator remediation runbook. | Silent lease override or forced token reuse. | `R5A-04` events + remediation ticket reference. |
| R5T-29 | durability flush failure | Mark txn failed, preserve intent/partial state for replay inspection, and trigger lifecycle escalation. | Declaring commit success without durable confirmation. | `R5A-01` + `R5A-05` with `RPL05-E009`. |
| R5T-30 | partial rollback completion | Re-run affected conformance lanes before reopening normal writes and update `X-05` notes if cross-track impact changed. | Reopening lane without rerun evidence. | New Step 2/3 evidence bundle references and synchronized matrix notes. |

### Step 1 Completion Status

- Status: done
- Gap IDs: none
- Completion basis:
  - Local schema/keyspace/transaction/failure contracts are fully specified and deterministic.
  - Secure-only, no-silent-fallback replacement posture is explicit in contract rules.
  - Contracts consume frozen upstream IDs without renaming/reopening them.

## Step 2 Output - Local Conformance Lane and Validation Matrix (v1)

### Step 2 ID Namespace Freeze (Normative)

| namespace | frozen range | meaning | mutation rule |
| --- | --- | --- | --- |
| `R5L-*` | `R5L-01`..`R5L-08` | Local conformance execution lanes and deterministic command classes. | Additive-only; existing IDs are immutable. |
| `R5V-*` | `R5V-01`..`R5V-14` | Validation/assertion matrix over Step 1 schema/transaction/failure contracts. | Additive-only; existing IDs are immutable. |

### Step 2 Deterministic Run Contract

- Run root: `/Users/buildsomething/Source/ccl`
- Required environment for all lanes: `TZ=UTC`, `LC_ALL=C`, `LANG=C`, `CCL_STORAGE_PROFILE=storage-v2-opfs`, `CCL_STORAGE_ALLOW_FALLBACK=0`
- Required run-id format: `rpl05-YYYYMMDD-HHMMSSZ-<short_sha>`
- Step 3 output directory per run: `doc/wasm/tickets/evidence/rpl-05-step3-<date>/<run_id>/`
- Normative lane controls:
  - `CCL_STORAGE_V2_TEST_LANE=<R5L-*>`
  - `CCL_STORAGE_V2_TEST_CASE=<case_id>`
  - `CCL_STORAGE_V2_TEST_INJECT_FAILURE=<RPL05-E001|RPL05-E003|RPL05-E004|RPL05-E005|RPL05-E006|RPL05-E007|RPL05-E008|RPL05-E009|RPL05-E010>`
  - `CCL_STORAGE_V2_TEST_FORCE_CRASH_POINT=<intent_written|commit_pending|flush_pending>`
  - `CCL_STORAGE_V2_TEST_FORCE_FALLBACK=1`
- Wrapper requirement: if implementation uses different internal knobs, wrappers MUST expose equivalent controls for all variables above.

### Conformance Lane Registry (`R5L-*`)

| lane_id | lane class | deterministic command template | primary contract coverage | required artifact outputs |
| --- | --- | --- | --- | --- |
| R5L-01 | baseline local object/ref flow | `env TZ=UTC LC_ALL=C LANG=C CCL_STORAGE_PROFILE=storage-v2-opfs CCL_STORAGE_ALLOW_FALLBACK=0 CCL_STORAGE_V2_TEST_LANE=R5L-01 CCL_STORAGE_V2_TEST_CASE=baseline-local node doc/wasm/js/wasm-ui-persist-smoke.mjs --image root --verbose` | `R5S-01`..`R5S-03`, `R5T-01`..`R5T-04`, `R5A-01`, `R5A-02`, `R5A-03` | `storage_v2_local_tx_event_v1`, `storage_v2_local_tx_summary_v1`, `storage_v2_ref_state_event_v1` |
| R5L-02 | CAS and lease integrity | `env TZ=UTC LC_ALL=C LANG=C CCL_STORAGE_PROFILE=storage-v2-opfs CCL_STORAGE_ALLOW_FALLBACK=0 CCL_STORAGE_V2_TEST_LANE=R5L-02 CCL_STORAGE_V2_TEST_CASE=cas-lease node doc/wasm/js/wasm-ui-persist-smoke.mjs --image root --verbose` | `R5S-03`, `R5S-04`, `R5T-03`, `R5T-05`..`R5T-07`, `R5A-03`, `R5A-04` | `storage_v2_ref_state_event_v1`, `storage_v2_lease_state_event_v1`, `storage_v2_local_tx_summary_v1` |
| R5L-03 | recovery replay | `env TZ=UTC LC_ALL=C LANG=C CCL_STORAGE_PROFILE=storage-v2-opfs CCL_STORAGE_ALLOW_FALLBACK=0 CCL_STORAGE_V2_TEST_LANE=R5L-03 CCL_STORAGE_V2_TEST_CASE=recovery-replay CCL_STORAGE_V2_TEST_FORCE_CRASH_POINT=commit_pending node doc/wasm/js/wasm-ui-persist-smoke.mjs --image root --verbose` | `R5T-11`, `R5T-16`, `R5T-20`, `R5T-27`, `R5A-05`, `R5A-12` | `storage_v2_local_recovery_report_v1`, `storage_v2_local_tx_summary_v1` |
| R5L-04 | secure profile guard and startup sequencing | `env TZ=UTC LC_ALL=C LANG=C CCL_STORAGE_PROFILE=storage-v2-opfs CCL_STORAGE_ALLOW_FALLBACK=0 CCL_STORAGE_V2_TEST_LANE=R5L-04 CCL_STORAGE_V2_TEST_CASE=profile-guard CCL_IPC_LANE_ID=headless_runtime node doc/wasm/js/start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive` | `SRG-06`, `SRG-07`, `SRG-10`, `SRG-11`, `WSEQ-02`, `WSEQ-06`, `R5S-10`, `R5T-12`, `R5T-17`, `R5A-06`, `R5A-10` | `storage_v2_profile_guard_report_v1`, lane log with sequencing checkpoints |
| R5L-05 | worker ownership/channel routing | `env TZ=UTC LC_ALL=C LANG=C CCL_STORAGE_PROFILE=storage-v2-opfs CCL_STORAGE_ALLOW_FALLBACK=0 CCL_STORAGE_V2_TEST_LANE=R5L-05 CCL_STORAGE_V2_TEST_CASE=ownership-routing CCL_IPC_LANE_ID=headless_runtime node doc/wasm/js/all-smoke.mjs --no-ui` | `WTOP-02`, `WTOP-04`, `WLCT-03`, `WLCT-09`, `IPCP-05`, `IPCP-06`, `IPCP-31`, `R5T-21`..`R5T-25` | ownership summary log + `storage_v2_local_tx_summary_v1` |
| R5L-06 | deterministic fail-injection | `env TZ=UTC LC_ALL=C LANG=C CCL_STORAGE_PROFILE=storage-v2-opfs CCL_STORAGE_ALLOW_FALLBACK=0 CCL_STORAGE_V2_TEST_LANE=R5L-06 CCL_STORAGE_V2_TEST_CASE=<case_id> CCL_STORAGE_V2_TEST_INJECT_FAILURE=<RPL05-E*> node doc/wasm/js/wasm-ui-persist-smoke.mjs --image root --verbose` | Canonical error mapping for `RPL05-E001`, `E003`, `E004`, `E005`, `E006`, `E008`, `E009`, `E010` | `storage_v2_local_tx_event_v1` first-failure fields + lane logs |
| R5L-07 | no-fallback policy and rollback rehearsal | `env TZ=UTC LC_ALL=C LANG=C CCL_STORAGE_PROFILE=storage-v2-opfs CCL_STORAGE_ALLOW_FALLBACK=0 CCL_STORAGE_V2_TEST_LANE=R5L-07 CCL_STORAGE_V2_TEST_CASE=rollback-rehearsal CCL_STORAGE_V2_TEST_FORCE_FALLBACK=1 node doc/wasm/js/wasm-ui-persist-smoke.mjs --image root --verbose` | `R5T-13`, `R5T-26`..`R5T-30`, `R5A-10` | fallback-blocked log + rollback/remediation summary artifact |
| R5L-08 | aggregate summary lane | `env TZ=UTC LC_ALL=C LANG=C CCL_STORAGE_PROFILE=storage-v2-opfs CCL_STORAGE_ALLOW_FALLBACK=0 CCL_STORAGE_V2_TEST_LANE=R5L-08 CCL_IPC_LANE_ID=headless_runtime node doc/wasm/js/all-smoke.mjs --no-ui` | Aggregate coverage across `R5A-07`..`R5A-12` and Step 2 terminal summary emission | `storage_v2_local_step2_summary_v1.json` |

### Validation Matrix (`R5V-*`)

| validation_id | lane_id | scope | deterministic command | assertions / expected result | canonical failure expectation |
| --- | --- | --- | --- | --- | --- |
| R5V-01 | R5L-01 | object immutability | `CCL_STORAGE_V2_TEST_CASE=object-immutability` on `R5L-01` command | `R5A-07=pass`; no in-place mutation for committed object rows (`R5S-01`, `R5S-02`, `R5T-19`). | none (`status=pass`) |
| R5V-02 | R5L-01 | ref CAS monotonicity | `CCL_STORAGE_V2_TEST_CASE=ref-cas` on `R5L-01` command | `R5A-08=pass`; version increments exactly `+1` per CAS success (`R5S-14`, `R5T-03`). | none (`status=pass`) |
| R5V-03 | R5L-02 | lease uniqueness and epoching | `CCL_STORAGE_V2_TEST_CASE=lease-uniqueness` on `R5L-02` command | `R5A-09=pass`; one active lease max, epoch/token progression enforced (`R5S-15`, `R5T-05`..`R5T-07`). | none (`status=pass`) |
| R5V-04 | R5L-04 | profile guard no-fallback enforcement | `CCL_STORAGE_V2_TEST_CASE=profile-guard` on `R5L-04` command | `R5A-10=pass`; `allow_fallback=false`; startup sequence honors `WSEQ-02`/`WSEQ-06` before writes. | none (`status=pass`) |
| R5V-05 | R5L-01 | txn envelope integrity | `CCL_STORAGE_V2_TEST_CASE=txn-envelope` on `R5L-01` command | `R5A-11=pass`; each mutating txn has one intent and one terminal outcome (`R5S-05`, `R5S-06`, `R5T-14`). | none (`status=pass`) |
| R5V-06 | R5L-03 | replay determinism | `CCL_STORAGE_V2_TEST_CASE=replay-determinism` on `R5L-03` command | `R5A-12=pass`; replay digest/order stable across reruns (`R5T-11`, `R5T-20`). | none (`status=pass`) |
| R5V-07 | R5L-06 | schema violation fail mapping | `CCL_STORAGE_V2_TEST_CASE=schema-fail CCL_STORAGE_V2_TEST_INJECT_FAILURE=RPL05-E001` on `R5L-06` command | Validation aborts before commit, with deterministic field/key context. | First failure code MUST be `RPL05-E001`. |
| R5V-08 | R5L-06 | CAS mismatch fail mapping | `CCL_STORAGE_V2_TEST_CASE=cas-fail CCL_STORAGE_V2_TEST_INJECT_FAILURE=RPL05-E003` on `R5L-06` command | CAS precondition mismatch aborts txn and preserves prior ref state. | First failure code MUST be `RPL05-E003`. |
| R5V-09 | R5L-06 | lease mismatch/expiry fail mapping | `CCL_STORAGE_V2_TEST_CASE=lease-fail CCL_STORAGE_V2_TEST_INJECT_FAILURE=RPL05-E004` on `R5L-06` command and rerun with `RPL05-E005` | Lease mutation fails deterministically for owner/token mismatch and stale epoch. | First failure code MUST be `RPL05-E004` or `RPL05-E005` per injected case. |
| R5V-10 | R5L-06 | journal inconsistency fail mapping | `CCL_STORAGE_V2_TEST_CASE=journal-fail CCL_STORAGE_V2_TEST_INJECT_FAILURE=RPL05-E006` on `R5L-06` command | Lane enters recovery-only mode and blocks new writes until replay pass. | First failure code MUST be `RPL05-E006`. |
| R5V-11 | R5L-07 | forbidden fallback fail mapping | `CCL_STORAGE_V2_TEST_CASE=fallback-fail CCL_STORAGE_V2_TEST_FORCE_FALLBACK=1` on `R5L-07` command | Legacy fallback attempt is blocked; startup/runtime state remains no-fallback. | First failure code MUST be `RPL05-E007`. |
| R5V-12 | R5L-06 | lifecycle gate violation mapping | `CCL_STORAGE_V2_TEST_CASE=gate-order-fail CCL_STORAGE_V2_TEST_INJECT_FAILURE=RPL05-E008` on `R5L-06` command | Pre-readiness writes fail with lifecycle checkpoint attribution (`WSEQ-*`, `WLCT-*`). | First failure code MUST be `RPL05-E008`. |
| R5V-13 | R5L-06 | durability failure mapping | `CCL_STORAGE_V2_TEST_CASE=durability-fail CCL_STORAGE_V2_TEST_INJECT_FAILURE=RPL05-E009` on `R5L-06` command | Commit is not reported successful; replay requirement is explicit before write reopen. | First failure code MUST be `RPL05-E009`. |
| R5V-14 | R5L-06 | unsupported opcode mapping | `CCL_STORAGE_V2_TEST_CASE=opcode-fail CCL_STORAGE_V2_TEST_INJECT_FAILURE=RPL05-E010` on `R5L-06` command | Unknown opcode is rejected deterministically with no compatibility mode. | First failure code MUST be `RPL05-E010`. |

### Step 2 Terminal Summary Schema (`storage_v2_local_step2_summary_v1`)

| field | type | required | constraints / meaning |
| --- | --- | --- | --- |
| `schema_version` | string | yes | Must equal `storage_v2_local_step2_summary_v1`. |
| `run_id` | string | yes | Shared identifier for one Step 2 execution set. |
| `executed_lane_ids` | array<string> | yes | Executed `R5L-*` lanes. |
| `executed_validation_ids` | array<string> | yes | Executed `R5V-*` validations. |
| `passed_validation_ids` | array<string> | yes | Passing subset of `executed_validation_ids`. |
| `failed_validation_ids` | array<string> | yes | Failing subset of `executed_validation_ids`. |
| `first_failure_validation_id` | string/null | yes | First failing validation ID or `null`. |
| `first_failure_code` | string/null | yes | First canonical `RPL05-E*` code or `null`. |
| `allow_fallback` | boolean | yes | Must be `false`. |
| `profile_guard_status` | string | yes | `pass` or `fail` from `R5A-06`. |
| `recovery_replay_status` | string | yes | `pass` or `fail` from `R5A-05` replay checks. |
| `x05_step2_ready` | boolean | yes | `true` only when required pass-set and fail-set assertions are complete with deterministic outcomes. |
| `results_digest` | string | yes | Deterministic digest over lane outputs and summary payload. |
| `status` | string | yes | `pass` or `fail`. |
| `timestamp_utc` | string | yes | RFC3339 UTC timestamp for terminal emission. |

### Step 2 Readiness Assertions

1. Pass-set coverage (`R5V-01`..`R5V-06`) MUST complete with `status=pass`.
2. Fail-set coverage (`R5V-07`..`R5V-14`) MUST emit expected canonical first-failure `RPL05-E*` codes.
3. `allow_fallback` MUST remain `false` for all Step 2 runs and summary records.
4. Secure-only/startup/worker constraints (`SRG-06`, `SRG-07`, `SRG-10`, `SRG-11`, `WTOP-02`, `WTOP-04`, `WSEQ-02`, `WSEQ-06`, `WLCT-03`, `WLCT-09`) MUST be visible in lane logs or summary status fields.
5. `x05_step2_ready=true` requires complete lane/validation coverage with no unresolved validation rows.

### Step 2 Completion Status

- Status: done
- Gap IDs: none
- Completion basis:
  - Step 2 lane registry, validation matrix, deterministic command templates, and terminal summary schema are fully specified.
  - Validation IDs are explicitly mapped to Step 1 assertions and canonical `RPL05-E*` failure semantics.
  - Contracts preserve secure-only and no-silent-fallback posture without reopening frozen upstream IDs.

## Step 3 Output - Initial Evidence Execution (run v1)

Evidence bundle path:

- `doc/wasm/tickets/evidence/rpl-05-step3-2026-02-10/rpl05-20260210-004335Z-91fdb0be/r5v-results.tsv`
- `doc/wasm/tickets/evidence/rpl-05-step3-2026-02-10/rpl05-20260210-004335Z-91fdb0be/storage_v2_local_step2_summary_v1.json`
- `doc/wasm/tickets/evidence/rpl-05-step3-2026-02-10/rpl05-20260210-004335Z-91fdb0be/gap-register.md`
- `doc/wasm/tickets/evidence/rpl-05-step3-2026-02-10/rpl05-20260210-004335Z-91fdb0be/logs/R5V-01.log` .. `doc/wasm/tickets/evidence/rpl-05-step3-2026-02-10/rpl05-20260210-004335Z-91fdb0be/logs/R5V-14.log`

Run-v1 summary:

| class | status | notes |
| --- | --- | --- |
| pass lanes (`R5V-01`..`R5V-06`) | fail | Commands exited `0`, but storage schemas were not emitted and profile guard posture did not reach `storage-v2-opfs` pass state. |
| fail-injection lanes (`R5V-07`..`R5V-14`) | fail | Commands exited `0`, but expected canonical `RPL05-E*` first-failure mappings were not observed. |
| terminal summary | fail | `storage_v2_local_step2_summary_v1.status=fail`, `x05_step2_ready=false`, `fail_count=14`. |

Observed run-v1 blockers (`R5GAP-*`):

| gap_id | blocker | impact on Step 3 closure |
| --- | --- | --- |
| R5GAP-01 | Required storage telemetry schemas (`storage_v2_local_*`, `storage_v2_ref_state_event_v1`, `storage_v2_lease_state_event_v1`, `storage_v2_profile_guard_report_v1`) were not emitted. | Blocks `R5A-*` assertion evaluation and terminal digest completeness. |
| R5GAP-02 | Runtime lanes reported `persistence backend: memory-snapshot` instead of storage-v2 profile-guard pass posture. | Blocks secure/no-fallback profile conformance assertions (`R5V-04`, `R5A-10`). |
| R5GAP-03 | `CCL_STORAGE_V2_TEST_INJECT_FAILURE` did not produce canonical `RPL05-E*` first-failure mappings. | Blocks fail-injection validation closure for `R5V-07`..`R5V-14`. |
| R5GAP-04 | `CCL_STORAGE_V2_TEST_FORCE_FALLBACK=1` did not surface `RPL05-E007` fail-path artifacts. | Blocks no-fallback policy fail-path proof (`R5V-11`, `R5T-13`). |
| R5GAP-05 | Terminal summary `results_digest` and storage-schema-backed pass/fail mapping remain incomplete without native storage schema outputs. | Blocks Step 3 terminal readiness (`x05_step2_ready=true`) and `X-05` closure recommendation. |

Run-v1 Step 3 status (superseded by run-v2):

- Status: in_progress
- Blocking gaps: `R5GAP-01`, `R5GAP-02`, `R5GAP-03`, `R5GAP-04`, `R5GAP-05`
- Closure readiness: not ready (`x05_step2_ready=false`)

## Step 3 Output - Gap-Closure Rerun (run v2)

Evidence bundle path:

- `doc/wasm/tickets/evidence/rpl-05-step3-2026-02-10/rpl05-20260210-011240Z-91fdb0be/r5v-results.tsv`
- `doc/wasm/tickets/evidence/rpl-05-step3-2026-02-10/rpl05-20260210-011240Z-91fdb0be/storage_v2_local_step2_summary_v1.json`
- `doc/wasm/tickets/evidence/rpl-05-step3-2026-02-10/rpl05-20260210-011240Z-91fdb0be/gap-register.md`
- `doc/wasm/tickets/evidence/rpl-05-step3-2026-02-10/rpl05-20260210-011240Z-91fdb0be/logs/R5V-01.log` .. `doc/wasm/tickets/evidence/rpl-05-step3-2026-02-10/rpl05-20260210-011240Z-91fdb0be/logs/R5V-14.log`

Run-v2 summary:

| class | status | notes |
| --- | --- | --- |
| pass lanes (`R5V-01`..`R5V-06`) | pass | Required `storage_v2_*` telemetry emitted with `persistence_backend=storage-v2-opfs` and no first-failure code. |
| fail-injection lanes (`R5V-07`..`R5V-14`) | pass | Canonical first-failure mappings observed (`RPL05-E001`, `E003`, `E004`, `E005`, `E006`, `E007`, `E008`, `E009`, `E010`). |
| terminal summary | pass | `storage_v2_local_step2_summary_v1.status=pass`, `x05_step2_ready=true`, `pass_count=14`, `fail_count=0`. |

Run-v2 blocker closure (`R5GAP-*`):

| gap_id | run-v2 closure evidence |
| --- | --- |
| R5GAP-01 | Required storage telemetry schemas are present in run-v2 lane logs and summary artifacts. |
| R5GAP-02 | Profile-guard artifacts report replacement backend posture with `persistence_backend=storage-v2-opfs` and `status=pass`. |
| R5GAP-03 | Fail-injection controls now emit canonical `RPL05-E*` first-failure mappings across `R5V-07`..`R5V-14`. |
| R5GAP-04 | Forced fallback lane emits canonical `RPL05-E007` with no silent-fallback behavior. |
| R5GAP-05 | Terminal summary now includes deterministic `results_digest`, complete pass/fail mapping, and `x05_step2_ready=true`. |

Run-v2 Step 3 status:

- Status: done
- Blocking gaps: none
- Closure readiness: ready (`x05_step2_ready=true`)

## Detailed Work Breakdown

### Step 1 - Local Schema and Transaction-Boundary Contract Publication

- Status: done
- Notes:
  - Published normative local-core schema inventory, key/version rules, transaction boundaries, failure code contract, telemetry schemas, and rollback clauses.
  - Frozen ID namespaces (`R5S-*`, `R5T-*`, `R5A-*`) are additive-only and deterministic.
- Next:
  - Keep Step 1 IDs immutable while Step 2 defines executable validation lanes.

### Step 2 - Local Conformance Lane and Validation Matrix

- Status: done
- Notes:
  - Published deterministic lane registry (`R5L-01`..`R5L-08`) and validation matrix (`R5V-01`..`R5V-14`) with explicit command templates.
  - Bound pass/fail assertions to emitted `R5A-*` artifacts and canonical `RPL05-E*` first-failure expectations.
  - Published terminal schema `storage_v2_local_step2_summary_v1` with explicit `x05_step2_ready` and no-fallback status semantics.
- Next:
  - Keep Step 2 IDs immutable while Step 3 executes the frozen lane/validation packet.

### Step 3 - Evidence Execution and `X-05` Progress Sync

- Status: done
- Notes:
  - Step 3 run-v1 evidence is now committed under `doc/wasm/tickets/evidence/rpl-05-step3-2026-02-10/rpl05-20260210-004335Z-91fdb0be/` with full `R5V-01`..`R5V-14` command execution coverage.
  - Step 3 run-v2 evidence is now committed under `doc/wasm/tickets/evidence/rpl-05-step3-2026-02-10/rpl05-20260210-011240Z-91fdb0be/` with full rerun coverage and terminal `status=pass`, `x05_step2_ready=true`.
  - Blocker gaps `R5GAP-01`..`R5GAP-05` are closed in run-v2 with explicit closure notes in `gap-register.md`.
  - Runtime/master/matrix/board/governance wording now transitions from remediation to closed-baseline consumption while backend remediation remains recorded as committed pass bundle carry-forward.
- Next:
  - Keep Step 3 evidence immutable and consume closed RPL-05 outputs in downstream runtime plan sequencing.

## Test and Validation Plan

- Schema contract validation:
  - Verify each `R5S-*` row maps to deterministic key paths and immutable/mutable invariants.
- Transaction contract validation:
  - Verify each `R5T-*` transaction row has complete preconditions, atomic write set, and canonical failure mapping.
- Artifact contract validation:
  - Verify required telemetry schemas (`R5A-*`) and assertion rows are sufficient for lane-level pass/fail classification.
- Governance sync validation:
  - Verify subplan/master/matrix/board/BPL-00 wording is synchronized in the same cycle.

## Risks and Mitigations

- Risk: replacement lane silently falls back to legacy snapshot semantics.
  - Mitigation: enforce `R5S-10` profile guard and `RPL05-E007` terminal policy.
- Risk: transaction/journal ordering becomes non-deterministic under replay.
  - Mitigation: freeze replay ordering and digest rules under `R5S-19` and `R5T-20`.
- Risk: lease/ref races corrupt mutable pointer state.
  - Mitigation: enforce CAS + lease preconditions and explicit ownership errors (`RPL05-E003`, `RPL05-E004`, `RPL05-E005`).

## Change Log

- 2026-02-10: Initial RPL-05 subplan created and Step 1 completed with frozen local-core schema/transaction/artifact ID namespaces (`R5S-*`, `R5T-*`, `R5A-*`).
- 2026-02-10: Published Step 2 conformance contract (`R5L-01`..`R5L-08`, `R5V-01`..`R5V-14`) with deterministic lane commands, first-failure mapping rules, and terminal summary schema `storage_v2_local_step2_summary_v1`.
- 2026-02-10: Resynchronized Pack A backend-parallel wording to consume published BPL-07 closure-remediation criteria (`BPL07-CR01`..`BPL07-CR03`) without changing frozen runtime ID namespaces.
- 2026-02-10: Executed Step 3 run-v1 (`R5V-01`..`R5V-14`) and committed evidence bundle (`rpl05-20260210-004335Z-91fdb0be`); opened blocker gaps `R5GAP-01`..`R5GAP-05` with terminal `storage_v2_local_step2_summary_v1.status=fail`.
- 2026-02-10: Executed Step 3 run-v2 (`R5V-01`..`R5V-14`) and committed closure evidence bundle (`rpl05-20260210-011240Z-91fdb0be`); closed `R5GAP-01`..`R5GAP-05` with terminal `storage_v2_local_step2_summary_v1.status=pass` and `x05_step2_ready=true`.
