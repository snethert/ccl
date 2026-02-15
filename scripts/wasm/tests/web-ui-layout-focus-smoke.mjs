import assert from "node:assert/strict";

import {
  createState,
  addTask,
  addWindow,
  addWidget,
  initLayout,
  splitLayout,
  wrapInTabs,
  setActiveTab,
  dockLayout,
  reconcileFocus
} from "../../../web-ui/src/index.mjs";

let state = createState();
state = addTask(state, { id: "task-1", title: "Task" });
state = addWindow(state, { id: "win-1", taskId: "task-1", kind: "document" });
state = addWidget(state, { id: "widget-1", kind: "button", windowId: "win-1" });

state = initLayout(state, { kind: "leaf", windowId: "w1" });
const rootId = state.layout.rootId;
state = splitLayout(state, rootId, "h", 0.6, { windowId: "w2" });

const splitId = state.layout.rootId;
const leftId = state.layout.nodes[splitId].children[0];
state = wrapInTabs(state, leftId, { newTab: { windowId: "w3" }, activateNew: true });

const tabsId = Object.keys(state.layout.nodes)
  .sort()
  .find((id) => state.layout.nodes[id].kind === "tabs");
const tabId = state.layout.nodes[tabsId].children[1];
state = setActiveTab(state, tabsId, tabId);
state = dockLayout(state, state.layout.rootId, "left");

assert.equal(state.layout.nodes[state.layout.rootId].kind, "dock");
assert.equal(state.layout.nodes[tabsId].props.activeId, tabId);

const focused = reconcileFocus(state, { target: { id: "mock" }, seq: 1 }, {
  resolveTarget: () => ({ widgetId: "widget-1" })
});

assert.equal(focused.focus.widgetId, "widget-1");
assert.equal(focused.focus.windowId, "win-1");

console.log("PASS: web-ui layout/focus smoke test");
