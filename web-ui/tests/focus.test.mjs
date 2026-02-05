import { test } from "node:test";
import assert from "node:assert/strict";

import { createState } from "../src/state.mjs";
import { setFocus, FOCUS_REASONS } from "../src/focus.mjs";

test("focus history records deterministic sequence", () => {
  let state = createState();
  state = setFocus(state, "window-1", FOCUS_REASONS.USER, 1);
  state = setFocus(state, "window-2", FOCUS_REASONS.COMMAND, 2);

  assert.equal(state.focus, "window-2");
  assert.equal(state.focusHistory.length, 2);
  assert.deepEqual(state.focusHistory[0], {
    seq: 1,
    target: "window-1",
    reason: FOCUS_REASONS.USER
  });
});
