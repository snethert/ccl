import { test } from "node:test";
import assert from "node:assert/strict";

import { replayEvents } from "./replay-harness.mjs";

const initialState = {
  workspace: { id: "workspace-0", taskIds: [], activeTaskId: null, title: "Workspace" },
  tasks: {},
  windows: {},
  widgets: {},
  layout: null
};

test("replay handles recording events", () => {
  const events = [
    { seq: 1, type: "recording:append", payload: { recording: { id: "rec-1" } } },
    { seq: 2, type: "recording:entry.append", payload: { entry: { id: "ent-1", recordingId: "rec-1" } } },
    { seq: 3, type: "recording:anchor.attach", payload: { anchor: { id: "anc-1", entryId: "ent-1" } } },
    { seq: 4, type: "recording:entry.fold", payload: { entryId: "ent-1", folded: true } },
    { seq: 5, type: "command-history:append", payload: { invocation: { id: "inv-1", commandId: "cmd-1" } } }
  ];

  const result = replayEvents(initialState, events);
  const store = result.state.recordingStore;
  assert.deepEqual(store.recordingOrder, ["rec-1"]);
  assert.deepEqual(store.entryOrder, ["ent-1"]);
  assert.equal(store.anchors["anc-1"].entryId, "ent-1");
  assert.equal(store.entries["ent-1"].metadata.folded, true);
  assert.equal(result.state.commandHistory.length, 1);
});
