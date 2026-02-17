import { test } from "node:test";
import assert from "node:assert/strict";

import { runHeadless } from "./browser-runner.mjs";

test("headless browser render-only harness runs without kernel", async (t) => {
  if (process.env.WEB_UI_ENABLE_BROWSER_TESTS !== "1") {
    t.skip("Set WEB_UI_ENABLE_BROWSER_TESTS=1 to run browser tests");
    return;
  }
  const result = await runHeadless({ kernelEnabled: false, timeoutMs: 10000 });
  if (result.skipped) {
    t.skip(result.reason);
    return;
  }

  assert.equal(result.kernelEnabled, false);
  assert.equal(result.ok, true, result.error || "Render-only harness failed");
  assert.equal(result.uiBundleOk, true);
  assert.equal(result.wasmUiOk, true);
  assert.equal(result.uiBundleInfo?.skipped, true);
  assert.equal(result.wasmUiInfo?.skipped, true);
  assert.equal(result.domOk, true);
  assert.equal(result.domSnapshotMatch, true);
  assert.equal(result.domReuseOk, true);
  assert.equal(result.canvasWidgetOk, true);
  assert.equal(result.webglWidgetOk, true);
  assert.equal(result.canvasOk, true);
  assert.equal(result.canvasBackendHitOk, true);
  assert.equal(result.canvasMeasureOk, true);
  assert.equal(result.webglOk, true);
  assert.equal(result.webglBackendHitOk, true);
  assert.equal(result.webglMeasureOk, true);
  assert.equal(result.persistenceOk, true);
  assert.equal(result.uiBridgeOk, true);
});
