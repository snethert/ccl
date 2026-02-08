import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createRegistry,
  registerCommand,
  executeCommand,
  createRecordingStore,
  appendRecordingToStore,
  appendEntryToStore,
  createState,
  addPresentation
} from "../src/index.mjs";

test("phase-1 runtime enforces recording entry to recording linkage", () => {
  const store = appendRecordingToStore(createRecordingStore(), { id: "rec-1" });
  const next = appendEntryToStore(store, { id: "ent-1", recordingId: "rec-1", seq: 100 });
  assert.deepEqual(next.recordings["rec-1"].entryIds, ["ent-1"]);
  assert.equal(next.recordings["rec-1"].seqStart, 100);
  assert.equal(next.recordings["rec-1"].seqEnd, 100);
  assert.throws(
    () => appendEntryToStore(next, { id: "ent-2", recordingId: "rec-missing" }),
    /Recording not found/
  );
});

test("phase-1 runtime command execution uses typed defaults in command registry", () => {
  const registry = createRegistry();
  registerCommand(registry, {
    id: "cmd.inspect",
    args: [{ name: "target", type: "selection", required: true, defaultFrom: ["selection"] }],
    exec: ({ args }) => args.target.id
  });

  const selection = { id: "sel-1", targetIds: ["pres-1"] };
  const result = executeCommand(registry, "cmd.inspect", { selection });
  assert.equal(result.ok, true);
  assert.equal(result.result, "sel-1");
  assert.equal(result.invocation.defaults.target.source, "selection");
});

test("phase-1 runtime degrades invalid typed presentation metadata safely", () => {
  let state = createState();
  state = addPresentation(state, {
    id: "pres-1",
    type: "command",
    metadata: { title: "Missing command id and args" }
  });
  const presentation = state.presentations["pres-1"];
  assert.equal(presentation.type, "value");
  assert.equal(presentation.metadata.degradedFromType, "command");
  assert.ok(Array.isArray(presentation.metadata.missingMetadata));
  assert.ok(presentation.metadata.missingMetadata.includes("commandId"));
});
