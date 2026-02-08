import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createState,
  addTask,
  addWindow,
  addWidget,
  setFocus,
  setCommandState,
  grantCapability,
  setSafeMode,
  openInspectorWindow,
  refreshInspectorWindow,
  pinWatch,
  stageEdit,
  registerInspectorCommands,
  INSPECTOR_WATCH_PIN_COMMAND,
  INSPECTOR_WATCH_UNPIN_COMMAND,
  INSPECTOR_EDIT_STAGE_COMMAND,
  INSPECTOR_EDIT_APPLY_COMMAND,
  INSPECTOR_EDIT_UNDO_COMMAND
} from "../src/state.mjs";
import { createRegistry, executeCommand } from "../src/commands.mjs";

test("inspector window lists focus and command state", () => {
  let state = createState();
  state = addTask(state, { id: "task-1" });
  state = addWindow(state, { id: "win-1", taskId: "task-1" });
  state = addWidget(state, { id: "widget-1", kind: "button", windowId: "win-1" });
  state = setFocus(state, { windowId: "win-1", widgetId: "widget-1" });
  state = setCommandState(state, "demo.action", false, "Disabled");
  state = grantCapability(state, "dom.escape");
  state = setSafeMode(state, true, { reason: "test" });

  state = openInspectorWindow(state, { taskId: "task-1" });
  const inspector = Object.values(state.windows).find((win) => win.metadata?.role === "inspector");
  assert.ok(inspector);

  const focusListId = inspector.metadata.widgets.sections.focus.listId;
  const commandListId = inspector.metadata.widgets.sections.commands.listId;
  const capabilityListId = inspector.metadata.widgets.sections.capabilities.listId;
  const requestListId = inspector.metadata.widgets.sections.capabilityRequests.listId;
  const watchesListId = inspector.metadata.widgets.sections.watches.listId;
  const focusItems = state.widgets[focusListId].props.items;
  const commandItems = state.widgets[commandListId].props.items;
  const capabilityItems = state.widgets[capabilityListId].props.items;
  const requestItems = state.widgets[requestListId].props.items;
  const watchItems = state.widgets[watchesListId].props.items;

  assert.ok(focusItems.some((item) => item.label.includes("Focus:")));
  assert.ok(commandItems.some((item) => item.label.includes("demo.action")));
  assert.ok(capabilityItems.some((item) => item.label.includes("Safe mode: enabled")));
  assert.ok(capabilityItems.some((item) => item.label.includes("Granted: dom.escape")));
  assert.ok(requestItems.some((item) => item.label.includes("No capability requests")));
  assert.ok(watchItems.some((item) => item.label.includes("No pinned watches")));
});

test("inspector watch commands pin and unpin watches", () => {
  const registry = createRegistry();
  registerInspectorCommands(registry);

  let state = createState();
  state = addTask(state, { id: "task-1" });
  state = addWindow(state, { id: "win-1", taskId: "task-1" });
  state = pinWatch(state, {
    entryId: "ent-1",
    recordingId: "rec-1",
    label: "Seed watch",
    valueSummary: "old"
  });
  assert.equal(state.watches.length, 1);

  let result = executeCommand(registry, INSPECTOR_WATCH_PIN_COMMAND, {
    state,
    item: { entryId: "ent-2", recordingId: "rec-2", label: "Pinned from command" }
  });
  assert.equal(result.ok, true);
  state = result.result;
  assert.equal(state.watches.length, 2);

  const watchId = state.watches.find((watch) => watch.entryId === "ent-2")?.id;
  assert.ok(watchId);
  result = executeCommand(registry, INSPECTOR_WATCH_UNPIN_COMMAND, {
    state,
    watchId
  });
  assert.equal(result.ok, true);
  state = result.result;
  assert.equal(state.watches.some((watch) => watch.id === watchId), false);

  state = openInspectorWindow(state, { taskId: "task-1" });
  const inspector = Object.values(state.windows).find((win) => win.metadata?.role === "inspector");
  state = refreshInspectorWindow(state, inspector.id);
  const watchesListId = inspector.metadata.widgets.sections.watches.listId;
  const watchItems = state.widgets[watchesListId].props.items;
  assert.ok(watchItems.some((item) => item.label.includes("Seed watch")));
});

test("inspector staged edits can be applied and undone", () => {
  const registry = createRegistry();
  registerInspectorCommands(registry);

  let state = createState();
  state = addTask(state, { id: "task-1" });
  state = stageEdit(state, {
    placeId: "slot-1",
    label: "Slot edit",
    before: "old",
    after: "new"
  });
  assert.equal(state.editGroups.length, 1);

  let result = executeCommand(registry, INSPECTOR_EDIT_STAGE_COMMAND, {
    state,
    edit: { placeId: "slot-2", label: "Inline edit", before: 1, after: 2 }
  });
  assert.equal(result.ok, true);
  state = result.result;
  assert.equal(state.editGroups.length, 2);

  const editGroupId = state.editGroups[0].id;
  result = executeCommand(registry, INSPECTOR_EDIT_APPLY_COMMAND, { state, editGroupId });
  assert.equal(result.ok, true);
  state = result.result;
  assert.equal(state.editGroups[0].status, "applied");

  result = executeCommand(registry, INSPECTOR_EDIT_UNDO_COMMAND, { state, editGroupId });
  assert.equal(result.ok, true);
  state = result.result;
  assert.equal(state.editGroups[0].status, "undone");

  state = openInspectorWindow(state, { taskId: "task-1" });
  const inspector = Object.values(state.windows).find((win) => win.metadata?.role === "inspector");
  state = refreshInspectorWindow(state, inspector.id);
  const editsListId = inspector.metadata.widgets.sections.stagedEdits.listId;
  const editItems = state.widgets[editsListId].props.items;
  assert.ok(editItems.some((item) => item.label.includes("undone")));
});
