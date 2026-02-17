import { test } from "node:test";
import assert from "node:assert/strict";

import { createRuntimeCommandClient } from "../src/runtime-command-client.mjs";
import { SAB_RING_TRANSPORT } from "../src/runtime-transport.mjs";

function commandSpec() {
  return {
    id: "runtime.eval.form",
    title: "Eval Form",
    args: [{ name: "form", type: "string", required: true }]
  };
}

function createAcceptingTransport() {
  const enqueued = [];
  return {
    enqueued,
    transport: {
      transport: SAB_RING_TRANSPORT,
      enqueueFrame(frame, meta) {
        enqueued.push({ frame, meta });
        return { ok: true };
      }
    }
  };
}

test("runtime command baseline has no hard admission cap and tracks pending deterministically", async () => {
  const { enqueued, transport } = createAcceptingTransport();
  const client = createRuntimeCommandClient({
    timeoutMs: 0,
    commandTransport: transport
  });

  const settledPromises = [];
  for (let i = 0; i < 96; i += 1) {
    const dispatch = client.dispatchTypedCommand(
      commandSpec(),
      { id: `inv-${i}`, args: { form: `(+ ${i} 1)` }, source: "palette" },
      { context: { package: "CL-USER" }, jobId: "job-admission" }
    );
    assert.equal(dispatch.ok, true);
    assert.equal(dispatch.requestId, `req-inv-${i}`);
    settledPromises.push(dispatch.promise.catch(() => null));
  }

  assert.equal(
    client.pendingCount(),
    96,
    "baseline admission currently has no hard inflight cap; commands remain admitted until timeout/result/cancel"
  );
  assert.equal(enqueued.length, 96);

  client.cancelAll("runtime-command-admission baseline cleanup");
  await Promise.allSettled(settledPromises);
  assert.equal(client.pendingCount(), 0);
});

test("runtime command timeout path cleans up pending entries and preserves request-id sequencing", async () => {
  const { transport } = createAcceptingTransport();
  const client = createRuntimeCommandClient({
    timeoutMs: 15,
    commandTransport: transport
  });

  const first = client.dispatchTypedCommand(
    commandSpec(),
    { args: { form: "(+ 1 2)" }, source: "palette" },
    { context: { package: "CL-USER" }, jobId: "job-timeout" }
  );
  assert.equal(first.ok, true);
  assert.equal(first.requestId, "req-1");
  assert.equal(client.pendingCount(), 1);

  await assert.rejects(first.promise, (err) => {
    assert.equal(err.ok, false);
    assert.equal(err.requestId, "req-1");
    assert.equal(err.reason, "Runtime command timeout");
    return true;
  });
  assert.equal(client.pendingCount(), 0);

  const second = client.dispatchTypedCommand(
    commandSpec(),
    { args: { form: "(+ 2 3)" }, source: "palette" },
    { context: { package: "CL-USER" }, jobId: "job-timeout" }
  );
  assert.equal(second.ok, true);
  assert.equal(second.requestId, "req-2");

  await assert.rejects(second.promise, (err) => {
    assert.equal(err.ok, false);
    assert.equal(err.requestId, "req-2");
    assert.equal(err.reason, "Runtime command timeout");
    return true;
  });
  assert.equal(client.pendingCount(), 0);
});
