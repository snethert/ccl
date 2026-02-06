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

async function loadJson(relPath) {
  const response = await fetch(relPath);
  if (!response.ok) {
    throw new Error(`Failed to load ${relPath}: ${response.status}`);
  }
  return response.json();
}

async function run() {
  const initialState = await loadJson("../fixtures/basic-state.json");
  const eventLog = await loadJson("../fixtures/basic-events.json");
  const expectedSnapshot = await loadJson("../fixtures/basic-snapshot.json");
  const expectedDomSnapshot = await loadJson("../fixtures/dom-snapshot.json");

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

  const ok =
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
    persistenceOk;
  const payload = {
    ok,
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
    persistenceOk
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
