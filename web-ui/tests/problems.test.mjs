import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createState,
  addTask,
  raiseError,
  openProblemsWindow,
  refreshProblemsWindow,
  registerProblemsCommands,
  PROBLEMS_OPEN_COMMAND,
  PROBLEMS_REFRESH_COMMAND,
  PROBLEMS_ITEM_OPEN_COMMAND
} from "../src/state.mjs";
import { createRegistry, executeCommand } from "../src/commands.mjs";

test("problems window lists errors", () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = raiseError(state, { taskId: "task-1", message: "Boom", kind: "error" });

  state = openProblemsWindow(state, { taskId: "task-1" });
  const window = Object.values(state.windows).find((win) => win.metadata?.role === "problems");
  assert.ok(window, "problems window exists");
  const listId = window.metadata.widgets.listId;
  const items = state.widgets[listId].props.items;
  assert.ok(items[0].label.includes("Boom"));
});

test("refreshProblemsWindow updates list", () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = openProblemsWindow(state, { taskId: "task-1" });
  const window = Object.values(state.windows).find((win) => win.metadata?.role === "problems");

  state = raiseError(state, { taskId: "task-1", message: "Later", kind: "warning" });
  state = refreshProblemsWindow(state, window.id);
  const items = state.widgets[window.metadata.widgets.listId].props.items;
  assert.ok(items[0].label.includes("Later"));
});

test("problems commands open and refresh", () => {
  const registry = createRegistry();
  registerProblemsCommands(registry);

  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  const opened = executeCommand(registry, PROBLEMS_OPEN_COMMAND, { state, taskId: "task-1" });
  assert.equal(opened.ok, true);
  state = opened.result;

  const window = Object.values(state.windows).find((win) => win.metadata?.role === "problems");
  const refreshed = executeCommand(registry, PROBLEMS_REFRESH_COMMAND, { state, windowId: window.id });
  assert.equal(refreshed.ok, true);
});

test("problems item command opens debugger", () => {
  const registry = createRegistry();
  registerProblemsCommands(registry);

  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = raiseError(state, { taskId: "task-1", message: "Boom", kind: "error" });
  state = openProblemsWindow(state, { taskId: "task-1" });

  const window = Object.values(state.windows).find((win) => win.metadata?.role === "problems");
  const items = state.widgets[window.metadata.widgets.listId].props.items;
  const item = items[0];

  const opened = executeCommand(registry, PROBLEMS_ITEM_OPEN_COMMAND, { state, item });
  assert.equal(opened.ok, true);
  state = opened.result;

  const debuggerWindow = Object.values(state.windows).find((win) => win.metadata?.role === "debugger");
  assert.ok(debuggerWindow, "debugger window opens");
});
