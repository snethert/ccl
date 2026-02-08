import { test } from "node:test";
import assert from "node:assert/strict";

import { createRegistry } from "../src/commands.mjs";
import {
  createState,
  addTask,
  raiseError,
  appendRecording,
  appendRecordingEntry,
  openTranscriptWindow,
  refreshTranscriptWindow,
  openProblemsWindow,
  registerListSelectionCommands,
  registerRecordingCommands,
  registerTranscriptCommands,
  registerProblemsCommands,
  registerDebuggerCommands
} from "../src/state.mjs";
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

test("phase-2 integration: problems -> debugger -> restart -> transcript update", () => {
  const registry = createRegistry();
  registerListSelectionCommands(registry);
  registerRecordingCommands(registry);
  registerTranscriptCommands(registry);
  registerProblemsCommands(registry);
  registerDebuggerCommands(registry);

  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = appendRecording(state, {
    id: "rec-1",
    context: { commandId: "repl.eval", sessionId: "s-1", workspaceId: "w-1" },
    input: { kind: "form", text: "(explode)", package: "CL-USER" }
  });
  state = appendRecordingEntry(state, {
    id: "ent-1",
    recordingId: "rec-1",
    seq: 1,
    streamId: "stdout",
    text: "error"
  });
  state = raiseError(state, {
    taskId: "task-1",
    message: "Boom",
    kind: "error",
    restarts: [{ id: "rst-1", title: "Retry", safety: "safe", argSchema: [] }]
  });
  state = openTranscriptWindow(state, { taskId: "task-1" });
  state = openProblemsWindow(state, { taskId: "task-1" });

  const transcriptWindow = Object.values(state.windows).find((win) => win.metadata?.role === "transcript");
  const problemsWindow = Object.values(state.windows).find((win) => win.metadata?.role === "problems");
  assert.ok(transcriptWindow, "transcript window exists");
  assert.ok(problemsWindow, "problems window exists");

  let pendingRestart = null;
  let currentState = state;
  let restartSeq = 2;
  const options = {
    registry,
    commandEffectHandlers: {
      runtimeDispatch: ({ output }) => {
        if (output?.kind === "restart.invoke") {
          pendingRestart = output;
        }
      }
    },
    onCommandResult: ({ result }) => {
      const value = result?.result ?? null;
      if (isStateLike(value)) {
        currentState = value;
      } else if (value && isStateLike(value.state)) {
        currentState = value.state;
      }
      if (pendingRestart) {
        const entryId = `ent-restart-${restartSeq}`;
        currentState = appendRecordingEntry(currentState, {
          id: entryId,
          recordingId: "rec-1",
          seq: restartSeq,
          streamId: "stdout",
          text: `Restart ${pendingRestart.restartId} invoked`
        });
        restartSeq += 1;
        currentState = refreshTranscriptWindow(currentState, transcriptWindow.id);
        pendingRestart = null;
      }
    }
  };

  let tree = renderWindow(currentState, problemsWindow.id, options);
  const problemRow = findByDataAttr(
    tree,
    "data-item-id",
    currentState.widgets[problemsWindow.metadata.widgets.listId].props.items[0].id
  );
  assert.ok(problemRow, "problem row exists");
  problemRow.props.onClick({ type: "click" });

  const debuggerWindow = Object.values(currentState.windows).find((win) => win.metadata?.role === "debugger");
  assert.ok(debuggerWindow, "debugger window opened");
  tree = renderWindow(currentState, debuggerWindow.id, options);
  const restartRow = findByDataAttr(tree, "data-item-id", "rst-1");
  assert.ok(restartRow, "restart row exists");
  restartRow.props.onClick({ type: "click" });

  const transcriptListId = transcriptWindow.metadata.widgets.listId;
  const transcriptItems = currentState.widgets[transcriptListId].props.items;
  assert.ok(transcriptItems.some((item) => item.entryId === "ent-restart-2"));

  const snapshot = createSnapshot(currentState, { now: () => 0 });
  const restored = restoreStateFromSnapshot(snapshot);
  assert.ok(restored.state.recordingStore.entries["ent-restart-2"]);
});
