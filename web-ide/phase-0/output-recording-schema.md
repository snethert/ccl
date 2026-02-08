# Phase 0 Spec: Output Recording Schema (v0)

## Version
Schema version: `0`

## Purpose
Define a formal output recording model so REPL transcripts are deterministic, replayable, and addressable independently of the DOM.

## Goals
- Every evaluation emits a structured recording with stable anchors.
- Operations act on recording entries, not DOM nodes.
- Copy, fold, replay, and navigation are deterministic after re-render.
- Recordings persist across sessions (worldlets).

## Non-Goals
- Rendering details or UI layout.
- Full persistence of live object graphs.
- Arbitrary binary output handling (handled by attachments later).

## Core Concepts
- Recording: a single evaluation run or system event with input, output, and provenance.
- Recording entry: an atomic output element (text, presentation, system, error).
- Anchor: a stable identifier for a recording entry or subrange.
- Transcript: ordered list of recordings and entries across streams.

## IDs and Sequencing
- `recording.id` and `entry.id` are stable, globally unique strings.
- `entry.seq` is a monotonically increasing integer per stream.
- `recording.seqStart` and `recording.seqEnd` bound the entries for the run.

## Schema

### Recording
```json
{
  "id": "rec-000123",
  "jobId": "job-42",
  "status": "ok",
  "seqStart": 1200,
  "seqEnd": 1215,
  "tsStart": 1710012345000,
  "tsEnd": 1710012345123,
  "streamId": "repl",
  "input": {
    "kind": "form",
    "text": "(defun foo (x) (+ x 1))",
    "package": "CL-USER",
    "sourceLocation": {
      "file": "src/foo.lisp",
      "line": 12,
      "column": 1
    }
  },
  "context": {
    "commandId": "repl.eval",
    "sessionId": "session-01",
    "workspaceId": "workspace-0"
  },
  "entryIds": ["ent-001", "ent-002"],
  "metadata": {}
}
```

### Recording Entry
```json
{
  "id": "ent-001",
  "recordingId": "rec-000123",
  "kind": "text",
  "streamId": "stdout",
  "seq": 1201,
  "ts": 1710012345003,
  "text": "; compiling...\n",
  "anchorId": "anc-9001",
  "presentationId": null,
  "metadata": {}
}
```

### Entry Kinds
- `text`: plain text output.
- `presentation`: structured value with `presentationId`.
- `system`: system notices (compilation, loading, indexing).
- `error`: error output with structured metadata.

### Anchor
```json
{
  "id": "anc-9001",
  "entryId": "ent-001",
  "range": { "start": 0, "end": 13 },
  "path": []
}
```

Notes:
- `range` is optional for non-text entries.
- `path` supports structured sub-targets (for nested presentations).

## Transcript Indexes
For efficient navigation, maintain indexes (in memory, derived, or persisted):
- `recordingOrder`: ordered list of `recording.id`.
- `entryOrder`: ordered list of `entry.id`.
- `byAnchor`: `anchorId -> {entryId, range, path}`.
- `byPresentation`: `presentationId -> entryId`.

## Operations (Minimum Viable)
- `appendRecording(recording)`
- `appendEntry(entry)`
- `foldEntry(entryId, folded)`
- `copyAsForm(entryId|anchorId)`
- `copyWithContext(entryId|anchorId)`
- `replayAsInput(recordingId)`
- `reRunRecording(recordingId)`

## Invariants
- Entries are immutable after creation.
- Anchors must remain valid after re-render.
- Output operations never depend on DOM nodes.

## Persistence
- Recordings and entries are persisted in workspace snapshots.
- Entries referencing live objects store a `presentationId` plus a safe `summaryText`.

## Phase 0 Decisions
- `recording.input.kind` is expanded to support `form`, `file`, and `command`.
- Large/binary output is represented by `kind: "system"` entries with `metadata.attachmentRef`; blob persistence stays out of v0.
