import { test } from "node:test";
import assert from "node:assert/strict";

import { markPresentationStale, revalidatePresentations } from "../src/world-state.mjs";

test("markPresentationStale annotates metadata", () => {
  const result = markPresentationStale({ id: "pres-1", metadata: {} }, "gone");
  assert.equal(result.metadata.stale, true);
  assert.equal(result.metadata.staleReason, "gone");
});

test("revalidatePresentations marks stale when resolver fails", () => {
  const state = { presentations: { "pres-1": { id: "pres-1", metadata: {} } } };
  const result = revalidatePresentations(state, () => ({ ok: false, reason: "missing" }));
  assert.equal(result.state.presentations["pres-1"].metadata.stale, true);
  assert.deepEqual(result.stale, ["pres-1"]);
});
