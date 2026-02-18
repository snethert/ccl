import { test } from "node:test";
import assert from "node:assert/strict";

import { restoreStateFromSnapshot } from "../src/persistence/serialize.mjs";

test("phase-4 restore drops layout nodes with missing windows", () => {
  const snapshot = {
    schemaVersion: "4",
    createdAt: 0,
    workspaceId: "workspace-0",
    metadata: {},
    state: {
      workspace: { id: "workspace-0", taskIds: ["task-1"], activeTaskId: "task-1", title: "Workspace" },
      tasks: { "task-1": { id: "task-1", title: "Task", windowIds: [], activeWindowId: null, metadata: {} } },
      windows: {},
      widgets: {},
      layout: {
        rootId: "layout-0",
        nodes: {
          "layout-0": { id: "layout-0", kind: "leaf", children: [], props: { windowId: "win-missing" } }
        }
      }
    }
  };

  const restored = restoreStateFromSnapshot(snapshot);
  assert.equal(restored.state.layout, null);
});
