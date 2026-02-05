import { test } from "node:test";
import assert from "node:assert/strict";

import { runHeadless } from "./browser-runner.mjs";

test("headless browser harness runs deterministically", async (t) => {
  const result = await runHeadless();
  if (result.skipped) {
    t.skip(result.reason);
    return;
  }
  assert.equal(result.ok, true, result.error || "Headless harness failed");
  assert.equal(result.snapshotMatch, true);
  assert.equal(result.domOk, true);
  assert.equal(result.canvasOk, true);
});
