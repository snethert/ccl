# BPL-06 - Dual-Path Build and Differential Harness

Status: in_progress  
Priority: P0  
Owner: Compiler/backend migration track  
Last Updated: 2026-02-09  
Parent Plan: `doc/wasm/backend-migration-master-plan.md`

## Scope

In scope:

- Define dual-path backend execution contract for compat vs native lowering lanes.
- Publish deterministic differential checkpoints `BPL06-CP01`..`BPL06-CP05` mapped one-to-one to `B5M-*` seam contracts.
- Define evidence artifact schema and rollback invocation requirements for checkpoint reruns.

Out of scope:

- Numeric/lowering implementation changes inside compiler/subprims (BPL-05 ownership).
- Size/perf budget signoff and thresholds (BPL-07 ownership).
- Runtime/UI bridge migration design (RPL-04 ownership).

## Dependencies

- BPL-03 frame/debug baseline (`FDC-01`..`FDC-10`).
- BPL-04 benchmark gate outputs (`BPL04-G01`..`BPL04-G06`).
- BPL-05 seam and handoff outputs (`B5S-01`..`B5S-05`, `B5M-01`..`B5M-05`, `B5H-01`, `B5H-02`).
- Cross-track dependency row `X-04` remains parallel/open.

## Deliverables

1. Step 1 dual-build contract and deterministic checkpoint matrix (`BPL06-CP01`..`BPL06-CP05`).
2. Step 2 parity fixture set and evidence artifact schema with runnable command templates.
3. Step 3 triage and promotion workflow that feeds BPL-07 and BPL-08 gate consumers.

## Exit Criteria

- Every BPL-05 seam row has exactly one deterministic BPL-06 checkpoint row.
- Each checkpoint defines compat/native command legs, parity assertions, and rollback trigger linkage.
- Evidence artifacts are schema-bound and replayable without re-discovery.
- Cross-track `X-04` integration check requirements are explicit and consumable.

## Current Notes

- BPL-05 Step 2/3 requires this ticket to publish non-alias checkpoint IDs and deterministic rollback execution order (`B5H-01`, `B5H-02`).
- Existing aggregate and strict smoke harness commands already exist for checkpoint lanes:
  - `node doc/wasm/js/all-smoke.mjs` (`--no-ui` lane available).
  - `node doc/wasm/js/start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive`.
- Step 1 contract output is now published below and consumes all seam IDs `B5M-01`..`B5M-05`.
- Step 2 fixture matrix and artifact templates are now published below with deterministic run preconditions and checkpoint-complete coverage.

## Immediate Next Step

- Action: execute BPL-06 Step 3 by defining promotion-blocking triage workflow and downstream evidence handoff rules for BPL-07/BPL-08 consumers.
- Why now: Step 2 fixtures/templates are now frozen, so the next blocker is deterministic triage/promotion governance over emitted checkpoint evidence.
- Success evidence: Step 3 publishes severity classes, rollback obligations, and BPL-07/BPL-08 intake contracts keyed to `BPL06-CP01`..`BPL06-CP05`.

## Step 1 Output - Dual-Build Checkpoint Contract Matrix (v1)

### Checkpoint Matrix

| checkpoint_id | linked_seam | contract objective | compat leg command template | native leg command template | deterministic parity assertions | rollback trigger linkage | gate anchors | source anchors |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BPL06-CP01 | `B5M-01` | Numeric callsite parity before promoting `WASM_LOWERING_NUMERIC_CALLSITE_MODE=native`. | `WASM_LOWERING_PROMOTION_POLICY=hold WASM_LOWERING_NUMERIC_CALLSITE_MODE=compat node doc/wasm/js/all-smoke.mjs --no-ui` | `WASM_LOWERING_PROMOTION_POLICY=hold WASM_LOWERING_NUMERIC_CALLSITE_MODE=native node doc/wasm/js/all-smoke.mjs --no-ui` | Both runs exit `0`; both include `PASS: all wasm smoke tests`; no mismatch in checkpoint comparison fields (`exit_code`, `fail_markers`, `stdout_sha256`). | On mismatch/regression, execute `WASM_LOWERING_NUMERIC_CALLSITE_MODE=compat` rollback command path from `B5M-01`. | `BPL04-G01`, `BPL04-G02`, `CON-03`, `CON-04` | `doc/wasm/backend-tickets/BPL-05-ir-lowering-arm-decoupling.md:76`; `doc/wasm/js/all-smoke.mjs:7`; `doc/wasm/js/all-smoke.mjs:79`; `doc/wasm/js/all-smoke.mjs:94` |
| BPL06-CP02 | `B5M-02` | Entrypoint lookup parity before promoting `WASM_ENTRYPOINT_LOOKUP_MODE=manifest`. | `WASM_LOWERING_PROMOTION_POLICY=hold WASM_ENTRYPOINT_LOOKUP_MODE=slot node doc/wasm/js/all-smoke.mjs --no-ui` | `WASM_LOWERING_PROMOTION_POLICY=hold WASM_ENTRYPOINT_LOOKUP_MODE=manifest node doc/wasm/js/all-smoke.mjs --no-ui` | Both runs exit `0`; no manifest/entrypoint mismatch markers; parity summary fields are identical for command exit and failure-code sets. | On mismatch/regression, execute `WASM_ENTRYPOINT_LOOKUP_MODE=slot` rollback command path from `B5M-02`. | `BPL04-G03`, `CON-05`, `CON-03` | `doc/wasm/backend-tickets/BPL-05-ir-lowering-arm-decoupling.md:77`; `doc/wasm/js/all-smoke.mjs:30`; `doc/wasm/js/all-smoke.mjs:31` |
| BPL06-CP03 | `B5M-03` | Helper-dispatch parity before promoting `WASM_DIV_HELPER_MODE=native`. | `WASM_LOWERING_PROMOTION_POLICY=hold WASM_DIV_HELPER_MODE=compat node doc/wasm/js/all-smoke.mjs --no-ui` | `WASM_LOWERING_PROMOTION_POLICY=hold WASM_DIV_HELPER_MODE=native node doc/wasm/js/all-smoke.mjs --no-ui` | Both runs exit `0`; no no-fallback policy failure markers; helper-lane mismatch count is zero. | On mismatch/regression, execute `WASM_DIV_HELPER_MODE=compat` rollback command path from `B5M-03`. | `BPL04-G04`, `CON-06`, `CON-03` | `doc/wasm/backend-tickets/BPL-05-ir-lowering-arm-decoupling.md:78`; `doc/wasm/js/all-smoke.mjs:94` |
| BPL06-CP04 | `B5M-04` | Tailcall/frame parity before promoting `WASM_TAILCALL_NUMERIC_MODE=frame_reuse`. | `WASM_LOWERING_PROMOTION_POLICY=hold WASM_TAILCALL_NUMERIC_MODE=wrapper node doc/wasm/js/all-smoke.mjs --no-ui` and `WASM_LOWERING_PROMOTION_POLICY=hold WASM_TAILCALL_NUMERIC_MODE=wrapper node doc/wasm/js/start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive` | `WASM_LOWERING_PROMOTION_POLICY=hold WASM_TAILCALL_NUMERIC_MODE=frame_reuse node doc/wasm/js/all-smoke.mjs --no-ui` and `WASM_LOWERING_PROMOTION_POLICY=hold WASM_TAILCALL_NUMERIC_MODE=frame_reuse node doc/wasm/js/start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive` | Both command pairs exit `0`; strict lane preserves `wasm_ccl_start_lisp rc=0`; no frame/debug invariant mismatch in comparison summary. | On mismatch/regression, execute `WASM_TAILCALL_NUMERIC_MODE=wrapper` rollback command path from `B5M-04`. | `BPL04-G05`, `FDC-10`, `FDC-03` | `doc/wasm/backend-tickets/BPL-05-ir-lowering-arm-decoupling.md:79`; `doc/wasm/js/start-lisp-noninteractive-smoke.mjs:84`; `doc/wasm/js/start-lisp-noninteractive-smoke.mjs:152`; `doc/wasm/js/start-lisp-noninteractive-smoke.mjs:173` |
| BPL06-CP05 | `B5M-05` | Cross-slice promotion governance parity and freeze/advance control. | `WASM_LOWERING_PROMOTION_POLICY=hold node doc/wasm/js/all-smoke.mjs --no-ui` | `WASM_LOWERING_PROMOTION_POLICY=advance node doc/wasm/js/all-smoke.mjs --no-ui` | Promotion remains blocked unless `BPL06-CP01`..`BPL06-CP04` are green and aggregate lane parity is clean; any unresolved mismatch forces hold posture. | On mismatch/regression, execute `WASM_LOWERING_PROMOTION_POLICY=hold` rollback command path from `B5M-05`. | `BPL04-G06`, `CON-08` | `doc/wasm/backend-tickets/BPL-05-ir-lowering-arm-decoupling.md:80`; `doc/wasm/js/all-smoke.mjs:94` |

### Normative Evidence Artifact Contract (Step 1 freeze)

Each checkpoint run in Step 2/Step 3 MUST emit one artifact per leg (`compat`, `native`) using the schema below:

| field | requirement |
| --- | --- |
| `run_id` | Required, unique (`YYYYMMDD-HHMMSSZ-<short_sha>`). |
| `checkpoint_id` | Required, one of `BPL06-CP01`..`BPL06-CP05`. |
| `seam_id` | Required, one of `B5M-01`..`B5M-05` (one-to-one with `checkpoint_id`). |
| `leg` | Required, `compat` or `native`. |
| `lane_class` | Required, `headless_runtime` or `ui_runtime`; Step 2 defaults to `headless_runtime`. |
| `command` | Required, fully materialized command line executed for this leg. |
| `exit_code` | Required integer; parity requires same value across legs and expected `0` for pass. |
| `fail_markers` | Required array; parity requires exact match and empty for pass lanes. |
| `stdout_sha256` | Required hash of normalized stdout payload. |
| `stderr_sha256` | Required hash of normalized stderr payload. |
| `gate_refs` | Required list of `BPL04-G*`/`CON-*`/`FDC-*` anchors from checkpoint row. |
| `rollback_command` | Required command string copied from linked `B5M-*` row. |

Artifact location contract for Step 2 execution:

- `doc/wasm/tickets/evidence/bpl-06/<run_id>/BPL06-CP0X-compat.json`
- `doc/wasm/tickets/evidence/bpl-06/<run_id>/BPL06-CP0X-native.json`
- `doc/wasm/tickets/evidence/bpl-06/<run_id>/BPL06-CP0X-diff-summary.json`

Step 1 closure assertions:

1. Every seam row `B5M-01`..`B5M-05` is now bound to exactly one checkpoint row `BPL06-CP01`..`BPL06-CP05`.
2. Every checkpoint row has explicit compat/native command templates, deterministic parity assertions, and rollback linkage.
3. Evidence schema and path contracts are frozen so Step 2 can execute without re-defining checkpoint semantics.

## Step 2 Output - Parity Fixture Matrix and Evidence Templates (v1)

### Deterministic Run Preconditions (all fixtures)

1. Run from repository root: `/Users/buildsomething/Source/ccl`.
2. Force stable process environment before each leg:
   - `TZ=UTC`
   - `LC_ALL=C`
   - `LANG=C`
   - `CCL_IPC_TEST_INJECT_FAILURE` unset/empty.
3. Force lane class deterministically:
   - `CCL_IPC_LANE_ID=headless_runtime`
   - `CCL_IPC_CONFORMANCE_ID=<checkpoint_id>`.
4. Capture per-leg stdout/stderr logs and compute normalized hashes for artifact fields `stdout_sha256` and `stderr_sha256`.
5. Compare compat/native case artifacts only on frozen parity fields: `exit_code`, `fail_markers`, `stdout_sha256`, `stderr_sha256`.

### Fixture Matrix

| fixture_id | checkpoint_id | seam_id | lane_class | compat leg command | native leg command | comparator template | artifacts emitted | source anchors |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BPL06-FX01 | `BPL06-CP01` | `B5M-01` | `headless_runtime` | `WASM_LOWERING_PROMOTION_POLICY=hold WASM_LOWERING_NUMERIC_CALLSITE_MODE=compat node doc/wasm/js/all-smoke.mjs --no-ui` | `WASM_LOWERING_PROMOTION_POLICY=hold WASM_LOWERING_NUMERIC_CALLSITE_MODE=native node doc/wasm/js/all-smoke.mjs --no-ui` | `BPL06-CMP-01` | `BPL06-CP01-compat.json`, `BPL06-CP01-native.json`, `BPL06-CP01-diff-summary.json` | `doc/wasm/backend-tickets/BPL-05-ir-lowering-arm-decoupling.md:76`; `doc/wasm/js/all-smoke.mjs:7`; `doc/wasm/js/all-smoke.mjs:79`; `doc/wasm/js/all-smoke.mjs:94` |
| BPL06-FX02 | `BPL06-CP02` | `B5M-02` | `headless_runtime` | `WASM_LOWERING_PROMOTION_POLICY=hold WASM_ENTRYPOINT_LOOKUP_MODE=slot node doc/wasm/js/all-smoke.mjs --no-ui` | `WASM_LOWERING_PROMOTION_POLICY=hold WASM_ENTRYPOINT_LOOKUP_MODE=manifest node doc/wasm/js/all-smoke.mjs --no-ui` | `BPL06-CMP-01` | `BPL06-CP02-compat.json`, `BPL06-CP02-native.json`, `BPL06-CP02-diff-summary.json` | `doc/wasm/backend-tickets/BPL-05-ir-lowering-arm-decoupling.md:77`; `doc/wasm/js/all-smoke.mjs:30`; `doc/wasm/js/all-smoke.mjs:31`; `doc/wasm/js/all-smoke.mjs:94` |
| BPL06-FX03 | `BPL06-CP03` | `B5M-03` | `headless_runtime` | `WASM_LOWERING_PROMOTION_POLICY=hold WASM_DIV_HELPER_MODE=compat node doc/wasm/js/all-smoke.mjs --no-ui` | `WASM_LOWERING_PROMOTION_POLICY=hold WASM_DIV_HELPER_MODE=native node doc/wasm/js/all-smoke.mjs --no-ui` | `BPL06-CMP-01` | `BPL06-CP03-compat.json`, `BPL06-CP03-native.json`, `BPL06-CP03-diff-summary.json` | `doc/wasm/backend-tickets/BPL-05-ir-lowering-arm-decoupling.md:78`; `doc/wasm/js/all-smoke.mjs:94` |
| BPL06-FX04 | `BPL06-CP04` | `B5M-04` | `headless_runtime` | `WASM_LOWERING_PROMOTION_POLICY=hold WASM_TAILCALL_NUMERIC_MODE=wrapper node doc/wasm/js/all-smoke.mjs --no-ui && WASM_LOWERING_PROMOTION_POLICY=hold WASM_TAILCALL_NUMERIC_MODE=wrapper node doc/wasm/js/start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive` | `WASM_LOWERING_PROMOTION_POLICY=hold WASM_TAILCALL_NUMERIC_MODE=frame_reuse node doc/wasm/js/all-smoke.mjs --no-ui && WASM_LOWERING_PROMOTION_POLICY=hold WASM_TAILCALL_NUMERIC_MODE=frame_reuse node doc/wasm/js/start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive` | `BPL06-CMP-01` | `BPL06-CP04-compat.json`, `BPL06-CP04-native.json`, `BPL06-CP04-diff-summary.json` | `doc/wasm/backend-tickets/BPL-05-ir-lowering-arm-decoupling.md:79`; `doc/wasm/js/start-lisp-noninteractive-smoke.mjs:84`; `doc/wasm/js/start-lisp-noninteractive-smoke.mjs:152`; `doc/wasm/js/start-lisp-noninteractive-smoke.mjs:180` |
| BPL06-FX05 | `BPL06-CP05` | `B5M-05` | `headless_runtime` | `WASM_LOWERING_PROMOTION_POLICY=hold node doc/wasm/js/all-smoke.mjs --no-ui` | `WASM_LOWERING_PROMOTION_POLICY=advance node doc/wasm/js/all-smoke.mjs --no-ui` | `BPL06-CMP-01` | `BPL06-CP05-compat.json`, `BPL06-CP05-native.json`, `BPL06-CP05-diff-summary.json` | `doc/wasm/backend-tickets/BPL-05-ir-lowering-arm-decoupling.md:80`; `doc/wasm/js/all-smoke.mjs:94` |

### Comparator Template - `BPL06-CMP-01`

Use this command template after generating `compat` and `native` case artifacts:

```bash
node -e '
const fs = require("node:fs");
const compat = JSON.parse(fs.readFileSync(process.argv[1], "utf8"));
const native = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const required = ["exit_code", "fail_markers", "stdout_sha256", "stderr_sha256"];
const mismatch_fields = required.filter((field) =>
  JSON.stringify(compat[field]) !== JSON.stringify(native[field])
);
const summary = {
  schema_version: "backend_diff_checkpoint_summary_v1",
  run_id: compat.run_id,
  checkpoint_id: compat.checkpoint_id,
  seam_id: compat.seam_id,
  fixture_id: compat.fixture_id,
  lane_class: compat.lane_class,
  compat_case_path: process.argv[1],
  native_case_path: process.argv[2],
  required_equal_fields: required,
  mismatch_fields,
  mismatch_count: mismatch_fields.length,
  result: mismatch_fields.length === 0 ? "pass" : "fail",
  rollback_required: mismatch_fields.length > 0,
  rollback_command: compat.rollback_command,
  gate_refs: compat.gate_refs,
  generated_at_utc: new Date().toISOString()
};
fs.writeFileSync(process.argv[3], JSON.stringify(summary, null, 2) + "\n");
if (mismatch_fields.length > 0) process.exit(1);
' \
"<compat_case.json>" \
"<native_case.json>" \
"<diff_summary.json>"
```

### Published Evidence Template Files

- `doc/wasm/tickets/evidence/bpl-06/templates/backend_diff_case_result_v1.template.json`
- `doc/wasm/tickets/evidence/bpl-06/templates/backend_diff_checkpoint_summary_v1.template.json`
- `doc/wasm/tickets/evidence/bpl-06/templates/bpl06-fixture-matrix-v1.tsv`

Step 2 closure assertions:

1. All frozen checkpoints `BPL06-CP01`..`BPL06-CP05` now have deterministic fixture rows (`BPL06-FX01`..`BPL06-FX05`).
2. Comparator semantics are frozen under `BPL06-CMP-01` with checkpoint-pass/fail determined only by required parity fields.
3. Machine-fillable evidence templates are now published on disk for both case-level and checkpoint-summary artifacts.

## Detailed Work Breakdown

### Step 1 - Dual-Build Contract Freeze

- Status: done
- Notes:
  - Published deterministic checkpoint contract matrix `BPL06-CP01`..`BPL06-CP05`.
  - Bound each checkpoint row one-to-one to seam rows `B5M-01`..`B5M-05` with explicit rollback linkage.
  - Froze evidence artifact schema and output path contract for Step 2 execution.
- Next:
  - Keep checkpoint IDs and seam linkage immutable while Step 2 fixtures are authored.

### Step 2 - Parity Fixture Set and Artifact Templates

- Status: done
- Notes:
  - Published fixture matrix `BPL06-FX01`..`BPL06-FX05` with deterministic preconditions and full checkpoint coverage.
  - Published comparator template `BPL06-CMP-01` and artifact templates for `backend_diff_case_result_v1` and `backend_diff_checkpoint_summary_v1`.
- Next:
  - Keep fixture and template IDs stable; evolve additively when new checkpoints are introduced.

### Step 3 - Triage and Consumer Gate Integration

- Status: planned
- Notes:
  - Must route checkpoint outcomes into BPL-07 perf gates and BPL-08 runtime-alignment intake checks.
- Next:
  - Define promotion-blocking triage policy and downstream evidence handoff rules.

## Test and Validation Plan

- Contract linkage validation:
  - Verify every `BPL06-CP*` row references exactly one `B5M-*` row and no seam row is unreferenced.
- Command-lane validation:
  - Verify all command templates map to existing runnable harness scripts and flags.
- Evidence-schema validation:
  - Verify required artifact fields are sufficient to compare compat/native outcomes deterministically.
- Governance sync validation:
  - Verify master plan, dependency matrix, and program board next-step language matches this ticket.

## Risks and Mitigations

- Risk: dual-path runs become non-deterministic across lane classes.
  - Mitigation: default Step 2 checkpoint runs to `--no-ui` headless lane and hash normalized outputs.
- Risk: checkpoint IDs drift from seam IDs and break rollback mapping.
  - Mitigation: enforce one-to-one `checkpoint_id`/`seam_id` mapping in this ticket and downstream consumers.
- Risk: parity pass/fail decisions become subjective.
  - Mitigation: freeze machine-actionable parity fields (`exit_code`, `fail_markers`, `stdout_sha256`, `stderr_sha256`) in Step 1.

## Change Log

- 2026-02-09: Initialized BPL-06 and closed Step 1 with deterministic checkpoint contract matrix (`BPL06-CP01`..`BPL06-CP05`) mapped to seam contracts (`B5M-01`..`B5M-05`) plus evidence artifact schema freeze.
- 2026-02-09: Closed Step 2 by publishing parity fixture matrix (`BPL06-FX01`..`BPL06-FX05`), comparator template (`BPL06-CMP-01`), and machine-fillable evidence templates for all frozen checkpoints.
