# Backend/Shared Doc Sync Protocol

Status: Active  
Owner: Backend governance (`BPL-00`)  
Last Updated: 2026-02-10

## Purpose

Stop per-ticket status fan-out across runtime/backend/shared docs.

Backend execution updates backend docs only. Shared docs are updated in scheduled merge cycles.

## Modes

### 1) Backend-Local Mode (default)

Update only:

- `doc/wasm/backend-migration-master-plan.md`
- `doc/wasm/backend-tickets/*`
- backend evidence artifacts (`doc/wasm/tickets/evidence/bpl-*`)
- `doc/wasm/backend-sync/merge-queue.md`

Do not update in this mode:

- `doc/wasm/runtime-replacement-master-plan.md`
- `doc/wasm/runtime-backend-dependency-matrix.md`
- `doc/wasm/wasm-program-board.md`

### 2) Shared-Merge Mode (batched)

Run only when one of these is true:

1. backend milestone closure (`BPL-*` status transition affecting cross-track posture),
2. dependency-row status change (`X-*` open/in_progress/done/cancelled),
3. explicit user request for shared sync.

Shared-Merge Mode consumes pending rows from `merge-queue.md` and updates shared docs in one batch.

## Merge Workflow

1. During Backend-Local Mode, append a pending row to `merge-queue.md` for each cross-track-impacting backend change.
2. Keep runtime/matrix/board unchanged while implementing backend work.
3. In Shared-Merge Mode, process all pending rows in one change and mark them `merged`.
4. Record merge commit hash and date in `merge-queue.md`.

## Definition of Done for a Merge Cycle

- Pending queue rows touched by the merge are marked `merged`.
- `runtime-replacement-master-plan.md`, `runtime-backend-dependency-matrix.md`, and `wasm-program-board.md` are synchronized once.
- No backend ticket status text is copied repeatedly outside merge cycles.
