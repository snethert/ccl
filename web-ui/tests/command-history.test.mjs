import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createState,
  addTask,
  recordCommandInvocation,
  openCommandHistoryWindow,
  refreshCommandHistoryWindow,
  registerCommandHistoryCommands,
  COMMAND_HISTORY_EXECUTE_COMMAND,
  COMMAND_HISTORY_OPEN_COMMAND
} from "../src/state.mjs";
import { createRegistry, registerCommand, executeCommand } from "../src/commands.mjs";

test("command history window lists invocations", () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = recordCommandInvocation(state, { id: "inv-1", commandId: "cmd-1", args: { value: 1 } });

  state = openCommandHistoryWindow(state, { taskId: "task-1" });
  const window = Object.values(state.windows).find((win) => win.metadata?.role === "command-history");
  assert.ok(window, "command history window exists");
  const listId = window.metadata.widgets.listId;
  const items = state.widgets[listId].props.items;
  assert.ok(items[0].label.includes("cmd-1"));
});

test("refreshCommandHistoryWindow updates list", () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = openCommandHistoryWindow(state, { taskId: "task-1" });
  const window = Object.values(state.windows).find((win) => win.metadata?.role === "command-history");

  state = recordCommandInvocation(state, { id: "inv-1", commandId: "cmd-1" });
  state = refreshCommandHistoryWindow(state, window.id);
  const items = state.widgets[window.metadata.widgets.listId].props.items;
  assert.ok(items[0].label.includes("cmd-1"));
});

test("command history execute command replays invocation", () => {
  const registry = createRegistry();
  registerCommand(registry, {
    id: "cmd-1",
    exec: (ctx) => ({ state: { ...ctx.state, marker: ctx.payload?.value ?? null } })
  });
  registerCommandHistoryCommands(registry);

  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });

  const open = executeCommand(registry, COMMAND_HISTORY_OPEN_COMMAND, { state, taskId: "task-1" });
  state = open.result;

  const result = executeCommand(registry, COMMAND_HISTORY_EXECUTE_COMMAND, {
    state,
    registry,
    invocation: { id: "inv-1", commandId: "cmd-1", args: { value: "ok" } }
  });
  assert.equal(result.ok, true);
  assert.equal(result.result.marker, "ok");
});
