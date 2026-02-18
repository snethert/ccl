import { test } from "node:test";
import assert from "node:assert/strict";

import { createState, addTask, addWindow, addWidget } from "../src/state.mjs";
import { renderWindow } from "../src/widgets.mjs";

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

function collectNodes(node, predicate, out = []) {
  if (!node || node.kind !== "element") {
    return out;
  }
  if (predicate(node)) {
    out.push(node);
  }
  const children = node.children ?? [];
  for (const child of children) {
    collectNodes(child, predicate, out);
  }
  return out;
}

function findByClass(node, className) {
  return collectNodes(node, (entry) => {
    const value = String(entry.props?.className ?? "");
    return value.split(/\s+/).includes(className);
  })[0];
}

test("virtual list renders spacer and visible rows", () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = addWindow(state, { id: "win-1", taskId: "task-1", kind: "document" });
  state = addWidget(state, { id: "root", kind: "container", windowId: "win-1" });
  state = addWidget(state, {
    id: "list",
    kind: "list",
    parentId: "root",
    props: {
      virtual: true,
      rowHeight: 20,
      viewportHeight: 60,
      scrollTop: 40,
      overscan: 0,
      style: { background: "#fff" },
      items: Array.from({ length: 10 }, (_, index) => ({ id: `row-${index}`, label: `Row ${index}` }))
    }
  });

  const tree = renderWindow(state, "win-1");
  const list = findByDataAttr(tree, "data-widget-id", "list");

  assert.ok(list, "virtual list exists");
  assert.equal(list.tag, "div");
  assert.equal(list.props["data-virtual-start"], 2);
  assert.equal(list.props["data-virtual-end"], 5);
  assert.equal(list.props["data-virtual-total"], 10);

  const spacer = findByClass(list, "ui-virtual-spacer");
  assert.ok(spacer, "virtual list spacer exists");
  assert.equal(spacer.props.style.height, "200px");

  const rows = collectNodes(list, (entry) => entry.props?.["data-virtual-index"] !== undefined);
  const indexes = rows.map((entry) => entry.props["data-virtual-index"]);
  assert.deepEqual(indexes, [2, 3, 4]);
});

test("virtual tree flattens expanded items", () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = addWindow(state, { id: "win-1", taskId: "task-1", kind: "document" });
  state = addWidget(state, { id: "root", kind: "container", windowId: "win-1" });
  state = addWidget(state, {
    id: "tree",
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

  const treeNode = renderWindow(state, "win-1");
  const treeWidget = findByDataAttr(treeNode, "data-widget-id", "tree");

  assert.ok(treeWidget, "virtual tree exists");
  assert.equal(treeWidget.props["data-virtual-start"], 0);
  assert.equal(treeWidget.props["data-virtual-end"], 2);
  assert.equal(treeWidget.props["data-virtual-total"], 3);

  const rows = collectNodes(treeWidget, (entry) => entry.props?.["data-virtual-index"] !== undefined);
  const indexes = rows.map((entry) => entry.props["data-virtual-index"]);
  assert.deepEqual(indexes, [0, 1]);

  const childRow = collectNodes(treeWidget, (entry) => {
    const className = String(entry.props?.className ?? "");
    return (
      entry.props?.["data-item-id"] === "child" &&
      className.split(/\s+/).includes("ui-tree-row")
    );
  })[0];
  assert.ok(childRow, "child row exists");
  assert.equal(childRow.props.style.paddingLeft, "16px");
});

test("virtual table renders header and rows", () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = addWindow(state, { id: "win-1", taskId: "task-1", kind: "document" });
  state = addWidget(state, { id: "root", kind: "container", windowId: "win-1" });
  state = addWidget(state, {
    id: "table",
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
  const table = findByDataAttr(tree, "data-widget-id", "table");

  assert.ok(table, "virtual table exists");
  assert.equal(table.props["data-virtual-start"], 0);
  assert.equal(table.props["data-virtual-end"], 2);
  assert.equal(table.props["data-virtual-total"], 6);

  const header = findByClass(table, "ui-table-header");
  assert.ok(header, "table header exists");
  assert.equal(header.children.length, 2);

  const rows = collectNodes(table, (entry) => entry.props?.["data-virtual-index"] !== undefined);
  const indexes = rows.map((entry) => entry.props["data-virtual-index"]);
  assert.deepEqual(indexes, [0, 1]);
});
