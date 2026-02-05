import { replayEvents } from "../replay-harness.mjs";
import { snapshotToString, stableStringify } from "../snapshot.mjs";
import { createRegistry, registerCommand } from "../../src/commands.mjs";
import { createState, addTask, addWindow, addWidget } from "../../src/state.mjs";
import { createElement, createText } from "../../src/vdom.mjs";
import { renderWindow } from "../../src/widgets.mjs";
import { createDomRoot } from "../../backends/dom/renderer.mjs";

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

  const widgetRoot = createDomRoot(widgetRenderTarget, { document });
  widgetRoot.render(renderWindow(widgetState, "win-1", { registry }));

  const runButton = widgetRenderTarget.querySelector("[data-widget-id='btn-run']");
  const blockedButton = widgetRenderTarget.querySelector("[data-widget-id='btn-blocked']");
  const commandDomOk =
    runButton &&
    blockedButton &&
    runButton.getAttribute("data-command-id") === "demo.run" &&
    blockedButton.getAttribute("data-command-id") === "demo.blocked" &&
    blockedButton.disabled === true &&
    blockedButton.getAttribute("data-disabled-reason") === "Blocked";

  if (runButton) {
    runButton.click();
  }
  const commandInvokeOk = commandCalls === 1;

  const canvas = document.createElement("canvas");
  canvas.width = 10;
  canvas.height = 10;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#ff0000";
  ctx.fillRect(0, 0, 10, 10);
  const pixel = ctx.getImageData(5, 5, 1, 1).data;
  const canvasOk = pixel[0] === 255 && pixel[1] === 0 && pixel[2] === 0 && pixel[3] === 255;

  const ok =
    snapshotMatch &&
    domOk &&
    domSnapshotMatch &&
    domReuseOk &&
    commandDomOk &&
    commandInvokeOk &&
    canvasOk;
  const payload = {
    ok,
    snapshotMatch,
    domOk,
    domSnapshotMatch,
    domReuseOk,
    commandDomOk,
    commandInvokeOk,
    canvasOk
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
