import assert from "node:assert/strict";

import {
  createRegistry,
  registerCommand,
  createState,
  addTask,
  addWindow,
  addWidget,
  renderWindow
} from "../../../web-ui/src/index.mjs";

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

const registry = createRegistry();
let lastItemId = null;

registerCommand(registry, {
  id: "demo.item",
  exec: (ctx) => {
    lastItemId = ctx.itemId ?? null;
  }
});

let state = createState();
state = addTask(state, { id: "task-1", title: "Task" });
state = addWindow(state, { id: "win-1", taskId: "task-1", kind: "document" });
state = addWidget(state, { id: "root", kind: "container", windowId: "win-1" });
state = addWidget(state, {
  id: "list",
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
const item = findByDataAttr(tree, "data-item-id", "alpha");

assert.ok(item, "list item exists");
assert.equal(item.tag, "button");
assert.equal(typeof item.props.onClick, "function");
item.props.onClick({ type: "click" });
assert.equal(lastItemId, "alpha");

console.log("PASS: web-ui list smoke test");
