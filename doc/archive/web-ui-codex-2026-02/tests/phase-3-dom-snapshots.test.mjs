import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs/promises";

import {
  createState,
  addTask,
  appendRecording,
  appendRecordingEntry,
  openTranscriptWindow,
  raiseError,
  openDebuggerWindow,
  openInspectorWindow,
  openProblemsWindow
} from "../src/state.mjs";
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

async function renderWindowSnapshot(state, windowId, fixtureName) {
  const backend = createMockBackend();
  const container = backend.createElement("root");
  const root = createRoot(backend, container);
  const tree = renderWindow(state, windowId);
  root.render(tree);

  const expected = JSON.parse(
    await fs.readFile(new URL(`./fixtures/${fixtureName}`, import.meta.url), "utf8")
  );
  const actual = serialize(container);
  assert.equal(stableStringify(actual), stableStringify(expected));
}

test("phase-3 transcript window dom snapshot", async () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = appendRecording(state, {
    id: "rec-1",
    context: { commandId: "repl.eval", sessionId: "s-1", workspaceId: "w-1" },
    input: { kind: "form", text: "(+ 1 2)", package: "CL-USER" }
  });
  state = appendRecordingEntry(state, {
    id: "ent-1",
    recordingId: "rec-1",
    seq: 1,
    streamId: "stdout",
    text: "3"
  });
  state = openTranscriptWindow(state, { taskId: "task-1" });
  const window = Object.values(state.windows).find((win) => win.metadata?.role === "transcript");
  await renderWindowSnapshot(state, window.id, "transcript-dom-snapshot.json");
});

test("phase-3 debugger window dom snapshot", async () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = raiseError(state, {
    taskId: "task-1",
    message: "Boom",
    kind: "error",
    restarts: [{ id: "restart-1", title: "Retry", safety: "safe", recommended: true }]
  });
  state = openDebuggerWindow(state, { taskId: "task-1" });
  const window = Object.values(state.windows).find((win) => win.metadata?.role === "debugger");
  await renderWindowSnapshot(state, window.id, "debugger-dom-snapshot.json");
});

test("phase-3 inspector window dom snapshot", async () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = openInspectorWindow(state, { taskId: "task-1" });
  const window = Object.values(state.windows).find((win) => win.metadata?.role === "inspector");
  await renderWindowSnapshot(state, window.id, "inspector-dom-snapshot.json");
});

test("phase-3 problems window dom snapshot", async () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = raiseError(state, { taskId: "task-1", message: "Boom", kind: "error" });
  state = openProblemsWindow(state, { taskId: "task-1" });
  const window = Object.values(state.windows).find((win) => win.metadata?.role === "problems");
  await renderWindowSnapshot(state, window.id, "problems-dom-snapshot.json");
});
