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
  assert.equal(result.commandInputOk, true);
  assert.equal(result.commandListOk, true);
  assert.equal(result.imeCompositionOk, true);
  assert.equal(result.deadKeyOk, true);
  assert.equal(result.mobileInputOk, true);
  assert.equal(result.virtualListOk, true);
  assert.equal(result.virtualTreeOk, true);
  assert.equal(result.virtualTableOk, true);
  assert.equal(result.canvasWidgetOk, true);
  assert.equal(result.canvasWidgetCommandOk, true);
  assert.equal(result.webglWidgetOk, true);
  assert.equal(result.webglWidgetCommandOk, true);
  assert.equal(result.focusOk, true);
  assert.equal(result.measureOk, true);
  assert.equal(result.hitTestOk, true);
  assert.equal(result.captureEventsOk, true);
  assert.equal(result.invalidateOk, true);
  assert.equal(result.canvasOk, true);
  assert.equal(result.canvasBackendHitOk, true);
  assert.equal(result.canvasMeasureOk, true);
  assert.equal(result.webglOk, true);
  assert.equal(result.webglBackendHitOk, true);
  assert.equal(result.webglMeasureOk, true);
  assert.equal(result.persistenceOk, true);
});
