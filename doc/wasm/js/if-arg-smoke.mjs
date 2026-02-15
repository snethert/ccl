/*
 * WASM32 if-arg smoke test.
 *
 * Validates:
 *  1) Compiled module registry installs if-arg entry into the table
 *  2) if returns arg_z when non-NIL, else returns the embedded constant
 */

import fs from "node:fs/promises";
import { fileURLToPath } from "node:url";

import {
  createCclImports,
  createSharedCclRuntime,
  installCompiledModulesFromRegistry,
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
const subprimsMapUrl = new URL("../../../build/wasm32/subprims-map.json", import.meta.url);
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

assert(
  typeof kernel.instance.exports.wasm_test_entry_funcall1_raw === "function",
  "missing wasm_test_entry_funcall1_raw export",
);

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

const { installed, entries } = await installCompiledModulesFromRegistry({
  kernel: kernel.instance.exports,
  memory: runtime.memory,
  subprimsTable: runtime.subprimsTable,
  microkernel,
});
assert(installed > 0, "no compiled modules installed");

const entryIndex = 214;
const entry = entries.find((item) => item.entryIndex === entryIndex);
assert(entry, `missing compiled module entry ${entryIndex}`);

const nilValue = kernel.instance.exports.wasm_get_lisp_nil() >>> 0;
const elseFixnum = 17;
const elseValue = (elseFixnum << 2) >>> 0;

const fixnumShift = 2;
const testValue = (9 << fixnumShift) >>> 0;

const resultTrue = kernel.instance.exports.wasm_test_entry_funcall1_raw(entryIndex, testValue) >>> 0;
assert(resultTrue === testValue, `unexpected true branch result: got=0x${resultTrue.toString(16)} expected=0x${testValue.toString(16)}`);

const resultFalse = kernel.instance.exports.wasm_test_entry_funcall1_raw(entryIndex, nilValue) >>> 0;
assert(resultFalse === elseValue, `unexpected false branch result: got=0x${resultFalse.toString(16)} expected=0x${elseValue.toString(16)}`);

console.log("PASS: wasm if-arg smoke test");
