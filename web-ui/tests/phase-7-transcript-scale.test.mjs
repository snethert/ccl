import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createState,
  addTask,
  appendRecording,
  appendRecordingEntry,
  openTranscriptWindow,
  refreshTranscriptWindow,
  createSnapshot,
  restoreStateFromSnapshot,
  createQualityCollector
} from "../src/index.mjs";
import { stableStringify } from "./snapshot.mjs";

function findWindowByRole(state, role) {
  return Object.values(state.windows ?? {}).find((window) => window.metadata?.role === role) ?? null;
}

function buildTranscriptState(entryCount) {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = appendRecording(state, { id: "rec-1", context: { commandId: "repl.eval" }, input: { kind: "form", text: "(values)" } });
  for (let index = 1; index <= entryCount; index += 1) {
    state = appendRecordingEntry(state, {
      id: `ent-${index}`,
      recordingId: "rec-1",
      seq: index,
      streamId: "stdout",
      text: `value-${index}`
    });
  }
  return state;
}

test("phase-7 transcript scale supports 10k entries with deterministic window limits", () => {
  let state = buildTranscriptState(10000);
  state = openTranscriptWindow(state, { taskId: "task-1", limit: 150 });
  const transcriptWindow = findWindowByRole(state, "transcript");
  assert.ok(transcriptWindow);

  const listId = transcriptWindow.metadata.widgets.listId;
  const items = state.widgets[listId].props.items;
  assert.equal(items.length, 151);
  assert.equal(items[0].kind, "recording");
  assert.equal(items[0].entryCount, 150);
  assert.equal(items[items.length - 1].entryId, "ent-10000");

  const firstVisible = items[1];
  const firstVisibleIndex = Number.parseInt(String(firstVisible.entryId).replace("ent-", ""), 10);
  assert.equal(Number.isFinite(firstVisibleIndex), true);
  assert.equal(firstVisibleIndex >= 9850, true);
});

test("phase-7 transcript scale snapshot truncation remains deterministic", () => {
  const state = buildTranscriptState(4000);
  const budget = { maxEntries: 2500, maxBytes: 1024 * 1024 };

  const snapshotA = createSnapshot(state, {
    now: () => 10,
    recordingBudget: budget
  });
  assert.equal(snapshotA.state.recordingStore.truncation.applied, true);
  assert.equal(snapshotA.state.recordingStore.entryOrder.length, 2500);

  const restored = restoreStateFromSnapshot(snapshotA);
  const snapshotB = createSnapshot(restored.state, {
    now: () => 20,
    recordingBudget: budget
  });

  assert.equal(
    stableStringify(snapshotA.state.recordingStore.entryOrder),
    stableStringify(snapshotB.state.recordingStore.entryOrder)
  );
  assert.equal(snapshotB.state.recordingStore.entryOrder.length, 2500);
  assert.equal(snapshotB.state.recordingStore.truncation ?? null, null);

  const collector = createQualityCollector({
    budgets: {
      transcript: {
        minSupportedEntries: 2500
      }
    }
  });
  collector.recordTranscript({
    entryCount: snapshotB.state.recordingStore.entryOrder.length,
    recordingCount: snapshotB.state.recordingStore.recordingOrder.length,
    truncatedEntries: snapshotA.state.recordingStore.truncation.droppedEntries,
    mode: "snapshot"
  });
  const report = collector.evaluate();
  assert.equal(report.ok, true);
});

test("phase-7 transcript scale integration replay-save-restore-continue flow remains coherent", () => {
  let state = buildTranscriptState(1500);
  state = openTranscriptWindow(state, { taskId: "task-1", limit: 25 });
  const initialWindow = findWindowByRole(state, "transcript");
  assert.ok(initialWindow);

  const snapshot = createSnapshot(state, {
    now: () => 100,
    recordingBudget: { maxEntries: 2000, maxBytes: 1024 * 1024 }
  });
  const restored = restoreStateFromSnapshot(snapshot);
  let nextState = restored.state;

  nextState = appendRecordingEntry(nextState, {
    id: "ent-1501",
    recordingId: "rec-1",
    seq: 1501,
    streamId: "stdout",
    text: "value-1501"
  });
  nextState = refreshTranscriptWindow(nextState, initialWindow.id, { limit: 25 });

  const listId = nextState.windows[initialWindow.id].metadata.widgets.listId;
  const items = nextState.widgets[listId].props.items;
  assert.equal(items[items.length - 1].entryId, "ent-1501");
  assert.equal(nextState.recordingStore.entries["ent-1501"].recordingId, "rec-1");
});

