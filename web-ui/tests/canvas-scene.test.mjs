import { test } from "node:test";
import assert from "node:assert/strict";

import { buildScene } from "../backends/canvas/scene.mjs";

test("buildScene normalizes scene nodes deterministically", () => {
  const nodes = [
    {
      id: 42,
      kind: "rect",
      bounds: { x: "4", y: null, width: "5.5", height: "nope" },
      props: { fill: "#fff" },
      children: [
        {
          id: "child",
          kind: "rect",
          bounds: { x: 1, y: 2, width: 3, height: 4 }
        }
      ]
    }
  ];

  const scene = buildScene(nodes, { rootId: 7 });
  const repeat = buildScene(nodes, { rootId: 7 });

  assert.equal(scene.id, "7");
  assert.deepEqual(scene, repeat);
  assert.equal(scene.children.length, 1);

  const rect = scene.children[0];
  assert.equal(rect.id, "42");
  assert.deepEqual(rect.bounds, { x: 4, y: 0, width: 5.5, height: 0 });
  assert.equal(rect.children.length, 1);
  assert.deepEqual(rect.children[0].bounds, { x: 1, y: 2, width: 3, height: 4 });
});
