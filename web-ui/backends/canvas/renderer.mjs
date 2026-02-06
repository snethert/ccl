import {
  buildScene,
  hitTestScene,
  normalizeBounds,
  coalesceBounds,
  collectBoundsById,
  boundsIntersect,
  flattenScene
} from "./scene.mjs";
import { createMeasureCache } from "./measure.mjs";

const DEFAULT_FONT = "12px monospace";

function normalizePoint(point) {
  const x = Number(point?.x ?? 0);
  const y = Number(point?.y ?? 0);
  return { x: Number.isFinite(x) ? x : 0, y: Number.isFinite(y) ? y : 0 };
}

function drawNode(ctx, node) {
  if (node.kind === "group") {
    for (const child of node.children ?? []) {
      drawNode(ctx, child);
    }
    return;
  }
  if (node.kind === "rect") {
    const { x, y, width, height } = node.bounds;
    if (node.props?.fill) {
      ctx.fillStyle = node.props.fill;
      ctx.fillRect(x, y, width, height);
    }
    if (node.props?.stroke) {
      ctx.strokeStyle = node.props.stroke;
      ctx.strokeRect(x, y, width, height);
    }
    return;
  }
  if (node.kind === "text") {
    const { x, y } = node.bounds;
    ctx.font = node.props?.font ?? DEFAULT_FONT;
    ctx.fillStyle = node.props?.fill ?? "#000";
    ctx.fillText(String(node.props?.text ?? ""), x, y);
    return;
  }
  if (node.kind === "path") {
    if (typeof node.props?.path === "function") {
      ctx.save();
      node.props.path(ctx);
      if (node.props?.fill) {
        ctx.fillStyle = node.props.fill;
        ctx.fill();
      }
      if (node.props?.stroke) {
        ctx.strokeStyle = node.props.stroke;
        ctx.stroke();
      }
      ctx.restore();
    }
  }
}

function drawScene(ctx, scene, options = {}) {
  const width = options.width ?? ctx.canvas?.width ?? 0;
  const height = options.height ?? ctx.canvas?.height ?? 0;
  ctx.clearRect(0, 0, width, height);
  drawNode(ctx, scene);
}

function buildDrawList(scene) {
  const nodes = flattenScene(scene);
  const drawList = [];
  for (const node of nodes) {
    if (node.kind === "group") continue;
    const bounds = normalizeBounds(node.bounds ?? {});
    drawList.push({
      node,
      bounds: bounds.width > 0 && bounds.height > 0 ? bounds : null
    });
  }
  return drawList;
}

function shouldDrawEntry(entry, clipRect) {
  if (!clipRect || !entry.bounds) return true;
  return boundsIntersect(entry.bounds, clipRect);
}

function drawSceneDirty(ctx, drawList, rects = [], options = {}) {
  if (!rects.length) {
    drawScene(ctx, options.scene, options);
    return;
  }
  for (const rect of rects) {
    ctx.save();
    ctx.beginPath();
    ctx.rect(rect.x, rect.y, rect.width, rect.height);
    ctx.clip();
    ctx.clearRect(rect.x, rect.y, rect.width, rect.height);
    for (const entry of drawList) {
      if (!shouldDrawEntry(entry, rect)) {
        continue;
      }
      drawNode(ctx, entry.node);
    }
    ctx.restore();
  }
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

export function createCanvasBackend({ canvas, document: doc, onMeasureTextCacheMiss } = {}) {
  if (!canvas) {
    throw new Error("Canvas element is required");
  }
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    throw new Error("Canvas 2D context is required");
  }
  const measureCache = createMeasureCache((text, options) => {
    ctx.font = options.font ?? DEFAULT_FONT;
    const metrics = ctx.measureText(String(text ?? ""));
    const fontSizeMatch = String(options.font ?? DEFAULT_FONT).match(/(\d+(?:\.\d+)?)px/);
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
      if (scene !== undefined) {
        currentScene = Array.isArray(scene) ? buildScene(scene) : scene ?? buildScene([]);
      }
      const activeScene = currentScene ?? buildScene([]);
      const dirtyRects = computeDirtyRects(activeScene, options);
      if (dirtyRects.length === 0) {
        drawScene(ctx, activeScene, { width: canvas.width, height: canvas.height });
        return;
      }
      const drawList = buildDrawList(activeScene);
      drawSceneDirty(ctx, drawList, dirtyRects, {
        width: canvas.width,
        height: canvas.height,
        scene: activeScene
      });
    },
    hitTest(point) {
      return hitTestScene(currentScene, normalizePoint(point));
    },
    measureText(text, options = {}) {
      const result = measureCache.measureText(text, options);
      if (!result.cacheHit && typeof onMeasureTextCacheMiss === "function") {
        onMeasureTextCacheMiss({ text, font: options.font ?? DEFAULT_FONT });
      }
      return result;
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

export function createCanvasRoot(canvas, options = {}) {
  const backend = createCanvasBackend({ canvas, document: options.document, onMeasureTextCacheMiss: options.onCacheMiss });
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
    invalidate(callback) {
      return backend.invalidate(callback);
    },
    getScene() {
      return backend.getScene();
    }
  };
}
