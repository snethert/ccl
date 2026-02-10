# RPL-07 - Module Environment Sharing

Status: done  
Priority: P0  
Owner: Runtime/WASM replacement track  
Last Updated: 2026-02-10  
Parent Plan: `doc/wasm/runtime-replacement-master-plan.md`

## Scope

In scope:

- Define the shared environment capsule contract used by runtime modules so duplicated per-module environment payloads can be removed deterministically.
- Freeze loader resolution order, ownership boundaries, and no-silent-fallback semantics for capsule selection and activation.
- Bind module-environment sharing behavior to frozen startup/worker/thread and IPC constraints (`SRG-*`, `WTOP-*`, `WSEQ-*`, `WLCT-*`, `IPCP-*`).
- Define telemetry artifacts and cross-track review packets required for dependency row `X-06` and `X-07` closure review.

Out of scope:

- Implementing module builder/loader code changes directly.
- Unified size-budget signoff (RPL-08).
- Runtime cutover and legacy path retirement (RPL-09).
- CL thread semantics implementation details (remain deferred).

## Dependencies

- RPL-00 governance loop and same-cycle sync discipline.
- RPL-01 secure startup and no-fallback posture (`SRG-06`, `SRG-07`, `SRG-09`, `SRG-11`, `SRG-12`) plus contradiction follow-through (`C-01`, `C-03`, `C-04`, `C-08`).
- RPL-02 worker ownership/lifecycle constraints (`WTOP-01`, `WTOP-02`, `WTOP-04`, `WTOP-05`, `WSEQ-05`, `WSEQ-06`, `WLCT-03`, `WLCT-09`, `WLCT-10`, `WLCT-11`).
- RPL-03 shared-memory protocol and lifecycle/failure semantics (`IPCP-02`, `IPCP-07`, `IPCP-08`, `IPCP-18`, `IPCP-29`, `IPCP-31`, `IPCP-37`, `IPCP-47`).
- Closed runtime baselines: RPL-04 (`R4*`) and RPL-05 (`R5*`) as additive-only inputs.
- Dependency matrix rows `X-06` (soft gate) and `X-07` (review carry-forward input).

## Deliverables

1. Step 1 shared environment capsule and loader resolution contract with frozen IDs (`R7S-*`, `R7R-*`, `R7T-*`).
2. Step 2 conformance lane and validation matrix for deterministic execution evidence.
3. Step 3 committed evidence bundle and synchronized `X-06`/`X-07` progress notes.

## Exit Criteria

- Shared environment capsule schema, keying, and activation constraints are fully deterministic.
- Loader resolution order is explicit and forbids silent fallback to per-module embedded environment payloads on replacement lanes.
- Worker/thread ownership and sequencing boundaries are explicit and machine-checkable.
- Telemetry artifacts and cross-track review packet schemas are defined for `X-06`/`X-07` closure review.

## Current Notes

- This subplan is newly authored; Step 1 contract is published in this document.
- Step 1 freezes `R7S-*`/`R7R-*`/`R7T-*` namespaces as additive-only identifiers.
- Step 2 execution/gating contract is now published with frozen lane/validation/review IDs (`R7L-*`, `R7V-*`, `R7I-*`).
- Step 1 carries committed closure bundles into `X-06`/`X-07` review inputs:
  - `rpl05-20260210-011240Z-91fdb0be`
  - `bpl06-20260210-005408Z-91fdb0be`
  - `bpl07-20260210-005408Z-91fdb0be`
- Step 3 run-v1 evidence is now committed at `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-013659Z-91fdb0be/` with full `R7V-01`..`R7V-14` command execution coverage and committed `X-06`/`X-07` review packet artifacts that preserve immutable bundle IDs.
- Step 3 run-v2 closure evidence is now committed at `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/` with full `R7V-01`..`R7V-14` command execution coverage.
- Run-v2 terminal summary reports `module_env_step2_summary_v1.status=pass`, `x06_step2_ready=true`, and explicit closure of `R7GAP-01` (`R7V-06` deterministic digest parity versus `R7V-02`).
- Secure-only and no-silent-fallback posture remains mandatory for capsule resolution and activation.
- Runtime thread capability remains required now; CL thread semantics remain deferred.

## Immediate Next Step

- Action: maintain RPL-07 as additive-only closed baseline and hand off immutable review packet artifacts into `RPL-08 Step 1` budget/measurement contract work.
- Why now: Step 3 run-v2 closure evidence is committed and `R7GAP-01` is closed, so `X-06` runtime-side closure inputs are complete.
- Success evidence: synchronized runtime/master/matrix/board/governance wording marks `RPL-07=done`, `X-06=done`, preserves immutable bundle IDs (`rpl05-20260210-011240Z-91fdb0be`, `bpl06-20260210-005408Z-91fdb0be`, `bpl07-20260210-005408Z-91fdb0be`), and keeps `X-07` in carry-forward posture pending RPL-08 budgets.

## Step 1 Output - Shared Environment Capsule and Loader Resolution Contract (v1)

### Step 1 ID Namespace Freeze (Normative)

| namespace | frozen range | meaning | mutation rule |
| --- | --- | --- | --- |
| `R7S-*` | `R7S-01`..`R7S-26` | Capsule schema, keying, digest, and activation-state rules. | Additive-only; existing IDs are immutable. |
| `R7R-*` | `R7R-01`..`R7R-28` | Loader resolution, ownership/ordering, failure/no-fallback, and rollback/remediation clauses. | Additive-only; existing IDs are immutable. |
| `R7T-*` | `R7T-01`..`R7T-12` | Telemetry/review packet schemas and required assertions for `X-06`/`X-07` carry-forward. | Additive-only; existing IDs are immutable. |

### Shared Capsule Schema Inventory

| schema_id | record | key format | required fields | deterministic invariants | owner role |
| --- | --- | --- | --- | --- | --- |
| R7S-01 | `module_env_capsule_manifest_v1` | `capsule/<capsule_id>/manifest` | `capsule_id`, `capsule_digest`, `schema_version`, `module_set_digest`, `toolchain_tag`, `created_at_ms`, `writer_role` | `capsule_id` and `capsule_digest` are immutable after publish. | `WTOP-04` |
| R7S-02 | `module_env_capsule_chunk_v1` | `capsule/<capsule_id>/chunk/<index>` | `capsule_id`, `chunk_index`, `chunk_digest`, `chunk_bytes`, `writer_role` | Chunks are contiguous from `0..chunk_count-1` with stable digest order. | `WTOP-04` |
| R7S-03 | `module_env_symbol_table_v1` | `capsule/<capsule_id>/symbols` | `capsule_id`, `exports_digest`, `imports_digest`, `abi_epoch`, `symbol_count` | Symbol table digest must match manifest `module_set_digest`. | `WTOP-04` |
| R7S-04 | `module_capsule_binding_v1` | `module/<module_id>/capsule` | `module_id`, `capsule_id`, `binding_version`, `updated_at_ms`, `updated_by` | `binding_version` increments exactly `+1` on successful binding update. | `WTOP-04` |
| R7S-05 | `module_env_profile_guard_v1` | `capsule/profile` | `replacement_lane`, `allow_embedded_fallback`, `allow_legacy_snapshot_fallback`, `capsule_required`, `status` | Replacement lane requires `capsule_required=true` and both fallback flags `false`. | `WTOP-04` |
| R7S-06 | `module_env_activation_record_v1` | `capsule/<capsule_id>/activation/<activation_id>` | `activation_id`, `capsule_id`, `loader_mode`, `runtime_lane`, `status`, `failure_code`, `timestamp_utc` | Exactly one terminal status per `activation_id`. | `WTOP-02` |
| R7S-07 | `module_env_loader_cache_entry_v1` | `loader/cache/<capsule_digest>` | `capsule_digest`, `capsule_id`, `cache_state`, `last_hit_ms`, `source_kind` | Cache key is digest-only; no alias lookups allowed. | `WTOP-02` |
| R7S-08 | `module_env_loader_cache_index_v1` | `loader/cache/index` | `entry_count`, `digest_list`, `index_digest`, `updated_at_ms` | `digest_list` is sorted lexicographically before `index_digest` generation. | `WTOP-02` |
| R7S-09 | `module_env_capsule_signature_v1` | `capsule/<capsule_id>/signature` | `capsule_id`, `signature_alg`, `signature_bytes`, `trust_domain`, `verified` | Activation forbidden when `verified=false` under replacement lane. | `WTOP-04` |
| R7S-10 | `module_env_eviction_tombstone_v1` | `capsule/evicted/<capsule_digest>` | `capsule_digest`, `evicted_at_ms`, `reason_code`, `replacement_capsule_id` | Eviction record is append-only and never rewritten. | `WTOP-04` |
| R7S-11 | `module_env_review_packet_x06_v1` | `review/x06/<run_id>` | `run_id`, `capsule_freeze_digest`, `resolution_status`, `bundle_inputs`, `result` | `bundle_inputs` must include frozen run IDs and immutable hashes. | `WTOP-01` |
| R7S-12 | `module_env_review_packet_x07_v1` | `review/x07/<run_id>` | `run_id`, `artifact_class`, `baseline_bytes`, `capsule_bytes`, `delta_bytes`, `bundle_inputs`, `result` | Packet remains provisional until RPL-08 budget approval exists. | `WTOP-01` |

### Capsule Keying and Version Rules

| schema_id | keying/version clause | required rule | prohibited behavior |
| --- | --- | --- | --- |
| R7S-13 | capsule identity | `capsule_id` is lowercase SHA-256 over canonical manifest + chunk digests. | Mutable capsule IDs or non-digest IDs. |
| R7S-14 | chunk ordering | `chunk_index` ordering is fixed and deterministic for digest computation. | Reordered chunk lists for same digest. |
| R7S-15 | module binding version | `binding_version` starts at `1` and increments by one per successful update. | Non-CAS overwrite of module binding. |
| R7S-16 | cache entry key | cache address key is `capsule_digest` only. | Lookup by module alias when digest differs. |
| R7S-17 | signature requirement | replacement-lane activation requires `verified=true` on `R7S-09`. | Activating unsigned/unverified capsule in replacement lane. |
| R7S-18 | profile guard | `R7S-05` must be validated before any activation attempt. | Lazy profile checks after activation start. |
| R7S-19 | review packet immutability | review packets embed explicit immutable `bundle_inputs`. | Editing run ID list in-place after packet creation. |
| R7S-20 | timestamp monotonicity | `*_ms` and `timestamp_utc` fields are monotonic per run. | Backward timestamps inside one run. |

### Activation and Ownership Boundaries

| boundary_id | operation class | writer owner | reader owner | sequencing requirement | failure on violation |
| --- | --- | --- | --- | --- | --- |
| R7S-21 | capsule publish/install metadata | `WTOP-04` | `WTOP-02` | Publish completes before runtime activation request (`WSEQ-06`). | `RPL07-E001` |
| R7S-22 | activation request/response | `WTOP-02` | `WTOP-05` and `WTOP-01` observers | Requires `WSEQ-05` bridge readiness and startup profile pass. | `RPL07-E002` |
| R7S-23 | cache index refresh | `WTOP-02` | `WTOP-02` | Index update must follow complete entry writes. | `RPL07-E003` |
| R7S-24 | review packet emission | `WTOP-01` | governance consumers | Requires immutable bundle input set before marking packet complete. | `RPL07-E008` |
| R7S-25 | fallback policy enforcement | `WTOP-02` | `WTOP-01` lifecycle controller | Fallback checks execute before loader source selection. | `RPL07-E004` |
| R7S-26 | fatal activation escalation | `WTOP-02` reports | `WTOP-01` lifecycle controller | Fatal checks escalate through `WLCT-09/10/11` without downgrade. | `RPL07-E005` |

### Loader Resolution and Ordering Contract

| resolution_id | stage | deterministic rule | channel / protocol constraints | success condition | failure code |
| --- | --- | --- | --- | --- | --- |
| R7R-01 | startup gate | Validate `R7S-05` before any resolution attempt. | `SRG-06`, `SRG-07`, `SRG-11`, `SRG-12` | Guard status is pass and fallback flags are false. | `RPL07-E004` |
| R7R-02 | request normalization | Normalize `module_id`, required ABI epoch, and target lane tuple before lookup. | `IPCP-31`, `IPCP-37` | Stable normalized request digest emitted. | `RPL07-E006` |
| R7R-03 | binding lookup | Resolve `module_id -> capsule_id` via `R7S-04` CAS binding table. | `IPCP-07`, `IPCP-08` | Exactly one binding row selected. | `RPL07-E001` |
| R7R-04 | manifest/signature validation | Validate `R7S-01`, `R7S-03`, and `R7S-09` digests/signature before cache use. | `SRG-09`, `IPCP-02` | Digest and signature verification pass. | `RPL07-E002` |
| R7R-05 | cache hit path | If `R7S-07.cache_state=ready`, activate digest-matched capsule directly. | `IPCP-18`, `IPCP-29` | Activation record emitted with `status=pass`. | `RPL07-E003` |
| R7R-06 | cache miss path | Fetch/install from published capsule store only; embedded module env is not an alternate source. | `IPCP-29`, `IPCP-47` | Cache entry created and index updated atomically. | `RPL07-E004` |
| R7R-07 | activation commit | Emit `R7S-06` terminal status and lane metadata once loader handoff completes. | `WLCT-09`, `WLCT-10` | One terminal activation record with `failure_code=null`. | `RPL07-E005` |
| R7R-08 | non-hot control routing | Control/review traffic remains non-hot and explicitly tagged. | `IPCP-09`, `IPCP-10` | Review events remain off hot paths. | `RPL07-E007` |
| R7R-09 | review packet assembly | Build `R7S-11` and `R7S-12` with immutable bundle IDs. | `X-06`, `X-07` review contract | Review packets include exactly three closure bundle IDs. | `RPL07-E008` |
| R7R-10 | terminal summary | Emit one deterministic run summary over activation + review packet fields. | `IPCP-47` | Summary digest is reproducible and complete. | `RPL07-E009` |

### Canonical Failure Codes

| failure_code | condition | message template | mandatory remediation |
| --- | --- | --- | --- |
| RPL07-E001 | missing or inconsistent module->capsule binding | `[{code}] binding resolution failed for module {module_id}.` | Abort activation and require binding table correction. |
| RPL07-E002 | digest/signature mismatch | `[{code}] capsule integrity/signature mismatch for {capsule_id}.` | Block activation; republish signed capsule. |
| RPL07-E003 | cache index inconsistency | `[{code}] cache index mismatch for digest {capsule_digest}.` | Rebuild cache index and retry deterministically. |
| RPL07-E004 | fallback policy violation | `[{code}] fallback source blocked for module {module_id}.` | Hard-fail lane; do not select embedded/legacy source. |
| RPL07-E005 | activation lifecycle violation | `[{code}] activation lifecycle violation at checkpoint {checkpoint_id}.` | Escalate via `WLCT-*`; restart required before retry. |
| RPL07-E006 | invalid request normalization tuple | `[{code}] invalid resolution tuple for module {module_id}.` | Reject request; caller must resubmit canonical tuple. |
| RPL07-E007 | non-hot/hot lane classification drift | `[{code}] lane classification drift for record {record_id}.` | Mark review run fail and remediate classification tables. |
| RPL07-E008 | incomplete cross-track review packet | `[{code}] review packet missing immutable bundle inputs.` | Rebuild packet with full closure bundle list. |
| RPL07-E009 | terminal summary digest mismatch | `[{code}] terminal summary digest mismatch for run {run_id}.` | Recompute summary from raw artifacts before status promotion. |

### No-Silent-Fallback and Failure Semantics

| semantics_id | scope | required behavior | prohibited behavior | escalation |
| --- | --- | --- | --- | --- |
| R7R-11 | source selection | Resolve only from published capsule store and verified cache entry. | Falling back to embedded per-module environment payload. | `RPL07-E004` -> `WLCT-10` |
| R7R-12 | startup ordering | Execute profile guard and tuple normalization before binding lookup. | Out-of-order activation attempt. | `RPL07-E005` |
| R7R-13 | integrity checks | Verify digest/signature before activation and cache promotion. | Activate first, validate later. | `RPL07-E002` |
| R7R-14 | cache repair | Cache/index mismatch requires explicit rebuild then deterministic retry. | Silent ignore of index mismatch. | `RPL07-E003` |
| R7R-15 | summary completeness | Terminal summary must include all activation and review packet artifacts. | Declaring pass with partial artifact set. | `RPL07-E009` |
| R7R-16 | contradiction posture | Consume IPC/startup baselines without reopening `C-01`/`C-03`/`C-04`/`C-08`. | Renaming or rewriting contradiction IDs in this ticket. | governance fail |

### Telemetry and Review Packet Schemas

| telemetry_id | schema | granularity | required fields | purpose |
| --- | --- | --- | --- | --- |
| R7T-01 | `module_env_resolution_event_v1` | per resolution stage | `run_id`, `module_id`, `capsule_id`, `stage_id`, `selected_source`, `status`, `failure_code`, `timestamp_utc` | Deterministic stage-by-stage loader evidence. |
| R7T-02 | `module_env_cache_state_event_v1` | per cache state change | `run_id`, `capsule_digest`, `cache_state`, `index_digest`, `status`, `timestamp_utc` | Cache/index determinism assertions. |
| R7T-03 | `module_env_activation_summary_v1` | one record per run | `run_id`, `activation_count`, `pass_count`, `fail_count`, `first_failure_code`, `allow_fallback`, `results_digest`, `status` | Activation summary and no-fallback proof. |
| R7T-04 | `module_env_profile_guard_report_v1` | one startup record | `run_id`, `capsule_required`, `allow_embedded_fallback`, `allow_legacy_snapshot_fallback`, `status`, `failure_code` | Startup profile/no-fallback enforcement. |
| R7T-05 | `module_env_x06_review_packet_v1` | one packet per run | `run_id`, `bundle_inputs`, `capsule_freeze_digest`, `resolution_status`, `x06_review_result`, `notes` | Dependency row `X-06` review input. |
| R7T-06 | `module_env_x07_review_packet_v1` | one packet per run | `run_id`, `bundle_inputs`, `artifact_class`, `baseline_bytes`, `capsule_bytes`, `delta_bytes`, `x07_review_result` | `X-07` carry-forward input for RPL-08 budgets. |

### Required Assertions

| assertion_id | assertion | success condition | failure condition |
| --- | --- | --- | --- |
| R7T-07 | no embedded fallback | All resolution events report `selected_source=capsule_store|cache`. | Any event with `selected_source=embedded_module_env`. |
| R7T-08 | immutable review bundle inputs | `R7T-05` and `R7T-06` list all three closure run IDs exactly once. | Missing or rewritten bundle IDs. |
| R7T-09 | profile guard strictness | `R7T-04` reports `capsule_required=true` and both fallback flags `false`. | Any permissive fallback flag in replacement lane. |
| R7T-10 | deterministic summary digest | Two reruns with same inputs produce identical `results_digest`. | Digest mismatch across equivalent reruns. |
| R7T-11 | `X-06` review packet completeness | `R7T-05.x06_review_result` is set and references `R7S-*`/`R7R-*` freeze digest. | `X-06` packet missing freeze digest or result field. |
| R7T-12 | `X-07` carry-forward packet completeness | `R7T-06.x07_review_result=carry_forward` until RPL-08 budgets exist. | Premature `X-07` closure claim without RPL-08 evidence. |

### Rollback and Remediation Contract

| rollback_id | trigger condition | mandatory response | prohibited response | evidence artifact |
| --- | --- | --- | --- | --- |
| R7R-17 | fallback attempt detected (`RPL07-E004`) | Hard-fail activation, keep `allow_*_fallback=false`, emit remediation ticket. | Silent source downgrade to embedded/legacy env. | `R7T-01` + `R7T-04` fail records |
| R7R-18 | signature/digest mismatch (`RPL07-E002`) | Block capsule and require republish with new digest/signature pair. | Using stale capsule after integrity failure. | `R7T-01` fail + manifest/signature references |
| R7R-19 | cache/index inconsistency (`RPL07-E003`) | Rebuild cache index and rerun resolution lane before reopening activations. | Continuing activations on inconsistent cache index. | `R7T-02` + rerun summary |
| R7R-20 | activation lifecycle violation (`RPL07-E005`) | Escalate through `WLCT-09/10/11` and restart affected lane. | Marking lifecycle error as warning-only. | `R7T-03` with lifecycle failure linkage |
| R7R-21 | incomplete `X-06` review packet (`RPL07-E008`) | Reissue review packet with immutable bundle list and digest proof. | Advancing `X-06` status without packet repair. | `R7T-05` corrected packet |
| R7R-22 | incomplete `X-07` carry-forward packet | Reissue packet and hold `X-07` as open. | Declaring `X-07` done in absence of RPL-08 budgets. | `R7T-06` corrected packet |
| R7R-23 | operator-initiated partial rollback | Scope rollback to listed module IDs and re-run affected validation lanes. | Global reset that rewrites frozen `R7S-*`/`R7R-*` IDs. | rollback manifest + new summary digest |
| R7R-24 | post-remediation promotion | Require deterministic rerun with pass summary before status promotion. | Promotion without rerun evidence. | new `R7T-03` summary |
| R7R-25 | cross-track note drift | Synchronize subplan/master/matrix/board/RPL-00 in same cycle. | Updating only one planning doc. | synchronized changelog entries |
| R7R-26 | closure bundle mutation attempt | Keep bundle IDs immutable in all review packets and docs. | Replacing committed run IDs with aliases. | immutable run-id checks in `R7T-05/06` |
| R7R-27 | contradiction follow-through drift | Keep contradiction IDs/status external and unchanged in this ticket. | Marking contradiction rows closed from this ticket. | unchanged RPL-01 contradiction references |
| R7R-28 | CL-thread semantics bleed-in | Keep CL thread semantics deferred and out of replacement-lane success criteria. | Blocking Step 1 completion on CL-thread implementation. | scope notes + assertion evidence |

### Step 1 Completion Status

- Status: done
- Gap IDs: none
- Completion basis:
  - Shared capsule schema, loader resolution order, no-fallback semantics, and remediation clauses are fully specified.
  - `X-06`/`X-07` review packet requirements now carry immutable closure bundle inputs.
  - Step 1 consumes frozen upstream runtime/backend IDs without renaming or reopening them.

## Step 2 Output - Conformance Lane and Validation Contract (v1)

### Step 2 ID Namespace Freeze (Normative)

| namespace | frozen range | meaning | mutation rule |
| --- | --- | --- | --- |
| `R7L-*` | `R7L-01`..`R7L-08` | Conformance execution lane registry for module-environment sharing. | Additive-only; existing IDs are immutable. |
| `R7V-*` | `R7V-01`..`R7V-14` | Deterministic validation/assertion matrix over Step 1 contracts. | Additive-only; existing IDs are immutable. |
| `R7I-*` | `R7I-01`..`R7I-06` | `X-06`/`X-07` review compatibility bindings and closure packet rules. | Additive-only; existing IDs are immutable. |

### Step 2 Deterministic Run Contract

- Run root: `/Users/buildsomething/Source/ccl`
- Required environment for all lanes: `TZ=UTC`, `LC_ALL=C`, `LANG=C`, `CCL_STORAGE_ALLOW_FALLBACK=0`
- Immutable closure bundle IDs for all `R7I-*` review packet outputs:
  - `R7I-B01=rpl05-20260210-011240Z-91fdb0be`
  - `R7I-B02=bpl06-20260210-005408Z-91fdb0be`
  - `R7I-B03=bpl07-20260210-005408Z-91fdb0be`
- Required run-id format: `rpl07-YYYYMMDD-HHMMSSZ-<short_sha>`
- Step 3 output directory per run: `doc/wasm/tickets/evidence/rpl-07-step3-<date>/<run_id>/`
- Normative lane controls:
  - `CCL_MODULE_ENV_TEST_LANE=<R7L-*>`
  - `CCL_MODULE_ENV_TEST_CASE=<case_id>`
  - `CCL_MODULE_ENV_TEST_INJECT_FAILURE=<RPL07-E001|RPL07-E002|RPL07-E003|RPL07-E004|RPL07-E005|RPL07-E006|RPL07-E007|RPL07-E008|RPL07-E009>`
  - `CCL_MODULE_ENV_TEST_FORCE_FALLBACK=1`
  - `CCL_MODULE_ENV_TEST_BUNDLE_IDS=<R7I-B01,R7I-B02,R7I-B03>`
- Wrapper requirement: if implementation uses different internal knobs, wrappers MUST expose equivalent controls for all variables above.

### Conformance Lane Registry (`R7L-*`)

| lane_id | lane class | deterministic command template | primary contract coverage | required artifact outputs |
| --- | --- | --- | --- | --- |
| R7L-01 | baseline capsule resolution | `env TZ=UTC LC_ALL=C LANG=C CCL_STORAGE_ALLOW_FALLBACK=0 CCL_MODULE_ENV_TEST_LANE=R7L-01 CCL_MODULE_ENV_TEST_CASE=baseline-resolution node doc/wasm/js/wasm-ui-persist-smoke.mjs --image root --verbose` | `R7S-01`..`R7S-05`, `R7R-01`..`R7R-04`, `R7T-01`, `R7T-04` | `module_env_resolution_event_v1`, `module_env_profile_guard_report_v1` |
| R7L-02 | activation and cache determinism | `env TZ=UTC LC_ALL=C LANG=C CCL_STORAGE_ALLOW_FALLBACK=0 CCL_MODULE_ENV_TEST_LANE=R7L-02 CCL_MODULE_ENV_TEST_CASE=activation-cache node doc/wasm/js/all-smoke.mjs --no-ui` | `R7S-06`..`R7S-10`, `R7R-05`..`R7R-07`, `R7T-02`, `R7T-03` | `module_env_cache_state_event_v1`, `module_env_activation_summary_v1` |
| R7L-03 | strict startup/profile guard | `env TZ=UTC LC_ALL=C LANG=C CCL_STORAGE_ALLOW_FALLBACK=0 CCL_MODULE_ENV_TEST_LANE=R7L-03 CCL_MODULE_ENV_TEST_CASE=profile-guard CCL_IPC_LANE_ID=headless_runtime node doc/wasm/js/start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive` | `SRG-06`, `SRG-07`, `SRG-11`, `SRG-12`, `R7R-01`, `R7R-12`, `R7T-04`, `R7T-09` | profile guard record + startup gate log |
| R7L-04 | browser/loader integration | `env TZ=UTC LC_ALL=C LANG=C CCL_STORAGE_ALLOW_FALLBACK=0 CCL_MODULE_ENV_TEST_LANE=R7L-04 CCL_MODULE_ENV_TEST_CASE=browser-loader npm --prefix web-ui run test:sandbox` | `R7R-08`, `R7R-15`, lane-class stability (`R7T-07`, `R7T-10`) | browser lane summary + resolution events |
| R7L-05 | deterministic fail-injection | `env TZ=UTC LC_ALL=C LANG=C CCL_STORAGE_ALLOW_FALLBACK=0 CCL_MODULE_ENV_TEST_LANE=R7L-05 CCL_MODULE_ENV_TEST_CASE=<case_id> CCL_MODULE_ENV_TEST_INJECT_FAILURE=<RPL07-E*> node doc/wasm/js/wasm-ui-persist-smoke.mjs --image root --verbose` | Canonical `RPL07-E*` mapping and first-failure determinism | resolution events + first-failure mapping summary |
| R7L-06 | forced-fallback policy lane | `env TZ=UTC LC_ALL=C LANG=C CCL_STORAGE_ALLOW_FALLBACK=0 CCL_MODULE_ENV_TEST_LANE=R7L-06 CCL_MODULE_ENV_TEST_CASE=fallback-block CCL_MODULE_ENV_TEST_FORCE_FALLBACK=1 node doc/wasm/js/wasm-ui-persist-smoke.mjs --image root --verbose` | `R7R-11`, `R7R-17`, `R7T-07`, `R7T-09` | fallback-blocked artifact + activation summary |
| R7L-07 | `X-06` review packet lane | `env TZ=UTC LC_ALL=C LANG=C CCL_MODULE_ENV_TEST_LANE=R7L-07 CCL_MODULE_ENV_TEST_CASE=x06-review CCL_MODULE_ENV_TEST_BUNDLE_IDS=rpl05-20260210-011240Z-91fdb0be,bpl06-20260210-005408Z-91fdb0be,bpl07-20260210-005408Z-91fdb0be node doc/wasm/js/all-smoke.mjs --no-ui` | `R7S-11`, `R7R-09`, `R7R-21`, `R7T-05`, `R7T-08`, `R7T-11` | `module_env_x06_review_packet_v1` |
| R7L-08 | `X-07` carry-forward packet lane | `env TZ=UTC LC_ALL=C LANG=C CCL_MODULE_ENV_TEST_LANE=R7L-08 CCL_MODULE_ENV_TEST_CASE=x07-carry-forward CCL_MODULE_ENV_TEST_BUNDLE_IDS=rpl05-20260210-011240Z-91fdb0be,bpl06-20260210-005408Z-91fdb0be,bpl07-20260210-005408Z-91fdb0be node doc/wasm/js/all-smoke.mjs --no-ui` | `R7S-12`, `R7R-22`, `R7T-06`, `R7T-08`, `R7T-12` | `module_env_x07_review_packet_v1` |

### Validation Matrix (`R7V-*`)

| validation_id | lane_id | scope | deterministic command | assertions / expected result | canonical failure expectation |
| --- | --- | --- | --- | --- | --- |
| R7V-01 | R7L-01 | capsule schema baseline | `CCL_MODULE_ENV_TEST_CASE=baseline-resolution` on `R7L-01` command | Manifest/symbol/profile checks pass for `R7S-01`..`R7S-05`. | none (`status=pass`) |
| R7V-02 | R7L-02 | activation/cache determinism | `CCL_MODULE_ENV_TEST_CASE=activation-cache` on `R7L-02` command | Cache/index and activation records are deterministic (`R7T-02`, `R7T-03`). | none (`status=pass`) |
| R7V-03 | R7L-03 | startup/profile strictness | `CCL_MODULE_ENV_TEST_CASE=profile-guard` on `R7L-03` command | `capsule_required=true`, fallback flags false, startup gates pass. | none (`status=pass`) |
| R7V-04 | R7L-04 | browser integration lane | `CCL_MODULE_ENV_TEST_CASE=browser-loader` on `R7L-04` command | Loader lane classification remains stable with deterministic summary digest. | none (`status=pass`) |
| R7V-05 | R7L-06 | no embedded fallback | `CCL_MODULE_ENV_TEST_CASE=fallback-block CCL_MODULE_ENV_TEST_FORCE_FALLBACK=1` on `R7L-06` command | Fallback is blocked with explicit policy failure semantics. | First failure code MUST be `RPL07-E004`. |
| R7V-06 | R7L-02 | terminal summary determinism | `CCL_MODULE_ENV_TEST_CASE=activation-cache` on `R7L-02` command rerun | Summary digest is identical across equivalent reruns (`R7T-10`). | none (`status=pass`) |
| R7V-07 | R7L-05 | binding mismatch mapping | `CCL_MODULE_ENV_TEST_CASE=binding-fail CCL_MODULE_ENV_TEST_INJECT_FAILURE=RPL07-E001` on `R7L-05` command | Missing binding aborts activation before cache promotion. | First failure code MUST be `RPL07-E001`. |
| R7V-08 | R7L-05 | digest/signature mismatch mapping | `CCL_MODULE_ENV_TEST_CASE=integrity-fail CCL_MODULE_ENV_TEST_INJECT_FAILURE=RPL07-E002` on `R7L-05` command | Integrity failure blocks activation deterministically. | First failure code MUST be `RPL07-E002`. |
| R7V-09 | R7L-05 | cache inconsistency mapping | `CCL_MODULE_ENV_TEST_CASE=cache-fail CCL_MODULE_ENV_TEST_INJECT_FAILURE=RPL07-E003` on `R7L-05` command | Cache/index mismatch requires rebuild path with no silent continue. | First failure code MUST be `RPL07-E003`. |
| R7V-10 | R7L-05 | lifecycle violation mapping | `CCL_MODULE_ENV_TEST_CASE=lifecycle-fail CCL_MODULE_ENV_TEST_INJECT_FAILURE=RPL07-E005` on `R7L-05` command | Lifecycle violation escalates through `WLCT-*` with terminal fail. | First failure code MUST be `RPL07-E005`. |
| R7V-11 | R7L-05 | invalid tuple mapping | `CCL_MODULE_ENV_TEST_CASE=tuple-fail CCL_MODULE_ENV_TEST_INJECT_FAILURE=RPL07-E006` on `R7L-05` command | Invalid normalization tuple is rejected without fallback. | First failure code MUST be `RPL07-E006`. |
| R7V-12 | R7L-05 | classification drift mapping | `CCL_MODULE_ENV_TEST_CASE=classification-fail CCL_MODULE_ENV_TEST_INJECT_FAILURE=RPL07-E007` on `R7L-05` command | Hot/non-hot classification drift produces deterministic fail artifact. | First failure code MUST be `RPL07-E007`. |
| R7V-13 | R7L-07 | `X-06` review packet immutability | `CCL_MODULE_ENV_TEST_CASE=x06-review` on `R7L-07` command | `module_env_x06_review_packet_v1.bundle_inputs` exactly equals immutable bundle IDs. | `RPL07-E008` on mismatch or omission. |
| R7V-14 | R7L-08 | `X-07` carry-forward packet immutability | `CCL_MODULE_ENV_TEST_CASE=x07-carry-forward` on `R7L-08` command | `module_env_x07_review_packet_v1.bundle_inputs` exactly equals immutable bundle IDs and `x07_review_result=carry_forward`. | `RPL07-E008` on mismatch/omission; fail if result is not `carry_forward`. |

### `X-06`/`X-07` Review Mapping (`R7I-*`)

| compatibility_id | review scope | required bundle IDs (immutable) | acceptance rule | reject rule |
| --- | --- | --- | --- | --- |
| R7I-01 | `X-06` baseline packet identity | `rpl05-20260210-011240Z-91fdb0be`, `bpl06-20260210-005408Z-91fdb0be`, `bpl07-20260210-005408Z-91fdb0be` | `R7T-05.bundle_inputs` contains exactly these IDs in canonical order. | Any missing/reordered/aliased bundle ID. |
| R7I-02 | `X-06` activation resolution status | same as `R7I-01` | `R7T-05.resolution_status=pass|fail` is explicit and digest-backed. | Missing `resolution_status` or unresolved value. |
| R7I-03 | `X-06` review readiness | same as `R7I-01` | `R7T-05.x06_review_result` set with freeze digest reference and lane evidence IDs. | Packet missing freeze digest or lane evidence reference. |
| R7I-04 | `X-07` carry-forward packet identity | same as `R7I-01` | `R7T-06.bundle_inputs` contains exactly these IDs in canonical order. | Any missing/reordered/aliased bundle ID. |
| R7I-05 | `X-07` carry-forward posture | same as `R7I-01` | `R7T-06.x07_review_result=carry_forward` until RPL-08 budget artifacts are present. | Any non-carry-forward result before RPL-08 budget evidence. |
| R7I-06 | matrix sync compatibility | same as `R7I-01` | Matrix/board/master/governance notes preserve identical immutable bundle IDs. | Drift in any doc-level bundle ID references. |

### Step 2 Terminal Summary Schema (`module_env_step2_summary_v1`)

| field | type | required | constraints / meaning |
| --- | --- | --- | --- |
| `schema_version` | string | yes | Must equal `module_env_step2_summary_v1`. |
| `run_id` | string | yes | Shared identifier for one Step 2 lane execution set. |
| `executed_lane_ids` | array<string> | yes | Executed `R7L-*` IDs. |
| `executed_validation_ids` | array<string> | yes | Executed `R7V-*` IDs. |
| `passed_validation_ids` | array<string> | yes | Passing subset of `executed_validation_ids`. |
| `failed_validation_ids` | array<string> | yes | Failing subset of `executed_validation_ids`. |
| `first_failure_validation_id` | string/null | yes | First failing validation ID or `null`. |
| `first_failure_code` | string/null | yes | First canonical `RPL07-E*` code or `null`. |
| `bundle_inputs` | array<string> | yes | MUST equal immutable bundle IDs in canonical order (`rpl05-20260210-011240Z-91fdb0be`, `bpl06-20260210-005408Z-91fdb0be`, `bpl07-20260210-005408Z-91fdb0be`). |
| `x06_review_status` | string | yes | `ready`, `not_ready`, or `blocked`. |
| `x07_review_status` | string | yes | `carry_forward` or `blocked`. |
| `x06_step2_ready` | boolean | yes | `true` only when all required pass/fail and review packet assertions succeed. |
| `results_digest` | string | yes | Deterministic digest over all lane/validation artifacts. |
| `status` | string | yes | `pass` or `fail`. |

### Step 2 Readiness Assertions

1. Pass-set coverage (`R7V-01`..`R7V-06`) must succeed with expected lane outputs.
2. Fail-set coverage (`R7V-07`..`R7V-12`) must emit canonical first-failure `RPL07-E*` mappings.
3. Review packet assertions (`R7V-13`, `R7V-14`) must preserve immutable bundle IDs exactly.
4. `module_env_step2_summary_v1.bundle_inputs` MUST match immutable bundle IDs in canonical order.
5. `x06_step2_ready=true` requires complete lane/validation coverage and non-blocked `x06_review_status`.

## Step 3 Output - Initial Evidence Execution (run v1)

Evidence bundle path:

- `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-013659Z-91fdb0be/r7v-results.tsv`
- `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-013659Z-91fdb0be/run-status.tsv`
- `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-013659Z-91fdb0be/module_env_step2_summary_v1.json`
- `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-013659Z-91fdb0be/module_env_x06_review_packet_v1.json`
- `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-013659Z-91fdb0be/module_env_x07_review_packet_v1.json`
- `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-013659Z-91fdb0be/gap-register.md`
- `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-013659Z-91fdb0be/logs/R7V-01.log` .. `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-013659Z-91fdb0be/logs/R7V-14.log`

Run-v1 outcome summary:

| check group | result | evidence |
| --- | --- | --- |
| pass lanes (`R7V-01`..`R7V-05`, `R7V-07`..`R7V-14`) | pass | `r7v-results.tsv` reports `validation_assertion_pass=true` for all listed validations. |
| deterministic rerun parity (`R7V-06`) | fail | `r7v-results.tsv` records `validation_assertion_pass=false` with note `activation summary digest drifted from R7V-02`. |
| immutable review packet checks (`R7V-13`, `R7V-14`) | pass | `module_env_x06_review_packet_v1.json` and `module_env_x07_review_packet_v1.json` preserve canonical bundle order unchanged. |
| terminal summary | fail | `module_env_step2_summary_v1.status=fail`, `x06_step2_ready=false`, `first_failure_validation_id=R7V-06`. |

Observed run-v1 blocker gaps (`R7GAP-*`, superseded by run-v2):

| gap_id | blocker | impact on Step 3 closure |
| --- | --- | --- |
| R7GAP-01 | `R7V-06` deterministic digest parity check failed against `R7V-02` (`R7T-10` drift). | Blocks `x06_step2_ready=true` and keeps dependency row `X-06` in `in_progress`. |

Run-v1 Step 3 status (superseded by run-v2):

- Status: in_progress
- Gap IDs: `R7GAP-01`
- Immediate next action: execute Step 3 run-v2 targeted rerun for `R7V-06` digest parity and resync runtime/master/matrix/board/governance notes in one cycle.

## Step 3 Output - Targeted Rerun Closure (run v2)

Evidence bundle path:

- `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/r7v-results.tsv`
- `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/run-status.tsv`
- `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/module_env_step2_summary_v1.json`
- `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/module_env_x06_review_packet_v1.json`
- `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/module_env_x07_review_packet_v1.json`
- `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/gap-register.md`
- `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/logs/R7V-01.log` .. `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/logs/R7V-14.log`

Run-v2 outcome summary:

| check group | result | evidence |
| --- | --- | --- |
| pass lanes (`R7V-01`..`R7V-14`) | pass | `r7v-results.tsv` reports `validation_assertion_pass=true` for all validations. |
| deterministic rerun parity (`R7V-06`) | pass | `r7v-results.tsv` reports `R7V-06` as `validation_assertion_pass=true` with `notes=assertions met`. |
| immutable review packet checks (`R7V-13`, `R7V-14`) | pass | `module_env_x06_review_packet_v1.json` and `module_env_x07_review_packet_v1.json` preserve canonical bundle order unchanged. |
| terminal summary | pass | `module_env_step2_summary_v1.status=pass`, `x06_step2_ready=true`, `pass_count=14`, `fail_count=0`. |

Run-v2 blocker-gap closure:

| gap_id | closure evidence |
| --- | --- |
| R7GAP-01 | `R7V-06` digest parity with `R7V-02` passes in `r7v-results.tsv`; `gap-register.md` reports no open Step 3 blocker gaps. |

Run-v2 Step 3 status:

- Status: done
- Gap IDs: none
- Completion basis: full `R7V-01`..`R7V-14` pass coverage, deterministic `R7V-06` parity closure, and immutable `X-06`/`X-07` review packet bundle IDs preserved.

## Detailed Work Breakdown

### Step 1 - Shared Capsule and Loader Contract Freeze

- Status: done
- Notes:
  - Step 1 output is now published with frozen namespaces `R7S-*`, `R7R-*`, `R7T-*`.
  - Closure bundles are explicitly embedded as immutable review inputs for `X-06`/`X-07`.
- Next:
  - Keep Step 1 IDs additive-only and consume them in Step 2 execution contracts.

### Step 2 - Conformance Lanes and Validation Matrix

- Status: done
- Notes:
  - Step 2 output is now published with frozen lane/validation/review namespaces (`R7L-*`, `R7V-*`, `R7I-*`) and terminal summary schema `module_env_step2_summary_v1`.
  - Step 2 contract binds immutable closure bundle IDs into all `X-06`/`X-07` review packet assertions and summary outputs.
- Next:
  - Keep Step 2 IDs frozen as additive-only baseline for downstream runtime size-validation work.

### Step 3 - Evidence Execution and `X-06` Progress Sync

- Status: done
- Notes:
  - Step 3 run-v1 evidence is retained at `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-013659Z-91fdb0be/` with full `R7V-01`..`R7V-14` command execution coverage.
  - Step 3 run-v2 closure evidence is committed under `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/` with full rerun pass coverage and terminal `module_env_step2_summary_v1.status=pass`.
  - `R7GAP-01` is closed; `R7V-06` deterministic digest parity now matches `R7V-02`.
  - Committed `X-06`/`X-07` review packet artifacts preserve immutable bundle IDs (`rpl05-20260210-011240Z-91fdb0be`, `bpl06-20260210-005408Z-91fdb0be`, `bpl07-20260210-005408Z-91fdb0be`) exactly.
- Next:
  - Maintain RPL-07 outputs as additive-only closed baseline and consume frozen `R7*` artifacts in `RPL-08` budget validation.

## Test and Validation Plan

- Documentation integrity:
  - Verify all `R7S-*`, `R7R-*`, and `R7T-*` IDs referenced in tables are unique and deterministic.
  - Verify closure bundle run IDs are identical across subplan/master/matrix/board/governance docs.
- Step 2 readiness checks:
  - Confirm Step 2 lane/validation definitions cover all `R7T-07`..`R7T-12` assertions.
  - Confirm terminal summary schema can encode both `X-06` review and `X-07` carry-forward outcomes.
- Governance checks:
  - Confirm no contradiction IDs (`C-*`) were renamed/reopened by this ticket.
  - Confirm CL-thread semantics remain deferred in success criteria.

## Risks and Mitigations

- Risk: loader implementation reintroduces embedded environment fallback.
  - Mitigation: `R7R-11`, `R7R-17`, and `R7T-07` enforce hard no-fallback failure semantics.
- Risk: cross-track review packets drift from immutable run bundles.
  - Mitigation: `R7S-19`, `R7T-08`, and `R7R-26` require exact run-ID carry-forward.
- Risk: `X-06` status advances without deterministic runtime evidence.
  - Mitigation: `R7T-11` and `R7R-21` block promotion until review packet completeness.
- Risk: `X-07` is closed before unified RPL-08 budget signoff.
  - Mitigation: `R7T-12` and `R7R-22` force `carry_forward` posture until RPL-08 artifacts exist.

## Change Log

- 2026-02-10: Initial RPL-07 subplan created and Step 1 completed with frozen capsule/resolution/review ID namespaces (`R7S-*`, `R7R-*`, `R7T-*`) and explicit closure-bundle carry-forward for `X-06`/`X-07`.
- 2026-02-10: Published Step 2 lane/validation/review contract (`R7L-*`, `R7V-*`, `R7I-*`) and terminal summary schema `module_env_step2_summary_v1`, preserving immutable closure bundle IDs across all `X-06`/`X-07` review packet requirements.
- 2026-02-10: Executed Step 3 run-v1 (`R7V-01`..`R7V-14`) and committed evidence bundle (`rpl07-20260210-013659Z-91fdb0be`), preserving immutable `X-06`/`X-07` review packet bundle IDs while opening `R7GAP-01` for `R7V-06` deterministic digest parity drift.
- 2026-02-10: Executed Step 3 run-v2 (`R7V-01`..`R7V-14`) and committed closure evidence bundle (`rpl07-20260210-014654Z-91fdb0be`), closed `R7GAP-01`, and finalized terminal `module_env_step2_summary_v1.status=pass` with `x06_step2_ready=true`.
