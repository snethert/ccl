import assert from "node:assert/strict";

import {
  createRegistry,
  registerCommand,
  createState,
  addTask,
  addWindow,
  addWidget,
  renderWindow,
  createCanvasBackend
} from "../../../web-ui/src/index.mjs";

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

const registry = createRegistry();
let hitCtx = null;

registerCommand(registry, {
  id: "demo.canvas",
  exec: (ctx) => {
    hitCtx = ctx;
  }
});

let state = createState();
state = addTask(state, { id: "task-1", title: "Task" });
state = addWindow(state, { id: "win-1", taskId: "task-1", kind: "document" });
state = addWidget(state, { id: "root", kind: "container", windowId: "win-1" });
state = addWidget(state, {
  id: "canvas",
  kind: "canvas-view",
  parentId: "root",
  props: {
    command: "demo.canvas",
    width: 80,
    height: 60,
    scene: [
      {
        id: "rect-1",
        kind: "rect",
        bounds: { x: 0, y: 0, width: 20, height: 20 },
        props: { fill: "#00f", commandId: "demo.canvas" }
      }
    ]
  }
});

const tree = renderWindow(state, "win-1", { registry });
const canvas = findByWidgetId(tree, "canvas");

assert.ok(canvas, "canvas widget exists");
assert.equal(canvas.tag, "canvas");
assert.equal(canvas.props.width, 80);
assert.equal(canvas.props.height, 60);
assert.equal(canvas.props["data-command-id"], "demo.canvas");
assert.equal(typeof canvas.props.__canvasRender, "function");
assert.equal(typeof canvas.props.onClick, "function");

const target = {
  __canvasBackend: {},
  getBoundingClientRect: () => ({ left: 0, top: 0 })
};
canvas.props.onClick({ currentTarget: target, clientX: 5, clientY: 5, type: "click" });

assert.ok(hitCtx, "canvas command invoked");
assert.equal(hitCtx.canvasId, "canvas");
assert.equal(hitCtx.hitId, "rect-1");
assert.equal(hitCtx.hitKind, "rect");

const calls = [];
const ctx = {
  canvas: { width: 100, height: 100 },
  clearRect: (...args) => calls.push(["clearRect", ...args]),
  fillRect: (...args) => calls.push(["fillRect", ...args]),
  strokeRect: (...args) => calls.push(["strokeRect", ...args]),
  fillText: (...args) => calls.push(["fillText", ...args]),
  save: () => calls.push(["save"]),
  restore: () => calls.push(["restore"]),
  beginPath: () => calls.push(["beginPath"]),
  rect: (...args) => calls.push(["rect", ...args]),
  clip: () => calls.push(["clip"]),
  measureText: () => ({ width: 0, actualBoundingBoxAscent: 0, actualBoundingBoxDescent: 0 })
};
const mockCanvas = {
  width: 100,
  height: 100,
  getContext: () => ctx
};
ctx.canvas = mockCanvas;

const backend = createCanvasBackend({ canvas: mockCanvas });
backend.render(
  [
    { id: "rect", kind: "rect", bounds: { x: 0, y: 0, width: 10, height: 10 }, props: { fill: "#f00" } },
    { id: "outside", kind: "rect", bounds: { x: 50, y: 50, width: 10, height: 10 }, props: { fill: "#00f" } }
  ],
  { dirtyRects: [{ x: 2, y: 2, width: 4, height: 4 }] }
);

const dirtyClear = calls.find((entry) => entry[0] === "clearRect");
assert.ok(dirtyClear, "dirty rect clear was issued");
assert.deepEqual(dirtyClear.slice(1), [2, 2, 4, 4]);
const fillCalls = calls.filter((entry) => entry[0] === "fillRect");
assert.equal(fillCalls.length, 1);
assert.deepEqual(fillCalls[0].slice(1), [0, 0, 10, 10]);

console.log("PASS: web-ui canvas smoke test");
