import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createState,
  addTask,
  createRegistry,
  registerInspectorCommands,
  executeCommand,
  createRuntimeCommandClient,
  applyRuntimeMessage,
  INSPECTOR_WATCH_PIN_COMMAND,
  INSPECTOR_EDIT_STAGE_COMMAND,
  INSPECTOR_EDIT_APPLY_COMMAND
} from "../src/index.mjs";
import { createSabRing, SAB_RING_TRANSPORT } from "../../scripts/wasm/lib/sab-ring.mjs";

test("inspector watch pin command dispatches runtime command and settles with inspector update", async () => {
  const registry = createRegistry();
  registerInspectorCommands(registry);

  const ring = createSabRing({ capacity: 8192 });
  const client = createRuntimeCommandClient({
    now: () => 5000,
    timeoutMs: 5000,
    commandTransport: {
      transport: SAB_RING_TRANSPORT,
      ring
    }
  });

  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });

  const execResult = executeCommand(registry, INSPECTOR_WATCH_PIN_COMMAND, {
    state,
    presentationId: "pres-1",
    label: "Pinned Result",
    source: "inspector",
    runtimeCommandClient: client,
    runtimeContext: { package: "CL-USER" }
  });
  assert.equal(execResult.ok, true);
  assert.equal(execResult.pending, true);
  assert.equal(execResult.runtimeDispatched, true);
  assert.equal(typeof execResult.requestId, "string");

  state = execResult.result?.state ?? execResult.result ?? state;
  const invocation = state.commandHistory[state.commandHistory.length - 1];
  assert.equal(invocation.commandId, INSPECTOR_WATCH_PIN_COMMAND);
  assert.equal(invocation.result?.status, "pending");

  const resultMessage = {
    version: 1,
    kind: "command.result",
    jobId: "job-1",
    streamId: "commands",
    requestId: execResult.requestId,
    seq: 2,
    ts: 5002,
    payload: {
      invocationId: invocation.id,
      commandId: "runtime.watch.pin",
      result: { watchId: "watch-1", status: "pinned" },
      diagnostics: [],
      durationMs: 2
    },
    error: null
  };
  let applied = applyRuntimeMessage(state, resultMessage, { commandClient: client });
  assert.equal(applied.handled, true);
  state = applied.state;
  assert.equal(state.commandHistory.find((entry) => entry.id === invocation.id)?.result?.status, "succeeded");

  applied = applyRuntimeMessage(state, {
    version: 1,
    kind: "inspector.update",
    jobId: "job-1",
    streamId: "inspector",
    requestId: null,
    seq: 3,
    ts: 5003,
    payload: {
      type: "watch.sync",
      taskId: "task-1",
      watches: [{ id: "watch-1", presentationId: "pres-1", label: "Pinned Result", valueSummary: "42", pinned: true }]
    },
    error: null
  });
  assert.equal(applied.handled, true);
  state = applied.state;
  assert.equal(state.watches.length, 1);
  assert.equal(state.watches[0].id, "watch-1");

  const settled = await execResult.promise;
  assert.equal(settled.ok, true);
  assert.equal(settled.commandId, "runtime.watch.pin");
  assert.equal(settled.clientCommandId, INSPECTOR_WATCH_PIN_COMMAND);
});

test("inspector staged edit commands dispatch runtime place commands and settle", async () => {
  const registry = createRegistry();
  registerInspectorCommands(registry);

  const ring = createSabRing({ capacity: 8192 });
  const client = createRuntimeCommandClient({
    now: () => 6000,
    timeoutMs: 5000,
    commandTransport: {
      transport: SAB_RING_TRANSPORT,
      ring
    }
  });

  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });

  const stageResult = executeCommand(registry, INSPECTOR_EDIT_STAGE_COMMAND, {
    state,
    placeId: "pl-slot-x",
    before: "3",
    after: "4",
    label: "Set slot X",
    source: "inspector",
    runtimeCommandClient: client
  });
  assert.equal(stageResult.ok, true);
  assert.equal(stageResult.pending, true);
  assert.equal(typeof stageResult.requestId, "string");
  state = stageResult.result?.state ?? stageResult.result ?? state;
  const stageInvocation = state.commandHistory[state.commandHistory.length - 1];

  let applied = applyRuntimeMessage(state, {
    version: 1,
    kind: "command.result",
    jobId: "job-2",
    streamId: "commands",
    requestId: stageResult.requestId,
    seq: 4,
    ts: 6004,
    payload: {
      invocationId: stageInvocation.id,
      commandId: "runtime.place.stage",
      result: { editGroupId: "edit-1", status: "staged" },
      diagnostics: [],
      durationMs: 3
    },
    error: null
  }, { commandClient: client });
  state = applied.state;

  applied = applyRuntimeMessage(state, {
    version: 1,
    kind: "inspector.update",
    jobId: "job-2",
    streamId: "inspector",
    requestId: null,
    seq: 5,
    ts: 6005,
    payload: {
      type: "edit-group",
      taskId: "task-1",
      editGroup: {
        id: "edit-1",
        label: "Set slot X",
        status: "staged",
        edits: [{ placeId: "pl-slot-x", before: "3", after: "4" }]
      }
    },
    error: null
  });
  state = applied.state;
  assert.equal(state.editGroups[0].status, "staged");

  const applyResult = executeCommand(registry, INSPECTOR_EDIT_APPLY_COMMAND, {
    state,
    editGroupId: "edit-1",
    source: "inspector",
    runtimeCommandClient: client
  });
  assert.equal(applyResult.ok, true);
  assert.equal(applyResult.pending, true);
  assert.equal(typeof applyResult.requestId, "string");
  state = applyResult.result?.state ?? applyResult.result ?? state;
  const applyInvocation = state.commandHistory[state.commandHistory.length - 1];

  applied = applyRuntimeMessage(state, {
    version: 1,
    kind: "command.result",
    jobId: "job-2",
    streamId: "commands",
    requestId: applyResult.requestId,
    seq: 6,
    ts: 6006,
    payload: {
      invocationId: applyInvocation.id,
      commandId: "runtime.place.apply",
      result: { editGroupId: "edit-1", status: "applied" },
      diagnostics: [],
      durationMs: 2
    },
    error: null
  }, { commandClient: client });
  state = applied.state;

  applied = applyRuntimeMessage(state, {
    version: 1,
    kind: "inspector.update",
    jobId: "job-2",
    streamId: "inspector",
    requestId: null,
    seq: 7,
    ts: 6007,
    payload: {
      type: "edit-group",
      taskId: "task-1",
      editGroup: {
        id: "edit-1",
        label: "Set slot X",
        status: "applied",
        edits: [{ placeId: "pl-slot-x", before: "3", after: "4" }]
      }
    },
    error: null
  });
  state = applied.state;
  assert.equal(state.editGroups[0].status, "applied");

  await stageResult.promise;
  await applyResult.promise;
});
