/**
 * Cold-load watchdog — interrupts hung WASM execution via V8 inspector.
 *
 * Used as a Worker thread. Monitors a SharedArrayBuffer heartbeat.
 * When an entry takes longer than the timeout, sends
 * Runtime.terminateExecution to the main thread's V8 inspector.
 *
 * workerData: { inspectorUrl: string, sab: SharedArrayBuffer, timeout: number }
 *
 * SAB layout (Int32Array):
 *   [0] = current entry index (0 = idle)
 *   [1] = arm timestamp low 32 bits (ms since epoch, wraps every ~49 days)
 *   [2] = kill count (incremented by watchdog on each termination)
 */

import { workerData, parentPort } from "node:worker_threads";

const { inspectorUrl, sab, timeout } = workerData;
const view = new Int32Array(sab);
const POLL_MS = 200;

let ws = null;
let wsReady = false;
let msgId = 1;

function connectInspector() {
  return new Promise((resolve, reject) => {
    ws = new WebSocket(inspectorUrl);
    ws.onopen = () => { wsReady = true; resolve(); };
    ws.onerror = (e) => reject(new Error(`WS error: ${e.message || e}`));
    ws.onclose = () => { wsReady = false; };
    ws.onmessage = () => {}; // ignore responses
  });
}

async function terminateExecution() {
  if (!ws || !wsReady) return false;
  const id = msgId++;
  ws.send(JSON.stringify({ id, method: "Runtime.terminateExecution" }));
  return true;
}

async function run() {
  try {
    await connectInspector();
    parentPort.postMessage({ event: "ready" });
  } catch (e) {
    parentPort.postMessage({ event: "error", msg: e.message });
    return;
  }

  // Poll loop: check heartbeat, terminate if stale
  setInterval(() => {
    const armTime = Atomics.load(view, 1);
    if (armTime === 0) return; // idle

    const now = Date.now() & 0x7FFFFFFF;
    let elapsed;
    if (now >= armTime) {
      elapsed = now - armTime;
    } else {
      // Wrapped
      elapsed = (0x7FFFFFFF - armTime) + now;
    }

    if (elapsed > timeout) {
      const entryIdx = Atomics.load(view, 0);
      parentPort.postMessage({ event: "timeout", entry: entryIdx, elapsed });
      // Increment kill count
      Atomics.add(view, 2, 1);
      // Disarm to avoid repeated termination
      Atomics.store(view, 1, 0);
      // Terminate WASM execution
      terminateExecution();
    }
  }, POLL_MS);
}

run();
