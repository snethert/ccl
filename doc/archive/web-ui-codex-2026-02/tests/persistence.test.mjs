import { test } from "node:test";
import assert from "node:assert/strict";

import { createState, addTask, addWindow, addWidget } from "../src/state.mjs";
import {
  createSnapshot,
  restoreStateFromSnapshot,
  createRecordingStore,
  appendRecordingToStore,
  appendEntryToStore,
  createMemoryStore,
  createPersistenceManager
} from "../src/index.mjs";
import { stableStringify } from "./snapshot.mjs";

test("createSnapshot strips non-serializable values", () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = addWindow(state, { id: "win-1", taskId: "task-1", kind: "document" });
  state = addWidget(state, {
    id: "root",
    kind: "container",
    windowId: "win-1",
    props: { onClick: () => "nope", data: { ok: true } }
  });

  const snapshot = createSnapshot(state, { now: () => 0 });
  const widget = snapshot.state.widgets.root;
  assert.ok(widget, "widget persists");
  assert.equal(widget.props.onClick, undefined);
  assert.deepEqual(widget.props.data, { ok: true });
});

test("restoreStateFromSnapshot validates focus targets", () => {
  const snapshot = {
    schemaVersion: "1",
    createdAt: 0,
    workspaceId: "workspace-0",
    metadata: {},
    state: {
      workspace: { id: "workspace-0", taskIds: ["task-1"], activeTaskId: "task-1", title: "Workspace" },
      tasks: { "task-1": { id: "task-1", title: "Task", windowIds: [], activeWindowId: null, metadata: {} } },
      windows: {},
      widgets: {},
      layout: null,
      focus: { taskId: "task-1", windowId: "win-missing", widgetId: null },
      idCounters: { task: 1, window: 0, widget: 0 }
    }
  };

  const restored = restoreStateFromSnapshot(snapshot);
  assert.ok(restored, "restored state exists");
  assert.equal(restored.state.focus, null);
});

test("persistence manager round-trips state", async () => {
  const store = createMemoryStore();
  const manager = createPersistenceManager({ store, workspaceId: "workspace-0", flushDelay: 0, now: () => 0 });

  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = addWindow(state, { id: "win-1", taskId: "task-1", kind: "document" });
  state = addWidget(state, { id: "root", kind: "container", windowId: "win-1" });

  manager.schedulePersist(state);
  await manager.flushNow();

  const restored = await manager.restoreState();
  const before = createSnapshot(state, { now: () => 0 });
  const after = createSnapshot(restored, { now: () => 0 });

  assert.equal(stableStringify(before.state), stableStringify(after.state));
});

test("createSnapshot persists recording store and command history", () => {
  const store = appendEntryToStore(
    appendRecordingToStore(createRecordingStore(), { id: "rec-1" }),
    { id: "ent-1", recordingId: "rec-1" }
  );
  const state = createState({
    recordingStore: store,
    commandHistory: [{ id: "inv-1", commandId: "cmd-1", args: { value: 1 } }]
  });

  const snapshot = createSnapshot(state, { now: () => 0 });
  assert.ok(snapshot.state.recordingStore);
  assert.equal(snapshot.state.recordingStore.recordingOrder[0], "rec-1");
  assert.deepEqual(snapshot.state.commandHistory, [{ id: "inv-1", commandId: "cmd-1", args: { value: 1 } }]);
});

test("restoreStateFromSnapshot migrates legacy snapshots", () => {
  const legacy = {
    workspace: { id: "workspace-0", taskIds: [], activeTaskId: null, title: "Workspace" },
    tasks: {},
    windows: {},
    widgets: {},
    layout: null
  };

  const restored = restoreStateFromSnapshot(legacy);
  assert.ok(restored, "restored legacy snapshot");
  assert.equal(restored.snapshot.schemaVersion, "5");
});

test("restoreStateFromSnapshot revalidates presentations when resolver is provided", () => {
  const state = createState({
    presentations: {
      "pres-1": {
        id: "pres-1",
        type: "value",
        metadata: { summary: "stale me" }
      }
    }
  });
  const snapshot = createSnapshot(state, { now: () => 0 });

  const restored = restoreStateFromSnapshot(snapshot, {
    presentationResolver: () => ({ ok: false, reason: "not-live" })
  });

  assert.ok(restored, "restored state exists");
  assert.equal(restored.state.presentations["pres-1"].metadata.stale, true);
  assert.equal(restored.state.presentations["pres-1"].metadata.staleReason, "not-live");
  assert.deepEqual(restored.stalePresentations, ["pres-1"]);
});

test("createSnapshot applies recording store truncation budget with marker", () => {
  let store = createRecordingStore();
  store = appendRecordingToStore(store, { id: "rec-1" });
  store = appendEntryToStore(store, { id: "ent-1", recordingId: "rec-1", text: "1111111111" });
  store = appendEntryToStore(store, { id: "ent-2", recordingId: "rec-1", text: "2222222222" });
  store = appendEntryToStore(store, { id: "ent-3", recordingId: "rec-1", text: "3333333333" });

  const state = createState({ recordingStore: store });
  const snapshot = createSnapshot(state, {
    now: () => 0,
    recordingBudget: { maxEntries: 2, maxBytes: 1024 }
  });

  const persisted = snapshot.state.recordingStore;
  assert.deepEqual(persisted.entryOrder, ["ent-2", "ent-3"]);
  assert.equal(persisted.truncation.applied, true);
  assert.equal(persisted.truncation.droppedEntries, 1);
  assert.equal(persisted.truncation.retainedEntries, 2);
  assert.equal(persisted.truncation.maxEntries, 2);
});

test("createSnapshot persists inspector watches", () => {
  const state = createState({
    watches: [
      {
        id: "watch-1",
        label: "Result Watch",
        entryId: "ent-1",
        recordingId: "rec-1",
        valueSummary: "3",
        pinned: true
      }
    ],
    watchSeq: 2
  });

  const snapshot = createSnapshot(state, { now: () => 0 });
  const restored = restoreStateFromSnapshot(snapshot);
  assert.equal(Array.isArray(restored.state.watches), true);
  assert.equal(restored.state.watches.length, 1);
  assert.equal(restored.state.watches[0].label, "Result Watch");
  assert.equal(restored.state.watchSeq, 2);
});
