import { test } from "node:test";
import assert from "node:assert/strict";

import { createRegistry, registerCommand } from "../src/commands.mjs";
import {
  createState,
  addTask,
  addWindow,
  addWidget,
  registerRecordingCommands,
  registerListSelectionCommands,
  LIST_SELECTION_UPDATE_COMMAND
} from "../src/state.mjs";
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

test("widget command wiring dispatches command effect handlers", () => {
  const registry = createRegistry();
  let runtimeOutput = null;
  let clipboardText = null;

  registerCommand(registry, {
    id: "demo.replay",
    exec: (ctx) => ({
      state: ctx.state,
      output: {
        kind: "recording.replay",
        recordingId: "rec-1",
        input: { kind: "form", text: "(+ 1 2)" },
        context: { commandId: "repl.eval" }
      }
    })
  });

  registerCommand(registry, {
    id: "demo.copy",
    exec: (ctx) => ({
      state: ctx.state,
      output: {
        kind: "form",
        text: "(copy me)"
      }
    })
  });

  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = addWindow(state, { id: "win-1", taskId: "task-1", kind: "document" });
  state = addWidget(state, { id: "root", kind: "container", windowId: "win-1" });
  state = addWidget(state, {
    id: "btn-replay",
    kind: "button",
    parentId: "root",
    props: { label: "Replay", command: "demo.replay" }
  });
  state = addWidget(state, {
    id: "btn-copy",
    kind: "button",
    parentId: "root",
    props: { label: "Copy", command: "demo.copy" }
  });

  const commandEffectHandlers = {
    runtimeDispatch: ({ output }) => {
      runtimeOutput = output;
    },
    clipboardWrite: ({ text }) => {
      clipboardText = text;
    }
  };

  const tree = renderWindow(state, "win-1", { registry, commandEffectHandlers });
  const replayButton = findByWidgetId(tree, "btn-replay");
  const copyButton = findByWidgetId(tree, "btn-copy");
  assert.ok(replayButton, "replay button exists");
  assert.ok(copyButton, "copy button exists");

  replayButton.props.onClick({ type: "click" });
  copyButton.props.onClick({ type: "click" });

  assert.ok(runtimeOutput, "runtime effect dispatched");
  assert.equal(runtimeOutput.kind, "recording.replay");
  assert.equal(runtimeOutput.recordingId, "rec-1");
  assert.equal(clipboardText, "(copy me)");
});

test("widget command wiring appends structured invocation history for typed commands", () => {
  const registry = createRegistry();
  registerRecordingCommands(registry);
  let clipboardText = null;

  registerCommand(registry, {
    id: "demo.typed",
    args: [{ name: "target", type: "selection", required: true, defaultFrom: ["selection"] }],
    exec: (ctx) => ({
      state: ctx.state,
      output: {
        kind: "form",
        text: `(inspect ${ctx.args.target.id})`
      }
    })
  });

  let currentState = createState({
    selection: {
      id: "sel-1",
      kind: "presentation",
      targetIds: ["pres-1"],
      anchorId: "pres-1",
      metadata: {}
    }
  });
  currentState = addTask(currentState, { id: "task-1", title: "Task" });
  currentState = addWindow(currentState, { id: "win-1", taskId: "task-1", kind: "document" });
  currentState = addWidget(currentState, { id: "root", kind: "container", windowId: "win-1" });
  currentState = addWidget(currentState, {
    id: "btn-typed",
    kind: "button",
    parentId: "root",
    props: { label: "Typed", command: "demo.typed" }
  });

  const options = {
    registry,
    commandEffectHandlers: {
      clipboardWrite: ({ text }) => {
        clipboardText = text;
      }
    },
    onCommandResult: ({ result }) => {
      const value = result?.result ?? null;
      if (value && value.workspace && value.tasks && value.windows) {
        currentState = value;
      } else if (value && value.state && value.state.workspace && value.state.tasks && value.state.windows) {
        currentState = value.state;
      }
    }
  };

  const tree = renderWindow(currentState, "win-1", options);
  const typedButton = findByWidgetId(tree, "btn-typed");
  assert.ok(typedButton, "typed button exists");
  typedButton.props.onClick({ type: "click" });

  assert.equal(clipboardText, "(inspect sel-1)");
  assert.equal(currentState.commandHistory.length, 1);
  assert.equal(currentState.commandHistory[0].commandId, "demo.typed");
  assert.equal(currentState.commandHistory[0].defaults.target.source, "selection");
});

test("list selection supports multi-select and action bar hooks", () => {
  const registry = createRegistry();
  let itemCalls = 0;
  let inspectCtx = null;

  registerListSelectionCommands(registry);
  registerCommand(registry, {
    id: "demo.item",
    exec: () => {
      itemCalls += 1;
    }
  });
  registerCommand(registry, {
    id: "demo.inspect",
    exec: (ctx) => {
      inspectCtx = ctx;
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
      selectionCommand: LIST_SELECTION_UPDATE_COMMAND,
      selectionMode: "multi",
      selectionActionBar: true,
      selectionActionCommands: { inspect: "demo.inspect" },
      items: [
        { id: "alpha", label: "Alpha", presentationType: "value" },
        { id: "beta", label: "Beta", presentationType: "value" }
      ]
    }
  });

  let currentState = state;
  const onCommandResult = ({ result }) => {
    const next = result?.result ?? null;
    if (next && next.workspace && next.tasks && next.windows) {
      currentState = next;
    }
  };

  let tree = renderWindow(currentState, "win-1", { registry, onCommandResult });
  const alphaButton = findByDataAttr(tree, "data-item-id", "alpha");
  assert.ok(alphaButton, "first list item exists");
  alphaButton.props.onClick({ type: "click" });
  assert.equal(itemCalls, 1);
  assert.deepEqual(currentState.selection.targetIds, ["alpha"]);

  tree = renderWindow(currentState, "win-1", { registry, onCommandResult });
  const betaButton = findByDataAttr(tree, "data-item-id", "beta");
  assert.ok(betaButton, "second list item exists");
  betaButton.props.onClick({ type: "click", ctrlKey: true });
  assert.equal(itemCalls, 1, "modifier selection does not execute item command");
  assert.deepEqual(currentState.selection.targetIds, ["alpha", "beta"]);

  tree = renderWindow(currentState, "win-1", { registry, onCommandResult });
  const inspectButton = findByDataAttr(tree, "data-action-id", "inspect");
  assert.ok(inspectButton, "selection action button exists");
  inspectButton.props.onClick({ type: "click" });
  assert.ok(inspectCtx, "selection action command executed");
  assert.equal(inspectCtx.actionId, "inspect");
  assert.deepEqual(inspectCtx.selectedItemIds, ["alpha", "beta"]);
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
  assert.equal(canvas.props["aria-hidden"], "true");
  assert.equal(canvas.props.role, "presentation");
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
  assert.equal(canvas.props["aria-hidden"], "true");
  assert.equal(canvas.props.role, "presentation");
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

test("canvas view exposes accessibility props when enabled", () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = addWindow(state, { id: "win-1", taskId: "task-1", kind: "document" });
  state = addWidget(state, { id: "root", kind: "container", windowId: "win-1" });
  state = addWidget(state, {
    id: "widget-canvas",
    kind: "canvas-view",
    parentId: "root",
    props: {
      width: 100,
      height: 80,
      accessibility: {
        enabled: true,
        label: "Chart",
        role: "img",
        tabIndex: 0
      }
    }
  });

  const tree = renderWindow(state, "win-1", {});
  const canvas = findByWidgetId(tree, "widget-canvas");

  assert.ok(canvas, "canvas view exists");
  assert.equal(canvas.props["data-accessible"], "true");
  assert.equal(canvas.props["aria-label"], "Chart");
  assert.equal(canvas.props.role, "img");
  assert.equal(canvas.props.tabIndex, 0);
});

test("webgl view exposes accessibility props when enabled", () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = addWindow(state, { id: "win-1", taskId: "task-1", kind: "document" });
  state = addWidget(state, { id: "root", kind: "container", windowId: "win-1" });
  state = addWidget(state, {
    id: "widget-webgl",
    kind: "webgl-view",
    parentId: "root",
    props: {
      width: 100,
      height: 80,
      accessibility: {
        enabled: true,
        label: "Scene",
        role: "img",
        tabIndex: 0
      }
    }
  });

  const tree = renderWindow(state, "win-1", {});
  const canvas = findByWidgetId(tree, "widget-webgl");

  assert.ok(canvas, "webgl view exists");
  assert.equal(canvas.props["data-accessible"], "true");
  assert.equal(canvas.props["aria-label"], "Scene");
  assert.equal(canvas.props.role, "img");
  assert.equal(canvas.props.tabIndex, 0);
});
