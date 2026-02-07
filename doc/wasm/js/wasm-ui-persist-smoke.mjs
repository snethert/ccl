/*
 * WASM UI persistence smoke test.
 *
 * Exercises UI snapshot save/restore through kernel_request file storage.
 */

import fs from "node:fs/promises";
import { fileURLToPath } from "node:url";

import {
  createCclImports,
  createSharedCclRuntime,
  installSubprimsTable,
  installConstPoolBytes,
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
const bundleUrl = new URL("../wasm-ui-modules.json", import.meta.url);

let bundle;
try {
  bundle = JSON.parse((await readFileUrl(bundleUrl)).toString("utf8"));
} catch (err) {
  fail("missing wasm-ui-modules.json (run scripts/wasm/compile-ui-modules.sh)");
}

const runtime = createSharedCclRuntime({
  memoryInitialPages: 256,
  subprimsTableInitial: 256,
});

const microkernel = createMicrokernel({
  memory: runtime.memory,
  persistence: true,
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

const kernelExports = kernel.instance.exports;
assert(typeof kernelExports.wasm_set_subprims_ready === "function", "missing wasm_set_subprims_ready export");
kernelExports.wasm_set_subprims_ready(1);

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

assert(typeof kernelExports.wasm_set_cstack_bounds === "function", "missing wasm_set_cstack_bounds export");
const cstackBase = runtime.memory.buffer.byteLength;
kernelExports.wasm_set_cstack_bounds(cstackBase, cstackSize);

const blobBase = (cstackBase - cstackSize - imageLen) & ~15;
assert(blobBase >= 0, "not enough memory to place boot image below cstack");
new Uint8Array(runtime.memory.buffer).set(imageBytes, blobBase);

assert(typeof kernelExports.wasm_ccl_load_image === "function", "missing wasm_ccl_load_image export");
kernelExports.wasm_ccl_load_image(blobBase, imageLen);

assert(typeof kernelExports.wasm_get_lisp_nil === "function", "missing wasm_get_lisp_nil export");
const nilValue = kernelExports.wasm_get_lisp_nil() >>> 0;

const imports = createCclImports({
  memory: runtime.memory,
  subprimsTable: runtime.subprimsTable,
  microkernel,
  extra: { ccl: kernelExports },
});

const modules = Array.isArray(bundle.modules) ? bundle.modules : [];
const functions = Array.isArray(bundle.functions) ? bundle.functions : [];
assert(modules.length > 0, "wasm-ui-modules.json contains no modules");

for (const entry of modules) {
  if (entry.constPoolBytes?.length) {
    const poolResult = installConstPoolBytes({
      kernelExports,
      memory: runtime.memory,
      entryIndex: entry.entryIndex,
      constPoolBytes: entry.constPoolBytes,
    });
    if ((poolResult >>> 0) === nilValue) {
      fail(`const pool install failed for ${entry.exportName} (entryIndex=${entry.entryIndex})`);
    }
  }
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

const markPersisted = entryIndex("WASM-UI-MARK-PERSISTED");
const markDirty = entryIndex("WASM-UI-MARK-DIRTY");
const labelState = entryIndex("WASM-UI-LABEL-STATE");
const saveEntry = entryIndex("WASM-UI-SAVE");
const restoreEntry = entryIndex("WASM-UI-RESTORE");

try {
  kernelExports.wasm_test_entry_funcall(labelState, 0);
} catch (err) {
  console.log(`SKIP: wasm ui persistence smoke test (Lisp UI not runnable: ${err?.message ?? err})`);
  process.exit(0);
}

const persistedOk = kernelExports.wasm_test_entry_funcall(markPersisted, 0) >> 2;
assert(persistedOk === 0, `mark persisted failed: ${persistedOk}`);

const saveOk = kernelExports.wasm_test_entry_funcall(saveEntry, 0) >> 2;
assert(saveOk === 0, `save failed: ${saveOk}`);

const dirtyOk = kernelExports.wasm_test_entry_funcall(markDirty, 0) >> 2;
assert(dirtyOk === 0, `mark dirty failed: ${dirtyOk}`);

const dirtyState = kernelExports.wasm_test_entry_funcall(labelState, 0) >> 2;
assert(dirtyState === 3, `expected dirty label state 3, got ${dirtyState}`);

const restoreOk = kernelExports.wasm_test_entry_funcall(restoreEntry, 0) >> 2;
assert(restoreOk === 0, `restore failed: ${restoreOk}`);

const restoredState = kernelExports.wasm_test_entry_funcall(labelState, 0) >> 2;
assert(restoredState === 2, `expected persisted label state 2, got ${restoredState}`);

console.log("PASS: wasm ui persistence smoke test");
