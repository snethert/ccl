import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createState,
  recordCommandInvocation,
  applyRuntimeMessage,
  createRuntimeCommandClient,
  createRegistry,
  registerCommand,
  executeCommand
} from "../src/index.mjs";
import { RUNTIME_MESSAGE_KINDS } from "../bridge/runtime.mjs";
import { createSabRing, SAB_RING_TRANSPORT } from "../../doc/wasm/js/sab-ring.mjs";

function commandSpec() {
  return {
    id: "runtime.eval.form",
    title: "Eval Form",
    args: [{ name: "form", type: "string", required: true }]
  };
}

test("runtime command client dispatches command.invoke and resolves command.result", async () => {
  const ring = createSabRing({ capacity: 8192 });
  const client = createRuntimeCommandClient({
    now: () => 1000,
    timeoutMs: 2000,
    commandTransport: {
      transport: SAB_RING_TRANSPORT,
      ring
    }
  });

  const dispatch = client.dispatchTypedCommand(
    commandSpec(),
    { id: "inv-1", args: { form: "(+ 1 2)" }, source: "palette" },
    { context: { package: "CL-USER" }, jobId: "job-1" }
  );
  assert.equal(dispatch.ok, true);
  assert.equal(dispatch.transport, SAB_RING_TRANSPORT);
  assert.equal(dispatch.message.kind, RUNTIME_MESSAGE_KINDS.commandInvoke);
  assert.equal(dispatch.message.payload.invocation.commandId, "runtime.eval.form");
  assert.equal(dispatch.message.payload.invocation.args.form, "(+ 1 2)");
  assert.equal(client.pendingCount(), 1);

  let state = createState();
  state = recordCommandInvocation(state, {
    id: "inv-1",
    commandId: "runtime.eval.form",
    args: { form: "(+ 1 2)" },
    ts: 1000,
    source: "palette"
  });
  const runtimeDispatches = [];

  const runtimeResultMessage = {
    version: 1,
    kind: "command.result",
    jobId: "job-1",
    streamId: "commands",
    requestId: dispatch.requestId,
    seq: 2,
    ts: 1004,
    payload: {
      invocationId: "inv-1",
      commandId: "runtime.eval.form",
      result: { valueSummary: "3" },
      effects: { output: { kind: "recording.replay", recordingId: "rec-1" } },
      diagnostics: [],
      durationMs: 4
    },
    error: null
  };
  const applied = applyRuntimeMessage(state, runtimeResultMessage, {
    commandClient: client,
    commandEffectHandlers: {
      runtimeDispatch: ({ output }) => runtimeDispatches.push(output)
    }
  });
  assert.equal(applied.handled, true);
  assert.equal(applied.errors.length, 0);
  assert.equal(runtimeDispatches.length, 1);
  assert.equal(runtimeDispatches[0].kind, "recording.replay");
  const updated = applied.state.commandHistory.find((entry) => entry.id === "inv-1");
  assert.equal(updated.result.status, "succeeded");
  assert.deepEqual(updated.result.value, { valueSummary: "3" });

  const settled = await dispatch.promise;
  assert.equal(settled.ok, true);
  assert.equal(settled.requestId, dispatch.requestId);
  assert.equal(client.pendingCount(), 0);
});

test("runtime command client rejects on command.error and state marks invocation failed", async () => {
  const ring = createSabRing({ capacity: 8192 });
  const client = createRuntimeCommandClient({
    now: () => 2000,
    timeoutMs: 2000,
    commandTransport: {
      transport: SAB_RING_TRANSPORT,
      ring
    }
  });

  const dispatch = client.dispatchTypedCommand(
    commandSpec(),
    { id: "inv-2", args: { form: "(foo)" }, source: "palette" },
    { context: { package: "CL-USER" }, jobId: "job-2" }
  );
  assert.equal(dispatch.ok, true);

  let state = createState();
  state = recordCommandInvocation(state, {
    id: "inv-2",
    commandId: "runtime.eval.form",
    args: { form: "(foo)" },
    ts: 2000,
    source: "palette"
  });

  const runtimeErrorMessage = {
    version: 1,
    kind: "command.error",
    jobId: "job-2",
    streamId: "commands",
    requestId: dispatch.requestId,
    seq: 3,
    ts: 2008,
    payload: {
      invocationId: "inv-2",
      commandId: "runtime.eval.form",
      phase: "execute",
      retryable: true,
      condition: { type: "simple-error", summary: "Undefined function FOO", presentationId: null },
      diagnostics: []
    },
    error: null
  };
  const applied = applyRuntimeMessage(state, runtimeErrorMessage, { commandClient: client });
  assert.equal(applied.handled, true);
  const updated = applied.state.commandHistory.find((entry) => entry.id === "inv-2");
  assert.equal(updated.result.status, "failed");
  assert.equal(updated.result.phase, "execute");

  await assert.rejects(dispatch.promise, (err) => {
    assert.equal(err.ok, false);
    assert.equal(err.requestId, dispatch.requestId);
    return true;
  });
  assert.equal(client.pendingCount(), 0);
});

test("executeCommand routes runtime.* typed commands through runtime command client", () => {
  const ring = createSabRing({ capacity: 8192 });
  const client = createRuntimeCommandClient({
    now: () => 3000,
    timeoutMs: 0,
    commandTransport: {
      transport: SAB_RING_TRANSPORT,
      ring
    }
  });
  const registry = createRegistry();
  registerCommand(registry, {
    id: "runtime.eval.form",
    title: "Eval Form",
    args: [{ name: "form", type: "string", required: true }]
  });

  const result = executeCommand(registry, "runtime.eval.form", {
    runtimeCommandClient: client,
    args: { form: "(+ 1 2)" },
    invocation: { id: "inv-3", source: "palette" },
    runtimeContext: { package: "CL-USER" }
  });

  assert.equal(result.ok, true);
  assert.equal(result.pending, true);
  assert.equal(result.runtimeDispatched, true);
  assert.equal(result.requestId.startsWith("req-"), true);
  void result.promise?.catch(() => {});
  client.cancelAll("test teardown");
});
