import { test } from "node:test";
import assert from "node:assert/strict";

import { createState, addTask, addWindow, addWidget } from "../src/state.mjs";
import { renderWindow } from "../src/widgets.mjs";
import { themeToCssVars } from "../src/index.mjs";

function findByWidgetId(node, widgetId) {
  if (!node || node.kind !== "element") return null;
  if (node.props?.["data-widget-id"] === widgetId) return node;
  for (const child of node.children ?? []) {
    const found = findByWidgetId(child, widgetId);
    if (found) return found;
  }
  return null;
}

test("phase-7 accessibility canvas and webgl widgets expose explicit accessibility contracts", () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = addWindow(state, { id: "win-1", taskId: "task-1", kind: "document" });
  state = addWidget(state, { id: "root", kind: "container", windowId: "win-1" });
  state = addWidget(state, { id: "canvas-default", kind: "canvas-view", parentId: "root", props: { width: 80, height: 40 } });
  state = addWidget(state, {
    id: "canvas-accessible",
    kind: "canvas-view",
    parentId: "root",
    props: {
      width: 80,
      height: 40,
      accessibility: { enabled: true, role: "img", label: "Profiler flame chart", tabIndex: 0 }
    }
  });
  state = addWidget(state, {
    id: "webgl-accessible",
    kind: "webgl-view",
    parentId: "root",
    props: {
      width: 80,
      height: 40,
      accessibility: { enabled: true, role: "img", label: "Heap graph", tabIndex: 1 }
    }
  });

  const tree = renderWindow(state, "win-1");
  const canvasDefault = findByWidgetId(tree, "canvas-default");
  const canvasAccessible = findByWidgetId(tree, "canvas-accessible");
  const webglAccessible = findByWidgetId(tree, "webgl-accessible");

  assert.ok(canvasDefault);
  assert.equal(canvasDefault.props.role, "presentation");
  assert.equal(canvasDefault.props["aria-hidden"], "true");
  assert.equal(canvasDefault.props["data-accessible"], "false");

  assert.ok(canvasAccessible);
  assert.equal(canvasAccessible.props.role, "img");
  assert.equal(canvasAccessible.props["aria-label"], "Profiler flame chart");
  assert.equal(canvasAccessible.props.tabIndex, 0);
  assert.equal(canvasAccessible.props["data-accessible"], "true");

  assert.ok(webglAccessible);
  assert.equal(webglAccessible.props.role, "img");
  assert.equal(webglAccessible.props["aria-label"], "Heap graph");
  assert.equal(webglAccessible.props.tabIndex, 1);
  assert.equal(webglAccessible.props["data-accessible"], "true");
});

test("phase-7 accessibility list/tree/table keep explicit role and aria metadata", () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = addWindow(state, { id: "win-1", taskId: "task-1", kind: "document" });
  state = addWidget(state, { id: "root", kind: "container", windowId: "win-1" });
  state = addWidget(state, {
    id: "list",
    kind: "list",
    parentId: "root",
    props: {
      role: "listbox",
      "aria-label": "Transcript entries",
      items: [{ id: "item-1", label: "Entry 1" }]
    }
  });
  state = addWidget(state, {
    id: "tree",
    kind: "tree",
    parentId: "root",
    props: {
      role: "tree",
      "aria-label": "Inspector tree",
      items: [{ id: "node-1", label: "Root", expanded: true, children: [{ id: "node-2", label: "Leaf" }] }]
    }
  });
  state = addWidget(state, {
    id: "table",
    kind: "table",
    parentId: "root",
    props: {
      role: "grid",
      "aria-label": "Problem list",
      columns: [{ id: "message", label: "Message" }],
      rows: [{ id: "row-1", cells: { message: "Warning" } }]
    }
  });

  const tree = renderWindow(state, "win-1");
  assert.equal(findByWidgetId(tree, "list").props.role, "listbox");
  assert.equal(findByWidgetId(tree, "list").props["aria-label"], "Transcript entries");
  assert.equal(findByWidgetId(tree, "tree").props.role, "tree");
  assert.equal(findByWidgetId(tree, "tree").props["aria-label"], "Inspector tree");
  assert.equal(findByWidgetId(tree, "table").props.role, "grid");
  assert.equal(findByWidgetId(tree, "table").props["aria-label"], "Problem list");
});

test("phase-7 accessibility reduced-motion themes emit zero-duration motion tokens", () => {
  const vars = themeToCssVars({
    mode: "dark",
    motion: {
      reduced: true,
      fast: 120,
      normal: 180,
      slow: 240,
      easing: "linear"
    }
  });

  assert.equal(vars["--ui-motion-fast"], "0ms");
  assert.equal(vars["--ui-motion-normal"], "0ms");
  assert.equal(vars["--ui-motion-slow"], "0ms");
  assert.equal(vars["--ui-motion-easing"], "linear");
  assert.equal(vars["--ui-motion-reduced"], "1");
});

