/*
 * Stream seek/truncate smoke test (STREAM_SEEK / STREAM_TRUNCATE).
 *
 * Exercises file-backed streams via kernel_request without instantiating the
 * full WASM kernel.
 */

import assert from "node:assert/strict";

import {
  createMicrokernel,
  KERNEL_STATUS_DONE,
  KERNEL_OP_STREAM_OPEN,
  KERNEL_OP_STREAM_WRITE,
  KERNEL_OP_STREAM_READ,
  KERNEL_OP_STREAM_CLOSE,
  KERNEL_OP_STREAM_SEEK,
  KERNEL_OP_STREAM_TRUNCATE,
  KERNEL_STREAM_KIND_FILE,
} from "./microkernel.mjs";
import { createSharedCclRuntime } from "./ccl-loader.mjs";
import {
  FILE_MODE_READ,
  FILE_MODE_WRITE,
  FILE_MODE_CREATE,
  FILE_MODE_TRUNCATE,
} from "./persist-service.mjs";

const runtime = createSharedCclRuntime({
  memoryInitialPages: 1,
  subprimsTableInitial: 1,
  createMemory: true,
});

const microkernel = createMicrokernel({
  memory: runtime.memory,
  persistence: true,
});

const {
  kernel_request,
  kernel_poll,
  kernel_result,
  kernel_response_size,
  kernel_copy_response,
  kernel_drop_request,
} = microkernel.imports;

const view = new DataView(runtime.memory.buffer);
const encoder = new TextEncoder();

function writeU32(ptr, value) {
  view.setUint32(ptr >>> 0, value >>> 0, true);
}

function writeU64(ptr, value) {
  const v = typeof value === "bigint" ? value : BigInt(Math.trunc(value));
  const lo = Number(v & 0xffffffffn) >>> 0;
  const hi = Number((v >> 32n) & 0xffffffffn) >>> 0;
  view.setUint32(ptr >>> 0, lo, true);
  view.setUint32((ptr + 4) >>> 0, hi, true);
}

function writeI64(ptr, value) {
  const v = typeof value === "bigint" ? value : BigInt(Math.trunc(value));
  writeU64(ptr, BigInt.asUintN(64, v));
}

function readU64(ptr) {
  const lo = BigInt(view.getUint32(ptr >>> 0, true));
  const hi = BigInt(view.getUint32((ptr + 4) >>> 0, true));
  return (hi << 32n) | lo;
}

function callKernel(opcode, payloadPtr, payloadLen, responsePtr = 0, responseCap = 0) {
  const reqId = kernel_request(opcode, payloadPtr >>> 0, payloadLen >>> 0) >>> 0;
  const status = kernel_poll(reqId) >>> 0;
  assert.equal(status, KERNEL_STATUS_DONE, `request ${reqId} not done`);
  const result = kernel_result(reqId) | 0;
  let responseLen = 0;
  if (responseCap > 0) {
    responseLen = kernel_copy_response(reqId, responsePtr >>> 0, responseCap >>> 0) >>> 0;
  } else {
    responseLen = kernel_response_size(reqId) >>> 0;
  }
  kernel_drop_request(reqId);
  return { result, responseLen };
}

const pathPtr = 0x1000;
const fileArgPtr = 0x1100;
const openPayloadPtr = 0x1200;
const ioPayloadPtr = 0x1300;
const seekPayloadPtr = 0x1400;
const truncPayloadPtr = 0x1500;
const responsePtr = 0x1600;
const dataPtr = 0x1700;

const pathBytes = encoder.encode("seek-truncate.bin");
new Uint8Array(runtime.memory.buffer, pathPtr, pathBytes.length).set(pathBytes);

const modeFlags = FILE_MODE_READ | FILE_MODE_WRITE | FILE_MODE_CREATE | FILE_MODE_TRUNCATE;
writeU32(fileArgPtr + 0, modeFlags);
writeU32(fileArgPtr + 4, pathPtr);
writeU32(fileArgPtr + 8, pathBytes.length);
writeU32(fileArgPtr + 12, 0);

writeU32(openPayloadPtr + 0, KERNEL_STREAM_KIND_FILE);
writeU32(openPayloadPtr + 4, 0);
writeU32(openPayloadPtr + 8, fileArgPtr);
writeU32(openPayloadPtr + 12, 16);

const openRes = callKernel(KERNEL_OP_STREAM_OPEN, openPayloadPtr, 16);
assert.ok(openRes.result >= 3, `expected file stream sid, got ${openRes.result}`);
const sid = openRes.result >>> 0;

const data = new Uint8Array([0x41, 0x42, 0x43, 0x44, 0x45]);
new Uint8Array(runtime.memory.buffer, dataPtr, data.length).set(data);
writeU32(ioPayloadPtr + 0, sid);
writeU32(ioPayloadPtr + 4, 0);
writeU32(ioPayloadPtr + 8, dataPtr);
writeU32(ioPayloadPtr + 12, data.length);

const writeRes = callKernel(KERNEL_OP_STREAM_WRITE, ioPayloadPtr, 16);
assert.equal(writeRes.result, data.length, `expected write ${data.length}, got ${writeRes.result}`);

writeU32(seekPayloadPtr + 0, sid);
writeU32(seekPayloadPtr + 4, 0); // SEEK_SET
writeI64(seekPayloadPtr + 8, 0);

const seekRes = callKernel(KERNEL_OP_STREAM_SEEK, seekPayloadPtr, 16, responsePtr, 8);
assert.equal(seekRes.result, 0, `seek returned ${seekRes.result}`);
assert.equal(seekRes.responseLen, 8, `seek response length ${seekRes.responseLen}`);
assert.equal(readU64(responsePtr), 0n, "seek to start returned non-zero position");

writeU32(ioPayloadPtr + 0, sid);
writeU32(ioPayloadPtr + 4, data.length);

const readRes = callKernel(KERNEL_OP_STREAM_READ, ioPayloadPtr, 8, responsePtr, 16);
assert.equal(readRes.result, data.length, `expected read ${data.length}, got ${readRes.result}`);
const got = new Uint8Array(runtime.memory.buffer, responsePtr, data.length);
assert.deepEqual(Array.from(got), Array.from(data), "readback mismatch");

writeU32(truncPayloadPtr + 0, sid);
writeU32(truncPayloadPtr + 4, 0);
writeU64(truncPayloadPtr + 8, 3);

const truncRes = callKernel(KERNEL_OP_STREAM_TRUNCATE, truncPayloadPtr, 16);
assert.equal(truncRes.result, 0, `truncate returned ${truncRes.result}`);

writeU32(seekPayloadPtr + 0, sid);
writeU32(seekPayloadPtr + 4, 2); // SEEK_END
writeI64(seekPayloadPtr + 8, 0);

const seekEndRes = callKernel(KERNEL_OP_STREAM_SEEK, seekPayloadPtr, 16, responsePtr, 8);
assert.equal(seekEndRes.result, 0, `seek end returned ${seekEndRes.result}`);
assert.equal(readU64(responsePtr), 3n, "seek end returned wrong position");

writeU32(seekPayloadPtr + 0, sid);
writeU32(seekPayloadPtr + 4, 0); // SEEK_SET
writeI64(seekPayloadPtr + 8, 0);
callKernel(KERNEL_OP_STREAM_SEEK, seekPayloadPtr, 16, responsePtr, 8);

writeU32(ioPayloadPtr + 0, sid);
writeU32(ioPayloadPtr + 4, data.length);

const readTruncRes = callKernel(KERNEL_OP_STREAM_READ, ioPayloadPtr, 8, responsePtr, 16);
assert.equal(readTruncRes.result, 3, `expected read 3 after truncate, got ${readTruncRes.result}`);
const gotTrunc = new Uint8Array(runtime.memory.buffer, responsePtr, 3);
assert.deepEqual(Array.from(gotTrunc), Array.from(data.subarray(0, 3)), "truncated read mismatch");

writeU32(ioPayloadPtr + 0, sid);
writeU32(ioPayloadPtr + 4, 0);
const closeRes = callKernel(KERNEL_OP_STREAM_CLOSE, ioPayloadPtr, 8);
assert.equal(closeRes.result, 0, `close returned ${closeRes.result}`);

console.log("PASS: stream seek/truncate smoke test");
