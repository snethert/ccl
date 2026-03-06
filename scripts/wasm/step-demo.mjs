/*
 * Stage-2 stepping demo driver (Node).
 *
 * Runs the tiny explicit-step state machine exported by the kernel:
 *   - wasm_step_demo_step() returns BLOCKED when stdin read is PENDING
 *   - feedStdin() completes it
 *   - next step copies bytes and writes them to stdout via STREAM_WRITE
 *
 * This is an executable sketch to validate the yield/resume boundary.
 */

import fs from "node:fs/promises";
import { fileURLToPath } from "node:url";

import { createMicrokernel } from "./microkernel.mjs";
import { createCclImports, createSharedCclRuntime, instantiateWasm } from "./ccl-loader.mjs";

function fail(msg) {
  console.error(`FAIL: ${msg}`);
  process.exit(1);
}

function assert(cond, msg) {
  if (!cond) fail(msg);
}

function readFileUrl(url) {
  return fs.readFile(fileURLToPath(url));
}

const kernelUrl = new URL("../../../build/wasm32/kernel/wasmcl.wasm", import.meta.url);
const kernelBytes = await readFileUrl(kernelUrl);

const runtime = createSharedCclRuntime({
  memoryInitialPages: 8,
  subprimsTableInitial: 512,
  createMemory: true,
});

const stdoutChunks = [];
const microkernel = createMicrokernel({
  memory: runtime.memory,
  asyncStdin: true,
  writeStdout: (bytes) => stdoutChunks.push(Buffer.from(bytes)),
  writeStderr: () => {},
});

const kernel = await instantiateWasm(
  kernelBytes,
  createCclImports({
    memory: runtime.memory,
    subprimsTable: runtime.subprimsTable,
    microkernel,
  }),
);

const ex = kernel.instance.exports;
assert(typeof ex.wasm_step_demo_reset === "function", "missing wasm_step_demo_reset export");
assert(typeof ex.wasm_step_demo_step === "function", "missing wasm_step_demo_step export");

// Step codes (match lisp-kernel/wasm-step-demo.c).
const STEP_RUNNING = 0;
const STEP_BLOCKED = 1;
const STEP_DONE = 2;

ex.wasm_step_demo_reset();

let st = ex.wasm_step_demo_step() | 0;
assert(st === STEP_BLOCKED, `expected BLOCKED first step, got ${st}`);

const msg = Buffer.from("hello", "utf8");
microkernel.feedStdin(msg);

for (let i = 0; i < 16; i++) {
  st = ex.wasm_step_demo_step() | 0;
  if (st === STEP_DONE) break;
  assert(st === STEP_BLOCKED || st === STEP_RUNNING, `unexpected step status ${st}`);
}
assert(st === STEP_DONE, `expected DONE, got ${st}`);

const out = Buffer.concat(stdoutChunks);
assert(out.equals(msg), `unexpected stdout: got=${JSON.stringify(out.toString("utf8"))}`);

console.log("PASS: step demo");

