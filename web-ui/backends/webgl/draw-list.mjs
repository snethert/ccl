import { flattenScene, normalizeBounds, boundsIntersect } from "../canvas/scene.mjs";

const DEFAULT_COLOR = [0, 0, 0, 1];

function clamp01(value) {
  if (!Number.isFinite(value)) return 0;
  if (value < 0) return 0;
  if (value > 1) return 1;
  return value;
}

function normalizeChannel(value) {
  if (!Number.isFinite(value)) return 0;
  if (value > 1) {
    return clamp01(value / 255);
  }
  return clamp01(value);
}

function parseHexColor(hex) {
  const clean = hex.replace("#", "").trim();
  if (clean.length === 3) {
    const r = parseInt(clean[0] + clean[0], 16);
    const g = parseInt(clean[1] + clean[1], 16);
    const b = parseInt(clean[2] + clean[2], 16);
    return [r / 255, g / 255, b / 255, 1];
  }
  if (clean.length === 6 || clean.length === 8) {
    const r = parseInt(clean.slice(0, 2), 16);
    const g = parseInt(clean.slice(2, 4), 16);
    const b = parseInt(clean.slice(4, 6), 16);
    const a = clean.length === 8 ? parseInt(clean.slice(6, 8), 16) / 255 : 1;
    return [r / 255, g / 255, b / 255, clamp01(a)];
  }
  return DEFAULT_COLOR;
}

function parseRgbColor(match) {
  const parts = match[1].split(",").map((entry) => entry.trim());
  if (parts.length < 3) return DEFAULT_COLOR;
  const r = normalizeChannel(Number.parseFloat(parts[0]));
  const g = normalizeChannel(Number.parseFloat(parts[1]));
  const b = normalizeChannel(Number.parseFloat(parts[2]));
  const a = parts.length >= 4 ? normalizeChannel(Number.parseFloat(parts[3])) : 1;
  return [r, g, b, a];
}

export function parseWebGLColor(value) {
  if (!value) return DEFAULT_COLOR;
  if (Array.isArray(value)) {
    const [r, g, b, a = 1] = value;
    return [normalizeChannel(r), normalizeChannel(g), normalizeChannel(b), normalizeChannel(a)];
  }
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (trimmed.startsWith("#")) {
      return parseHexColor(trimmed);
    }
    const rgbMatch = trimmed.match(/^rgba?\((.+)\)$/i);
    if (rgbMatch) {
      return parseRgbColor(rgbMatch);
    }
  }
  return DEFAULT_COLOR;
}

function rectToTriangles(bounds) {
  const x1 = bounds.x;
  const y1 = bounds.y;
  const x2 = bounds.x + bounds.width;
  const y2 = bounds.y + bounds.height;
  return [
    x1, y1, x2, y1, x1, y2,
    x1, y2, x2, y1, x2, y2
  ];
}

function shouldInclude(bounds, clipRect) {
  if (!bounds || bounds.width <= 0 || bounds.height <= 0) return false;
  if (!clipRect) return true;
  return boundsIntersect(bounds, clipRect);
}

export function buildWebGLDrawList(scene, options = {}) {
  const nodes = flattenScene(scene);
  const clipRect = options.clipRect ? normalizeBounds(options.clipRect ?? {}) : null;
  const positions = [];
  const colors = [];

  for (const node of nodes) {
    if (node.kind !== "rect") {
      continue;
    }
    const bounds = normalizeBounds(node.bounds ?? {});
    if (!shouldInclude(bounds, clipRect)) {
      continue;
    }
    const color = parseWebGLColor(node.props?.fill ?? node.props?.color ?? "#000");
    const vertices = rectToTriangles(bounds);
    for (let i = 0; i < vertices.length; i += 2) {
      positions.push(vertices[i], vertices[i + 1]);
      colors.push(color[0], color[1], color[2], color[3]);
    }
  }

  return {
    positions: new Float32Array(positions),
    colors: new Float32Array(colors),
    count: positions.length / 2
  };
}
