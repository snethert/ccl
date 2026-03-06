/*
 * WASM kernel smoke test for file stream seek/truncate.
 *
 * Validates that the C-side lisp_open/lisp_lseek/lisp_ftruncate path works
 * through the kernel_request file stream backend.
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
  persistence: true,
});

const kernel = await instantiateWasm(
  kernelBytes,
  createCclImports({
    memory: runtime.memory,
    subprimsTable: runtime.subprimsTable,
    microkernel,
  }),
);

assert(
  typeof kernel.instance.exports.wasm_kernel_request_smoke_file_seek_truncate === "function",
  "missing wasm_kernel_request_smoke_file_seek_truncate export",
);

const r = kernel.instance.exports.wasm_kernel_request_smoke_file_seek_truncate() | 0;
assert(r === 0, `expected seek/truncate smoke success, got ${r}`);

console.log("PASS: wasm file seek/truncate smoke test");
