import { test } from "node:test";
import assert from "node:assert/strict";

import { createState, recordEvent } from "../src/state.mjs";

test("event log ring buffer evicts oldest entries deterministically", () => {
  let state = createState({ eventLog: { capacity: 2, entries: [] } });
  state = recordEvent(state, { seq: 1, type: "a", payload: {} });
  state = recordEvent(state, { seq: 2, type: "b", payload: {} });
  state = recordEvent(state, { seq: 3, type: "c", payload: {} });

  assert.equal(state.eventLog.entries.length, 2);
  assert.equal(state.eventLog.entries[0].seq, 2);
  assert.equal(state.eventLog.entries[1].seq, 3);
});
