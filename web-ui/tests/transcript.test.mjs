import { test } from "node:test";
import assert from "node:assert/strict";
import { createRegistry, executeCommand } from "../src/commands.mjs";

import {
  createState,
  addTask,
  addPresentation,
  appendRecording,
  appendRecordingEntry,
  LIST_SELECTION_UPDATE_COMMAND,
  INSPECTOR_WATCH_PIN_COMMAND,
  RECORDING_TOGGLE_COMMAND,
  RECORDING_COPY_WITH_CONTEXT_COMMAND,
  RECORDING_REPLAY_AS_INPUT_COMMAND,
  RECORDING_RERUN_COMMAND,
  TRANSCRIPT_ITEM_OPEN_COMMAND,
  openTranscriptWindow,
  refreshTranscriptWindow,
  registerRecordingCommands
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
  assert.equal(items[0].kind, "recording");
  assert.equal(items[0].recordingId, "rec-1");
  assert.equal(items[0].selectable, false);
  assert.equal(items[0].command, RECORDING_TOGGLE_COMMAND);
  assert.ok(items[1].label.includes("Hello"));
  assert.equal(items[1].anchorId, null);
  assert.equal(items[1].presentationType, "value");
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
  assert.equal(
    state.widgets[listId].props.selectionActionCommands["toggle-fold"],
    RECORDING_TOGGLE_COMMAND
  );
  assert.ok(
    state.widgets[listId].props.selectionActions.some((action) => action.id === "toggle-fold")
  );
  assert.equal(
    state.widgets[listId].props.selectionActionCommands["pin-watch"],
    INSPECTOR_WATCH_PIN_COMMAND
  );
  assert.ok(
    state.widgets[listId].props.selectionActions.some((action) => action.id === "pin-watch")
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
  assert.ok(items[1].label.includes("Later"));
});

test("recording header command toggles collapsed run visibility", () => {
  const registry = createRegistry();
  registerRecordingCommands(registry);

  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = appendRecording(state, { id: "rec-1", context: { commandId: "repl.eval" }, input: { kind: "form", text: "(+ 1 2)" } });
  state = appendRecordingEntry(state, {
    id: "ent-1",
    recordingId: "rec-1",
    seq: 1,
    streamId: "stdout",
    text: "3"
  });
  state = openTranscriptWindow(state, { taskId: "task-1" });
  const window = Object.values(state.windows).find((win) => win.metadata?.role === "transcript");
  const listId = window.metadata.widgets.listId;

  const header = state.widgets[listId].props.items[0];
  assert.equal(header.command, RECORDING_TOGGLE_COMMAND);
  const toggled = executeCommand(registry, RECORDING_TOGGLE_COMMAND, { state, item: header });
  assert.equal(toggled.ok, true);
  state = toggled.result;
  assert.equal(state.recordingStore.recordings["rec-1"].metadata.collapsed, true);

  state = refreshTranscriptWindow(state, window.id);
  const items = state.widgets[listId].props.items;
  assert.equal(items.length, 1);
  assert.equal(items[0].kind, "recording");
  assert.ok(items[0].label.startsWith("[+]"));
});

test("recording toggle command folds and unfolds transcript entries", () => {
  const registry = createRegistry();
  registerRecordingCommands(registry);

  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = appendRecording(state, { id: "rec-1", context: { commandId: "repl.eval" }, input: { kind: "form", text: "(+ 1 2)" } });
  state = appendRecordingEntry(state, {
    id: "ent-1",
    recordingId: "rec-1",
    seq: 1,
    streamId: "stdout",
    text: "3"
  });
  state = openTranscriptWindow(state, { taskId: "task-1" });
  const window = Object.values(state.windows).find((win) => win.metadata?.role === "transcript");
  const listId = window.metadata.widgets.listId;

  const entryItem = state.widgets[listId].props.items.find((item) => item.entryId === "ent-1");
  let toggled = executeCommand(registry, RECORDING_TOGGLE_COMMAND, { state, item: entryItem });
  assert.equal(toggled.ok, true);
  state = toggled.result;
  assert.equal(state.recordingStore.entries["ent-1"].metadata.folded, true);

  state = refreshTranscriptWindow(state, window.id);
  let refreshedEntry = state.widgets[listId].props.items.find((item) => item.entryId === "ent-1");
  assert.ok(refreshedEntry.label.includes("[folded]"));

  toggled = executeCommand(registry, RECORDING_TOGGLE_COMMAND, { state, item: refreshedEntry });
  assert.equal(toggled.ok, true);
  state = toggled.result;
  assert.equal(state.recordingStore.entries["ent-1"].metadata.folded, false);
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
