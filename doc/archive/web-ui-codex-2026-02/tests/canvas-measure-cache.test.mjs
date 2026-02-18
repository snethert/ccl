import { test } from "node:test";
import assert from "node:assert/strict";

import { createMeasureCache } from "../backends/canvas/measure.mjs";

test("measure cache tracks hits and misses", () => {
  let calls = 0;
  const cache = createMeasureCache((text, options) => {
    calls += 1;
    const width = String(text ?? "").length;
    return { width, height: 1, ascent: 1, descent: 0, font: options.font };
  });

  const first = cache.measureText("hello", { font: "12px monospace" });
  const second = cache.measureText("hello", { font: "12px monospace" });
  const third = cache.measureText("hello", { font: "14px monospace" });

  assert.equal(first.cacheHit, false);
  assert.equal(second.cacheHit, true);
  assert.equal(third.cacheHit, false);
  assert.equal(calls, 2);
  assert.equal(cache.stats.hits, 1);
  assert.equal(cache.stats.misses, 2);
});
