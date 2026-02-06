import { test } from "node:test";
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
  openCommandPaletteWindow,
  refreshCommandPaletteWindow,
  openKeybindingWindow,
  refreshKeybindingWindow,
  registerCommandPaletteCommands,
  registerTaskCommands,
  registerCommandSurfaceCommands,
  bindCommandPaletteDefaults,
  bindCommandSurfaceDefaults
} from "../src/state.mjs";
import { createRegistry, registerCommand, bindKey, executeCommand, resolveKey } from "../src/commands.mjs";
import { makeContext } from "../src/context.mjs";

function makeRegistry() {
  const registry = createRegistry();
  registerCommand(registry, { id: "alpha.run", title: "Alpha Run" });
  registerCommand(registry, { id: "beta.build", title: "Beta Build" });
  registerCommand(registry, { id: "gamma.test", title: "Gamma Test" });
  registerCommand(registry, { id: "delta.pick", title: "Delta Pick" });
  bindKey(registry, "global", "K", "alpha.run");
  bindKey(registry, "task", "B", "beta.build", "task-1");
  bindKey(registry, "context", "C", "gamma.test", "ctx-1");
  bindKey(registry, "widget", "W", "delta.pick", "widget-1");
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
  bindCommandPaletteDefaults(registry, { taskId: "task-1" });

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

  const resolved = resolveKey(registry, "ArrowDown", { taskId: "task-1" });
  assert.equal(resolved, COMMAND_PALETTE_SELECT_NEXT_COMMAND);
});

test("command surface open/close commands toggle windows", () => {
  const registry = createRegistry();
  registerCommandSurfaceCommands(registry);
  bindCommandSurfaceDefaults(registry);

  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  const ctx = makeContext(state, { taskId: "task-1" });

  const openedPalette = executeCommand(registry, COMMAND_PALETTE_OPEN_COMMAND, ctx);
  assert.equal(openedPalette.ok, true);
  state = openedPalette.result;
  let palette = Object.values(state.windows).find((win) => win.metadata?.role === "command-palette");
  assert.ok(palette);

  const closedPalette = executeCommand(registry, COMMAND_PALETTE_CLOSE_COMMAND, { ...ctx, state });
  assert.equal(closedPalette.ok, true);
  state = closedPalette.result;
  palette = Object.values(state.windows).find((win) => win.metadata?.role === "command-palette");
  assert.equal(palette, undefined);

  const openedKeybindings = executeCommand(registry, KEYBINDINGS_OPEN_COMMAND, { ...ctx, state });
  assert.equal(openedKeybindings.ok, true);
  state = openedKeybindings.result;
  let viewer = Object.values(state.windows).find((win) => win.metadata?.role === "keybindings");
  assert.ok(viewer);

  const closedKeybindings = executeCommand(registry, KEYBINDINGS_CLOSE_COMMAND, { ...ctx, state });
  assert.equal(closedKeybindings.ok, true);
  state = closedKeybindings.result;
  viewer = Object.values(state.windows).find((win) => win.metadata?.role === "keybindings");
  assert.equal(viewer, undefined);

  const paletteShortcut = resolveKey(registry, "Ctrl+Shift+P", {});
  assert.equal(paletteShortcut, COMMAND_PALETTE_OPEN_COMMAND);
  const keybindingsShortcut = resolveKey(registry, "Ctrl+Shift+K", {});
  assert.equal(keybindingsShortcut, KEYBINDINGS_OPEN_COMMAND);
  const dismissShortcut = resolveKey(registry, "Escape", {});
  assert.equal(dismissShortcut, COMMAND_SURFACE_DISMISS_COMMAND);
});

test("task commands list, switch, archive, and close", () => {
  const registry = createRegistry();
  registerTaskCommands(registry);

  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task One" });
  state = addTask(state, { id: "task-2", title: "Task Two" });
  state = addWindow(state, { id: "win-1", taskId: "task-1", title: "Win 1" });
  state = addWindow(state, { id: "win-2", taskId: "task-2", title: "Win 2" });

  const ctx = makeContext(state, { taskId: "task-1" });
  const listed = executeCommand(registry, TASK_LIST_COMMAND, ctx);
  assert.equal(listed.ok, true);
  state = listed.result;
  const listWindow = Object.values(state.windows).find((win) => win.metadata?.role === "task-list");
  assert.ok(listWindow);
  const listItems = state.widgets[listWindow.metadata.widgets.listId].props.items;
  assert.ok(listItems.some((item) => item.id === "task-1"));
  assert.ok(listItems.some((item) => item.id === "task-2"));

  const switched = executeCommand(registry, TASK_SWITCH_COMMAND, { ...ctx, state, itemId: "task-2" });
  assert.equal(switched.ok, true);
  state = switched.result;
  assert.equal(state.workspace.activeTaskId, "task-2");
  assert.equal(state.focus?.windowId, "win-2");

  const archived = executeCommand(registry, TASK_ARCHIVE_COMMAND, { ...ctx, state, itemId: "task-2" });
  assert.equal(archived.ok, true);
  state = archived.result;
  assert.equal(state.tasks["task-2"].metadata.archived, true);
  assert.equal(state.workspace.activeTaskId, "task-1");

  const closed = executeCommand(registry, TASK_CLOSE_COMMAND, { ...ctx, state, itemId: "task-1" });
  assert.equal(closed.ok, true);
  state = closed.result;
  assert.equal(state.tasks["task-1"], undefined);
});

test("keybinding viewer lists bindings", () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  const registry = makeRegistry();

  state = openKeybindingWindow(state, {
    registry,
    taskId: "task-1",
    traceKey: "W",
    contextId: "ctx-1",
    widgetId: "widget-1"
  });
  const viewer = Object.values(state.windows).find((win) => win.metadata?.role === "keybindings");
  assert.ok(viewer);
  const listId = viewer.metadata.widgets.listId;
  const items = state.widgets[listId].props.items;

  assert.ok(items.some((item) => item.label.includes("global: K → alpha.run")));
  assert.ok(items.some((item) => item.label.includes("task(task-1): B → beta.build")));
  assert.ok(items.some((item) => item.label.includes("context(ctx-1): C → gamma.test")));
  assert.ok(items.some((item) => item.label.includes("widget(widget-1): W → delta.pick")));

  const traceListId = viewer.metadata.widgets.traceListId;
  const traceItems = state.widgets[traceListId].props.items;
  assert.ok(traceItems.some((item) => item.label.includes("widget(widget-1): W → delta.pick")));
  assert.ok(traceItems.some((item) => item.label.includes("context(ctx-1): W →")));

  state = refreshKeybindingWindow(state, viewer.id, {
    registry,
    traceKey: "K",
    contextId: "ctx-1",
    widgetId: "widget-1"
  });
  const traceItemsGlobal = state.widgets[traceListId].props.items;
  assert.ok(traceItemsGlobal.some((item) => item.label.includes("global: K → alpha.run (match)")));
  assert.ok(traceItemsGlobal.some((item) => item.label.includes("skipped-after-match")));
});
