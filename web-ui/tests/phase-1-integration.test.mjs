import { test } from "node:test";
import assert from "node:assert/strict";

import { createRegistry, registerCommand } from "../src/commands.mjs";
import {
  createState,
  addTask,
  addWindow,
  addWidget,
  appendRecording,
  appendRecordingEntry,
  registerRecordingCommands
} from "../src/state.mjs";
import { replayAsInput } from "../src/recordings.mjs";
import { createSnapshot, restoreStateFromSnapshot } from "../src/persistence/serialize.mjs";
import { renderWindow } from "../src/widgets.mjs";

function findByWidgetId(node, id) {
  if (!node || node.kind !== "element") return null;
  if (node.props?.["data-widget-id"] === id) return node;
  for (const child of node.children ?? []) {
    const found = findByWidgetId(child, id);
    if (found) return found;
  }
  return null;
}

function isStateLike(value) {
  return (
    value &&
    typeof value === "object" &&
    Object.prototype.hasOwnProperty.call(value, "workspace") &&
    Object.prototype.hasOwnProperty.call(value, "tasks") &&
    Object.prototype.hasOwnProperty.call(value, "windows")
  );
}

test("phase-1 integration preserves typed invocation history and recording state across snapshot restore", () => {
  const registry = createRegistry();
  registerRecordingCommands(registry);
  registerCommand(registry, {
    id: "demo.inspect",
    args: [{ name: "target", type: "selection", required: true, defaultFrom: ["selection"] }],
    exec: (ctx) => ({
      state: ctx.state,
      output: {
        kind: "form",
        text: `(inspect ${ctx.args.target.id})`
      }
    })
  });

  let state = createState({
    selection: {
      id: "sel-1",
      kind: "presentation",
      targetIds: ["pres-1"],
      anchorId: "pres-1",
      metadata: {}
    }
  });
  state = addTask(state, { id: "task-1", title: "Task" });
  state = appendRecording(state, {
    id: "rec-1",
    context: { commandId: "repl.eval", sessionId: "s-1", workspaceId: "workspace-0" },
    input: { kind: "form", text: "(+ 1 2)", package: "CL-USER" }
  });
  state = appendRecordingEntry(state, {
    id: "ent-1",
    recordingId: "rec-1",
    seq: 1,
    streamId: "stdout",
    text: "3"
  });
  state = addWindow(state, { id: "win-1", taskId: "task-1", kind: "document" });
  state = addWidget(state, { id: "root", kind: "container", windowId: "win-1" });
  state = addWidget(state, {
    id: "btn-typed",
    kind: "button",
    parentId: "root",
    props: { label: "Inspect", command: "demo.inspect" }
  });

  let clipboardText = null;
  let currentState = state;
  const tree = renderWindow(currentState, "win-1", {
    registry,
    commandEffectHandlers: {
      clipboardWrite: ({ text }) => {
        clipboardText = text;
      }
    },
    onCommandResult: ({ result }) => {
      const value = result?.result ?? null;
      if (isStateLike(value)) {
        currentState = value;
      } else if (value && isStateLike(value.state)) {
        currentState = value.state;
      }
    }
  });

  const button = findByWidgetId(tree, "btn-typed");
  assert.ok(button, "typed button exists");
  button.props.onClick({ type: "click" });

  assert.equal(clipboardText, "(inspect sel-1)");
  assert.equal(currentState.commandHistory.length, 1);
  assert.equal(currentState.commandHistory[0].commandId, "demo.inspect");
  assert.equal(currentState.commandHistory[0].defaults.target.source, "selection");

  const snapshot = createSnapshot(currentState, { now: () => 0 });
  const restored = restoreStateFromSnapshot(snapshot);
  assert.ok(restored, "restored snapshot");
  assert.equal(restored.state.commandHistory.length, 1);
  assert.equal(restored.state.commandHistory[0].commandId, "demo.inspect");
  assert.deepEqual(restored.state.recordingStore.recordingOrder, ["rec-1"]);
  assert.deepEqual(restored.state.recordingStore.entryOrder, ["ent-1"]);
});

test("phase-1 integration replay payload remains deterministic across snapshot restore", () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = appendRecording(state, {
    id: "rec-1",
    context: { commandId: "repl.eval", sessionId: "s-1", workspaceId: "workspace-0" },
    input: { kind: "form", text: "(+ 1 2)", package: "CL-USER" }
  });
  state = appendRecordingEntry(state, {
    id: "ent-1",
    recordingId: "rec-1",
    seq: 1,
    streamId: "stdout",
    text: "3"
  });
  state = appendRecording(state, {
    id: "rec-2",
    context: { commandId: "repl.eval", sessionId: "s-1", workspaceId: "workspace-0" },
    input: { kind: "form", text: "(* 2 3)", package: "CL-USER" }
  });
  state = appendRecordingEntry(state, {
    id: "ent-2",
    recordingId: "rec-2",
    seq: 2,
    streamId: "stdout",
    text: "6"
  });

  const before = replayAsInput(state.recordingStore, "rec-2");
  const snapshot = createSnapshot(state, { now: () => 0 });
  const restored = restoreStateFromSnapshot(snapshot);
  const replayId = restored.state.recordingStore.recordingOrder.at(-1);
  const after = replayAsInput(restored.state.recordingStore, replayId);

  assert.deepEqual(after, before);
});
