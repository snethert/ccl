import assert from "node:assert/strict";

import {
  createRegistry,
  registerCommand,
  createState,
  addTask,
  addWindow,
  addWidget,
  renderWindow,
  createWebGLBackend
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

function createMockWebGL() {
  const calls = [];
  const gl = {
    VERTEX_SHADER: 0x8b31,
    FRAGMENT_SHADER: 0x8b30,
    COMPILE_STATUS: 0x8b81,
    LINK_STATUS: 0x8b82,
    ARRAY_BUFFER: 0x8892,
    STATIC_DRAW: 0x88e4,
    TRIANGLES: 0x0004,
    COLOR_BUFFER_BIT: 0x4000,
    BLEND: 0x0be2,
    SRC_ALPHA: 0x0302,
    ONE_MINUS_SRC_ALPHA: 0x0303,
    SCISSOR_TEST: 0x0c11,
    RGBA: 0x1908,
    UNSIGNED_BYTE: 0x1401,
    createShader: () => ({}),
    shaderSource: () => {},
    compileShader: () => {},
    getShaderParameter: () => true,
    getShaderInfoLog: () => "",
    deleteShader: () => {},
    createProgram: () => ({}),
    attachShader: () => {},
    linkProgram: () => {},
    getProgramParameter: () => true,
    getProgramInfoLog: () => "",
    deleteProgram: () => {},
    getAttribLocation: () => 0,
    getUniformLocation: () => ({}),
    useProgram: () => {},
    createBuffer: () => ({}),
    bindBuffer: () => {},
    bufferData: () => {},
    enableVertexAttribArray: () => {},
    vertexAttribPointer: () => {},
    uniform2f: () => {},
    drawArrays: (...args) => calls.push(["drawArrays", ...args]),
    viewport: () => {},
    clearColor: () => {},
    clear: () => {},
    enable: () => {},
    disable: () => {},
    scissor: () => {},
    blendFunc: () => {},
    readPixels: () => {}
  };
  return { gl, calls };
}

const { gl, calls } = createMockWebGL();
const mockCanvas = {
  width: 100,
  height: 100,
  getContext: (type) => (type === "webgl" || type === "experimental-webgl" ? gl : null)
};

const backend = createWebGLBackend({ canvas: mockCanvas });
backend.render(
  [
    { id: "rect", kind: "rect", bounds: { x: 0, y: 0, width: 10, height: 10 }, props: { fill: "#f00" } },
    { id: "rect2", kind: "rect", bounds: { x: 20, y: 20, width: 5, height: 5 }, props: { fill: "#0f0" } }
  ],
  { dirtyRects: [{ x: 0, y: 0, width: 12, height: 12 }] }
);

assert.ok(calls.find((entry) => entry[0] === "drawArrays"), "webgl backend drawArrays called");

const registry = createRegistry();
let hitCtx = null;

registerCommand(registry, {
  id: "demo.webgl",
  exec: (ctx) => {
    hitCtx = ctx;
  }
});

let state = createState();
state = addTask(state, { id: "task-1", title: "Task" });
state = addWindow(state, { id: "win-1", taskId: "task-1", kind: "document" });
state = addWidget(state, { id: "root", kind: "container", windowId: "win-1" });
state = addWidget(state, {
  id: "webgl",
  kind: "webgl-view",
  parentId: "root",
  props: {
    command: "demo.webgl",
    width: 80,
    height: 60,
    scene: [
      {
        id: "rect-1",
        kind: "rect",
        bounds: { x: 0, y: 0, width: 20, height: 20 },
        props: { fill: "#00f", commandId: "demo.webgl" }
      }
    ]
  }
});

const tree = renderWindow(state, "win-1", { registry });
const widget = findByWidgetId(tree, "webgl");

assert.ok(widget, "webgl widget exists");
assert.equal(widget.tag, "canvas");
assert.equal(widget.props["data-command-id"], "demo.webgl");
assert.equal(typeof widget.props.__webglRender, "function");
assert.equal(typeof widget.props.onClick, "function");

const target = {
  __webglBackend: {},
  getBoundingClientRect: () => ({ left: 0, top: 0 })
};
widget.props.onClick({ currentTarget: target, clientX: 5, clientY: 5, type: "click" });

assert.ok(hitCtx, "webgl command invoked");
assert.equal(hitCtx.webglId, "webgl");
assert.equal(hitCtx.hitId, "rect-1");
assert.equal(hitCtx.hitKind, "rect");

console.log("PASS: web-ui webgl smoke test");
