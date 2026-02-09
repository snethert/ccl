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
| RPL-00 | in_progress | P0 | `doc/wasm/tickets/RPL-00-governance-and-baseline-freeze.md` | 2026-02-09 | First downstream update cycle has started through RPL-01 Step 1 execution. |
| RPL-01 | in_progress | P0 | `doc/wasm/tickets/RPL-01-secure-runtime-gating.md` | 2026-02-09 | Step 1 contradiction inventory v1 (`C-01`..`C-14`) committed; capability matrix definition is next. |
| RPL-02 | planned | P0 | `doc/wasm/tickets/RPL-02-worker-topology-and-thread-bootstrap.md` | 2026-02-09 | Define required workers/threads for MVP runtime architecture. |
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

Next Step Analysis:

- Immediate Next Step: continue applying the same dual-update governance loop for RPL-01 Step 2 execution.
- Why this step now: the first downstream update cycle has now been executed and the process needs one more cycle to confirm repeatability.
- Evidence required to close next step: RPL-01 Step 2 updates land with synchronized master/subplan status and evidence markers.

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
- Contradictions are now tracked with per-item status/notes for resumable doc reconciliation.

Next Step Analysis:

- Immediate Next Step: execute Step 2 by drafting a required capability matrix with check IDs and startup assertions mapped from contradiction IDs.
- Why this step now: contradiction inventory is in place, so startup requirements can be codified as deterministic checks.
- Evidence required to close next step: matrix committed with pass/fail assertions and contradiction-ID mapping references.

---

### RPL-02 - Worker Topology and Thread Bootstrap

- Status: `planned`
- Priority: `P0`
- Last Updated: `2026-02-09`
- Subplan: `doc/wasm/tickets/RPL-02-worker-topology-and-thread-bootstrap.md` (pending)
- Dependencies: RPL-01

Notes:

- MVP runtime architecture may require worker threads even before CL-level thread semantics.
- Required worker roles must be explicit (kernel/runtime/storage/UI mediation boundaries).

Next Step Analysis:

- Immediate Next Step: document worker-role topology and startup sequence.
- Why this step now: shared-memory channels and storage service boundaries depend on worker ownership.
- Evidence required to close next step: topology diagram and startup lifecycle contract committed.

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
