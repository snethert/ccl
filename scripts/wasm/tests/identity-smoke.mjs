/*
 * WASM32 identity smoke test.
 *
 * Validates:
 *  1) Compiled module registry installs identity entry into the table
 *  2) identity returns arg_z
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
import path from "node:path";
import { ensureSubprimsMap } from "../lib/ensure-subprims-map.mjs";

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
const imageUrl = new URL("../../../build/wasm32/images/minimal.image", import.meta.url);

const runtime = createSharedCclRuntime({
  memoryInitialPages: 256,
  subprimsTableInitial: 512,
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
const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const subprimsMap = await ensureSubprimsMap(repoRoot);
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

const entryIndex = 215;
const entry = entries.find((item) => item.entryIndex === entryIndex);
assert(entry, `missing compiled module entry ${entryIndex}`);

const fixnumShift = 2;
const testValue = (42 << fixnumShift) >>> 0;
const nilValue = kernel.instance.exports.wasm_get_lisp_nil() >>> 0;

const resultValue = kernel.instance.exports.wasm_test_entry_funcall1_raw(entryIndex, testValue) >>> 0;
assert(resultValue === testValue, `unexpected identity result: got=0x${resultValue.toString(16)} expected=0x${testValue.toString(16)}`);

const resultNil = kernel.instance.exports.wasm_test_entry_funcall1_raw(entryIndex, nilValue) >>> 0;
assert(resultNil === nilValue, `unexpected identity nil result: got=0x${resultNil.toString(16)} expected=0x${nilValue.toString(16)}`);

console.log("PASS: wasm identity smoke test");
