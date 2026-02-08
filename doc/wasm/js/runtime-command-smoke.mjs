/*
 * Runtime command transport smoke test.
 *
 * Exercises KERNEL_OP_RUNTIME_COMMAND_POLL with a queued command.invoke envelope.
 */

import assert from "node:assert/strict";

import {
  createMicrokernel,
  KERNEL_OP_RUNTIME_COMMAND_POLL
} from "./microkernel.mjs";

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
  let off = 24;
  const invocationId = decodeUtf8(bytes.subarray(off, off + invocationLen));
  off += invocationLen;
  const commandId = decodeUtf8(bytes.subarray(off, off + commandLen));
  off += commandLen;
  const argsForm = decodeUtf8(bytes.subarray(off, off + argsLen));
  off += argsLen;
  const contextForm = decodeUtf8(bytes.subarray(off, off + contextLen));
  return { version, invocationId, commandId, argsForm, contextForm };
}

const memory = new WebAssembly.Memory({ initial: 1 });
const microkernel = createMicrokernel({ memory, asyncStdin: true });
const queued = microkernel.enqueueRuntimeCommand({
  version: 1,
  kind: "command.invoke",
  jobId: "job-smoke",
  streamId: "commands",
  requestId: "req-inv-smoke",
  seq: 1,
  ts: Date.now(),
  payload: {
    invocation: {
      id: "inv-smoke",
      commandId: "runtime.eval.form",
      args: { form: "(+ 1 2)" },
      defaults: {},
      source: "smoke",
      ts: Date.now()
    },
    context: { package: "CL-USER" }
  },
  error: null
});
assert.equal(queued.ok, true, "queue command.invoke");

const payloadPtr = 0;
const payload = new DataView(memory.buffer, payloadPtr, 8);
payload.setUint32(0, 4096, true);
payload.setUint32(4, 0, true);

const reqId = microkernel.imports.kernel_request(KERNEL_OP_RUNTIME_COMMAND_POLL, payloadPtr, 8);
assert.equal(microkernel.imports.kernel_poll(reqId), 1, "command poll status DONE");
assert.equal(microkernel.imports.kernel_result(reqId), 1, "command poll result has frame");
const frameSize = microkernel.imports.kernel_response_size(reqId);
assert(frameSize > 24, "frame response size");
const outPtr = 64;
assert.equal(microkernel.imports.kernel_copy_response(reqId, outPtr, frameSize), frameSize, "frame copied");
const frame = decodeFrame(new Uint8Array(memory.buffer, outPtr, frameSize));
assert.equal(frame.version, 1, "frame version");
assert.equal(frame.invocationId, "inv-smoke", "invocation id");
assert.equal(frame.commandId, "runtime.eval.form", "command id");
assert(frame.argsForm.includes("\"form\""), "args form contains key");
assert(frame.contextForm.includes("CL-USER"), "context form contains package");
microkernel.imports.kernel_drop_request(reqId);

console.log("PASS: runtime command transport smoke");
