import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createMicrokernel,
  KERNEL_OP_RUNTIME_COMMAND_POLL
} from "../../doc/wasm/js/microkernel.mjs";
import { createSabRing, SAB_RING_TRANSPORT } from "../../doc/wasm/js/sab-ring.mjs";
import { createRuntimeCommandClient } from "../src/index.mjs";

function decodeUtf8(bytes) {
  return new TextDecoder().decode(bytes);
}

function decodeFrame(bytes) {
  const dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const version = dv.getUint32(0, true);
  const invocationLen = dv.getUint32(4, true);
  const commandLen = dv.getUint32(8, true);
  const argsLen = dv.getUint32(12, true);
  const contextLen = dv.getUint32(16, true);
  let offset = 24;
  const invocationId = decodeUtf8(bytes.subarray(offset, offset + invocationLen));
  offset += invocationLen;
  const commandId = decodeUtf8(bytes.subarray(offset, offset + commandLen));
  offset += commandLen;
  const argsForm = decodeUtf8(bytes.subarray(offset, offset + argsLen));
  offset += argsLen;
  const contextForm = decodeUtf8(bytes.subarray(offset, offset + contextLen));
  return { version, invocationId, commandId, argsForm, contextForm };
}

test("microkernel runtime command poll returns encoded command frame", () => {
  const ring = createSabRing({ capacity: 8192 });
  const memory = new WebAssembly.Memory({ initial: 1 });
  const microkernel = createMicrokernel({
    memory,
    asyncStdin: true,
    runtimeBridge: {
      commandTransport: {
        transport: SAB_RING_TRANSPORT,
        sharedBuffer: ring.sharedBuffer
      }
    }
  });
  const client = createRuntimeCommandClient({
    timeoutMs: 0,
    commandTransport: {
      transport: SAB_RING_TRANSPORT,
      ring
    }
  });
  const dispatched = client.dispatchTypedCommand(
    {
      id: "runtime.eval.form",
      title: "Eval Form",
      args: [{ name: "form", type: "string", required: true }]
    },
    { id: "inv-1", args: { form: "(+ 1 2)" }, source: "palette" },
    { context: { package: "CL-USER" }, jobId: "job-1" }
  );
  assert.equal(dispatched.ok, true);
  assert.equal(dispatched.transport, SAB_RING_TRANSPORT);

  const payloadPtr = 0;
  const payloadView = new DataView(memory.buffer, payloadPtr, 8);
  payloadView.setUint32(0, 4096, true);
  payloadView.setUint32(4, 0, true);

  const reqId = microkernel.imports.kernel_request(KERNEL_OP_RUNTIME_COMMAND_POLL, payloadPtr, 8);
  assert.equal(microkernel.imports.kernel_poll(reqId), 1);
  assert.equal(microkernel.imports.kernel_result(reqId), 1);
  const size = microkernel.imports.kernel_response_size(reqId);
  assert.ok(size > 24);
  const outPtr = 64;
  const copied = microkernel.imports.kernel_copy_response(reqId, outPtr, size);
  assert.equal(copied, size);
  const out = new Uint8Array(memory.buffer, outPtr, size);
  const frame = decodeFrame(out);
  assert.equal(frame.version, 1);
  assert.equal(frame.invocationId, "inv-1");
  assert.equal(frame.commandId, "runtime.eval.form");
  assert.ok(frame.argsForm.includes("\"form\""));
  assert.ok(frame.argsForm.includes("(+ 1 2)"));
  assert.ok(frame.contextForm.includes("\"package\""));
  assert.ok(frame.contextForm.includes("CL-USER"));
  microkernel.imports.kernel_drop_request(reqId);

  void dispatched.promise.catch(() => {});
  client.cancelAll("phase-5-runtime-command-roundtrip test completed");
});

test("runtime command poll returns zero when sab ring is empty", () => {
  const ring = createSabRing({ capacity: 4096 });
  const memory = new WebAssembly.Memory({ initial: 1 });
  const microkernel = createMicrokernel({
    memory,
    runtimeBridge: {
      commandTransport: {
        transport: SAB_RING_TRANSPORT,
        sharedBuffer: ring.sharedBuffer
      }
    }
  });

  const payloadPtr = 0;
  const payloadView = new DataView(memory.buffer, payloadPtr, 8);
  payloadView.setUint32(0, 4096, true);
  payloadView.setUint32(4, 0, true);

  const reqId = microkernel.imports.kernel_request(KERNEL_OP_RUNTIME_COMMAND_POLL, payloadPtr, 8);
  assert.equal(microkernel.imports.kernel_poll(reqId), 1);
  const size = microkernel.imports.kernel_response_size(reqId);
  assert.equal(size, 0);
  assert.equal(microkernel.imports.kernel_result(reqId), 0);
  microkernel.imports.kernel_drop_request(reqId);
});

test("runtime command poll returns ENOSYS when sab transport is not configured", () => {
  const memory = new WebAssembly.Memory({ initial: 1 });
  const microkernel = createMicrokernel({ memory });

  const payloadPtr = 0;
  const payloadView = new DataView(memory.buffer, payloadPtr, 8);
  payloadView.setUint32(0, 4096, true);
  payloadView.setUint32(4, 0, true);

  const reqId = microkernel.imports.kernel_request(KERNEL_OP_RUNTIME_COMMAND_POLL, payloadPtr, 8);
  assert.equal(microkernel.imports.kernel_poll(reqId), 1);
  assert.equal(microkernel.imports.kernel_result(reqId), -52);
  assert.equal(microkernel.imports.kernel_response_size(reqId), 0);
  microkernel.imports.kernel_drop_request(reqId);
});
