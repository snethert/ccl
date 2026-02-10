# RPL-06 - Storage V2 Sync and Merge

Status: done  
Priority: P1  
Owner: Runtime/WASM replacement track  
Last Updated: 2026-02-10  
Parent Plan: `doc/wasm/runtime-replacement-master-plan.md`

## Scope

In scope:

- Define Storage V2 remote sync contract for object upload/download, ref synchronization, and lease-safe update flow.
- Define deterministic conflict records, merge-candidate records, and finalization rules.
- Freeze no-silent-fallback behavior for replacement-lane sync and merge paths.
- Define machine-actionable evidence artifacts for sync/merge validation lanes.

Out of scope:

- Local-core schema/transaction semantics already closed under RPL-05.
- Runtime/UI transport migration and bridge semantics (RPL-04).
- Module environment sharing and artifact budget work (RPL-07/RPL-08).

## Dependencies

- RPL-00 governance sync discipline.
- RPL-01 secure startup/no-fallback requirements (`SRG-*`, `RPL01-E*`).
- RPL-02 worker ownership/lifecycle boundaries (`WTOP-*`, `WSEQ-*`, `WLCT-*`).
- RPL-03 shared-channel transport/error semantics (`IPCP-*`, `IPCV-*`).
- RPL-05 closed local-core baseline (`R5S-*`, `R5T-*`, `R5A-*`).

## Deliverables

1. Step 1 sync/merge contract with frozen IDs for remote API, state records, and failure mappings.
2. Step 2 deterministic lane and validation matrix for success/failure/rollback coverage.
3. Step 3 committed evidence bundle with terminal summary and synchronized master-plan updates.

## Exit Criteria

- Remote sync and merge workflows are deterministic and machine-verifiable.
- Conflict and merge-finalization records are explicitly modeled with immutable audit fields.
- Replacement lane forbids silent fallback to legacy sync behavior.
- Validation lanes cover pass/fail cases and canonical failure-code mappings.

## Current Notes

- This subplan is now authored and Step 1 is published in this document.
- Step 1 freezes sync/merge namespace IDs (`R6S-*`, `R6T-*`, `R6A-*`) as additive-only.
- Step 1 consumes frozen upstream IDs from `RPL-01`, `RPL-02`, `RPL-03`, and `RPL-05` without mutation.
- Step 2 lane/validation matrix is now published with frozen `R6L-*` and `R6V-*` IDs plus terminal schema `storage_v2_sync_step2_summary_v1`.
- Step 3 run-v1 closure evidence is now committed at `doc/wasm/tickets/evidence/rpl-06-step3-2026-02-10/rpl06-20260210-054023Z-50d752af/` with full `R6V-01`..`R6V-14` execution coverage.
- Run-v1 terminal summary reports `storage_v2_sync_step2_summary_v1.status=pass`, `allow_fallback=false`, and no open Step 3 blocker gaps.

## Immediate Next Step

- Action: maintain RPL-06 as additive-only closed baseline and consume frozen sync/merge contracts/evidence in downstream runtime sequencing.
- Why now: Step 3 closure criteria are satisfied with committed evidence and terminal pass summary.
- Success evidence: runtime/master/governance docs mark `RPL-06=done`, reference `rpl06-20260210-054023Z-50d752af`, and preserve frozen `R6S-*`/`R6T-*`/`R6A-*`/`R6L-*`/`R6V-*` IDs without rewrites.

## Detailed Work Breakdown

### Step 1 - Sync/Merge Contract and State Schema

- Status: done
- Notes:
  - Step 1 output is now published with frozen ID namespaces `R6S-*`, `R6T-*`, and `R6A-*`.
  - Remote API contract, conflict/merge state records, and canonical failure mappings are now explicit.
  - No-fallback replacement-lane semantics and rollback/remediation clauses are defined.
- Next:
  - Keep Step 1 IDs immutable while Step 2 defines deterministic lane coverage.

### Step 2 - Validation Lane and Evidence Matrix

- Status: done
- Notes:
  - Step 2 output is now published with frozen lane IDs `R6L-01`..`R6L-08` and validation IDs `R6V-01`..`R6V-14`.
  - Deterministic command templates now cover upload/download, CAS sync, conflict/merge flow, fail-injection mappings, and no-fallback enforcement.
  - Terminal schema `storage_v2_sync_step2_summary_v1` is now defined for Step 3 evidence closure.
- Next:
  - Keep `R6L-*`/`R6V-*`/`storage_v2_sync_step2_summary_v1` frozen as additive-only closed baseline inputs.

### Step 3 - Evidence Run and Closure

- Status: done
- Notes:
  - Step 3 run-v1 evidence is now committed under `doc/wasm/tickets/evidence/rpl-06-step3-2026-02-10/rpl06-20260210-054023Z-50d752af/` with full `R6V-01`..`R6V-14` coverage.
  - Terminal `storage_v2_sync_step2_summary_v1` now reports `status=pass`, `allow_fallback=false`, `pass_count=14`, `fail_count=0`.
  - `gap-register.md` reports no open Step 3 blocker gaps.
- Next:
  - Keep Step 3 evidence immutable and consume RPL-06 as a closed baseline.

## Step 1 Output - Sync/Merge Contract (v1)

### ID Namespace Freeze

| namespace | frozen range | meaning | mutation rule |
| --- | --- | --- | --- |
| `R6S-*` | `R6S-01`..`R6S-20` | Sync state records and remote endpoint contracts. | Additive-only; existing IDs immutable. |
| `R6T-*` | `R6T-01`..`R6T-20` | Sync/merge transaction semantics, failure behavior, rollback rules. | Additive-only; existing IDs immutable. |
| `R6A-*` | `R6A-01`..`R6A-10` | Telemetry schemas and required assertions for Step 2/3 evidence. | Additive-only; existing IDs immutable. |

### Remote API and Sync State Records

| id | record / endpoint | contract |
| --- | --- | --- |
| R6S-01 | `sync_pull_cursor_v1` | Cursor includes `namespace`, `last_applied_event_id`, `last_applied_ref_version`, `timestamp_utc`; monotonic per namespace. |
| R6S-02 | `sync_push_batch_v1` | Batch carries ordered `ops[]`, `client_txn_id`, `base_ref_versions`, `batch_digest`; server validates digest before apply. |
| R6S-03 | `sync_object_advert_v1` | Object advert includes `object_id`, `byte_length`, `chunk_count`, `content_hash`; immutable once published. |
| R6S-04 | `sync_ref_delta_v1` | Ref delta includes `namespace`, `ref_name`, `old_version`, `new_version`, `old_target`, `new_target`, `source_event_id`. |
| R6S-05 | `sync_conflict_record_v1` | Conflict record includes `conflict_id`, `namespace`, `ref_name`, `client_state`, `remote_state`, `detected_at_utc`, `resolution_state`. |
| R6S-06 | `sync_merge_candidate_v1` | Merge candidate includes `candidate_id`, `conflict_id`, `base_object_id`, `left_object_id`, `right_object_id`, `strategy`, `status`. |
| R6S-07 | `sync_merge_finalization_v1` | Finalization includes `candidate_id`, `final_object_id`, `final_ref_version`, `finalized_at_utc`, `finalizer_id`, `result_digest`. |
| R6S-08 | `sync_lease_guard_v1` | Lease guard binds sync mutation to lease token/epoch tuple from RPL-05 local-core contract. |
| R6S-09 | `sync_profile_guard_v1` | Guard requires replacement-lane profile, secure startup gates satisfied, and `allow_fallback=false`. |
| R6S-10 | `sync_run_summary_v1` | Terminal run summary carries operation counts, first failure code, fallback flag, and deterministic digest over events. |

### Sync and Merge Semantics

| id | operation | required semantics |
| --- | --- | --- |
| R6T-01 | pull replay ordering | Apply remote events in canonical event-id order; no map-iteration ordering allowed. |
| R6T-02 | push CAS enforcement | Push apply requires base ref version match; mismatches create conflict records, not silent overwrite. |
| R6T-03 | object transfer integrity | Chunk/object hashes must match advert; mismatch aborts apply and marks batch failed. |
| R6T-04 | conflict creation | Any divergent ref transition with shared base creates `sync_conflict_record_v1` deterministically. |
| R6T-05 | merge candidate generation | Candidate generation is deterministic from conflict record + selected strategy id. |
| R6T-06 | merge finalization | Finalization requires explicit `finalizer_id` and emits immutable `sync_merge_finalization_v1` record. |
| R6T-07 | lease-safe mutation | Sync mutations that update refs require active lease guard when policy enabled. |
| R6T-08 | no-silent-fallback | Any fallback path attempt fails hard with canonical failure code and aborts batch. |
| R6T-09 | retry idempotency | Retries with identical `client_txn_id` are idempotent and must not duplicate committed changes. |
| R6T-10 | rollback and replay | Partial apply failures trigger deterministic rollback/replay path before accepting new mutating sync traffic. |

### Canonical Failure Mappings

| id | code | condition |
| --- | --- | --- |
| R6T-11 | `RPL06-E001` | sync payload/schema validation failure |
| R6T-12 | `RPL06-E002` | object hash/chunk integrity mismatch |
| R6T-13 | `RPL06-E003` | push CAS/base-version mismatch |
| R6T-14 | `RPL06-E004` | lease guard/token mismatch |
| R6T-15 | `RPL06-E005` | conflict merge candidate generation failure |
| R6T-16 | `RPL06-E006` | merge finalization contract violation |
| R6T-17 | `RPL06-E007` | forbidden fallback attempt in replacement lane |
| R6T-18 | `RPL06-E008` | lifecycle/startup gate prerequisite violation |
| R6T-19 | `RPL06-E009` | rollback/replay consistency failure |
| R6T-20 | `RPL06-E010` | unsupported sync opcode or strategy id |

### Telemetry and Assertion Contracts

| id | artifact / assertion | requirement |
| --- | --- | --- |
| R6A-01 | `storage_v2_sync_event_v1` | Per-op event with `run_id`, `op_type`, `status`, `failure_code`, `timestamp_utc`. |
| R6A-02 | `storage_v2_sync_conflict_event_v1` | Conflict event includes full local/remote ref tuples and deterministic `conflict_id`. |
| R6A-03 | `storage_v2_merge_candidate_event_v1` | Candidate event includes strategy id, inputs, and deterministic candidate digest. |
| R6A-04 | `storage_v2_merge_finalization_event_v1` | Finalization event includes final object/ref metadata and result digest. |
| R6A-05 | `storage_v2_sync_summary_v1` | Terminal summary must include `allow_fallback=false` and `status=pass|fail`. |
| R6A-06 | assertion: deterministic replay | Equivalent inputs produce stable event ordering and stable summary digest. |
| R6A-07 | assertion: no silent overwrite | CAS mismatch creates conflict record; no direct overwrite accepted. |
| R6A-08 | assertion: no fallback | Any fallback attempt yields `RPL06-E007` and run `status=fail`. |
| R6A-09 | assertion: merge auditability | Every merge finalization maps to prior conflict and candidate records. |
| R6A-10 | assertion: rollback safety | Partial failures require rollback/replay completion before new writes. |

## Test and Validation Plan

- Unit:
  - Validate sync payload schemas and deterministic digest calculations for `R6S-*` records.
- Integration:
  - Validate pull/push CAS behavior, conflict creation, merge candidate generation, and finalization replay.
- Regression:
  - Validate no-silent-fallback and rollback/replay behavior under injected failure conditions.

## Step 2 Output - Validation Lane and Evidence Matrix (v1)

### Step 2 ID Namespace Freeze

| namespace | frozen range | meaning | mutation rule |
| --- | --- | --- | --- |
| `R6L-*` | `R6L-01`..`R6L-08` | Deterministic sync/merge execution lanes. | Additive-only; existing IDs immutable. |
| `R6V-*` | `R6V-01`..`R6V-14` | Validation/assertion matrix over Step 1 sync/merge contracts. | Additive-only; existing IDs immutable. |

### Step 2 Deterministic Run Contract

- Run root: `/Users/buildsomething/Source/ccl`
- Required environment for all lanes: `TZ=UTC`, `LC_ALL=C`, `LANG=C`, `CCL_STORAGE_PROFILE=storage-v2-opfs`, `CCL_STORAGE_ALLOW_FALLBACK=0`
- Required run-id format: `rpl06-YYYYMMDD-HHMMSSZ-<short_sha>`
- Step 3 output directory per run: `doc/wasm/tickets/evidence/rpl-06-step3-<date>/<run_id>/`
- Normative lane controls:
  - `CCL_STORAGE_V2_SYNC_LANE=<R6L-*>`
  - `CCL_STORAGE_V2_SYNC_CASE=<case_id>`
  - `CCL_STORAGE_V2_SYNC_INJECT_FAILURE=<RPL06-E001|RPL06-E003|RPL06-E004|RPL06-E006|RPL06-E007|RPL06-E008|RPL06-E009|RPL06-E010>`
  - `CCL_STORAGE_V2_SYNC_FORCE_FALLBACK=1`
  - `CCL_STORAGE_V2_SYNC_RUN_ID=<run_id>`

### Deterministic Lane Registry

| lane_id | lane class | command template | primary contract coverage |
| --- | --- | --- | --- |
| R6L-01 | baseline pull/push sync | `env TZ=UTC LC_ALL=C LANG=C CCL_STORAGE_PROFILE=storage-v2-opfs CCL_STORAGE_ALLOW_FALLBACK=0 CCL_STORAGE_V2_SYNC_LANE=R6L-01 CCL_STORAGE_V2_SYNC_CASE=baseline node doc/wasm/js/storage-v2-sync-conformance.mjs` | `R6S-01`..`R6S-04`, `R6T-01`..`R6T-03`, `R6A-01`, `R6A-05` |
| R6L-02 | ref CAS + lease guard sync | `env TZ=UTC LC_ALL=C LANG=C CCL_STORAGE_PROFILE=storage-v2-opfs CCL_STORAGE_ALLOW_FALLBACK=0 CCL_STORAGE_V2_SYNC_LANE=R6L-02 CCL_STORAGE_V2_SYNC_CASE=cas-lease node doc/wasm/js/storage-v2-sync-conformance.mjs` | `R6S-04`, `R6S-08`, `R6T-02`, `R6T-07`, `R6A-01`, `R6A-07` |
| R6L-03 | conflict detection | `env TZ=UTC LC_ALL=C LANG=C CCL_STORAGE_PROFILE=storage-v2-opfs CCL_STORAGE_ALLOW_FALLBACK=0 CCL_STORAGE_V2_SYNC_LANE=R6L-03 CCL_STORAGE_V2_SYNC_CASE=conflict-detect node doc/wasm/js/storage-v2-sync-conformance.mjs` | `R6S-05`, `R6T-04`, `R6A-02`, `R6A-07` |
| R6L-04 | merge candidate generation | `env TZ=UTC LC_ALL=C LANG=C CCL_STORAGE_PROFILE=storage-v2-opfs CCL_STORAGE_ALLOW_FALLBACK=0 CCL_STORAGE_V2_SYNC_LANE=R6L-04 CCL_STORAGE_V2_SYNC_CASE=merge-candidate node doc/wasm/js/storage-v2-sync-conformance.mjs` | `R6S-06`, `R6T-05`, `R6A-03`, `R6A-09` |
| R6L-05 | merge finalization | `env TZ=UTC LC_ALL=C LANG=C CCL_STORAGE_PROFILE=storage-v2-opfs CCL_STORAGE_ALLOW_FALLBACK=0 CCL_STORAGE_V2_SYNC_LANE=R6L-05 CCL_STORAGE_V2_SYNC_CASE=merge-finalize node doc/wasm/js/storage-v2-sync-conformance.mjs` | `R6S-07`, `R6T-06`, `R6A-04`, `R6A-09` |
| R6L-06 | failure injection | `env TZ=UTC LC_ALL=C LANG=C CCL_STORAGE_PROFILE=storage-v2-opfs CCL_STORAGE_ALLOW_FALLBACK=0 CCL_STORAGE_V2_SYNC_LANE=R6L-06 CCL_STORAGE_V2_SYNC_CASE=<case_id> CCL_STORAGE_V2_SYNC_INJECT_FAILURE=<RPL06-E*> node doc/wasm/js/storage-v2-sync-conformance.mjs` | `R6T-11`..`R6T-20` |
| R6L-07 | no-fallback policy | `env TZ=UTC LC_ALL=C LANG=C CCL_STORAGE_PROFILE=storage-v2-opfs CCL_STORAGE_ALLOW_FALLBACK=0 CCL_STORAGE_V2_SYNC_LANE=R6L-07 CCL_STORAGE_V2_SYNC_CASE=fallback-fail CCL_STORAGE_V2_SYNC_FORCE_FALLBACK=1 node doc/wasm/js/storage-v2-sync-conformance.mjs` | `R6T-08`, `R6A-08` |
| R6L-08 | aggregate summary lane | `env TZ=UTC LC_ALL=C LANG=C CCL_STORAGE_PROFILE=storage-v2-opfs CCL_STORAGE_ALLOW_FALLBACK=0 CCL_STORAGE_V2_SYNC_LANE=R6L-08 CCL_STORAGE_V2_SYNC_CASE=aggregate-summary node doc/wasm/js/storage-v2-sync-conformance.mjs` | Aggregate `R6A-*` assertions + terminal summary |

### Validation Matrix

| validation_id | lane_id | objective | expected result |
| --- | --- | --- | --- |
| R6V-01 | R6L-01 | deterministic replay ordering | `R6A-06=pass`, stable summary digest |
| R6V-02 | R6L-01 | object transfer integrity | no `RPL06-E002`; object/chunk digests match |
| R6V-03 | R6L-02 | CAS mismatch produces conflict, not overwrite | `R6A-07=pass` |
| R6V-04 | R6L-02 | lease guard enforcement | failing lease path maps to `RPL06-E004` |
| R6V-05 | R6L-03 | conflict record creation | conflict emits `sync_conflict_record_v1` with deterministic `conflict_id` |
| R6V-06 | R6L-04 | merge candidate determinism | candidate digest stable for equivalent inputs |
| R6V-07 | R6L-05 | merge finalization auditability | finalization maps to prior conflict + candidate |
| R6V-08 | R6L-06 | schema failure mapping | first failure code `RPL06-E001` |
| R6V-09 | R6L-06 | CAS failure mapping | first failure code `RPL06-E003` |
| R6V-10 | R6L-06 | merge finalization failure mapping | first failure code `RPL06-E006` |
| R6V-11 | R6L-06 | lifecycle prerequisite failure mapping | first failure code `RPL06-E008` |
| R6V-12 | R6L-06 | rollback/replay consistency failure mapping | first failure code `RPL06-E009` |
| R6V-13 | R6L-07 | no-fallback hard fail mapping | first failure code `RPL06-E007`; run `status=fail` |
| R6V-14 | R6L-08 | aggregate summary correctness | `storage_v2_sync_step2_summary_v1.status=pass` with `allow_fallback=false` |

### Terminal Summary Schema

`storage_v2_sync_step2_summary_v1` required fields:

- `schema_version`, `run_id`, `timestamp_utc`
- `executed_lanes`, `passed_validations`, `failed_validations`
- `first_failure_code`, `allow_fallback`, `status`
- `results_digest`

## Step 3 Output - Initial Evidence Execution (run v1)

Evidence bundle path:

- `doc/wasm/tickets/evidence/rpl-06-step3-2026-02-10/rpl06-20260210-054023Z-50d752af/r6v-results.tsv`
- `doc/wasm/tickets/evidence/rpl-06-step3-2026-02-10/rpl06-20260210-054023Z-50d752af/run-status.tsv`
- `doc/wasm/tickets/evidence/rpl-06-step3-2026-02-10/rpl06-20260210-054023Z-50d752af/storage_v2_sync_step2_summary_v1.json`
- `doc/wasm/tickets/evidence/rpl-06-step3-2026-02-10/rpl06-20260210-054023Z-50d752af/gap-register.md`
- `doc/wasm/tickets/evidence/rpl-06-step3-2026-02-10/rpl06-20260210-054023Z-50d752af/logs/R6V-01.log` .. `doc/wasm/tickets/evidence/rpl-06-step3-2026-02-10/rpl06-20260210-054023Z-50d752af/logs/R6V-14.log`

Run-v1 outcome summary:

| check group | result | evidence |
| --- | --- | --- |
| pass lanes (`R6V-01`..`R6V-07`, `R6V-14`) | pass | `r6v-results.tsv` reports `result=pass` for all listed validations. |
| fail-injection lanes (`R6V-08`..`R6V-13`) | pass | `r6v-results.tsv` reports expected canonical first-failure codes (`RPL06-E001`, `E003`, `E006`, `E008`, `E009`, `E007`) with expected non-zero exits. |
| deterministic digest checks (`R6V-01`, `R6V-06`) | pass | `r6v-results.tsv` notes stable summary/candidate digests across equivalent reruns. |
| terminal summary | pass | `storage_v2_sync_step2_summary_v1.status=pass`, `allow_fallback=false`, `pass_count=14`, `fail_count=0`. |

Run-v1 Step 3 status:

- Status: done
- Gap IDs: none
- Completion basis: full `R6V-01`..`R6V-14` pass coverage with deterministic digest checks and canonical failure mappings.

## Risks and Mitigations

- Risk: merge behavior diverges across runtimes due nondeterministic ordering.
  - Mitigation: enforce canonical ordering and digest assertions in Step 2 lanes.
- Risk: fallback paths silently re-enable legacy sync behavior.
  - Mitigation: explicit `R6T-08` hard-fail semantics with required `RPL06-E007` mapping.
- Risk: insufficient auditability for conflict/merge investigations.
  - Mitigation: require immutable conflict/candidate/finalization records with deterministic IDs.

## Change Log

- 2026-02-10: Initial subplan created and Step 1 sync/merge contract published (`R6S-*`, `R6T-*`, `R6A-*`).
- 2026-02-10: Published Step 2 deterministic lane/validation matrix (`R6L-*`, `R6V-*`) and terminal summary schema `storage_v2_sync_step2_summary_v1`.
- 2026-02-10: Expanded Step 2 lane command templates to executable deterministic sync-conformance commands (`doc/wasm/js/storage-v2-sync-conformance.mjs`) and published Step 2 run contract controls (`CCL_STORAGE_V2_SYNC_*`).
- 2026-02-10: Executed Step 3 run-v1 (`R6V-01`..`R6V-14`), committed evidence bundle (`rpl06-20260210-054023Z-50d752af`), and closed Step 3 with terminal `storage_v2_sync_step2_summary_v1.status=pass`.
