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
  openInspectorWindow
} from "../src/state.mjs";

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
  const focusItems = state.widgets[focusListId].props.items;
  const commandItems = state.widgets[commandListId].props.items;
  const capabilityItems = state.widgets[capabilityListId].props.items;

  assert.ok(focusItems.some((item) => item.label.includes("Focus:")));
  assert.ok(commandItems.some((item) => item.label.includes("demo.action")));
  assert.ok(capabilityItems.some((item) => item.label.includes("Safe mode: enabled")));
  assert.ok(capabilityItems.some((item) => item.label.includes("Granted: dom.escape")));
});
