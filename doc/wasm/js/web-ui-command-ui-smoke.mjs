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
  registerCommandPaletteCommands,
  bindCommandPaletteDefaults,
  createRegistry,
  registerCommand,
  executeCommand,
  bindKey,
  resolveKey
} from "../../../web-ui/src/index.mjs";

const registry = createRegistry();
registerCommand(registry, { id: "alpha.run", title: "Alpha Run" });
registerCommand(registry, { id: "beta.build", title: "Beta Build" });
bindKey(registry, "global", "K", "alpha.run");
bindKey(registry, "task", "B", "beta.build", "task-1");
registerCommandPaletteCommands(registry);
bindCommandPaletteDefaults(registry, { taskId: "task-1" });

let state = createState();
state = addTask(state, { id: "task-1", title: "Task" });

state = openCommandPaletteWindow(state, { registry, taskId: "task-1" });
const paletteWindow = Object.values(state.windows).find((win) => win.metadata?.role === "command-palette");
assert.ok(paletteWindow, "command palette window exists");
const filterId = paletteWindow.metadata.widgets.filterId;
assert.equal(
  state.widgets[filterId].props.command,
  COMMAND_PALETTE_FILTER_COMMAND
);
const paletteItems = state.widgets[paletteWindow.metadata.widgets.listId].props.items;
assert.ok(paletteItems.some((item) => item.label.includes("alpha.run")));
assert.equal(
  state.widgets[paletteWindow.metadata.widgets.listId].props.itemCommand,
  COMMAND_PALETTE_EXECUTE_COMMAND
);
assert.equal(paletteItems[0].selected, true);

state = applyCommandPaletteFilter(state, { registry, windowId: paletteWindow.id, filter: "beta" });
const filteredItems = state.widgets[paletteWindow.metadata.widgets.listId].props.items;
assert.equal(filteredItems.length, 1);
assert.ok(filteredItems[0].label.includes("beta.build"));

state = refreshCommandPaletteWindow(state, paletteWindow.id, { registry, filter: "" });
state = applyCommandPaletteSelection(state, { registry, windowId: paletteWindow.id, delta: 1 });
const selected = resolveCommandPaletteSelection(state, { windowId: paletteWindow.id });
assert.equal(selected.commandId, "beta.build");
assert.equal(COMMAND_PALETTE_SELECT_NEXT_COMMAND, "ui.command-palette.select-next");

const bound = resolveKey(registry, "ArrowDown", { taskId: "task-1" });
assert.equal(bound, COMMAND_PALETTE_SELECT_NEXT_COMMAND);

const execSelected = executeCommand(registry, COMMAND_PALETTE_EXECUTE_SELECTION_COMMAND, {
  state,
  windowId: paletteWindow.id,
  taskId: "task-1"
});
assert.equal(execSelected.ok, true);
assert.equal(execSelected.result.ok, true);
assert.equal(execSelected.result.result, null);

state = openKeybindingWindow(state, { registry, taskId: "task-1" });
const keybindingWindow = Object.values(state.windows).find((win) => win.metadata?.role === "keybindings");
assert.ok(keybindingWindow, "keybinding window exists");
const keybindingItems = state.widgets[keybindingWindow.metadata.widgets.listId].props.items;
assert.ok(keybindingItems.some((item) => item.label.includes("global: K → alpha.run")));
assert.ok(keybindingItems.some((item) => item.label.includes("task(task-1): B → beta.build")));

console.log("PASS: web-ui command palette smoke test");
