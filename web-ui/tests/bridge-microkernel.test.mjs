import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createMicrokernel,
  KERNEL_OP_UI_POLL,
  KERNEL_OP_UI_RENDER,
  KERNEL_OP_UI_MEASURE_TEXT,
} from "../../doc/wasm/js/microkernel.mjs";

import { encodeEvents, EVENT_TYPES } from "../bridge/codec.mjs";

function encodeUtf8(text) {
  return new TextEncoder().encode(String(text));
}

function writeBytes(mem, ptr, bytes) {
  new Uint8Array(mem.buffer, ptr, bytes.length).set(bytes);
}

function buildTreePayload() {
  const strings = ["div", "data-widget-id", "w1", "hi"];
  const bytes = strings.map(encodeUtf8);
  const stringTableSize = bytes.reduce((sum, b) => sum + 4 + b.length, 0);
  const headerSize = 24;
  const nodesSize = 60 + 16;
  const totalSize = headerSize + stringTableSize + nodesSize;
  const buf = new ArrayBuffer(totalSize);
  const dv = new DataView(buf);
  const out = new Uint8Array(buf);
  dv.setUint32(0, 0x55494231, true);
  dv.setUint32(4, 1, true);
  dv.setUint32(8, strings.length, true);
  dv.setUint32(12, 2, true);
  dv.setUint32(16, 0, true);
  dv.setUint32(20, 0, true);
  let off = headerSize;
  bytes.forEach((b) => {
    dv.setUint32(off, b.length, true);
    off += 4;
    out.set(b, off);
    off += b.length;
  });
  // element node
  dv.setUint32(off, 1, true);
  dv.setUint32(off + 4, 0, true);
  dv.setUint32(off + 8, 0xffffffff, true);
  off += 12;
  dv.setUint32(off, 0, true); // tag
  dv.setUint32(off + 4, 1, true); // props
  dv.setUint32(off + 8, 1, true); // children
  off += 12;
  dv.setUint32(off, 1, true); // key index data-widget-id
  dv.setUint32(off + 4, 3, true); // string value
  dv.setUint32(off + 8, 2, true); // w1
  dv.setUint32(off + 12, 0, true);
  off += 16;
  dv.setUint32(off, 1, true); // child index
  off += 4;
  // text node
  dv.setUint32(off, 0, true);
  dv.setUint32(off + 4, 0, true);
  dv.setUint32(off + 8, 0xffffffff, true);
  off += 12;
  dv.setUint32(off, 3, true); // "hi"
  return new Uint8Array(buf);
}

test("microkernel handles UI poll/render/measure opcodes", () => {
  const memory = new WebAssembly.Memory({ initial: 1 });
  const encodedEvents = encodeEvents([
    { type: EVENT_TYPES.pointer, flags: 1, x: 10, y: 20, targetId: "w1" },
  ]);
  const treePayload = buildTreePayload();
  const uiService = {
    pollEvents: () => encodedEvents,
    renderTree: () => 0,
    measureText: () => ({ width: 10, height: 12, ascent: 9, descent: 3 }),
  };

  const microkernel = createMicrokernel({ memory, uiService });
  const { kernel_request, kernel_poll, kernel_result, kernel_response_size, kernel_copy_response, kernel_drop_request } =
    microkernel.imports;

  // UI_POLL
  const pollPtr = 0;
  const pollView = new DataView(memory.buffer, pollPtr, 12);
  pollView.setUint32(0, 16, true);
  pollView.setUint32(4, 4096, true);
  pollView.setUint32(8, 0, true);
  const pollId = kernel_request(KERNEL_OP_UI_POLL, pollPtr, 12);
  assert.equal(kernel_poll(pollId), 1);
  assert.equal(kernel_result(pollId), 1);
  const pollSize = kernel_response_size(pollId);
  const pollOutPtr = 64;
  const copied = kernel_copy_response(pollId, pollOutPtr, pollSize);
  assert.equal(copied, pollSize);
  const got = new Uint8Array(memory.buffer, pollOutPtr, pollSize);
  assert.equal(got[0], encodedEvents.payload[0]);
  kernel_drop_request(pollId);

  // UI_RENDER
  const renderPtr = 512;
  writeBytes(memory, renderPtr, treePayload);
  const renderId = kernel_request(KERNEL_OP_UI_RENDER, renderPtr, treePayload.length);
  assert.equal(kernel_result(renderId), 0);
  kernel_drop_request(renderId);

  // UI_MEASURE_TEXT
  const fontBytes = encodeUtf8("12px monospace");
  const textBytes = encodeUtf8("hello");
  const fontPtr = 2048;
  const textPtr = fontPtr + fontBytes.length + 8;
  writeBytes(memory, fontPtr, fontBytes);
  writeBytes(memory, textPtr, textBytes);
  const measPtr = 1536;
  const measView = new DataView(memory.buffer, measPtr, 16);
  measView.setUint32(0, fontPtr, true);
  measView.setUint32(4, fontBytes.length, true);
  measView.setUint32(8, textPtr, true);
  measView.setUint32(12, textBytes.length, true);
  const measId = kernel_request(KERNEL_OP_UI_MEASURE_TEXT, measPtr, 16);
  assert.equal(kernel_result(measId), 0);
  const measSize = kernel_response_size(measId);
  const measOutPtr = 4096;
  kernel_copy_response(measId, measOutPtr, measSize);
  const dv = new DataView(memory.buffer, measOutPtr, measSize);
  assert.equal(dv.getFloat64(0, true), 10);
  assert.equal(dv.getFloat64(8, true), 12);
  kernel_drop_request(measId);
});
