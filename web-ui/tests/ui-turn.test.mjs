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
