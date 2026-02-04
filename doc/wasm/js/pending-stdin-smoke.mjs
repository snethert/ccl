/*
 * Node-first Stage-2 smoke test: PENDING stdin reads.
 *
 * Validates that:
 *  - STREAM_READ may return PENDING when no input is available,
 *  - the request completes when stdin is fed or closed,
 *  - the kernel can poll/result/copy/drop using the manual request lifecycle helpers.
 */

import fs from "node:fs/promises";
import { fileURLToPath } from "node:url";

import { createMicrokernel, KERNEL_STATUS_DONE, KERNEL_STATUS_ERROR, KERNEL_STATUS_PENDING } from "./microkernel.mjs";
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
  memoryInitialPages: 8,
  subprimsTableInitial: 256,
  createMemory: true,
});

const microkernel = createMicrokernel({
  memory: runtime.memory,
  asyncStdin: true,
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

const ex = kernel.instance.exports;

assert(
  typeof ex.wasm_kernel_request_smoke_begin_stdin_read === "function",
  "missing wasm_kernel_request_smoke_begin_stdin_read export",
);
assert(typeof ex.wasm_kernel_request_smoke_poll === "function", "missing wasm_kernel_request_smoke_poll export");
assert(typeof ex.wasm_kernel_request_smoke_result === "function", "missing wasm_kernel_request_smoke_result export");
assert(typeof ex.wasm_kernel_request_smoke_copy_response === "function", "missing wasm_kernel_request_smoke_copy_response export");
assert(typeof ex.wasm_kernel_request_smoke_drop === "function", "missing wasm_kernel_request_smoke_drop export");

// ---- Case 1: pending -> feed -> done ----
const rid1 = ex.wasm_kernel_request_smoke_begin_stdin_read(16) >>> 0;
assert(rid1 !== 0, "expected non-zero request id");
assert((ex.wasm_kernel_request_smoke_poll(rid1) >>> 0) === KERNEL_STATUS_PENDING, "expected PENDING read");

const msg = Buffer.from("abc", "utf8");
microkernel.feedStdin(msg);

assert((ex.wasm_kernel_request_smoke_poll(rid1) >>> 0) === KERNEL_STATUS_DONE, "expected DONE after feedStdin");
const r1 = ex.wasm_kernel_request_smoke_result(rid1) | 0;
assert(r1 === msg.length, `unexpected read result: got=${r1} want=${msg.length}`);

const dstCap = 64;
const dstPtr = (runtime.memory.buffer.byteLength - dstCap - 16) >>> 0;
const copied1 = ex.wasm_kernel_request_smoke_copy_response(rid1, dstPtr, dstCap) | 0;
assert(copied1 === msg.length, `unexpected copy count: got=${copied1} want=${msg.length}`);
{
  const got = Buffer.from(new Uint8Array(runtime.memory.buffer, dstPtr, copied1));
  assert(got.equals(msg), `unexpected bytes: got=${got.toString("utf8")} want=${msg.toString("utf8")}`);
}
ex.wasm_kernel_request_smoke_drop(rid1);

// After drop, poll should report ERROR (invalid request id).
assert((ex.wasm_kernel_request_smoke_poll(rid1) >>> 0) === KERNEL_STATUS_ERROR, "expected ERROR after drop");

// ---- Case 2: pending -> close -> EOF ----
const rid2 = ex.wasm_kernel_request_smoke_begin_stdin_read(16) >>> 0;
assert(rid2 !== 0, "expected non-zero request id (rid2)");
assert((ex.wasm_kernel_request_smoke_poll(rid2) >>> 0) === KERNEL_STATUS_PENDING, "expected PENDING read (rid2)");

microkernel.closeStdin();

assert((ex.wasm_kernel_request_smoke_poll(rid2) >>> 0) === KERNEL_STATUS_DONE, "expected DONE after closeStdin");
const r2 = ex.wasm_kernel_request_smoke_result(rid2) | 0;
assert(r2 === 0, `unexpected EOF result: got=${r2} want=0`);
const copied2 = ex.wasm_kernel_request_smoke_copy_response(rid2, dstPtr, dstCap) | 0;
assert(copied2 === 0, `unexpected EOF response bytes: got=${copied2} want=0`);
ex.wasm_kernel_request_smoke_drop(rid2);

console.log("PASS: pending stdin smoke test");

