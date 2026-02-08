import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createState,
  addTask,
  addPresentation,
  appendRecording,
  appendRecordingEntry,
  LIST_SELECTION_UPDATE_COMMAND,
  RECORDING_COPY_WITH_CONTEXT_COMMAND,
  RECORDING_REPLAY_AS_INPUT_COMMAND,
  RECORDING_RERUN_COMMAND,
  TRANSCRIPT_ITEM_OPEN_COMMAND,
  openTranscriptWindow,
  refreshTranscriptWindow
} from "../src/state.mjs";

test("transcript window lists recording entries", () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = appendRecording(state, { id: "rec-1" });
  state = appendRecordingEntry(state, {
    id: "ent-1",
    recordingId: "rec-1",
    seq: 1,
    streamId: "stdout",
    text: "Hello",
    presentationId: "pres-1"
  });

  state = openTranscriptWindow(state, { taskId: "task-1" });
  const window = Object.values(state.windows).find((win) => win.metadata?.role === "transcript");
  assert.ok(window, "transcript window exists");
  const listId = window.metadata.widgets.listId;
  const items = state.widgets[listId].props.items;
  assert.ok(items[0].label.includes("Hello"));
  assert.equal(items[0].anchorId, null);
  assert.equal(items[0].presentationType, "value");
  assert.equal(state.widgets[listId].props.itemCommand, TRANSCRIPT_ITEM_OPEN_COMMAND);
  assert.equal(state.widgets[listId].props.selectionCommand, LIST_SELECTION_UPDATE_COMMAND);
  assert.equal(state.widgets[listId].props.selectionActionBar, true);
  assert.equal(
    state.widgets[listId].props.selectionActionCommands.describe,
    RECORDING_COPY_WITH_CONTEXT_COMMAND
  );
  assert.equal(
    state.widgets[listId].props.selectionActionCommands["do-again"],
    RECORDING_REPLAY_AS_INPUT_COMMAND
  );
  assert.equal(
    state.widgets[listId].props.selectionActionCommands["do-again-with-args"],
    RECORDING_RERUN_COMMAND
  );
});

test("refreshTranscriptWindow updates entries", () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = openTranscriptWindow(state, { taskId: "task-1" });
  const window = Object.values(state.windows).find((win) => win.metadata?.role === "transcript");

  state = appendRecording(state, { id: "rec-1" });
  state = appendRecordingEntry(state, {
    id: "ent-1",
    recordingId: "rec-1",
    seq: 1,
    streamId: "stdout",
    text: "Later"
  });
  state = refreshTranscriptWindow(state, window.id);

  const items = state.widgets[window.metadata.widgets.listId].props.items;
  assert.ok(items[0].label.includes("Later"));
});

test("refreshTranscriptWindow revalidates presentations when resolver is provided", () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = addPresentation(state, {
    id: "pres-1",
    type: "value",
    metadata: { summary: "42" }
  });
  state = appendRecording(state, { id: "rec-1" });
  state = appendRecordingEntry(state, {
    id: "ent-1",
    recordingId: "rec-1",
    seq: 1,
    streamId: "stdout",
    text: "42",
    presentationId: "pres-1"
  });
  state = openTranscriptWindow(state, { taskId: "task-1" });
  const window = Object.values(state.windows).find((win) => win.metadata?.role === "transcript");

  state = refreshTranscriptWindow(state, window.id, {
    presentationResolver: () => ({ ok: false, reason: "unbound" })
  });

  assert.equal(state.presentations["pres-1"].metadata.stale, true);
  assert.equal(state.presentations["pres-1"].metadata.staleReason, "unbound");
});

test("transcript derives presentation types from entry kinds when presentation id is absent", () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = appendRecording(state, { id: "rec-1" });
  state = appendRecordingEntry(state, {
    id: "ent-system",
    recordingId: "rec-1",
    kind: "system",
    streamId: "system",
    text: "compile-file"
  });
  state = appendRecordingEntry(state, {
    id: "ent-error",
    recordingId: "rec-1",
    kind: "error",
    streamId: "stderr",
    text: "Division by zero"
  });
  state = openTranscriptWindow(state, { taskId: "task-1" });

  const window = Object.values(state.windows).find((win) => win.metadata?.role === "transcript");
  const items = state.widgets[window.metadata.widgets.listId].props.items;
  const byId = Object.fromEntries(items.map((item) => [item.entryId, item]));
  assert.equal(byId["ent-system"].presentationType, "command");
  assert.equal(byId["ent-error"].presentationType, "condition-section");
  assert.equal(byId["ent-system"].presentationId, null);
  assert.equal(byId["ent-error"].presentationId, null);
});
