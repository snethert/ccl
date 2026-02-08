import { test } from "node:test";
import assert from "node:assert/strict";

import { normalizeRestart, normalizeConditionReport } from "../src/conditions.mjs";

test("normalizeRestart applies defaults", () => {
  const restart = normalizeRestart({ id: "rst-1", title: "Retry" });
  assert.equal(restart.safety, "safe");
  assert.deepEqual(restart.argSchema, []);
});

test("normalizeConditionReport normalizes sections", () => {
  const report = normalizeConditionReport({ id: "err-1", sections: [{ text: "Oops" }] });
  assert.equal(report.id, "err-1");
  assert.equal(report.sections[0].text, "Oops");
});
