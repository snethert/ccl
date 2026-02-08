import { buildScene, hitTestScene, normalizeBounds, coalesceBounds, collectBoundsById } from "../canvas/scene.mjs";
import { createMeasureCache } from "../canvas/measure.mjs";
import { buildWebGLDrawList, parseWebGLColor } from "./draw-list.mjs";
import { normalizeThemeTokens, resolveFontString } from "../../src/theme.mjs";

const DEFAULT_FONT = "12px monospace";

const VERTEX_SHADER = `
attribute vec2 a_position;
attribute vec4 a_color;
uniform vec2 u_resolution;
varying vec4 v_color;
void main() {
  vec2 zeroToOne = a_position / u_resolution;
  vec2 zeroToTwo = zeroToOne * 2.0;
  vec2 clip = zeroToTwo - 1.0;
  gl_Position = vec4(clip * vec2(1.0, -1.0), 0.0, 1.0);
  v_color = a_color;
}
`;

const FRAGMENT_SHADER = `
precision mediump float;
varying vec4 v_color;
void main() {
  gl_FragColor = v_color;
}
`;

function getWebGLContext(canvas) {
  if (!canvas?.getContext) return null;
  return canvas.getContext("webgl") || canvas.getContext("experimental-webgl") || null;
}

function compileShader(gl, type, source) {
  const shader = gl.createShader(type);
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    const info = gl.getShaderInfoLog(shader) || "unknown";
    gl.deleteShader(shader);
    throw new Error(`WebGL shader compile failed: ${info}`);
  }
  return shader;
}

function createProgram(gl, vsSource, fsSource) {
  const vs = compileShader(gl, gl.VERTEX_SHADER, vsSource);
  const fs = compileShader(gl, gl.FRAGMENT_SHADER, fsSource);
  const program = gl.createProgram();
  gl.attachShader(program, vs);
  gl.attachShader(program, fs);
  gl.linkProgram(program);
  gl.deleteShader(vs);
  gl.deleteShader(fs);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    const info = gl.getProgramInfoLog(program) || "unknown";
    gl.deleteProgram(program);
    throw new Error(`WebGL program link failed: ${info}`);
  }
  return program;
}

function normalizePoint(point) {
  const x = Number(point?.x ?? 0);
  const y = Number(point?.y ?? 0);
  return { x: Number.isFinite(x) ? x : 0, y: Number.isFinite(y) ? y : 0 };
}

function computeDirtyRects(scene, options = {}) {
  const rects = [];
  if (Array.isArray(options.dirty)) {
    for (const bounds of options.dirty) {
      rects.push(normalizeBounds(bounds ?? {}));
    }
  }
  if (Array.isArray(options.dirtyRects)) {
    for (const bounds of options.dirtyRects) {
      rects.push(normalizeBounds(bounds ?? {}));
    }
  }
  if (Array.isArray(options.dirtyNodes)) {
    for (const node of options.dirtyNodes) {
      rects.push(normalizeBounds(node?.bounds ?? {}));
    }
  }
  if (Array.isArray(options.dirtyIds)) {
    rects.push(...collectBoundsById(scene, options.dirtyIds));
  }
  if (rects.length === 0) {
    return [];
  }
  return coalesceBounds(rects);
}

function drawList(gl, draw, buffers, locations) {
  if (!draw || draw.count === 0) return;
  gl.bindBuffer(gl.ARRAY_BUFFER, buffers.position);
  gl.bufferData(gl.ARRAY_BUFFER, draw.positions, gl.STATIC_DRAW);
  gl.enableVertexAttribArray(locations.position);
  gl.vertexAttribPointer(locations.position, 2, gl.FLOAT, false, 0, 0);

  gl.bindBuffer(gl.ARRAY_BUFFER, buffers.color);
  gl.bufferData(gl.ARRAY_BUFFER, draw.colors, gl.STATIC_DRAW);
  gl.enableVertexAttribArray(locations.color);
  gl.vertexAttribPointer(locations.color, 4, gl.FLOAT, false, 0, 0);

  gl.drawArrays(gl.TRIANGLES, 0, draw.count);
}

function toScissorRect(rect, height) {
  const x = rect.x;
  const y = height - rect.y - rect.height;
  return {
    x: Math.max(0, Math.floor(x)),
    y: Math.max(0, Math.floor(y)),
    width: Math.max(0, Math.ceil(rect.width)),
    height: Math.max(0, Math.ceil(rect.height))
  };
}

function createMeasureContext(doc) {
  if (doc?.createElement) {
    const canvas = doc.createElement("canvas");
    return canvas.getContext("2d");
  }
  if (typeof OffscreenCanvas !== "undefined") {
    const canvas = new OffscreenCanvas(1, 1);
    return canvas.getContext("2d");
  }
  return null;
}

export function createWebGLBackend({ canvas, document: doc, onMeasureTextCacheMiss } = {}) {
  if (!canvas) {
    throw new Error("Canvas element is required");
  }
  const gl = getWebGLContext(canvas);
  if (!gl) {
    throw new Error("WebGL context is required");
  }

  const program = createProgram(gl, VERTEX_SHADER, FRAGMENT_SHADER);
  const positionLocation = gl.getAttribLocation(program, "a_position");
  const colorLocation = gl.getAttribLocation(program, "a_color");
  const resolutionLocation = gl.getUniformLocation(program, "u_resolution");
  const positionBuffer = gl.createBuffer();
  const colorBuffer = gl.createBuffer();

  gl.useProgram(program);
  gl.enable(gl.BLEND);
  gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

  const measureCtx = createMeasureContext(doc);
  let defaultFont = DEFAULT_FONT;
  let defaultBackground = null;

  function applyTheme(theme) {
    if (!theme) {
      defaultFont = DEFAULT_FONT;
      defaultBackground = null;
      return;
    }
    const tokens = normalizeThemeTokens(theme);
    defaultFont = resolveFontString(tokens, { mono: true });
    defaultBackground = tokens.color?.bg ?? null;
  }

  const measureCache = createMeasureCache((text, options) => {
    if (!measureCtx) {
      return { width: 0, height: 0, ascent: 0, descent: 0 };
    }
    measureCtx.font = options.font ?? defaultFont;
    const metrics = measureCtx.measureText(String(text ?? ""));
    const fontSizeMatch = String(options.font ?? defaultFont).match(/(\d+(?:\.\d+)?)px/);
    const fontSize = fontSizeMatch ? Number.parseFloat(fontSizeMatch[1]) : 12;
    const ascent = metrics.actualBoundingBoxAscent ?? fontSize * 0.8;
    const descent = metrics.actualBoundingBoxDescent ?? fontSize * 0.2;
    return {
      width: metrics.width,
      height: ascent + descent,
      ascent,
      descent
    };
  });

  let currentScene = buildScene([]);
  const viewRef = doc?.defaultView ?? globalThis;

  return {
    render(scene, options = {}) {
      if (Object.prototype.hasOwnProperty.call(options, "theme")) {
        applyTheme(options.theme);
      }
      const background = options.background ?? defaultBackground;
      const clearColor = background ? parseWebGLColor(background) : [0, 0, 0, 0];
      if (scene !== undefined) {
        currentScene = Array.isArray(scene) ? buildScene(scene) : scene ?? buildScene([]);
      }
      const activeScene = currentScene ?? buildScene([]);
      const dirtyRects = computeDirtyRects(activeScene, options);
      const width = canvas.width;
      const height = canvas.height;

      gl.useProgram(program);
      gl.viewport(0, 0, width, height);
      gl.uniform2f(resolutionLocation, width, height);

      const buffers = { position: positionBuffer, color: colorBuffer };
      const locations = { position: positionLocation, color: colorLocation };

      if (dirtyRects.length === 0) {
        gl.disable(gl.SCISSOR_TEST);
        gl.clearColor(clearColor[0], clearColor[1], clearColor[2], clearColor[3]);
        gl.clear(gl.COLOR_BUFFER_BIT);
        const draw = buildWebGLDrawList(activeScene);
        drawList(gl, draw, buffers, locations);
        return;
      }

      gl.enable(gl.SCISSOR_TEST);
      for (const rect of dirtyRects) {
        const scissor = toScissorRect(rect, height);
        gl.scissor(scissor.x, scissor.y, scissor.width, scissor.height);
        gl.clearColor(clearColor[0], clearColor[1], clearColor[2], clearColor[3]);
        gl.clear(gl.COLOR_BUFFER_BIT);
        const draw = buildWebGLDrawList(activeScene, { clipRect: rect });
        drawList(gl, draw, buffers, locations);
      }
      gl.disable(gl.SCISSOR_TEST);
    },
    hitTest(point) {
      return hitTestScene(currentScene, normalizePoint(point));
    },
    measureText(text, options = {}) {
      const font = options.font ?? defaultFont;
      const result = measureCache.measureText(text, { ...options, font });
      if (!result.cacheHit && typeof onMeasureTextCacheMiss === "function") {
        onMeasureTextCacheMiss({ text, font });
      }
      return result;
    },
    setTheme(theme) {
      applyTheme(theme);
    },
    captureEvents(target, handlers = {}, options = {}) {
      if (!target) return () => {};
      const capture = options.capture ?? true;
      const passive = options.passive ?? false;
      const entries = [];
      for (const [event, handler] of Object.entries(handlers)) {
        if (typeof handler !== "function") continue;
        const listener = (evt) => handler(evt);
        target.addEventListener(event, listener, { capture, passive });
        entries.push({ event, listener });
      }
      return () => {
        for (const entry of entries) {
          target.removeEventListener(entry.event, entry.listener, { capture });
        }
      };
    },
    invalidate(callback) {
      if (typeof callback !== "function") return () => {};
      if (typeof viewRef?.requestAnimationFrame !== "function") {
        const timeoutId = viewRef?.setTimeout
          ? viewRef.setTimeout(() => callback(), 0)
          : setTimeout(() => callback(), 0);
        return () => {
          if (viewRef?.clearTimeout) {
            viewRef.clearTimeout(timeoutId);
          } else {
            clearTimeout(timeoutId);
          }
        };
      }
      const handle = viewRef.requestAnimationFrame(() => callback());
      return () => {
        if (typeof viewRef.cancelAnimationFrame === "function") {
          viewRef.cancelAnimationFrame(handle);
        }
      };
    },
    getScene() {
      return currentScene;
    }
  };
}

export function createWebGLRoot(canvas, options = {}) {
  const backend = createWebGLBackend({ canvas, document: options.document, onMeasureTextCacheMiss: options.onCacheMiss });
  return {
    render(scene, opts) {
      backend.render(scene, opts);
    },
    hitTest(point) {
      return backend.hitTest(point);
    },
    measureText(text, opts) {
      return backend.measureText(text, opts);
    },
    setTheme(theme) {
      if (typeof backend.setTheme === "function") {
        backend.setTheme(theme);
      }
    },
    invalidate(callback) {
      return backend.invalidate(callback);
    },
    getScene() {
      return backend.getScene();
    }
  };
}
