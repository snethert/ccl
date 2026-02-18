import { allocateId } from "./ids.mjs";

const DEFAULT_AXIS = "h";
const DEFAULT_REGION = "left";

function ensureLayoutCounter(counters) {
  const safe = counters ?? {};
  const current = Number.isInteger(safe.layout) ? safe.layout : 0;
  return { ...safe, layout: current };
}

function bumpLayoutCounter(counters, ids = []) {
  let next = Number.isInteger(counters?.layout) ? counters.layout : 0;
  for (const id of ids) {
    const match = /^layout-(\d+)$/.exec(id);
    if (!match) continue;
    const value = Number.parseInt(match[1], 10);
    if (Number.isFinite(value)) {
      next = Math.max(next, value + 1);
    }
  }
  return { ...counters, layout: next };
}

function normalizeSplitWeights(count, weights, ratio = null) {
  if (Array.isArray(weights) && weights.length === count) {
    return weights.map((value) => Number(value));
  }
  if (count === 2 && typeof ratio === "number" && Number.isFinite(ratio)) {
    const first = Math.max(0, Math.min(1, ratio));
    return [first, 1 - first];
  }
  if (count <= 0) return [];
  const value = 1 / count;
  return Array(count).fill(value);
}

function normalizeLayoutNode(node) {
  const kind = node.kind ?? "leaf";
  const children = Array.isArray(node.children) ? node.children.map(String) : [];
  const props = { ...(node.props ?? {}) };

  if (kind === "split") {
    props.axis = props.axis === "v" ? "v" : DEFAULT_AXIS;
    props.weights = normalizeSplitWeights(children.length, props.weights, props.ratio);
    delete props.ratio;
  }

  if (kind === "tabs") {
    const activeId = props.activeId ?? (children.length > 0 ? children[0] : null);
    props.activeId = activeId ?? null;
  }

  if (kind === "dock") {
    props.region = props.region ?? DEFAULT_REGION;
  }

  if (kind === "leaf") {
    props.windowId = props.windowId ?? null;
  }

  return {
    id: String(node.id),
    kind,
    children,
    props
  };
}

function cloneLayout(layout) {
  const nodes = {};
  for (const [id, node] of Object.entries(layout.nodes ?? {})) {
    nodes[id] = {
      id: node.id,
      kind: node.kind,
      children: Array.isArray(node.children) ? [...node.children] : [],
      props: { ...(node.props ?? {}) }
    };
  }
  return { rootId: layout.rootId ?? null, nodes };
}

function buildLayoutTree(spec, counters) {
  const alloc = spec.id ? { id: String(spec.id), counters } : allocateId(counters, "layout");
  let nextCounters = alloc.counters;
  const kind = spec.kind ?? spec.type ?? "leaf";
  const props = { ...(spec.props ?? {}) };

  if (kind === "leaf" && spec.windowId !== undefined) {
    props.windowId = spec.windowId;
  }
  if (kind === "split") {
    props.axis = spec.axis ?? props.axis;
    props.weights = spec.weights ?? props.weights;
    props.ratio = spec.ratio ?? props.ratio;
  }
  if (kind === "tabs" && spec.activeId) {
    props.activeId = spec.activeId;
  }
  if (kind === "dock" && spec.region) {
    props.region = spec.region;
  }

  const nodes = {};
  const children = [];
  if (Array.isArray(spec.children)) {
    for (const child of spec.children) {
      if (child && typeof child === "object") {
        const built = buildLayoutTree(child, nextCounters);
        nextCounters = built.counters;
        Object.assign(nodes, built.nodes);
        children.push(built.rootId);
      } else if (child !== null && child !== undefined) {
        const leafSpec = { kind: "leaf", windowId: child };
        const built = buildLayoutTree(leafSpec, nextCounters);
        nextCounters = built.counters;
        Object.assign(nodes, built.nodes);
        children.push(built.rootId);
      }
    }
  }

  const normalized = normalizeLayoutNode({
    id: alloc.id,
    kind,
    children,
    props
  });
  nodes[normalized.id] = normalized;
  return { rootId: normalized.id, nodes, counters: nextCounters };
}

function findParent(layout, childId) {
  for (const [id, node] of Object.entries(layout.nodes ?? {})) {
    const index = node.children?.indexOf(childId);
    if (index !== undefined && index !== -1) {
      return { parentId: id, index };
    }
  }
  return null;
}

function replaceChildId(children, fromId, toId) {
  const next = [...children];
  const index = next.indexOf(fromId);
  if (index !== -1) {
    next[index] = toId;
  }
  return next;
}

export function normalizeLayout(layout, counters) {
  const ensured = ensureLayoutCounter(counters ?? {});
  if (!layout) {
    return { layout: null, counters: ensured };
  }

  if (layout.rootId && layout.nodes) {
    const nodes = {};
    for (const [id, node] of Object.entries(layout.nodes)) {
      nodes[id] = normalizeLayoutNode({ ...node, id: node.id ?? id });
    }
    const rootId = nodes[layout.rootId] ? layout.rootId : Object.keys(nodes)[0] ?? null;
    const bumped = bumpLayoutCounter(ensured, Object.keys(nodes));
    return { layout: { rootId, nodes }, counters: bumped };
  }

  const spec = layout.root ?? layout;
  const built = buildLayoutTree(spec, ensured);
  const bumped = bumpLayoutCounter(built.counters, Object.keys(built.nodes));
  return { layout: { rootId: built.rootId, nodes: built.nodes }, counters: bumped };
}

export function createLayout(rootSpec, counters) {
  return normalizeLayout({ root: rootSpec }, counters);
}

export function repairLayout(layout, windows = {}) {
  if (!layout || !layout.nodes) return null;
  const nodes = {};
  for (const [id, node] of Object.entries(layout.nodes)) {
    nodes[id] = {
      id: node.id,
      kind: node.kind,
      children: Array.isArray(node.children) ? [...node.children] : [],
      props: { ...(node.props ?? {}) }
    };
  }
  const validWindows = new Set(Object.keys(windows ?? {}));

  function prune(nodeId) {
    const node = nodes[nodeId];
    if (!node) return null;
    if (node.kind === "leaf") {
      const windowId = node.props?.windowId ?? null;
      if (windowId && !validWindows.has(windowId)) {
        delete nodes[nodeId];
        return null;
      }
      return nodeId;
    }
    const nextChildren = [];
    for (const childId of node.children ?? []) {
      const kept = prune(childId);
      if (kept) nextChildren.push(kept);
    }
    if (nextChildren.length === 0) {
      delete nodes[nodeId];
      return null;
    }
    const props = { ...(node.props ?? {}) };
    if (node.kind === "split") {
      props.weights = normalizeSplitWeights(nextChildren.length, props.weights, props.ratio);
      delete props.ratio;
    }
    if (node.kind === "tabs") {
      props.activeId = nextChildren.includes(props.activeId) ? props.activeId : nextChildren[0] ?? null;
    }
    nodes[nodeId] = normalizeLayoutNode({ ...node, children: nextChildren, props });
    return nodeId;
  }

  let rootId = prune(layout.rootId);
  if (!rootId) {
    rootId = Object.keys(nodes)[0] ?? null;
  }
  if (!rootId) return null;
  return { rootId, nodes };
}

export function splitLayoutNode(layout, counters, targetId, axis = "h", ratio = 0.5, options = {}) {
  const normalized = normalizeLayout(layout, counters);
  if (!normalized.layout) {
    throw new Error("Layout is required");
  }
  const parent = findParent(normalized.layout, targetId);
  const nextLayout = cloneLayout(normalized.layout);
  const target = nextLayout.nodes[targetId];
  if (!target) {
    throw new Error(`Unknown layout node: ${targetId}`);
  }
  if (target.kind !== "leaf") {
    throw new Error(`Split target must be a leaf: ${targetId}`);
  }

  let nextCounters = normalized.counters;
  const newLeafAlloc = allocateId(nextCounters, "layout");
  nextCounters = newLeafAlloc.counters;
  const splitAlloc = allocateId(nextCounters, "layout");
  nextCounters = splitAlloc.counters;

  const newLeafId = newLeafAlloc.id;
  const splitId = splitAlloc.id;

  nextLayout.nodes[newLeafId] = normalizeLayoutNode({
    id: newLeafId,
    kind: "leaf",
    children: [],
    props: { windowId: options.windowId ?? null }
  });

  const insert = options.insert === "before" ? "before" : "after";
  const children = insert === "before" ? [newLeafId, targetId] : [targetId, newLeafId];
  nextLayout.nodes[splitId] = normalizeLayoutNode({
    id: splitId,
    kind: "split",
    children,
    props: { axis, ratio }
  });

  if (parent) {
    const parentNode = nextLayout.nodes[parent.parentId];
    nextLayout.nodes[parent.parentId] = normalizeLayoutNode({
      ...parentNode,
      children: replaceChildId(parentNode.children ?? [], targetId, splitId)
    });
  } else {
    nextLayout.rootId = splitId;
  }

  const bumped = bumpLayoutCounter(nextCounters, Object.keys(nextLayout.nodes));
  return { layout: nextLayout, counters: bumped };
}

export function wrapInTabsNode(layout, counters, targetId, options = {}) {
  const normalized = normalizeLayout(layout, counters);
  if (!normalized.layout) {
    throw new Error("Layout is required");
  }
  const parent = findParent(normalized.layout, targetId);
  const nextLayout = cloneLayout(normalized.layout);
  const target = nextLayout.nodes[targetId];
  if (!target) {
    throw new Error(`Unknown layout node: ${targetId}`);
  }

  let nextCounters = normalized.counters;
  let newTabId = null;
  if (options.newTab) {
    const newLeafAlloc = allocateId(nextCounters, "layout");
    nextCounters = newLeafAlloc.counters;
    newTabId = newLeafAlloc.id;
    nextLayout.nodes[newTabId] = normalizeLayoutNode({
      id: newTabId,
      kind: "leaf",
      children: [],
      props: { windowId: options.newTab.windowId ?? null }
    });
  }

  const tabsAlloc = allocateId(nextCounters, "layout");
  nextCounters = tabsAlloc.counters;
  const tabsId = tabsAlloc.id;

  const insert = options.insert === "before" ? "before" : "after";
  const children = [targetId];
  if (newTabId) {
    if (insert === "before") {
      children.unshift(newTabId);
    } else {
      children.push(newTabId);
    }
  }

  const activeId = options.activeId ?? (options.activateNew && newTabId ? newTabId : targetId);
  nextLayout.nodes[tabsId] = normalizeLayoutNode({
    id: tabsId,
    kind: "tabs",
    children,
    props: { activeId }
  });

  if (parent) {
    const parentNode = nextLayout.nodes[parent.parentId];
    nextLayout.nodes[parent.parentId] = normalizeLayoutNode({
      ...parentNode,
      children: replaceChildId(parentNode.children ?? [], targetId, tabsId)
    });
  } else {
    nextLayout.rootId = tabsId;
  }

  const bumped = bumpLayoutCounter(nextCounters, Object.keys(nextLayout.nodes));
  return { layout: nextLayout, counters: bumped };
}

export function setActiveTabNode(layout, counters, tabsId, tabId) {
  const normalized = normalizeLayout(layout, counters);
  if (!normalized.layout) {
    throw new Error("Layout is required");
  }
  const nextLayout = cloneLayout(normalized.layout);
  const tabs = nextLayout.nodes[tabsId];
  if (!tabs || tabs.kind !== "tabs") {
    throw new Error(`Unknown tabs node: ${tabsId}`);
  }
  if (!tabs.children.includes(tabId)) {
    throw new Error(`Tab ${tabId} not found in ${tabsId}`);
  }
  nextLayout.nodes[tabsId] = normalizeLayoutNode({
    ...tabs,
    props: { ...(tabs.props ?? {}), activeId: tabId }
  });
  return { layout: nextLayout, counters: normalized.counters };
}

export function dockLayoutNode(layout, counters, targetId, region = DEFAULT_REGION) {
  const normalized = normalizeLayout(layout, counters);
  if (!normalized.layout) {
    throw new Error("Layout is required");
  }
  const parent = findParent(normalized.layout, targetId);
  const nextLayout = cloneLayout(normalized.layout);
  if (!nextLayout.nodes[targetId]) {
    throw new Error(`Unknown layout node: ${targetId}`);
  }

  let nextCounters = normalized.counters;
  const dockAlloc = allocateId(nextCounters, "layout");
  nextCounters = dockAlloc.counters;
  const dockId = dockAlloc.id;

  nextLayout.nodes[dockId] = normalizeLayoutNode({
    id: dockId,
    kind: "dock",
    children: [targetId],
    props: { region }
  });

  if (parent) {
    const parentNode = nextLayout.nodes[parent.parentId];
    nextLayout.nodes[parent.parentId] = normalizeLayoutNode({
      ...parentNode,
      children: replaceChildId(parentNode.children ?? [], targetId, dockId)
    });
  } else {
    nextLayout.rootId = dockId;
  }

  const bumped = bumpLayoutCounter(nextCounters, Object.keys(nextLayout.nodes));
  return { layout: nextLayout, counters: bumped };
}
