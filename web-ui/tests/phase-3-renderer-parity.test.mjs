import { test } from "node:test";
import assert from "node:assert/strict";

import { createCanvasBackend } from "../backends/canvas/renderer.mjs";
import { createWebGLBackend } from "../backends/webgl/renderer.mjs";

function createCanvasStub() {
  const calls = { clearRect: 0, fillRect: [], fillText: [] };
  const ctx = {
    canvas: { width: 200, height: 100 },
    font: "",
    fillStyle: "",
    strokeStyle: "",
    clearRect() {
      calls.clearRect += 1;
    },
    fillRect(x, y, width, height) {
      calls.fillRect.push({ x, y, width, height, color: this.fillStyle });
    },
    fillText(text, x, y) {
      calls.fillText.push({ text, x, y, color: this.fillStyle, font: this.font });
    },
    measureText(text) {
      return { width: String(text ?? "").length, actualBoundingBoxAscent: 8, actualBoundingBoxDescent: 2 };
    }
  };
  const canvas = {
    width: 200,
    height: 100,
    getContext(kind) {
      if (kind !== "2d") return null;
      return ctx;
    }
  };
  return { canvas, ctx, calls };
}

function createWebGLStub() {
  const calls = { clearColor: [] };
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
    clearColor(r, g, b, a) {
      calls.clearColor.push([r, g, b, a]);
    },
    clear() {},
    scissor() {},
    disable() {}
  };
  const canvas = {
    width: 200,
    height: 100,
    getContext(kind) {
      if (kind === "webgl" || kind === "experimental-webgl") {
        return gl;
      }
      return null;
    }
  };
  return { canvas, gl, calls };
}

test("phase-3 renderer parity: canvas uses theme background and font", () => {
  const { canvas, ctx, calls } = createCanvasStub();
  const backend = createCanvasBackend({ canvas });
  backend.render([], {
    theme: { mode: "dark", color: { bg: "#112233" }, font: { mono: "TestMono", size: { md: 13 } } }
  });
  assert.equal(calls.fillRect.length, 1);
  assert.equal(calls.fillRect[0].color, "#112233");

  backend.measureText("hi");
  assert.equal(ctx.font, "13px TestMono");
});

test("phase-3 renderer parity: webgl uses theme background and font", () => {
  const { canvas, calls } = createWebGLStub();
  const measureCtx = { font: "", measureText: () => ({ width: 1, actualBoundingBoxAscent: 8, actualBoundingBoxDescent: 2 }) };
  const doc = { createElement: () => ({ getContext: () => measureCtx }) };
  const backend = createWebGLBackend({ canvas, document: doc });

  backend.render([], {
    theme: { mode: "dark", color: { bg: "#112233" }, font: { mono: "TestMono", size: { md: 15 } } }
  });
  const lastClear = calls.clearColor[calls.clearColor.length - 1];
  assert.deepEqual(lastClear, [0x11 / 255, 0x22 / 255, 0x33 / 255, 1]);

  backend.measureText("hi");
  assert.equal(measureCtx.font, "15px TestMono");
});
