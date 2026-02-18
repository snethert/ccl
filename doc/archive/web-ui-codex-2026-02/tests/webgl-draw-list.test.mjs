import { test } from "node:test";
import assert from "node:assert/strict";

import { buildScene } from "../backends/canvas/scene.mjs";
import { buildWebGLDrawList, parseWebGLColor } from "../backends/webgl/draw-list.mjs";

test("buildWebGLDrawList emits deterministic vertices", () => {
  const scene = buildScene([
    {
      id: "rect-1",
      kind: "rect",
      bounds: { x: 0, y: 0, width: 10, height: 20 },
      props: { fill: "#ff0000" }
    },
    {
      id: "rect-2",
      kind: "rect",
      bounds: { x: 20, y: 5, width: 5, height: 5 },
      props: { fill: "#00ff00" }
    }
  ]);

  const draw = buildWebGLDrawList(scene);
  assert.equal(draw.count, 12);
  assert.equal(draw.positions.length, 24);
  assert.equal(draw.colors.length, 48);

  const clipped = buildWebGLDrawList(scene, { clipRect: { x: 0, y: 0, width: 15, height: 25 } });
  assert.equal(clipped.count, 6);
});

test("parseWebGLColor supports hex and rgba", () => {
  assert.deepEqual(parseWebGLColor("#000"), [0, 0, 0, 1]);
  assert.deepEqual(parseWebGLColor("#ff0000"), [1, 0, 0, 1]);
  assert.deepEqual(parseWebGLColor("rgba(0, 128, 255, 0.5)"), [0, 0.5019607843137255, 1, 0.5]);
});
