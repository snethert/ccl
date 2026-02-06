import { test } from "node:test";
import assert from "node:assert/strict";

import { createState, addTask, addWindow, raiseError, openDebuggerWindow } from "../src/state.mjs";

test("debugger window coalesces errors per task", () => {
  let state = createState();
  state = addTask(state, { id: "task-1" });
  state = addWindow(state, { id: "win-1", taskId: "task-1" });

  state = raiseError(state, {
    taskId: "task-1",
    kind: "condition",
    message: "Boom",
    restarts: [{ id: "abort", title: "Abort" }],
    coalesceKey: "boom"
  });

  state = raiseError(state, {
    taskId: "task-1",
    kind: "condition",
    message: "Boom again",
    restarts: [{ id: "abort", title: "Abort" }],
    coalesceKey: "boom"
  });

  assert.equal(state.errors.length, 1);
  assert.equal(state.errors[0].count, 2);

  state = openDebuggerWindow(state, { taskId: "task-1", errorId: state.errors[0].id });
  const debuggerWindow = Object.values(state.windows).find((win) => win.metadata?.role === "debugger");
  assert.ok(debuggerWindow);
  const restartListId = debuggerWindow.metadata.widgets.restartsId;
  const restartItems = state.widgets[restartListId].props.items;
  assert.ok(restartItems.some((item) => item.label.includes("Abort")));
});
