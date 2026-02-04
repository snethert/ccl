/*
 * Node-first kernel_request smoke test.
 *
 * Validates that the WASM kernel can call the JS microkernel via the
 * kernel_request ABI, including copy-based response transfer.
 */

import fs from "node:fs/promises";
import { fileURLToPath } from "node:url";

import { createMicrokernel, KERNEL_ABI_VERSION } from "./microkernel.mjs";
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

const kernelUrl = new URL("./wasmcl.wasm", import.meta.url);
const kernelBytes = await readFileUrl(kernelUrl);

const runtime = createSharedCclRuntime({
  memoryInitialPages: 8, // 512 KiB is enough for this test
  // The kernel links against an imported indirect function table with a
  // non-trivial minimum size (subprims slots). Leave plenty of room.
  subprimsTableInitial: 256,
  createMemory: true,
});

const stdoutChunks = [];
const stderrChunks = [];
const microkernel = createMicrokernel({
  memory: runtime.memory,
  writeStdout: (bytes) => stdoutChunks.push(new Uint8Array(bytes)),
  writeStderr: (bytes) => stderrChunks.push(new Uint8Array(bytes)),
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
  typeof kernel.instance.exports.wasm_kernel_caps_abi_version === "function",
  "missing wasm_kernel_caps_abi_version export",
);
const abiVersion = kernel.instance.exports.wasm_kernel_caps_abi_version() >>> 0;
assert(abiVersion === KERNEL_ABI_VERSION, `unexpected ABI version: got=${abiVersion} want=${KERNEL_ABI_VERSION}`);

assert(
  typeof kernel.instance.exports.wasm_kernel_request_smoke_write === "function",
  "missing wasm_kernel_request_smoke_write export",
);
const wrote = kernel.instance.exports.wasm_kernel_request_smoke_write(1) | 0;
assert(wrote > 0, `expected write to succeed, got ${wrote}`);

const out = Buffer.concat(stdoutChunks.map((u8) => Buffer.from(u8)));
assert(out.toString("utf8") === "kernel_request smoke write\n", `unexpected stdout: ${JSON.stringify(out.toString("utf8"))}`);
assert(stderrChunks.length === 0, "unexpected stderr output");

console.log("PASS: kernel_request smoke test");
