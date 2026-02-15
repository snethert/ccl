/*
 * WASM32 fixnum ops smoke test (mul/ash/logand/logior/logxor/lognot).
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

assert(typeof kernel.instance.exports.wasm_test_entry_funcall2 === "function", "missing wasm_test_entry_funcall2 export");

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

function ensureEntry(entryIndex) {
  const entry = entries.find((item) => item.entryIndex === entryIndex);
  assert(entry, `missing compiled module entry ${entryIndex}`);
}

ensureEntry(206);
ensureEntry(207);
ensureEntry(208);
ensureEntry(209);
ensureEntry(210);
ensureEntry(211);

const mulResult = kernel.instance.exports.wasm_test_entry_funcall2(206, 6, 7) >> 2;
assert(mulResult === 42, `unexpected fixnum mul result: got=${mulResult} expected=42`);

const ashLeft = kernel.instance.exports.wasm_test_entry_funcall2(207, 3, 2) >> 2;
assert(ashLeft === 12, `unexpected fixnum ash left result: got=${ashLeft} expected=12`);

const ashRight = kernel.instance.exports.wasm_test_entry_funcall2(207, 16, -2) >> 2;
assert(ashRight === 4, `unexpected fixnum ash right result: got=${ashRight} expected=4`);

const logandResult = kernel.instance.exports.wasm_test_entry_funcall2(208, 6, 3) >> 2;
assert(logandResult === (6 & 3), `unexpected fixnum logand result: got=${logandResult} expected=${6 & 3}`);

const logiorResult = kernel.instance.exports.wasm_test_entry_funcall2(209, 6, 3) >> 2;
assert(logiorResult === (6 | 3), `unexpected fixnum logior result: got=${logiorResult} expected=${6 | 3}`);

const logxorResult = kernel.instance.exports.wasm_test_entry_funcall2(210, 6, 3) >> 2;
assert(logxorResult === (6 ^ 3), `unexpected fixnum logxor result: got=${logxorResult} expected=${6 ^ 3}`);

const lognotResult = kernel.instance.exports.wasm_test_entry_funcall2(211, 5, 0) >> 2;
assert(lognotResult === ~5, `unexpected fixnum lognot result: got=${lognotResult} expected=${~5}`);

console.log("PASS: wasm fixnum ops smoke test");
