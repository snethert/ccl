import { replayEvents } from "../replay-harness.mjs";
import { snapshotToString, stableStringify } from "../snapshot.mjs";

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

  const result = replayEvents(initialState, eventLog.events);
  const snapshot = snapshotToString(result.snapshots[0]);
  const snapshotMatch = snapshot === stableStringify(expectedSnapshot);

  const root = document.getElementById("root");
  root.textContent = "ok";
  const domOk = root.textContent === "ok";

  const canvas = document.createElement("canvas");
  canvas.width = 10;
  canvas.height = 10;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#ff0000";
  ctx.fillRect(0, 0, 10, 10);
  const pixel = ctx.getImageData(5, 5, 1, 1).data;
  const canvasOk = pixel[0] === 255 && pixel[1] === 0 && pixel[2] === 0 && pixel[3] === 255;

  const ok = snapshotMatch && domOk && canvasOk;
  const payload = { ok, snapshotMatch, domOk, canvasOk };

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
