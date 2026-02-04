/*
 * Demo wiring (no WASI): instantiate the kernel, then install subprims into the
 * shared table from one or more provider modules.
 *
 * This is intended as an executable sketch, not a production microkernel.
 */

import {
  createCclImports,
  createSharedCclRuntime,
  fetchBytes,
  fetchJson,
  instantiateWasm,
  installSubprimsTable,
} from "./ccl-loader.mjs";
import { createMicrokernel } from "./microkernel.mjs";

// Update these URLs to point at your built artifacts.
const kernelUrl = new URL("wasmcl.wasm", import.meta.url);
const subprimsUrl = new URL("subprims.wasm", import.meta.url);
const subprimsMapUrl = new URL("../subprims-map.json", import.meta.url);

const runtime = createSharedCclRuntime({
  // These sizes are placeholders.
  memoryInitialPages: 256, // 16 MiB
  subprimsTableInitial: 256,
});

const microkernel = createMicrokernel({
  memory: runtime.memory,
});

const kernelBytes = await fetchBytes(kernelUrl);
const kernel = await instantiateWasm(
  kernelBytes,
  createCclImports({
    memory: runtime.memory,
    subprimsTable: runtime.subprimsTable,
    microkernel,
  }),
);

// Set up a manual cstack region. This is intentionally simplistic: it assumes
// the top of linear memory is available.
if (typeof kernel.instance.exports.wasm_set_cstack_bounds === "function") {
  const cstackSize = 1 << 20; // 1 MiB placeholder
  const cstackBase = runtime.memory.buffer.byteLength;
  kernel.instance.exports.wasm_set_cstack_bounds(cstackBase, cstackSize);
}

// Providers: in the simplest model, subprims implementations are module exports
// installed into the shared table. Later modules can override earlier ones.
const providers = [];
providers.push({ exports: kernel.instance.exports });

try {
  const subprimsBytes = await fetchBytes(subprimsUrl);
  const subprims = await instantiateWasm(
    subprimsBytes,
    createCclImports({
      memory: runtime.memory,
      subprimsTable: runtime.subprimsTable,
      microkernel,
    }),
  );
  providers.push({ exports: subprims.instance.exports });
} catch (e) {
  // eslint-disable-next-line no-console
  console.warn(`subprims provider not loaded: ${e}`);
}

const subprimsMap = await fetchJson(subprimsMapUrl);
const { installed, needed } = installSubprimsTable({
  table: runtime.subprimsTable,
  subprimsMap,
  providers,
  verbose: true,
});
// eslint-disable-next-line no-console
console.log(`installed ${installed}/${needed} subprims`);

// Start the kernel. We expect an explicit export to avoid relying on `main`.
if (typeof kernel.instance.exports.wasm_ccl_start !== "function") {
  throw new Error("kernel missing export wasm_ccl_start (add it in pmcl-kernel.c)");
}
kernel.instance.exports.wasm_ccl_start();
