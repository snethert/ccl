import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createState,
  enqueueUiSignal,
  beginUiTurn,
  advanceUiTurn,
  yieldUiTurn,
  endUiTurn
} from "../src/index.mjs";
import { replayEvents } from "./replay-harness.mjs";

test("ui turn drains queued signals and advances phases", () => {
  let state = createState();
  state = enqueueUiSignal(state, { type: "input:pointer", payload: { x: 1 } });
  state = enqueueUiSignal(state, { type: "input:key", payload: { key: "K" } });

  state = beginUiTurn(state, { commitPolicy: "rAF" });
  assert.ok(state.ui.turn);
  assert.equal(state.ui.turn.phase, "signals");
  assert.equal(state.ui.turn.signals.length, 2);
  assert.equal(state.ui.queue.length, 0);

  state = advanceUiTurn(state, "commands");
  assert.equal(state.ui.turn.phase, "commands");

  state = yieldUiTurn(state, "awaiting-input");
  assert.equal(state.ui.turn.phase, "yielded");
  assert.equal(state.ui.turn.yielded, true);
  assert.equal(state.ui.turn.yieldReason, "awaiting-input");

  state = endUiTurn(state);
  assert.equal(state.ui.turn, null);
  assert.equal(state.ui.history.length, 1);
});

test("ui turn prevents nested turns and backwards phases", () => {
  let state = createState();
  state = beginUiTurn(state);
  assert.throws(() => beginUiTurn(state), /UI turn already active/);
  state = advanceUiTurn(state, "commands");
  assert.throws(() => advanceUiTurn(state, "signals"), /cannot move backwards/);
});

test("replay harness applies ui turn events", () => {
  const events = [
    { seq: 1, type: "ui:signal.enqueue", payload: { signal: { type: "input:pointer", payload: { x: 1 } } } },
    { seq: 2, type: "ui:turn.begin", payload: { commitPolicy: "rAF" } },
    { seq: 3, type: "ui:turn.phase", payload: { phase: "commands" } },
    { seq: 4, type: "ui:turn.yield", payload: { reason: "awaiting-input" } },
    { seq: 5, type: "ui:turn.end", payload: {} }
  ];

  const result = replayEvents({}, events);
  assert.equal(result.state.ui.turn, null);
  assert.equal(result.state.ui.history.length, 1);
  assert.equal(result.state.ui.history[0].phase, "yielded");
  assert.equal(result.state.ui.history[0].yielded, true);
  assert.equal(result.state.eventLog.entries.length, events.length);
});
