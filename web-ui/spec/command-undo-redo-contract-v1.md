# Command Undo/Redo Contract v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-17  
Scope: Undo/redo semantics for command-driven state mutation in `web-ui`  
Depends on: `web-ui/spec/command-schema-v1.json`, `web-ui/spec/command-routing-algorithm-v1.md`, `web-ui/spec/event-log-ordering-and-clock-rules-v1.md`, `web-ui/spec/snapshot-schema-v1.json`  
Compatibility: `v1.x` preserves command reversibility classes, transaction boundaries, and stack behavior; incompatible model changes require `v2`.

## 1. Purpose

This contract defines reversible command execution for `web-ui`.
It is normative for undo/redo eligibility, transaction boundaries, stack retention, and replay semantics.

## 2. Reversibility Classes

Every mutating command <a id="REQ-COMMAND-UNDO-REDO-CONTRACT-V1-143E8FE166"></a>MUST declare one class:

1. `reversible`: command has deterministic inverse payload.
2. `non-reversible`: command cannot be undone; clears redo stack and opens a new history boundary.
3. `compound`: command wraps nested sub-commands and supplies deterministic inverse plan.

Command metadata <a id="REQ-COMMAND-UNDO-REDO-CONTRACT-V1-83643CF122"></a>MUST expose this class at registration time.

## 3. Transaction Boundaries

Undo/redo operates on transactions, not raw low-level events.

Rules:

1. A transaction <a id="REQ-COMMAND-UNDO-REDO-CONTRACT-V1-2F014EF7F4"></a>MUST have `txId`, `commandId`, `startedAtSeq`, `endedAtSeq`, and `inverse` lanes.
2. Nested transactions are allowed only for `compound` commands and <a id="REQ-COMMAND-UNDO-REDO-CONTRACT-V1-6DE63DBC7D"></a>MUST collapse into one top-level undo unit.
3. Failed commands <a id="REQ-COMMAND-UNDO-REDO-CONTRACT-V1-62A6A13AC3"></a>MUST NOT produce undo entries.
4. Transactions that emit side effects outside modeled state <a id="REQ-COMMAND-UNDO-REDO-CONTRACT-V1-0B784E1AAA"></a>MUST declare compensating behavior or be `non-reversible`.

## 4. Undo/Redo Stack Model

State shape:

1. `undoStack[]`
2. `redoStack[]`
3. `historyLimit` (default `500` transactions)

Rules:

1. Pushing a new successful transaction <a id="REQ-COMMAND-UNDO-REDO-CONTRACT-V1-573E72C591"></a>MUST clear `redoStack` unless command is replaying a redo action.
2. Undo pops from `undoStack`, applies inverse deterministically, then pushes corresponding redo entry.
3. Redo pops from `redoStack`, reapplies forward transaction deterministically, then pushes undo entry.
4. Stack overflow beyond `historyLimit` <a id="REQ-COMMAND-UNDO-REDO-CONTRACT-V1-11EFE7642A"></a>MUST evict oldest undo entries first.

## 5. Persistence and Replay

1. Undo/redo history MAY be persisted per workspace/session.
2. Persisted history <a id="REQ-COMMAND-UNDO-REDO-CONTRACT-V1-D612ADB658"></a>MUST reference stable IDs and reject stale references at restore.
3. Event-log replay <a id="REQ-COMMAND-UNDO-REDO-CONTRACT-V1-447706C047"></a>MUST reproduce identical undo/redo stack states for identical command logs.

## 6. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `undo-redo.empty-undo-stack` | Undo requested but stack is empty. | No | Disable or gray out undo affordance. |
| `undo-redo.empty-redo-stack` | Redo requested but stack is empty. | No | Disable or gray out redo affordance. |
| `undo-redo.non-reversible` | Requested command has no reversible contract. | No | Surface reason and continue with forward-only history. |
| `undo-redo.inverse-invalid` | Stored inverse payload is malformed or stale. | Conditional | Recompute/repair history and retry. |
| `undo-redo.transaction-conflict` | Undo/redo cannot apply due to state precondition mismatch. | Conditional | Refresh state, possibly fall back to snapshot restore. |

## 7. Conformance

An implementation is conformant only if it enforces Sections 2-6.
