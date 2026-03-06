/*
 * Stream lifecycle smoke test (STREAM_OPEN / STREAM_CLOSE).
 *
 * Validates that the WASM kernel can allocate a non-standard stream SID,
 * perform I/O on it, close it, and observe EBADF afterwards.
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
  memoryInitialPages: 17, // kernel declares min 17 pages
  subprimsTableInitial: 512,
  createMemory: true,
});

const microkernel = createMicrokernel({
  memory: runtime.memory,
});

const namedBytes = new Uint8Array([0x00, 0x11, 0x22, 0x33, 0xaa, 0xbb, 0xcc, 0xdd]);
microkernel.registerNamedBlob("named.bin", namedBytes);

const kernel = await instantiateWasm(
  kernelBytes,
  createCclImports({
    memory: runtime.memory,
    subprimsTable: runtime.subprimsTable,
    microkernel,
  }),
);

assert(
  typeof kernel.instance.exports.wasm_kernel_request_smoke_pipe_roundtrip === "function",
  "missing wasm_kernel_request_smoke_pipe_roundtrip export",
);
assert(
  typeof kernel.instance.exports.wasm_kernel_request_smoke_named_roundtrip === "function",
  "missing wasm_kernel_request_smoke_named_roundtrip export",
);

const r = kernel.instance.exports.wasm_kernel_request_smoke_pipe_roundtrip() | 0;
assert(r === 0, `expected pipe roundtrip success, got ${r}`);

const r2 = kernel.instance.exports.wasm_kernel_request_smoke_named_roundtrip() | 0;
assert(r2 === 0, `expected named stream roundtrip success, got ${r2}`);

console.log("PASS: stream open/close smoke test");
