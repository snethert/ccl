import assert from "node:assert/strict";

import {
  createState,
  addTask,
  addWindow,
  raiseError,
  openDebuggerWindow
} from "../../../web-ui/src/index.mjs";

let state = createState();
state = addTask(state, { id: "task-1", title: "Task" });
state = addWindow(state, { id: "win-1", taskId: "task-1", kind: "document" });

state = raiseError(state, {
  taskId: "task-1",
  kind: "condition",
  message: "Boom",
  restarts: [{ id: "abort", title: "Abort" }],
  coalesceKey: "boom"
});

state = openDebuggerWindow(state, { taskId: "task-1", errorId: state.errors[0].id });
const debuggerWindow = Object.values(state.windows).find((win) => win.metadata?.role === "debugger");
assert.ok(debuggerWindow, "debugger window created");

const restartListId = debuggerWindow.metadata.widgets.restartsId;
const restartItems = state.widgets[restartListId].props.items;
assert.ok(restartItems.some((item) => item.label.includes("Abort")), "restart list populated");

console.log("PASS: web-ui debugger smoke test");
