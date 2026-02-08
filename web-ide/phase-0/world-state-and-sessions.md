# Phase 0 Spec: World State and Sessions (v0)

## Purpose
Define the minimal world state model so sessions feel safe and recoverable without full image snapshotting.

## Goals
- Workspace state persists across sessions (worldlets).
- Stale references are readable and revalidatable.
- Restores never break core navigation or history.

## Non-Goals
- Full image snapshot or object graph persistence.
- Durable storage of large binary data.

## World State Model
A workspace snapshot must preserve:
- Layout and window structure.
- Open instruments and their last known state.
- Transcript (recordings and entries).
- Command history.
- Inspector pins and watches.
- Selection and focus history.

### Snapshot Payload (Summary)
```json
{
  "workspaceId": "workspace-0",
  "createdAt": 1710012345000,
  "state": {
    "layout": {"rootId": "layout-1", "nodes": {}},
    "windows": {},
    "widgets": {},
    "recordings": {},
    "entries": {},
    "presentations": {},
    "commandHistory": [],
    "watches": [],
    "selection": null,
    "focus": null
  }
}
```

## Staleness and Revalidation
- A presentation may reference a runtime object that no longer exists.
- Stale presentations are preserved as readable summaries.
- Revalidation attempts to rebind stale presentations when possible.

### Revalidation Rules
1. If object id is valid in runtime, bind presentation to live object.
2. If object id is invalid, show summary text and mark as stale.
3. If a command depends on stale object, require explicit confirmation.

## Session Restore
- Restore layout, open instruments, and transcript first.
- Replay command history only if explicitly requested.
- Inspector pins and watches are restored as "pending" until revalidated.

## Persistence Requirements
- Snapshots must be versioned and migrated.
- Large transcripts may be truncated with explicit markers.

## Invariants
- Restore must never block the UI.
- Stale data must be clearly labeled.
- User actions never silently discard state.

## Phase 0 Decisions
- Default snapshot truncation keeps the most recent 5,000 transcript entries or 20 MB payload budget, with explicit truncation markers.
- v1 supports multiple named worldlets plus one auto-restore worldlet per workspace.
