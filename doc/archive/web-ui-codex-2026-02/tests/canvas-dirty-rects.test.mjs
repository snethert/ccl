import { test } from "node:test";
import assert from "node:assert/strict";

import { createCanvasBackend } from "../backends/canvas/renderer.mjs";
import { coalesceBounds } from "../backends/canvas/scene.mjs";

function createMockCanvas() {
  const calls = [];
  const ctx = {
    canvas: { width: 100, height: 100 },
    clearRect: (...args) => calls.push(["clearRect", ...args]),
    fillRect: (...args) => calls.push(["fillRect", ...args]),
    strokeRect: (...args) => calls.push(["strokeRect", ...args]),
    fillText: (...args) => calls.push(["fillText", ...args]),
    save: () => calls.push(["save"]),
    restore: () => calls.push(["restore"]),
    beginPath: () => calls.push(["beginPath"]),
    rect: (...args) => calls.push(["rect", ...args]),
    clip: () => calls.push(["clip"]),
    measureText: () => ({ width: 0, actualBoundingBoxAscent: 0, actualBoundingBoxDescent: 0 })
  };
  const canvas = {
    width: 100,
    height: 100,
    getContext: () => ctx
  };
  ctx.canvas = canvas;
  return { canvas, ctx, calls };
}

test("canvas backend clears only dirty rects", () => {
  const { canvas, calls } = createMockCanvas();
  const backend = createCanvasBackend({ canvas });
  const scene = [
    { id: "rect", kind: "rect", bounds: { x: 0, y: 0, width: 10, height: 10 }, props: { fill: "#f00" } }
  ];

  backend.render(scene, { dirtyRects: [{ x: 2, y: 2, width: 4, height: 4 }] });

  const clearCalls = calls.filter((entry) => entry[0] === "clearRect");
  assert.equal(clearCalls.length, 1);
  assert.deepEqual(clearCalls[0].slice(1), [2, 2, 4, 4]);
});

test("canvas backend draws only nodes intersecting dirty rects", () => {
  const { canvas, calls } = createMockCanvas();
  const backend = createCanvasBackend({ canvas });
  const scene = [
    { id: "inside", kind: "rect", bounds: { x: 1, y: 1, width: 4, height: 4 }, props: { fill: "#0f0" } },
    { id: "outside", kind: "rect", bounds: { x: 50, y: 50, width: 10, height: 10 }, props: { fill: "#00f" } }
  ];

  backend.render(scene, { dirtyRects: [{ x: 0, y: 0, width: 10, height: 10 }] });

  const fillCalls = calls.filter((entry) => entry[0] === "fillRect");
  assert.equal(fillCalls.length, 1);
  assert.deepEqual(fillCalls[0].slice(1), [1, 1, 4, 4]);
});

test("coalesceBounds merges overlapping rects", () => {
  const rects = coalesceBounds([
    { x: 0, y: 0, width: 10, height: 10 },
    { x: 8, y: 8, width: 4, height: 4 },
    { x: 30, y: 30, width: 2, height: 2 }
  ]);

  assert.equal(rects.length, 2);
  assert.deepEqual(rects[0], { x: 0, y: 0, width: 12, height: 12 });
  assert.deepEqual(rects[1], { x: 30, y: 30, width: 2, height: 2 });
});
