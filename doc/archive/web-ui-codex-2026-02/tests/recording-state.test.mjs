import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createState,
  appendRecording,
  appendRecordingEntry,
  attachRecordingAnchor,
  setRecordingEntryFolded,
  recordCommandInvocation
} from "../src/state.mjs";

test("state recording helpers update recordingStore", () => {
  let state = createState();
  state = appendRecording(state, { id: "rec-1" });
  state = appendRecordingEntry(state, { id: "ent-1", recordingId: "rec-1" });
  state = attachRecordingAnchor(state, { id: "anc-1", entryId: "ent-1" });
  state = setRecordingEntryFolded(state, "ent-1", true);

  assert.deepEqual(state.recordingStore.recordingOrder, ["rec-1"]);
  assert.deepEqual(state.recordingStore.entryOrder, ["ent-1"]);
  assert.equal(state.recordingStore.anchors["anc-1"].entryId, "ent-1");
  assert.equal(state.recordingStore.entries["ent-1"].metadata.folded, true);
});

test("recordCommandInvocation appends normalized invocation", () => {
  let state = createState();
  state = recordCommandInvocation(state, {
    id: "inv-1",
    commandId: "cmd-1",
    args: { value: 1 }
  });
  assert.equal(state.commandHistory.length, 1);
  assert.equal(state.commandHistory[0].commandId, "cmd-1");
});
