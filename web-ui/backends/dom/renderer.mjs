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
    }
  };
}

export function createDomRoot(container, options = {}) {
  const backend = createDomBackend({ document: options.document, container });
  return createRoot(backend, container);
}
