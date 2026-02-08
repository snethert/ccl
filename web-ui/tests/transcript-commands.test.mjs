import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createState,
  addTask,
  appendRecording,
  appendRecordingEntry,
  addPresentation,
  registerTranscriptCommands,
  TRANSCRIPT_OPEN_COMMAND,
  TRANSCRIPT_REFRESH_COMMAND,
  TRANSCRIPT_ITEM_OPEN_COMMAND
} from "../src/state.mjs";
import { createRegistry, registerCommand, registerPresentationTranslator, executeCommand } from "../src/commands.mjs";

test("transcript open/refresh commands work", () => {
  const registry = createRegistry();
  registerTranscriptCommands(registry);

  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });

  const opened = executeCommand(registry, TRANSCRIPT_OPEN_COMMAND, { state, taskId: "task-1" });
  assert.equal(opened.ok, true);
  state = opened.result;
  const window = Object.values(state.windows).find((win) => win.metadata?.role === "transcript");
  assert.ok(window, "transcript window exists");

  state = appendRecording(state, { id: "rec-1" });
  state = appendRecordingEntry(state, {
    id: "ent-1",
    recordingId: "rec-1",
    seq: 1,
    streamId: "stdout",
    text: "Hello"
  });

  const refreshed = executeCommand(registry, TRANSCRIPT_REFRESH_COMMAND, { state, windowId: window.id });
  assert.equal(refreshed.ok, true);
  state = refreshed.result;
  const items = state.widgets[window.metadata.widgets.listId].props.items;
  assert.ok(items[0].label.includes("Hello"));
});

test("transcript item command resolves presentation translator", () => {
  const registry = createRegistry();
  registerCommand(registry, {
    id: "alpha.run",
    exec: (ctx) => ({ state: { ...ctx.state, marker: "ok" } })
  });
  registerPresentationTranslator(registry, "value", "click", () => "alpha.run");
  registerTranscriptCommands(registry);

  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = addPresentation(state, { id: "pres-1", type: "value" });
  state = appendRecording(state, { id: "rec-1" });
  state = appendRecordingEntry(state, {
    id: "ent-1",
    recordingId: "rec-1",
    presentationId: "pres-1",
    text: "Value"
  });

  const result = executeCommand(registry, TRANSCRIPT_ITEM_OPEN_COMMAND, {
    state,
    registry,
    item: { entryId: "ent-1", presentationId: "pres-1" }
  });
  assert.equal(result.ok, true);
  assert.equal(result.result.marker, "ok");
});
