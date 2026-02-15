/*
 * WASM32 subprim non-local-exit coherence smoke test.
 *
 * Validates deterministic kernel selftest coverage for throw/unwind boundaries:
 *  1) direct mkcatch/nthrow single-value unwind
 *  2) funcall-driven nthrow unwind that returns with pending throw
 *  3) save-vsp/cstack/last-lisp-frame coherence after each boundary pass
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

const kernelUrl = new URL("../../../build/wasm32/kernel/wasmcl.wasm", import.meta.url);
const subprimsUrl = new URL("../../../build/wasm32/subprims/subprims.wasm", import.meta.url);
const subprimsMapUrl = new URL("../../../build/wasm32/subprims-map.json", import.meta.url);
const imageUrl = new URL("../../../build/wasm32/images/minimal.image", import.meta.url);

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

assert(typeof kernel.instance.exports.wasm_set_cstack_bounds === "function", "missing wasm_set_cstack_bounds export");
assert(typeof kernel.instance.exports.wasm_get_cstack_pointer === "function", "missing wasm_get_cstack_pointer export");
assert(
  typeof kernel.instance.exports.wasm_subprim_nonlocal_exit_coherence_selftest === "function",
  "missing wasm_subprim_nonlocal_exit_coherence_selftest export",
);
assert(typeof kernel.instance.exports.wasm_ccl_load_image === "function", "missing wasm_ccl_load_image export");

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
  const rc = kernel.instance.exports.wasm_subprim_nonlocal_exit_coherence_selftest() >>> 0;
  assert(rc === 1, `subprim non-local-exit coherence selftest failed: iteration=${i} rc=${rc}`);
  const sp = kernel.instance.exports.wasm_get_cstack_pointer() >>> 0;
  assert(sp === initialSp, `cstack pointer drift after non-local-exit selftest: iteration=${i} got=${sp} expected=${initialSp}`);
}

console.log("PASS: wasm subprim non-local-exit coherence smoke test");
