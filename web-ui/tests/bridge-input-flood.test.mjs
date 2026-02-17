import { test } from "node:test";
import assert from "node:assert/strict";

import { selectEvents, EVENT_TYPES } from "../bridge/codec.mjs";

function buildFloodEvents(count = 4000) {
  const events = [];
  for (let i = 0; i < count; i += 1) {
    if ((i & 1) === 0) {
      events.push({
        seq: i,
        type: EVENT_TYPES.pointer,
        flags: 4, // move
        targetId: "canvas-main",
        windowId: "main",
        x: i,
        y: i * 0.5,
        button: 0,
        buttons: 1,
        modifiers: 0,
        pointerType: 0,
        clickCount: 0
      });
    } else {
      events.push({
        seq: i,
        type: EVENT_TYPES.wheel,
        flags: 0,
        targetId: "canvas-main",
        windowId: "main",
        deltaX: i * 0.25,
        deltaY: i * -0.5,
        deltaMode: 0,
        modifiers: 0
      });
    }
  }
  return events;
}

test("selectEvents returns deterministic prefixes for large pointer/wheel floods", () => {
  const events = buildFloodEvents(5000);
  const maxEvents = 750;
  const maxBytes = 96000;

  const expected = selectEvents(events, maxEvents, maxBytes);
  assert.equal(expected.overflow, false);
  assert.ok(expected.events.length > 0);
  assert.ok(expected.events.length <= maxEvents);

  for (let run = 0; run < 20; run += 1) {
    const actual = selectEvents(events, maxEvents, maxBytes);
    assert.equal(actual.overflow, false);
    assert.equal(actual.events.length, expected.events.length);

    for (let i = 0; i < actual.events.length; i += 1) {
      assert.equal(actual.events[i], expected.events[i]);
      assert.equal(actual.events[i], events[i]);
    }
  }
});

test("selectEvents keeps stable queue-order prefixes under byte pressure", () => {
  const events = buildFloodEvents(2000);
  const maxBytes = 4096;

  const selected = selectEvents(events, 0, maxBytes);
  assert.equal(selected.overflow, false);
  assert.ok(selected.events.length > 0);
  assert.ok(selected.events.length < events.length);

  for (let i = 0; i < selected.events.length; i += 1) {
    assert.equal(selected.events[i].seq, i);
    assert.equal(selected.events[i], events[i]);
  }
});
