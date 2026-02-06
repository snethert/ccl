import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createState,
  addTask,
  addWindow,
  addWidget,
  setFocus,
  setCommandState,
  openInspectorWindow
} from "../src/state.mjs";

test("inspector window lists focus and command state", () => {
  let state = createState();
  state = addTask(state, { id: "task-1" });
  state = addWindow(state, { id: "win-1", taskId: "task-1" });
  state = addWidget(state, { id: "widget-1", kind: "button", windowId: "win-1" });
  state = setFocus(state, { windowId: "win-1", widgetId: "widget-1" });
  state = setCommandState(state, "demo.action", false, "Disabled");

  state = openInspectorWindow(state, { taskId: "task-1" });
  const inspector = Object.values(state.windows).find((win) => win.metadata?.role === "inspector");
  assert.ok(inspector);

  const focusListId = inspector.metadata.widgets.sections.focus.listId;
  const commandListId = inspector.metadata.widgets.sections.commands.listId;
  const focusItems = state.widgets[focusListId].props.items;
  const commandItems = state.widgets[commandListId].props.items;

  assert.ok(focusItems.some((item) => item.label.includes("Focus:")));
  assert.ok(commandItems.some((item) => item.label.includes("demo.action")));
});
