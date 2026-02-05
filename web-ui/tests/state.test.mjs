import { test } from "node:test";
import assert from "node:assert/strict";

import { createState, addTask, addWindow, addWidget } from "../src/state.mjs";

function makeStateWithTaskAndWindow() {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = addWindow(state, { id: "win-1", taskId: "task-1", title: "Main" });
  return state;
}

test("addTask wires workspace and active task", () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "First" });

  assert.equal(state.workspace.activeTaskId, "task-1");
  assert.deepEqual(state.workspace.taskIds, ["task-1"]);
  assert.ok(state.tasks["task-1"]);
});

test("addWindow wires task and active window", () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = addWindow(state, { id: "win-1", taskId: "task-1", title: "Main" });

  assert.deepEqual(state.tasks["task-1"].windowIds, ["win-1"]);
  assert.equal(state.tasks["task-1"].activeWindowId, "win-1");
  assert.equal(state.windows["win-1"].taskId, "task-1");
});

test("addWidget wires parent/child and window root", () => {
  let state = makeStateWithTaskAndWindow();
  state = addWidget(state, { id: "widget-root", windowId: "win-1", kind: "root" });
  state = addWidget(state, { id: "widget-child", parentId: "widget-root", kind: "label" });

  assert.equal(state.windows["win-1"].rootWidgetId, "widget-root");
  assert.deepEqual(state.widgets["widget-root"].childIds, ["widget-child"]);
});
