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
  const listItem = widgetRenderTarget.querySelector("[data-item-id='alpha']");
  const commandDomOk =
    runButton &&
    blockedButton &&
    input &&
    listItem &&
    runButton.getAttribute("data-command-id") === "demo.run" &&
    blockedButton.getAttribute("data-command-id") === "demo.blocked" &&
    blockedButton.disabled === true &&
    blockedButton.getAttribute("data-disabled-reason") === "Blocked" &&
    input.getAttribute("data-command-id") === "demo.input" &&
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

  const ok =
    snapshotMatch &&
    domOk &&
    domSnapshotMatch &&
    domReuseOk &&
    commandDomOk &&
    commandInvokeOk &&
    commandInputOk &&
    commandListOk &&
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
    webglMeasureOk;
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
    webglMeasureOk
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
