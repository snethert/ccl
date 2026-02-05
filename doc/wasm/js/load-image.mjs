/*
 * Node helper: load a CCL heap image into the WASM32 kernel (no WASI).
 *
 * This exercises the in-memory boot image path and skips `start_lisp` (boot-only).
 *
 * Usage:
 *   node doc/wasm/js/load-image.mjs /path/to/ccl.image
 *   node doc/wasm/js/load-image.mjs --run /path/to/ccl.image
 */

import fs from "node:fs/promises";
import { fileURLToPath } from "node:url";

import {
  createCclImports,
  createSharedCclRuntime,
  instantiateWasm,
  installCompiledModulesFromRegistry,
  installSubprimsTable,
} from "./ccl-loader.mjs";
import { createMicrokernel } from "./microkernel.mjs";

function fail(msg) {
  console.error(`FAIL: ${msg}`);
  process.exit(1);
}

const args = process.argv.slice(2);
const runToplevel = args.includes("--run");
const imagePath = args.find((arg) => !arg.startsWith("--"));
if (!imagePath) {
  console.error("Usage: node doc/wasm/js/load-image.mjs [--run] /path/to/ccl.image");
  process.exit(2);
}

const kernelUrl = new URL("wasmcl.wasm", import.meta.url);
const kernelBytes = await fs.readFile(fileURLToPath(kernelUrl));

const imageBytes = await fs.readFile(imagePath);
const imageLen = imageBytes.byteLength >>> 0;

const runtime = createSharedCclRuntime({
  // Start with 16 MiB and grow if needed.
  memoryInitialPages: 256,
  subprimsTableInitial: 256,
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

let subprims = null;
let subprimsMap = null;
if (runToplevel) {
  const subprimsUrl = new URL("subprims.wasm", import.meta.url);
  const subprimsBytes = await fs.readFile(fileURLToPath(subprimsUrl));
  const subprimsMapUrl = new URL("../subprims-map.json", import.meta.url);
  subprimsMap = JSON.parse(await fs.readFile(fileURLToPath(subprimsMapUrl), "utf-8"));

  subprims = await instantiateWasm(
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

  if (typeof kernel.instance.exports.wasm_set_subprims_ready === "function") {
    kernel.instance.exports.wasm_set_subprims_ready(1);
  }
}

const pageSize = 65536;
const cstackSize = 1 << 20; // 1 MiB
const reserve = 4 << 20; // slack for heap/loader scratch

const needBytes = imageLen + cstackSize + reserve;
let haveBytes = runtime.memory.buffer.byteLength;
if (needBytes > haveBytes) {
  const growPages = Math.ceil((needBytes - haveBytes) / pageSize);
  runtime.memory.grow(growPages);
  haveBytes = runtime.memory.buffer.byteLength;
}

if (typeof kernel.instance.exports.wasm_set_cstack_bounds !== "function") {
  fail("kernel missing export wasm_set_cstack_bounds");
}
const cstackBase = runtime.memory.buffer.byteLength;
kernel.instance.exports.wasm_set_cstack_bounds(cstackBase, cstackSize);

const blobBase = (cstackBase - cstackSize - imageLen) & ~15;
if (blobBase < 0) {
  fail("not enough memory to place boot image below cstack");
}
new Uint8Array(runtime.memory.buffer).set(imageBytes, blobBase);

if (typeof kernel.instance.exports.wasm_ccl_load_image !== "function") {
  fail("kernel missing export wasm_ccl_load_image");
}
if (typeof kernel.instance.exports.wasm_get_lisp_nil !== "function") {
  fail("kernel missing export wasm_get_lisp_nil");
}

try {
  const rc = kernel.instance.exports.wasm_ccl_load_image(blobBase, imageLen);
  const nil = kernel.instance.exports.wasm_get_lisp_nil() >>> 0;
  console.log(`wasm_ccl_load_image rc=${rc} lisp_nil=0x${nil.toString(16)}`);
  const { installed, count } = await installCompiledModulesFromRegistry({
    kernel,
    memory: runtime.memory,
    subprimsTable: runtime.subprimsTable,
    microkernel,
  });
  console.log(`compiled modules installed ${installed}/${count}`);
} catch (e) {
  console.error(`wasm_ccl_load_image trapped: ${e}`);
  process.exit(3);
}

if (runToplevel) {
  const bootEntry = kernel.instance.exports.wasm_boot_entry;
  const runToplevelFn = kernel.instance.exports.wasm_run_toplevel;
  if (typeof bootEntry !== "function") {
    fail("kernel missing export wasm_boot_entry");
  }
  if (typeof runToplevelFn !== "function") {
    fail("kernel missing export wasm_run_toplevel");
  }

  const bootIndex = 200;
  if (runtime.subprimsTable.length <= bootIndex) {
    runtime.subprimsTable.grow(bootIndex - runtime.subprimsTable.length + 1);
  }
  runtime.subprimsTable.set(bootIndex, bootEntry);

  try {
    const rc = runToplevelFn();
    console.log(`wasm_run_toplevel rc=${rc}`);
  } catch (e) {
    console.error(`wasm_run_toplevel trapped: ${e}`);
    process.exit(4);
  }
}
