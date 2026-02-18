import { test } from "node:test";
import assert from "node:assert/strict";

import {
  PERSISTENCE_SCHEMA_VERSION,
  createState,
  createRecordingStore,
  appendRecordingToStore,
  appendEntryToStore,
  createSnapshot,
  restoreStateFromSnapshot
} from "../src/index.mjs";

test("phase-1 persistence schema version is allocated", () => {
  assert.equal(PERSISTENCE_SCHEMA_VERSION, "5");
});

test("phase-1 persistence snapshot truncates recording store by budget", () => {
  let recordingStore = createRecordingStore();
  recordingStore = appendRecordingToStore(recordingStore, { id: "rec-1" });
  recordingStore = appendEntryToStore(recordingStore, { id: "ent-1", recordingId: "rec-1", text: "1111111111" });
  recordingStore = appendEntryToStore(recordingStore, { id: "ent-2", recordingId: "rec-1", text: "2222222222" });
  recordingStore = appendEntryToStore(recordingStore, { id: "ent-3", recordingId: "rec-1", text: "3333333333" });

  const snapshot = createSnapshot(createState({ recordingStore }), {
    now: () => 0,
    recordingBudget: { maxEntries: 2, maxBytes: 1024 }
  });

  assert.deepEqual(snapshot.state.recordingStore.entryOrder, ["ent-2", "ent-3"]);
  assert.equal(snapshot.state.recordingStore.truncation.applied, true);
  assert.equal(snapshot.state.recordingStore.truncation.droppedEntries, 1);
});

test("phase-1 persistence migrates v2 snapshot envelope to v5", () => {
  const v2Snapshot = {
    schemaVersion: "2",
    createdAt: 0,
    workspaceId: "workspace-0",
    metadata: {},
    state: {
      workspace: { id: "workspace-0", title: "Workspace", taskIds: [], activeTaskId: null },
      tasks: {},
      windows: {},
      widgets: {},
      layout: null
    }
  };
  const restored = restoreStateFromSnapshot(v2Snapshot);
  assert.equal(restored.snapshot.schemaVersion, "5");
  assert.ok(Array.isArray(restored.snapshot.migrationLog));
  assert.equal(restored.snapshot.migrationLog.at(-1).toVersion, "5");
});
