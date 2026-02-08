import { test } from "node:test";
import assert from "node:assert/strict";

import {
  OUTPUT_RECORDING_SCHEMA_VERSION,
  PRESENTATION_TAXONOMY_VERSION,
  TYPED_COMMAND_MODEL_VERSION,
  createRecordingStore,
  appendRecordingToStore,
  appendEntryToStore,
  copyAsForm,
  copyWithContext,
  replayAsInput,
  reRunRecording,
  executeTypedCommand
} from "../src/index.mjs";

test("phase-0 schema versions are allocated", () => {
  assert.equal(OUTPUT_RECORDING_SCHEMA_VERSION, "0");
  assert.equal(PRESENTATION_TAXONOMY_VERSION, "0");
  assert.equal(TYPED_COMMAND_MODEL_VERSION, "0");
});

test("phase-0 runtime contracts for recording and typed commands", () => {
  let store = createRecordingStore();
  store = appendRecordingToStore(store, {
    id: "rec-1",
    context: { commandId: "repl.eval", sessionId: "s-1", workspaceId: "w-1" },
    input: { kind: "form", text: "(+ 1 2)", package: "CL-USER" }
  });
  store = appendEntryToStore(store, {
    id: "ent-1",
    recordingId: "rec-1",
    text: "(+ 1 2)",
    anchorId: "anc-1",
    seq: 10
  });

  const copied = copyAsForm(store, "ent-1");
  assert.equal(copied.text, "(+ 1 2)");
  const contextual = copyWithContext(store, "ent-1");
  assert.equal(contextual.package, "CL-USER");

  const replay = replayAsInput(store, "rec-1");
  assert.equal(replay.input.text, "(+ 1 2)");
  const rerun = reRunRecording(store, "rec-1");
  assert.equal(rerun.commandId, "repl.eval");
  assert.equal(rerun.payload.context.sourceRecordingId, "rec-1");

  const execution = executeTypedCommand(
    {
      id: "demo.inspect",
      args: [{ name: "target", type: "selection", required: true, defaultFrom: ["selection"] }],
      exec: ({ args }) => ({ inspected: args.target.id })
    },
    { id: "inv-1", commandId: "demo.inspect", args: {} },
    { selection: { id: "sel-1", targetIds: ["pres-1"] } }
  );
  assert.equal(execution.ok, true);
  assert.equal(execution.result.inspected, "sel-1");
});
