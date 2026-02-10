# BPL-07 - Size and Performance Gates

Status: in_progress  
Priority: P1  
Owner: Compiler/backend migration track  
Last Updated: 2026-02-10  
Parent Plan: `doc/wasm/backend-migration-master-plan.md`

## Scope

In scope:

- Define backend performance and artifact-size budget baselines keyed to frozen `BPL06-CP01`..`BPL06-CP05` checkpoints.
- Freeze deterministic measurement command templates and evidence paths for repeatable reruns.
- Provide machine-actionable pass/fail interpretations that consume `BPL06-INT-*`, `BPL06-SEV-*`, and `BPL06-RB-*` contracts.

Out of scope:

- Differential parity semantics and triage class definitions (owned by BPL-06).
- Runtime storage semantics and local/remote persistence migration (owned by RPL-05/RPL-06).
- Final cross-track signoff for packaging/artifact convergence (`X-06`/`X-07`; Step 3 ownership).

## Dependencies

- BPL-06 closed checkpoints/fixtures/intake contracts: `BPL06-CP01`..`BPL06-CP05`, `BPL06-FX01`..`BPL06-FX05`, `BPL06-INT-01`..`BPL06-INT-05`.
- BPL-06 severity and rollback contracts: `BPL06-SEV-01`..`BPL06-SEV-04`, `BPL06-RB-01`..`BPL06-RB-05`.
- BPL-04 gate anchors and BPL-05 handoff requirements (`BPL04-G*`, `B5H-03`, `B5H-05`).
- Dependency rows `X-06` and `X-07` remain open soft gates for final signoff.

## Deliverables

1. Step 1 budget and measurement baseline sheet keyed one-to-one to frozen BPL-06 checkpoints.
2. Step 2 measurement execution packet (run evidence + budget evaluation summaries).
3. Step 3 soft-gate closure packet for `X-06`/`X-07` signoff input to BPL-08/BPL-09.

## Exit Criteria

- Step 1 publishes exactly five stable budget rows (`BPL07-BM01`..`BPL07-BM05`) covering `BPL06-CP01`..`BPL06-CP05` with no checkpoint gaps.
- Every row has deterministic commands, fixed artifact paths, explicit intake/rollback/severity references, and pass/fail interpretation.
- Step 2 produces evidence files under `doc/wasm/tickets/evidence/bpl-07/<run_id>/` without redefining Step 1 semantics.
- Step 3 records final `X-06`/`X-07` signoff posture without rewriting frozen upstream IDs.

## Current Notes

- BPL-06 is closed through Step 3 with frozen checkpoint (`BPL06-CP*`), fixture (`BPL06-FX*`), severity (`BPL06-SEV-*`), rollback (`BPL06-RB-*`), and intake (`BPL06-INT-*`) contracts.
- Step 1 output is now published below as Budget and Measurement Baseline v1.
- `X-04` is already closed and remains an immutable intake baseline.
- Step 2 run-v1 evidence is now published at `doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-002604Z-91fdb0be/` with row summaries for `BPL07-BM01`..`BPL07-BM05`.
- Step 2 remediation run-v2 evidence is now published at `doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/`, keyed to committed intake bundle `doc/wasm/tickets/evidence/bpl-06/bpl06-20260210-005408Z-91fdb0be/`.
- Run-v2 measured all command legs with `exit_code=0`; aggregate summary is `row_count=5`, `pass_count=5`, `fail_count=0`, `overall_result=pass`.
- `BPL07-BM05` now passes the perf budget (`-0.560224%` vs max `+1.0%`) with size delta `0` bytes and `intake_pass=true`.
- Step 3 closure-readiness criteria v1 now evaluate as `CR01=pass`, `CR02=pass`, `CR03=pass`; `CR04`/`CR05` backend preconditions are satisfied and remain open only for runtime-side soft-gate evidence.

## Immediate Next Step

- Action: carry BPL-07 remediation run-v2 pass bundle into published BPL-08 Step 3 closure rows as immutable backend signoff input while runtime executes `RPL-08 Step 1`.
- Why now: backend closure packetization is complete and only runtime-owned unified budget approval remains for `X-07`.
- Success evidence: synchronized matrix/master/board/BPL-00/BPL-07/BPL-08 wording preserves immutable run IDs and explicit `X-07=open` carry-forward posture without reopening backend checkpoints.

## Step 1 Output - Budget and Measurement Baseline (v1)

### Step 1 Deterministic Measurement Contract

- Run root: `/Users/buildsomething/Source/ccl`
- Required environment: `TZ=UTC`, `LC_ALL=C`, `LANG=C`, `CCL_IPC_LANE_ID=headless_runtime`
- Required run-id format: `bpl07-YYYYMMDD-HHMMSSZ-<short_sha>`
- Step 2 output directory per run: `doc/wasm/tickets/evidence/bpl-07/<run_id>/`
- Required size anchors (backend-owned artifacts):
  - `doc/wasm/js/wasmcl.wasm`
  - `doc/wasm/js/subprims.wasm`
- Metric formulas (all rows):
  - `perf_delta_pct = ((native_elapsed_sec - compat_elapsed_sec) / compat_elapsed_sec) * 100`
  - `size_total_bytes = wasmcl_size_bytes + subprims_size_bytes`
  - `size_delta_bytes = native_size_total_bytes - compat_size_total_bytes`

### Budget Baseline Rows

| budget_row_id | checkpoint coverage | frozen intake + severity/rollback linkage | budget category and metric definition | command template (deterministic mapping) | artifact inputs (required) | pass/fail interpretation | owner | downstream consumer |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BPL07-BM01 | `BPL06-CP01` (`BPL06-FX01`) | Intake: `BPL06-INT-01`; severity precedence: `BPL06-SEV-01`..`BPL06-SEV-03`; rollback: `BPL06-RB-01` | Category: numeric callsite runtime + artifact size. Metrics: `perf_delta_pct`, `size_delta_bytes`. Budget: `perf_delta_pct <= +3.0`; `size_delta_bytes <= +16384`. | Compat leg: `/usr/bin/time -p -o doc/wasm/tickets/evidence/bpl-07/<run_id>/BPL06-CP01-compat.time env TZ=UTC LC_ALL=C LANG=C CCL_IPC_LANE_ID=headless_runtime CCL_IPC_CONFORMANCE_ID=BPL06-CP01 WASM_LOWERING_PROMOTION_POLICY=hold WASM_LOWERING_NUMERIC_CALLSITE_MODE=compat node doc/wasm/js/all-smoke.mjs --no-ui` Native leg: same command with `WASM_LOWERING_NUMERIC_CALLSITE_MODE=native` and output `BPL06-CP01-native.time`; capture size snapshots after each leg via `stat -f '%z' doc/wasm/js/wasmcl.wasm` and `stat -f '%z' doc/wasm/js/subprims.wasm`. | `doc/wasm/tickets/evidence/bpl-06/<bpl06_run_id>/BPL06-CP01-compat.json`; `doc/wasm/tickets/evidence/bpl-06/<bpl06_run_id>/BPL06-CP01-native.json`; `doc/wasm/tickets/evidence/bpl-06/<bpl06_run_id>/BPL06-CP01-diff-summary.json`; Step 2 timing/size snapshots under `doc/wasm/tickets/evidence/bpl-07/<run_id>/`. | Pass only if intake summary remains `result=pass` with `mismatch_count=0` and both budget thresholds pass. Fail if intake rejects or budget exceeds threshold; on fail, freeze promotion and execute `BPL06-RB-01` posture (`WASM_LOWERING_NUMERIC_CALLSITE_MODE=compat`). | performance gate owner + compiler lowering owner | BPL-09 cutover packet, BPL-08 reference-only reporting |
| BPL07-BM02 | `BPL06-CP02` (`BPL06-FX02`) | Intake: `BPL06-INT-02`; severity precedence: `BPL06-SEV-01`..`BPL06-SEV-03`; rollback: `BPL06-RB-02` | Category: entrypoint/manifest lookup runtime + artifact size. Metrics: `perf_delta_pct`, `size_delta_bytes`. Budget: `perf_delta_pct <= +2.0`; `size_delta_bytes <= +8192`. | Compat leg: `/usr/bin/time -p -o doc/wasm/tickets/evidence/bpl-07/<run_id>/BPL06-CP02-compat.time env TZ=UTC LC_ALL=C LANG=C CCL_IPC_LANE_ID=headless_runtime CCL_IPC_CONFORMANCE_ID=BPL06-CP02 WASM_LOWERING_PROMOTION_POLICY=hold WASM_ENTRYPOINT_LOOKUP_MODE=slot node doc/wasm/js/all-smoke.mjs --no-ui` Native leg: same command with `WASM_ENTRYPOINT_LOOKUP_MODE=manifest` and output `BPL06-CP02-native.time`; capture size snapshots after each leg via the two `stat` commands above. | `doc/wasm/tickets/evidence/bpl-06/<bpl06_run_id>/BPL06-CP02-compat.json`; `doc/wasm/tickets/evidence/bpl-06/<bpl06_run_id>/BPL06-CP02-native.json`; `doc/wasm/tickets/evidence/bpl-06/<bpl06_run_id>/BPL06-CP02-diff-summary.json`; Step 2 timing/size snapshots under `doc/wasm/tickets/evidence/bpl-07/<run_id>/`. | Pass only if intake acceptance for manifest parity holds and both budget thresholds pass. Fail on any manifest mismatch, intake rejection, or budget overrun; apply `BPL06-RB-02` (`WASM_ENTRYPOINT_LOOKUP_MODE=slot`) and keep promotion blocked. | performance gate owner + module/loader + provider owner | BPL-08 integration checkpoint (`CON-05`), BPL-09 cutover packet |
| BPL07-BM03 | `BPL06-CP03` (`BPL06-FX03`) | Intake: `BPL06-INT-03`; severity precedence: `BPL06-SEV-01`..`BPL06-SEV-03`; rollback: `BPL06-RB-03` | Category: helper-dispatch runtime + artifact size. Metrics: `perf_delta_pct`, `size_delta_bytes`. Budget: `perf_delta_pct <= +2.5`; `size_delta_bytes <= +8192`. | Compat leg: `/usr/bin/time -p -o doc/wasm/tickets/evidence/bpl-07/<run_id>/BPL06-CP03-compat.time env TZ=UTC LC_ALL=C LANG=C CCL_IPC_LANE_ID=headless_runtime CCL_IPC_CONFORMANCE_ID=BPL06-CP03 WASM_LOWERING_PROMOTION_POLICY=hold WASM_DIV_HELPER_MODE=compat node doc/wasm/js/all-smoke.mjs --no-ui` Native leg: same command with `WASM_DIV_HELPER_MODE=native` and output `BPL06-CP03-native.time`; capture size snapshots after each leg via the two `stat` commands above. | `doc/wasm/tickets/evidence/bpl-06/<bpl06_run_id>/BPL06-CP03-compat.json`; `doc/wasm/tickets/evidence/bpl-06/<bpl06_run_id>/BPL06-CP03-native.json`; `doc/wasm/tickets/evidence/bpl-06/<bpl06_run_id>/BPL06-CP03-diff-summary.json`; Step 2 timing/size snapshots under `doc/wasm/tickets/evidence/bpl-07/<run_id>/`. | Pass only if no-fallback intake acceptance remains valid and budget thresholds pass. Fail on any no-fallback violation, intake rejection, or budget overrun; apply `BPL06-RB-03` (`WASM_DIV_HELPER_MODE=compat`) and block promotion. | performance gate owner + subprims/provider owner | BPL-08 compatibility assertions (`CON-06`), BPL-09 cutover packet |
| BPL07-BM04 | `BPL06-CP04` (`BPL06-FX04`) | Intake: `BPL06-INT-04`; severity precedence: `BPL06-SEV-01`..`BPL06-SEV-03`; rollback: `BPL06-RB-04` | Category: tailcall/frame runtime + artifact size. Metrics: strict + aggregate `perf_delta_pct`, `size_delta_bytes`. Budget: `perf_delta_pct <= +4.0`; `size_delta_bytes <= +16384`. | Compat leg: `/usr/bin/time -p -o doc/wasm/tickets/evidence/bpl-07/<run_id>/BPL06-CP04-compat.time env TZ=UTC LC_ALL=C LANG=C CCL_IPC_LANE_ID=headless_runtime CCL_IPC_CONFORMANCE_ID=BPL06-CP04 WASM_LOWERING_PROMOTION_POLICY=hold WASM_TAILCALL_NUMERIC_MODE=wrapper node doc/wasm/js/all-smoke.mjs --no-ui && WASM_LOWERING_PROMOTION_POLICY=hold WASM_TAILCALL_NUMERIC_MODE=wrapper node doc/wasm/js/start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive` Native leg: same command with `WASM_TAILCALL_NUMERIC_MODE=frame_reuse` and output `BPL06-CP04-native.time`; capture size snapshots after each leg via the two `stat` commands above. | `doc/wasm/tickets/evidence/bpl-06/<bpl06_run_id>/BPL06-CP04-compat.json`; `doc/wasm/tickets/evidence/bpl-06/<bpl06_run_id>/BPL06-CP04-native.json`; `doc/wasm/tickets/evidence/bpl-06/<bpl06_run_id>/BPL06-CP04-diff-summary.json`; strict-lane artifacts and Step 2 timing/size snapshots under `doc/wasm/tickets/evidence/bpl-07/<run_id>/`. | Pass only if strict + aggregate intake acceptance remains valid and budget thresholds pass. Fail on any frame/debug mismatch, strict-lane failure, intake rejection, or budget overrun; apply `BPL06-RB-04` (`WASM_TAILCALL_NUMERIC_MODE=wrapper`) and block promotion. | performance gate owner + subprims/runtime execution owner | BPL-08 frame/debug intake (`FDC-10`, `FDC-03`), BPL-09 cutover packet |
| BPL07-BM05 | `BPL06-CP05` (`BPL06-FX05`) | Intake: `BPL06-INT-05`; severity precedence: `BPL06-SEV-01`..`BPL06-SEV-04`; rollback: `BPL06-RB-05` | Category: cross-slice aggregate runtime + artifact size gate. Metrics: aggregate `perf_delta_pct`, `size_delta_bytes`. Budget: `perf_delta_pct <= +1.0`; `size_delta_bytes <= 0`. | Compat leg: `/usr/bin/time -p -o doc/wasm/tickets/evidence/bpl-07/<run_id>/BPL06-CP05-compat.time env TZ=UTC LC_ALL=C LANG=C CCL_IPC_LANE_ID=headless_runtime CCL_IPC_CONFORMANCE_ID=BPL06-CP05 WASM_LOWERING_PROMOTION_POLICY=hold node doc/wasm/js/all-smoke.mjs --no-ui` Native leg: same command with `WASM_LOWERING_PROMOTION_POLICY=advance` and output `BPL06-CP05-native.time`; capture size snapshots after each leg via the two `stat` commands above. | `doc/wasm/tickets/evidence/bpl-06/<bpl06_run_id>/BPL06-CP05-compat.json`; `doc/wasm/tickets/evidence/bpl-06/<bpl06_run_id>/BPL06-CP05-native.json`; `doc/wasm/tickets/evidence/bpl-06/<bpl06_run_id>/BPL06-CP05-diff-summary.json`; Step 2 timing/size snapshots under `doc/wasm/tickets/evidence/bpl-07/<run_id>/`. | Pass only if `BPL06-INT-05` acceptance holds, all upstream checkpoint intakes are accepted, and both aggregate budgets pass. Fail on any upstream unresolved checkpoint, any intake rejection, or any budget overrun; enforce `BPL06-RB-05` (`WASM_LOWERING_PROMOTION_POLICY=hold`) immediately. | backend governance owner + performance gate owner | BPL-08 freeze/advance compatibility gate, BPL-09 final cutover packet |

### Step 1 Exit Checks (Resumability)

1. Coverage check: confirm exactly five baseline rows (`BPL07-BM01`..`BPL07-BM05`) and one-to-one checkpoint mapping to `BPL06-CP01`..`BPL06-CP05`.
2. Intake linkage check: each row references exactly one `BPL06-INT-*` contract and the correct checkpoint-specific rollback row (`BPL06-RB-*`).
3. Determinism check: each row command explicitly pins locale/time env and checkpoint lane IDs (`CCL_IPC_CONFORMANCE_ID`).
4. Artifact contract check: each row names both BPL-06 intake artifact paths and Step 2 output path under `doc/wasm/tickets/evidence/bpl-07/<run_id>/`.
5. Consumer check: each row names downstream use in BPL-08 and/or BPL-09 without introducing new dependency rows.

## Step 2 Output - Run-v1 Measurement Packet (`bpl07-20260210-002604Z-91fdb0be`)

### Published Evidence Bundle

- Run directory: `doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-002604Z-91fdb0be/`
- Run summary: `doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-002604Z-91fdb0be/bpl07-step2-run-summary.json`
- Per-row summaries:
  - `doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-002604Z-91fdb0be/BPL07-BM01-budget-summary.json`
  - `doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-002604Z-91fdb0be/BPL07-BM02-budget-summary.json`
  - `doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-002604Z-91fdb0be/BPL07-BM03-budget-summary.json`
  - `doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-002604Z-91fdb0be/BPL07-BM04-budget-summary.json`
  - `doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-002604Z-91fdb0be/BPL07-BM05-budget-summary.json`

### Run-v1 Row Results

| budget_row_id | checkpoint_id | perf_delta_pct | size_delta_bytes | perf budget gate | size budget gate | intake artifact gate | overall_result | fail_reasons |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BPL07-BM01 | `BPL06-CP01` | `-1.322751%` | `0` | pass | pass | fail | fail | `bpl06_intake_artifacts_missing` |
| BPL07-BM02 | `BPL06-CP02` | `-0.542005%` | `0` | pass | pass | fail | fail | `bpl06_intake_artifacts_missing` |
| BPL07-BM03 | `BPL06-CP03` | `-0.554017%` | `0` | pass | pass | fail | fail | `bpl06_intake_artifacts_missing` |
| BPL07-BM04 | `BPL06-CP04` | `+0.111359%` | `0` | pass | pass | fail | fail | `bpl06_intake_artifacts_missing` |
| BPL07-BM05 | `BPL06-CP05` | `+1.955307%` | `0` | fail (budget `<= +1.0%`) | pass | fail | fail | `bpl06_intake_artifacts_missing`; `performance_budget_exceeded_or_uncomputable` |

Step 2 closure assertions:

1. All five frozen row IDs (`BPL07-BM01`..`BPL07-BM05`) executed compat/native command legs with recorded timing, logs, and per-leg metrics artifacts.
2. Deterministic output bundle is committed under one run directory with row-level and aggregate summaries.
3. Evidence clearly records unresolved intake and perf blockers without rewriting any frozen `BPL06-*` identifiers.

## Step 2 Output - Run-v2 Remediation Packet (`bpl07-20260210-005408Z-91fdb0be`)

### Published Evidence Bundle

- Intake run ID: `bpl06-20260210-005408Z-91fdb0be`
- Intake directory: `doc/wasm/tickets/evidence/bpl-06/bpl06-20260210-005408Z-91fdb0be/`
- Run directory: `doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/`
- Run summary: `doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/bpl07-step2-run-summary.json`
- Per-row summaries:
  - `doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/BPL07-BM01-budget-summary.json`
  - `doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/BPL07-BM02-budget-summary.json`
  - `doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/BPL07-BM03-budget-summary.json`
  - `doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/BPL07-BM04-budget-summary.json`
  - `doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/BPL07-BM05-budget-summary.json`

### Run-v2 Row Results

| budget_row_id | checkpoint_id | perf_delta_pct | size_delta_bytes | perf budget gate | size budget gate | intake artifact gate | overall_result | fail_reasons |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BPL07-BM01 | `BPL06-CP01` | `-2.191781%` | `0` | pass | pass | pass | pass | none |
| BPL07-BM02 | `BPL06-CP02` | `+0.840336%` | `0` | pass | pass | pass | pass | none |
| BPL07-BM03 | `BPL06-CP03` | `-0.276243%` | `0` | pass | pass | pass | pass | none |
| BPL07-BM04 | `BPL06-CP04` | `+0.000000%` | `0` | pass | pass | pass | pass | none |
| BPL07-BM05 | `BPL06-CP05` | `-0.560224%` | `0` | pass (budget `<= +1.0%`) | pass | pass | pass | none |

Step 2 remediation closure assertions:

1. One concrete BPL-06 intake bundle now exists for all frozen checkpoints (`BPL06-CP01`..`BPL06-CP05`) with required `compat`, `native`, and `diff-summary` artifacts.
2. Intake parity checks for the concrete bundle all pass (`result=pass`, `mismatch_count=0`, `rollback_required=false`) across `BPL06-CP01`..`BPL06-CP05`.
3. Run-v2 budget packet passes all five rows (`overall_result=pass`), including prior blocker row `BPL07-BM05`.

## Step 3 Output - X-06/X-07 Closure-Readiness Criteria (v1)

### Closure-Readiness Criteria Matrix

| criteria_id | target soft gate | blocker class addressed | deterministic check command | required artifacts | pass interpretation | fail interpretation + contract linkage | owner | latest disposition (`run-v1` -> `run-v2`) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BPL07-CR01 | `X-06`, `X-07` | Missing BPL-06 intake artifacts for all checkpoint rows (`BPL06-INT-01`..`BPL06-INT-05`) | `for cp in 01 02 03 04 05; do for leg in compat native; do test -f "doc/wasm/tickets/evidence/bpl-06/<bpl06_run_id>/BPL06-CP${cp}-${leg}.json"; done; test -f "doc/wasm/tickets/evidence/bpl-06/<bpl06_run_id>/BPL06-CP${cp}-diff-summary.json"; done` | `doc/wasm/tickets/evidence/bpl-06/<bpl06_run_id>/BPL06-CP01..05-{compat,native}.json`; `doc/wasm/tickets/evidence/bpl-06/<bpl06_run_id>/BPL06-CP01..05-diff-summary.json` | All 15 intake artifacts exist for one concrete `<bpl06_run_id>` and are consumable by `BPL07-BM01`..`BPL07-BM05`. | Treat as artifact-integrity failure (`BPL06-SEV-04`) and keep promotion frozen under `BPL06-RB-05` (`WASM_LOWERING_PROMOTION_POLICY=hold`). | harness owner + backend governance owner | run-v1 fail (`bpl06_intake_artifacts_missing`) -> run-v2 pass (`bpl06-20260210-005408Z-91fdb0be`) |
| BPL07-CR02 | `X-06`, `X-07` | Intake acceptance not yet proven because artifact set is missing | `node -e 'const fs=require(\"node:fs\"); const cps=[\"01\",\"02\",\"03\",\"04\",\"05\"]; for (const cp of cps){ const p=\"doc/wasm/tickets/evidence/bpl-06/\" + process.argv[1] + \"/BPL06-CP\" + cp + \"-diff-summary.json\"; const s=JSON.parse(fs.readFileSync(p,\"utf8\")); if(!(s.result===\"pass\" && s.mismatch_count===0 && s.rollback_required===false)) process.exit(1); }' <bpl06_run_id>` | Same `BPL06-CP01`..`BPL06-CP05` diff summaries as `CR01`; intake linkage to `BPL06-INT-01`..`BPL06-INT-05` | All five checkpoint summaries are parity-pass (`result=pass`, `mismatch_count=0`, `rollback_required=false`) for the same `<bpl06_run_id>`. | Apply checkpoint-specific rollback obligations (`BPL06-RB-01`..`BPL06-RB-05`) and keep `X-06`/`X-07` open until all intake rows are accepted. | harness owner + checkpoint owners | run-v1 blocked by `CR01` -> run-v2 pass (`bpl06-20260210-005408Z-91fdb0be`) |
| BPL07-CR03 | `X-07` (and aggregate `X-06` portability packet) | `BPL07-BM05` performance-budget overrun (`+1.955307%` vs `<= +1.0%`) | `node -e 'const fs=require(\"node:fs\"); const j=JSON.parse(fs.readFileSync(process.argv[1],\"utf8\")); if(!(j.intake_artifacts.intake_pass===true && j.gate_results.performance_budget_pass===true && j.gate_results.size_budget_pass===true)) process.exit(1);' doc/wasm/tickets/evidence/bpl-07/<bpl07_run_id>/BPL07-BM05-budget-summary.json` | `doc/wasm/tickets/evidence/bpl-07/<bpl07_run_id>/BPL07-BM05-budget-summary.json`; linked `BPL06-INT-05` pass artifacts from `<bpl06_run_id>` | `BPL07-BM05` reports `intake_pass=true`, `performance_budget_pass=true`, and `size_budget_pass=true`; rollback hold can be lifted for closure review. | Keep `BPL06-RB-05` hold posture active and block unified budget signoff until `BPL07-BM05` budget row passes. | performance gate owner + backend governance owner | run-v1 fail (`performance_budget_exceeded_or_uncomputable`) -> run-v2 pass (`bpl07-20260210-005408Z-91fdb0be`, `perf_delta_pct=-0.560224%`) |
| BPL07-CR04 | `X-06` | Backend side of packaging-portability closure readiness | `node -e 'const fs=require(\"node:fs\"); const j=JSON.parse(fs.readFileSync(process.argv[1],\"utf8\")); if(!(j.row_count===5 && j.pass_count===5 && j.overall_result===\"pass\")) process.exit(1);' doc/wasm/tickets/evidence/bpl-07/<bpl07_run_id>/bpl07-step2-run-summary.json` | Passing BPL-07 run summary for `<bpl07_run_id>` plus runtime-side packaging-freeze evidence required by matrix row `X-06` | Backend closure-readiness is achieved only when `CR01`..`CR03` are pass and the runtime packaging-freeze condition for `X-06` is satisfied. | Keep `X-06` open; no `done` transition allowed in matrix until both backend and runtime closure conditions are present. | backend governance owner + runtime packaging owner | run-v1 blocked (`pass_count=0`) -> run-v2 backend pass (`pass_count=5`); runtime packaging-freeze evidence pending |
| BPL07-CR05 | `X-07` | Unified runtime/backend budget approval readiness | `node -e 'const fs=require(\"node:fs\"); const run=JSON.parse(fs.readFileSync(process.argv[1],\"utf8\")); const bm05=JSON.parse(fs.readFileSync(process.argv[2],\"utf8\")); if(!(run.overall_result===\"pass\" && bm05.gate_results.performance_budget_pass===true && bm05.gate_results.size_budget_pass===true)) process.exit(1);' doc/wasm/tickets/evidence/bpl-07/<bpl07_run_id>/bpl07-step2-run-summary.json doc/wasm/tickets/evidence/bpl-07/<bpl07_run_id>/BPL07-BM05-budget-summary.json` | Passing backend bundle (`CR04`) plus unified budget approval artifact required by matrix row `X-07` | `X-07` can enter closure review only when backend pass bundle exists and unified budget sheet is approved across runtime/backend tracks. | Keep `X-07` open; BPL-08/BPL-09 signoff inputs remain provisional. | backend governance owner + runtime size-validation owner | run-v1 blocked -> run-v2 backend pass; runtime unified budget approval evidence pending |

### Step 3 Exit Checks (Resumability)

1. Coverage check: exactly five closure-readiness criteria rows are published (`BPL07-CR01`..`BPL07-CR05`) with no ID gaps.
2. Blocker linkage check: `CR01`/`CR02` explicitly gate missing BPL-06 intake artifacts and reference `BPL06-INT-01`..`BPL06-INT-05`.
3. Perf-overrun linkage check: `CR03` explicitly gates `BPL07-BM05` and enforces `BPL06-RB-05` hold posture on failure.
4. Soft-gate mapping check: `CR04` maps to `X-06`; `CR05` maps to `X-07`; both remain open until their listed closure conditions are met.
5. Sync check: immediate-next-step wording is aligned across BPL-07, backend master, dependency matrix, program board, and BPL-00 in the same change.

## Detailed Work Breakdown

### Step 1 - Budget and Measurement Baseline Definition

- Status: done
- Notes:
  - Published budget baseline rows `BPL07-BM01`..`BPL07-BM05` with full checkpoint coverage (`BPL06-CP01`..`BPL06-CP05`).
  - Frozen deterministic command templates, metric formulas, artifact paths, and pass/fail interpretation for all rows.
  - Bound every row to explicit intake (`BPL06-INT-*`) and rollback/severity (`BPL06-SEV-*`, `BPL06-RB-*`) contracts.
- Next:
  - Keep Step 1 rows immutable; future updates must be additive-only.

### Step 2 - Measurement Packet Execution and Budget Evaluation

- Status: done
- Notes:
  - Executed run-v1 bundle `bpl07-20260210-002604Z-91fdb0be` with full `BPL07-BM01`..`BPL07-BM05` coverage and explicit blocker capture.
  - Executed remediation run-v2 bundle `bpl07-20260210-005408Z-91fdb0be` keyed to intake run `bpl06-20260210-005408Z-91fdb0be`.
  - All compat/native command legs exited `0`; row-level timing and size metrics are published.
  - Run-v2 row verdicts are all `pass`; prior blocker row `BPL07-BM05` now passes perf budget (`-0.560224%` <= `+1.0%`) with size delta `0`.
- Next:
  - Preserve run-v1 and run-v2 artifacts as frozen baseline + remediation evidence for Step 3 soft-gate readiness.

### Step 3 - Soft-Gate Signoff Preparation (`X-06`/`X-07`)

- Status: done
- Notes:
  - Published closure-readiness criteria packet (`BPL07-CR01`..`BPL07-CR05`) keyed to run-v1 evidence and frozen BPL-06 intake/rollback contracts.
  - Missing intake-artifact blockers are formalized under `CR01`/`CR02`; `BPL07-BM05` perf-overrun disposition is formalized under `CR03`.
  - Remediation run-v2 now satisfies `CR01`..`CR03` using concrete run IDs `bpl06-20260210-005408Z-91fdb0be` and `bpl07-20260210-005408Z-91fdb0be`.
  - `X-06`/`X-07` soft-gate readiness mapping remains explicit (`CR04`, `CR05`); backend preconditions are now satisfied and runtime-side closure evidence remains open.
- Next:
  - Request matrix-level closure review for `CR04`/`CR05` using run-v2 backend pass evidence while waiting runtime-side `RPL-07`/`RPL-08` signoff artifacts.

## Test and Validation Plan

- Row-integrity validation:
  - Verify `BPL07-BM01`..`BPL07-BM05` checkpoint coverage has no gaps or duplicate checkpoint mappings.
- Command reproducibility validation:
  - Verify all commands are runnable from repo root and match the corresponding `BPL06-FX*` fixture semantics.
- Contract-link validation:
  - Verify each row references one `BPL06-INT-*` and one checkpoint-matched `BPL06-RB-*` row.
- Governance validation:
  - Verify immediate-next-step language is synchronized across BPL-07 subplan, backend master, dependency matrix, program board, and BPL-00.

## Risks and Mitigations

- Risk: budget evaluation diverges from frozen parity intake semantics.
  - Mitigation: Step 1 makes `BPL06-INT-*` acceptance a mandatory precondition for every budget pass.
- Risk: size/perf regressions are masked by non-deterministic environment variation.
  - Mitigation: enforce fixed locale/time/lane env and explicit per-leg timing/size snapshots.
- Risk: soft-gate closure is attempted before runtime packaging methodology is stable.
  - Mitigation: keep `X-06`/`X-07` open until Step 3 unified signoff evidence is published.

## Change Log

- 2026-02-10: Initialized BPL-07 and published Step 1 Budget and Measurement Baseline v1 (`BPL07-BM01`..`BPL07-BM05`) with deterministic command templates and frozen BPL-06 intake linkage.
- 2026-02-10: Resynced Pack A posture to keep backend execution on BPL-07 Step 1 baseline hardening/consumption while runtime executes RPL-05 progression over the same frozen `BPL06-*` intake artifacts.
- 2026-02-10: Executed BPL-07 Step 2 run-v1 packet (`bpl07-20260210-002604Z-91fdb0be`) and published row/aggregate summaries; all rows currently fail on missing BPL-06 intake artifacts and `BPL07-BM05` also fails perf budget threshold.
- 2026-02-10: Closed BPL-07 Step 3 by publishing closure-readiness criteria packet (`BPL07-CR01`..`BPL07-CR05`) for `X-06`/`X-07`, explicitly capturing missing intake-artifact blockers and `BPL07-BM05` perf-budget disposition.
- 2026-02-10: Executed `bpl07-step3-remediation-run-v2` with concrete intake run `bpl06-20260210-005408Z-91fdb0be` and rerun packet `bpl07-20260210-005408Z-91fdb0be`; `CR01`..`CR03` now pass and backend preconditions for `CR04`/`CR05` are satisfied.
- 2026-02-10: Resynced immediate-next-step wording across BPL-07/backend-master/matrix/board/BPL-00 to Pack A runtime run-v2 execution while preserving backend run-v2 pass bundle as `X-06`/`X-07` closure-review input.
- 2026-02-10: Resynced immediate-next-step wording to BPL-08 Step 3 closure-readiness publication after Step 2 deterministic validation packet (`BPL08-IV01`..`BPL08-IV06`) was committed.
- 2026-02-10: Resynced immediate-next-step wording after BPL-08 Step 3 publication (`BPL08-CR01`..`BPL08-CR06`) to preserve backend pass bundle carry-forward while `X-07` remains open for runtime unified budget signoff.
