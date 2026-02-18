export function normalizeBounds(bounds = {}) {
  const x = Number(bounds.x ?? 0);
  const y = Number(bounds.y ?? 0);
  const width = Number(bounds.width ?? 0);
  const height = Number(bounds.height ?? 0);
  return {
    x: Number.isFinite(x) ? x : 0,
    y: Number.isFinite(y) ? y : 0,
    width: Number.isFinite(width) ? width : 0,
    height: Number.isFinite(height) ? height : 0
  };
}

export function boundsIntersect(a, b) {
  if (!a || !b) return false;
  return (
    a.x <= b.x + b.width &&
    a.x + a.width >= b.x &&
    a.y <= b.y + b.height &&
    a.y + a.height >= b.y
  );
}

export function mergeBounds(a, b) {
  if (!a) return normalizeBounds(b ?? {});
  if (!b) return normalizeBounds(a ?? {});
  const left = Math.min(a.x, b.x);
  const top = Math.min(a.y, b.y);
  const right = Math.max(a.x + a.width, b.x + b.width);
  const bottom = Math.max(a.y + a.height, b.y + b.height);
  return {
    x: left,
    y: top,
    width: right - left,
    height: bottom - top
  };
}

export function coalesceBounds(boundsList = []) {
  const rects = boundsList
    .map((bounds) => normalizeBounds(bounds ?? {}))
    .filter((bounds) => bounds.width > 0 && bounds.height > 0);

  const merged = [];
  for (const rect of rects) {
    let current = rect;
    for (let i = 0; i < merged.length; i += 1) {
      if (!boundsIntersect(merged[i], current)) {
        continue;
      }
      current = mergeBounds(merged[i], current);
      merged.splice(i, 1);
      i = -1;
    }
    merged.push(current);
  }

  merged.sort((a, b) => {
    if (a.y !== b.y) return a.y - b.y;
    if (a.x !== b.x) return a.x - b.x;
    if (a.width !== b.width) return a.width - b.width;
    return a.height - b.height;
  });
  return merged;
}

export function normalizeSceneNode(node) {
  if (!node || typeof node !== "object") {
    throw new Error("Scene node must be an object");
  }
  const kind = node.kind ?? "rect";
  const children = Array.isArray(node.children) ? node.children.map(normalizeSceneNode) : [];
  return {
    id: String(node.id ?? ""),
    kind,
    bounds: normalizeBounds(node.bounds),
    props: { ...(node.props ?? {}) },
    children
  };
}

export function buildScene(nodes = [], options = {}) {
  const children = Array.isArray(nodes) ? nodes.map(normalizeSceneNode) : [];
  return {
    id: String(options.rootId ?? "scene-root"),
    kind: "group",
    bounds: normalizeBounds(options.bounds ?? {}),
    props: { ...(options.props ?? {}) },
    children
  };
}

export function flattenScene(scene) {
  const out = [];
  function walk(node) {
    out.push(node);
    for (const child of node.children ?? []) {
      walk(child);
    }
  }
  walk(scene);
  return out;
}

export function collectBoundsById(scene, ids = []) {
  if (!scene || !Array.isArray(ids) || ids.length === 0) {
    return [];
  }
  const wanted = new Set(ids.map((id) => String(id)));
  const nodes = flattenScene(scene);
  const bounds = [];
  for (const node of nodes) {
    if (!wanted.has(String(node.id))) {
      continue;
    }
    bounds.push(normalizeBounds(node.bounds ?? {}));
  }
  return bounds;
}

function hitBounds(bounds, point) {
  if (!bounds) return false;
  return (
    point.x >= bounds.x &&
    point.y >= bounds.y &&
    point.x <= bounds.x + bounds.width &&
    point.y <= bounds.y + bounds.height
  );
}

export function hitTestScene(scene, point) {
  if (!scene) return null;
  const nodes = flattenScene(scene);
  for (let i = nodes.length - 1; i >= 0; i -= 1) {
    const node = nodes[i];
    if (node.kind === "group") continue;
    if (hitBounds(node.bounds, point)) {
      return node;
    }
  }
  return null;
}
