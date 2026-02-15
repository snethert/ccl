import assert from "node:assert/strict";

import {
  createState,
  addTask,
  addWindow,
  addWidget,
  setFocus,
  setCommandState,
  openInspectorWindow
} from "../../../web-ui/src/index.mjs";

let state = createState();
state = addTask(state, { id: "task-1", title: "Task" });
state = addWindow(state, { id: "win-1", taskId: "task-1", kind: "document" });
state = addWidget(state, { id: "widget-1", kind: "button", windowId: "win-1" });
state = setFocus(state, { windowId: "win-1", widgetId: "widget-1" });
state = setCommandState(state, "demo.action", false, "Disabled");

state = openInspectorWindow(state, { taskId: "task-1" });
const inspector = Object.values(state.windows).find((win) => win.metadata?.role === "inspector");
assert.ok(inspector, "inspector window created");

const focusListId = inspector.metadata.widgets.sections.focus.listId;
const focusItems = state.widgets[focusListId].props.items;
assert.ok(focusItems.some((item) => item.label.includes("Focus:")), "focus section populated");

console.log("PASS: web-ui inspector smoke test");
