import { test } from "node:test";
import assert from "node:assert/strict";

import {
  RUNTIME_BRIDGE_VERSION,
  RUNTIME_MESSAGE_KINDS,
  createRuntimeMessage,
  encodeRuntimeMessage,
  decodeRuntimeMessage,
  normalizeRuntimeMessage
} from "../bridge/runtime.mjs";

test("createRuntimeMessage fills defaults", () => {
  const message = createRuntimeMessage(
    { kind: RUNTIME_MESSAGE_KINDS.output, payload: { text: "ok" } },
    { now: () => 123 }
  );
  assert.equal(message.version, RUNTIME_BRIDGE_VERSION);
  assert.equal(message.seq, 0);
  assert.equal(message.ts, 123);
  assert.equal(message.kind, RUNTIME_MESSAGE_KINDS.output);
  assert.deepEqual(message.payload, { text: "ok" });
});

test("encode/decode round trips runtime messages", () => {
  const encoded = encodeRuntimeMessage({
    version: RUNTIME_BRIDGE_VERSION,
    kind: RUNTIME_MESSAGE_KINDS.commandResult,
    seq: 5,
    ts: 999,
    payload: { value: 42 }
  });
  const decoded = decodeRuntimeMessage(encoded, { strictKinds: true });
  assert.equal(decoded.ok, true);
  assert.equal(decoded.message.kind, RUNTIME_MESSAGE_KINDS.commandResult);
  assert.equal(decoded.message.seq, 5);
  assert.equal(decoded.message.ts, 999);
  assert.deepEqual(decoded.message.payload, { value: 42 });
});

test("normalizeRuntimeMessage rejects unsupported version", () => {
  assert.throws(() =>
    normalizeRuntimeMessage({
      version: 99,
      kind: RUNTIME_MESSAGE_KINDS.output,
      seq: 1,
      ts: 1,
      payload: null
    })
  );
});

test("decodeRuntimeMessage reports invalid kinds in strict mode", () => {
  const decoded = decodeRuntimeMessage(
    {
      version: RUNTIME_BRIDGE_VERSION,
      kind: "runtime.unknown",
      seq: 1,
      ts: 1,
      payload: {}
    },
    { strictKinds: true }
  );
  assert.equal(decoded.ok, false);
  assert.ok(decoded.error.includes("Unsupported runtime message kind"));
});

test("normalizeRuntimeMessage requires seq and ts", () => {
  assert.throws(() =>
    normalizeRuntimeMessage({
      version: RUNTIME_BRIDGE_VERSION,
      kind: RUNTIME_MESSAGE_KINDS.output,
      ts: 1,
      payload: {}
    })
  );
  assert.throws(() =>
    normalizeRuntimeMessage({
      version: RUNTIME_BRIDGE_VERSION,
      kind: RUNTIME_MESSAGE_KINDS.output,
      seq: 1,
      payload: {}
    })
  );
});
