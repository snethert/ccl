import assert from "node:assert/strict";

import {
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

function collectByDataAttr(node, attr, out = []) {
  if (!node || node.kind !== "element") {
    return out;
  }
  if (node.props?.[attr] !== undefined) {
    out.push(node);
  }
  const children = node.children ?? [];
  for (const child of children) {
    collectByDataAttr(child, attr, out);
  }
  return out;
}

let state = createState();
state = addTask(state, { id: "task-1", title: "Task" });
state = addWindow(state, { id: "win-1", taskId: "task-1", kind: "document" });
state = addWidget(state, { id: "root", kind: "container", windowId: "win-1" });
state = addWidget(state, {
  id: "virtual-list",
  kind: "list",
  parentId: "root",
  props: {
    virtual: true,
    rowHeight: 20,
    viewportHeight: 60,
    scrollTop: 40,
    overscan: 0,
    items: Array.from({ length: 10 }, (_, index) => ({ id: `row-${index}`, label: `Row ${index}` }))
  }
});
state = addWidget(state, {
  id: "virtual-tree",
  kind: "tree",
  parentId: "root",
  props: {
    virtual: true,
    rowHeight: 10,
    viewportHeight: 15,
    scrollTop: 0,
    overscan: 0,
    items: [
      { id: "parent", label: "Parent", expanded: true, children: [{ id: "child", label: "Child" }] },
      { id: "sibling", label: "Sibling", expanded: false, children: [{ id: "hidden", label: "Hidden" }] }
    ]
  }
});
state = addWidget(state, {
  id: "virtual-table",
  kind: "table",
  parentId: "root",
  props: {
    virtual: true,
    rowHeight: 20,
    viewportHeight: 40,
    scrollTop: 0,
    overscan: 0,
    columns: [
      { id: "col-a", label: "Column A" },
      { id: "col-b", label: "Column B" }
    ],
    rows: Array.from({ length: 6 }, (_, index) => ({
      id: `row-${index}`,
      cells: { "col-a": `A${index}`, "col-b": `B${index}` }
    }))
  }
});

const tree = renderWindow(state, "win-1");

const list = findByDataAttr(tree, "data-widget-id", "virtual-list");
assert.ok(list, "virtual list exists");
assert.equal(list.props["data-virtual-start"], 2);
assert.equal(list.props["data-virtual-end"], 5);
assert.equal(list.props["data-virtual-total"], 10);
const listRows = collectByDataAttr(list, "data-virtual-index");
assert.deepEqual(
  listRows.map((row) => row.props["data-virtual-index"]),
  [2, 3, 4]
);

const treeWidget = findByDataAttr(tree, "data-widget-id", "virtual-tree");
assert.ok(treeWidget, "virtual tree exists");
assert.equal(treeWidget.props["data-virtual-start"], 0);
assert.equal(treeWidget.props["data-virtual-end"], 2);
assert.equal(treeWidget.props["data-virtual-total"], 3);
const treeRows = collectByDataAttr(treeWidget, "data-virtual-index");
assert.deepEqual(
  treeRows.map((row) => row.props["data-virtual-index"]),
  [0, 1]
);

const table = findByDataAttr(tree, "data-widget-id", "virtual-table");
assert.ok(table, "virtual table exists");
assert.equal(table.props["data-virtual-start"], 0);
assert.equal(table.props["data-virtual-end"], 2);
assert.equal(table.props["data-virtual-total"], 6);
const tableRows = collectByDataAttr(table, "data-virtual-index");
assert.deepEqual(
  tableRows.map((row) => row.props["data-virtual-index"]),
  [0, 1]
);

console.log("PASS: web-ui virtual widgets smoke test");
