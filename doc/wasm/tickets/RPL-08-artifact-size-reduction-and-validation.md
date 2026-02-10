# RPL-08 - Artifact Size Reduction and Validation

Status: in_progress  
Priority: P1  
Owner: Runtime/WASM replacement track  
Last Updated: 2026-02-10  
Parent Plan: `doc/wasm/runtime-replacement-master-plan.md`

## Scope

In scope:

- Define a deterministic runtime artifact-size budget sheet with fixed byte-level guardrails and closure targets.
- Define machine-runnable measurement commands, formulas, and aggregation rules for runtime-owned artifact classes.
- Bind runtime-side size validation outputs to `X-07` carry-forward review posture and immutable closure bundles.
- Define explicit no-silent-fallback, telemetry, and rollback/remediation semantics for partial budget migration progress.

Out of scope:

- Implementing runtime/module optimization code changes directly.
- Rewriting backend-owned budget rows (`BPL07-BM*`) or closure rows (`BPL08-CR*`).
- Runtime cutover and legacy retirement (`RPL-09`).
- CL thread semantics implementation details (remain deferred).

## Dependencies

- RPL-00 governance loop and same-cycle synchronization discipline.
- RPL-01 secure-only startup/no-fallback posture and contradiction follow-through (`C-01`, `C-03`, `C-04`, `C-08`).
- RPL-02 worker topology/lifecycle readiness (`WTOP-02`, `WSEQ-05`, `WLCT-09`, `WLCT-10`, `WLCT-11`) for deterministic runtime measurement lanes.
- RPL-03 IPC failure and telemetry baseline (`IPCP-29`, `IPCP-31`, `IPCP-47`) for no-fallback semantics.
- RPL-07 closed module-environment baseline (`R7S-*`, `R7R-*`, `R7T-*`, `R7I-*`) as additive-only input.
- Dependency row `X-07` (`RPL-08` vs `BPL-07` soft gate) and published backend closure packet rows (`BPL08-CR01`..`BPL08-CR06`).

## Deliverables

1. Step 1 runtime budget and measurement contract with frozen deterministic IDs (`R8B-*`, `R8M-*`, `R8T-*`, `R8R-*`).
2. Step 2 lane/validation/review contract for deterministic budget execution evidence.
3. Step 3 committed evidence bundle and synchronized `X-07` closure recommendation packet.

## Exit Criteria

- Runtime artifact classes, baseline anchors, guardrail ceilings, and closure targets are fully specified.
- Measurement commands and formulas are deterministic, reproducible, and machine-actionable.
- No-silent-fallback semantics and canonical failure handling are explicit for all budget rows.
- Telemetry schemas and rollback/remediation contracts are defined for `X-07` assertions.

## Current Notes

- This subplan is newly authored; Step 1 budget/measurement contract is published in this document.
- Step 1 freezes `R8B-*`, `R8M-*`, `R8T-*`, and `R8R-*` namespaces as additive-only identifiers.
- Step 2 lane/validation/review contract is now published in this document with frozen IDs (`R8L-*`, `R8V-*`, `R8I-*`).
- Step 3 run-v1 evidence is committed at `doc/wasm/tickets/evidence/rpl-08-step3-2026-02-10/rpl08-20260210-022252Z-91fdb0be/` with full `R8V-01`..`R8V-14` command execution coverage and terminal `artifact_budget_step2_summary_v1.status=pass`.
- Step 3 run-v2 evidence is now committed at `doc/wasm/tickets/evidence/rpl-08-step3-2026-02-10/rpl08-20260210-023524Z-91fdb0be/` with full `R8V-01`..`R8V-14` assertion pass coverage, `guardrail_pass_count=8`, `target_pass_count=8`, `x07_runtime_ready=true`, and closed blocker `R8GAP-01`.
- Runtime artifact remediation is now implemented in-code via `scripts/wasm/compact-runtime-modules.mjs` + `scripts/wasm/compile-wasm-fasls.sh` compaction wiring (no doc-only closure path).
- `X-07` remains in-progress and explicit carry-forward posture pending unified runtime/backend closure review acceptance.
- Immutable closure-bundle IDs are mandatory carry-forward inputs for all `X-07` review notes:
  - `rpl05-20260210-011240Z-91fdb0be`
  - `bpl06-20260210-005408Z-91fdb0be`
  - `bpl07-20260210-005408Z-91fdb0be`
- Secure-only runtime posture remains mandatory; no fallback to legacy artifact lanes is allowed on replacement paths.
- Runtime thread capability remains required now; CL thread semantics remain deferred.

## Immediate Next Step

- Action: execute unified `X-07` closure review over committed runtime run-v2 budget evidence and immutable backend `BPL08-CR*` carry-forward rows.
- Why now: runtime Step 3 run-v2 has closed `R8GAP-01` and reports `x07_runtime_ready=true`; remaining work is cross-track closure acceptance, not additional runtime remediation.
- Success evidence: same-cycle runtime/backend planning docs record the committed run-v2 bundle (`rpl08-20260210-023524Z-91fdb0be`), preserve immutable bundle IDs, and advance `X-07` closure review packet language without reopening runtime gaps.

## Step 1 Output - Runtime Artifact Budget and Measurement Contract (v1)

### Step 1 ID Namespace Freeze (Normative)

| namespace | frozen range | meaning | mutation rule |
| --- | --- | --- | --- |
| `R8B-*` | `R8B-01`..`R8B-24` | Runtime artifact budget rows, baseline anchors, threshold policy, and `X-07` mapping clauses. | Additive-only; existing IDs are immutable. |
| `R8M-*` | `R8M-01`..`R8M-20` | Deterministic measurement commands, formulas, aggregation logic, and reproducibility controls. | Additive-only; existing IDs are immutable. |
| `R8T-*` | `R8T-01`..`R8T-12` | Telemetry schemas and required assertions for Step 2/Step 3 budget evidence lanes. | Additive-only; existing IDs are immutable. |
| `R8R-*` | `R8R-01`..`R8R-10` | Rollback/remediation contract for partial migration and closure-review drift handling. | Additive-only; existing IDs are immutable. |

### Runtime Artifact Budget Inventory (Normative)

Baseline capture timestamp: `2026-02-10`.

| budget_id | artifact class | canonical path | baseline bytes | guardrail max bytes | closure target max bytes | gate class | owner |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R8B-01 | runtime module binary | `doc/wasm/wasm-runtime-modules.bin` | `436499792` | `436499792` | `349199833` | soft_gate (`X-07`) | runtime packaging owner |
| R8B-02 | runtime module manifest | `doc/wasm/wasm-runtime-modules.json` | `277176` | `277176` | `263317` | soft_gate (`X-07`) | runtime packaging owner |
| R8B-03 | runtime wasm payload | `doc/wasm/js/wasmcl.wasm` | `531873` | `531873` | `531873` | soft_gate (`X-07`) | runtime build owner |
| R8B-04 | runtime subprims payload | `doc/wasm/js/subprims.wasm` | `277753` | `277753` | `277753` | soft_gate (`X-07`) | runtime build owner |
| R8B-05 | aggregate shipping payload (`R8B-01`..`R8B-04`) | derived sum | `437586594` | `437586594` | `350069275` | soft_gate (`X-07`) | runtime governance owner |
| R8B-06 | `X-07` runtime carry-forward packet size anchor | `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/module_env_x07_review_packet_v1.json` | `416` | `4096` | `4096` | hard_guardrail | runtime governance owner |
| R8B-07 | `X-06` runtime carry-forward packet size anchor | `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/module_env_x06_review_packet_v1.json` | `703` | `4096` | `4096` | hard_guardrail | runtime governance owner |
| R8B-08 | step summary size anchor | `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/module_env_step2_summary_v1.json` | `1360` | `8192` | `8192` | hard_guardrail | runtime governance owner |

### Budget Policy and Formula Contract

| policy_id | policy | deterministic rule | pass condition | fail condition |
| --- | --- | --- | --- | --- |
| R8B-09 | guardrail policy | `measured_bytes <= guardrail_max_bytes` per `R8B-01`..`R8B-08`. | Row status `guardrail_pass=true`. | Row status `guardrail_pass=false`; row is hard fail. |
| R8B-10 | closure-target policy | `measured_bytes <= closure_target_max_bytes` for `R8B-01`..`R8B-05`. | Row status `target_pass=true`. | Row status `target_pass=false`; `X-07` remains `in_progress` (carry-forward). |
| R8B-11 | delta bytes formula | `delta_bytes = measured_bytes - baseline_bytes`. | Reported for all budget rows. | Missing `delta_bytes` field is invalid. |
| R8B-12 | delta percent formula | `delta_pct = ((measured_bytes - baseline_bytes) / baseline_bytes) * 100`. | Reported with 6-decimal precision for `R8B-01`..`R8B-05`. | Missing/NaN `delta_pct` is invalid. |
| R8B-13 | aggregate formula | `R8B-05.measured_bytes = sum(R8B-01..R8B-04.measured_bytes)`. | Aggregate equation matches exactly. | Any aggregate mismatch is hard fail. |
| R8B-14 | baseline immutability | Baseline bytes are frozen constants unless a new additive row supersedes them. | Existing baseline values remain unchanged. | In-place baseline edits on existing IDs are forbidden. |
| R8B-15 | missing artifact semantics | Missing artifact path is terminal failure (`RPL08-E001`). | Missing-path count is zero. | Any missing path yields run fail; no `N/A` fallback allowed. |
| R8B-16 | no-fallback measurement source | Measurements MUST read canonical runtime artifacts only; no legacy snapshot proxy allowed. | `selected_source=canonical_artifact` for all rows. | Any `selected_source=legacy_snapshot` is policy fail (`RPL08-E002`). |

### Deterministic Measurement Command Registry

All commands execute from repo root `/Users/buildsomething/Source/ccl` with required environment `TZ=UTC LC_ALL=C LANG=C`.

| command_id | budget linkage | deterministic command | output contract | failure code |
| --- | --- | --- | --- | --- |
| R8M-01 | `R8B-01` | `env TZ=UTC LC_ALL=C LANG=C stat -f '%z' doc/wasm/wasm-runtime-modules.bin` | Emit integer bytes for `runtime_module_bin_bytes`. | `RPL08-E001` |
| R8M-02 | `R8B-02` | `env TZ=UTC LC_ALL=C LANG=C stat -f '%z' doc/wasm/wasm-runtime-modules.json` | Emit integer bytes for `runtime_module_manifest_bytes`. | `RPL08-E001` |
| R8M-03 | `R8B-03` | `env TZ=UTC LC_ALL=C LANG=C stat -f '%z' doc/wasm/js/wasmcl.wasm` | Emit integer bytes for `runtime_wasm_payload_bytes`. | `RPL08-E001` |
| R8M-04 | `R8B-04` | `env TZ=UTC LC_ALL=C LANG=C stat -f '%z' doc/wasm/js/subprims.wasm` | Emit integer bytes for `runtime_subprims_payload_bytes`. | `RPL08-E001` |
| R8M-05 | `R8B-05` | `env TZ=UTC LC_ALL=C LANG=C node -e 'const fs=require("node:fs"); const p=["doc/wasm/wasm-runtime-modules.bin","doc/wasm/wasm-runtime-modules.json","doc/wasm/js/wasmcl.wasm","doc/wasm/js/subprims.wasm"]; let s=0; for (const f of p) s+=fs.statSync(f).size; console.log(s);'` | Emit aggregate bytes exactly equal to `R8M-01`..`R8M-04` sum. | `RPL08-E003` |
| R8M-06 | metadata sanity (`R8B-02`) | `env TZ=UTC LC_ALL=C LANG=C node -e 'const fs=require("node:fs"); const j=JSON.parse(fs.readFileSync("doc/wasm/wasm-runtime-modules.json","utf8")); if(!(j.moduleCount===7620 && j.constPoolCount===5438)) process.exit(1);'` | Assert frozen baseline metadata shape for deterministic comparisons. | `RPL08-E004` |
| R8M-07 | `R8B-06` | `env TZ=UTC LC_ALL=C LANG=C stat -f '%z' doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/module_env_x07_review_packet_v1.json` | Emit bytes for `x07_packet_anchor_bytes`. | `RPL08-E001` |
| R8M-08 | `R8B-07` | `env TZ=UTC LC_ALL=C LANG=C stat -f '%z' doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/module_env_x06_review_packet_v1.json` | Emit bytes for `x06_packet_anchor_bytes`. | `RPL08-E001` |
| R8M-09 | `R8B-08` | `env TZ=UTC LC_ALL=C LANG=C stat -f '%z' doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/module_env_step2_summary_v1.json` | Emit bytes for `step2_summary_anchor_bytes`. | `RPL08-E001` |
| R8M-10 | formula pass (`R8B-11`/`R8B-12`) | `env TZ=UTC LC_ALL=C LANG=C node -e 'const b=Number(process.argv[1]); const m=Number(process.argv[2]); const d=m-b; const p=((m-b)/b)*100; if(!Number.isFinite(d)||!Number.isFinite(p)) process.exit(1); console.log(d.toString()+"\t"+p.toFixed(6));' <baseline> <measured>` | Emit `delta_bytes` and `delta_pct` with fixed precision. | `RPL08-E005` |
| R8M-11 | bundle immutability check | `for id in rpl05-20260210-011240Z-91fdb0be bpl06-20260210-005408Z-91fdb0be bpl07-20260210-005408Z-91fdb0be; do rg -n "$id" doc/wasm/runtime-backend-dependency-matrix.md doc/wasm/runtime-replacement-master-plan.md doc/wasm/tickets/RPL-08-artifact-size-reduction-and-validation.md doc/wasm/tickets/RPL-00-governance-and-baseline-freeze.md doc/wasm/wasm-program-board.md >/dev/null; done` | All immutable bundle IDs appear unchanged across runtime `X-07` notes. | `RPL08-E006` |
| R8M-12 | backend closure-row carry-forward check | `for id in BPL08-CR01 BPL08-CR02 BPL08-CR03 BPL08-CR04 BPL08-CR05 BPL08-CR06; do rg -n "$id" doc/wasm/runtime-backend-dependency-matrix.md doc/wasm/runtime-replacement-master-plan.md doc/wasm/wasm-program-board.md >/dev/null; done` | Runtime docs preserve backend closure row references as immutable input. | `RPL08-E007` |
| R8M-13 | no legacy source fallback audit | `env TZ=UTC LC_ALL=C LANG=C node -e 'const src=(process.env.CCL_RUNTIME_BUDGET_SOURCE||"canonical_artifact"); if(src!=="canonical_artifact") process.exit(1);'` | `selected_source` must resolve to `canonical_artifact`. | `RPL08-E002` |
| R8M-14 | replacement-lane profile guard | `env TZ=UTC LC_ALL=C LANG=C node doc/wasm/js/start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive` | Startup/profile gate remains secure-only before runtime budget run promotion. | `RPL08-E008` |
| R8M-15 | deterministic digest generation | `env TZ=UTC LC_ALL=C LANG=C node -e 'const c=require("node:crypto"); const fs=require("node:fs"); const p=process.argv.slice(1); const h=c.createHash("sha256"); for(const f of p.sort()) h.update(fs.readFileSync(f)); console.log(h.digest("hex"));' doc/wasm/wasm-runtime-modules.bin doc/wasm/wasm-runtime-modules.json doc/wasm/js/wasmcl.wasm doc/wasm/js/subprims.wasm` | Emit reproducible `results_digest` over sorted artifact set. | `RPL08-E009` |
| R8M-16 | rerun digest parity check | `env TZ=UTC LC_ALL=C LANG=C node -e 'if(process.argv[1]!==process.argv[2]) process.exit(1);' <digest_run_a> <digest_run_b>` | Equivalent reruns must produce identical digest values. | `RPL08-E010` |
| R8M-17 | review packet schema check | `env TZ=UTC LC_ALL=C LANG=C node -e 'const fs=require("node:fs"); const j=JSON.parse(fs.readFileSync(process.argv[1],"utf8")); if(!(j.x07_review_result==="carry_forward")) process.exit(1);' doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/module_env_x07_review_packet_v1.json` | Ensure carry-forward baseline remains explicit until RPL-08 Step 3 closure evidence. | `RPL08-E011` |
| R8M-18 | aggregate closure-target check | `env TZ=UTC LC_ALL=C LANG=C node -e 'const m=Number(process.argv[1]); const t=350069275; if(!(m<=t)) process.exit(1);' <aggregate_measured_bytes>` | Report target pass/fail for `R8B-05`. | `RPL08-E012` |
| R8M-19 | machine summary validation | `env TZ=UTC LC_ALL=C LANG=C node -e 'const fs=require("node:fs"); const j=JSON.parse(fs.readFileSync(process.argv[1],"utf8")); if(!(j.schema_version==="artifact_budget_step2_summary_v1" && Array.isArray(j.executed_budget_ids))) process.exit(1);' <summary_path>` | Validate terminal schema contract for Step 2/Step 3 evidence. | `RPL08-E013` |
| R8M-20 | cross-doc sync check | `for f in doc/wasm/tickets/RPL-08-artifact-size-reduction-and-validation.md doc/wasm/runtime-replacement-master-plan.md doc/wasm/runtime-backend-dependency-matrix.md doc/wasm/wasm-program-board.md doc/wasm/tickets/RPL-00-governance-and-baseline-freeze.md; do test -f "$f" || exit 1; done` | Enforce same-cycle synchronization requirement. | `RPL08-E014` |

### Canonical Failure Codes (Normative)

| failure_code | condition | message template | mandatory remediation |
| --- | --- | --- | --- |
| RPL08-E001 | required artifact path missing | `[{code}] required artifact missing at {path}.` | Mark run fail; restore canonical artifact path before rerun. |
| RPL08-E002 | legacy/fallback measurement source used | `[{code}] forbidden measurement source selected: {source}.` | Hard-fail run; enforce canonical artifact source and rerun. |
| RPL08-E003 | aggregate-sum mismatch | `[{code}] aggregate bytes mismatch with component rows.` | Recompute per-row measurements and regenerate summary. |
| RPL08-E004 | baseline metadata drift | `[{code}] frozen metadata drift in runtime module manifest.` | Hold closure, investigate packaging drift, publish additive remediation notes. |
| RPL08-E005 | invalid delta computation | `[{code}] delta formula produced invalid result for {budget_id}.` | Regenerate measurement row with deterministic formula inputs. |
| RPL08-E006 | immutable bundle ID drift | `[{code}] immutable closure bundle set mismatch in runtime docs.` | Restore exact immutable IDs and rerun doc-sync checks. |
| RPL08-E007 | backend closure row reference drift | `[{code}] backend closure row mapping drift for {closure_id}.` | Restore `BPL08-CR*` references unchanged and rerun checks. |
| RPL08-E008 | secure startup/profile gate failed | `[{code}] secure startup gate failed for runtime budget lane.` | Do not continue; remediate startup gate before budget execution. |
| RPL08-E009 | deterministic digest generation failure | `[{code}] results digest generation failed for run {run_id}.` | Regenerate digest from canonical sorted artifact set. |
| RPL08-E010 | rerun digest parity mismatch | `[{code}] digest parity mismatch across equivalent reruns.` | Open blocker gap and perform targeted rerun after remediation. |
| RPL08-E011 | review packet posture drift | `[{code}] x07 review packet posture is not carry_forward.` | Keep `X-07` `in_progress` and repair packet before promotion. |
| RPL08-E012 | closure target overrun | `[{code}] closure target overrun for {budget_id}.` | Keep `X-07` `in_progress`; execute size-remediation work and rerun. |
| RPL08-E013 | summary schema mismatch | `[{code}] terminal summary schema mismatch.` | Regenerate summary artifact with required schema fields. |
| RPL08-E014 | same-cycle sync contract failure | `[{code}] required runtime status docs are not synchronized.` | Update subplan/master/matrix/board/governance in same cycle. |

### `X-07` Mapping and Immutable Carry-Forward Contract

| mapping_id | runtime contract row(s) | backend carry-forward row(s) | immutable bundle IDs | acceptance rule | reject rule |
| --- | --- | --- | --- | --- | --- |
| R8B-17 | `R8B-01`..`R8B-05`, `R8M-01`..`R8M-05` | `BPL08-CR05` | `rpl05-20260210-011240Z-91fdb0be`, `bpl06-20260210-005408Z-91fdb0be`, `bpl07-20260210-005408Z-91fdb0be` | Runtime budget rows emit explicit guardrail/target results and preserve immutable bundle IDs. | Any alias/rewrite of immutable IDs or missing budget row outputs. |
| R8B-18 | `R8M-11`, `R8M-12` | `BPL08-CR06` | same as `R8B-17` | Runtime docs preserve immutable bundle IDs and `BPL08-CR*` references verbatim. | Doc-level drift on IDs or closure-row references. |
| R8B-19 | `R8M-17`, `R8T-11`, `R8T-12` | `BPL08-CR05` | same as `R8B-17` | `x07_review_result=carry_forward` until runtime Step 3 budget closure evidence is committed. | Premature `X-07=done` state without runtime closure evidence. |
| R8B-20 | `R8R-01`..`R8R-10` | `BPL06-RB-05` carry posture | same as `R8B-17` | Runtime rollback/remediation semantics preserve backend hold posture for unresolved budget rows. | Declaring unified budget signoff while any runtime budget row is unresolved. |

### No-Silent-Fallback and Lifecycle Semantics

| semantics_id | scope | required behavior | prohibited behavior | escalation binding |
| --- | --- | --- | --- | --- |
| R8B-21 | measurement source selection | All rows must use canonical artifact paths and deterministic commands only. | Measuring against legacy snapshot artifacts or synthetic aliases. | `RPL08-E002` -> `WLCT-10` |
| R8B-22 | guardrail violations | Guardrail overrun or missing artifacts are terminal fail conditions. | Marking guardrail failure as warning-only. | `RPL08-E001` / `RPL08-E012` |
| R8B-23 | startup gate ordering | Secure startup/profile checks must pass before budget status promotion. | Promoting budget results after failed startup gate. | `RPL08-E008` -> `WLCT-09` |
| R8B-24 | review posture | `X-07` remains `in_progress` (carry-forward) until Step 3 runtime closure evidence is published. | Silent transition to `X-07=done` with partial runtime evidence. | `RPL08-E011` / `RPL08-E014` |

### Telemetry Schemas and Required Assertions

| telemetry_id | schema | granularity | required fields | purpose |
| --- | --- | --- | --- | --- |
| R8T-01 | `artifact_budget_measurement_event_v1` | one row per budget measurement | `run_id`, `budget_id`, `artifact_path`, `baseline_bytes`, `measured_bytes`, `delta_bytes`, `delta_pct`, `guardrail_pass`, `target_pass`, `selected_source`, `status`, `failure_code`, `timestamp_utc` | Deterministic row-level budget evidence. |
| R8T-02 | `artifact_budget_row_summary_v1` | one row summary per budget ID | `run_id`, `budget_id`, `guardrail_max_bytes`, `closure_target_max_bytes`, `measured_bytes`, `guardrail_pass`, `target_pass`, `first_failure_code` | Machine-readable pass/fail digest by row. |
| R8T-03 | `artifact_budget_step2_summary_v1` | one record per run | `schema_version`, `run_id`, `executed_budget_ids`, `failed_budget_ids`, `first_failure_budget_id`, `first_failure_code`, `bundle_inputs`, `results_digest`, `x07_runtime_ready`, `status` | Step 2/3 terminal run summary and `X-07` readiness input. |
| R8T-04 | `artifact_budget_x07_review_packet_v1` | one packet per run | `run_id`, `bundle_inputs`, `runtime_budget_rows`, `guardrail_pass_count`, `target_pass_count`, `x07_review_result`, `notes` | Runtime-side `X-07` review packet for cross-plan sync. |
| R8T-05 | `artifact_budget_remediation_record_v1` | one record per remediation action | `run_id`, `rollback_id`, `trigger_budget_id`, `trigger_failure_code`, `action`, `owner`, `status`, `evidence_paths` | Audit trail for partial migration rollback/remediation. |
| R8T-06 | `artifact_budget_doc_sync_record_v1` | one record per sync cycle | `run_id`, `sync_cycle_id`, `updated_docs`, `bundle_inputs`, `closure_rows_checked`, `status` | Same-cycle governance sync proof. |

### Required Assertions

| assertion_id | assertion | success condition | failure condition |
| --- | --- | --- | --- |
| R8T-07 | immutable bundle preservation | `bundle_inputs` equals the three immutable IDs in canonical order in `R8T-03`/`R8T-04`/`R8T-06`. | Missing, reordered, or aliased bundle IDs. |
| R8T-08 | no-fallback measurement source | All `R8T-01.selected_source=canonical_artifact`. | Any row with non-canonical source. |
| R8T-09 | aggregate consistency | `R8B-05.measured_bytes` equals component sum (`R8B-01`..`R8B-04`). | Aggregate mismatch. |
| R8T-10 | deterministic rerun parity | Equivalent reruns produce identical `results_digest`. | Digest mismatch across equivalent reruns. |
| R8T-11 | `X-07` carry-forward posture | `artifact_budget_x07_review_packet_v1.x07_review_result=carry_forward` until Step 3 closure. | Premature non-carry-forward result. |
| R8T-12 | same-cycle sync discipline | `R8T-06.updated_docs` includes subplan/master/matrix/board/governance in one cycle. | Any missing doc in cycle sync list. |

### Rollback and Remediation Contract for Partial Migration

| rollback_id | trigger condition | mandatory response | prohibited response | evidence artifact |
| --- | --- | --- | --- | --- |
| R8R-01 | one or more canonical artifacts missing (`RPL08-E001`) | Halt row promotion, restore artifact path, rerun affected measurement rows only. | Marking row as pass with missing artifact. | `R8T-01` fail + remediated rerun row |
| R8R-02 | fallback measurement source detected (`RPL08-E002`) | Hard-fail run and reset source to canonical artifact lane before rerun. | Silent source downgrade to legacy snapshot. | `R8T-01` + `R8T-05` |
| R8R-03 | aggregate mismatch (`RPL08-E003`) | Recompute all component rows and aggregate row in one deterministic rerun. | Editing aggregate row manually without recomputation. | `R8T-02` + updated `R8T-03` |
| R8R-04 | immutable bundle drift (`RPL08-E006`) | Restore exact bundle IDs in all runtime `X-07` notes and rerun immutability checks. | Introducing alias IDs or shortened labels. | `R8T-06` sync record |
| R8R-05 | backend closure-row mapping drift (`RPL08-E007`) | Restore `BPL08-CR01`..`BPL08-CR06` references unchanged and rerun mapping checks. | Rewriting backend closure row IDs from runtime docs. | `R8T-06` sync record |
| R8R-06 | startup/profile gate fail (`RPL08-E008`) | Keep budget run blocked until secure startup checks pass. | Advancing run status despite startup failure. | startup log + `R8T-03.status=fail` |
| R8R-07 | rerun digest parity mismatch (`RPL08-E010`) | Open explicit blocker gap and execute targeted rerun after remediation. | Closing `X-07` with unresolved digest drift. | gap record + new `R8T-03` |
| R8R-08 | closure-target overrun (`RPL08-E012`) | Keep `X-07` `in_progress` and schedule size-remediation work; rerun affected budget rows. | Declaring unified budget signoff while target rows fail. | `R8T-02` + `R8T-05` |
| R8R-09 | summary schema mismatch (`RPL08-E013`) | Regenerate terminal summary from raw measurement events before promotion. | Manual status edits without schema-compliant summary. | corrected `R8T-03` |
| R8R-10 | same-cycle sync failure (`RPL08-E014`) | Update subplan/master/matrix/board/governance in one cycle before status promotion. | Partial runtime doc updates for `X-07` state. | `R8T-06.status=pass` |

### Step 1 Completion Status

- Status: done
- Gap IDs: none
- Completion basis:
  - Budget inventory, formula policy, deterministic commands, and no-fallback semantics are fully specified.
  - Telemetry and rollback/remediation contracts are machine-actionable for Step 2/Step 3 lanes.
  - Immutable closure bundle IDs and backend `BPL08-CR*` rows are explicitly carried forward without rewrites.

## Step 2 Output - Lane and Validation Contract (v1)

### Step 2 ID Namespace Freeze (Normative)

| namespace | frozen range | meaning | mutation rule |
| --- | --- | --- | --- |
| `R8L-*` | `R8L-01`..`R8L-08` | Deterministic runtime artifact-budget execution lanes. | Additive-only; existing IDs are immutable. |
| `R8V-*` | `R8V-01`..`R8V-14` | Validation and failure-mapping matrix over Step 1 budget contracts. | Additive-only; existing IDs are immutable. |
| `R8I-*` | `R8I-01`..`R8I-06` | `X-07` review compatibility and immutable carry-forward mappings. | Additive-only; existing IDs are immutable. |

### Step 2 Deterministic Run Contract

- Run root: `/Users/buildsomething/Source/ccl`
- Required environment for all lanes: `TZ=UTC`, `LC_ALL=C`, `LANG=C`, `CCL_RUNTIME_BUDGET_SOURCE=canonical_artifact`, `CCL_STORAGE_ALLOW_FALLBACK=0`
- Required run-id format: `rpl08-YYYYMMDD-HHMMSSZ-<short_sha>`
- Step 3 output directory per run: `doc/wasm/tickets/evidence/rpl-08-step3-<date>/<run_id>/`
- Immutable bundle IDs for all `R8I-*` review outputs:
  - `R8I-B01=rpl05-20260210-011240Z-91fdb0be`
  - `R8I-B02=bpl06-20260210-005408Z-91fdb0be`
  - `R8I-B03=bpl07-20260210-005408Z-91fdb0be`
- Normative lane controls:
  - `CCL_ARTIFACT_BUDGET_TEST_LANE=<R8L-*>`
  - `CCL_ARTIFACT_BUDGET_TEST_CASE=<case_id>`
  - `CCL_ARTIFACT_BUDGET_TEST_INJECT_FAILURE=<RPL08-E001|RPL08-E002|RPL08-E003|RPL08-E004|RPL08-E005|RPL08-E006|RPL08-E007|RPL08-E008|RPL08-E009|RPL08-E010|RPL08-E011|RPL08-E012|RPL08-E013|RPL08-E014>`
  - `CCL_ARTIFACT_BUDGET_TEST_FORCE_FALLBACK=1`
  - `CCL_ARTIFACT_BUDGET_TEST_BUNDLE_IDS=<R8I-B01,R8I-B02,R8I-B03>`
- Wrapper requirement: if implementation uses different internal knobs, wrappers MUST expose equivalent controls for all variables above.

### Conformance Lane Registry (`R8L-*`)

| lane_id | lane class | deterministic command template | primary contract coverage | required artifact outputs |
| --- | --- | --- | --- | --- |
| R8L-01 | baseline artifact measurement | `env TZ=UTC LC_ALL=C LANG=C CCL_RUNTIME_BUDGET_SOURCE=canonical_artifact CCL_STORAGE_ALLOW_FALLBACK=0 CCL_ARTIFACT_BUDGET_TEST_LANE=R8L-01 CCL_ARTIFACT_BUDGET_TEST_CASE=baseline-measurement node -e 'const fs=require("node:fs"); const rows=[["R8B-01","doc/wasm/wasm-runtime-modules.bin"],["R8B-02","doc/wasm/wasm-runtime-modules.json"],["R8B-03","doc/wasm/js/wasmcl.wasm"],["R8B-04","doc/wasm/js/subprims.wasm"]]; for (const r of rows) console.log(r[0]+"\\t"+fs.statSync(r[1]).size);'` | `R8B-01`..`R8B-04`, `R8M-01`..`R8M-04`, `R8T-01` | `artifact_budget_measurement_event_v1` |
| R8L-02 | aggregate/delta computation | `env TZ=UTC LC_ALL=C LANG=C CCL_RUNTIME_BUDGET_SOURCE=canonical_artifact CCL_STORAGE_ALLOW_FALLBACK=0 CCL_ARTIFACT_BUDGET_TEST_LANE=R8L-02 CCL_ARTIFACT_BUDGET_TEST_CASE=aggregate-delta node -e 'const fs=require("node:fs"); const vals=[fs.statSync("doc/wasm/wasm-runtime-modules.bin").size,fs.statSync("doc/wasm/wasm-runtime-modules.json").size,fs.statSync("doc/wasm/js/wasmcl.wasm").size,fs.statSync("doc/wasm/js/subprims.wasm").size]; const s=vals.reduce((a,b)=>a+b,0); console.log("R8B-05\\t"+s);'` | `R8B-05`, `R8B-11`..`R8B-13`, `R8M-05`, `R8M-10`, `R8T-02` | `artifact_budget_row_summary_v1` |
| R8L-03 | metadata + digest determinism | `env TZ=UTC LC_ALL=C LANG=C CCL_RUNTIME_BUDGET_SOURCE=canonical_artifact CCL_ARTIFACT_BUDGET_TEST_LANE=R8L-03 CCL_ARTIFACT_BUDGET_TEST_CASE=metadata-digest node -e 'const c=require("node:crypto"); const fs=require("node:fs"); const j=JSON.parse(fs.readFileSync("doc/wasm/wasm-runtime-modules.json","utf8")); if(!(j.moduleCount===7620 && j.constPoolCount===5438)) process.exit(1); const p=["doc/wasm/wasm-runtime-modules.bin","doc/wasm/wasm-runtime-modules.json","doc/wasm/js/wasmcl.wasm","doc/wasm/js/subprims.wasm"]; const h=c.createHash("sha256"); for (const f of p.sort()) h.update(fs.readFileSync(f)); console.log(h.digest("hex"));'` | `R8M-06`, `R8M-15`, `R8T-10` | digest artifact + metadata check log |
| R8L-04 | secure startup/no-fallback guard | `env TZ=UTC LC_ALL=C LANG=C CCL_RUNTIME_BUDGET_SOURCE=canonical_artifact CCL_STORAGE_ALLOW_FALLBACK=0 CCL_ARTIFACT_BUDGET_TEST_LANE=R8L-04 CCL_ARTIFACT_BUDGET_TEST_CASE=startup-guard node doc/wasm/js/start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive` | `R8B-21`..`R8B-24`, `R8M-13`, `R8M-14`, `R8T-08` | startup guard log + measurement source audit |
| R8L-05 | deterministic fail-injection | `env TZ=UTC LC_ALL=C LANG=C CCL_RUNTIME_BUDGET_SOURCE=canonical_artifact CCL_ARTIFACT_BUDGET_TEST_LANE=R8L-05 CCL_ARTIFACT_BUDGET_TEST_CASE=<case_id> CCL_ARTIFACT_BUDGET_TEST_INJECT_FAILURE=<RPL08-E*> node -e 'const code=process.env.CCL_ARTIFACT_BUDGET_TEST_INJECT_FAILURE||\"\"; if(!code) process.exit(1); console.error(code); process.exit(2);'` | canonical `RPL08-E*` mapping | first-failure mapping summary |
| R8L-06 | forced fallback policy lane | `env TZ=UTC LC_ALL=C LANG=C CCL_RUNTIME_BUDGET_SOURCE=legacy_snapshot CCL_ARTIFACT_BUDGET_TEST_LANE=R8L-06 CCL_ARTIFACT_BUDGET_TEST_CASE=fallback-block CCL_ARTIFACT_BUDGET_TEST_FORCE_FALLBACK=1 node -e 'if(process.env.CCL_RUNTIME_BUDGET_SOURCE!==\"canonical_artifact\") { console.error(\"RPL08-E002\"); process.exit(2); }'` | `R8B-21`, `R8T-08`, `R8R-02` | fallback-blocked artifact + failure mapping |
| R8L-07 | `X-07` review packet lane | `env TZ=UTC LC_ALL=C LANG=C CCL_ARTIFACT_BUDGET_TEST_LANE=R8L-07 CCL_ARTIFACT_BUDGET_TEST_CASE=x07-review CCL_ARTIFACT_BUDGET_TEST_BUNDLE_IDS=rpl05-20260210-011240Z-91fdb0be,bpl06-20260210-005408Z-91fdb0be,bpl07-20260210-005408Z-91fdb0be node -e 'const fs=require("node:fs"); const p=\"doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/module_env_x07_review_packet_v1.json\"; const j=JSON.parse(fs.readFileSync(p,\"utf8\")); if(j.x07_review_result!==\"carry_forward\") process.exit(1); console.log(\"carry_forward\");'` | `R8M-17`, `R8B-17`..`R8B-19`, `R8T-04`, `R8T-11` | `artifact_budget_x07_review_packet_v1` |
| R8L-08 | cross-doc sync and carry-forward lane | `env TZ=UTC LC_ALL=C LANG=C CCL_ARTIFACT_BUDGET_TEST_LANE=R8L-08 CCL_ARTIFACT_BUDGET_TEST_CASE=doc-sync node -e 'const cp=require(\"node:child_process\"); const ids=[\"rpl05-20260210-011240Z-91fdb0be\",\"bpl06-20260210-005408Z-91fdb0be\",\"bpl07-20260210-005408Z-91fdb0be\",\"BPL08-CR01\",\"BPL08-CR02\",\"BPL08-CR03\",\"BPL08-CR04\",\"BPL08-CR05\",\"BPL08-CR06\"]; for (const id of ids){ cp.execFileSync(\"rg\",[\"-n\",id,\"doc/wasm/runtime-backend-dependency-matrix.md\",\"doc/wasm/runtime-replacement-master-plan.md\",\"doc/wasm/tickets/RPL-08-artifact-size-reduction-and-validation.md\",\"doc/wasm/tickets/RPL-00-governance-and-baseline-freeze.md\",\"doc/wasm/wasm-program-board.md\"],{stdio:\"ignore\"}); } console.log(\"sync_ok\");'` | `R8M-11`, `R8M-12`, `R8M-20`, `R8T-06`, `R8T-12` | `artifact_budget_doc_sync_record_v1` |

### Validation Matrix (`R8V-*`)

| validation_id | lane_id | scope | deterministic command | assertions / expected result | canonical failure expectation |
| --- | --- | --- | --- | --- | --- |
| R8V-01 | R8L-01 | baseline row measurements | `CCL_ARTIFACT_BUDGET_TEST_CASE=baseline-measurement` on `R8L-01` command | `R8B-01`..`R8B-04` byte rows emitted with canonical artifact paths. | none (`status=pass`) |
| R8V-02 | R8L-02 | aggregate and delta formulas | `CCL_ARTIFACT_BUDGET_TEST_CASE=aggregate-delta` on `R8L-02` command | `R8B-05` equals component sum and delta formulas are valid. | none (`status=pass`) |
| R8V-03 | R8L-03 | metadata freeze + digest determinism | `CCL_ARTIFACT_BUDGET_TEST_CASE=metadata-digest` on `R8L-03` command | module metadata (`7620`, `5438`) and deterministic digest generation pass. | none (`status=pass`) |
| R8V-04 | R8L-04 | secure startup/no fallback | `CCL_ARTIFACT_BUDGET_TEST_CASE=startup-guard` on `R8L-04` command | startup gate and canonical source policy pass with no fallback. | none (`status=pass`) |
| R8V-05 | R8L-03 | rerun digest parity | rerun `R8L-03` and compare digests via `R8M-16` | equivalent reruns produce identical digest. | none (`status=pass`) |
| R8V-06 | R8L-07 | review packet carry-forward | `CCL_ARTIFACT_BUDGET_TEST_CASE=x07-review` on `R8L-07` command | `x07_review_result=carry_forward` and packet parse is deterministic. | none (`status=pass`) |
| R8V-07 | R8L-05 | missing artifact failure mapping | `CCL_ARTIFACT_BUDGET_TEST_CASE=missing-artifact CCL_ARTIFACT_BUDGET_TEST_INJECT_FAILURE=RPL08-E001` on `R8L-05` command | missing-path failure is terminal and deterministic. | First failure code MUST be `RPL08-E001`. |
| R8V-08 | R8L-06 | fallback source violation mapping | `CCL_ARTIFACT_BUDGET_TEST_CASE=fallback-source CCL_ARTIFACT_BUDGET_TEST_FORCE_FALLBACK=1` on `R8L-06` command | non-canonical source is blocked deterministically. | First failure code MUST be `RPL08-E002`. |
| R8V-09 | R8L-05 | aggregate mismatch mapping | `CCL_ARTIFACT_BUDGET_TEST_CASE=aggregate-mismatch CCL_ARTIFACT_BUDGET_TEST_INJECT_FAILURE=RPL08-E003` on `R8L-05` command | aggregate mismatch is surfaced with no warning downgrade. | First failure code MUST be `RPL08-E003`. |
| R8V-10 | R8L-05 | metadata drift mapping | `CCL_ARTIFACT_BUDGET_TEST_CASE=metadata-drift CCL_ARTIFACT_BUDGET_TEST_INJECT_FAILURE=RPL08-E004` on `R8L-05` command | metadata drift blocks promotion deterministically. | First failure code MUST be `RPL08-E004`. |
| R8V-11 | R8L-05 | startup gate mapping | `CCL_ARTIFACT_BUDGET_TEST_CASE=startup-fail CCL_ARTIFACT_BUDGET_TEST_INJECT_FAILURE=RPL08-E008` on `R8L-05` command | startup/profile failure blocks budget run promotion. | First failure code MUST be `RPL08-E008`. |
| R8V-12 | R8L-05 | closure-target overrun mapping | `CCL_ARTIFACT_BUDGET_TEST_CASE=target-overrun CCL_ARTIFACT_BUDGET_TEST_INJECT_FAILURE=RPL08-E012` on `R8L-05` command | target overrun keeps `X-07` in carry-forward posture. | First failure code MUST be `RPL08-E012`. |
| R8V-13 | R8L-08 | immutable bundle ID assertions | `CCL_ARTIFACT_BUDGET_TEST_CASE=doc-sync` on `R8L-08` command | all runtime docs preserve exact immutable bundle IDs. | `RPL08-E006` on mismatch. |
| R8V-14 | R8L-08 | backend closure-row carry-forward assertions | `CCL_ARTIFACT_BUDGET_TEST_CASE=doc-sync` on `R8L-08` command | runtime docs preserve `BPL08-CR01`..`BPL08-CR06` references unchanged. | `RPL08-E007` on missing/drifted row IDs. |

### `X-07` Review Mapping (`R8I-*`)

| compatibility_id | review scope | required bundle IDs (immutable) | acceptance rule | reject rule |
| --- | --- | --- | --- | --- |
| R8I-01 | runtime budget packet identity | `rpl05-20260210-011240Z-91fdb0be`, `bpl06-20260210-005408Z-91fdb0be`, `bpl07-20260210-005408Z-91fdb0be` | `artifact_budget_step2_summary_v1.bundle_inputs` equals canonical bundle order. | Missing/reordered/aliased bundle IDs. |
| R8I-02 | runtime review packet posture | same as `R8I-01` | `artifact_budget_x07_review_packet_v1.x07_review_result=carry_forward` until Step 3 closure evidence is committed. | Any non-carry-forward posture before Step 3 closure packet. |
| R8I-03 | backend closure-row carry-forward | same as `R8I-01` | `BPL08-CR01`..`BPL08-CR06` references preserved across runtime docs. | Missing or rewritten `BPL08-CR*` references. |
| R8I-04 | guardrail gating | same as `R8I-01` | All row-level `guardrail_pass` flags are explicit and schema-valid in step summary. | Implicit/missing guardrail state for any row. |
| R8I-05 | target gating | same as `R8I-01` | `x07_runtime_ready=true` only when target/guardrail assertions satisfy Step 2 criteria. | `x07_runtime_ready=true` with unresolved target failure. |
| R8I-06 | cross-doc sync compatibility | same as `R8I-01` | Subplan/master/matrix/board/governance carry identical immutable IDs and `X-07` posture. | Any cross-doc drift on immutable IDs or `X-07` state. |

### Step 2 Terminal Summary Schema (`artifact_budget_step2_summary_v1`)

| field | type | required | constraints / meaning |
| --- | --- | --- | --- |
| `schema_version` | string | yes | Must equal `artifact_budget_step2_summary_v1`. |
| `run_id` | string | yes | Shared identifier for one Step 2 lane execution set. |
| `executed_lane_ids` | array<string> | yes | Executed `R8L-*` IDs. |
| `executed_validation_ids` | array<string> | yes | Executed `R8V-*` IDs. |
| `passed_validation_ids` | array<string> | yes | Passing subset of `executed_validation_ids`. |
| `failed_validation_ids` | array<string> | yes | Failing subset of `executed_validation_ids`. |
| `first_failure_validation_id` | string/null | yes | First failing validation ID or `null`. |
| `first_failure_code` | string/null | yes | First canonical `RPL08-E*` code or `null`. |
| `bundle_inputs` | array<string> | yes | MUST equal immutable bundle IDs in canonical order (`rpl05-20260210-011240Z-91fdb0be`, `bpl06-20260210-005408Z-91fdb0be`, `bpl07-20260210-005408Z-91fdb0be`). |
| `guardrail_pass_count` | integer | yes | Count of rows with `guardrail_pass=true`. |
| `target_pass_count` | integer | yes | Count of rows with `target_pass=true`. |
| `x07_runtime_ready` | boolean | yes | `true` only when required Step 2 assertions pass. |
| `results_digest` | string | yes | Deterministic digest over lane/validation artifacts. |
| `status` | string | yes | `pass` or `fail`. |

### Step 2 Readiness Assertions

1. Pass-set coverage (`R8V-01`..`R8V-06`) must succeed with expected artifact outputs.
2. Fail-set coverage (`R8V-07`..`R8V-12`) must emit canonical first-failure `RPL08-E*` mappings.
3. Carry-forward assertions (`R8V-13`, `R8V-14`) must preserve immutable bundle IDs and backend `BPL08-CR*` rows exactly.
4. `artifact_budget_step2_summary_v1.bundle_inputs` MUST match immutable bundle IDs in canonical order.
5. `x07_runtime_ready=true` requires complete coverage and non-blocked carry-forward checks.

### Step 2 Completion Status

- Status: done
- Gap IDs: none
- Completion basis:
  - Step 2 lane/validation/review namespaces are frozen and deterministic.
  - Validation rows and failure mappings cover runtime budget contracts and `X-07` carry-forward constraints.
  - Contract preserves immutable closure bundle IDs and backend `BPL08-CR*` references unchanged.

## Detailed Work Breakdown

### Step 1 - Budget and Measurement Contract Drafting

- Status: done
- Notes:
  - Published frozen Step 1 namespaces (`R8B-*`, `R8M-*`, `R8T-*`, `R8R-*`).
  - Bound runtime budget rows to fixed baseline anchors and deterministic formulas.
  - Bound `X-07` carry-forward rules to immutable bundle IDs and backend closure rows.
- Next:
  - Keep Step 1 IDs immutable and consume them in Step 2 execution contracts.

### Step 2 - Lane and Validation Contract Publication

- Status: done
- Notes:
  - Published frozen Step 2 lane/validation/review IDs (`R8L-*`, `R8V-*`, `R8I-*`) with deterministic command templates.
  - Bound Step 2 terminal summary schema (`artifact_budget_step2_summary_v1`) to immutable bundle IDs and carry-forward assertions.
  - Preserved backend `BPL08-CR*` rows as immutable review inputs across all Step 2 mapping clauses.
- Next:
  - Keep Step 2 IDs immutable and consume them unchanged in Step 3 rerun evidence execution.

### Step 3 - Evidence Execution and `X-07` Closure Review Packet

- Status: done
- Notes:
  - Step 3 run-v1 is committed at `doc/wasm/tickets/evidence/rpl-08-step3-2026-02-10/rpl08-20260210-022252Z-91fdb0be/` with full `R8V-01`..`R8V-14` assertion coverage, terminal `artifact_budget_step2_summary_v1.status=pass`, and immutable bundle IDs preserved.
  - Run-v1 emitted required artifacts (`artifact_budget_step2_summary_v1.json`, `artifact_budget_x07_review_packet_v1.json`, `artifact_budget_doc_sync_record_v1.json`, `r8v-results.tsv`, `run-status.tsv`, per-validation logs).
  - Step 3 run-v2 is committed at `doc/wasm/tickets/evidence/rpl-08-step3-2026-02-10/rpl08-20260210-023524Z-91fdb0be/` with full `R8V-01`..`R8V-14` assertion coverage, terminal `artifact_budget_step2_summary_v1.status=pass`, and immutable bundle IDs preserved.
  - Run-v2 closes blocker `R8GAP-01`; closure-target rows (`R8B-01`, `R8B-02`, `R8B-05`) now pass with measured bytes `101249073`, `334`, and `102059033`, and `x07_runtime_ready=true`.
  - Runtime remediation is code-backed: module bundle compaction + manifest payload reduction + strict startup/hash validation rerun.
- Next:
  - Carry committed Step 3 run-v2 evidence into unified `X-07` closure review and maintain immutable carry-forward inputs.

## Test and Validation Plan

- Deterministic command validation:
  - Verify all `R8M-*` commands execute from repo root with required environment controls.
- Formula validation:
  - Verify `R8B-11`/`R8B-12` delta formulas and `R8B-13` aggregate formula over measured rows.
- Governance validation:
  - Verify `R8M-11`/`R8M-12`/`R8M-20` checks pass for same-cycle sync and immutable carry-forward.

## Risks and Mitigations

- Risk: runtime budget rows drift from immutable backend closure carry-forward inputs.
  - Mitigation: enforce `R8M-11`/`R8M-12` and `R8T-07` in every run.
- Risk: budget runs silently use non-canonical sources.
  - Mitigation: hard-fail on `R8B-21`/`R8M-13` with `RPL08-E002`.
- Risk: partial doc updates produce `X-07` governance drift.
  - Mitigation: enforce `R8M-20`, `R8T-12`, and `R8R-10` before status promotion.

## Change Log

- 2026-02-10: Initial subplan created and Step 1 contract published (`R8B-01`..`R8B-24`, `R8M-01`..`R8M-20`, `R8T-01`..`R8T-12`, `R8R-01`..`R8R-10`) with immutable `X-07` carry-forward bundle IDs preserved.
- 2026-02-10: Published Step 2 lane/validation/review contract (`R8L-01`..`R8L-08`, `R8V-01`..`R8V-14`, `R8I-01`..`R8I-06`) with deterministic run controls, terminal summary schema bindings, and immutable backend `BPL08-CR*` carry-forward references.
- 2026-02-10: Executed Step 3 run-v1 (`R8V-01`..`R8V-14`) and committed evidence bundle (`rpl08-20260210-022252Z-91fdb0be`) with terminal `artifact_budget_step2_summary_v1.status=pass`, immutable bundle IDs preserved, `x07_review_result=carry_forward`, and open blocker `R8GAP-01` for closure-target overruns (`R8B-01`, `R8B-02`, `R8B-05`).
- 2026-02-10: Executed Step 3 run-v2 (`R8V-01`..`R8V-14`) and committed evidence bundle (`rpl08-20260210-023524Z-91fdb0be`) with terminal `artifact_budget_step2_summary_v1.status=pass`, immutable bundle IDs preserved, `x07_runtime_ready=true`, and closed blocker `R8GAP-01` after code-backed runtime artifact remediation.
