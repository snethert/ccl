import { replayEvents } from "../replay-harness.mjs";
import { snapshotToString, stableStringify } from "../snapshot.mjs";
import { createRegistry, registerCommand } from "../../src/commands.mjs";
import { createState, addTask, addWindow, addWidget } from "../../src/state.mjs";
import { reconcileFocus, resolveFocusTargetFromElement } from "../../src/focus.mjs";
import { createElement, createText } from "../../src/vdom.mjs";
import { renderWindow } from "../../src/widgets.mjs";
import { createDomBackend, createDomRoot } from "../../backends/dom/renderer.mjs";
import { createCanvasBackend } from "../../backends/canvas/renderer.mjs";
import { createWebGLBackend } from "../../backends/webgl/renderer.mjs";
import { createIndexedDBStore, createPersistenceManager, createSnapshot } from "../../src/index.mjs";
import {
  createMicrokernel,
  KERNEL_OP_UI_POLL,
  KERNEL_OP_UI_RENDER,
  KERNEL_OP_UI_MEASURE_TEXT
} from "../../../doc/wasm/js/microkernel.mjs";
import {
  createCclImports,
  createSharedCclRuntime,
  installConstPoolBytes,
  installSubprimsTable,
  instantiateWasm
} from "../../../doc/wasm/js/ccl-loader.mjs";
import { createUiBridge } from "../../bridge/ui-bridge.mjs";

const _bridgeEncoder = typeof TextEncoder !== "undefined" ? new TextEncoder() : null;
const _bridgeDecoder = typeof TextDecoder !== "undefined" ? new TextDecoder("utf-8") : null;

function encodeBridgeUtf8(text) {
  if (_bridgeEncoder) return _bridgeEncoder.encode(String(text));
  const s = String(text);
  const out = new Uint8Array(s.length);
  for (let i = 0; i < s.length; i++) out[i] = s.charCodeAt(i) & 0xff;
  return out;
}

function decodeBridgeUtf8(bytes) {
  if (_bridgeDecoder) return _bridgeDecoder.decode(bytes);
  let out = "";
  for (let i = 0; i < bytes.length; i++) out += String.fromCharCode(bytes[i]);
  return out;
}

class UiStringTable {
  constructor() {
    this.map = new Map();
    this.list = [];
    this.bytes = [];
  }

  indexOf(value) {
    if (value === null || value === undefined) return 0xffffffff;
    const key = String(value);
    if (this.map.has(key)) return this.map.get(key);
    const idx = this.list.length;
    this.list.push(key);
    this.map.set(key, idx);
    this.bytes.push(encodeBridgeUtf8(key));
    return idx;
  }

  totalSize() {
    let size = 0;
    for (const bytes of this.bytes) {
      size += 4 + bytes.length;
    }
    return size;
  }
}

function f64ToU32Parts(value) {
  const buf = new ArrayBuffer(8);
  const dv = new DataView(buf);
  dv.setFloat64(0, Number(value ?? 0), true);
  return { lo: dv.getUint32(0, true), hi: dv.getUint32(4, true) };
}

function encodeUiTreePayload(nodes, rootIndex = 0) {
  const table = new UiStringTable();
  nodes.forEach((node) => {
    if (!node) return;
    if (node.kind === "text") {
      table.indexOf(node.text ?? "");
      table.indexOf(node.key);
      return;
    }
    table.indexOf(node.tag ?? "div");
    table.indexOf(node.key);
    const props = node.props ?? {};
    for (const [key, value] of Object.entries(props)) {
      table.indexOf(key);
      if (typeof value === "string") table.indexOf(value);
    }
  });

  const stringCount = table.list.length;
  const nodeCount = nodes.length;
  const headerSize = 24;
  let nodeBytes = 0;
  for (const node of nodes) {
    if (!node) continue;
    nodeBytes += 12;
    if (node.kind === "text") {
      nodeBytes += 4;
    } else {
      const propCount = Object.keys(node.props ?? {}).length;
      const childCount = Array.isArray(node.children) ? node.children.length : 0;
      nodeBytes += 12 + propCount * 16 + childCount * 4;
    }
  }
  const totalSize = headerSize + table.totalSize() + nodeBytes;
  const buf = new ArrayBuffer(totalSize);
  const dv = new DataView(buf);
  const out = new Uint8Array(buf);
  let off = 0;
  dv.setUint32(off, 0x55494231, true);
  dv.setUint32(off + 4, 1, true);
  dv.setUint32(off + 8, stringCount, true);
  dv.setUint32(off + 12, nodeCount, true);
  dv.setUint32(off + 16, rootIndex >>> 0, true);
  dv.setUint32(off + 20, 0, true);
  off = headerSize;
  table.bytes.forEach((b) => {
    dv.setUint32(off, b.length, true);
    off += 4;
    out.set(b, off);
    off += b.length;
  });

  nodes.forEach((node) => {
    const keyIndex = table.indexOf(node?.key);
    const flags = keyIndex !== 0xffffffff ? 1 : 0;
    if (node.kind === "text") {
      dv.setUint32(off, 0, true);
      dv.setUint32(off + 4, flags, true);
      dv.setUint32(off + 8, keyIndex, true);
      off += 12;
      dv.setUint32(off, table.indexOf(node.text ?? ""), true);
      off += 4;
      return;
    }
    const tagIndex = table.indexOf(node.tag ?? "div");
    const props = node.props ?? {};
    const propEntries = Object.entries(props);
    const children = Array.isArray(node.children) ? node.children : [];
    dv.setUint32(off, 1, true);
    dv.setUint32(off + 4, flags, true);
    dv.setUint32(off + 8, keyIndex, true);
    off += 12;
    dv.setUint32(off, tagIndex, true);
    dv.setUint32(off + 4, propEntries.length, true);
    dv.setUint32(off + 8, children.length, true);
    off += 12;
    for (const [key, value] of propEntries) {
      const keyIdx = table.indexOf(key);
      let valueType = 0;
      let valueLo = 0;
      let valueHi = 0;
      if (value === null || value === undefined) {
        valueType = 0;
      } else if (typeof value === "boolean") {
        valueType = 1;
        valueLo = value ? 1 : 0;
      } else if (typeof value === "number") {
        valueType = 2;
        const parts = f64ToU32Parts(value);
        valueLo = parts.lo;
        valueHi = parts.hi;
      } else {
        valueType = 3;
        valueLo = table.indexOf(String(value));
      }
      dv.setUint32(off, keyIdx, true);
      dv.setUint32(off + 4, valueType, true);
      dv.setUint32(off + 8, valueLo >>> 0, true);
      dv.setUint32(off + 12, valueHi >>> 0, true);
      off += 16;
    }
    for (const child of children) {
      dv.setUint32(off, child >>> 0, true);
      off += 4;
    }
  });

  return new Uint8Array(buf);
}

function buildUiBridgeTreePayload() {
  return encodeUiTreePayload([
    {
      kind: "element",
      tag: "div",
      props: { "data-window-id": "win-1" },
      children: [1],
    },
    {
      kind: "element",
      tag: "button",
      props: { "data-widget-id": "btn-1" },
      children: [2],
    },
    { kind: "text", text: "Click" },
  ]);
}

function buildUiBridgeCanvasPayload() {
  const scene = JSON.stringify([
    { id: "bottom", kind: "rect", bounds: { x: 0, y: 0, width: 50, height: 50 }, props: { fill: "#000" } },
    { id: "top", kind: "rect", bounds: { x: 5, y: 5, width: 20, height: 20 }, props: { fill: "#f00" } }
  ]);
  return {
    payload: encodeUiTreePayload([
      {
        kind: "element",
        tag: "div",
        props: { "data-window-id": "win-canvas" },
        children: [1],
      },
      {
        kind: "element",
        tag: "canvas",
        props: {
          "data-widget-id": "canvas-1",
          "data-canvas-scene": scene,
          style: "width:64px;height:64px;",
          width: 64,
          height: 64
        },
        children: [],
      },
    ]),
    hitTarget: "canvas-1:top",
  };
}

function buildUiBridgeWebglPayload() {
  const scene = JSON.stringify([
    { id: "bottom", kind: "rect", bounds: { x: 0, y: 0, width: 50, height: 50 }, props: { fill: "#000" } },
    { id: "top", kind: "rect", bounds: { x: 6, y: 6, width: 18, height: 18 }, props: { fill: "#00f" } }
  ]);
  return {
    payload: encodeUiTreePayload([
      {
        kind: "element",
        tag: "div",
        props: { "data-window-id": "win-webgl" },
        children: [1],
      },
      {
        kind: "element",
        tag: "canvas",
        props: {
          "data-widget-id": "webgl-1",
          "data-webgl-scene": scene,
          style: "width:64px;height:64px;",
          width: 64,
          height: 64
        },
        children: [],
      },
    ]),
    hitTarget: "webgl-1:top",
  };
}

function uiEventRecordSize(typeId) {
  switch (typeId) {
  case 1: // pointer
    return 16 + 40;
  case 2: // key
    return 16 + 32;
  case 3: // composition
    return 16 + 16;
  case 4: // text
    return 16 + 16;
  case 5: // focus
  case 6: // blur
    return 16 + 16;
  case 7: // wheel
    return 16 + 32;
  default:
    return 16 + 16;
  }
}

function decodeUiEventBatch(payload) {
  const dv = new DataView(payload.buffer, payload.byteOffset, payload.byteLength);
  if (payload.byteLength < 16) {
    return { count: 0, events: [] };
  }
  const magic = dv.getUint32(0, true);
  const version = dv.getUint32(4, true);
  if (magic !== 0x55494531 || version !== 1) {
    return { count: 0, events: [] };
  }
  const stringCount = dv.getUint32(8, true);
  const eventCount = dv.getUint32(12, true);
  let off = 16;
  const strings = new Array(stringCount);
  for (let i = 0; i < stringCount; i++) {
    const len = dv.getUint32(off, true);
    off += 4;
    strings[i] = decodeBridgeUtf8(payload.subarray(off, off + len));
    off += len;
  }
  const events = [];
  for (let i = 0; i < eventCount; i++) {
    if (off + 16 > payload.byteLength) break;
    const type = dv.getUint32(off, true);
    const flags = dv.getUint32(off + 4, true);
    const targetIdx = dv.getUint32(off + 8, true);
    const windowIdx = dv.getUint32(off + 12, true);
    const targetId = targetIdx === 0xffffffff ? null : strings[targetIdx] ?? null;
    const windowId = windowIdx === 0xffffffff ? null : strings[windowIdx] ?? null;
    const size = uiEventRecordSize(type);
    off += size;
    events.push({ type, flags, targetId, windowId });
  }
  return { count: eventCount, events };
}

async function loadJson(relPath) {
  const response = await fetch(relPath);
  if (!response.ok) {
    throw new Error(`Failed to load ${relPath}: ${response.status}`);
  }
  return response.json();
}

async function loadBytes(relPath) {
  const response = await fetch(relPath);
  if (!response.ok) {
    throw new Error(`Failed to load ${relPath}: ${response.status}`);
  }
  return response.arrayBuffer();
}

async function run() {
  const initialState = await loadJson("../fixtures/basic-state.json");
  const eventLog = await loadJson("../fixtures/basic-events.json");
  const expectedSnapshot = await loadJson("../fixtures/basic-snapshot.json");
  const expectedDomSnapshot = await loadJson("../fixtures/dom-snapshot.json");
  let uiBundleOk = false;
  let uiBundleInfo = null;
  try {
    const uiBundle = await loadJson("/doc/wasm/wasm-ui-modules.json");
    const modules = Array.isArray(uiBundle?.modules) ? uiBundle.modules : [];
    const functions = Array.isArray(uiBundle?.functions) ? uiBundle.functions : [];
    const functionNames = new Set(functions.map((fn) => fn?.name).filter(Boolean));
    uiBundleOk =
      modules.length > 0 &&
      functionNames.has("WASM-UI-DEMO") &&
      functionNames.has("WASM-UI-TURN") &&
      functionNames.has("WASM-UI-POLL");
    uiBundleInfo = { modules: modules.length, functions: functions.length };
  } catch (err) {
    uiBundleInfo = { error: err?.message ?? String(err) };
  }

  const result = replayEvents(initialState, eventLog.events);
  const snapshot = snapshotToString(result.snapshots[0]);
  const snapshotMatch = snapshot === stableStringify(expectedSnapshot);

  const root = document.getElementById("root");
  root.textContent = "ok";
  const domOk = root.textContent === "ok";

  const domRenderTarget = document.createElement("div");
  domRenderTarget.id = "dom-render-target";
  root.appendChild(domRenderTarget);

  const domBackend = createDomBackend({ document, container: domRenderTarget });
  const domRoot = createDomRoot(domRenderTarget, { document });
  const tree1 = createElement(
    "div",
    { id: "view", className: "pane" },
    [
      createElement("span", { "data-key": "label" }, [createText("Hello")], "label"),
      createElement("button", { "data-key": "btn", disabled: true }, [createText("Click")], "btn")
    ],
    "view"
  );
  domRoot.render(tree1);

  const labelNode = domRenderTarget.querySelector("[data-key='label']");
  const buttonNode = domRenderTarget.querySelector("[data-key='btn']");

  const tree2 = createElement(
    "div",
    { id: "view", className: "pane active", "data-role": "main" },
    [
      createElement("button", { "data-key": "btn", disabled: false }, [createText("Go")], "btn"),
      createElement("span", { "data-key": "label" }, [createText("Hello")], "label"),
      createElement("span", { "data-key": "extra" }, [createText("New")], "extra")
    ],
    "view"
  );
  domRoot.render(tree2);

  const domReuseOk =
    domRenderTarget.querySelector("[data-key='label']") === labelNode &&
    domRenderTarget.querySelector("[data-key='btn']") === buttonNode;

  function serializeDom(node) {
    if (node.nodeType === Node.TEXT_NODE) {
      return { kind: "text", text: node.nodeValue ?? "" };
    }
    if (node.nodeType !== Node.ELEMENT_NODE) {
      return null;
    }
    const attrs = {};
    const names = Array.from(node.attributes ?? []).map((attr) => attr.name).sort();
    for (const name of names) {
      attrs[name] = node.getAttribute(name);
    }
    const children = [];
    node.childNodes.forEach((child) => {
      const entry = serializeDom(child);
      if (entry) {
        children.push(entry);
      }
    });
    return { kind: "element", tag: node.tagName.toLowerCase(), attrs, children };
  }

  const domSnapshot = serializeDom(domRenderTarget);
  const domSnapshotMatch = stableStringify(domSnapshot) === stableStringify(expectedDomSnapshot);

  const widgetRenderTarget = document.createElement("div");
  widgetRenderTarget.id = "widget-render-target";
  root.appendChild(widgetRenderTarget);

  const registry = createRegistry();
  let commandCalls = 0;
  let inputValue = null;
  let listItemId = null;
  let canvasHitCtx = null;
  let webglHitCtx = null;
  let imeValue = null;
  registerCommand(registry, {
    id: "demo.run",
    exec: () => {
      commandCalls += 1;
    }
  });
  registerCommand(registry, {
    id: "demo.blocked",
    enabled: () => [false, "Blocked"]
  });
  registerCommand(registry, {
    id: "demo.input",
    exec: (ctx) => {
      inputValue = ctx.inputValue ?? null;
    }
  });
  registerCommand(registry, {
    id: "demo.ime",
    exec: (ctx) => {
      imeValue = ctx.inputValue ?? null;
    }
  });
  registerCommand(registry, {
    id: "demo.item",
    exec: (ctx) => {
      listItemId = ctx.itemId ?? null;
    }
  });
  registerCommand(registry, {
    id: "demo.canvas",
    exec: (ctx) => {
      canvasHitCtx = ctx;
    }
  });
  registerCommand(registry, {
    id: "demo.webgl",
    exec: (ctx) => {
      webglHitCtx = ctx;
    }
  });

  let widgetState = createState();
  widgetState = addTask(widgetState, { id: "task-1", title: "Task" });
  widgetState = addWindow(widgetState, { id: "win-1", taskId: "task-1", kind: "document" });
  widgetState = addWidget(widgetState, { id: "root-widget", kind: "container", windowId: "win-1" });
  widgetState = addWidget(widgetState, {
    id: "btn-run",
    kind: "button",
    parentId: "root-widget",
    props: { label: "Run", command: "demo.run" }
  });
  widgetState = addWidget(widgetState, {
    id: "btn-blocked",
    kind: "button",
    parentId: "root-widget",
    props: { label: "Blocked", command: "demo.blocked" }
  });
  widgetState = addWidget(widgetState, {
    id: "input-text",
    kind: "text-input",
    parentId: "root-widget",
    props: { placeholder: "Type", command: "demo.input" }
  });
  widgetState = addWidget(widgetState, {
    id: "input-ime",
    kind: "text-input",
    parentId: "root-widget",
    props: { placeholder: "IME", command: "demo.ime" }
  });
  widgetState = addWidget(widgetState, {
    id: "list-widget",
    kind: "list",
    parentId: "root-widget",
    props: {
      itemCommand: "demo.item",
      items: [
        { id: "alpha", label: "Alpha" },
        { id: "beta", label: "Beta" }
      ]
    }
  });

  const widgetRoot = createDomRoot(widgetRenderTarget, { document });
  widgetRoot.render(renderWindow(widgetState, "win-1", { registry }));

  const runButton = widgetRenderTarget.querySelector("[data-widget-id='btn-run']");
  const blockedButton = widgetRenderTarget.querySelector("[data-widget-id='btn-blocked']");
  const input = widgetRenderTarget.querySelector("[data-widget-id='input-text']");
  const imeInput = widgetRenderTarget.querySelector("[data-widget-id='input-ime']");
  const listItem = widgetRenderTarget.querySelector("[data-item-id='alpha']");
  const commandDomOk =
    runButton &&
    blockedButton &&
    input &&
    imeInput &&
    listItem &&
    runButton.getAttribute("data-command-id") === "demo.run" &&
    blockedButton.getAttribute("data-command-id") === "demo.blocked" &&
    blockedButton.disabled === true &&
    blockedButton.getAttribute("data-disabled-reason") === "Blocked" &&
    input.getAttribute("data-command-id") === "demo.input" &&
    imeInput.getAttribute("data-command-id") === "demo.ime" &&
    listItem.getAttribute("data-command-id") === "demo.item";

  if (runButton) {
    runButton.click();
  }
  if (input) {
    input.value = "hello";
    input.dispatchEvent(new Event("input", { bubbles: true }));
  }
  const commandInvokeOk = commandCalls === 1;
  const commandInputOk = inputValue === "hello";
  if (listItem) {
    listItem.click();
  }
  const commandListOk = listItemId === "alpha";

  const compositionEvents = {
    baseline: [],
    cancel: [],
    multi: [],
    selection: []
  };
  const deadKeyEvents = [];
  const beforeInputEvents = [];
  let compositionMode = "baseline";

  function createCompositionEvent(type, data, isComposing = true) {
    if (typeof CompositionEvent === "function") {
      return new CompositionEvent(type, { data, bubbles: true });
    }
    const event = new Event(type, { bubbles: true });
    try {
      Object.defineProperty(event, "data", { value: data });
      Object.defineProperty(event, "isComposing", { value: isComposing });
    } catch (err) {
      // ignore
    }
    return event;
  }

  function createInputEvent(type, options = {}) {
    if (typeof InputEvent === "function") {
      return new InputEvent(type, { bubbles: true, ...options });
    }
    const event = new Event(type, { bubbles: true });
    try {
      Object.assign(event, options);
    } catch (err) {
      // ignore
    }
    return event;
  }

  let imeCompositionValue = null;
  let mobileInputValue = null;

  if (imeInput) {
    imeInput.addEventListener("compositionstart", (event) => {
      compositionEvents[compositionMode]?.push({ type: event.type, data: event.data ?? null });
    });
    imeInput.addEventListener("compositionupdate", (event) => {
      compositionEvents[compositionMode]?.push({ type: event.type, data: event.data ?? null });
    });
    imeInput.addEventListener("compositionend", (event) => {
      compositionEvents[compositionMode]?.push({ type: event.type, data: event.data ?? null });
    });
    imeInput.addEventListener("keydown", (event) => {
      deadKeyEvents.push({ type: event.type, key: event.key ?? null });
    });
    imeInput.addEventListener("keyup", (event) => {
      deadKeyEvents.push({ type: event.type, key: event.key ?? null });
    });
    imeInput.addEventListener("beforeinput", (event) => {
      beforeInputEvents.push({ type: event.type, inputType: event.inputType ?? null, data: event.data ?? null });
    });

    compositionMode = "baseline";
    imeInput.dispatchEvent(createCompositionEvent("compositionstart", "I", true));
    imeInput.dispatchEvent(createCompositionEvent("compositionupdate", "IM", true));
    imeInput.value = "IM";
    imeInput.dispatchEvent(createInputEvent("input", { data: "IM", inputType: "insertCompositionText", isComposing: true }));
    imeInput.dispatchEvent(createCompositionEvent("compositionend", "IME", false));
    imeInput.value = "IME";
    imeInput.dispatchEvent(createInputEvent("input", { data: "IME", inputType: "insertCompositionText", isComposing: false }));
    imeCompositionValue = imeValue;

    const beforeCancelValue = imeValue;
    compositionMode = "cancel";
    imeInput.dispatchEvent(createCompositionEvent("compositionstart", "X", true));
    imeInput.dispatchEvent(createCompositionEvent("compositionupdate", "XY", true));
    imeInput.dispatchEvent(createCompositionEvent("compositionend", "", false));
    const afterCancelValue = imeValue;

    compositionMode = "multi";
    imeInput.dispatchEvent(createCompositionEvent("compositionstart", "A", true));
    imeInput.dispatchEvent(createCompositionEvent("compositionupdate", "AB", true));
    imeInput.dispatchEvent(createCompositionEvent("compositionupdate", "ABC", true));
    imeInput.value = "ABC";
    imeInput.dispatchEvent(createInputEvent("input", { data: "ABC", inputType: "insertCompositionText", isComposing: false }));
    imeInput.dispatchEvent(createCompositionEvent("compositionend", "ABC", false));
    const multiStepValue = imeValue;

    compositionMode = "selection";
    imeInput.value = "select";
    if (typeof imeInput.setSelectionRange === "function") {
      imeInput.setSelectionRange(1, 3);
    }
    const selectionBefore = {
      start: imeInput.selectionStart,
      end: imeInput.selectionEnd
    };
    imeInput.dispatchEvent(createCompositionEvent("compositionstart", "S", true));
    imeInput.dispatchEvent(createCompositionEvent("compositionupdate", "SE", true));
    imeInput.dispatchEvent(createInputEvent("input", { data: "SE", inputType: "insertCompositionText", isComposing: true }));
    const selectionAfter = {
      start: imeInput.selectionStart,
      end: imeInput.selectionEnd
    };

    const deadKeyDown = new KeyboardEvent("keydown", { key: "Dead", code: "Quote", bubbles: true });
    const deadKeyUp = new KeyboardEvent("keyup", { key: "Dead", code: "Quote", bubbles: true });
    imeInput.dispatchEvent(deadKeyDown);
    imeInput.dispatchEvent(deadKeyUp);

    imeInput.value = "mobile";
    imeInput.dispatchEvent(createInputEvent("beforeinput", { data: "mobile", inputType: "insertText" }));
    imeInput.dispatchEvent(createInputEvent("input", { data: "mobile", inputType: "insertText", isComposing: false }));
    mobileInputValue = imeValue;

    const compositionBaseline = compositionEvents.baseline;
    const compositionCancel = compositionEvents.cancel;
    const compositionMulti = compositionEvents.multi;
    const compositionSelection = compositionEvents.selection;

    var imeCompositionOk =
      compositionBaseline.length === 3 &&
      compositionBaseline[0].type === "compositionstart" &&
      compositionBaseline[1].type === "compositionupdate" &&
      compositionBaseline[2].type === "compositionend" &&
      compositionBaseline[2].data === "IME" &&
      imeCompositionValue === "IME";
    var imeCancelOk =
      compositionCancel.length >= 3 &&
      compositionCancel[0].type === "compositionstart" &&
      compositionCancel[compositionCancel.length - 1].type === "compositionend" &&
      afterCancelValue === beforeCancelValue;
    var imeMultiStepOk =
      compositionMulti.length >= 3 &&
      compositionMulti[0].type === "compositionstart" &&
      compositionMulti[compositionMulti.length - 1].type === "compositionend" &&
      multiStepValue === "ABC";
    var imeSelectionOk =
      compositionSelection.length >= 2 &&
      selectionBefore.start === selectionAfter.start &&
      selectionBefore.end === selectionAfter.end;
  }

  const imeCompositionOkResolved = imeCompositionOk ?? false;
  const imeCancelOkResolved = imeCancelOk ?? false;
  const imeMultiStepOkResolved = imeMultiStepOk ?? false;
  const imeSelectionOkResolved = imeSelectionOk ?? false;
  const deadKeyOk = deadKeyEvents.length === 2 && deadKeyEvents.every((event) => event.key === "Dead");
  const mobileInputOk =
    beforeInputEvents.some((event) => event.inputType === "insertText") &&
    mobileInputValue === "mobile";

  const virtualTarget = document.createElement("div");
  virtualTarget.id = "virtual-widget-target";
  root.appendChild(virtualTarget);

  let virtualState = createState();
  virtualState = addTask(virtualState, { id: "task-virtual", title: "Virtual Task" });
  virtualState = addWindow(virtualState, { id: "win-virtual", taskId: "task-virtual", kind: "document" });
  virtualState = addWidget(virtualState, { id: "virtual-root", kind: "container", windowId: "win-virtual" });
  virtualState = addWidget(virtualState, {
    id: "virtual-list",
    kind: "list",
    parentId: "virtual-root",
    props: {
      virtual: true,
      rowHeight: 20,
      viewportHeight: 60,
      scrollTop: 40,
      overscan: 0,
      items: Array.from({ length: 10 }, (_, index) => ({ id: `row-${index}`, label: `Row ${index}` }))
    }
  });
  virtualState = addWidget(virtualState, {
    id: "virtual-tree",
    kind: "tree",
    parentId: "virtual-root",
    props: {
      virtual: true,
      rowHeight: 10,
      viewportHeight: 15,
      scrollTop: 0,
      overscan: 0,
      items: [
        { id: "parent", label: "Parent", expanded: true, children: [{ id: "child", label: "Child" }] },
        { id: "sibling", label: "Sibling", expanded: false, children: [{ id: "hidden", label: "Hidden" }] }
      ]
    }
  });
  virtualState = addWidget(virtualState, {
    id: "virtual-table",
    kind: "table",
    parentId: "virtual-root",
    props: {
      virtual: true,
      rowHeight: 20,
      viewportHeight: 40,
      scrollTop: 0,
      overscan: 0,
      columns: [
        { id: "col-a", label: "Column A" },
        { id: "col-b", label: "Column B" }
      ],
      rows: Array.from({ length: 6 }, (_, index) => ({
        id: `row-${index}`,
        cells: { "col-a": `A${index}`, "col-b": `B${index}` }
      }))
    }
  });

  const virtualRoot = createDomRoot(virtualTarget, { document });
  virtualRoot.render(renderWindow(virtualState, "win-virtual", { registry }));

  const virtualList = virtualTarget.querySelector("[data-widget-id='virtual-list']");
  const virtualListRows = virtualList ? virtualList.querySelectorAll("[data-virtual-index]") : [];
  const virtualListOk =
    virtualList &&
    virtualList.getAttribute("data-virtual-start") === "2" &&
    virtualList.getAttribute("data-virtual-end") === "5" &&
    virtualList.getAttribute("data-virtual-total") === "10" &&
    virtualListRows.length === 3;

  const virtualTree = virtualTarget.querySelector("[data-widget-id='virtual-tree']");
  const virtualTreeRows = virtualTree ? virtualTree.querySelectorAll("[data-virtual-index]") : [];
  const virtualTreeOk =
    virtualTree &&
    virtualTree.getAttribute("data-virtual-start") === "0" &&
    virtualTree.getAttribute("data-virtual-end") === "2" &&
    virtualTree.getAttribute("data-virtual-total") === "3" &&
    virtualTreeRows.length === 2;

  const virtualTable = virtualTarget.querySelector("[data-widget-id='virtual-table']");
  const virtualTableRows = virtualTable ? virtualTable.querySelectorAll("[data-virtual-index]") : [];
  const virtualTableOk =
    virtualTable &&
    virtualTable.getAttribute("data-virtual-start") === "0" &&
    virtualTable.getAttribute("data-virtual-end") === "2" &&
    virtualTable.getAttribute("data-virtual-total") === "6" &&
    virtualTableRows.length === 2;

  const canvasWidgetTarget = document.createElement("div");
  canvasWidgetTarget.id = "canvas-widget-target";
  root.appendChild(canvasWidgetTarget);

  let canvasState = createState();
  canvasState = addTask(canvasState, { id: "task-canvas", title: "Canvas Task" });
  canvasState = addWindow(canvasState, { id: "win-canvas", taskId: "task-canvas", kind: "document" });
  canvasState = addWidget(canvasState, { id: "canvas-root", kind: "container", windowId: "win-canvas" });
  canvasState = addWidget(canvasState, {
    id: "canvas-widget",
    kind: "canvas-view",
    parentId: "canvas-root",
    props: {
      command: "demo.canvas",
      width: 80,
      height: 60,
      style: { width: "80px", height: "60px" },
      scene: [
        {
          id: "rect-1",
          kind: "rect",
          bounds: { x: 0, y: 0, width: 20, height: 20 },
          props: { fill: "#00f", commandId: "demo.canvas" }
        }
      ]
    }
  });

  const canvasWidgetRoot = createDomRoot(canvasWidgetTarget, { document });
  canvasWidgetRoot.render(renderWindow(canvasState, "win-canvas", { registry }));

  const canvasNode = canvasWidgetTarget.querySelector("[data-widget-id='canvas-widget']");
  const canvasWidgetOk = Boolean(canvasNode?.__canvasBackend && canvasNode?.__canvasScene);
  if (canvasNode) {
    const canvasRect = canvasNode.getBoundingClientRect();
    const click = new MouseEvent("click", {
      bubbles: true,
      clientX: canvasRect.left + 5,
      clientY: canvasRect.top + 5
    });
    canvasNode.dispatchEvent(click);
  }
  const canvasWidgetCommandOk = canvasHitCtx?.hitId === "rect-1" && canvasHitCtx?.canvasId === "canvas-widget";

  const webglWidgetTarget = document.createElement("div");
  webglWidgetTarget.id = "webgl-widget-target";
  root.appendChild(webglWidgetTarget);

  let webglState = createState();
  webglState = addTask(webglState, { id: "task-webgl", title: "WebGL Task" });
  webglState = addWindow(webglState, { id: "win-webgl", taskId: "task-webgl", kind: "document" });
  webglState = addWidget(webglState, { id: "webgl-root", kind: "container", windowId: "win-webgl" });
  webglState = addWidget(webglState, {
    id: "webgl-widget",
    kind: "webgl-view",
    parentId: "webgl-root",
    props: {
      command: "demo.webgl",
      width: 80,
      height: 60,
      style: { width: "80px", height: "60px" },
      scene: [
        {
          id: "rect-1",
          kind: "rect",
          bounds: { x: 0, y: 0, width: 20, height: 20 },
          props: { fill: "#00f", commandId: "demo.webgl" }
        }
      ]
    }
  });

  const webglWidgetRoot = createDomRoot(webglWidgetTarget, { document });
  webglWidgetRoot.render(renderWindow(webglState, "win-webgl", { registry }));

  const webglNode = webglWidgetTarget.querySelector("[data-widget-id='webgl-widget']");
  const webglWidgetOk = Boolean(webglNode?.__webglBackend && webglNode?.__webglScene);
  if (webglNode) {
    const webglRect = webglNode.getBoundingClientRect();
    const click = new MouseEvent("click", {
      bubbles: true,
      clientX: webglRect.left + 5,
      clientY: webglRect.top + 5
    });
    webglNode.dispatchEvent(click);
  }
  const webglWidgetCommandOk = webglHitCtx?.hitId === "rect-1" && webglHitCtx?.webglId === "webgl-widget";

  const focusState = reconcileFocus(widgetState, { target: runButton, seq: 1 }, {
    deferWhileComposing: true,
    resolveTarget: (element) => resolveFocusTargetFromElement(element, widgetState)
  });
  const focusOk = focusState.focus?.widgetId === "btn-run" && focusState.focus?.windowId === "win-1";

  const measure = domBackend.measureText("Hello", { font: "16px monospace" });
  const measureOk = Number.isFinite(measure.width) && measure.width > 0 && measure.height > 0;

  const hitTestTarget = document.createElement("div");
  hitTestTarget.style.cssText = "position: relative; width: 60px; height: 60px;";
  const hitButton = document.createElement("button");
  hitButton.textContent = "Hit";
  hitButton.setAttribute("data-hit", "target");
  hitButton.style.cssText = "position: absolute; left: 10px; top: 10px; width: 20px; height: 20px;";
  hitTestTarget.appendChild(hitButton);
  root.appendChild(hitTestTarget);

  const rect = hitButton.getBoundingClientRect();
  const hit = domBackend.hitTest(
    { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 },
    { container: hitTestTarget }
  );
  const hitTestOk = hit === hitButton;

  let capturedTarget = null;
  const releaseCapture = domBackend.captureEvents(hitTestTarget, {
    click: (event) => {
      capturedTarget = event.target;
    }
  });
  hitButton.click();
  releaseCapture();
  const captureEventsOk = capturedTarget === hitButton;

  const invalidateOk = await new Promise((resolve) => {
    domBackend.invalidate(() => resolve(true));
  });

  const canvas = document.createElement("canvas");
  canvas.width = 10;
  canvas.height = 10;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#ff0000";
  ctx.fillRect(0, 0, 10, 10);
  const pixel = ctx.getImageData(5, 5, 1, 1).data;
  const canvasOk = pixel[0] === 255 && pixel[1] === 0 && pixel[2] === 0 && pixel[3] === 255;

  const canvasBackend = createCanvasBackend({ canvas, document });
  canvasBackend.render([
    { id: "bottom", kind: "rect", bounds: { x: 0, y: 0, width: 8, height: 8 }, props: { fill: "#000" } },
    { id: "top", kind: "rect", bounds: { x: 0, y: 0, width: 8, height: 8 }, props: { fill: "#111" } }
  ]);
  const backendHit = canvasBackend.hitTest({ x: 4, y: 4 });
  const canvasBackendHitOk = backendHit?.id === "top";
  const measureFirst = canvasBackend.measureText("Hello", { font: "12px monospace" });
  const measureSecond = canvasBackend.measureText("Hello", { font: "12px monospace" });
  const canvasMeasureOk = measureFirst.cacheHit === false && measureSecond.cacheHit === true;

  const webglCanvas = document.createElement("canvas");
  webglCanvas.width = 10;
  webglCanvas.height = 10;
  const webglBackend = createWebGLBackend({ canvas: webglCanvas, document });
  webglBackend.render([
    { id: "bottom", kind: "rect", bounds: { x: 0, y: 0, width: 10, height: 10 }, props: { fill: "#000" } },
    { id: "top", kind: "rect", bounds: { x: 0, y: 0, width: 10, height: 10 }, props: { fill: "#ff0000" } }
  ]);
  const gl = webglCanvas.getContext("webgl");
  const webglPixel = new Uint8Array(4);
  if (gl) {
    gl.readPixels(5, 5, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, webglPixel);
  }
  const webglOk = webglPixel[0] >= 250 && webglPixel[1] <= 5 && webglPixel[2] <= 5 && webglPixel[3] >= 250;
  const webglHit = webglBackend.hitTest({ x: 4, y: 4 });
  const webglBackendHitOk = webglHit?.id === "top";
  const webglMeasureFirst = webglBackend.measureText("Hello", { font: "12px monospace" });
  const webglMeasureSecond = webglBackend.measureText("Hello", { font: "12px monospace" });
  const webglMeasureOk = webglMeasureFirst.cacheHit === false && webglMeasureSecond.cacheHit === true;

  const persistStore = await createIndexedDBStore({ name: "web-ui-test-persistence", version: 1 });
  const persistManager = createPersistenceManager({
    store: persistStore,
    workspaceId: "workspace-0",
    flushDelay: 0,
    now: () => 0
  });
  persistManager.schedulePersist(widgetState);
  await persistManager.flushNow();
  const restoredState = await persistManager.restoreState();
  const persistedBaseline = createSnapshot(widgetState, { now: () => 0 });
  const persistedRoundTrip = createSnapshot(restoredState ?? widgetState, { now: () => 0 });
  const persistenceOk =
    stableStringify(persistedBaseline.state) === stableStringify(persistedRoundTrip.state);
  await persistStore.clearSnapshot("workspace-0");
  persistManager.close();

  const bridgeTarget = document.createElement("div");
  bridgeTarget.id = "ui-bridge-target";
  root.appendChild(bridgeTarget);

  const uiBridge = createUiBridge({ container: bridgeTarget, document });
  const uiMemory = new WebAssembly.Memory({ initial: 1 });
  const uiMicrokernel = createMicrokernel({ memory: uiMemory, uiService: uiBridge });
  const {
    kernel_request,
    kernel_poll,
    kernel_result,
    kernel_response_size,
    kernel_copy_response,
    kernel_drop_request
  } = uiMicrokernel.imports;

  function writeUiBytes(ptr, bytes) {
    new Uint8Array(uiMemory.buffer, ptr, bytes.length).set(bytes);
  }

  function pollUiEvents({ maxEvents = 8, maxBytes = 4096 } = {}) {
    const pollPtr = 0;
    const pollView = new DataView(uiMemory.buffer, pollPtr, 12);
    pollView.setUint32(0, maxEvents, true);
    pollView.setUint32(4, maxBytes, true);
    pollView.setUint32(8, 0, true);
    const pollId = kernel_request(KERNEL_OP_UI_POLL, pollPtr, 12);
    const status = kernel_poll(pollId);
    const count = kernel_result(pollId) | 0;
    const size = kernel_response_size(pollId) >>> 0;
    let batch = { count: 0, events: [] };
    let copied = 0;
    if (size > 0) {
      const pollOutPtr = 2048;
      copied = kernel_copy_response(pollId, pollOutPtr, size) >>> 0;
      const pollBytes = new Uint8Array(uiMemory.buffer, pollOutPtr, size);
      batch = decodeUiEventBatch(pollBytes);
    }
    kernel_drop_request(pollId);
    return { status, count, size, copied, batch };
  }

  const uiTreePayload = buildUiBridgeTreePayload();
  const uiTreePtr = 256;
  writeUiBytes(uiTreePtr, uiTreePayload);
  const renderId = kernel_request(KERNEL_OP_UI_RENDER, uiTreePtr, uiTreePayload.length);
  const renderResult = kernel_result(renderId) | 0;
  kernel_drop_request(renderId);
  const uiBridgeRenderOk = renderResult === 0;
  if (typeof uiBridge.flush === "function") {
    uiBridge.flush();
  }

  const uiButton = bridgeTarget.querySelector("[data-widget-id='btn-1']");
  const uiBridgeDomOk = Boolean(uiButton && uiButton.textContent === "Click");

  let uiBridgeEventOk = false;
  if (uiButton && typeof PointerEvent === "function") {
    const rect = uiButton.getBoundingClientRect();
    const x = rect.left + rect.width / 2;
    const y = rect.top + rect.height / 2;
    uiButton.dispatchEvent(
      new PointerEvent("pointerdown", { bubbles: true, clientX: x, clientY: y, button: 0, buttons: 1 })
    );
    uiButton.dispatchEvent(
      new PointerEvent("pointerup", { bubbles: true, clientX: x, clientY: y, button: 0, buttons: 0 })
    );

    const poll = pollUiEvents();
    const targetHit = poll.batch.events.some((evt) => evt.type === 1 && evt.targetId === "btn-1");
    uiBridgeEventOk =
      poll.status === 1 &&
      poll.count > 0 &&
      poll.size > 0 &&
      poll.copied === poll.size &&
      targetHit;
  }

  const fontBytes = encodeBridgeUtf8("12px monospace");
  const textBytes = encodeBridgeUtf8("Hello");
  const measPtr = 8192;
  const fontPtr = measPtr + 16;
  const textPtr = fontPtr + fontBytes.length + 8;
  writeUiBytes(fontPtr, fontBytes);
  writeUiBytes(textPtr, textBytes);
  const measView = new DataView(uiMemory.buffer, measPtr, 16);
  measView.setUint32(0, fontPtr, true);
  measView.setUint32(4, fontBytes.length, true);
  measView.setUint32(8, textPtr, true);
  measView.setUint32(12, textBytes.length, true);
  const measId = kernel_request(KERNEL_OP_UI_MEASURE_TEXT, measPtr, 16);
  const measResult = kernel_result(measId) | 0;
  const measSize = kernel_response_size(measId) >>> 0;
  let uiBridgeMeasureOk = false;
  if (measSize === 32) {
    const measOutPtr = textPtr + textBytes.length + 16;
    kernel_copy_response(measId, measOutPtr, measSize);
    const measDv = new DataView(uiMemory.buffer, measOutPtr, measSize);
    const width = measDv.getFloat64(0, true);
    const height = measDv.getFloat64(8, true);
    uiBridgeMeasureOk = measResult === 0 && width > 0 && height > 0;
  }
  kernel_drop_request(measId);

  const canvasInfo = buildUiBridgeCanvasPayload();
  const canvasPtr = 16384;
  writeUiBytes(canvasPtr, canvasInfo.payload);
  const canvasRenderId = kernel_request(KERNEL_OP_UI_RENDER, canvasPtr, canvasInfo.payload.length);
  const canvasRenderResult = kernel_result(canvasRenderId) | 0;
  kernel_drop_request(canvasRenderId);
  if (typeof uiBridge.flush === "function") {
    uiBridge.flush();
  }

  const bridgeCanvasNode = bridgeTarget.querySelector("[data-widget-id='canvas-1']");
  let uiBridgeCanvasOk = false;
  if (bridgeCanvasNode && typeof PointerEvent === "function") {
    const rect = bridgeCanvasNode.getBoundingClientRect();
    const x = rect.left + 12;
    const y = rect.top + 12;
    bridgeCanvasNode.dispatchEvent(
      new PointerEvent("pointerdown", { bubbles: true, clientX: x, clientY: y, button: 0, buttons: 1 })
    );
    bridgeCanvasNode.dispatchEvent(
      new PointerEvent("pointerup", { bubbles: true, clientX: x, clientY: y, button: 0, buttons: 0 })
    );
    const poll = pollUiEvents();
    const hit = poll.batch.events.some(
      (evt) => evt.type === 1 && typeof evt.targetId === "string" && evt.targetId.startsWith("canvas-1:")
    );
    uiBridgeCanvasOk = canvasRenderResult === 0 && hit;
  }

  const webglInfo = buildUiBridgeWebglPayload();
  const webglPtr = canvasPtr + canvasInfo.payload.length + 1024;
  writeUiBytes(webglPtr, webglInfo.payload);
  const webglRenderId = kernel_request(KERNEL_OP_UI_RENDER, webglPtr, webglInfo.payload.length);
  const webglRenderResult = kernel_result(webglRenderId) | 0;
  kernel_drop_request(webglRenderId);
  if (typeof uiBridge.flush === "function") {
    uiBridge.flush();
  }

  const bridgeWebglNode = bridgeTarget.querySelector("[data-widget-id='webgl-1']");
  let uiBridgeWebglOk = false;
  if (bridgeWebglNode && typeof PointerEvent === "function") {
    const rect = bridgeWebglNode.getBoundingClientRect();
    const x = rect.left + 14;
    const y = rect.top + 14;
    bridgeWebglNode.dispatchEvent(
      new PointerEvent("pointerdown", { bubbles: true, clientX: x, clientY: y, button: 0, buttons: 1 })
    );
    bridgeWebglNode.dispatchEvent(
      new PointerEvent("pointerup", { bubbles: true, clientX: x, clientY: y, button: 0, buttons: 0 })
    );
    const poll = pollUiEvents();
    const hit = poll.batch.events.some(
      (evt) => evt.type === 1 && typeof evt.targetId === "string" && evt.targetId.startsWith("webgl-1:")
    );
    if (!hit) {
      const ctx = bridgeWebglNode.getContext ? bridgeWebglNode.getContext("webgl") : null;
      uiBridgeWebglOk = webglRenderResult === 0 && ctx === null;
    } else {
      uiBridgeWebglOk = webglRenderResult === 0 && hit;
    }
  }

  const uiBridgeOk =
    uiBridgeRenderOk && uiBridgeDomOk && uiBridgeEventOk && uiBridgeMeasureOk && uiBridgeCanvasOk && uiBridgeWebglOk;

  let wasmUiOk = false;
  let wasmUiInfo = null;
  if (uiBundleOk) {
    try {
      const wasmBridgeTarget = document.createElement("div");
      wasmBridgeTarget.id = "wasm-ui-target";
      root.appendChild(wasmBridgeTarget);

      const wasmUiBridge = createUiBridge({ container: wasmBridgeTarget, document });
      const runtime = createSharedCclRuntime({
        memoryInitialPages: 256,
        subprimsTableInitial: 256
      });
      const wasmMicrokernel = createMicrokernel({
        memory: runtime.memory,
        uiService: wasmUiBridge,
        persistence: { backend: "memory-snapshot" }
      });

      const kernelBytes = await loadBytes("/doc/wasm/js/wasmcl.wasm");
      const kernel = await instantiateWasm(
        kernelBytes,
        createCclImports({
          memory: runtime.memory,
          subprimsTable: runtime.subprimsTable,
          microkernel: wasmMicrokernel
        })
      );
      const kernelExports = kernel.instance.exports;

      const subprimsBytes = await loadBytes("/doc/wasm/js/subprims.wasm");
      const subprimsMap = await loadJson("/doc/wasm/subprims-map.json");
      const subprims = await instantiateWasm(
        subprimsBytes,
        createCclImports({
          memory: runtime.memory,
          subprimsTable: runtime.subprimsTable,
          microkernel: wasmMicrokernel,
          extra: { ccl: kernelExports }
        })
      );

      installSubprimsTable({
        table: runtime.subprimsTable,
        subprimsMap,
        providers: [{ exports: kernelExports }, { exports: subprims.instance.exports }]
      });

      if (typeof kernelExports.wasm_set_subprims_ready !== "function") {
        throw new Error("missing wasm_set_subprims_ready export");
      }
      kernelExports.wasm_set_subprims_ready(1);

      if (typeof kernelExports.wasm_set_cstack_bounds !== "function" ||
          typeof kernelExports.wasm_ccl_load_image !== "function") {
        throw new Error("missing image load exports");
      }

      let imageBytes;
      try {
        imageBytes = new Uint8Array(await loadBytes("/doc/wasm/root.image"));
      } catch (_err) {
        imageBytes = new Uint8Array(await loadBytes("/doc/wasm/minimal.image"));
      }
      const imageLen = imageBytes.byteLength >>> 0;
      const pageSize = 65536;
      const cstackSize = 1 << 20;
      const reserve = 4 << 20;
      const needBytes = imageLen + cstackSize + reserve;
      let haveBytes = runtime.memory.buffer.byteLength;
      if (needBytes > haveBytes) {
        const growPages = Math.ceil((needBytes - haveBytes) / pageSize);
        runtime.memory.grow(growPages);
        haveBytes = runtime.memory.buffer.byteLength;
      }
      const cstackBase = runtime.memory.buffer.byteLength;
      kernelExports.wasm_set_cstack_bounds(cstackBase, cstackSize);
      const blobBase = (cstackBase - cstackSize - imageLen) & ~15;
      if (blobBase < 0) {
        throw new Error("not enough memory to place boot image below cstack");
      }
      new Uint8Array(runtime.memory.buffer).set(imageBytes, blobBase);
      kernelExports.wasm_ccl_load_image(blobBase, imageLen);
      if (typeof kernelExports.wasm_reset_root_image_runtime_state === "function") {
        const resetRc = kernelExports.wasm_reset_root_image_runtime_state() | 0;
        if (resetRc !== 0) {
          throw new Error(`wasm_reset_root_image_runtime_state failed: ${resetRc}`);
        }
      }

      const uiBundle = await loadJson("/doc/wasm/wasm-ui-modules.json");
      const uiModules = Array.isArray(uiBundle?.modules) ? uiBundle.modules : [];
      const uiFunctions = Array.isArray(uiBundle?.functions) ? uiBundle.functions : [];
      const kernelDemoTurn = typeof kernelExports.wasm_ui_demo_turn === "function"
        ? kernelExports.wasm_ui_demo_turn
        : null;

      const nilValue = typeof kernelExports.wasm_get_lisp_nil === "function"
        ? (kernelExports.wasm_get_lisp_nil() >>> 0)
        : 0;

      const uiImports = createCclImports({
        memory: runtime.memory,
        subprimsTable: runtime.subprimsTable,
        microkernel: wasmMicrokernel,
        extra: { ccl: kernelExports }
      });

      if (!kernelDemoTurn) {
        if (!uiModules.length) {
          throw new Error("wasm-ui-modules.json contains no modules");
        }
        for (const entry of uiModules) {
          if (entry.constPoolBytes?.length) {
            const poolResult = installConstPoolBytes({
              kernelExports,
              memory: runtime.memory,
              entryIndex: entry.entryIndex,
              constPoolBytes: entry.constPoolBytes
            });
            if ((poolResult >>> 0) === nilValue) {
              throw new Error(`const pool install failed for ${entry.exportName}`);
            }
            if (typeof kernelExports.wasm_pending_throw_p === "function" &&
                kernelExports.wasm_pending_throw_p() >>> 0) {
              throw new Error(`const pool install signaled pending throw for ${entry.exportName}`);
            }
          }
          const bytes = Uint8Array.from(entry.moduleBytes ?? []);
          const { instance } = await instantiateWasm(bytes, uiImports);
          const fn = instance?.exports?.[entry.exportName];
          if (typeof fn !== "function") {
            throw new Error(`compiled UI module missing export ${entry.exportName}`);
          }
          const idx = entry.entryIndex >>> 0;
          if (runtime.subprimsTable.length <= idx) {
            runtime.subprimsTable.grow(idx - runtime.subprimsTable.length + 1);
          }
          runtime.subprimsTable.set(idx, fn);
        }
      }

      const turnResults = [];
      let callWasmTurn = null;
      if (kernelDemoTurn) {
        callWasmTurn = () => {
          const res = kernelDemoTurn() | 0;
          turnResults.push(res);
          return res;
        };
      } else {
        const turnEntry = uiFunctions.find((fn) => fn?.name === "WASM-UI-TURN")?.entryIndex;
        if (turnEntry == null) {
          throw new Error("missing WASM-UI-TURN entry");
        }
        if (typeof kernelExports.wasm_test_entry_funcall !== "function") {
          throw new Error("missing wasm_test_entry_funcall export");
        }
        callWasmTurn = () => {
          const res = kernelExports.wasm_test_entry_funcall(turnEntry >>> 0, 0) >> 2;
          turnResults.push(res);
          return res;
        };
      }
      const flushWasmUi = () => {
        if (typeof wasmUiBridge.flush === "function") {
          wasmUiBridge.flush();
        }
      };
      const labelText = () =>
        wasmBridgeTarget.querySelector("[data-widget-id='demo-label']")?.textContent ?? "";
      const clickNode = (node, { offsetX, offsetY } = {}) => {
        if (!node || typeof PointerEvent !== "function") return false;
        const rect = node.getBoundingClientRect();
        if (rect.width <= 0 || rect.height <= 0) return false;
        const baseX = Number.isFinite(offsetX) ? offsetX : rect.width / 2;
        const baseY = Number.isFinite(offsetY) ? offsetY : rect.height / 2;
        const x = rect.left + Math.min(rect.width - 1, Math.max(1, baseX));
        const y = rect.top + Math.min(rect.height - 1, Math.max(1, baseY));
        node.dispatchEvent(
          new PointerEvent("pointerdown", { bubbles: true, clientX: x, clientY: y, button: 0, buttons: 1 })
        );
        node.dispatchEvent(
          new PointerEvent("pointerup", { bubbles: true, clientX: x, clientY: y, button: 0, buttons: 0 })
        );
        return true;
      };

      const initialResult = callWasmTurn();
      flushWasmUi();

      const wasmButton = wasmBridgeTarget.querySelector("[data-widget-id='demo-button']");
      const wasmLabel = wasmBridgeTarget.querySelector("[data-widget-id='demo-label']");
      const wasmCanvas = wasmBridgeTarget.querySelector("canvas[data-canvas-scene]");
      const wasmWebgl = wasmBridgeTarget.querySelector("canvas[data-webgl-scene]");
      const initialLabel = wasmLabel?.textContent ?? "";
      const initialOk =
        initialResult >= 0 &&
        Boolean(wasmButton && wasmLabel && initialLabel === "Ready" && wasmCanvas && wasmWebgl);

      let clickOk = false;
      let canvasOk = false;
      let webglOk = false;
      let clickLabel = null;
      let canvasLabel = null;
      let webglLabel = null;

      if (clickNode(wasmButton)) {
        const clickResult = callWasmTurn();
        flushWasmUi();
        clickLabel = labelText();
        clickOk = clickResult >= 0 && clickLabel === "Clicked";
      }

      if (clickNode(wasmCanvas, { offsetX: 10, offsetY: 10 })) {
        const canvasResult = callWasmTurn();
        flushWasmUi();
        canvasLabel = labelText();
        canvasOk =
          canvasResult >= 0 &&
          typeof canvasLabel === "string" &&
          canvasLabel.startsWith("Canvas ") &&
          canvasLabel.includes(":");
      }

      if (clickNode(wasmWebgl, { offsetX: 12, offsetY: 12 })) {
        const webglResult = callWasmTurn();
        flushWasmUi();
        webglLabel = labelText();
        const webglCtx = typeof wasmWebgl?.getContext === "function"
          ? wasmWebgl.getContext("webgl")
          : null;
        const expectsHitId = Boolean(webglCtx);
        webglOk =
          webglResult >= 0 &&
          typeof webglLabel === "string" &&
          webglLabel.startsWith("WebGL ") &&
          (expectsHitId ? webglLabel.includes(":") : true);
      }

      wasmUiOk = initialOk && clickOk && canvasOk && webglOk;
      wasmUiInfo = {
        turnResults,
        initialLabel,
        clickLabel,
        canvasLabel,
        webglLabel
      };
    } catch (err) {
      wasmUiInfo = { error: err?.message ?? String(err) };
    }
  } else {
    wasmUiInfo = { error: "missing wasm-ui-modules.json" };
  }

  const ok =
    uiBundleOk &&
    snapshotMatch &&
    domOk &&
    domSnapshotMatch &&
    domReuseOk &&
    commandDomOk &&
    commandInvokeOk &&
    commandInputOk &&
    commandListOk &&
    imeCompositionOkResolved &&
    imeCancelOkResolved &&
    imeMultiStepOkResolved &&
    imeSelectionOkResolved &&
    deadKeyOk &&
    mobileInputOk &&
    virtualListOk &&
    virtualTreeOk &&
    virtualTableOk &&
    canvasWidgetOk &&
    canvasWidgetCommandOk &&
    webglWidgetOk &&
    webglWidgetCommandOk &&
    focusOk &&
    measureOk &&
    hitTestOk &&
    captureEventsOk &&
    invalidateOk &&
    canvasOk &&
    canvasBackendHitOk &&
    canvasMeasureOk &&
    webglOk &&
    webglBackendHitOk &&
    webglMeasureOk &&
    persistenceOk &&
    uiBridgeOk &&
    wasmUiOk;
  const payload = {
    ok,
    uiBundleOk,
    uiBundleInfo,
    wasmUiOk,
    wasmUiInfo,
    snapshotMatch,
    domOk,
    domSnapshotMatch,
    domReuseOk,
    commandDomOk,
    commandInvokeOk,
    commandInputOk,
    commandListOk,
    imeCompositionOk: imeCompositionOkResolved,
    imeCancelOk: imeCancelOkResolved,
    imeMultiStepOk: imeMultiStepOkResolved,
    imeSelectionOk: imeSelectionOkResolved,
    deadKeyOk,
    mobileInputOk,
    virtualListOk,
    virtualTreeOk,
    virtualTableOk,
    canvasWidgetOk,
    canvasWidgetCommandOk,
    webglWidgetOk,
    webglWidgetCommandOk,
    focusOk,
    measureOk,
    hitTestOk,
    captureEventsOk,
    invalidateOk,
    canvasOk,
    canvasBackendHitOk,
    canvasMeasureOk,
    webglOk,
    webglBackendHitOk,
    webglMeasureOk,
    persistenceOk,
    uiBridgeOk,
    uiBridgeCanvasOk,
    uiBridgeWebglOk
  };

  if (window.__WEB_UI_TEST_DONE__) {
    window.__WEB_UI_TEST_DONE__(payload);
  } else {
    console.log("WEB_UI_TEST_RESULT", JSON.stringify(payload));
  }
}

run().catch((err) => {
  const payload = { ok: false, error: err.message };
  if (window.__WEB_UI_TEST_DONE__) {
    window.__WEB_UI_TEST_DONE__(payload);
  } else {
    console.error("WEB_UI_TEST_ERROR", payload);
  }
});
