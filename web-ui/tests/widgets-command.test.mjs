import { test } from "node:test";
import assert from "node:assert/strict";

import { createRegistry, registerCommand } from "../src/commands.mjs";
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

function findByDataAttr(node, attr, value) {
  if (!node || node.kind !== "element") {
    return null;
  }
  if (node.props?.[attr] === value) {
    return node;
  }
  const children = node.children ?? [];
  for (const child of children) {
    const found = findByDataAttr(child, attr, value);
    if (found) return found;
  }
  return null;
}

test("button command wiring dispatches through registry", () => {
  const registry = createRegistry();
  let calls = 0;

  registerCommand(registry, {
    id: "demo.run",
    exec: () => {
      calls += 1;
    }
  });
  registerCommand(registry, {
    id: "demo.blocked",
    enabled: () => [false, "Blocked"],
    exec: () => {
      calls += 10;
    }
  });

  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = addWindow(state, { id: "win-1", taskId: "task-1", kind: "document" });
  state = addWidget(state, { id: "root", kind: "container", windowId: "win-1" });
  state = addWidget(state, {
    id: "widget-run",
    kind: "button",
    parentId: "root",
    props: { label: "Run", command: "demo.run" }
  });
  state = addWidget(state, {
    id: "widget-blocked",
    kind: "button",
    parentId: "root",
    props: { label: "Blocked", command: "demo.blocked" }
  });

  const tree = renderWindow(state, "win-1", { registry });
  const runButton = findByWidgetId(tree, "widget-run");
  const blockedButton = findByWidgetId(tree, "widget-blocked");

  assert.ok(runButton, "run button exists");
  assert.ok(blockedButton, "blocked button exists");

  assert.equal(runButton.props.disabled, undefined);
  assert.equal(runButton.props["data-command-id"], "demo.run");
  assert.equal(typeof runButton.props.onClick, "function");

  runButton.props.onClick({ type: "click" });
  assert.equal(calls, 1);

  assert.equal(blockedButton.props.disabled, true);
  assert.equal(blockedButton.props["data-command-id"], "demo.blocked");
  assert.equal(blockedButton.props["data-disabled-reason"], "Blocked");
  assert.equal(typeof blockedButton.props.onClick, "function");

  blockedButton.props.onClick({ type: "click" });
  assert.equal(calls, 1);
});

test("text input command wiring provides input value", () => {
  const registry = createRegistry();
  let lastValue = null;

  registerCommand(registry, {
    id: "demo.input",
    exec: (ctx) => {
      lastValue = ctx.inputValue ?? null;
    }
  });

  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = addWindow(state, { id: "win-1", taskId: "task-1", kind: "document" });
  state = addWidget(state, { id: "root", kind: "container", windowId: "win-1" });
  state = addWidget(state, {
    id: "widget-input",
    kind: "text-input",
    parentId: "root",
    props: { placeholder: "Type", command: "demo.input" }
  });

  const tree = renderWindow(state, "win-1", { registry });
  const input = findByWidgetId(tree, "widget-input");

  assert.ok(input, "input exists");
  assert.equal(input.tag, "input");
  assert.equal(input.props.type, "text");
  assert.equal(input.props["data-command-id"], "demo.input");
  assert.equal(typeof input.props.onInput, "function");

  input.props.onInput({ target: { value: "hello" } });
  assert.equal(lastValue, "hello");
});

test("list item command wiring provides item context", () => {
  const registry = createRegistry();
  let lastCtx = null;

  registerCommand(registry, {
    id: "demo.item",
    exec: (ctx) => {
      lastCtx = ctx;
    }
  });

  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = addWindow(state, { id: "win-1", taskId: "task-1", kind: "document" });
  state = addWidget(state, { id: "root", kind: "container", windowId: "win-1" });
  state = addWidget(state, {
    id: "widget-list",
    kind: "list",
    parentId: "root",
    props: {
      itemCommand: "demo.item",
      items: [
        { id: "alpha", label: "Alpha" },
        { id: "beta", label: "Beta" }
      ]
    }
  });

  const tree = renderWindow(state, "win-1", { registry });
  const itemButton = findByDataAttr(tree, "data-item-id", "alpha");

  assert.ok(itemButton, "list item exists");
  assert.equal(itemButton.tag, "button");
  assert.equal(itemButton.props["data-command-id"], "demo.item");
  assert.equal(typeof itemButton.props.onClick, "function");

  itemButton.props.onClick({ type: "click" });
  assert.ok(lastCtx, "command context set");
  assert.equal(lastCtx.itemId, "alpha");
  assert.equal(lastCtx.itemIndex, 0);
  assert.equal(lastCtx.listId, "widget-list");
});

test("canvas view command wiring uses hit testing", () => {
  const registry = createRegistry();
  let lastCtx = null;

  registerCommand(registry, {
    id: "demo.canvas",
    exec: (ctx) => {
      lastCtx = ctx;
    }
  });

  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = addWindow(state, { id: "win-1", taskId: "task-1", kind: "document" });
  state = addWidget(state, { id: "root", kind: "container", windowId: "win-1" });
  state = addWidget(state, {
    id: "widget-canvas",
    kind: "canvas-view",
    parentId: "root",
    props: {
      command: "demo.canvas",
      width: 100,
      height: 80,
      scene: [
        {
          id: "rect-1",
          kind: "rect",
          bounds: { x: 0, y: 0, width: 20, height: 20 },
          props: { commandId: "demo.canvas", fill: "#00f" }
        }
      ]
    }
  });

  const tree = renderWindow(state, "win-1", { registry });
  const canvas = findByWidgetId(tree, "widget-canvas");

  assert.ok(canvas, "canvas view exists");
  assert.equal(canvas.tag, "canvas");
  assert.equal(canvas.props["data-command-id"], "demo.canvas");
  assert.equal(typeof canvas.props.onClick, "function");

  const target = {
    __canvasBackend: {},
    getBoundingClientRect: () => ({ left: 0, top: 0 })
  };
  canvas.props.onClick({ currentTarget: target, clientX: 5, clientY: 5, type: "click" });

  assert.ok(lastCtx, "canvas command executed");
  assert.equal(lastCtx.canvasId, "widget-canvas");
  assert.equal(lastCtx.hitId, "rect-1");
  assert.equal(lastCtx.hitKind, "rect");
});

test("webgl view command wiring uses hit testing", () => {
  const registry = createRegistry();
  let lastCtx = null;

  registerCommand(registry, {
    id: "demo.webgl",
    exec: (ctx) => {
      lastCtx = ctx;
    }
  });

  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = addWindow(state, { id: "win-1", taskId: "task-1", kind: "document" });
  state = addWidget(state, { id: "root", kind: "container", windowId: "win-1" });
  state = addWidget(state, {
    id: "widget-webgl",
    kind: "webgl-view",
    parentId: "root",
    props: {
      command: "demo.webgl",
      width: 100,
      height: 80,
      scene: [
        {
          id: "rect-1",
          kind: "rect",
          bounds: { x: 0, y: 0, width: 20, height: 20 },
          props: { commandId: "demo.webgl", fill: "#00f" }
        }
      ]
    }
  });

  const tree = renderWindow(state, "win-1", { registry });
  const canvas = findByWidgetId(tree, "widget-webgl");

  assert.ok(canvas, "webgl view exists");
  assert.equal(canvas.tag, "canvas");
  assert.equal(canvas.props["data-command-id"], "demo.webgl");
  assert.equal(typeof canvas.props.onClick, "function");

  const target = {
    __webglBackend: {},
    getBoundingClientRect: () => ({ left: 0, top: 0 })
  };
  canvas.props.onClick({ currentTarget: target, clientX: 5, clientY: 5, type: "click" });

  assert.ok(lastCtx, "webgl command executed");
  assert.equal(lastCtx.webglId, "widget-webgl");
  assert.equal(lastCtx.hitId, "rect-1");
  assert.equal(lastCtx.hitKind, "rect");
});
