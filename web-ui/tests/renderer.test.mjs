import { test } from "node:test";
import assert from "node:assert/strict";

import { createElement, createText } from "../src/vdom.mjs";
import { createRoot } from "../src/renderer.mjs";

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

function findByDataKey(node, key) {
  if (node.kind === "element" && node.props["data-key"] === key) {
    return node;
  }
  if (!node.children) return null;
  for (const child of node.children) {
    const found = findByDataKey(child, key);
    if (found) return found;
  }
  return null;
}

test("renderer mounts and patches keyed trees", () => {
  const backend = createMockBackend();
  const container = backend.createElement("root");
  const root = createRoot(backend, container);

  const tree1 = createElement(
    "div",
    { id: "root" },
    [
      createElement("span", { "data-key": "label" }, [createText("Hello")], "label"),
      createElement("button", { "data-key": "btn", disabled: true }, [createText("Click")], "btn")
    ],
    "root"
  );

  root.render(tree1);

  const labelNode = findByDataKey(container, "label");
  const buttonNode = findByDataKey(container, "btn");

  const tree2 = createElement(
    "div",
    { id: "root", className: "active" },
    [
      createElement("button", { "data-key": "btn", disabled: false }, [createText("Go")], "btn"),
      createElement("span", { "data-key": "label" }, [createText("Hello")], "label"),
      createElement("span", { "data-key": "extra" }, [createText("New")], "extra")
    ],
    "root"
  );

  root.render(tree2);

  assert.strictEqual(findByDataKey(container, "label"), labelNode);
  assert.strictEqual(findByDataKey(container, "btn"), buttonNode);

  assert.deepEqual(serialize(container), {
    kind: "element",
    tag: "root",
    props: {},
    children: [
      {
        kind: "element",
        tag: "div",
        props: { id: "root", className: "active" },
        children: [
          {
            kind: "element",
            tag: "button",
            props: { "data-key": "btn", disabled: false },
            children: [{ kind: "text", text: "Go" }]
          },
          {
            kind: "element",
            tag: "span",
            props: { "data-key": "label" },
            children: [{ kind: "text", text: "Hello" }]
          },
          {
            kind: "element",
            tag: "span",
            props: { "data-key": "extra" },
            children: [{ kind: "text", text: "New" }]
          }
        ]
      }
    ]
  });
});

test("renderer rejects duplicate keys", () => {
  const backend = createMockBackend();
  const container = backend.createElement("root");
  const root = createRoot(backend, container);
  const tree = createElement("div", null, [
    createElement("span", { "data-key": "a" }, [createText("A")], "dup"),
    createElement("span", { "data-key": "b" }, [createText("B")], "dup")
  ]);
  assert.throws(() => root.render(tree), /Duplicate key/);
});

test("renderer replaces nodes when keyed type changes", () => {
  const backend = createMockBackend();
  const container = backend.createElement("root");
  const root = createRoot(backend, container);

  const tree1 = createElement(
    "div",
    { id: "root" },
    [createElement("span", { "data-key": "swap" }, [createText("Old")], "swap")],
    "root"
  );

  root.render(tree1);

  const previous = findByDataKey(container, "swap");

  const tree2 = createElement(
    "div",
    { id: "root" },
    [createElement("button", { "data-key": "swap" }, [createText("New")], "swap")],
    "root"
  );

  root.render(tree2);

  const next = findByDataKey(container, "swap");
  assert.notStrictEqual(next, previous);
  assert.deepEqual(serialize(container), {
    kind: "element",
    tag: "root",
    props: {},
    children: [
      {
        kind: "element",
        tag: "div",
        props: { id: "root" },
        children: [
          {
            kind: "element",
            tag: "button",
            props: { "data-key": "swap" },
            children: [{ kind: "text", text: "New" }]
          }
        ]
      }
    ]
  });
});

test("renderer removes nodes missing from next tree", () => {
  const backend = createMockBackend();
  const container = backend.createElement("root");
  const root = createRoot(backend, container);

  const tree1 = createElement(
    "div",
    { id: "root" },
    [
      createElement("span", { "data-key": "keep" }, [createText("Keep")], "keep"),
      createElement("span", { "data-key": "drop" }, [createText("Drop")], "drop")
    ],
    "root"
  );

  root.render(tree1);

  const tree2 = createElement(
    "div",
    { id: "root" },
    [createElement("span", { "data-key": "keep" }, [createText("Keep")], "keep")],
    "root"
  );

  root.render(tree2);

  assert.strictEqual(findByDataKey(container, "drop"), null);
  assert.deepEqual(serialize(container), {
    kind: "element",
    tag: "root",
    props: {},
    children: [
      {
        kind: "element",
        tag: "div",
        props: { id: "root" },
        children: [
          {
            kind: "element",
            tag: "span",
            props: { "data-key": "keep" },
            children: [{ kind: "text", text: "Keep" }]
          }
        ]
      }
    ]
  });
});
