import { test } from "node:test";
import assert from "node:assert/strict";

import { createRegistry } from "../src/commands.mjs";
import {
  createState,
  addTask,
  appendRecording,
  appendRecordingEntry,
  openTranscriptWindow,
  registerListSelectionCommands,
  registerRecordingCommands,
  registerTranscriptCommands
} from "../src/state.mjs";
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

function isStateLike(value) {
  return (
    value &&
    typeof value === "object" &&
    Object.prototype.hasOwnProperty.call(value, "workspace") &&
    Object.prototype.hasOwnProperty.call(value, "tasks") &&
    Object.prototype.hasOwnProperty.call(value, "windows")
  );
}

test("transcript action bar dispatches runtime and clipboard effects", () => {
  const registry = createRegistry();
  registerListSelectionCommands(registry);
  registerRecordingCommands(registry);
  registerTranscriptCommands(registry);

  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = appendRecording(state, {
    id: "rec-1",
    context: { commandId: "repl.eval", sessionId: "s-1", workspaceId: "w-1" },
    input: { kind: "form", text: "(+ 1 2)", package: "CL-USER" }
  });
  state = appendRecordingEntry(state, {
    id: "ent-value",
    recordingId: "rec-1",
    text: "(+ 1 2)",
    seq: 1,
    streamId: "stdout"
  });
  state = appendRecordingEntry(state, {
    id: "ent-command",
    recordingId: "rec-1",
    kind: "system",
    text: "repl.eval",
    seq: 2,
    streamId: "system"
  });
  state = openTranscriptWindow(state, { taskId: "task-1" });

  const transcriptWindow = Object.values(state.windows).find((win) => win.metadata?.role === "transcript");
  assert.ok(transcriptWindow, "transcript window exists");

  let currentState = state;
  let runtimeOutput = null;
  let clipboardText = null;

  const options = {
    registry,
    commandEffectHandlers: {
      runtimeDispatch: ({ output }) => {
        runtimeOutput = output;
      },
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
  };

  let tree = renderWindow(currentState, transcriptWindow.id, options);
  const commandRow = findByDataAttr(tree, "data-item-id", "transcript-ent-command");
  assert.ok(commandRow, "command transcript row exists");
  commandRow.props.onClick({ type: "click" });

  tree = renderWindow(currentState, transcriptWindow.id, options);
  const replayButton = findByDataAttr(tree, "data-action-id", "do-again");
  assert.ok(replayButton, "replay action exists");

  replayButton.props.onClick({ type: "click" });
  assert.ok(runtimeOutput, "runtime effect dispatched");
  assert.equal(runtimeOutput.kind, "recording.replay");
  assert.equal(runtimeOutput.recordingId, "rec-1");

  tree = renderWindow(currentState, transcriptWindow.id, options);
  const valueRow = findByDataAttr(tree, "data-item-id", "transcript-ent-value");
  assert.ok(valueRow, "value transcript row exists");
  valueRow.props.onClick({ type: "click" });

  tree = renderWindow(currentState, transcriptWindow.id, options);
  const describeButton = findByDataAttr(tree, "data-action-id", "describe");
  assert.ok(describeButton, "describe action exists");

  describeButton.props.onClick({ type: "click" });
  assert.ok(typeof clipboardText === "string" && clipboardText.includes("(+ 1 2)"));
});
