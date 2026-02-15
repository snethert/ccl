/*
 * Compiled modules refresh opcode smoke test (WASM-only).
 *
 * Validates that the kernel can invoke KERNEL_OP_COMPILED_MODULES_REFRESH
 * and that the JS microkernel installs from the registry synchronously.
 */

import fs from "node:fs/promises";
import { fileURLToPath } from "node:url";

import { createMicrokernel } from "./microkernel.mjs";
import {
  createCclImports,
  createSharedCclRuntime,
  instantiateWasm,
  installCompiledModulesFromRegistrySync,
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
const subprimsUrl = new URL("../../../build/wasm32/subprims/subprims.wasm", import.meta.url);
const subprimsMapUrl = new URL("../../../build/wasm32/subprims-map.json", import.meta.url);
const imageUrl = new URL("../../../build/wasm32/images/minimal.image", import.meta.url);

const kernelBytes = await readFileUrl(kernelUrl);

const runtime = createSharedCclRuntime({
  memoryInitialPages: 256,
  subprimsTableInitial: 256,
  createMemory: true,
});

let kernel = null;
const microkernel = createMicrokernel({
  memory: runtime.memory,
  compiledModulesInstaller: ({ registry, nil }) => {
    if (!kernel) return 0;
    const { installed } = installCompiledModulesFromRegistrySync({
      kernel,
      memory: runtime.memory,
      subprimsTable: runtime.subprimsTable,
      microkernel,
      registry,
      nil,
    });
    return installed;
  },
});

kernel = await instantiateWasm(
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

assert(
  typeof kernel.instance.exports.wasm_kernel_request_smoke_compiled_modules_refresh === "function",
  "missing wasm_kernel_request_smoke_compiled_modules_refresh export",
);

const installed = kernel.instance.exports.wasm_kernel_request_smoke_compiled_modules_refresh() | 0;
assert(installed >= 0, `unexpected refresh result: ${installed}`);

console.log("PASS: compiled modules refresh opcode smoke test");
