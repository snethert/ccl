import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createState,
  addTask,
  addPresentation,
  appendRecording,
  appendRecordingEntry,
  openTranscriptWindow,
  openInspectorWindow,
  refreshInspectorWindow,
  registerListSelectionCommands,
  registerRecordingCommands,
  registerTranscriptCommands,
  registerInspectorCommands
} from "../src/state.mjs";
import { createRegistry } from "../src/commands.mjs";
import { renderWindow } from "../src/widgets.mjs";
import { createSnapshot, restoreStateFromSnapshot } from "../src/persistence/serialize.mjs";

function findByDataAttr(node, attr, value) {
  if (!node || node.kind !== "element") return null;
  if (node.props?.[attr] === value) return node;
  for (const child of node.children ?? []) {
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

test("phase-2 transcript->inspector watch flow updates and survives restore", () => {
  const registry = createRegistry();
  registerListSelectionCommands(registry);
  registerRecordingCommands(registry);
  registerTranscriptCommands(registry);
  registerInspectorCommands(registry);

  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = addPresentation(state, {
    id: "pres-1",
    type: "value",
    metadata: { summary: "initial" }
  });
  state = appendRecording(state, {
    id: "rec-1",
    context: { commandId: "repl.eval", sessionId: "s-1", workspaceId: "w-1" },
    input: { kind: "form", text: "(compute)", package: "CL-USER" }
  });
  state = appendRecordingEntry(state, {
    id: "ent-1",
    recordingId: "rec-1",
    seq: 1,
    streamId: "stdout",
    text: "3",
    presentationId: "pres-1"
  });
  state = openTranscriptWindow(state, { taskId: "task-1" });
  state = openInspectorWindow(state, { taskId: "task-1" });

  const transcriptWindow = Object.values(state.windows).find((win) => win.metadata?.role === "transcript");
  const inspectorWindow = Object.values(state.windows).find((win) => win.metadata?.role === "inspector");
  assert.ok(transcriptWindow, "transcript window exists");
  assert.ok(inspectorWindow, "inspector window exists");

  let currentState = state;
  const options = {
    registry,
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
  const entryRow = findByDataAttr(tree, "data-item-id", "transcript-ent-1");
  assert.ok(entryRow, "entry row exists");
  entryRow.props.onClick({ type: "click", ctrlKey: true });

  tree = renderWindow(currentState, transcriptWindow.id, options);
  const pinWatchButton = findByDataAttr(tree, "data-action-id", "pin-watch");
  assert.ok(pinWatchButton, "pin watch action exists");
  pinWatchButton.props.onClick({ type: "click" });
  assert.equal(currentState.watches.length, 1);
  assert.equal(currentState.watches[0].presentationId, "pres-1");

  currentState = appendRecordingEntry(currentState, {
    id: "ent-2",
    recordingId: "rec-1",
    seq: 2,
    streamId: "stdout",
    text: "42",
    presentationId: "pres-1"
  });

  currentState = refreshInspectorWindow(currentState, inspectorWindow.id);
  const watchesListId = inspectorWindow.metadata.widgets.sections.watches.listId;
  const watchItems = currentState.widgets[watchesListId].props.items;
  assert.ok(watchItems.some((item) => item.label.includes("42")));

  const snapshot = createSnapshot(currentState, { now: () => 0 });
  const restored = restoreStateFromSnapshot(snapshot);
  assert.equal(restored.state.watches.length, 1);
  assert.equal(restored.state.watches[0].valueSummary, "42");
});
