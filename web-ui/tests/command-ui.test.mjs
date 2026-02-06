import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createState,
  addTask,
  COMMAND_PALETTE_FILTER_COMMAND,
  COMMAND_PALETTE_EXECUTE_COMMAND,
  applyCommandPaletteFilter,
  openCommandPaletteWindow,
  refreshCommandPaletteWindow,
  openKeybindingWindow
} from "../src/state.mjs";
import { createRegistry, registerCommand, bindKey } from "../src/commands.mjs";

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

  state = applyCommandPaletteFilter(state, {
    registry,
    windowId: paletteWindow.id,
    filter: "alpha"
  });
  const filtered = state.widgets[listId].props.items;
  assert.equal(filtered.length, 1);
  assert.ok(filtered[0].label.includes("alpha.run"));

  state = refreshCommandPaletteWindow(state, paletteWindow.id, { registry, filter: "" });
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
