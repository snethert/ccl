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

test("command history execute command records typed invocation with resolved defaults", () => {
  const registry = createRegistry();
  registerCommand(registry, {
    id: "cmd.inspect",
    args: [{ name: "target", type: "selection", required: true, defaultFrom: ["selection"] }],
    exec: (ctx) => ({ state: { ...ctx.state, marker: ctx.args.target.id } })
  });
  registerCommandHistoryCommands(registry);

  let state = createState({
    selection: {
      id: "sel-1",
      kind: "presentation",
      targetIds: ["pres-1"],
      anchorId: "pres-1",
      metadata: {}
    }
  });
  state = addTask(state, { id: "task-1", title: "Task" });

  const result = executeCommand(registry, COMMAND_HISTORY_EXECUTE_COMMAND, {
    state,
    registry,
    invocation: { commandId: "cmd.inspect", args: {} }
  });
  assert.equal(result.ok, true);
  assert.equal(result.result.marker, "sel-1");
  assert.equal(result.result.commandHistory.length, 1);
  assert.equal(result.result.commandHistory[0].commandId, "cmd.inspect");
  assert.equal(result.result.commandHistory[0].defaults.target.source, "selection");
});

test("recordCommandInvocation auto-allocates deterministic id when missing", () => {
  let state = createState();
  state = recordCommandInvocation(state, { commandId: "cmd-1", args: {} });
  state = recordCommandInvocation(state, { commandId: "cmd-2", args: {} });
  assert.equal(state.commandHistory[0].id, "inv-1");
  assert.equal(state.commandHistory[1].id, "inv-2");
});
