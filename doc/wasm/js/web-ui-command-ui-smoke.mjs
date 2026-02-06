import assert from "node:assert/strict";

import {
  createState,
  addTask,
  addWindow,
  COMMAND_PALETTE_FILTER_COMMAND,
  COMMAND_PALETTE_EXECUTE_COMMAND,
  COMMAND_PALETTE_SELECT_NEXT_COMMAND,
  COMMAND_PALETTE_EXECUTE_SELECTION_COMMAND,
  COMMAND_PALETTE_OPEN_COMMAND,
  COMMAND_PALETTE_CLOSE_COMMAND,
  KEYBINDINGS_OPEN_COMMAND,
  KEYBINDINGS_CLOSE_COMMAND,
  COMMAND_SURFACE_DISMISS_COMMAND,
  TASK_LIST_COMMAND,
  TASK_SWITCH_COMMAND,
  TASK_CLOSE_COMMAND,
  TASK_ARCHIVE_COMMAND,
  applyCommandPaletteFilter,
  applyCommandPaletteSelection,
  resolveCommandPaletteSelection,
  refreshCommandPaletteWindow,
  refreshKeybindingWindow,
  registerCommandPaletteCommands,
  registerTaskCommands,
  registerCommandSurfaceCommands,
  bindCommandPaletteDefaults,
  bindCommandSurfaceDefaults,
  createRegistry,
  registerCommand,
  executeCommand,
  bindKey,
  resolveKey
} from "../../../web-ui/src/index.mjs";

const registry = createRegistry();
registerCommand(registry, { id: "alpha.run", title: "Alpha Run" });
registerCommand(registry, { id: "beta.build", title: "Beta Build" });
registerCommand(registry, { id: "gamma.test", title: "Gamma Test" });
registerCommand(registry, { id: "delta.pick", title: "Delta Pick" });
bindKey(registry, "global", "K", "alpha.run");
bindKey(registry, "task", "B", "beta.build", "task-1");
bindKey(registry, "context", "C", "gamma.test", "ctx-1");
bindKey(registry, "widget", "W", "delta.pick", "widget-1");
registerCommandPaletteCommands(registry);
registerTaskCommands(registry);
registerCommandSurfaceCommands(registry);
bindCommandPaletteDefaults(registry, { taskId: "task-1" });
bindCommandSurfaceDefaults(registry);

let state = createState();
state = addTask(state, { id: "task-1", title: "Task" });

const openedPalette = executeCommand(registry, COMMAND_PALETTE_OPEN_COMMAND, {
  state,
  taskId: "task-1"
});
assert.equal(openedPalette.ok, true);
state = openedPalette.result;
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
assert.equal(selected.commandId, "delta.pick");
assert.equal(COMMAND_PALETTE_SELECT_NEXT_COMMAND, "ui.command-palette.select-next");

const bound = resolveKey(registry, "ArrowDown", { taskId: "task-1" });
assert.equal(bound, COMMAND_PALETTE_SELECT_NEXT_COMMAND);
assert.equal(resolveKey(registry, "Ctrl+Shift+P", {}), COMMAND_PALETTE_OPEN_COMMAND);
assert.equal(resolveKey(registry, "Ctrl+Shift+K", {}), KEYBINDINGS_OPEN_COMMAND);
assert.equal(resolveKey(registry, "Escape", {}), COMMAND_SURFACE_DISMISS_COMMAND);

const execSelected = executeCommand(registry, COMMAND_PALETTE_EXECUTE_SELECTION_COMMAND, {
  state,
  windowId: paletteWindow.id,
  taskId: "task-1"
});
assert.equal(execSelected.ok, true);
assert.equal(execSelected.result.ok, true);
assert.equal(execSelected.result.result, null);

const openedKeybindings = executeCommand(registry, KEYBINDINGS_OPEN_COMMAND, {
  state,
  taskId: "task-1"
});
assert.equal(openedKeybindings.ok, true);
state = openedKeybindings.result;
const keybindingWindow = Object.values(state.windows).find((win) => win.metadata?.role === "keybindings");
assert.ok(keybindingWindow, "keybinding window exists");
state = refreshKeybindingWindow(state, keybindingWindow.id, {
  registry,
  traceKey: "W",
  contextId: "ctx-1",
  widgetId: "widget-1"
});
const keybindingItems = state.widgets[keybindingWindow.metadata.widgets.listId].props.items;
assert.ok(keybindingItems.some((item) => item.label.includes("global: K → alpha.run")));
assert.ok(keybindingItems.some((item) => item.label.includes("task(task-1): B → beta.build")));
assert.ok(keybindingItems.some((item) => item.label.includes("context(ctx-1): C → gamma.test")));
assert.ok(keybindingItems.some((item) => item.label.includes("widget(widget-1): W → delta.pick")));
const traceItems = state.widgets[keybindingWindow.metadata.widgets.traceListId].props.items;
assert.ok(traceItems.some((item) => item.label.includes("widget(widget-1): W → delta.pick")));

state = refreshKeybindingWindow(state, keybindingWindow.id, {
  registry,
  traceKey: "K",
  contextId: "ctx-1",
  widgetId: "widget-1"
});
const traceItemsGlobal = state.widgets[keybindingWindow.metadata.widgets.traceListId].props.items;
assert.ok(traceItemsGlobal.some((item) => item.label.includes("global: K → alpha.run (match)")));
assert.ok(traceItemsGlobal.some((item) => item.label.includes("skipped-after-match")));

state = addTask(state, { id: "task-2", title: "Task Two" });
state = addWindow(state, { id: "win-2", taskId: "task-2", title: "Win 2" });
const openedTaskList = executeCommand(registry, TASK_LIST_COMMAND, { state, taskId: "task-1" });
assert.equal(openedTaskList.ok, true);
state = openedTaskList.result;
const taskListWindow = Object.values(state.windows).find((win) => win.metadata?.role === "task-list");
assert.ok(taskListWindow, "task list window exists");

const switchedTask = executeCommand(registry, TASK_SWITCH_COMMAND, {
  state,
  taskId: "task-1",
  itemId: "task-2"
});
assert.equal(switchedTask.ok, true);
state = switchedTask.result;
assert.equal(state.workspace.activeTaskId, "task-2");

const archivedTask = executeCommand(registry, TASK_ARCHIVE_COMMAND, {
  state,
  taskId: "task-2",
  itemId: "task-2"
});
assert.equal(archivedTask.ok, true);
state = archivedTask.result;
assert.equal(state.workspace.activeTaskId, "task-1");

const closedKeybindings = executeCommand(registry, KEYBINDINGS_CLOSE_COMMAND, {
  state,
  taskId: "task-1"
});
assert.equal(closedKeybindings.ok, true);
state = closedKeybindings.result;
assert.ok(!Object.values(state.windows).some((win) => win.metadata?.role === "keybindings"));

const closedPalette = executeCommand(registry, COMMAND_PALETTE_CLOSE_COMMAND, {
  state,
  taskId: "task-1"
});
assert.equal(closedPalette.ok, true);
state = closedPalette.result;
assert.ok(!Object.values(state.windows).some((win) => win.metadata?.role === "command-palette"));

console.log("PASS: web-ui command palette smoke test");
