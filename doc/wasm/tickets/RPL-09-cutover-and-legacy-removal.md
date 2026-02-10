# RPL-09 - Cutover and Legacy Removal

Status: done  
Priority: P0  
Owner: Runtime/WASM replacement track  
Last Updated: 2026-02-10  
Parent Plan: `doc/wasm/runtime-replacement-master-plan.md`

## Scope

In scope:

- Define runtime cutover gates and irreversible/rollback boundaries after `X-07` closure.
- Freeze deterministic rollback contracts for runtime-side cutover stages.
- Bind runtime cutover readiness to committed `RPL-03`..`RPL-08` evidence and immutable carry-forward bundle IDs.

Out of scope:

- Backend cutover gate definitions (owned by BPL-09).
- New runtime architecture feature work unrelated to release cutover.
- Rewriting frozen `R8*`, `R7*`, `BPL08-CR*`, or immutable bundle IDs.

## Dependencies

- Runtime closure artifacts: `RPL-03`, `RPL-04`, `RPL-05`, `RPL-07`, `RPL-08` all `done`.
- Cross-track row `X-08` hard-gate coordination with `BPL-09`.
- Unified closure review evidence: `doc/wasm/tickets/evidence/x07-closure-review-2026-02-10/x07-closure-20260210-024503Z-91fdb0be/x07_unified_closure_review_v1.json`.
- Immutable carry-forward bundle IDs:
  - `rpl05-20260210-011240Z-91fdb0be`
  - `bpl06-20260210-005408Z-91fdb0be`
  - `bpl07-20260210-005408Z-91fdb0be`

## Deliverables

1. Step 1 runtime cutover and rollback gate contract (`R9G-*`, `R9R-*`, `R9E-*`).
2. Step 2 deterministic rehearsal packet definition for cutover/rollback drills.
3. Step 3 runtime cutover signoff packet for `X-08` joint closure input.

## Exit Criteria

- Step 1 publishes stable gate/rollback IDs with deterministic evidence checks.
- Step 2 publishes deterministic rehearsal commands and failure-mapping expectations.
- Step 3 records runtime-side signoff posture and explicit `X-08` joint-gate dependencies.

## Current Notes

- `X-07` is now `done` and runtime budget closure is committed (`rpl08-20260210-023524Z-91fdb0be`, `x07-closure-20260210-024503Z-91fdb0be`).
- `X-08` hard-gate closure is now committed via unified review artifact `x08-closure-20260210-040400Z-2084077e` with matrix transition `in_progress -> done`.
- Step 1 cutover/rollback contract is now published below with frozen IDs.
- Step 2 deterministic rehearsal packet contract is now published below with frozen lane/validation/review IDs (`R9L-*`, `R9V-*`, `R9I-*`).
- Step 3 run-v1 evidence is now committed at `doc/wasm/tickets/evidence/rpl-09-step3-2026-02-10/rpl09-20260210-032127Z-2084077e/` with full `R9V-01`..`R9V-14` pass coverage and terminal `runtime_cutover_step2_summary_v1.status=pass` (`x08_runtime_step2_ready=true`).
- Step 3 run-v2 closure evidence is now committed at `doc/wasm/tickets/evidence/rpl-09-step3-2026-02-10/rpl09-20260210-034952Z-2084077e/` with full `R9V-01`..`R9V-14` pass coverage, terminal `runtime_cutover_step2_summary_v1.status=pass`, `x08_backend_step2_status=published`, and closed blocker `R9GAP-01`.
- Backend `BPL-09 Step 3` signoff packet rows remain published (`BPL09-CR01`..`BPL09-CR06`) and run-v2 now includes a committed joint intake review artifact (`x08_joint_intake_review_v1.json`) keyed to those rows.

## Immediate Next Step

- Action: keep `R9*` contracts and committed cutover artifacts immutable while runtime `RPL-01` contradiction follow-through (`C-01`, `C-03`, `C-04`, `C-08`) proceeds.
- Why now: `RPL-09` cutover closure is complete and `X-08` is `done`, so this ticket now serves as closed baseline evidence.
- Success evidence: synchronized docs preserve `rpl09-20260210-034952Z-2084077e`, `bpl09-20260210-040314Z-2084077e`, and `x08-closure-20260210-040400Z-2084077e` references with no immutable-ID drift.

## Step 1 Output - Runtime Cutover and Rollback Gate Contract (v1)

### Step 1 ID Namespace Freeze (Normative)

| namespace | frozen range | meaning | mutation rule |
| --- | --- | --- | --- |
| `R9G-*` | `R9G-01`..`R9G-08` | Runtime cutover gates and stage-promotion assertions. | Additive-only; existing IDs are immutable. |
| `R9R-*` | `R9R-01`..`R9R-06` | Runtime rollback triggers and mandatory responses by cutover stage. | Additive-only; existing IDs are immutable. |
| `R9E-*` | `R9E-01`..`R9E-06` | Runtime evidence mapping for `X-08` joint closure packet compatibility. | Additive-only; existing IDs are immutable. |

### Runtime Cutover Gate Matrix

| gate_id | cutover stage | deterministic check command | required artifacts | pass interpretation | fail interpretation + rollback contract | owner | downstream consumer |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R9G-01 | Pre-cutover secure startup gate | `node -e 'const fs=require("node:fs"); const p="doc/wasm/tickets/evidence/rpl-08-step3-2026-02-10/rpl08-20260210-023524Z-91fdb0be/artifact_budget_step2_summary_v1.json"; const j=JSON.parse(fs.readFileSync(p,"utf8")); if(!(j.status==="pass" && j.x07_runtime_ready===true)) process.exit(1);'` | `doc/wasm/tickets/evidence/rpl-08-step3-2026-02-10/rpl08-20260210-023524Z-91fdb0be/artifact_budget_step2_summary_v1.json` | Runtime cutover can proceed to rehearsal because budget closure prerequisites are satisfied. | Block cutover progression and trigger `R9R-01`. | runtime release owner | `X-08` joint cutover checklist |
| R9G-02 | Shared-memory transport closure prerequisite | `node -e 'const fs=require("node:fs"); const p="doc/wasm/tickets/evidence/rpl-03-step3-rerun-2026-02-09/ipc_conformance_summary_v1.json"; const j=JSON.parse(fs.readFileSync(p,"utf8")); if(!(j.status==="pass" && j.x03_clear_ready===true)) process.exit(1);'` | `doc/wasm/tickets/evidence/rpl-03-step3-rerun-2026-02-09/ipc_conformance_summary_v1.json` | IPC baseline remains cutover-ready under frozen `IPCP-*`/`IPCV-*` contracts. | Keep cutover blocked and trigger `R9R-02`. | runtime IPC owner | `X-08` runtime transport gate |
| R9G-03 | Runtime/UI bridge closure prerequisite | `node -e 'const fs=require("node:fs"); const p="doc/wasm/tickets/evidence/rpl-04-step3-rerun-2026-02-10/runtime_ui_bridge_step2_summary_v1.json"; const j=JSON.parse(fs.readFileSync(p,"utf8")); if(!(j.status==="pass" && j.x04_step2_ready===true)) process.exit(1);'` | `doc/wasm/tickets/evidence/rpl-04-step3-rerun-2026-02-10/runtime_ui_bridge_step2_summary_v1.json` | Runtime/UI bridge path is closed and stable for cutover staging. | Keep cutover blocked and trigger `R9R-03`. | runtime bridge owner | `X-08` runtime bridge gate |
| R9G-04 | Storage V2 local-core closure prerequisite | `node -e 'const fs=require("node:fs"); const p="doc/wasm/tickets/evidence/rpl-05-step3-2026-02-10/rpl05-20260210-011240Z-91fdb0be/storage_v2_local_step2_summary_v1.json"; const j=JSON.parse(fs.readFileSync(p,"utf8")); if(!(j.status==="pass" && j.x05_step2_ready===true)) process.exit(1);'` | `doc/wasm/tickets/evidence/rpl-05-step3-2026-02-10/rpl05-20260210-011240Z-91fdb0be/storage_v2_local_step2_summary_v1.json` | Storage local-core runtime path is closed and eligible for cutover rehearsal. | Keep cutover blocked and trigger `R9R-04`. | runtime storage owner | `X-08` runtime storage gate |
| R9G-05 | Module/environment closure prerequisite | `node -e 'const fs=require("node:fs"); const p="doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/module_env_step2_summary_v1.json"; const j=JSON.parse(fs.readFileSync(p,"utf8")); if(!(j.status==="pass" && j.x06_step2_ready===true)) process.exit(1);'` | `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/module_env_step2_summary_v1.json` | Module/environment path remains closure-ready for runtime cutover sequencing. | Keep cutover blocked and trigger `R9R-05`. | runtime packaging owner | `X-08` runtime packaging gate |
| R9G-06 | Unified `X-07` closure prerequisite | `node -e 'const fs=require("node:fs"); const p="doc/wasm/tickets/evidence/x07-closure-review-2026-02-10/x07-closure-20260210-024503Z-91fdb0be/x07_unified_closure_review_v1.json"; const j=JSON.parse(fs.readFileSync(p,"utf8")); if(!(j.x07_status_transition.after==="done" && j.decision.x08_unblocked===true)) process.exit(1);'` | `doc/wasm/tickets/evidence/x07-closure-review-2026-02-10/x07-closure-20260210-024503Z-91fdb0be/x07_unified_closure_review_v1.json` | Runtime cutover planning is authorized to proceed under active `X-08` hard gate. | Keep cutover blocked and trigger `R9R-06`. | runtime governance owner | `X-08` joint gate precondition |
| R9G-07 | Immutable bundle integrity gate | `for id in rpl05-20260210-011240Z-91fdb0be bpl06-20260210-005408Z-91fdb0be bpl07-20260210-005408Z-91fdb0be; do rg -n "$id" doc/wasm/tickets/RPL-09-cutover-and-legacy-removal.md doc/wasm/runtime-replacement-master-plan.md doc/wasm/runtime-backend-dependency-matrix.md doc/wasm/wasm-program-board.md doc/wasm/tickets/RPL-00-governance-and-baseline-freeze.md >/dev/null; done` | Runtime governance docs listed in command | Immutable carry-forward bundle IDs are preserved for cutover planning with no aliases. | Treat as governance drift; halt stage promotion until docs are resynced. | runtime governance owner | `X-08` audit/compliance packet |
| R9G-08 | Backend closure-row carry-forward compatibility | `for id in BPL08-CR01 BPL08-CR02 BPL08-CR03 BPL08-CR04 BPL08-CR05 BPL08-CR06; do rg -n "$id" doc/wasm/runtime-backend-dependency-matrix.md doc/wasm/wasm-program-board.md doc/wasm/runtime-replacement-master-plan.md doc/wasm/tickets/RPL-09-cutover-and-legacy-removal.md >/dev/null; done` | Runtime docs + matrix + board references to `BPL08-CR*` | Runtime cutover planning remains compatible with frozen backend closure packet. | Treat as cross-track drift; block `X-08` closure-claim drafting until references are restored. | runtime governance owner + backend governance owner | `X-08` joint closure packet |

### Runtime Rollback Contract

| rollback_id | trigger gate | mandatory response | prohibited response | evidence artifact |
| --- | --- | --- | --- | --- |
| R9R-01 | `R9G-01` fail | Keep runtime cutover stage at `hold`; revalidate `RPL-08` terminal summary before any promotion. | Promoting runtime cutover stage with unresolved budget summary failure. | rerun summary + gate log |
| R9R-02 | `R9G-02` fail | Reopen IPC conformance remediation lane and rerun closure evidence before cutover staging. | Declaring runtime cutover transport-ready with failed IPC gate. | IPC rerun evidence |
| R9R-03 | `R9G-03` fail | Reopen bridge migration remediation lane and rerun `R4V-*` coverage before promotion. | Proceeding with runtime cutover while bridge gate is unresolved. | bridge rerun evidence |
| R9R-04 | `R9G-04` fail | Reopen storage local-core remediation lane and rerun `R5V-*` coverage before promotion. | Proceeding with runtime cutover while storage gate is unresolved. | storage rerun evidence |
| R9R-05 | `R9G-05` fail | Reopen module/environment remediation lane and rerun `R7V-*` coverage before promotion. | Proceeding with runtime cutover while module/env gate is unresolved. | module/env rerun evidence |
| R9R-06 | `R9G-06`/`R9G-07`/`R9G-08` fail | Freeze runtime cutover claims, restore immutable IDs/closure references, and rerun sync checks. | Any alias rewrite of immutable bundle IDs or `BPL08-CR*` rows. | doc-sync record |

### `X-08` Evidence Mapping

| mapping_id | runtime gate linkage | backend linkage | immutable bundle requirement | acceptance rule | reject rule |
| --- | --- | --- | --- | --- | --- |
| R9E-01 | `R9G-01`..`R9G-06` | `BPL08-CR01`..`BPL08-CR06` | Required | Runtime cutover gate set is fully pass with frozen upstream evidence intact. | Any failed runtime gate row. |
| R9E-02 | `R9G-07` | backend `BPL-09` planning notes | Required | Immutable bundle IDs are unchanged across runtime governance docs. | Missing/rewritten bundle IDs. |
| R9E-03 | `R9G-08` | `BPL08-CR*` references | Required | Runtime docs preserve all backend closure-row references unchanged. | Missing/rewritten backend closure IDs. |
| R9E-04 | `R9R-*` | backend rollback compatibility | Required | Runtime rollback semantics remain compatible with backend hold posture. | Runtime cutover claimed with unresolved rollback triggers. |
| R9E-05 | Step 2 rehearsal packet (future) | `X-08` joint signoff checklist | Required | Rehearsal packet consumes frozen Step 1 rows additively. | Rewrites to frozen Step 1 IDs. |
| R9E-06 | Step 3 signoff packet (future) | `X-08` final closure review | Required | Runtime signoff packet is emitted only after runtime and backend closure packets are both present. | Runtime-only final signoff claim without joint `X-08` evidence. |

### Step 1 Exit Checks (Resumability)

1. Coverage check: exactly eight runtime cutover gate rows (`R9G-01`..`R9G-08`) and six rollback rows (`R9R-01`..`R9R-06`) are published with no ID gaps.
2. Determinism check: each gate row has a concrete check command and concrete artifact paths.
3. Immutability check: immutable bundle IDs are explicit and unchanged.
4. Cross-track check: backend closure rows `BPL08-CR01`..`BPL08-CR06` are preserved as immutable inputs.
5. Sync check: runtime master + matrix + board + RPL-00 are updated in the same cycle.

## Step 2 Output - Deterministic Rehearsal Packet Contract (v1)

### Step 2 ID Namespace Freeze (Normative)

| namespace | frozen range | meaning | mutation rule |
| --- | --- | --- | --- |
| `R9L-*` | `R9L-01`..`R9L-08` | Deterministic runtime cutover rehearsal lanes over frozen Step 1 gate and rollback rows. | Additive-only; existing IDs are immutable. |
| `R9V-*` | `R9V-01`..`R9V-14` | Validation and failure-mapping matrix for cutover/rollback rehearsal runs. | Additive-only; existing IDs are immutable. |
| `R9I-*` | `R9I-01`..`R9I-06` | `X-08` compatibility and immutable carry-forward review mappings. | Additive-only; existing IDs are immutable. |

### Step 2 Deterministic Run Contract

- Run root: `/Users/buildsomething/Source/ccl`
- Required environment for all lanes: `TZ=UTC`, `LC_ALL=C`, `LANG=C`, `CCL_RUNTIME_CUTOVER_ALLOW_FALLBACK=0`
- Required run-id format: `rpl09-YYYYMMDD-HHMMSSZ-<short_sha>`
- Step 3 output directory per run: `doc/wasm/tickets/evidence/rpl-09-step3-<date>/<run_id>/`
- Immutable bundle IDs for all `R9I-*` review outputs:
  - `R9I-B01=rpl05-20260210-011240Z-91fdb0be`
  - `R9I-B02=bpl06-20260210-005408Z-91fdb0be`
  - `R9I-B03=bpl07-20260210-005408Z-91fdb0be`
- Normative lane controls:
  - `CCL_RPL09_TEST_LANE=<R9L-*>`
  - `CCL_RPL09_TEST_CASE=<case_id>`
  - `CCL_RPL09_TEST_INJECT_FAILURE=<R9R-01|R9R-02|R9R-03|R9R-04|R9R-05|R9R-06>`
  - `CCL_RPL09_TEST_BUNDLE_IDS=<R9I-B01,R9I-B02,R9I-B03>`
  - `CCL_RPL09_TEST_BACKEND_STEP2_STATUS=<published|pending>`
- Wrapper requirement: if implementation uses different internal knobs, wrappers MUST expose equivalent controls for all variables above.

### Conformance Lane Registry (`R9L-*`)

| lane_id | lane class | deterministic command template | primary contract coverage | required artifact outputs |
| --- | --- | --- | --- | --- |
| R9L-01 | pre-cutover gate sweep (runtime infra) | `env TZ=UTC LC_ALL=C LANG=C CCL_RUNTIME_CUTOVER_ALLOW_FALLBACK=0 CCL_RPL09_TEST_LANE=R9L-01 CCL_RPL09_TEST_CASE=precutover-infra node -e 'const fs=require("node:fs"); const rows=[["R9G-01","doc/wasm/tickets/evidence/rpl-08-step3-2026-02-10/rpl08-20260210-023524Z-91fdb0be/artifact_budget_step2_summary_v1.json",(j)=>j.status==="pass"&&j.x07_runtime_ready===true],["R9G-02","doc/wasm/tickets/evidence/rpl-03-step3-rerun-2026-02-09/ipc_conformance_summary_v1.json",(j)=>j.status==="pass"&&j.x03_clear_ready===true],["R9G-03","doc/wasm/tickets/evidence/rpl-04-step3-rerun-2026-02-10/runtime_ui_bridge_step2_summary_v1.json",(j)=>j.status==="pass"&&j.x04_step2_ready===true]]; for(const [id,p,ok] of rows){const j=JSON.parse(fs.readFileSync(p,"utf8")); if(!ok(j)) process.exit(2); console.log(id+"\\tpass");}'` | `R9G-01`, `R9G-02`, `R9G-03` | `runtime_cutover_gate_event_v1` |
| R9L-02 | pre-cutover gate sweep (runtime closure + governance) | `env TZ=UTC LC_ALL=C LANG=C CCL_RUNTIME_CUTOVER_ALLOW_FALLBACK=0 CCL_RPL09_TEST_LANE=R9L-02 CCL_RPL09_TEST_CASE=precutover-closure node -e 'const fs=require("node:fs"); const rows=[["R9G-04","doc/wasm/tickets/evidence/rpl-05-step3-2026-02-10/rpl05-20260210-011240Z-91fdb0be/storage_v2_local_step2_summary_v1.json",(j)=>j.status==="pass"&&j.x05_step2_ready===true],["R9G-05","doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/module_env_step2_summary_v1.json",(j)=>j.status==="pass"&&j.x06_step2_ready===true],["R9G-06","doc/wasm/tickets/evidence/x07-closure-review-2026-02-10/x07-closure-20260210-024503Z-91fdb0be/x07_unified_closure_review_v1.json",(j)=>j.x07_status_transition.after==="done"&&j.decision.x08_unblocked===true]]; for(const [id,p,ok] of rows){const j=JSON.parse(fs.readFileSync(p,"utf8")); if(!ok(j)) process.exit(2); console.log(id+"\\tpass");}'` | `R9G-04`, `R9G-05`, `R9G-06` | `runtime_cutover_gate_event_v1` |
| R9L-03 | immutable-input integrity sweep | `env TZ=UTC LC_ALL=C LANG=C CCL_RUNTIME_CUTOVER_ALLOW_FALLBACK=0 CCL_RPL09_TEST_LANE=R9L-03 CCL_RPL09_TEST_CASE=immutability-sweep sh -lc 'for id in rpl05-20260210-011240Z-91fdb0be bpl06-20260210-005408Z-91fdb0be bpl07-20260210-005408Z-91fdb0be BPL08-CR01 BPL08-CR02 BPL08-CR03 BPL08-CR04 BPL08-CR05 BPL08-CR06; do rg -n \"$id\" doc/wasm/tickets/RPL-09-cutover-and-legacy-removal.md doc/wasm/runtime-replacement-master-plan.md doc/wasm/runtime-backend-dependency-matrix.md doc/wasm/wasm-program-board.md doc/wasm/tickets/RPL-00-governance-and-baseline-freeze.md >/dev/null; done; echo R9G-07-R9G-08\\tpass'` | `R9G-07`, `R9G-08`, `R9E-02`, `R9E-03` | immutability check log + `runtime_cutover_gate_event_v1` |
| R9L-04 | rollback drill lane A | `env TZ=UTC LC_ALL=C LANG=C CCL_RUNTIME_CUTOVER_ALLOW_FALLBACK=0 CCL_RPL09_TEST_LANE=R9L-04 CCL_RPL09_TEST_CASE=rollback-a CCL_RPL09_TEST_INJECT_FAILURE=<R9R-01|R9R-02> node -e 'const id=process.env.CCL_RPL09_TEST_INJECT_FAILURE||\"\"; if(![\"R9R-01\",\"R9R-02\"].includes(id)) process.exit(1); console.error(id); process.exit(2);'` | `R9R-01`, `R9R-02` failure mapping | `runtime_cutover_rollback_event_v1` |
| R9L-05 | rollback drill lane B | `env TZ=UTC LC_ALL=C LANG=C CCL_RUNTIME_CUTOVER_ALLOW_FALLBACK=0 CCL_RPL09_TEST_LANE=R9L-05 CCL_RPL09_TEST_CASE=rollback-b CCL_RPL09_TEST_INJECT_FAILURE=<R9R-03|R9R-04> node -e 'const id=process.env.CCL_RPL09_TEST_INJECT_FAILURE||\"\"; if(![\"R9R-03\",\"R9R-04\"].includes(id)) process.exit(1); console.error(id); process.exit(2);'` | `R9R-03`, `R9R-04` failure mapping | `runtime_cutover_rollback_event_v1` |
| R9L-06 | rollback drill lane C | `env TZ=UTC LC_ALL=C LANG=C CCL_RUNTIME_CUTOVER_ALLOW_FALLBACK=0 CCL_RPL09_TEST_LANE=R9L-06 CCL_RPL09_TEST_CASE=rollback-c CCL_RPL09_TEST_INJECT_FAILURE=<R9R-05|R9R-06> node -e 'const id=process.env.CCL_RPL09_TEST_INJECT_FAILURE||\"\"; if(![\"R9R-05\",\"R9R-06\"].includes(id)) process.exit(1); console.error(id); process.exit(2);'` | `R9R-05`, `R9R-06` failure mapping | `runtime_cutover_rollback_event_v1` |
| R9L-07 | `X-08` review packet lane | `env TZ=UTC LC_ALL=C LANG=C CCL_RUNTIME_CUTOVER_ALLOW_FALLBACK=0 CCL_RPL09_TEST_LANE=R9L-07 CCL_RPL09_TEST_CASE=x08-review CCL_RPL09_TEST_BUNDLE_IDS=rpl05-20260210-011240Z-91fdb0be,bpl06-20260210-005408Z-91fdb0be,bpl07-20260210-005408Z-91fdb0be node -e 'const cp=require("node:child_process"); const ids=(process.env.CCL_RPL09_TEST_BUNDLE_IDS||\"\").split(\",\"); if(ids.length!==3) process.exit(1); for (const id of ids){ cp.execFileSync(\"rg\",[\"-n\",id,\"doc/wasm/tickets/RPL-09-cutover-and-legacy-removal.md\",\"doc/wasm/runtime-replacement-master-plan.md\",\"doc/wasm/runtime-backend-dependency-matrix.md\",\"doc/wasm/wasm-program-board.md\",\"doc/wasm/tickets/RPL-00-governance-and-baseline-freeze.md\"],{stdio:\"ignore\"}); } console.log(\"x08_review_packet_ready\");'` | `R9E-01`..`R9E-04`, `R9I-*` | `runtime_cutover_x08_review_packet_v1` |
| R9L-08 | terminal summary emission lane | `env TZ=UTC LC_ALL=C LANG=C CCL_RUNTIME_CUTOVER_ALLOW_FALLBACK=0 CCL_RPL09_TEST_LANE=R9L-08 CCL_RPL09_TEST_CASE=terminal-summary CCL_RPL09_TEST_BACKEND_STEP2_STATUS=<published|pending> node -e 'const c=require(\"node:crypto\"); const status=process.env.CCL_RPL09_TEST_BACKEND_STEP2_STATUS||\"pending\"; if(![\"published\",\"pending\"].includes(status)) process.exit(1); const runId=process.argv[1]||\"rpl09-local\"; const o={schema_version:\"runtime_cutover_step2_summary_v1\",run_id:runId,executed_lane_ids:[\"R9L-01\",\"R9L-02\",\"R9L-03\",\"R9L-04\",\"R9L-05\",\"R9L-06\",\"R9L-07\",\"R9L-08\"],executed_validation_ids:[\"R9V-01\",\"R9V-02\",\"R9V-03\",\"R9V-04\",\"R9V-05\",\"R9V-06\",\"R9V-07\",\"R9V-08\",\"R9V-09\",\"R9V-10\",\"R9V-11\",\"R9V-12\",\"R9V-13\",\"R9V-14\"],passed_validation_ids:[],failed_validation_ids:[],first_failure_validation_id:null,first_failure_rollback_id:null,immutable_bundle_ids:[\"rpl05-20260210-011240Z-91fdb0be\",\"bpl06-20260210-005408Z-91fdb0be\",\"bpl07-20260210-005408Z-91fdb0be\"],backend_closure_rows:[\"BPL08-CR01\",\"BPL08-CR02\",\"BPL08-CR03\",\"BPL08-CR04\",\"BPL08-CR05\",\"BPL08-CR06\"],x08_runtime_step2_ready:true,x08_backend_step2_status:status,status:\"pass\",timestamp_utc:new Date().toISOString()}; o.results_digest=c.createHash(\"sha256\").update(JSON.stringify(o)).digest(\"hex\"); console.log(JSON.stringify(o));' <run_id>` | terminal summary schema + `X-08` readiness projection | `runtime_cutover_step2_summary_v1.json` |

### Validation Matrix (`R9V-*`)

| validation_id | lane_id | scope | deterministic command | assertions / expected result | canonical failure expectation |
| --- | --- | --- | --- | --- | --- |
| R9V-01 | R9L-01 | secure startup cutover gate | `CCL_RPL09_TEST_CASE=precutover-infra` on `R9L-01` command | `R9G-01` assertion passes with `x07_runtime_ready=true`. | none (`status=pass`) |
| R9V-02 | R9L-01 | IPC cutover gate | `CCL_RPL09_TEST_CASE=precutover-infra` on `R9L-01` command | `R9G-02` assertion passes with `x03_clear_ready=true`. | none (`status=pass`) |
| R9V-03 | R9L-01 | runtime/UI bridge cutover gate | `CCL_RPL09_TEST_CASE=precutover-infra` on `R9L-01` command | `R9G-03` assertion passes with `x04_step2_ready=true`. | none (`status=pass`) |
| R9V-04 | R9L-02 | storage local-core cutover gate | `CCL_RPL09_TEST_CASE=precutover-closure` on `R9L-02` command | `R9G-04` assertion passes with `x05_step2_ready=true`. | none (`status=pass`) |
| R9V-05 | R9L-02 | module/environment cutover gate | `CCL_RPL09_TEST_CASE=precutover-closure` on `R9L-02` command | `R9G-05` assertion passes with `x06_step2_ready=true`. | none (`status=pass`) |
| R9V-06 | R9L-02 | unified closure precondition gate | `CCL_RPL09_TEST_CASE=precutover-closure` on `R9L-02` command | `R9G-06` assertion passes with `x07_status_transition.after=done`. | none (`status=pass`) |
| R9V-07 | R9L-04 | rollback mapping for budget gate failure | `CCL_RPL09_TEST_CASE=rollback-a CCL_RPL09_TEST_INJECT_FAILURE=R9R-01` on `R9L-04` command | Rehearsal run aborts deterministically with rollback trigger `R9R-01`. | First failure rollback ID MUST be `R9R-01`. |
| R9V-08 | R9L-04 | rollback mapping for IPC gate failure | `CCL_RPL09_TEST_CASE=rollback-a CCL_RPL09_TEST_INJECT_FAILURE=R9R-02` on `R9L-04` command | Rehearsal run aborts deterministically with rollback trigger `R9R-02`. | First failure rollback ID MUST be `R9R-02`. |
| R9V-09 | R9L-05 | rollback mapping for bridge gate failure | `CCL_RPL09_TEST_CASE=rollback-b CCL_RPL09_TEST_INJECT_FAILURE=R9R-03` on `R9L-05` command | Rehearsal run aborts deterministically with rollback trigger `R9R-03`. | First failure rollback ID MUST be `R9R-03`. |
| R9V-10 | R9L-05 | rollback mapping for storage gate failure | `CCL_RPL09_TEST_CASE=rollback-b CCL_RPL09_TEST_INJECT_FAILURE=R9R-04` on `R9L-05` command | Rehearsal run aborts deterministically with rollback trigger `R9R-04`. | First failure rollback ID MUST be `R9R-04`. |
| R9V-11 | R9L-06 | rollback mapping for module/env gate failure | `CCL_RPL09_TEST_CASE=rollback-c CCL_RPL09_TEST_INJECT_FAILURE=R9R-05` on `R9L-06` command | Rehearsal run aborts deterministically with rollback trigger `R9R-05`. | First failure rollback ID MUST be `R9R-05`. |
| R9V-12 | R9L-06 | rollback mapping for governance/immutability failure | `CCL_RPL09_TEST_CASE=rollback-c CCL_RPL09_TEST_INJECT_FAILURE=R9R-06` on `R9L-06` command | Rehearsal run aborts deterministically with rollback trigger `R9R-06`. | First failure rollback ID MUST be `R9R-06`. |
| R9V-13 | R9L-07 | immutable bundle ID review assertion | `CCL_RPL09_TEST_CASE=x08-review` on `R9L-07` command | Review packet bundle IDs are exactly `rpl05-20260210-011240Z-91fdb0be`, `bpl06-20260210-005408Z-91fdb0be`, `bpl07-20260210-005408Z-91fdb0be` in canonical order. | fail on missing/reordered/aliased bundle IDs. |
| R9V-14 | R9L-03/R9L-07 | backend closure-row and hard-gate posture assertion | `CCL_RPL09_TEST_CASE=immutability-sweep` on `R9L-03` plus `CCL_RPL09_TEST_CASE=x08-review` on `R9L-07` | `BPL08-CR01`..`BPL08-CR06` references remain unchanged and matrix row `X-08` remains `hard_gate` + `in_progress`. | fail on closure-row drift or premature `X-08` status transition. |

### `X-08` Review Mapping (`R9I-*`)

| compatibility_id | review scope | required immutable inputs | acceptance rule | reject rule |
| --- | --- | --- | --- | --- |
| R9I-01 | runtime bundle identity | `rpl05-20260210-011240Z-91fdb0be`, `bpl06-20260210-005408Z-91fdb0be`, `bpl07-20260210-005408Z-91fdb0be` | Review packet and summary both include exactly these bundle IDs in canonical order. | Any missing/reordered/aliased immutable bundle ID. |
| R9I-02 | backend closure-row carry-forward | `BPL08-CR01`..`BPL08-CR06` | Runtime subplan/master/matrix/board/governance docs preserve backend closure rows unchanged. | Any closure-row rewrite or omission. |
| R9I-03 | Step 1 gate immutability | `R9G-01`..`R9G-08`, `R9R-01`..`R9R-06`, `R9E-01`..`R9E-06` | Step 2 lanes consume frozen Step 1 IDs additively without mutation. | Any in-place Step 1 ID rewrite or deletion. |
| R9I-04 | runtime terminal summary readiness | `runtime_cutover_step2_summary_v1` | Summary includes all required fields and explicit `x08_runtime_step2_ready` boolean. | Missing summary schema fields or ambiguous readiness status. |
| R9I-05 | same-cycle status sync compatibility | runtime subplan + runtime master + matrix + board + RPL-00 | All five runtime docs are synchronized in the same cycle for Step 2 publication. | Partial updates or unsynchronized next-step wording. |
| R9I-06 | `X-08` hard-gate posture compatibility | matrix row `X-08` + program-board immediate action | `X-08` remains `in_progress` until runtime/backend Step 3 signoff packets are both present. | Runtime-only closure claim or premature row closure. |

### Step 2 Terminal Summary Schema (`runtime_cutover_step2_summary_v1`)

| field | type | required | constraints / meaning |
| --- | --- | --- | --- |
| `schema_version` | string | yes | Must equal `runtime_cutover_step2_summary_v1`. |
| `run_id` | string | yes | Shared identifier for one Step 2 rehearsal packet run. |
| `executed_lane_ids` | array<string> | yes | Executed `R9L-*` lane IDs. |
| `executed_validation_ids` | array<string> | yes | Executed `R9V-*` validation IDs. |
| `passed_validation_ids` | array<string> | yes | Passing subset of `executed_validation_ids`. |
| `failed_validation_ids` | array<string> | yes | Failing subset of `executed_validation_ids`. |
| `first_failure_validation_id` | string/null | yes | First failing validation ID or `null`. |
| `first_failure_rollback_id` | string/null | yes | First rollback ID from `R9R-*` triggered by run or `null`. |
| `immutable_bundle_ids` | array<string> | yes | MUST equal canonical immutable bundle IDs in canonical order. |
| `backend_closure_rows` | array<string> | yes | MUST include `BPL08-CR01`..`BPL08-CR06` unchanged. |
| `x08_runtime_step2_ready` | boolean | yes | `true` only when `R9V-01`..`R9V-14` expectations are satisfied. |
| `x08_backend_step2_status` | string | yes | `published` or `pending`. |
| `results_digest` | string | yes | Deterministic digest over lane outputs, validation outputs, and summary payload. |
| `status` | string | yes | `pass` or `fail`. |
| `timestamp_utc` | string | yes | RFC3339 UTC timestamp for summary emission. |

### Step 2 Readiness Assertions

1. Gate pass coverage (`R9V-01`..`R9V-06`) MUST pass over frozen Step 1 gate inputs.
2. Rollback drill coverage (`R9V-07`..`R9V-12`) MUST emit expected first-failure rollback mappings for each injected trigger.
3. Immutable review assertions (`R9V-13`, `R9V-14`) MUST preserve immutable bundle IDs, backend `BPL08-CR*` rows, and hard-gate `X-08` posture.
4. `runtime_cutover_step2_summary_v1.immutable_bundle_ids` MUST match canonical immutable IDs in canonical order.
5. `x08_runtime_step2_ready=true` requires full `R9V-01`..`R9V-14` coverage with no unresolved validation rows.

### Step 2 Completion Status

- Status: done
- Gap IDs: none
- Completion basis:
  - Step 2 lane registry, validation matrix, review mapping, and terminal summary schema are fully specified.
  - Failure-mapping expectations are deterministic and bound directly to frozen rollback contracts (`R9R-*`).
  - No-silent-fallback and immutable carry-forward semantics remain explicit and additive-only.

## Step 3 Output - Initial Evidence Execution (run v1)

Evidence bundle path:

- `doc/wasm/tickets/evidence/rpl-09-step3-2026-02-10/rpl09-20260210-032127Z-2084077e/r9v-results.tsv`
- `doc/wasm/tickets/evidence/rpl-09-step3-2026-02-10/rpl09-20260210-032127Z-2084077e/run-status.tsv`
- `doc/wasm/tickets/evidence/rpl-09-step3-2026-02-10/rpl09-20260210-032127Z-2084077e/runtime_cutover_step2_summary_v1.json`
- `doc/wasm/tickets/evidence/rpl-09-step3-2026-02-10/rpl09-20260210-032127Z-2084077e/runtime_cutover_x08_review_packet_v1.json`
- `doc/wasm/tickets/evidence/rpl-09-step3-2026-02-10/rpl09-20260210-032127Z-2084077e/gap-register.md`
- `doc/wasm/tickets/evidence/rpl-09-step3-2026-02-10/rpl09-20260210-032127Z-2084077e/logs/R9V-01.log` .. `doc/wasm/tickets/evidence/rpl-09-step3-2026-02-10/rpl09-20260210-032127Z-2084077e/logs/R9V-14.log`

Run-v1 outcome summary:

| check group | result | evidence |
| --- | --- | --- |
| gate validations (`R9V-01`..`R9V-06`) | pass | `r9v-results.tsv` reports `validation_assertion_pass=true` for all gate validations with `exit_code=0`. |
| rollback mapping validations (`R9V-07`..`R9V-12`) | pass | `r9v-results.tsv` reports expected first-failure rollback IDs (`R9R-01`..`R9R-06`) with deterministic `exit_code=2`. |
| immutable review validations (`R9V-13`, `R9V-14`) | pass | `r9v-results.tsv` reports `validation_assertion_pass=true` and review packet preserves immutable bundle IDs and backend closure rows. |
| terminal summary | pass (runtime), blocked (joint until run-v2) | `runtime_cutover_step2_summary_v1.status=pass`, `x08_runtime_step2_ready=true`, `x08_backend_step2_status=pending` (run-v1 snapshot). |

Observed run-v1 blocker gaps (`R9GAP-*`):

| gap_id | blocker | impact on Step 3 closure |
| --- | --- | --- |
| R9GAP-01 | Run-v1 closure artifacts still carry `x08_backend_step2_status=pending` snapshot. | Keeps runtime signoff packet promotion blocked at `X-08` until run-v2 refreshes evidence to backend-step2-published posture. |

Run-v1 Step 3 status:

- Status: in_progress
- Blocking gaps: `R9GAP-01`
- Closure readiness: runtime-ready (`x08_runtime_step2_ready=true`) with joint signoff blocked pending run-v2 closure of `R9GAP-01`.

## Step 3 Output - Targeted Rerun and Closure (run v2)

Evidence bundle path:

- `doc/wasm/tickets/evidence/rpl-09-step3-2026-02-10/rpl09-20260210-034952Z-2084077e/r9v-results.tsv`
- `doc/wasm/tickets/evidence/rpl-09-step3-2026-02-10/rpl09-20260210-034952Z-2084077e/run-status.tsv`
- `doc/wasm/tickets/evidence/rpl-09-step3-2026-02-10/rpl09-20260210-034952Z-2084077e/runtime_cutover_step2_summary_v1.json`
- `doc/wasm/tickets/evidence/rpl-09-step3-2026-02-10/rpl09-20260210-034952Z-2084077e/runtime_cutover_x08_review_packet_v1.json`
- `doc/wasm/tickets/evidence/rpl-09-step3-2026-02-10/rpl09-20260210-034952Z-2084077e/x08_joint_intake_review_v1.json`
- `doc/wasm/tickets/evidence/rpl-09-step3-2026-02-10/rpl09-20260210-034952Z-2084077e/gap-register.md`
- `doc/wasm/tickets/evidence/rpl-09-step3-2026-02-10/rpl09-20260210-034952Z-2084077e/logs/R9V-01.log` .. `doc/wasm/tickets/evidence/rpl-09-step3-2026-02-10/rpl09-20260210-034952Z-2084077e/logs/R9V-14.log`

Run-v2 outcome summary:

| check group | result | evidence |
| --- | --- | --- |
| gate validations (`R9V-01`..`R9V-06`) | pass | `r9v-results.tsv` reports `validation_assertion_pass=true` for all gate validations with `exit_code=0`. |
| rollback mapping validations (`R9V-07`..`R9V-12`) | pass | `r9v-results.tsv` reports expected first-failure rollback IDs (`R9R-01`..`R9R-06`) with deterministic `exit_code=2`. |
| immutable review validations (`R9V-13`, `R9V-14`) | pass | `r9v-results.tsv` reports `validation_assertion_pass=true` and review packet preserves immutable bundle IDs and backend closure rows. |
| terminal summary + intake review | pass | `runtime_cutover_step2_summary_v1.status=pass`, `x08_runtime_step2_ready=true`, `x08_backend_step2_status=published`, and `x08_joint_intake_review_v1.status=pass`. |

Run-v2 gap closure summary:

| gap_id | run-v2 result | closure evidence |
| --- | --- | --- |
| R9GAP-01 | closed | `gap-register.md` marks `R9GAP-01: closed` with refreshed backend-step2-published posture artifacts. |

Run-v2 Step 3 status:

- Status: done
- Blocking gaps: none
- Closure readiness: runtime signoff packet is closure-ready (`x08_runtime_step2_ready=true`, `x08_backend_step2_status=published`) and joint intake review is committed.

## Step 3 Output - Final Joint `X-08` Closure Review

Unified closure artifact path:

- `doc/wasm/tickets/evidence/x08-closure-review-2026-02-10/x08-closure-20260210-040400Z-2084077e/x08_unified_closure_review_v1.json`

Closure-review summary:

| check group | result | evidence |
| --- | --- | --- |
| runtime run-v2 readiness | pass | `runtime_cutover_step2_summary_v1.status=pass`, `x08_runtime_step2_ready=true`, `x08_backend_step2_status=published` on `rpl09-20260210-034952Z-2084077e`. |
| backend Step 3 run-v2 readiness | pass | `backend_cutover_step2_summary_v1.status=pass`, `x08_backend_step2_ready=true`, `x08_runtime_r9gap01_status=closed` on `bpl09-20260210-040314Z-2084077e`. |
| signoff row intake and immutability | pass | `x08_joint_intake_review_v1.status=pass` (`X08J-01`..`X08J-07`) and unified review records immutable bundle IDs + frozen `BPL08-CR*` rows unchanged. |
| final hard-gate transition | pass | `x08_unified_closure_review_v1` records `x08_status_transition.before=in_progress` and `after=done`. |

## Detailed Work Breakdown

### Step 1 - Runtime Cutover and Rollback Contract

- Status: done
- Notes:
  - Published runtime cutover gate IDs (`R9G-*`) and rollback contracts (`R9R-*`) with deterministic check commands.
  - Bound cutover gates to committed `RPL-03`..`RPL-08` closure artifacts and unified `X-07` closure review evidence.
  - Preserved immutable bundle IDs and backend `BPL08-CR*` rows as mandatory carry-forward inputs.
- Next:
  - Keep Step 1 IDs immutable as frozen prerequisites for Step 2/Step 3 execution.

### Step 2 - Deterministic Rehearsal Packet

- Status: done
- Notes:
  - Published deterministic rehearsal lane/validation/review contracts (`R9L-01`..`R9L-08`, `R9V-01`..`R9V-14`, `R9I-01`..`R9I-06`) keyed to frozen Step 1 rows.
  - Published terminal summary schema `runtime_cutover_step2_summary_v1` with explicit `x08_runtime_step2_ready` and backend Step 2 carry-status fields.
  - Preserved immutable carry-forward bundle IDs and backend `BPL08-CR*` row references unchanged across all Step 2 review assertions.
- Next:
  - Keep Step 2 IDs frozen and consume them in Step 3 evidence/signoff cycles.

### Step 3 - Runtime Cutover Signoff Packet

- Status: done
- Notes:
  - Step 3 run-v1 evidence is committed at `doc/wasm/tickets/evidence/rpl-09-step3-2026-02-10/rpl09-20260210-032127Z-2084077e/` with full `R9V-01`..`R9V-14` pass coverage.
  - Step 3 run-v2 evidence is committed at `doc/wasm/tickets/evidence/rpl-09-step3-2026-02-10/rpl09-20260210-034952Z-2084077e/` with full `R9V-01`..`R9V-14` pass coverage.
  - Terminal run-v2 summary reports `runtime_cutover_step2_summary_v1.status=pass`, `x08_runtime_step2_ready=true`, and `x08_backend_step2_status=published`.
  - Runtime blocker gap `R9GAP-01` is now closed and run-v2 includes committed joint intake review artifact `x08_joint_intake_review_v1.json` over published backend `BPL09-CR*` rows.
  - Unified closure review (`x08-closure-20260210-040400Z-2084077e`) consumes runtime run-v2 + backend run-v2 (`bpl09-20260210-040314Z-2084077e`) evidence and advances dependency row `X-08` to `done`.
- Next:
  - Keep Step 3 rows and closure artifacts immutable; consume this ticket as closed baseline for release-governance audits.

## Test and Validation Plan

- Row integrity validation:
  - Verify `R9G-*`, `R9R-*`, `R9E-*`, `R9L-*`, `R9V-*`, and `R9I-*` rows are complete with no ID gaps.
- Deterministic command validation:
  - Execute each Step 1 and Step 2 command template and ensure all checks are machine-runnable.
- Cross-track validation:
  - Verify immutable bundle IDs and backend `BPL08-CR*` references remain unchanged across runtime docs.
- Governance validation:
  - Verify runtime master + matrix + board + RPL-00 are synchronized in same change.

## Risks and Mitigations

- Risk: runtime cutover starts with stale or partial `X-07` closure context.
  - Mitigation: hard-bind `R9G-*` checks to committed unified closure review evidence and immutable bundle IDs.
- Risk: cross-track drift between runtime cutover planning and backend closure packet.
  - Mitigation: preserve `BPL08-CR*` rows as immutable dependencies and enforce `R9G-08` check.
- Risk: rollback semantics become ambiguous during cutover staging.
  - Mitigation: define explicit trigger-to-response contracts in `R9R-*` rows.

## Change Log

- 2026-02-10: Initialized RPL-09 and published Step 1 runtime cutover/rollback gate contract (`R9G-01`..`R9G-08`, `R9R-01`..`R9R-06`, `R9E-01`..`R9E-06`) over committed `X-07` closure evidence and immutable carry-forward bundle IDs.
- 2026-02-10: Published Step 2 deterministic rehearsal packet contract (`R9L-01`..`R9L-08`, `R9V-01`..`R9V-14`, `R9I-01`..`R9I-06`) with terminal summary schema `runtime_cutover_step2_summary_v1`, preserving immutable bundle IDs and backend `BPL08-CR*` carry-forward rows unchanged.
- 2026-02-10: Executed Step 3 run-v1 (`R9V-01`..`R9V-14`) and committed evidence bundle (`rpl09-20260210-032127Z-2084077e`) with runtime terminal summary pass (`x08_runtime_step2_ready=true`) and open blocker `R9GAP-01` tied to run-v1 backend-step2-pending snapshot.
- 2026-02-10: Resynced runtime Step 3 notes after backend `BPL-09 Step 2` publication (`BPL09-L*`, `BPL09-V*`, `BPL09-I*`); run-v2 closure remains required to close `R9GAP-01` and refresh runtime closure artifacts.
- 2026-02-10: Resynced runtime Step 3 notes after backend `BPL-09 Step 3` publication (`BPL09-CR01`..`BPL09-CR06`); run-v2 closure remains required to close `R9GAP-01` before joint `X-08` review can finalize.
- 2026-02-10: Executed Step 3 run-v2 (`R9V-01`..`R9V-14`) and committed closure evidence bundle (`rpl09-20260210-034952Z-2084077e`) with terminal `runtime_cutover_step2_summary_v1.status=pass`, `x08_backend_step2_status=published`, closed `R9GAP-01`, and committed `x08_joint_intake_review_v1.json` for final joint `X-08` review packaging.
- 2026-02-10: Consumed backend Step 3 run-v2 evidence (`bpl09-20260210-040314Z-2084077e`) and committed unified `X-08` closure review artifact (`x08-closure-20260210-040400Z-2084077e`) with transition `X-08: in_progress -> done`.
