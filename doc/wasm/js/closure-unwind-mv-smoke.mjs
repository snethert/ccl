/*
 * WASM32 closure + unwind-protect + MV>4 smoke test.
 *
 * Validates:
 *  1) Closure allocation captures and updates a closed-over var.
 *  2) unwind-protect preserves >4 multiple values through cleanup.
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
const bundleUrl = new URL("../wasm-smoke-modules.json", import.meta.url);

let bundle;
try {
  bundle = JSON.parse((await readFileUrl(bundleUrl)).toString("utf8"));
} catch (err) {
  fail("missing wasm-smoke-modules.json (run scripts/wasm/compile-smoke-modules.sh)");
}

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

const kernelExports = kernel.instance.exports;
const imports = createCclImports({
  memory: runtime.memory,
  subprimsTable: runtime.subprimsTable,
  microkernel,
  extra: { ccl: kernelExports },
});

const modules = Array.isArray(bundle.modules) ? bundle.modules : [];
const functions = Array.isArray(bundle.functions) ? bundle.functions : [];
assert(modules.length > 0, "wasm-smoke-modules.json contains no modules");

for (const entry of modules) {
  const bytes = Uint8Array.from(entry.moduleBytes ?? []);
  const { instance } = await instantiateWasm(bytes, imports);
  const fn = instance?.exports?.[entry.exportName];
  assert(typeof fn === "function", `compiled module missing export ${entry.exportName}`);
  const idx = entry.entryIndex >>> 0;
  if (runtime.subprimsTable.length <= idx) {
    runtime.subprimsTable.grow(idx - runtime.subprimsTable.length + 1);
  }
  runtime.subprimsTable.set(idx, fn);
}

function entryIndex(name) {
  const item = functions.find((fn) => fn.name === name);
  assert(item, `missing compiled function ${name}`);
  return item.entryIndex >>> 0;
}

assert(typeof kernelExports.wasm_test_entry_funcall === "function", "missing wasm_test_entry_funcall export");

const entry = entryIndex("WASM-SMOKE-CLOSURE-UNWIND-MV");
const result = kernelExports.wasm_test_entry_funcall(entry, 0) >> 2;
assert(result === 12, `unexpected closure/unwind/mv result: got=${result} expected=12`);

console.log("PASS: wasm closure/unwind-protect/mv>4 smoke test");
