import { test } from "node:test";
import assert from "node:assert/strict";

import { normalizeSelection } from "../src/selection.mjs";


test("normalizeSelection accepts string target", () => {
  const selection = normalizeSelection("item-1");
  assert.deepEqual(selection, {
    id: "item-1",
    kind: "item",
    targetIds: ["item-1"],
    anchorId: "item-1",
    metadata: {}
  });
});

test("normalizeSelection accepts object target", () => {
  const selection = normalizeSelection({ target: "row-7", kind: "row" });
  assert.equal(selection.id, "row-7");
  assert.equal(selection.kind, "row");
  assert.deepEqual(selection.targetIds, ["row-7"]);
  assert.equal(selection.anchorId, "row-7");
});
