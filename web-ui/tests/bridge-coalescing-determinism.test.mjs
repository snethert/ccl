import { test } from "node:test";
import assert from "node:assert/strict";

import { encodeEvents, selectEvents, EVENT_TYPES } from "../bridge/codec.mjs";

function buildMoveFlood(count = 300) {
  const events = [];
  for (let i = 0; i < count; i += 1) {
    events.push({
      seq: i,
      type: EVENT_TYPES.pointer,
      flags: 4, // move
      targetId: "canvas-main",
      windowId: "main",
      x: i,
      y: i,
      button: 0,
      buttons: 1,
      modifiers: 0,
      pointerType: 0,
      clickCount: 0
    });
  }
  return events;
}

test("baseline event selection has no implicit coalescing contract", () => {
  const events = buildMoveFlood(320);
  const selected = selectEvents(events, 0, 0);

  assert.equal(selected.overflow, false);
  assert.equal(
    selected.events.length,
    events.length,
    "baseline v1 keeps every queued event unless maxEvents/maxBytes impose a prefix limit"
  );

  for (let i = 0; i < selected.events.length; i += 1) {
    assert.equal(selected.events[i], events[i]);
    assert.equal(selected.events[i].x, i);
    assert.equal(selected.events[i].seq, i);
  }

  const encoded = encodeEvents(selected.events);
  const dv = new DataView(encoded.payload.buffer, encoded.payload.byteOffset, encoded.payload.byteLength);
  assert.equal(encoded.count, events.length);
  assert.equal(dv.getUint32(12, true), events.length); // event_count
});

test("byte-capped prefixes remain deterministic across repeated runs", () => {
  const events = buildMoveFlood(1200);
  const maxBytes = 6144;
  const first = selectEvents(events, 0, maxBytes);

  assert.equal(first.overflow, false);
  assert.ok(first.events.length > 0);
  assert.ok(first.events.length < events.length);

  for (let run = 0; run < 16; run += 1) {
    const next = selectEvents(events, 0, maxBytes);
    assert.equal(next.overflow, false);
    assert.equal(next.events.length, first.events.length);

    for (let i = 0; i < next.events.length; i += 1) {
      assert.equal(next.events[i].seq, i);
      assert.equal(next.events[i].x, i);
      assert.equal(next.events[i], events[i]);
    }
  }
});
