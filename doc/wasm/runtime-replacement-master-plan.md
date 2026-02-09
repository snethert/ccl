# Runtime Replacement Master Plan (Secure-Only, Shared-Memory, Storage V2)

Status: Active  
Owner: Runtime/WASM replacement track  
Last Updated: 2026-02-09  

## Purpose

This is the canonical execution and status document for replacing the current functional runtime architecture with:

- secure-environment-only startup assumptions,
- shared-memory hot-path communication (SAB + Atomics),
- Storage V2 semantics (immutable objects + mutable refs/leases + deterministic merge workflow),
- module/environment sharing to reduce runtime artifact size and duplication.

This document is designed for fresh-context recovery. Every ticket must carry current status, notes, and next-step analysis.

## Program Coordination

This runtime plan is one of two coordinated master plans:

- Runtime track: `doc/wasm/runtime-replacement-master-plan.md` (this document)
- Backend track: `doc/wasm/backend-migration-master-plan.md`

Cross-track dependencies and parallelization constraints are tracked in:

- `doc/wasm/runtime-backend-dependency-matrix.md`
- `doc/wasm/wasm-program-board.md`

## Scope

In scope:

- Runtime/microkernel ABI and worker topology changes.
- Runtime/UI hot-path transport migration to shared memory.
- Storage V2 implementation and migration from the current persistence service.
- Module packaging/discovery changes required for environment sharing and artifact-size reduction.
- Cutover planning and deprecation of legacy hot-path assumptions.

Out of scope:

- New user-facing feature work unrelated to replacement track.
- A portable fallback mode for non-secure environments in MVP.
- Final CL thread semantics implementation (host/worker threads may still be required in MVP runtime architecture).

## Related Source Documents

- `doc/wasm/roadmap.md`
- `doc/wasm/porting-status.md`
- `doc/wasm/mvp-unattended-execution-plan.md`
- `doc/wasm/mvp-unattended-execution-report.md`
- `doc/wasm/wasm-ui-persistence-problem-tracker.md`
- `doc/wasm/kernel-request-abi.md`
- `doc/wasm/js-microkernel-spec.md`
- `doc/wasm/persistence-service-spec.md`
- `doc/wasm/backend-migration-master-plan.md`
- `doc/wasm/runtime-backend-dependency-matrix.md`
- `doc/wasm/wasm-program-board.md`
- `web-ide/phase-8/implementation-plan.md`

## Status Legend

- `planned`: defined, not started.
- `in_progress`: active implementation.
- `blocked`: cannot continue until dependency/decision is resolved.
- `done`: merged and validated against defined exit criteria.
- `deferred`: intentionally paused and not current execution priority.
- `cancelled`: explicitly removed from scope.

## Update Contract (Required)

On every ticket update:

1. Update this document:
   - ticket `Status`,
   - `Last Updated`,
   - `Notes`,
   - `Next Step Analysis`.
2. Update the ticket subplan document referenced by `Subplan`.
3. If subplan content changes but this master plan is not updated in the same change, the ticket is considered out of sync.

## Fresh-Context Resume Protocol

When resuming work from scratch:

1. Read `Current Baseline Snapshot`.
2. Find the highest-priority ticket with `Status = in_progress` or `planned` and no unmet hard dependency.
3. Execute only the `Immediate Next Step` under that ticket.
4. At stop, update both this master plan and the ticket subplan before ending work.

## Current Baseline Snapshot (2026-02-09)

- Current runtime gates are green for the existing architecture (root-lane persistence closure and smoke/test lanes are passing), but blocker tracking remains focused on dispatch hardening.
- Existing ABI and microkernel baseline remain copy-based and portability-first.
- Existing persistence layer is still the memory-snapshot/chunked VFS model.
- Runtime/UI command/event pathways remain message-oriented in key paths.
- Runtime module artifact remains very large:
  - `doc/wasm/wasm-runtime-modules.bin`: 436,499,792 bytes
  - `doc/wasm/wasm-runtime-modules.json`: 7,620 modules, 5,438 const pools

## Ticket Board

| Ticket | Status | Priority | Subplan | Last Updated | Notes |
| --- | --- | --- | --- | --- | --- |
| RPL-00 | in_progress | P0 | `doc/wasm/tickets/RPL-00-governance-and-baseline-freeze.md` | 2026-02-09 | Eleventh downstream update cycle completed by publishing RPL-02 Step 3 mapping outputs and synchronizing `X-02` closure evidence across ticket/master/matrix docs. |
| RPL-01 | in_progress | P0 | `doc/wasm/tickets/RPL-01-secure-runtime-gating.md` | 2026-02-09 | RPL-02 Step 3 mapping is now published and `X-02` is cleared; contradiction follow-through now advances to RPL-03 Step 1 shared-memory IPC contract drafting. |
| RPL-02 | done | P0 | `doc/wasm/tickets/RPL-02-worker-topology-and-thread-bootstrap.md` | 2026-02-09 | Step 3 mapping output is complete (`X03M-01`..`X03M-05`) with explicit BPL-03 `B3*` consumption coverage; dependency row `X-02` is now `done`. |
| RPL-03 | planned | P0 | `doc/wasm/tickets/RPL-03-shared-memory-ipc-core.md` | 2026-02-09 | SAB/Atomics channels for kernel/runtime hot paths. |
| RPL-04 | planned | P0 | `doc/wasm/tickets/RPL-04-runtime-ui-bridge-shared-path.md` | 2026-02-09 | Runtime/UI ingress-egress migration off message hot path. |
| RPL-05 | planned | P0 | `doc/wasm/tickets/RPL-05-storage-v2-local-core.md` | 2026-02-09 | Local immutable object store + refs/leases baseline. |
| RPL-06 | planned | P1 | `doc/wasm/tickets/RPL-06-storage-v2-sync-merge.md` | 2026-02-09 | Remote sync, conflict records, merge-candidate/finalization flow. |
| RPL-07 | planned | P0 | `doc/wasm/tickets/RPL-07-module-environment-sharing.md` | 2026-02-09 | Module payload/environment sharing and loader changes. |
| RPL-08 | planned | P1 | `doc/wasm/tickets/RPL-08-artifact-size-reduction-and-validation.md` | 2026-02-09 | Size and perf validation gates tied to replacement architecture. |
| RPL-09 | planned | P0 | `doc/wasm/tickets/RPL-09-cutover-and-legacy-removal.md` | 2026-02-09 | Feature-flagged cutover, legacy path retirement, docs reconciliation. |

## Ticket Details

### RPL-00 - Governance and Baseline Freeze

- Status: `in_progress`
- Priority: `P0`
- Last Updated: `2026-02-09`
- Subplan: `doc/wasm/tickets/RPL-00-governance-and-baseline-freeze.md`
- Dependencies: none

Notes:

- This master plan is now the canonical tracker for replacement execution.
- Baseline architecture and blocker context have been captured from current docs.
- RPL-00 subplan has been authored and now governs sync/update behavior.
- Runtime track now has explicit parallel coordination points with backend migration track docs.
- Eleventh downstream governance cycle is now complete through synchronized RPL-02 Step 3 mapping publication and dependency-row `X-02` closure updates.

Next Step Analysis:

- Immediate Next Step: continue the dual-update governance loop by executing RPL-03 Step 1 and synchronizing runtime/master/matrix updates in the same cycle.
- Why this step now: `X-02` is now cleared, so governance priority shifts to protocol-contract progress on `X-03`.
- Evidence required to close next step: RPL-03 Step 1 output is published and dependency-row `X-03` notes are updated with concrete protocol evidence.

---

### RPL-01 - Secure Runtime Gating

- Status: `in_progress`
- Priority: `P0`
- Last Updated: `2026-02-09`
- Subplan: `doc/wasm/tickets/RPL-01-secure-runtime-gating.md`
- Dependencies: RPL-00

Notes:

- Boot contract must be secure-only for MVP (cross-origin isolation and required feature gates).
- Failure behavior must be explicit; no silent fallback mode.
- Step 1 contradiction inventory v1 is now recorded with explicit resolution actions (`C-01`..`C-14`).
- Step 2 capability/startup gate matrix v1 is now committed with frozen check IDs (`SRG-01`..`SRG-12`) and fail-code mapping.
- Step 3 diagnostics contract v1 is now committed (`startup_gate_check_result_v1` and `startup_gate_summary_v1`).
- Step 4 loader/harness integration plan v1 is now committed with concrete integration IDs (`LHI-01`..`LHI-06`).
- Step 5 validation/regression gate matrix v1 is now committed with frozen validation IDs (`VRG-01`..`VRG-10`).
- Step 6 handoff package v1 is now committed (`HND-01`..`HND-06`, `CRA-01`..`CRA-05`) with explicit closure-readiness results.
- Cross-track `X-01` gate is now cleared through explicit BPL-02 `SRG-01`..`SRG-12` linkage evidence plus Step 2 contract coverage validation (`CON-01`..`CON-08` -> `BCL-01`..`BCL-12`).
- Cross-track `X-02` gate is now cleared through explicit RPL-02 Step 3 mappings (`X03M-01`..`X03M-05`) and BPL-03 `B3*` consumption tables.
- Failure semantics are now explicit: fixed check order, first-failure abort, strict no-fallback enforcement.
- Integration entrypoints and diagnostics surfacing requirements are now explicit across loader/smoke/browser lanes.
- Matrix now distinguishes required runtime/thread capabilities from deferred CL thread semantics.
- Contradictions remain tracked with per-item status/notes for downstream remediation updates.

Next Step Analysis:

- Immediate Next Step: continue downstream contradiction remediation via RPL-03 Step 1 shared-memory IPC contract drafting and dependency-evidence alignment.
- Why this step now: worker topology/lifecycle constraints are now consumed and `X-02` is clear, so contradiction follow-through shifts to IPC protocol formalization.
- Evidence required to close next step: RPL-03 Step 1 publishes protocol IDs that explicitly align with secure-only/no-fallback assumptions and updates dependency-row `X-03` notes.

---

### RPL-02 - Worker Topology and Thread Bootstrap

- Status: `done`
- Priority: `P0`
- Last Updated: `2026-02-09`
- Subplan: `doc/wasm/tickets/RPL-02-worker-topology-and-thread-bootstrap.md`
- Dependencies: RPL-01

Notes:

- MVP runtime architecture may require worker threads even before CL-level thread semantics.
- Required worker roles must be explicit (kernel/runtime/storage/UI mediation boundaries).
- Step 1 topology output v1 now defines role ownership (`WTOP-01`..`WTOP-05`) and startup sequencing (`WSEQ-01`..`WSEQ-06`).
- Step 2 lifecycle contract v1 now defines deterministic states/transitions and role policies (`WLCS-01`..`WLCS-06`, `WLCT-01`..`WLCT-11`, `WLCR-01`..`WLCR-05`).
- Step 3 cross-track mapping output is now complete with explicit mapping classes (`X03M-01`..`X03M-05`) and synchronized BPL-03 `B3*` consumption evidence.
- Machine-actionable topology and lifecycle schemas (`worker_topology_ready_v1`, `worker_lifecycle_event_v1`, `worker_lifecycle_summary_v1`) are now available for harness and cross-track consumers.
- Dependency row `X-02` is now `done` with explicit mapping coverage for all required RPL-02 ID classes.

Next Step Analysis:

- Immediate Next Step: maintain RPL-02 outputs as frozen baseline while RPL-03 Step 1 protocol work consumes worker-topology and lifecycle constraints.
- Why this step now: RPL-02 exit criteria are satisfied and `X-02` is cleared, so this ticket shifts to additive-only maintenance.
- Evidence required to close next step: RPL-03 Step 1 references `WTOP-*`/`WSEQ-*`/`WLCS-*`/`WLCT-*`/`WLCR-*` directly without reopening or renaming frozen IDs.

---

### RPL-03 - Shared-Memory IPC Core

- Status: `planned`
- Priority: `P0`
- Last Updated: `2026-02-09`
- Subplan: `doc/wasm/tickets/RPL-03-shared-memory-ipc-core.md` (pending)
- Dependencies: RPL-01, RPL-02

Notes:

- Current copy-based request ABI is incompatible with target hot-path efficiency goals.
- Required replacement: shared command/response channels with Atomics signaling and explicit backpressure.

Next Step Analysis:

- Immediate Next Step: define ring/mailbox wire layout and signaling protocol version 1.
- Why this step now: all hot-path call migration work needs a stable IPC contract.
- Evidence required to close next step: protocol doc + conformance tests for queue correctness.

---

### RPL-04 - Runtime/UI Bridge Shared Path

- Status: `planned`
- Priority: `P0`
- Last Updated: `2026-02-09`
- Subplan: `doc/wasm/tickets/RPL-04-runtime-ui-bridge-shared-path.md` (pending)
- Dependencies: RPL-03

Notes:

- Existing runtime command/event payload flow remains JSON/message-oriented in key paths.
- Must move UI ingress and runtime effect/state egress off hot-path message transport.

Next Step Analysis:

- Immediate Next Step: define which runtime and UI message classes migrate first to shared channels.
- Why this step now: enables incremental replacement without breaking full bridge behavior.
- Evidence required to close next step: migration matrix and first migrated path passing existing bridge tests.

---

### RPL-05 - Storage V2 Local Core

- Status: `planned`
- Priority: `P0`
- Last Updated: `2026-02-09`
- Subplan: `doc/wasm/tickets/RPL-05-storage-v2-local-core.md` (pending)
- Dependencies: RPL-01, RPL-02

Notes:

- Current persistence service is VFS/chunk-store oriented and not aligned with new FormGraph/object/ref/lease model.
- Must establish local immutable objects + mutable ref/lease CAS semantics with crash-safety invariants.

Next Step Analysis:

- Immediate Next Step: define canonical local object schemas and metadata transaction boundaries.
- Why this step now: local correctness must exist before sync/merge protocol.
- Evidence required to close next step: schema spec + local persistence conformance tests.

---

### RPL-06 - Storage V2 Sync and Merge

- Status: `planned`
- Priority: `P1`
- Last Updated: `2026-02-09`
- Subplan: `doc/wasm/tickets/RPL-06-storage-v2-sync-merge.md` (pending)
- Dependencies: RPL-05

Notes:

- Team sync requires closure upload/download, ref CAS, deterministic merge-candidate and finalization workflows.
- Conflict records and merge records are required for deterministic auditability.

Next Step Analysis:

- Immediate Next Step: define remote API contract and local sync state schema.
- Why this step now: blocks multi-device correctness and conflict recovery behavior.
- Evidence required to close next step: remote endpoint contract + sync integration tests.

---

### RPL-07 - Module Environment Sharing

- Status: `planned`
- Priority: `P0`
- Last Updated: `2026-02-09`
- Subplan: `doc/wasm/tickets/RPL-07-module-environment-sharing.md` (pending)
- Dependencies: RPL-03

Notes:

- Runtime modules currently carry high payload cost and environment duplication pressure.
- Goal: environment sharing/discovery so modules do not each require full environment embedding.

Next Step Analysis:

- Immediate Next Step: define shared environment capsule format and loader resolution contract.
- Why this step now: key lever for artifact size reduction and startup efficiency.
- Evidence required to close next step: prototype bundle spec and loader install proof.

---

### RPL-08 - Artifact Size Reduction and Validation

- Status: `planned`
- Priority: `P1`
- Last Updated: `2026-02-09`
- Subplan: `doc/wasm/tickets/RPL-08-artifact-size-reduction-and-validation.md` (pending)
- Dependencies: RPL-07

Notes:

- Current runtime module binary size is a material deployment risk.
- Size reduction must be paired with deterministic validation so functional coverage does not regress.

Next Step Analysis:

- Immediate Next Step: define target budgets and measurement commands for each artifact class.
- Why this step now: replacement changes need objective impact tracking.
- Evidence required to close next step: budget sheet + automated regression checks.

---

### RPL-09 - Cutover and Legacy Removal

- Status: `planned`
- Priority: `P0`
- Last Updated: `2026-02-09`
- Subplan: `doc/wasm/tickets/RPL-09-cutover-and-legacy-removal.md` (pending)
- Dependencies: RPL-03, RPL-04, RPL-05, RPL-07

Notes:

- Replacement must ship without leaving unresolved hot-path dependence on legacy copy/message lanes.
- Cutover must be staged, reversible, and explicitly tracked by release gates.

Next Step Analysis:

- Immediate Next Step: define cutover gates and rollback triggers by feature flag stage.
- Why this step now: prevents late-cycle ambiguity on what "done" means for replacement.
- Evidence required to close next step: cutover checklist + rollback rehearsals.

## Subplan Registry Sync Rules

- Each ticket subplan must exist at the path listed above.
- Each subplan must include:
  - `Status`,
  - `Last Updated`,
  - `Notes`,
  - `Immediate Next Step`,
  - `Exit Criteria`,
  - `Change Log`.
- If a subplan moves paths, update both this board row and the ticket detail block in the same change.

## Ongoing Next-Step Analysis Rules

For every active ticket update, include all three:

1. What changed since the prior update.
2. What single next action will be executed next.
3. What evidence will prove that next action succeeded.

Avoid batching multiple unrelated next actions into one update.

## Change Log

- 2026-02-09: Initial master plan created with ticket board, detail blocks, update contract, and resume protocol.
- 2026-02-09: Scaffolded `RPL-00` and `RPL-01` subplans and synchronized ticket board/detail notes.
- 2026-02-09: Began RPL-01 execution with Step 1 contradiction inventory v1 and synchronized board/detail status updates.
- 2026-02-09: Added program-level coordination references for parallel backend migration planning.
- 2026-02-09: Synced RPL-01 Step 2 matrix completion (`SRG-01`..`SRG-12`) and advanced RPL-01/RPL-00 next-step analysis to Step 3 governance cycle.
- 2026-02-09: Synced RPL-01 Step 3 diagnostics contract completion and advanced RPL-01/RPL-00 next-step analysis to Step 4 integration planning.
- 2026-02-09: Synced RPL-01 Step 4 integration plan completion (`LHI-01`..`LHI-06`) and advanced RPL-01/RPL-00 next-step analysis to Step 5 validation gates.
- 2026-02-09: Synced RPL-01 Step 5 validation/regression matrix completion (`VRG-01`..`VRG-10`) and advanced RPL-01/RPL-00 next-step analysis to Step 6 handoff packaging.
- 2026-02-09: Synced RPL-01 Step 6 handoff package completion (`HND-01`..`HND-06`, `CRA-01`..`CRA-05`) and advanced next-step analysis to `X-01` consumption closure.
- 2026-02-09: Synced post-Step-6 consumption checkpoint by clearing `X-01` (BPL-02 `SRG-01`..`SRG-12` linkage) and advanced runtime next-step analysis to RPL-02 Step 1.
- 2026-02-09: Executed RPL-02 Step 1 worker-topology definition (`WTOP-01`..`WTOP-05`, `WSEQ-01`..`WSEQ-06`) and advanced runtime next-step analysis to RPL-02 Step 2 lifecycle contract work.
- 2026-02-09: Synced RPL-02 Step 1 readiness evidence into dependency matrix by advancing `X-02` to `in_progress` and reaffirming RPL-02 Step 2 lifecycle contract as the single immediate runtime action.
- 2026-02-09: Executed RPL-02 Step 2 lifecycle/failure-state contract (`WLCS-*`, `WLCT-*`, `WLCR-*`) with strict no-fallback semantics and advanced runtime next-step analysis to Step 3 cross-track mapping.
- 2026-02-09: Synced runtime master with BPL-02 Step 2 closure evidence so `X-01` remains clear on both startup-gate linkage and closed contract traceability.
- 2026-02-09: Executed RPL-02 Step 3 cross-track mapping (`X03M-01`..`X03M-05`), cleared dependency row `X-02`, marked RPL-02 `done`, and advanced governance/contradiction next-step focus to RPL-03 Step 1.
