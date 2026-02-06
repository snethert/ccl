import { test } from "node:test";
import assert from "node:assert/strict";

import { createState, addTask, addWindow, addWidget } from "../src/state.mjs";
import { renderWindow } from "../src/widgets.mjs";

function findByWidgetId(node, id) {
  if (!node || node.kind !== "element") {
    return null;
  }
  if (node.props?.["data-widget-id"] === id) {
    return node;
  }
  const children = node.children ?? [];
  for (const child of children) {
    const found = findByWidgetId(child, id);
    if (found) return found;
  }
  return null;
}

test("canvas view forwards dirty rect hints", () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = addWindow(state, { id: "win-1", taskId: "task-1", kind: "document" });
  state = addWidget(state, { id: "root", kind: "container", windowId: "win-1" });
  state = addWidget(state, {
    id: "canvas",
    kind: "canvas-view",
    parentId: "root",
    props: {
      width: 40,
      height: 30,
      dirtyRects: [{ x: 1, y: 2, width: 3, height: 4 }],
      scene: [
        { id: "rect", kind: "rect", bounds: { x: 0, y: 0, width: 10, height: 10 }, props: { fill: "#f00" } }
      ]
    }
  });

  const tree = renderWindow(state, "win-1");
  const canvas = findByWidgetId(tree, "canvas");
  assert.ok(canvas, "canvas widget exists");

  let received = null;
  const node = {
    __canvasBackend: {
      render: (scene, opts) => {
        received = opts;
      }
    }
  };

  canvas.props.__canvasRender(node);
  assert.deepEqual(received, { dirtyRects: [{ x: 1, y: 2, width: 3, height: 4 }] });
});

test("webgl view forwards dirty rect hints", () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = addWindow(state, { id: "win-1", taskId: "task-1", kind: "document" });
  state = addWidget(state, { id: "root", kind: "container", windowId: "win-1" });
  state = addWidget(state, {
    id: "webgl",
    kind: "webgl-view",
    parentId: "root",
    props: {
      width: 40,
      height: 30,
      dirtyIds: ["rect"],
      scene: [
        { id: "rect", kind: "rect", bounds: { x: 0, y: 0, width: 10, height: 10 }, props: { fill: "#0f0" } }
      ]
    }
  });

  const tree = renderWindow(state, "win-1");
  const webgl = findByWidgetId(tree, "webgl");
  assert.ok(webgl, "webgl widget exists");

  let received = null;
  const node = {
    __webglBackend: {
      render: (scene, opts) => {
        received = opts;
      }
    }
  };

  webgl.props.__webglRender(node);
  assert.deepEqual(received, { dirtyIds: ["rect"] });
});
