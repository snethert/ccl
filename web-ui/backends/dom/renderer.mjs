import { createRoot } from "../../src/renderer.mjs";

function isEventProp(name) {
  return name.startsWith("on") && name.length > 2;
}

function eventName(name) {
  return name.slice(2).toLowerCase();
}

function ensureDocument(doc, container) {
  if (doc) return doc;
  if (container && container.ownerDocument) return container.ownerDocument;
  if (typeof document !== "undefined") return document;
  throw new Error("DOM document is required for DOM backend");
}

export function createDomBackend({ document: doc, container } = {}) {
  const documentRef = ensureDocument(doc, container);
  const listeners = new WeakMap();
  let measureContext = null;
  const viewRef = documentRef.defaultView ?? globalThis;

  function getMeasureContext() {
    if (measureContext) return measureContext;
    const canvas = documentRef.createElement("canvas");
    measureContext = canvas.getContext("2d");
    return measureContext;
  }

  function parseFontSize(font) {
    if (!font) return 12;
    const match = String(font).match(/(\d+(?:\.\d+)?)px/);
    if (!match) return 12;
    const size = Number.parseFloat(match[1]);
    return Number.isFinite(size) ? size : 12;
  }

  function setEvent(node, name, handler) {
    const event = eventName(name);
    let map = listeners.get(node);
    if (!map) {
      map = new Map();
      listeners.set(node, map);
    }
    const prev = map.get(event);
    if (prev) {
      node.removeEventListener(event, prev);
    }
    if (handler) {
      node.addEventListener(event, handler);
      map.set(event, handler);
    } else {
      map.delete(event);
    }
  }

  function clearEvent(node, name) {
    const event = eventName(name);
    const map = listeners.get(node);
    if (!map) return;
    const prev = map.get(event);
    if (prev) {
      node.removeEventListener(event, prev);
      map.delete(event);
    }
  }

  function clearAllEvents(node) {
    const map = listeners.get(node);
    if (!map) return;
    for (const [event, handler] of map.entries()) {
      node.removeEventListener(event, handler);
    }
    listeners.delete(node);
  }

  return {
    createElement(tag) {
      return documentRef.createElement(tag);
    },
    createText(text) {
      return documentRef.createTextNode(text);
    },
    appendChild(parent, child) {
      parent.appendChild(child);
    },
    insertBefore(parent, child, anchor) {
      parent.insertBefore(child, anchor ?? null);
    },
    removeChild(parent, child) {
      parent.removeChild(child);
    },
    replaceChild(parent, next, prev) {
      parent.replaceChild(next, prev);
    },
    setText(node, text) {
      node.nodeValue = text;
    },
    setProp(node, name, value) {
      if (name.startsWith("__")) {
        node[name] = value;
        if (name === "__canvasRender" && typeof value === "function") {
          value(node);
        }
        if (name === "__webglRender" && typeof value === "function") {
          value(node);
        }
        return;
      }
      if (isEventProp(name) && typeof value === "function") {
        setEvent(node, name, value);
        return;
      }
      if (name === "class" || name === "className") {
        node.className = value ?? "";
        return;
      }
      if (name === "style") {
        if (value === null || value === undefined) {
          node.removeAttribute("style");
          node.style.cssText = "";
          return;
        }
        if (typeof value === "string") {
          node.style.cssText = value;
          return;
        }
        if (typeof value === "object") {
          node.style.cssText = "";
          for (const [key, styleValue] of Object.entries(value)) {
            node.style[key] = styleValue ?? "";
          }
          return;
        }
      }
      if (value === false || value === null || value === undefined) {
        if (name in node && typeof node[name] === "boolean") {
          node[name] = false;
        }
        node.removeAttribute(name);
        return;
      }
      if (name in node) {
        node[name] = value;
        return;
      }
      node.setAttribute(name, String(value));
    },
    removeProp(node, name) {
      if (name.startsWith("__")) {
        try {
          delete node[name];
        } catch (err) {
          node[name] = undefined;
        }
        return;
      }
      if (isEventProp(name)) {
        clearEvent(node, name);
        return;
      }
      if (name === "class" || name === "className") {
        node.className = "";
        return;
      }
      if (name === "style") {
        node.removeAttribute("style");
        node.style.cssText = "";
        return;
      }
      if (name in node) {
        node[name] = typeof node[name] === "boolean" ? false : "";
      }
      node.removeAttribute(name);
    },
    destroy(node) {
      clearAllEvents(node);
    },
    measureText(text, options = {}) {
      const ctx = getMeasureContext();
      if (!ctx) {
        return { width: 0, height: 0, ascent: 0, descent: 0 };
      }
      const font = options.font ?? "12px monospace";
      ctx.font = font;
      const metrics = ctx.measureText(String(text ?? ""));
      const fontSize = parseFontSize(font);
      const ascent = metrics.actualBoundingBoxAscent ?? fontSize * 0.8;
      const descent = metrics.actualBoundingBoxDescent ?? fontSize * 0.2;
      const height = ascent + descent;
      return {
        width: metrics.width,
        height,
        ascent,
        descent
      };
    },
    hitTest(point, options = {}) {
      const x = point?.x ?? 0;
      const y = point?.y ?? 0;
      if (typeof documentRef.elementFromPoint !== "function") {
        return null;
      }
      const element = documentRef.elementFromPoint(x, y);
      if (!element) return null;
      const target = options.container ?? null;
      if (target && !target.contains(element)) {
        return null;
      }
      return element;
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
    }
  };
}

export function createDomRoot(container, options = {}) {
  const backend = createDomBackend({ document: options.document, container });
  const schedule = typeof options.schedule === "function" ? options.schedule : null;
  return createRoot(backend, container, { schedule });
}
