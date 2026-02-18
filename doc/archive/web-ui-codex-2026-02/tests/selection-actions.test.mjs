import { test } from "node:test";
import assert from "node:assert/strict";

import { buildSelectionActions } from "../src/selection-actions.mjs";

test("buildSelectionActions intersects action sets", () => {
  const selection = { targetIds: ["p1", "p2"] };
  const presentations = {
    p1: { id: "p1", type: "symbol" },
    p2: { id: "p2", type: "value" }
  };
  const actions = buildSelectionActions(selection, presentations);
  const ids = actions.map((action) => action.id).sort();
  assert.deepEqual(ids, ["describe", "inspect"]);
});

test("buildSelectionActions applies canonical priority then alphabetic fallback", () => {
  const selection = { targetIds: ["p1", "p2"] };
  const presentations = {
    p1: { id: "p1", type: "alpha" },
    p2: { id: "p2", type: "beta" }
  };
  const actions = buildSelectionActions(selection, presentations, {
    actionsByType: {
      alpha: ["zzz", "do-again", "inspect", "custom-b", "custom-a"],
      beta: ["inspect", "custom-a", "custom-b", "do-again", "zzz"]
    }
  });
  assert.deepEqual(
    actions.map((action) => action.id),
    ["inspect", "do-again", "custom-a", "custom-b", "zzz"]
  );
});
