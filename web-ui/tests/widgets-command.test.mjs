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
