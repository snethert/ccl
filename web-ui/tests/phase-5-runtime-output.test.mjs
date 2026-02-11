import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createState,
  applyRuntimeOutput,
  applyRuntimeMessage,
  drainRuntimeSabMessages
} from "../src/index.mjs";
import {
  createMicrokernel,
  KERNEL_OP_STREAM_WRITE,
  KERNEL_OP_RUNTIME_EVENT
} from "../../doc/wasm/js/microkernel.mjs";
import { createSabRing, SAB_RING_TRANSPORT } from "../../doc/wasm/js/sab-ring.mjs";

function encodeUtf8(text) {
  return new TextEncoder().encode(String(text));
}

function writeBytes(mem, ptr, bytes) {
  new Uint8Array(mem.buffer, ptr, bytes.length).set(bytes);
}

test("applyRuntimeOutput ingests recording payloads", () => {
  const state = createState();
  const payload = {
    recording: { id: "rec-1", jobId: "job-1", streamId: "repl" },
    entry: { id: "ent-1", recordingId: "rec-1", kind: "text", text: "=> 42", seq: 1, ts: 10 },
    anchor: { id: "anc-1", entryId: "ent-1", range: { start: 4, end: 6 }, path: [] }
  };
  const result = applyRuntimeOutput(state, payload);
  assert.deepEqual(result.errors, []);
  assert.ok(result.state.recordingStore.recordings["rec-1"]);
  assert.ok(result.state.recordingStore.entries["ent-1"]);
  assert.ok(result.state.recordingStore.anchors["anc-1"]);
});

test("applyRuntimeMessage handles runtime.output", () => {
  const state = createState();
  const message = {
    kind: "runtime.output",
    payload: { recording: { id: "rec-2", jobId: "job-2", streamId: "repl" } }
  };
  const result = applyRuntimeMessage(state, message);
  assert.equal(result.handled, true);
  assert.ok(result.state.recordingStore.recordings["rec-2"]);
});

test("microkernel emits runtime.output on stdout writes", () => {
  const memory = new WebAssembly.Memory({ initial: 1 });
  const messages = [];
  const microkernel = createMicrokernel({
    memory,
    runtimeBridge: {
      jobId: "job-1",
      emit: (msg) => messages.push(msg)
    }
  });

  const payloadPtr = 0;
  const bytes = encodeUtf8("hello\n");
  const dataPtr = 64;
  writeBytes(memory, dataPtr, bytes);
  const dv = new DataView(memory.buffer, payloadPtr, 16);
  dv.setUint32(0, 1, true); // sid stdout
  dv.setUint32(4, 0, true); // flags
  dv.setUint32(8, dataPtr, true);
  dv.setUint32(12, bytes.length, true);

  const id = microkernel.imports.kernel_request(KERNEL_OP_STREAM_WRITE, payloadPtr, 16);
  microkernel.imports.kernel_poll(id);
  microkernel.imports.kernel_drop_request(id);

  assert.equal(messages.length, 1);
  assert.equal(messages[0].kind, "runtime.output");
  assert.equal(messages[0].payload.entry.text, "hello\n");
  assert.equal(messages[0].payload.recording.jobId, "job-1");
});

test("microkernel accepts KERNEL_OP_RUNTIME_EVENT payloads", () => {
  const memory = new WebAssembly.Memory({ initial: 1 });
  const messages = [];
  const microkernel = createMicrokernel({
    memory,
    runtimeBridge: {
      emit: (msg) => messages.push(msg)
    }
  });

  const payload = {
    version: 1,
    kind: "runtime.output",
    jobId: "job-2",
    streamId: "repl",
    requestId: null,
    seq: 1,
    ts: 123,
    payload: { recording: { id: "rec-9" } },
    error: null
  };
  const payloadPtr = 128;
  const bytes = encodeUtf8(JSON.stringify(payload));
  writeBytes(memory, payloadPtr, bytes);

  const id = microkernel.imports.kernel_request(KERNEL_OP_RUNTIME_EVENT, payloadPtr, bytes.length);
  microkernel.imports.kernel_poll(id);
  const result = microkernel.imports.kernel_result(id);
  microkernel.imports.kernel_drop_request(id);

  assert.equal(result, 0);
  assert.equal(messages.length, 1);
  assert.deepEqual(messages[0], payload);
});

test("microkernel emits runtime.output over sab_ring_v1 event transport", () => {
  const memory = new WebAssembly.Memory({ initial: 1 });
  const egressRing = createSabRing({ capacity: 8192 });
  let fallbackEmitCount = 0;
  const microkernel = createMicrokernel({
    memory,
    runtimeBridge: {
      jobId: "job-sab",
      emit: () => {
        fallbackEmitCount += 1;
      },
      eventTransport: {
        transport: SAB_RING_TRANSPORT,
        sharedBuffer: egressRing.sharedBuffer
      }
    }
  });

  const payloadPtr = 0;
  const bytes = encodeUtf8("sab out\n");
  const dataPtr = 64;
  writeBytes(memory, dataPtr, bytes);
  const dv = new DataView(memory.buffer, payloadPtr, 16);
  dv.setUint32(0, 1, true);
  dv.setUint32(4, 0, true);
  dv.setUint32(8, dataPtr, true);
  dv.setUint32(12, bytes.length, true);

  const id = microkernel.imports.kernel_request(KERNEL_OP_STREAM_WRITE, payloadPtr, 16);
  microkernel.imports.kernel_poll(id);
  microkernel.imports.kernel_drop_request(id);
  assert.equal(fallbackEmitCount, 0, "emit callback fallback not used");

  const drained = drainRuntimeSabMessages({ transport: SAB_RING_TRANSPORT, ring: egressRing });
  assert.equal(drained.errors.length, 0);
  assert.equal(drained.count, 1);
  assert.equal(drained.messages[0].kind, "runtime.output");
  assert.equal(drained.messages[0].payload.entry.text, "sab out\n");
});

test("microkernel routes KERNEL_OP_RUNTIME_EVENT payloads to sab_ring_v1 event transport", () => {
  const memory = new WebAssembly.Memory({ initial: 1 });
  const egressRing = createSabRing({ capacity: 8192 });
  let fallbackEmitCount = 0;
  const microkernel = createMicrokernel({
    memory,
    runtimeBridge: {
      emit: () => {
        fallbackEmitCount += 1;
      },
      eventTransport: {
        transport: SAB_RING_TRANSPORT,
        sharedBuffer: egressRing.sharedBuffer
      }
    }
  });

  const payload = {
    version: 1,
    kind: "command.result",
    jobId: "job-sab",
    streamId: "commands",
    requestId: "req-1",
    seq: 1,
    ts: 10,
    payload: { invocationId: "inv-1", commandId: "runtime.eval.form", result: { ok: true } },
    error: null
  };
  const payloadPtr = 128;
  const bytes = encodeUtf8(JSON.stringify(payload));
  writeBytes(memory, payloadPtr, bytes);

  const id = microkernel.imports.kernel_request(KERNEL_OP_RUNTIME_EVENT, payloadPtr, bytes.length);
  microkernel.imports.kernel_poll(id);
  const result = microkernel.imports.kernel_result(id);
  microkernel.imports.kernel_drop_request(id);

  assert.equal(result, 0);
  assert.equal(fallbackEmitCount, 0, "emit callback fallback not used");
  const drained = drainRuntimeSabMessages({ transport: SAB_RING_TRANSPORT, ring: egressRing });
  assert.equal(drained.count, 1);
  assert.equal(drained.messages[0].kind, "command.result");
  assert.equal(drained.messages[0].requestId, "req-1");
});
