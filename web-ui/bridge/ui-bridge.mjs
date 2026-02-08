import { createRoot } from "../src/renderer.mjs";
import { createDomBackend } from "../backends/dom/renderer.mjs";
import { createCanvasBackend } from "../backends/canvas/renderer.mjs";
import { createWebGLBackend } from "../backends/webgl/renderer.mjs";
import { decodeTree, encodeEvents, selectEvents, EVENT_TYPES } from "./codec.mjs";
import { normalizeThemeTokens, resolveFontString, themeToCssVars } from "../src/theme.mjs";
import { UI_STYLES, UI_STYLE_ID } from "../styles/ui.mjs";

const ERRNO = Object.freeze({
  E2BIG: 1,
  EINVAL: 28,
});

const POINTER_FLAGS = Object.freeze({
  down: 1,
  up: 2,
  move: 4,
  enter: 8,
  leave: 16,
  cancel: 32,
});

const KEY_FLAGS = Object.freeze({
  down: 1,
  up: 2,
});

function modifierBits(evt) {
  let bits = 0;
  if (evt.shiftKey) bits |= 1;
  if (evt.ctrlKey) bits |= 2;
  if (evt.altKey) bits |= 4;
  if (evt.metaKey) bits |= 8;
  return bits;
}

function pointerTypeId(pointerType) {
  switch (pointerType) {
  case "pen":
    return 1;
  case "touch":
    return 2;
  default:
    return 0;
  }
}

function findAttr(start, attr) {
  let node = start;
  while (node && node.getAttribute) {
    const value = node.getAttribute(attr);
    if (value) return value;
    node = node.parentElement;
  }
  return null;
}

function parseScenePayload(value) {
  if (!value) return [];
  if (typeof value !== "string") return [];
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed : [];
  } catch (_err) {
    return [];
  }
}

function scheduleRAF(fn) {
  if (typeof requestAnimationFrame === "function") {
    requestAnimationFrame(fn);
    return;
  }
  setTimeout(fn, 0);
}

export function createUiBridge({ container, document, theme, styles } = {}) {
  if (!container) {
    throw new Error("createUiBridge requires a container element");
  }
  const docRef = document ?? container.ownerDocument ?? null;
  const styleText = styles === false ? null : typeof styles === "string" ? styles : UI_STYLES;
  let currentTheme = normalizeThemeTokens(theme ?? null);
  const backend = createDomBackend({ document, container });
  const root = createRoot(backend, container, { schedule: scheduleRAF });
  const eventQueue = [];
  let wake = null;
  const viewRegistry = new Map();
  let syncScheduled = false;

  function ensureStyles() {
    if (!styleText || !docRef?.getElementById || !docRef?.createElement) return;
    const existing = docRef.getElementById(UI_STYLE_ID);
    if (existing) {
      if (existing.textContent !== styleText) {
        existing.textContent = styleText;
      }
      return;
    }
    const styleNode = docRef.createElement("style");
    styleNode.id = UI_STYLE_ID;
    styleNode.textContent = styleText;
    const target = docRef.head || docRef.body || docRef.documentElement || container;
    if (target?.appendChild) {
      target.appendChild(styleNode);
    }
  }

  function applyTheme(nextTheme = currentTheme) {
    currentTheme = normalizeThemeTokens(nextTheme ?? null);
    if (container?.classList) {
      container.classList.add("ui-root");
    } else if (container) {
      container.className = `${container.className ?? ""} ui-root`.trim();
    }
    if (container?.setAttribute) {
      container.setAttribute("data-ui-theme", currentTheme.mode);
      if (currentTheme.motion?.reduced) {
        container.setAttribute("data-motion", "reduced");
      } else {
        container.removeAttribute("data-motion");
      }
    }
    if (container?.style?.setProperty) {
      const vars = themeToCssVars(currentTheme);
      for (const [key, value] of Object.entries(vars)) {
        if (value === "" || value === null || value === undefined) {
          container.style.removeProperty(key);
        } else {
          container.style.setProperty(key, value);
        }
      }
    }
    for (const entry of viewRegistry.values()) {
      if (typeof entry.backend?.setTheme === "function") {
        entry.backend.setTheme(currentTheme);
      }
    }
  }

  ensureStyles();
  applyTheme(currentTheme);

  function ensureCanvasSize(canvas) {
    if (!canvas) return;
    const width = Number(canvas.width || 0);
    const height = Number(canvas.height || 0);
    if (width > 0 && height > 0) return;
    const rect = canvas.getBoundingClientRect();
    const dpr = container.ownerDocument?.defaultView?.devicePixelRatio ?? 1;
    const nextWidth = Math.max(1, Math.round(rect.width * dpr));
    const nextHeight = Math.max(1, Math.round(rect.height * dpr));
    if (nextWidth > 0 && nextHeight > 0) {
      canvas.width = nextWidth;
      canvas.height = nextHeight;
    }
  }

  function syncViews() {
    syncScheduled = false;
    const nodes = container.querySelectorAll("canvas[data-canvas-scene], canvas[data-webgl-scene]");
    const active = new Set();
    nodes.forEach((node) => {
      if (!(node instanceof HTMLCanvasElement)) return;
      active.add(node);
      const kind = node.hasAttribute("data-webgl-scene") ? "webgl" : "canvas";
      const sceneText = node.getAttribute(kind === "webgl" ? "data-webgl-scene" : "data-canvas-scene") ?? "";
      const viewId = node.getAttribute("data-view-id") || node.getAttribute("data-widget-id") || null;
      ensureCanvasSize(node);
      let entry = viewRegistry.get(node);
      if (!entry || entry.kind !== kind) {
        let backend = null;
        try {
          backend =
            kind === "webgl"
              ? createWebGLBackend({ canvas: node, document })
              : createCanvasBackend({ canvas: node, document });
        } catch (_err) {
          backend = null;
        }
        entry = { kind, backend, viewId: viewId ?? null, sceneText: "" };
        viewRegistry.set(node, entry);
      } else if (!entry.backend) {
        try {
          entry.backend =
            kind === "webgl"
              ? createWebGLBackend({ canvas: node, document })
              : createCanvasBackend({ canvas: node, document });
        } catch (_err) {
          entry.backend = null;
        }
      }
      entry.viewId = viewId ?? entry.viewId;
      if (entry.backend) {
        if (typeof entry.backend.setTheme === "function") {
          entry.backend.setTheme(currentTheme);
        }
        if (entry.sceneText !== sceneText) {
          entry.sceneText = sceneText;
          const scene = parseScenePayload(sceneText);
          entry.backend.render(scene, {
            theme: currentTheme,
            background: currentTheme.color?.bg ?? null
          });
        } else if (entry.backend.render) {
          entry.backend.render(undefined, {
            theme: currentTheme,
            background: currentTheme.color?.bg ?? null
          });
        }
      }
    });
    for (const [node] of viewRegistry.entries()) {
      if (!active.has(node)) {
        viewRegistry.delete(node);
      }
    }
  }

  function scheduleSync() {
    if (syncScheduled) return;
    syncScheduled = true;
    scheduleRAF(syncViews);
  }

  function findCanvasNode(start) {
    let node = start;
    while (node && node.getAttribute) {
      if (node.tagName === "CANVAS" && (node.hasAttribute("data-canvas-scene") || node.hasAttribute("data-webgl-scene"))) {
        return node;
      }
      node = node.parentElement;
    }
    return null;
  }

  function hitTestCanvas(evt) {
    const canvas = findCanvasNode(evt?.target);
    if (!canvas) return null;
    const entry = viewRegistry.get(canvas);
    if (!entry || typeof entry.backend?.hitTest !== "function") return null;
    const rect = canvas.getBoundingClientRect();
    if (!rect || rect.width === 0 || rect.height === 0) return null;
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const x = (evt.clientX ?? 0) - rect.left;
    const y = (evt.clientY ?? 0) - rect.top;
    const hit = entry.backend.hitTest({ x: x * scaleX, y: y * scaleY });
    if (!hit || !hit.id) return null;
    const viewId = entry.viewId;
    const targetId = viewId ? `${viewId}:${hit.id}` : String(hit.id);
    return { targetId };
  }

  function enqueueEvent(event) {
    eventQueue.push(event);
    if (typeof wake === "function") wake();
  }

  function pollEvents({ maxEvents = 0, maxBytes = 0, allowPending = false } = {}) {
    if (eventQueue.length === 0) {
      return allowPending ? { pending: true } : { payload: new Uint8Array(0), count: 0 };
    }
    const { events, overflow } = selectEvents(eventQueue, maxEvents, maxBytes);
    if (overflow) {
      return { error: ERRNO.E2BIG };
    }
    const res = encodeEvents(events);
    eventQueue.splice(0, events.length);
    return res;
  }

  function renderTree(payload) {
    try {
      const tree = decodeTree(payload);
      root.render(tree);
      scheduleSync();
      return 0;
    } catch (_err) {
      return -ERRNO.EINVAL;
    }
  }

  function measureText({ font, text } = {}) {
    const resolvedFont = font ?? resolveFontString(currentTheme, { mono: true });
    return backend.measureText(text ?? "", { font: resolvedFont });
  }

  function setWake(fn) {
    wake = typeof fn === "function" ? fn : null;
  }

  function resolveTargetIds(evt, options = {}) {
    const target = evt?.target ?? null;
    const windowId = findAttr(target, "data-window-id");
    let targetId = findAttr(target, "data-widget-id");
    if (options.useHitTest) {
      const hit = hitTestCanvas(evt);
      if (hit?.targetId) targetId = hit.targetId;
    }
    return { targetId, windowId };
  }

  function onPointer(evt, flag) {
    const { targetId, windowId } = resolveTargetIds(evt, { useHitTest: true });
    enqueueEvent({
      type: EVENT_TYPES.pointer,
      flags: flag,
      targetId,
      windowId,
      x: evt.clientX ?? 0,
      y: evt.clientY ?? 0,
      button: evt.button ?? 0,
      buttons: evt.buttons ?? 0,
      modifiers: modifierBits(evt),
      pointerType: pointerTypeId(evt.pointerType),
      clickCount: evt.detail ?? 0,
    });
  }

  function onKey(evt, flag) {
    const { targetId, windowId } = resolveTargetIds(evt);
    enqueueEvent({
      type: EVENT_TYPES.key,
      flags: flag,
      targetId,
      windowId,
      key: evt.key ?? "",
      code: evt.code ?? "",
      modifiers: modifierBits(evt),
      repeat: Boolean(evt.repeat),
      location: evt.location ?? 0,
      isComposing: Boolean(evt.isComposing),
      text: evt.key?.length === 1 ? evt.key : null,
    });
  }

  function onComposition(evt, phase) {
    const { targetId, windowId } = resolveTargetIds(evt);
    enqueueEvent({
      type: EVENT_TYPES.composition,
      flags: 0,
      targetId,
      windowId,
      phase,
      data: evt.data ?? "",
    });
  }

  function onText(evt) {
    const { targetId, windowId } = resolveTargetIds(evt);
    const data = typeof evt.data === "string" ? evt.data : "";
    if (!data) return;
    enqueueEvent({
      type: EVENT_TYPES.text,
      flags: 0,
      targetId,
      windowId,
      text: data,
    });
  }

  function onFocus(evt, typeId) {
    const { targetId, windowId } = resolveTargetIds(evt);
    enqueueEvent({
      type: typeId,
      flags: 0,
      targetId,
      windowId,
      relatedId: findAttr(evt.relatedTarget, "data-widget-id"),
    });
  }

  function onWheel(evt) {
    const { targetId, windowId } = resolveTargetIds(evt, { useHitTest: true });
    enqueueEvent({
      type: EVENT_TYPES.wheel,
      flags: 0,
      targetId,
      windowId,
      deltaX: evt.deltaX ?? 0,
      deltaY: evt.deltaY ?? 0,
      deltaMode: evt.deltaMode ?? 0,
      modifiers: modifierBits(evt),
    });
  }

  const listeners = [];
  const target = container;
  const doc = docRef;

  function add(targetNode, type, handler, options) {
    if (!targetNode?.addEventListener) return;
    targetNode.addEventListener(type, handler, options);
    listeners.push([targetNode, type, handler, options]);
  }

  add(target, "pointerdown", (e) => onPointer(e, POINTER_FLAGS.down));
  add(target, "pointerup", (e) => onPointer(e, POINTER_FLAGS.up));
  add(target, "pointermove", (e) => onPointer(e, POINTER_FLAGS.move));
  add(target, "pointerenter", (e) => onPointer(e, POINTER_FLAGS.enter));
  add(target, "pointerleave", (e) => onPointer(e, POINTER_FLAGS.leave));
  add(target, "pointercancel", (e) => onPointer(e, POINTER_FLAGS.cancel));
  add(target, "wheel", onWheel, { passive: true });

  if (doc) {
    add(doc, "keydown", (e) => onKey(e, KEY_FLAGS.down), true);
    add(doc, "keyup", (e) => onKey(e, KEY_FLAGS.up), true);
    add(doc, "compositionstart", (e) => onComposition(e, 0), true);
    add(doc, "compositionupdate", (e) => onComposition(e, 1), true);
    add(doc, "compositionend", (e) => onComposition(e, 2), true);
    add(doc, "beforeinput", onText, true);
    add(doc, "focusin", (e) => onFocus(e, EVENT_TYPES.focus), true);
    add(doc, "focusout", (e) => onFocus(e, EVENT_TYPES.blur), true);
  }

  function dispose() {
    for (const [node, type, handler, options] of listeners) {
      node.removeEventListener(type, handler, options);
    }
    listeners.length = 0;
    viewRegistry.clear();
  }

  return {
    pollEvents,
    renderTree,
    measureText,
    setWake,
    setTheme(nextTheme) {
      applyTheme(nextTheme);
      scheduleSync();
    },
    flush() {
      if (typeof root.flush === "function") {
        root.flush();
      }
      syncViews();
    },
    dispose,
  };
}
