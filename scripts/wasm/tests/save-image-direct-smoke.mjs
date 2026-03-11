/*
 * WASM direct save-image smoke test.
 *
 * Loads the boot image, forces the C save_application path, and verifies
 * that the persisted image contains a valid header and trailer.
 */

import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { createMicrokernel } from "../lib/microkernel.mjs";
import {
  createCclImports,
  createSharedCclRuntime,
  instantiateWasm,
  installSubprimsTable,
} from "../lib/ccl-loader.mjs";
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

function readAll(handle) {
  const chunks = [];
  for (;;) {
    const part = handle.read(1 << 20);
    if (!part || part.length === 0) break;
    chunks.push(Buffer.from(part));
  }
  return Buffer.concat(chunks);
}

const IMAGE_SIG0 = 0x4F70656E;
const IMAGE_SIG1 = 0x4D434C49;
const IMAGE_SIG2 = 0x6D616765;
const IMAGE_SIG3 = 0x46696C65;
const FILE_MODE_READ = 0x1;

const kernelUrl = new URL("../../../build/wasm32/kernel/wasmcl.wasm", import.meta.url);
const subprimsUrl = new URL("../../../build/wasm32/subprims/subprims.wasm", import.meta.url);
const imageUrl = new URL("../../../build/wasm32/wasm-boot.image", import.meta.url);
const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");

const kernelBytes = await readFileUrl(kernelUrl);
const subprimsBytes = await readFileUrl(subprimsUrl);
const imageBytes = await readFileUrl(imageUrl);
const subprimsMap = await ensureSubprimsMap(repoRoot);

const runtime = createSharedCclRuntime({
  memoryInitialPages: 256,
  subprimsTableInitial: 512,
  createMemory: true,
});

const microkernel = createMicrokernel({
  memory: runtime.memory,
  persistence: true,
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
assert(typeof ex.wasm_ccl_load_image === "function", "missing wasm_ccl_load_image export");
assert(typeof ex.wasm_save_image_direct === "function", "missing wasm_save_image_direct export");
assert(typeof ex.wasm_set_cstack_bounds === "function", "missing wasm_set_cstack_bounds export");

const pageSize = 65536;
const imageLen = imageBytes.byteLength >>> 0;
const cstackSize = 1 << 20;
const reserve = 4 << 20;
const needBytes = imageLen + cstackSize + reserve;
let haveBytes = runtime.memory.buffer.byteLength;
if (needBytes > haveBytes) {
  runtime.memory.grow(Math.ceil((needBytes - haveBytes) / pageSize));
}

const cstackBase = runtime.memory.buffer.byteLength;
ex.wasm_set_cstack_bounds(cstackBase, cstackSize);
const blobBase = (cstackBase - cstackSize - imageLen) & ~15;
assert(blobBase >= 0, "not enough memory to place boot image below cstack");
new Uint8Array(runtime.memory.buffer).set(imageBytes, blobBase);

assert((ex.wasm_ccl_load_image(blobBase, imageLen) | 0) === 0, "boot image load failed");
if (typeof subprims.instance.exports.wasm_set_subprims_nil === "function") {
  subprims.instance.exports.wasm_set_subprims_nil(ex.wasm_get_lisp_nil() >>> 0);
}
if (typeof ex.wasm_set_subprims_ready === "function") {
  ex.wasm_set_subprims_ready(0);
}

const encoder = new TextEncoder();
const outPath = "tmp/save-image-direct-smoke.image";
const pathBytes = encoder.encode(outPath);
const ensure = microkernel.persistence.ensureDirs(outPath);
assert(ensure?.ok, "ensureDirs failed for save-image smoke path");

assert(typeof ex.malloc === "function", "missing malloc export");
const pathPtr = ex.malloc(pathBytes.length + 1) >>> 0;
new Uint8Array(runtime.memory.buffer, pathPtr, pathBytes.length).set(pathBytes);

try {
  const saveRc = ex.wasm_save_image_direct(pathPtr, pathBytes.length >>> 0, 0) | 0;
  assert(saveRc === 0, `wasm_save_image_direct returned ${saveRc}`);
} finally {
  if (typeof ex.free === "function") {
    ex.free(pathPtr);
  }
}

const openRes = microkernel.persistence.openFile(pathBytes, FILE_MODE_READ);
assert(openRes?.ok, `failed to open persisted image (${openRes?.errno ?? "unknown"})`);
const persistedBytes = readAll(openRes.value);
openRes.value.close();

assert(persistedBytes.length >= 32, "persisted image too small");

const dv = new DataView(
  persistedBytes.buffer,
  persistedBytes.byteOffset,
  persistedBytes.byteLength,
);

assert(dv.getUint32(0, true) === IMAGE_SIG0, "header sig0 mismatch");
assert(dv.getUint32(4, true) === IMAGE_SIG1, "header sig1 mismatch");
assert(dv.getUint32(8, true) === IMAGE_SIG2, "header sig2 mismatch");
assert(dv.getUint32(12, true) === IMAGE_SIG3, "header sig3 mismatch");

const tailOff = persistedBytes.length - 16;
assert(dv.getUint32(tailOff, true) === IMAGE_SIG0, "trailer sig0 mismatch");
assert(dv.getUint32(tailOff + 4, true) === IMAGE_SIG1, "trailer sig1 mismatch");
assert(dv.getUint32(tailOff + 8, true) === IMAGE_SIG2, "trailer sig2 mismatch");

const delta = dv.getInt32(tailOff + 12, true);
const headerPos = delta >= 0 ? 0 : persistedBytes.length + delta;
assert(headerPos >= 0 && headerPos + 16 <= persistedBytes.length, `header position out of range (${headerPos})`);
assert(dv.getUint32(headerPos + 12, true) === IMAGE_SIG3, `resolved header sig3 mismatch at ${headerPos}`);

console.log("PASS: direct save-image smoke test");
