/*
 * WASM toplevel slot smoke test.
 *
 * Verifies that the kernel uses the TCR toplevel slot when the nrs
 * %toplevel-function% vcell is empty.
 */

import fs from "node:fs/promises";
import { fileURLToPath } from "node:url";

import { createMicrokernel } from "./microkernel.mjs";
import {
  createCclImports,
  createSharedCclRuntime,
  instantiateWasm,
  installCompiledModulesFromRegistry,
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

const kernelUrl = new URL("../../../build/wasm32/kernel/wasmcl.wasm", import.meta.url);
const kernelBytes = await readFileUrl(kernelUrl);

const imageUrl = new URL("../../../build/wasm32/images/minimal.image", import.meta.url);
const imageBytes = await readFileUrl(imageUrl);
const imageLen = imageBytes.byteLength >>> 0;

const subprimsUrl = new URL("../../../build/wasm32/subprims/subprims.wasm", import.meta.url);
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

assert(typeof ex.wasm_ccl_load_image === "function", "missing wasm_ccl_load_image export");
ex.wasm_ccl_load_image(blobBase, imageLen);

await installCompiledModulesFromRegistry({
  kernel: ex,
  memory: runtime.memory,
  subprimsTable: runtime.subprimsTable,
  microkernel,
});

const bootIndex = 200;
assert(typeof ex.wasm_boot_entry === "function", "missing wasm_boot_entry export");
if (runtime.subprimsTable.length <= bootIndex) {
  runtime.subprimsTable.grow(bootIndex - runtime.subprimsTable.length + 1);
}
runtime.subprimsTable.set(bootIndex, ex.wasm_boot_entry);

assert(typeof ex.wasm_run_toplevel === "function", "missing wasm_run_toplevel export");
const firstRc = ex.wasm_run_toplevel() | 0;
assert(firstRc === 0, `expected first toplevel exit rc=0, got ${firstRc}`);

const nilValue = ex.wasm_get_lisp_nil() >>> 0;
assert(typeof ex.wasm_get_current_tcr === "function", "missing wasm_get_current_tcr export");
assert(typeof ex.wasm_get_tcr_toplevel_function === "function", "missing wasm_get_tcr_toplevel_function export");
assert(typeof ex.wasm_set_tcr_toplevel_function === "function", "missing wasm_set_tcr_toplevel_function export");

const tcr = ex.wasm_get_current_tcr() >>> 0;
const slotBefore = ex.wasm_get_tcr_toplevel_function(tcr) >>> 0;
assert(slotBefore === nilValue, `expected empty toplevel slot, got 0x${slotBefore.toString(16)}`);

const fulltagMisc = 6;
const subtagFunction = 0x2a;
const header = (4 << 8) | subtagFunction;
const entryFixnum = (bootIndex << 2) >>> 0;
const fnObjAddr = (blobBase - 32) & ~7;
assert(fnObjAddr + 16 <= blobBase, "not enough reserve for test function object");

const view = new DataView(runtime.memory.buffer);
view.setUint32(fnObjAddr + 0, header, true);
view.setUint32(fnObjAddr + 4, entryFixnum, true);
view.setUint32(fnObjAddr + 8, entryFixnum, true);
view.setUint32(fnObjAddr + 12, 0, true);

const fnValue = (fnObjAddr + fulltagMisc) >>> 0;
ex.wasm_set_tcr_toplevel_function(tcr, fnValue);
const slotAfter = ex.wasm_get_tcr_toplevel_function(tcr) >>> 0;
assert(slotAfter === fnValue, `expected toplevel slot 0x${fnValue.toString(16)}, got 0x${slotAfter.toString(16)}`);

const secondRc = ex.wasm_run_toplevel() | 0;
assert(secondRc === 0, `expected slot-driven toplevel exit rc=0, got ${secondRc}`);

console.log("PASS: wasm toplevel slot smoke test");
