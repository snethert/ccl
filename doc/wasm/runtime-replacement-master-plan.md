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
| RPL-00 | in_progress | P0 | `doc/wasm/tickets/RPL-00-governance-and-baseline-freeze.md` | 2026-02-09 | Master plan created; subplan not yet authored. |
| RPL-01 | planned | P0 | `doc/wasm/tickets/RPL-01-secure-runtime-gating.md` | 2026-02-09 | Secure-only startup contract and boot validation. |
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
- Subplan: `doc/wasm/tickets/RPL-00-governance-and-baseline-freeze.md` (pending)
- Dependencies: none

Notes:

- This master plan is now the canonical tracker for replacement execution.
- Baseline architecture and blocker context have been captured from current docs.
- Ticket subplans are not yet created; template is available.

Next Step Analysis:

- Immediate Next Step: author RPL-00 subplan with explicit acceptance criteria and update cadence.
- Why this step now: prevents ticket drift before implementation starts.
- Evidence required to close next step: committed subplan with owner, cadence, and checklist.

---

### RPL-01 - Secure Runtime Gating

- Status: `planned`
- Priority: `P0`
- Last Updated: `2026-02-09`
- Subplan: `doc/wasm/tickets/RPL-01-secure-runtime-gating.md` (pending)
- Dependencies: RPL-00

Notes:

- Boot contract must be secure-only for MVP (cross-origin isolation and required feature gates).
- Failure behavior must be explicit; no silent fallback mode.

Next Step Analysis:

- Immediate Next Step: define startup capability matrix and hard-fail diagnostics contract.
- Why this step now: all downstream shared-memory work depends on deterministic startup guarantees.
- Evidence required to close next step: signed-off startup gate spec + test matrix.

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
