import { test } from "node:test";
import assert from "node:assert/strict";

import { buildScene, hitTestScene } from "../backends/canvas/scene.mjs";

test("hitTestScene returns the topmost hit", () => {
  const scene = buildScene([
    {
      id: "bottom",
      kind: "rect",
      bounds: { x: 0, y: 0, width: 20, height: 20 },
      props: { fill: "#111" }
    },
    {
      id: "top",
      kind: "rect",
      bounds: { x: 0, y: 0, width: 20, height: 20 },
      props: { fill: "#222" }
    }
  ]);

  const hit = hitTestScene(scene, { x: 5, y: 5 });
  assert.ok(hit, "hit should be found");
  assert.equal(hit.id, "top");
});

test("hitTestScene ignores groups and misses", () => {
  const scene = buildScene([
    { id: "group", kind: "group", bounds: { x: 0, y: 0, width: 10, height: 10 }, children: [] }
  ]);

  const hit = hitTestScene(scene, { x: 1, y: 1 });
  assert.equal(hit, null);
});
