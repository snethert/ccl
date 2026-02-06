import { test } from "node:test";
import assert from "node:assert/strict";

import { createState, addTask, addWindow, addWidget } from "../src/state.mjs";
import {
  createSnapshot,
  restoreStateFromSnapshot,
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
  assert.equal(restored.snapshot.schemaVersion, "1");
});
