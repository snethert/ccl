import assert from "node:assert/strict";

import {
  createState,
  addTask,
  addWindow,
  addWidget,
  createSnapshot,
  restoreStateFromSnapshot,
  createMemoryStore,
  createPersistenceManager
} from "../../../web-ui/src/index.mjs";
import { stableStringify } from "../../../web-ui/tests/snapshot.mjs";

let state = createState();
state = addTask(state, { id: "task-1", title: "Task" });
state = addWindow(state, { id: "win-1", taskId: "task-1", kind: "document" });
state = addWidget(state, { id: "root", kind: "container", windowId: "win-1" });

const store = createMemoryStore();
const manager = createPersistenceManager({ store, workspaceId: "workspace-0", flushDelay: 0, now: () => 0 });
manager.schedulePersist(state);
await manager.flushNow();

const restored = await manager.restoreState();
const before = createSnapshot(state, { now: () => 0 });
const after = createSnapshot(restored ?? state, { now: () => 0 });

assert.equal(stableStringify(before.state), stableStringify(after.state));

const legacy = { workspace: before.state.workspace, tasks: before.state.tasks, windows: before.state.windows, widgets: before.state.widgets };
const migrated = restoreStateFromSnapshot(legacy);
assert.ok(migrated, "legacy snapshot migrated");
assert.equal(migrated.snapshot.schemaVersion, "1");

console.log("PASS: web-ui persistence smoke test");
