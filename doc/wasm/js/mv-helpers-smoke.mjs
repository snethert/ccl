/*
 * WASM32 multi-value helpers smoke test.
 *
 * Validates:
 *  1) wasm_return_values3/4 set nargs + VSP for multiple values
 *  2) wasm_get_mv + wasm_get_mv_indexed read back values
 *  3) wasm_restore_vsp pops values
 */

import fs from "node:fs/promises";
import { fileURLToPath } from "node:url";

import {
  createCclImports,
  createSharedCclRuntime,
  installSubprimsTable,
  instantiateWasm,
} from "./ccl-loader.mjs";
import { createMicrokernel } from "./microkernel.mjs";

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
const subprimsUrl = new URL("./subprims.wasm", import.meta.url);
const subprimsMapUrl = new URL("../subprims-map.json", import.meta.url);
const imageUrl = new URL("../minimal.image", import.meta.url);

const runtime = createSharedCclRuntime({
  memoryInitialPages: 256,
  subprimsTableInitial: 256,
});

const microkernel = createMicrokernel({
  memory: runtime.memory,
  writeStdout: () => {},
  writeStderr: () => {},
});

const kernelBytes = await readFileUrl(kernelUrl);
const kernel = await instantiateWasm(
  kernelBytes,
  createCclImports({
    memory: runtime.memory,
    subprimsTable: runtime.subprimsTable,
    microkernel,
  }),
);

const subprimsBytes = await readFileUrl(subprimsUrl);
const subprimsMap = JSON.parse((await readFileUrl(subprimsMapUrl)).toString("utf8"));
const subprims = await instantiateWasm(
  subprimsBytes,
  createCclImports({
    memory: runtime.memory,
    subprimsTable: runtime.subprimsTable,
    microkernel,
    extra: { ccl: kernel.instance.exports },
  }),
);

installSubprimsTable({
  table: runtime.subprimsTable,
  subprimsMap,
  providers: [{ exports: kernel.instance.exports }, { exports: subprims.instance.exports }],
});

assert(typeof kernel.instance.exports.wasm_set_subprims_ready === "function", "missing wasm_set_subprims_ready export");
kernel.instance.exports.wasm_set_subprims_ready(1);

assert(typeof kernel.instance.exports.wasm_return_values3 === "function", "missing wasm_return_values3 export");
assert(typeof kernel.instance.exports.wasm_return_values4 === "function", "missing wasm_return_values4 export");
assert(typeof kernel.instance.exports.wasm_get_mv === "function", "missing wasm_get_mv export");
assert(typeof kernel.instance.exports.wasm_get_mv_indexed === "function", "missing wasm_get_mv_indexed export");
assert(typeof kernel.instance.exports.wasm_restore_vsp === "function", "missing wasm_restore_vsp export");

const imageBytes = await readFileUrl(imageUrl);
const imageLen = imageBytes.byteLength >>> 0;

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

assert(typeof kernel.instance.exports.wasm_set_cstack_bounds === "function", "missing wasm_set_cstack_bounds export");
const cstackBase = runtime.memory.buffer.byteLength;
kernel.instance.exports.wasm_set_cstack_bounds(cstackBase, cstackSize);

const blobBase = (cstackBase - cstackSize - imageLen) & ~15;
assert(blobBase >= 0, "not enough memory to place boot image below cstack");
new Uint8Array(runtime.memory.buffer).set(imageBytes, blobBase);

assert(typeof kernel.instance.exports.wasm_ccl_load_image === "function", "missing wasm_ccl_load_image export");
kernel.instance.exports.wasm_ccl_load_image(blobBase, imageLen);

const fixnumShift = 2;
const nilValue = kernel.instance.exports.wasm_get_lisp_nil() >>> 0;

const f0 = (10 << fixnumShift) >>> 0;
const f1 = (20 << fixnumShift) >>> 0;
const f2 = (30 << fixnumShift) >>> 0;
const f3 = (40 << fixnumShift) >>> 0;

const ret3 = kernel.instance.exports.wasm_return_values3(f0, f1, f2) >>> 0;
assert(ret3 === f0, "unexpected return from wasm_return_values3");
assert(kernel.instance.exports.wasm_get_mv(0) >>> 0 === f0, "mv[0] mismatch for values3");
assert(kernel.instance.exports.wasm_get_mv(1) >>> 0 === f1, "mv[1] mismatch for values3");
assert(kernel.instance.exports.wasm_get_mv(2) >>> 0 === f2, "mv[2] mismatch for values3");
assert(kernel.instance.exports.wasm_get_mv(3) >>> 0 === nilValue, "mv[3] should be NIL for values3");

kernel.instance.exports.wasm_restore_vsp();
assert(kernel.instance.exports.wasm_get_mv(1) >>> 0 === nilValue, "mv[1] should be NIL after restore");

const ret4 = kernel.instance.exports.wasm_return_values4(f0, f1, f2, f3) >>> 0;
assert(ret4 === f0, "unexpected return from wasm_return_values4");
const idx2 = (2 << fixnumShift) >>> 0;
const idx3 = (3 << fixnumShift) >>> 0;
assert(kernel.instance.exports.wasm_get_mv_indexed(idx2) >>> 0 === f2, "indexed mv[2] mismatch");
assert(kernel.instance.exports.wasm_get_mv_indexed(idx3) >>> 0 === f3, "indexed mv[3] mismatch");
assert(kernel.instance.exports.wasm_get_mv(4) >>> 0 === nilValue, "mv[4] should be NIL for values4");

kernel.instance.exports.wasm_restore_vsp();

console.log("PASS: wasm multi-value helpers smoke test");
