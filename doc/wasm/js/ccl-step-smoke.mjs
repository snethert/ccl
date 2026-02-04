/*
 * Stage-2 stepping smoke test (wasm_ccl_step).
 *
 * Drives the exported stepping API from doc/wasm/yield-resume.md against the
 * reference JS microkernel with asyncStdin enabled (PENDING reads).
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

const STEP_RUNNING = 0;
const STEP_BLOCKED = 1;
const STEP_EXITED = 2;
const STEP_TRAPPED = 3;

const kernelUrl = new URL("./wasmcl.wasm", import.meta.url);
const kernelBytes = await readFileUrl(kernelUrl);

const runtime = createSharedCclRuntime({
  memoryInitialPages: 8,
  subprimsTableInitial: 256,
  createMemory: true,
});

const stdoutChunks = [];
const microkernel = createMicrokernel({
  memory: runtime.memory,
  asyncStdin: true,
  writeStdout: (bytes) => stdoutChunks.push(new Uint8Array(bytes)),
  writeStderr: (_bytes) => {},
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
assert(typeof ex.wasm_ccl_init === "function", "missing wasm_ccl_init export");
assert(typeof ex.wasm_ccl_step === "function", "missing wasm_ccl_step export");
assert(typeof ex.wasm_ccl_blocked_request_id === "function", "missing wasm_ccl_blocked_request_id export");
assert(typeof ex.wasm_ccl_exit_code === "function", "missing wasm_ccl_exit_code export");
assert(typeof ex.wasm_ccl_last_error === "function", "missing wasm_ccl_last_error export");

const initr = ex.wasm_ccl_init() | 0;
assert(initr === 0, `expected init success, got ${initr}`);

let st = ex.wasm_ccl_step(0) | 0;
assert(st === STEP_BLOCKED, `expected initial step to block, got ${st}`);
{
  const blocked = ex.wasm_ccl_blocked_request_id() >>> 0;
  assert(blocked !== 0, "expected non-zero blocked request id (PENDING read)");
}

const input = new TextEncoder().encode("hello\n");
microkernel.feedStdin(input);

st = ex.wasm_ccl_step(0) | 0;
assert(st === STEP_RUNNING, `expected step to run after stdin feed, got ${st}`);

st = ex.wasm_ccl_step(0) | 0;
assert(st === STEP_BLOCKED, `expected to block again waiting for stdin, got ${st}`);

microkernel.closeStdin();
st = ex.wasm_ccl_step(0) | 0;
assert(st === STEP_EXITED, `expected exit after stdin close, got ${st}`);

assert((ex.wasm_ccl_exit_code() | 0) === 0, "expected exit code 0");
assert((ex.wasm_ccl_last_error() | 0) === 0, "expected no trapped error");

const out = Buffer.concat(stdoutChunks.map((u8) => Buffer.from(u8)));
assert(out.toString("utf8") === "hello\n", `unexpected stdout: ${JSON.stringify(out.toString("utf8"))}`);

console.log("PASS: wasm_ccl_step smoke test");

