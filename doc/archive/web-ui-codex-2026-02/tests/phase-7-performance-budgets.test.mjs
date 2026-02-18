import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createQualityCollector,
  createRoot,
  createElement,
  createText,
  createCanvasBackend
} from "../src/index.mjs";
import { createWebGLBackend } from "../backends/webgl/renderer.mjs";

function createMockBackend() {
  return {
    createElement(tag) {
      return { kind: "element", tag, props: {}, children: [] };
    },
    createText(text) {
      return { kind: "text", text };
    },
    appendChild(parent, child) {
      parent.children.push(child);
    },
    insertBefore(parent, child, anchor) {
      const current = parent.children.indexOf(child);
      if (current !== -1) parent.children.splice(current, 1);
      if (!anchor) {
        parent.children.push(child);
        return;
      }
      const anchorIndex = parent.children.indexOf(anchor);
      if (anchorIndex === -1) {
        parent.children.push(child);
        return;
      }
      parent.children.splice(anchorIndex, 0, child);
    },
    removeChild(parent, child) {
      const index = parent.children.indexOf(child);
      if (index >= 0) parent.children.splice(index, 1);
    },
    replaceChild(parent, next, prev) {
      const index = parent.children.indexOf(prev);
      if (index >= 0) parent.children[index] = next;
    },
    setText(node, text) {
      node.text = text;
    },
    setProp(node, name, value) {
      node.props[name] = value;
    },
    removeProp(node, name) {
      delete node.props[name];
    }
  };
}

function createCanvasStub() {
  const ctx = {
    canvas: { width: 120, height: 80 },
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
    width: 120,
    height: 80,
    getContext(kind) {
      if (kind === "2d") return ctx;
      return null;
    }
  };
  ctx.canvas = canvas;
  return { canvas };
}

function createWebGLStub() {
  const gl = {
    VERTEX_SHADER: 0x8b31,
    FRAGMENT_SHADER: 0x8b30,
    COMPILE_STATUS: 0x8b81,
    LINK_STATUS: 0x8b82,
    ARRAY_BUFFER: 0x8892,
    STATIC_DRAW: 0x88e4,
    TRIANGLES: 0x0004,
    BLEND: 0x0be2,
    SRC_ALPHA: 0x0302,
    ONE_MINUS_SRC_ALPHA: 0x0303,
    COLOR_BUFFER_BIT: 0x4000,
    SCISSOR_TEST: 0x0c11,
    createShader() {
      return {};
    },
    shaderSource() {},
    compileShader() {},
    getShaderParameter() {
      return true;
    },
    getShaderInfoLog() {
      return "";
    },
    createProgram() {
      return {};
    },
    attachShader() {},
    linkProgram() {},
    deleteShader() {},
    deleteProgram() {},
    getProgramParameter() {
      return true;
    },
    getProgramInfoLog() {
      return "";
    },
    getAttribLocation() {
      return 0;
    },
    getUniformLocation() {
      return {};
    },
    createBuffer() {
      return {};
    },
    useProgram() {},
    enable() {},
    blendFunc() {},
    bindBuffer() {},
    bufferData() {},
    enableVertexAttribArray() {},
    vertexAttribPointer() {},
    drawArrays() {},
    viewport() {},
    uniform2f() {},
    clearColor() {},
    clear() {},
    scissor() {},
    disable() {}
  };
  const canvas = {
    width: 160,
    height: 120,
    getContext(kind) {
      if (kind === "webgl" || kind === "experimental-webgl") {
        return gl;
      }
      return null;
    }
  };
  const measureCtx = {
    font: "",
    measureText() {
      return { width: 1, actualBoundingBoxAscent: 8, actualBoundingBoxDescent: 2 };
    }
  };
  const doc = {
    createElement() {
      return { getContext: () => measureCtx };
    }
  };
  return { canvas, doc };
}

test("phase-7 performance budgets evaluate deterministic pass/fail gates", () => {
  const passing = createQualityCollector();
  [8, 10, 12, 14, 15].forEach((durationMs) => passing.recordUiTurn({ durationMs }));
  passing.recordRender({ backend: "canvas", surface: "canvas", dirtyHintCount: 1, dirtyRectCount: 1, fullRedraw: false });
  passing.recordVirtualization({ widgetKind: "list", visibleCount: 4, expectedMaxVisible: 6 });
  passing.recordTranscript({ entryCount: 10000, recordingCount: 1, mode: "snapshot" });
  passing.recordReliability({ kind: "replay-run", deterministic: true, handled: true });

  const passReport = passing.evaluate();
  assert.equal(passReport.ok, true);
  assert.equal(passReport.failedChecks.length, 0);

  const failing = createQualityCollector();
  [12, 24, 48].forEach((durationMs) => failing.recordUiTurn({ durationMs }));
  failing.recordRender({ backend: "canvas", surface: "canvas", dirtyHintCount: 1, dirtyRectCount: 0, fullRedraw: true });
  failing.recordVirtualization({ widgetKind: "list", visibleCount: 10, expectedMaxVisible: 3 });
  failing.recordReliability({ kind: "runtime-fault", handled: true, message: "fault" });
  const failReport = failing.evaluate();

  assert.equal(failReport.ok, false);
  const failedIds = new Set(failReport.failedChecks.map((entry) => entry.id));
  assert.equal(failedIds.has("ui-turn-p99"), true);
  assert.equal(failedIds.has("render-no-full-redraw-with-dirty-hints"), true);
  assert.equal(failedIds.has("virtualization-visible-window-bounds"), true);
  assert.equal(failedIds.has("reliability-unhandled-runtime-faults"), true);
});

test("phase-7 performance budgets collect renderer root apply metrics", () => {
  const collector = createQualityCollector({ now: (() => {
    let tick = 0;
    return () => {
      tick += 2;
      return tick;
    };
  })() });
  const backend = createMockBackend();
  const container = backend.createElement("root");
  const root = createRoot(backend, container, { qualityCollector: collector });

  const treeA = createElement("div", { id: "root" }, [createText("A")], "root");
  const treeB = createElement("div", { id: "root", className: "patched" }, [createText("B")], "root");
  root.render(treeA);
  root.render(treeB);
  root.render(null);

  const operations = collector.snapshot().samples.renders.map((entry) => entry.operation);
  assert.equal(operations.includes("mount"), true);
  assert.equal(operations.includes("patch"), true);
  assert.equal(operations.includes("unmount"), true);
});

test("phase-7 performance budgets collect canvas and webgl dirty render metrics", () => {
  const collector = createQualityCollector();

  const canvasStub = createCanvasStub();
  const canvasBackend = createCanvasBackend({ canvas: canvasStub.canvas });
  canvasBackend.render(
    [{ id: "r1", kind: "rect", bounds: { x: 1, y: 1, width: 10, height: 10 }, props: { fill: "#f00" } }],
    { dirtyRects: [{ x: 0, y: 0, width: 20, height: 20 }], qualityCollector: collector }
  );

  const webglStub = createWebGLStub();
  const webglBackend = createWebGLBackend({ canvas: webglStub.canvas, document: webglStub.doc });
  webglBackend.render(
    [{ id: "r2", kind: "rect", bounds: { x: 2, y: 2, width: 8, height: 8 }, props: { fill: "#0f0" } }],
    { dirtyRects: [{ x: 0, y: 0, width: 20, height: 20 }], qualityCollector: collector }
  );

  const renderSamples = collector.snapshot().samples.renders.filter((entry) => entry.surface === "canvas" || entry.surface === "webgl");
  const canvasSample = renderSamples.find((entry) => entry.backend === "canvas");
  const webglSample = renderSamples.find((entry) => entry.backend === "webgl");
  assert.ok(canvasSample);
  assert.ok(webglSample);
  assert.equal(canvasSample.fullRedraw, false);
  assert.equal(webglSample.fullRedraw, false);
  assert.equal(canvasSample.dirtyRectCount > 0, true);
  assert.equal(webglSample.dirtyRectCount > 0, true);
});

