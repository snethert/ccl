/*
 * GC forwarding arithmetic smoke test.
 *
 * Runs a deterministic stress/self-test in the kernel that validates
 * mark-word prefix counting used by dnode forwarding math.
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
  memoryInitialPages: 32,
  subprimsTableInitial: 512,
  createMemory: true,
});

const microkernel = createMicrokernel({
  memory: runtime.memory,
  writeStdout: () => {},
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

assert(
  typeof kernel.instance.exports.wasm_gc_forwarding_selftest === "function",
  "missing wasm_gc_forwarding_selftest export",
);

for (let i = 0; i < 4; i += 1) {
  const rc = kernel.instance.exports.wasm_gc_forwarding_selftest() >>> 0;
  assert(rc === 1, `forwarding selftest failed: iteration=${i} rc=${rc}`);
}

console.log("PASS: gc forwarding smoke test");
