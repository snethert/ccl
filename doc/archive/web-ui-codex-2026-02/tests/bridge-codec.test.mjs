import { test } from "node:test";
import assert from "node:assert/strict";

import { decodeTree, encodeEvents, selectEvents, EVENT_TYPES } from "../bridge/codec.mjs";

function encodeUtf8(text) {
  return new TextEncoder().encode(String(text));
}

function buildTreePayload() {
  const strings = ["div", "className", "root", "data-widget-id", "w1", "hi"];
  const bytes = strings.map(encodeUtf8);
  const stringTableSize = bytes.reduce((sum, b) => sum + 4 + b.length, 0);
  const nodeCount = 2;
  const headerSize = 24;
  const nodesSize = 60 + 16; // element + text
  const totalSize = headerSize + stringTableSize + nodesSize;
  const buf = new ArrayBuffer(totalSize);
  const dv = new DataView(buf);
  const out = new Uint8Array(buf);

  dv.setUint32(0, 0x55494231, true); // UIB1
  dv.setUint32(4, 1, true);
  dv.setUint32(8, strings.length, true);
  dv.setUint32(12, nodeCount, true);
  dv.setUint32(16, 0, true); // root index
  dv.setUint32(20, 0, true);

  let off = headerSize;
  bytes.forEach((b) => {
    dv.setUint32(off, b.length, true);
    off += 4;
    out.set(b, off);
    off += b.length;
  });

  // Node 0: element
  dv.setUint32(off, 1, true); // kind element
  dv.setUint32(off + 4, 0, true); // flags
  dv.setUint32(off + 8, 0xffffffff, true); // key
  off += 12;
  dv.setUint32(off, 0, true); // tag index "div"
  dv.setUint32(off + 4, 2, true); // propCount
  dv.setUint32(off + 8, 1, true); // childCount
  off += 12;
  // prop 1: className = "root"
  dv.setUint32(off, 1, true); // key index
  dv.setUint32(off + 4, 3, true); // string
  dv.setUint32(off + 8, 2, true); // value index
  dv.setUint32(off + 12, 0, true);
  off += 16;
  // prop 2: data-widget-id = "w1"
  dv.setUint32(off, 3, true);
  dv.setUint32(off + 4, 3, true);
  dv.setUint32(off + 8, 4, true);
  dv.setUint32(off + 12, 0, true);
  off += 16;
  // child index
  dv.setUint32(off, 1, true);
  off += 4;

  // Node 1: text
  dv.setUint32(off, 0, true); // kind text
  dv.setUint32(off + 4, 0, true); // flags
  dv.setUint32(off + 8, 0xffffffff, true); // key
  off += 12;
  dv.setUint32(off, 5, true); // text index "hi"

  return new Uint8Array(buf);
}

test("decodeTree parses a simple element+text payload", () => {
  const payload = buildTreePayload();
  const tree = decodeTree(payload);
  assert.equal(tree.kind, "element");
  assert.equal(tree.tag, "div");
  assert.equal(tree.props.className, "root");
  assert.equal(tree.props["data-widget-id"], "w1");
  assert.equal(tree.children.length, 1);
  assert.equal(tree.children[0].kind, "text");
  assert.equal(tree.children[0].text, "hi");
});

test("encodeEvents produces a v1 event batch", () => {
  const { payload, count } = encodeEvents([
    { type: EVENT_TYPES.pointer, flags: 1, x: 10, y: 20, button: 0, buttons: 1, targetId: "w1" },
    { type: EVENT_TYPES.key, flags: 1, key: "K", code: "KeyK", targetId: "w1" }
  ]);
  const dv = new DataView(payload.buffer, payload.byteOffset, payload.byteLength);
  assert.equal(dv.getUint32(0, true), 0x55494531); // UIE1
  assert.equal(dv.getUint32(4, true), 1);
  assert.equal(dv.getUint32(12, true), count);
});

test("selectEvents respects maxEvents and maxBytes", () => {
  const events = [
    { type: EVENT_TYPES.pointer, flags: 1, x: 1, y: 2, targetId: "w1" },
    { type: EVENT_TYPES.key, flags: 1, key: "A", code: "KeyA", targetId: "w1" },
    { type: EVENT_TYPES.text, text: "hello" }
  ];
  const limited = selectEvents(events, 2, 0);
  assert.equal(limited.events.length, 2);
  const tiny = selectEvents(events, 10, 8);
  assert.equal(tiny.overflow, true);
});
