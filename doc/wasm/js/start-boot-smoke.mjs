/*
 * Boot+start smoke test (wasm_set_boot_image + wasm_ccl_start).
 *
 * Uses the minimal image to exercise the direct boot path that enters
 * start_lisp as part of wasm_ccl_start.
 */

import fs from "node:fs/promises";
import { fileURLToPath } from "node:url";

import { createMicrokernel } from "./microkernel.mjs";
import {
  createCclImports,
  createSharedCclRuntime,
  instantiateWasm,
  installSubprimsTable,
} from "./ccl-loader.mjs";

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

const imageUrl = new URL("../minimal.image", import.meta.url);
const imageBytes = await readFileUrl(imageUrl);
const imageLen = imageBytes.byteLength >>> 0;

const subprimsUrl = new URL("./subprims.wasm", import.meta.url);
const subprimsBytes = await readFileUrl(subprimsUrl);
const subprimsMapUrl = new URL("../../../build/wasm32/subprims-map.json", import.meta.url);
const subprimsMap = JSON.parse(await fs.readFile(fileURLToPath(subprimsMapUrl), "utf-8"));

const runtime = createSharedCclRuntime({
  memoryInitialPages: 256,
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

const ex = kernel.instance.exports;
if (typeof ex.wasm_set_subprims_ready === "function") {
  ex.wasm_set_subprims_ready(1);
}

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

assert(typeof ex.wasm_set_cstack_bounds === "function", "missing wasm_set_cstack_bounds export");
const cstackBase = runtime.memory.buffer.byteLength;
ex.wasm_set_cstack_bounds(cstackBase, cstackSize);

const blobBase = (cstackBase - cstackSize - imageLen) & ~15;
assert(blobBase >= 0, "not enough memory to place boot image below cstack");
new Uint8Array(runtime.memory.buffer).set(imageBytes, blobBase);

assert(typeof ex.wasm_set_boot_image === "function", "missing wasm_set_boot_image export");
ex.wasm_set_boot_image(blobBase, imageLen);

const bootIndex = 200;
assert(typeof ex.wasm_boot_entry === "function", "missing wasm_boot_entry export");
if (runtime.subprimsTable.length <= bootIndex) {
  runtime.subprimsTable.grow(bootIndex - runtime.subprimsTable.length + 1);
}
runtime.subprimsTable.set(bootIndex, ex.wasm_boot_entry);

assert(typeof ex.wasm_ccl_start === "function", "missing wasm_ccl_start export");
const rc = ex.wasm_ccl_start() | 0;
assert(rc === 0, `expected wasm_ccl_start rc=0, got ${rc}`);

console.log("PASS: wasm_ccl_start boot smoke test");
