/*
 * C-stack/Lisp-frame coherence smoke test.
 *
 * Runs a deterministic kernel self-test that validates:
 *  1) nested host frame enter/exit behavior
 *  2) unwind-style exit path when the top frame was already popped
 *  3) save-vsp and cstack pointer restoration invariants
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
const imageUrl = new URL("../../../build/wasm32/images/minimal.image", import.meta.url);
const kernelBytes = await readFileUrl(kernelUrl);
const imageBytes = await readFileUrl(imageUrl);
const imageLen = imageBytes.byteLength >>> 0;

const runtime = createSharedCclRuntime({
  memoryInitialPages: 64,
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
  typeof kernel.instance.exports.wasm_set_cstack_bounds === "function",
  "missing wasm_set_cstack_bounds export",
);
assert(
  typeof kernel.instance.exports.wasm_get_cstack_pointer === "function",
  "missing wasm_get_cstack_pointer export",
);
assert(
  typeof kernel.instance.exports.wasm_cstack_frame_coherence_selftest === "function",
  "missing wasm_cstack_frame_coherence_selftest export",
);

assert(
  typeof kernel.instance.exports.wasm_ccl_load_image === "function",
  "missing wasm_ccl_load_image export",
);

const pageSize = 65536;
const cstackSize = 1 << 20;
const reserve = 4 << 20;
const needBytes = imageLen + cstackSize + reserve;
let haveBytes = runtime.memory.buffer.byteLength;
if (needBytes > haveBytes) {
  const growPages = Math.ceil((needBytes - haveBytes) / pageSize);
  runtime.memory.grow(growPages);
  haveBytes = runtime.memory.buffer.byteLength;
}

const cstackBase = runtime.memory.buffer.byteLength >>> 0;
assert(cstackBase > cstackSize, `memory too small for cstack bounds: base=${cstackBase} size=${cstackSize}`);
kernel.instance.exports.wasm_set_cstack_bounds(cstackBase, cstackSize);

const blobBase = (cstackBase - cstackSize - imageLen) & ~15;
assert(blobBase >= 0, "not enough memory to place boot image below cstack");
new Uint8Array(runtime.memory.buffer).set(imageBytes, blobBase);
kernel.instance.exports.wasm_ccl_load_image(blobBase, imageLen);

const initialSp = kernel.instance.exports.wasm_get_cstack_pointer() >>> 0;
assert(initialSp !== 0, "unexpected zero cstack pointer after image load");

for (let i = 0; i < 4; i += 1) {
  const rc = kernel.instance.exports.wasm_cstack_frame_coherence_selftest() >>> 0;
  assert(rc === 1, `cstack frame coherence selftest failed: iteration=${i} rc=${rc}`);
  const sp = kernel.instance.exports.wasm_get_cstack_pointer() >>> 0;
  assert(sp === initialSp, `cstack pointer drift after selftest: iteration=${i} got=${sp} expected=${initialSp}`);
}

console.log("PASS: cstack frame coherence smoke test");
