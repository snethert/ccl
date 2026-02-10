# BPL-08 - Runtime Alignment Integration

Status: in_progress  
Priority: P0  
Owner: Compiler/backend migration track  
Last Updated: 2026-02-10  
Parent Plan: `doc/wasm/backend-migration-master-plan.md`

## Scope

In scope:

- Define deterministic backend/runtime integration checkpoints after `BPL-07` pass-bundle publication.
- Freeze ABI compatibility assertions spanning runtime shared-memory IPC, loader/module environment handoff, and backend promotion posture.
- Bind integration checkpoints to concrete existing evidence bundles and failure/rollback contracts.

Out of scope:

- Runtime-side artifact-size budget policy ownership (RPL-08 owns budget sheet approval workflow).
- Final cutover/release retirement mechanics (BPL-09 + RPL-09).
- Re-opening frozen `BPL06-*`, `BPL07-*`, `RPL03-*`, `RPL07-*` identifiers.

## Dependencies

- BPL-06 frozen intake contracts: `BPL06-INT-01`..`BPL06-INT-05`, rollback rows `BPL06-RB-01`..`BPL06-RB-05`.
- BPL-07 pass bundle: `bpl06-20260210-005408Z-91fdb0be`, `bpl07-20260210-005408Z-91fdb0be`.
- Runtime hard-gate closure evidence: `X-03=done` via `doc/wasm/tickets/evidence/rpl-03-step3-rerun-2026-02-09/`.
- Runtime module-environment closure evidence: `X-06=done` via `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/`.

## Deliverables

1. Step 1 integration checkpoint/assertion baseline (stable `BPL08-IC*` IDs).
2. Step 2 deterministic integration validation execution packet definition.
3. Step 3 closure-readiness packet for BPL-09 cutover intake.

## Exit Criteria

- Step 1 publishes stable checkpoint IDs with one-to-one evidence anchors and explicit pass/fail interpretation.
- Step 2 defines deterministic command/evidence mapping for all published checkpoints.
- Step 3 records integration closure posture with no frozen-ID rewrites.

## Current Notes

- `X-03` is already closed, so BPL-08 can proceed without runtime IPC hard-gate blockers.
- `X-06` is now `done`, so module/environment integration evidence is available for backend consumption.
- `X-07` remains `open` pending unified runtime/backend budget approval under RPL-08; BPL-08 must carry this as an external soft-gate input.
- BPL-07 pass-bundle artifacts are frozen and must be consumed as immutable integration inputs.
- Step 2 deterministic validation packet is now published below as `BPL08-IV01`..`BPL08-IV06`.
- Step 3 integration closure-readiness packet is now published below as `BPL08-CR01`..`BPL08-CR06`.

## Immediate Next Step

- Action: continue `Pack A` by carrying the published BPL-08 Step 3 closure packet as immutable backend signoff input while runtime executes `RPL-08 Step 1` unified budget-contract work for `X-07`.
- Why now: backend-owned BPL-08 closure packetization is complete and `X-07` remains runtime-owned/open until unified budget approval is committed.
- Success evidence: matrix/master/board/BPL-00/BPL-07/BPL-08 docs preserve `BPL08-CR*` rows with immutable bundle IDs and explicit `X-07=open` carry-forward posture.

## Step 1 Output - Integration Checkpoint and Assertion Baseline (v1)

### Step 1 Integration Matrix

| integration_id | integration surface | runtime anchor(s) | backend anchor(s) | required evidence bundle(s) | pass interpretation | fail interpretation + rollback posture | owner | downstream consumer |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BPL08-IC01 | Shared-memory request/response ABI compatibility | `IPCP-01`..`IPCP-49`, `IPCV-01`..`IPCV-12` | `CON-05`, `CON-06`, `FDC-03` | `doc/wasm/tickets/evidence/rpl-03-step3-rerun-2026-02-09/`; `doc/wasm/tickets/evidence/bpl-06/bpl06-20260210-005408Z-91fdb0be/` | IPC framing and ordering invariants are compatible with backend call boundary assumptions and no contradiction remains unresolved. | Treat as integration-severity failure; keep backend promotion hold posture (`BPL06-RB-05`) and block BPL-09 intake. | runtime IPC owner + backend integration owner | BPL-09 cutover gate packet |
| BPL08-IC02 | Module-environment resolution + backend entrypoint alignment | `R7R-01`..`R7R-28`, `R7V-01`..`R7V-14` | `BPL07-BM02`, `BPL06-INT-02` | `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/`; `doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/BPL07-BM02-budget-summary.json` | Runtime module/environment resolution and backend entrypoint assumptions are compatible with deterministic parity and budget contracts. | Treat as integration-severity failure; freeze manifest promotion path and retain fallback posture per `BPL06-RB-02`. | runtime module owner + backend loader owner | BPL-09 integration proof section |
| BPL08-IC03 | Numeric dispatch + helper semantics across runtime/backend boundary | `R7I-01`, `R7I-04`, `R7I-06` | `BPL07-BM01`, `BPL07-BM03`, `BPL06-INT-01`, `BPL06-INT-03` | `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/module_env_x06_review_packet_v1.json`; `doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/BPL07-BM01-budget-summary.json`; `doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/BPL07-BM03-budget-summary.json` | Numeric/runtime dispatch behavior remains parity-safe and budget-safe under promoted backend pathways. | Treat as integration-severity failure; apply `BPL06-RB-01`/`BPL06-RB-03` and block BPL-09 intake. | runtime env owner + backend numeric owner | BPL-09 risk/rollback packet |
| BPL08-IC04 | Frame/debug metadata + strict-lane startup compatibility | `R7V-10`, `R7V-11` | `FDC-10`, `BPL07-BM04`, `BPL06-INT-04` | `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/`; `doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/BPL07-BM04-budget-summary.json` | Frame/debug and strict startup expectations are compatible under runtime module-sharing and backend frame reuse policies. | Treat as integration-severity failure; enforce `BPL06-RB-04` and keep strict-lane promotion blocked. | runtime execution owner + backend debug owner | BPL-09 readiness checklist |
| BPL08-IC05 | Aggregate freeze/advance promotion contract compatibility | `module_env_step2_summary_v1`, `module_env_x07_review_packet_v1` | `BPL07-BM05`, `BPL06-INT-05`, `BPL06-RB-05` | `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/module_env_x07_review_packet_v1.json`; `doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/BPL07-BM05-budget-summary.json` | Aggregate promotion path remains parity-safe, performance-safe, and review-ready while waiting unified budget approval in `X-07`. | Treat as soft-gate failure; keep `X-07=open`, enforce `BPL06-RB-05` hold posture, and block BPL-09 signoff. | runtime size-validation owner + backend governance owner | BPL-09 gate precondition packet |
| BPL08-IC06 | Evidence immutability + cross-track carry-forward integrity | `X-07` carry-forward bundle IDs | `BPL07-CR05`, `BPL07-BM05` | `rpl05-20260210-011240Z-91fdb0be`; `bpl06-20260210-005408Z-91fdb0be`; `bpl07-20260210-005408Z-91fdb0be` references across matrix/master/subplans | All integration docs preserve immutable bundle IDs without rewrite and reference the same artifacts for closure review. | Treat as governance drift failure; halt closure review until docs are resynchronized with immutable IDs preserved. | backend governance owner + runtime governance owner | BPL-09 audit/compliance section |

### Step 1 Exit Checks (Resumability)

1. Coverage check: exactly six stable integration rows are published (`BPL08-IC01`..`BPL08-IC06`) with no ID gaps.
2. Evidence-anchor check: every row includes concrete runtime and backend evidence anchors.
3. Contract-link check: every row maps to at least one frozen `BPL06-INT-*`/`BPL06-RB-*` or `BPL07-*` integration contract where relevant.
4. Consumer check: each row names a concrete BPL-09 consumer path.
5. Sync check: backend master + BPL-00 + matrix + board notes are synchronized in the same change.

## Step 2 Output - Deterministic Integration Validation Packet (v1)

### Step 2 Validation Matrix

| validation_id | checkpoint linkage | deterministic check command | required artifacts | pass interpretation | fail interpretation + rollback posture | owner | downstream consumer |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BPL08-IV01 | `BPL08-IC01` | `node -e 'const fs=require(\"node:fs\"); const p=process.argv[1]; const j=JSON.parse(fs.readFileSync(p,\"utf8\")); if(!(j.status===\"pass\" && j.x03_clear_ready===true)) process.exit(1);' doc/wasm/tickets/evidence/rpl-03-step3-rerun-2026-02-09/ipc_conformance_summary_v1.json` | `doc/wasm/tickets/evidence/rpl-03-step3-rerun-2026-02-09/ipc_conformance_summary_v1.json`; `doc/wasm/tickets/evidence/bpl-06/bpl06-20260210-005408Z-91fdb0be/BPL06-CP01-diff-summary.json` | Shared-memory ABI baseline is proven pass and backend intake compatibility anchor remains parity-clean. | Treat as integration hard-fail; enforce `BPL06-RB-05` hold posture and block BPL-09 intake. | runtime IPC owner + backend integration owner | BPL-09 cutover gate packet |
| BPL08-IV02 | `BPL08-IC02` | `node -e 'const fs=require(\"node:fs\"); const p=process.argv[1]; const j=JSON.parse(fs.readFileSync(p,\"utf8\")); if(!(j.overall_result===\"pass\" && j.intake_artifacts.intake_pass===true && j.gate_results.performance_budget_pass===true && j.gate_results.size_budget_pass===true)) process.exit(1);' doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/BPL07-BM02-budget-summary.json` | `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/module_env_step2_summary_v1.json`; `doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/BPL07-BM02-budget-summary.json` | Entrypoint/manifest integration remains parity-safe and budget-safe under frozen module-environment evidence. | Treat as integration fail; apply `BPL06-RB-02` and block manifest promotion in closure packet. | runtime module owner + backend loader owner | BPL-09 integration proof section |
| BPL08-IV03 | `BPL08-IC03` | `node -e 'const fs=require(\"node:fs\"); const p1=JSON.parse(fs.readFileSync(process.argv[1],\"utf8\")); const p2=JSON.parse(fs.readFileSync(process.argv[2],\"utf8\")); if(!(p1.overall_result===\"pass\" && p2.overall_result===\"pass\" && p1.intake_artifacts.intake_pass===true && p2.intake_artifacts.intake_pass===true)) process.exit(1);' doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/BPL07-BM01-budget-summary.json doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/BPL07-BM03-budget-summary.json` | `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/module_env_x06_review_packet_v1.json`; `doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/BPL07-BM01-budget-summary.json`; `doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/BPL07-BM03-budget-summary.json` | Numeric dispatch and helper integration remain pass on both linked checkpoint rows. | Treat as integration fail; enforce `BPL06-RB-01`/`BPL06-RB-03` and block BPL-09 intake. | runtime env owner + backend numeric owner | BPL-09 risk/rollback packet |
| BPL08-IV04 | `BPL08-IC04` | `node -e 'const fs=require(\"node:fs\"); const p=JSON.parse(fs.readFileSync(process.argv[1],\"utf8\")); const s=JSON.parse(fs.readFileSync(process.argv[2],\"utf8\")); if(!(p.overall_result===\"pass\" && p.intake_artifacts.intake_pass===true && p.gate_results.performance_budget_pass===true && p.gate_results.size_budget_pass===true && s.status===\"pass\" && s.x06_step2_ready===true)) process.exit(1);' doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/BPL07-BM04-budget-summary.json doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/module_env_step2_summary_v1.json` | `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/module_env_step2_summary_v1.json`; `doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/BPL07-BM04-budget-summary.json` | Frame/debug strict-lane compatibility remains pass under runtime module sharing + backend frame reuse posture. | Treat as integration fail; enforce `BPL06-RB-04` and hold strict-lane promotion. | runtime execution owner + backend debug owner | BPL-09 readiness checklist |
| BPL08-IV05 | `BPL08-IC05` | `node -e 'const fs=require(\"node:fs\"); const run=JSON.parse(fs.readFileSync(process.argv[1],\"utf8\")); const bm05=JSON.parse(fs.readFileSync(process.argv[2],\"utf8\")); const review=JSON.parse(fs.readFileSync(process.argv[3],\"utf8\")); if(!(run.overall_result===\"pass\" && bm05.overall_result===\"pass\" && bm05.gate_results.performance_budget_pass===true && bm05.gate_results.size_budget_pass===true && review.x07_review_result===\"carry_forward\")) process.exit(1);' doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/bpl07-step2-run-summary.json doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/BPL07-BM05-budget-summary.json doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/module_env_x07_review_packet_v1.json` | `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/module_env_x07_review_packet_v1.json`; `doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/bpl07-step2-run-summary.json`; `doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/BPL07-BM05-budget-summary.json` | Aggregate promotion compatibility is backend-pass and correctly carried forward as `X-07` review input. | Treat as soft-gate fail; keep `X-07=open` and enforce `BPL06-RB-05` hold posture. | runtime size-validation owner + backend governance owner | BPL-09 gate precondition packet |
| BPL08-IV06 | `BPL08-IC06` | `for id in rpl05-20260210-011240Z-91fdb0be bpl06-20260210-005408Z-91fdb0be bpl07-20260210-005408Z-91fdb0be; do rg -n \"$id\" doc/wasm/runtime-backend-dependency-matrix.md doc/wasm/backend-migration-master-plan.md doc/wasm/backend-tickets/BPL-08-runtime-alignment-integration.md doc/wasm/backend-tickets/BPL-00-governance-and-baseline-freeze.md doc/wasm/wasm-program-board.md >/dev/null; done` | Immutable bundle IDs in matrix/master/subplans/program-board | All required docs preserve identical immutable bundle IDs with no alias rewrites. | Treat as governance drift fail; halt closure-review publishing until docs are synchronized. | backend governance owner + runtime governance owner | BPL-09 audit/compliance section |

### Step 2 Exit Checks (Resumability)

1. Coverage check: exactly six validation rows are published (`BPL08-IV01`..`BPL08-IV06`) with one-to-one linkage to `BPL08-IC01`..`BPL08-IC06`.
2. Determinism check: every row includes a concrete command runnable from repo root and anchored to immutable evidence paths/IDs.
3. Contract-link check: each row preserves frozen `BPL06-*`/`BPL07-*` linkage and does not introduce new dependency IDs.
4. Soft-gate check: `BPL08-IV05` explicitly carries `X-07=open` posture until runtime-side unified budget signoff.
5. Sync check: matrix/master/program-board/BPL-00/BPL-07 notes are synchronized to Step 2 publication in the same change.

## Step 3 Output - Integration Closure-Readiness Packet (v1)

### Step 3 Closure Matrix

| closure_id | validation linkage | target gate/posture | deterministic closure check command | required artifacts | pass interpretation | fail interpretation + carry-forward posture | owner | downstream consumer |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BPL08-CR01 | `BPL08-IV01` | BPL-09 IPC compatibility intake | `node -e 'const fs=require(\"node:fs\"); const j=JSON.parse(fs.readFileSync(process.argv[1],\"utf8\")); if(!(j.status===\"pass\" && j.x03_clear_ready===true)) process.exit(1);' doc/wasm/tickets/evidence/rpl-03-step3-rerun-2026-02-09/ipc_conformance_summary_v1.json` | `doc/wasm/tickets/evidence/rpl-03-step3-rerun-2026-02-09/ipc_conformance_summary_v1.json`; `doc/wasm/tickets/evidence/bpl-06/bpl06-20260210-005408Z-91fdb0be/BPL06-CP01-diff-summary.json` | IPC hard-gate compatibility is closure-ready for BPL-09 intake packet. | Keep backend promotion hold (`BPL06-RB-05`) and block BPL-09 closure packet signoff. | runtime IPC owner + backend integration owner | BPL-09 cutover gate packet |
| BPL08-CR02 | `BPL08-IV02` | Loader/entrypoint integration readiness | `node -e 'const fs=require(\"node:fs\"); const j=JSON.parse(fs.readFileSync(process.argv[1],\"utf8\")); if(!(j.overall_result===\"pass\" && j.intake_artifacts.intake_pass===true && j.gate_results.performance_budget_pass===true && j.gate_results.size_budget_pass===true)) process.exit(1);' doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/BPL07-BM02-budget-summary.json` | `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/module_env_step2_summary_v1.json`; `doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/BPL07-BM02-budget-summary.json` | Loader/entrypoint closure signal is compatible with module-environment runtime baseline. | Keep manifest fallback posture (`BPL06-RB-02`) and block BPL-09 integration proof closure. | runtime module owner + backend loader owner | BPL-09 integration proof section |
| BPL08-CR03 | `BPL08-IV03` | Numeric/helper cross-boundary closure readiness | `node -e 'const fs=require(\"node:fs\"); const a=JSON.parse(fs.readFileSync(process.argv[1],\"utf8\")); const b=JSON.parse(fs.readFileSync(process.argv[2],\"utf8\")); if(!(a.overall_result===\"pass\" && b.overall_result===\"pass\" && a.intake_artifacts.intake_pass===true && b.intake_artifacts.intake_pass===true)) process.exit(1);' doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/BPL07-BM01-budget-summary.json doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/BPL07-BM03-budget-summary.json` | `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/module_env_x06_review_packet_v1.json`; `doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/BPL07-BM01-budget-summary.json`; `doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/BPL07-BM03-budget-summary.json` | Numeric/helper integration is closure-ready under frozen backend/runtime artifacts. | Reapply `BPL06-RB-01`/`BPL06-RB-03` hold posture and keep BPL-09 closure provisional. | runtime env owner + backend numeric owner | BPL-09 risk/rollback packet |
| BPL08-CR04 | `BPL08-IV04` | Frame/debug strict-lane closure readiness | `node -e 'const fs=require(\"node:fs\"); const p=JSON.parse(fs.readFileSync(process.argv[1],\"utf8\")); const s=JSON.parse(fs.readFileSync(process.argv[2],\"utf8\")); if(!(p.overall_result===\"pass\" && p.intake_artifacts.intake_pass===true && p.gate_results.performance_budget_pass===true && p.gate_results.size_budget_pass===true && s.status===\"pass\" && s.x06_step2_ready===true)) process.exit(1);' doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/BPL07-BM04-budget-summary.json doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/module_env_step2_summary_v1.json` | `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/module_env_step2_summary_v1.json`; `doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/BPL07-BM04-budget-summary.json` | Frame/debug and strict-lane closure is backend-ready for BPL-09 packetization. | Enforce `BPL06-RB-04` and keep strict-lane signoff blocked. | runtime execution owner + backend debug owner | BPL-09 readiness checklist |
| BPL08-CR05 | `BPL08-IV05` | `X-07` carry-forward closure posture | `node -e 'const fs=require(\"node:fs\"); const run=JSON.parse(fs.readFileSync(process.argv[1],\"utf8\")); const bm=JSON.parse(fs.readFileSync(process.argv[2],\"utf8\")); const review=JSON.parse(fs.readFileSync(process.argv[3],\"utf8\")); if(!(run.overall_result===\"pass\" && bm.overall_result===\"pass\" && bm.gate_results.performance_budget_pass===true && bm.gate_results.size_budget_pass===true && review.x07_review_result===\"carry_forward\")) process.exit(1);' doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/bpl07-step2-run-summary.json doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/BPL07-BM05-budget-summary.json doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/module_env_x07_review_packet_v1.json` | `doc/wasm/tickets/evidence/rpl-07-step3-2026-02-10/rpl07-20260210-014654Z-91fdb0be/module_env_x07_review_packet_v1.json`; `doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/bpl07-step2-run-summary.json`; `doc/wasm/tickets/evidence/bpl-07/bpl07-20260210-005408Z-91fdb0be/BPL07-BM05-budget-summary.json` | Backend closure packet is complete and explicitly carries `X-07=open` until unified runtime/backend budget approval lands. | Keep `X-07=open`, enforce `BPL06-RB-05` hold posture, and block BPL-09 final signoff. | runtime size-validation owner + backend governance owner | BPL-09 gate precondition packet |
| BPL08-CR06 | `BPL08-IV06` | Immutable bundle integrity across governance docs | `for id in rpl05-20260210-011240Z-91fdb0be bpl06-20260210-005408Z-91fdb0be bpl07-20260210-005408Z-91fdb0be; do rg -n \"$id\" doc/wasm/runtime-backend-dependency-matrix.md doc/wasm/backend-migration-master-plan.md doc/wasm/backend-tickets/BPL-08-runtime-alignment-integration.md doc/wasm/backend-tickets/BPL-00-governance-and-baseline-freeze.md doc/wasm/backend-tickets/BPL-07-size-and-performance-gates.md doc/wasm/wasm-program-board.md >/dev/null; done` | Immutable bundle IDs in matrix/master/subplans/program-board | Closure packet remains audit-ready with identical immutable IDs and no alias rewrites. | Treat as governance drift failure; halt BPL-09 intake publication until docs are resynchronized. | backend governance owner + runtime governance owner | BPL-09 audit/compliance section |

### Step 3 Exit Checks (Resumability)

1. Coverage check: exactly six closure rows are published (`BPL08-CR01`..`BPL08-CR06`) with one-to-one linkage to `BPL08-IV01`..`BPL08-IV06`.
2. Determinism check: each closure row includes a concrete command over immutable evidence paths or immutable bundle IDs.
3. Carry-forward check: `BPL08-CR05` explicitly preserves `X-07=open` posture until RPL-08 unified budget approval is committed.
4. Immutability check: `BPL08-CR06` verifies identical carry-forward bundle IDs (`rpl05-20260210-011240Z-91fdb0be`, `bpl06-20260210-005408Z-91fdb0be`, `bpl07-20260210-005408Z-91fdb0be`) across governance docs.
5. Sync check: backend master + BPL-00 + BPL-07 + matrix + board are synchronized in the same change.

## Detailed Work Breakdown

### Step 1 - Integration Checkpoint and Assertion Baseline

- Status: done
- Notes:
  - Published integration checkpoint baseline rows `BPL08-IC01`..`BPL08-IC06`.
  - Bound rows to committed runtime/backend evidence bundles and frozen contract IDs.
  - Captured pass/fail interpretation and rollback posture per integration surface.
- Next:
  - Keep Step 1 rows immutable; consume them through Step 2/Step 3 additive-only updates.

### Step 2 - Deterministic Integration Validation Packet

- Status: done
- Notes:
  - Published `BPL08-IV01`..`BPL08-IV06` command/evidence mappings for all Step 1 checkpoints.
  - Preserved immutable bundle IDs and frozen `BPL06-*`/`BPL07-*` contract references.
  - Encoded explicit soft-gate carry-forward posture (`X-07=open`) in `BPL08-IV05`.
- Next:
  - Keep Step 2 rows immutable; consume them through Step 3 closure carry-forward updates.

### Step 3 - Integration Closure-Readiness Packet

- Status: done
- Notes:
  - Published closure-readiness packet rows `BPL08-CR01`..`BPL08-CR06`, keyed one-to-one to `BPL08-IV01`..`BPL08-IV06`.
  - Preserved immutable carry-forward bundle IDs (`rpl05-20260210-011240Z-91fdb0be`, `bpl06-20260210-005408Z-91fdb0be`, `bpl07-20260210-005408Z-91fdb0be`) across all closure checks.
  - Encoded explicit `X-07=open` carry-forward posture in `BPL08-CR05` until unified runtime/backend budget approval lands under RPL-08.
- Next:
  - Carry Step 3 closure packet forward as immutable input while runtime-side RPL-08 budget signoff remains open.

## Test and Validation Plan

- Row-integrity validation:
  - Verify `BPL08-IC01`..`BPL08-IC06` coverage and unique IDs.
- Evidence-anchor validation:
  - Verify all referenced evidence paths/run IDs are concrete and committed.
- Governance sync validation:
  - Verify backend master + BPL-00 + matrix + board remain synchronized on immediate-next-step language.

## Risks and Mitigations

- Risk: BPL-08 integration planning diverges from frozen runtime/backend evidence bundles.
  - Mitigation: require immutable bundle IDs in every Step 1 row and Step 2 command mapping.
- Risk: runtime-side `X-07` budget signoff assumptions leak into backend-owned closure claims.
  - Mitigation: keep `X-07` explicitly open and model it as external soft-gate input until RPL-08 evidence is committed.
- Risk: rollback posture ambiguity during integration validation.
  - Mitigation: reference frozen `BPL06-RB-*` rows directly in each applicable checkpoint.

## Change Log

- 2026-02-10: Initialized BPL-08 and published Step 1 integration checkpoint/assertion baseline (`BPL08-IC01`..`BPL08-IC06`) over frozen runtime/backend evidence bundles.
- 2026-02-10: Published Step 2 deterministic validation packet (`BPL08-IV01`..`BPL08-IV06`) with runnable command templates, immutable bundle IDs, and explicit `X-07` carry-forward posture.
- 2026-02-10: Published Step 3 integration closure-readiness packet (`BPL08-CR01`..`BPL08-CR06`) keyed to `BPL08-IV01`..`BPL08-IV06`, preserving immutable bundle IDs and explicit `X-07=open` carry-forward posture.
