import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createState,
  addTask,
  raiseError,
  openDebuggerWindow,
  registerDebuggerCommands,
  DEBUGGER_RESTART_INVOKE_COMMAND,
  LIST_SELECTION_UPDATE_COMMAND
} from "../src/state.mjs";
import { createRegistry, executeCommand } from "../src/commands.mjs";

test("debugger restart list wires item command", () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = raiseError(state, {
    taskId: "task-1",
    message: "Boom",
    kind: "error",
    restarts: [{ id: "restart-1", title: "Retry" }]
  });

  state = openDebuggerWindow(state, { taskId: "task-1" });
  const window = Object.values(state.windows).find((win) => win.metadata?.role === "debugger");
  assert.ok(window, "debugger window exists");
  const listId = window.metadata.widgets.restartsId;
  assert.equal(state.widgets[listId].props.itemCommand, DEBUGGER_RESTART_INVOKE_COMMAND);
  assert.equal(state.widgets[listId].props.selectionCommand, LIST_SELECTION_UPDATE_COMMAND);
  assert.equal(state.widgets[listId].props.selectionActionBar, true);
  assert.equal(
    state.widgets[listId].props.selectionActionCommands["invoke-restart"],
    DEBUGGER_RESTART_INVOKE_COMMAND
  );
});

test("debugger restart command records typed invocation", () => {
  const registry = createRegistry();
  registerDebuggerCommands(registry);

  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = raiseError(state, {
    taskId: "task-1",
    message: "Boom",
    kind: "error",
    restarts: [{ id: "restart-1", title: "Retry" }]
  });
  const errorId = state.errors[0].id;

  state = openDebuggerWindow(state, { taskId: "task-1", errorId });
  const window = Object.values(state.windows).find((win) => win.metadata?.role === "debugger");
  const listId = window.metadata.widgets.restartsId;
  const item = state.widgets[listId].props.items[0];

  const result = executeCommand(registry, DEBUGGER_RESTART_INVOKE_COMMAND, { state, item });
  assert.equal(result.ok, true);
  state = result.result?.state ?? result.result ?? state;

  assert.equal(state.commandHistory.length, 1);
  const invocation = state.commandHistory[0];
  assert.equal(invocation.commandId, DEBUGGER_RESTART_INVOKE_COMMAND);
  assert.equal(invocation.args.restartId, "restart-1");
  assert.equal(invocation.args.errorId, errorId);
});
