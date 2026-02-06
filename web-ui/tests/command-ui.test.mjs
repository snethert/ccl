import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createState,
  addTask,
  COMMAND_PALETTE_FILTER_COMMAND,
  COMMAND_PALETTE_EXECUTE_COMMAND,
  COMMAND_PALETTE_SELECT_NEXT_COMMAND,
  COMMAND_PALETTE_EXECUTE_SELECTION_COMMAND,
  applyCommandPaletteFilter,
  applyCommandPaletteSelection,
  resolveCommandPaletteSelection,
  openCommandPaletteWindow,
  refreshCommandPaletteWindow,
  openKeybindingWindow,
  registerCommandPaletteCommands
} from "../src/state.mjs";
import { createRegistry, registerCommand, bindKey, executeCommand } from "../src/commands.mjs";
import { makeContext } from "../src/context.mjs";

function makeRegistry() {
  const registry = createRegistry();
  registerCommand(registry, { id: "alpha.run", title: "Alpha Run" });
  registerCommand(registry, { id: "beta.build", title: "Beta Build" });
  bindKey(registry, "global", "K", "alpha.run");
  bindKey(registry, "task", "B", "beta.build", "task-1");
  return registry;
}

test("command palette lists commands and applies filter", () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });

  const registry = makeRegistry();
  state = openCommandPaletteWindow(state, { registry, taskId: "task-1" });
  const paletteWindow = Object.values(state.windows).find((win) => win.metadata?.role === "command-palette");
  assert.ok(paletteWindow);

  const filterId = paletteWindow.metadata.widgets.filterId;
  assert.equal(state.widgets[filterId].props.command, COMMAND_PALETTE_FILTER_COMMAND);

  const listId = paletteWindow.metadata.widgets.listId;
  const items = state.widgets[listId].props.items;
  assert.ok(items.some((item) => item.label.includes("alpha.run")));
  assert.ok(items.some((item) => item.label.includes("beta.build")));
  assert.equal(state.widgets[listId].props.itemCommand, COMMAND_PALETTE_EXECUTE_COMMAND);
  assert.equal(items[0].targetCommandId, "alpha.run");
  assert.equal(items[0].selected, true);
  assert.equal(items[1].selected, false);

  state = applyCommandPaletteFilter(state, {
    registry,
    windowId: paletteWindow.id,
    filter: "alpha"
  });
  const filtered = state.widgets[listId].props.items;
  assert.equal(filtered.length, 1);
  assert.ok(filtered[0].label.includes("alpha.run"));

  state = refreshCommandPaletteWindow(state, paletteWindow.id, { registry, filter: "" });

  state = applyCommandPaletteSelection(state, {
    registry,
    windowId: paletteWindow.id,
    delta: 1
  });
  const updatedItems = state.widgets[listId].props.items;
  assert.equal(updatedItems[0].selected, false);
  assert.equal(updatedItems[1].selected, true);

  const selection = resolveCommandPaletteSelection(state, { windowId: paletteWindow.id });
  assert.equal(selection.commandId, "beta.build");
  assert.equal(COMMAND_PALETTE_SELECT_NEXT_COMMAND, "ui.command-palette.select-next");
});

test("palette command registration wires navigation and execution", () => {
  const registry = createRegistry();
  registerCommand(registry, { id: "alpha.run", exec: () => "alpha" });
  registerCommand(registry, { id: "beta.build", exec: () => "beta" });
  registerCommandPaletteCommands(registry);

  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = openCommandPaletteWindow(state, { registry, taskId: "task-1" });
  const paletteWindow = Object.values(state.windows).find((win) => win.metadata?.role === "command-palette");
  assert.ok(paletteWindow);
  const listId = paletteWindow.metadata.widgets.listId;
  const listItems = state.widgets[listId].props.items;
  assert.ok(listItems.some((item) => item.targetCommandId === "alpha.run"));
  assert.ok(listItems.some((item) => item.targetCommandId === "beta.build"));
  assert.ok(!listItems.some((item) => item.targetCommandId === COMMAND_PALETTE_EXECUTE_COMMAND));

  const ctx = makeContext(state, { taskId: "task-1", windowId: paletteWindow.id });
  const next = executeCommand(registry, COMMAND_PALETTE_SELECT_NEXT_COMMAND, ctx);
  assert.equal(next.ok, true);
  const nextState = next.result;

  const selection = resolveCommandPaletteSelection(nextState, { windowId: paletteWindow.id });
  assert.equal(selection.commandId, "beta.build");

  const execSelected = executeCommand(registry, COMMAND_PALETTE_EXECUTE_SELECTION_COMMAND, {
    ...ctx,
    state: nextState
  });
  assert.equal(execSelected.ok, true);
  assert.equal(execSelected.result.ok, true);
  assert.equal(execSelected.result.result, "beta");
});

test("keybinding viewer lists bindings", () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  const registry = makeRegistry();

  state = openKeybindingWindow(state, { registry, taskId: "task-1" });
  const viewer = Object.values(state.windows).find((win) => win.metadata?.role === "keybindings");
  assert.ok(viewer);
  const listId = viewer.metadata.widgets.listId;
  const items = state.widgets[listId].props.items;

  assert.ok(items.some((item) => item.label.includes("global: K → alpha.run")));
  assert.ok(items.some((item) => item.label.includes("task(task-1): B → beta.build")));
});
