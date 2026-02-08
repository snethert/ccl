import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createState,
  addTask,
  addWindow,
  addWidget,
  enqueueUiSignal,
  beginUiTurn,
  advanceUiTurn,
  endUiTurn,
  createQualityCollector,
  createCanvasBackend
} from "../src/index.mjs";
import { renderWindow } from "../src/widgets.mjs";

function createCanvasStub() {
  const ctx = {
    canvas: { width: 160, height: 120 },
    clearRect() {},
    fillRect() {},
    strokeRect() {},
    fillText() {},
    save() {},
    restore() {},
    beginPath() {},
    rect() {},
    clip() {},
    measureText(text) {
      return {
        width: String(text ?? "").length,
        actualBoundingBoxAscent: 8,
        actualBoundingBoxDescent: 2
      };
    }
  };
  const canvas = {
    width: 160,
    height: 120,
    getContext(kind) {
      if (kind === "2d") return ctx;
      return null;
    }
  };
  ctx.canvas = canvas;
  return { canvas };
}

test("phase-7 integration quality gates pass for representative interaction flow", () => {
  let clock = 0;
  const now = () => {
    clock += 1;
    return clock;
  };
  const collector = createQualityCollector({ now });

  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = addWindow(state, { id: "win-1", taskId: "task-1", kind: "document" });
  state = addWidget(state, { id: "root", kind: "container", windowId: "win-1" });
  state = addWidget(state, {
    id: "list-1",
    kind: "list",
    parentId: "root",
    props: {
      virtual: true,
      rowHeight: 20,
      viewportHeight: 80,
      scrollTop: 40,
      overscan: 1,
      items: Array.from({ length: 200 }, (_, index) => ({ id: `item-${index}`, label: `Item ${index}` }))
    }
  });

  state = enqueueUiSignal(state, { type: "input:key", payload: { key: "Ctrl+Shift+P" } });
  state = beginUiTurn(state, { qualityCollector: collector, now });
  state = advanceUiTurn(state, "commands", { qualityCollector: collector, now });
  state = advanceUiTurn(state, "render", { qualityCollector: collector, now });
  state = endUiTurn(state, { qualityCollector: collector, now });

  const tree = renderWindow(state, "win-1", { qualityCollector: collector });
  assert.ok(tree);

  const canvasStub = createCanvasStub();
  const canvasBackend = createCanvasBackend({ canvas: canvasStub.canvas });
  canvasBackend.render(
    [{ id: "rect-1", kind: "rect", bounds: { x: 4, y: 4, width: 20, height: 20 }, props: { fill: "#f00" } }],
    { dirtyRects: [{ x: 0, y: 0, width: 30, height: 30 }], qualityCollector: collector }
  );

  collector.recordTranscript({
    entryCount: 10000,
    recordingCount: 1,
    truncatedEntries: 0,
    mode: "integration"
  });
  collector.recordReliability({
    kind: "replay-run",
    deterministic: true,
    handled: true,
    details: { flow: "phase-7-integration" }
  });

  const snapshot = collector.snapshot();
  assert.equal(snapshot.samples.uiTurns.length > 0, true);
  assert.equal(snapshot.samples.virtualization.length > 0, true);
  assert.equal(snapshot.samples.renders.length > 0, true);
  assert.equal(snapshot.samples.transcript.length > 0, true);
  assert.equal(snapshot.samples.reliability.length > 0, true);

  const report = collector.evaluate();
  assert.equal(report.ok, true);
  assert.equal(report.failedChecks.length, 0);
});

