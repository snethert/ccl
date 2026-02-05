import { test } from "node:test";
import assert from "node:assert/strict";

import { runHeadless } from "./browser-runner.mjs";

test("headless browser harness runs deterministically", async (t) => {
  if (process.env.WEB_UI_ENABLE_BROWSER_TESTS !== "1") {
    t.skip("Set WEB_UI_ENABLE_BROWSER_TESTS=1 to run browser tests");
    return;
  }
  const result = await runHeadless();
  if (result.skipped) {
    t.skip(result.reason);
    return;
  }
  assert.equal(result.ok, true, result.error || "Headless harness failed");
  assert.equal(result.snapshotMatch, true);
  assert.equal(result.domOk, true);
  assert.equal(result.domSnapshotMatch, true);
  assert.equal(result.domReuseOk, true);
  assert.equal(result.commandDomOk, true);
  assert.equal(result.commandInvokeOk, true);
  assert.equal(result.canvasOk, true);
});
