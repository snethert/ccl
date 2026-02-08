import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createState,
  registerRecordingCommands,
  RECORDING_APPEND_COMMAND,
  RECORDING_ENTRY_APPEND_COMMAND,
  RECORDING_ENTRY_FOLD_COMMAND,
  RECORDING_TOGGLE_COMMAND,
  RECORDING_COPY_AS_FORM_COMMAND,
  RECORDING_COPY_WITH_CONTEXT_COMMAND,
  RECORDING_REPLAY_AS_INPUT_COMMAND,
  RECORDING_RERUN_COMMAND,
  COMMAND_HISTORY_APPEND_COMMAND
} from "../src/state.mjs";
import { createRegistry, executeCommand } from "../src/commands.mjs";

test("recording commands mutate state", () => {
  const registry = createRegistry();
  registerRecordingCommands(registry);

  let state = createState();
  let result = executeCommand(registry, RECORDING_APPEND_COMMAND, {
    state,
    recording: { id: "rec-1" }
  });
  state = result.result;
  assert.equal(state.recordingStore.recordingOrder[0], "rec-1");

  result = executeCommand(registry, RECORDING_ENTRY_APPEND_COMMAND, {
    state,
    entry: { id: "ent-1", recordingId: "rec-1" }
  });
  state = result.result;
  assert.equal(state.recordingStore.entryOrder[0], "ent-1");

  result = executeCommand(registry, RECORDING_ENTRY_FOLD_COMMAND, {
    state,
    entryId: "ent-1",
    folded: true
  });
  state = result.result;
  assert.equal(state.recordingStore.entries["ent-1"].metadata.folded, true);

  result = executeCommand(registry, RECORDING_TOGGLE_COMMAND, {
    state,
    recordingId: "rec-1"
  });
  state = result.result;
  assert.equal(state.recordingStore.recordings["rec-1"].metadata.collapsed, true);
});

test("command history append command records invocation", () => {
  const registry = createRegistry();
  registerRecordingCommands(registry);

  let state = createState();
  const result = executeCommand(registry, COMMAND_HISTORY_APPEND_COMMAND, {
    state,
    invocation: { id: "inv-1", commandId: "cmd-1", args: { value: 1 } }
  });
  state = result.result;
  assert.equal(state.commandHistory.length, 1);
});

test("recording copy/replay/rerun commands return deterministic payloads", () => {
  const registry = createRegistry();
  registerRecordingCommands(registry);

  let state = createState();
  let result = executeCommand(registry, RECORDING_APPEND_COMMAND, {
    state,
    recording: {
      id: "rec-1",
      context: { commandId: "repl.eval", sessionId: "s-1", workspaceId: "w-1" },
      input: { kind: "form", text: "(+ 1 2)", package: "CL-USER" }
    }
  });
  state = result.result;
  result = executeCommand(registry, RECORDING_ENTRY_APPEND_COMMAND, {
    state,
    entry: { id: "ent-1", recordingId: "rec-1", anchorId: "anc-1", text: "(+ 1 2)" }
  });
  state = result.result;

  const copied = executeCommand(registry, RECORDING_COPY_AS_FORM_COMMAND, {
    state,
    entryId: "ent-1"
  });
  assert.equal(copied.ok, true);
  assert.equal(copied.result.output.text, "(+ 1 2)");

  const contextual = executeCommand(registry, RECORDING_COPY_WITH_CONTEXT_COMMAND, {
    state,
    anchorId: "anc-1"
  });
  assert.equal(contextual.ok, true);
  assert.equal(contextual.result.output.package, "CL-USER");
  assert.equal(contextual.result.output.context.commandId, "repl.eval");

  const replayed = executeCommand(registry, RECORDING_REPLAY_AS_INPUT_COMMAND, {
    state,
    recordingId: "rec-1"
  });
  assert.equal(replayed.ok, true);
  assert.equal(replayed.result.output.input.text, "(+ 1 2)");

  const replayedFromItem = executeCommand(registry, RECORDING_REPLAY_AS_INPUT_COMMAND, {
    state,
    item: { entryId: "ent-1" }
  });
  assert.equal(replayedFromItem.ok, true);
  assert.equal(replayedFromItem.result.output.recordingId, "rec-1");

  const rerun = executeCommand(registry, RECORDING_RERUN_COMMAND, {
    state,
    recordingId: "rec-1"
  });
  assert.equal(rerun.ok, true);
  assert.equal(rerun.result.output.payload.context.sourceRecordingId, "rec-1");

  const rerunFromItem = executeCommand(registry, RECORDING_RERUN_COMMAND, {
    state,
    item: { entryId: "ent-1" }
  });
  assert.equal(rerunFromItem.ok, true);
  assert.equal(rerunFromItem.result.output.recordingId, "rec-1");
});
