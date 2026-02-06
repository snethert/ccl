import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs/promises";

import { createState, addTask, addWindow, addWidget } from "../src/state.mjs";
import { renderWindow } from "../src/widgets.mjs";
import { createRoot } from "../src/renderer.mjs";
import { stableStringify } from "./snapshot.mjs";

function createMockBackend() {
  return {
    createElement(tag) {
      return { kind: "element", tag, props: {}, children: [] };
    },
    createText(text) {
      return { kind: "text", text };
    },
    appendChild(parent, child) {
      parent.children.push(child);
    },
    insertBefore(parent, child, anchor) {
      const current = parent.children.indexOf(child);
      if (current !== -1) {
        parent.children.splice(current, 1);
      }
      if (!anchor) {
        parent.children.push(child);
        return;
      }
      const anchorIndex = parent.children.indexOf(anchor);
      if (anchorIndex === -1) {
        parent.children.push(child);
        return;
      }
      parent.children.splice(anchorIndex, 0, child);
    },
    removeChild(parent, child) {
      const index = parent.children.indexOf(child);
      if (index !== -1) {
        parent.children.splice(index, 1);
      }
    },
    replaceChild(parent, next, prev) {
      const index = parent.children.indexOf(prev);
      if (index !== -1) {
        parent.children[index] = next;
      }
    },
    setText(node, text) {
      node.text = text;
    },
    setProp(node, name, value) {
      node.props[name] = value;
    },
    removeProp(node, name) {
      delete node.props[name];
    }
  };
}

function serialize(node) {
  if (node.kind === "text") {
    return { kind: "text", text: node.text };
  }
  return {
    kind: "element",
    tag: node.tag,
    props: { ...node.props },
    children: node.children.map(serialize)
  };
}

test("widget adapter renders a window tree via the renderer", async () => {
  const backend = createMockBackend();
  const container = backend.createElement("root");
  const root = createRoot(backend, container);

  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = addWindow(state, { id: "win-1", taskId: "task-1", kind: "document" });
  state = addWidget(state, {
    id: "widget-root",
    kind: "container",
    windowId: "win-1",
    props: { id: "widget-root", className: "root" }
  });
  state = addWidget(state, {
    id: "widget-label",
    kind: "label",
    parentId: "widget-root",
    props: { text: "Hello" }
  });
  state = addWidget(state, {
    id: "widget-btn",
    kind: "button",
    parentId: "widget-root",
    props: { label: "Run", disabled: true }
  });
  state = addWidget(state, {
    id: "widget-stack",
    kind: "container",
    parentId: "widget-root",
    props: { className: "stack" }
  });
  state = addWidget(state, {
    id: "widget-info",
    kind: "label",
    parentId: "widget-stack",
    props: { text: "Nested" }
  });
  state = addWidget(state, {
    id: "widget-list",
    kind: "list",
    parentId: "widget-root",
    props: {
      items: [
        { id: "alpha", label: "Alpha" },
        { id: "beta", label: "Beta", selected: true }
      ]
    }
  });

  state = addWidget(state, {
    id: "widget-canvas",
    kind: "canvas-view",
    parentId: "widget-root",
    props: {
      width: 80,
      height: 60,
      scene: [
        {
          id: "rect-1",
          kind: "rect",
          bounds: { x: 5, y: 5, width: 20, height: 10 },
          props: { fill: "#ff0000" }
        }
      ]
    }
  });

  const tree = renderWindow(state, "win-1");
  root.render(tree);

  const expected = JSON.parse(
    await fs.readFile(new URL("./fixtures/widget-snapshot.json", import.meta.url), "utf8")
  );

  assert.equal(stableStringify(serialize(container)), stableStringify(expected));
});
