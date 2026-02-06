import assert from "node:assert/strict";

import {
  createState,
  addTask,
  addWindow,
  initLayout,
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
  LAYOUT_SPLIT_COMMAND,
  LAYOUT_TABS_COMMAND,
  LAYOUT_DOCK_COMMAND,
  LAYOUT_SET_ACTIVE_TAB_COMMAND,
  CAPABILITY_REQUEST_COMMAND,
  CAPABILITY_REVOKE_COMMAND,
  CAPABILITY_OPEN_PANEL_COMMAND,
  CAPABILITY_SELECT_COMMAND,
  CAPABILITY_APPROVE_COMMAND,
  SAFE_MODE_ENABLE_COMMAND,
  SAFE_MODE_DISABLE_COMMAND,
  DOM_ESCAPE_COMMAND,
  applyCommandPaletteFilter,
  applyCommandPaletteSelection,
  resolveCommandPaletteSelection,
  refreshCommandPaletteWindow,
  refreshKeybindingWindow,
  registerCommandPaletteCommands,
  registerTaskCommands,
  registerLayoutCommands,
  registerCapabilityCommands,
  registerDomEscapeCommands,
  registerCommandSurfaceCommands,
  bindCommandPaletteDefaults,
  bindCommandSurfaceDefaults,
  createRegistry,
  registerCommand,
  registerPresentationTranslator,
  resolvePresentationCommand,
  executeCommand,
  enqueueUiSignal,
  beginUiTurn,
  advanceUiTurn,
  yieldUiTurn,
  endUiTurn,
  bindKey,
  resolveKey
} from "../../../web-ui/src/index.mjs";

const registry = createRegistry();
registerCommand(registry, { id: "alpha.run", title: "Alpha Run" });
registerCommand(registry, { id: "beta.build", title: "Beta Build" });
registerCommand(registry, { id: "gamma.test", title: "Gamma Test" });
registerCommand(registry, { id: "delta.pick", title: "Delta Pick" });
registerPresentationTranslator(registry, "file", "click", () => "alpha.run");
bindKey(registry, "global", "K", "alpha.run");
bindKey(registry, "task", "B", "beta.build", "task-1");
bindKey(registry, "context", "C", "gamma.test", "ctx-1");
bindKey(registry, "widget", "W", "delta.pick", "widget-1");
registerCommandPaletteCommands(registry);
registerTaskCommands(registry);
registerLayoutCommands(registry);
registerCommandSurfaceCommands(registry);
registerCapabilityCommands(registry);
registerDomEscapeCommands(registry);
bindCommandPaletteDefaults(registry, { taskId: "task-1" });
bindCommandSurfaceDefaults(registry);

let state = createState();
state = addTask(state, { id: "task-1", title: "Task" });

const resolvedPresentation = resolvePresentationCommand(
  registry,
  { id: "pres-1", type: "file", objectId: "file-1" },
  "click",
  {}
);
assert.equal(resolvedPresentation.commandId, "alpha.run");

const blockedEscape = executeCommand(registry, DOM_ESCAPE_COMMAND, { state, target: "#root" });
assert.equal(blockedEscape.ok, false);
assert.equal(blockedEscape.reason, "Missing capability: dom.escape");

const requestedEscape = executeCommand(registry, CAPABILITY_REQUEST_COMMAND, { state, capability: "dom.escape" });
assert.equal(requestedEscape.ok, true);
state = requestedEscape.result;

const openedMediation = executeCommand(registry, CAPABILITY_OPEN_PANEL_COMMAND, { state, taskId: "task-1" });
assert.equal(openedMediation.ok, true);
state = openedMediation.result;
const mediationWindow = Object.values(state.windows).find((win) => win.metadata?.role === "capability-mediation");
assert.ok(mediationWindow, "capability mediation window exists");
const mediationItems = state.widgets[mediationWindow.metadata.widgets.listId].props.items;
assert.ok(mediationItems.some((item) => item.label.includes("dom.escape")));

const selectedRequest = executeCommand(registry, CAPABILITY_SELECT_COMMAND, {
  state,
  taskId: "task-1",
  windowId: mediationWindow.id,
  itemId: mediationItems[0].id
});
assert.equal(selectedRequest.ok, true);
state = selectedRequest.result;

const approvedEscape = executeCommand(registry, CAPABILITY_APPROVE_COMMAND, {
  state,
  taskId: "task-1",
  windowId: mediationWindow.id
});
assert.equal(approvedEscape.ok, true);
state = approvedEscape.result;
assert.equal(state.capabilityRequests[0].status, "granted");

const allowedEscape = executeCommand(registry, DOM_ESCAPE_COMMAND, {
  state,
  target: "#root",
  detail: { reason: "probe" }
});
assert.equal(allowedEscape.ok, true);
state = allowedEscape.result;
assert.equal(state.domEscapes.length, 1);

const safeModeEnabled = executeCommand(registry, SAFE_MODE_ENABLE_COMMAND, { state });
assert.equal(safeModeEnabled.ok, true);
state = safeModeEnabled.result;

const blockedBySafeMode = executeCommand(registry, DOM_ESCAPE_COMMAND, { state, target: "#root" });
assert.equal(blockedBySafeMode.ok, false);
assert.equal(blockedBySafeMode.reason, "Safe mode");

const safeModeDisabled = executeCommand(registry, SAFE_MODE_DISABLE_COMMAND, { state });
assert.equal(safeModeDisabled.ok, true);
state = safeModeDisabled.result;

const revokedEscape = executeCommand(registry, CAPABILITY_REVOKE_COMMAND, { state, capability: "dom.escape" });
assert.equal(revokedEscape.ok, true);
state = revokedEscape.result;

const blockedAfterRevoke = executeCommand(registry, DOM_ESCAPE_COMMAND, { state, target: "#root" });
assert.equal(blockedAfterRevoke.ok, false);
assert.equal(blockedAfterRevoke.reason, "Missing capability: dom.escape");

let uiSeq = 1;
state = enqueueUiSignal(state, { type: "input:pointer", payload: { x: 5, y: 10 } }, { recordEvent: true, seq: uiSeq++ });
state = enqueueUiSignal(state, { type: "input:key", payload: { key: "K" } }, { recordEvent: true, seq: uiSeq++ });
state = beginUiTurn(state, { commitPolicy: "rAF", recordEvent: true, seq: uiSeq++ });
assert.equal(state.ui.turn.phase, "signals");
assert.equal(state.ui.turn.signals.length, 2);
state = advanceUiTurn(state, "commands", { recordEvent: true, seq: uiSeq++ });
assert.equal(state.ui.turn.phase, "commands");
state = yieldUiTurn(state, "awaiting-input", { recordEvent: true, seq: uiSeq++ });
assert.equal(state.ui.turn.phase, "yielded");
state = endUiTurn(state, { recordEvent: true, seq: uiSeq++ });
assert.equal(state.ui.turn, null);
const uiEventTypes = state.eventLog.entries.map((entry) => entry.type);
assert.deepEqual(uiEventTypes, [
  "ui:signal.enqueue",
  "ui:signal.enqueue",
  "ui:turn.begin",
  "ui:turn.phase",
  "ui:turn.yield",
  "ui:turn.end"
]);

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

state = addWindow(state, { id: "layout-win-1", taskId: "task-1", title: "Layout Win 1" });
state = addWindow(state, { id: "layout-win-2", taskId: "task-1", title: "Layout Win 2" });
state = addWindow(state, { id: "layout-win-3", taskId: "task-1", title: "Layout Win 3" });
state = initLayout(state, { kind: "leaf", windowId: "layout-win-1" });

const splitLayout = executeCommand(registry, LAYOUT_SPLIT_COMMAND, {
  state,
  windowId: "layout-win-1",
  newWindowId: "layout-win-2",
  axis: "v",
  ratio: 0.4
});
assert.equal(splitLayout.ok, true);
state = splitLayout.result;

const tabsLayout = executeCommand(registry, LAYOUT_TABS_COMMAND, {
  state,
  layoutId: Object.entries(state.layout.nodes).find(([, node]) => node.kind === "leaf" && node.props?.windowId === "layout-win-1")?.[0],
  newWindowId: "layout-win-3",
  activateNew: true
});
assert.equal(tabsLayout.ok, true);
state = tabsLayout.result;

const tabsId = Object.entries(state.layout.nodes).find(([, node]) => node.kind === "tabs")?.[0];
const tabId = Object.entries(state.layout.nodes).find(([, node]) => node.kind === "leaf" && node.props?.windowId === "layout-win-3")?.[0];
const setActive = executeCommand(registry, LAYOUT_SET_ACTIVE_TAB_COMMAND, {
  state,
  tabsId,
  tabId
});
assert.equal(setActive.ok, true);
state = setActive.result;

const dockedLayout = executeCommand(registry, LAYOUT_DOCK_COMMAND, {
  state,
  layoutId: tabId,
  region: "right"
});
assert.equal(dockedLayout.ok, true);
state = dockedLayout.result;

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
