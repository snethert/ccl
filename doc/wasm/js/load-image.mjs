/*
 * Node helper: load a CCL heap image into the WASM32 kernel (no WASI).
 *
 * This exercises the in-memory boot image path. By default it skips `start_lisp`
 * (boot-only), but `--start-lisp` enters via the post-load entrypoint.
 *
 * Usage:
 *   node doc/wasm/js/load-image.mjs /path/to/ccl.image
 *   node doc/wasm/js/load-image.mjs --run /path/to/ccl.image
 *   node doc/wasm/js/load-image.mjs --start-lisp /path/to/ccl.image
 *   node doc/wasm/js/load-image.mjs --start-lisp --modules bundle.json /path/to/ccl.image
 */

import fsSync from "node:fs";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import * as zlib from "node:zlib";

import {
  createCclImports,
  createSharedCclRuntime,
  decodeBundleBytesSync,
  instantiateWasm,
  installCompiledModulesFromBundle,
  installConstPoolBytes,
  installCompiledModulesFromRegistry,
  resolveBundleEntries,
  installSubprimsTable,
  storedLengthFor,
} from "./ccl-loader.mjs";
import { createMicrokernel } from "./microkernel.mjs";

function fail(msg) {
  console.error(`FAIL: ${msg}`);
  process.exit(1);
}

const args = process.argv.slice(2);
let runToplevel = false;
let runStartLisp = false;
let modulesPath = null;
const rest = [];
for (let i = 0; i < args.length; i++) {
  const arg = args[i];
  if (arg === "--run") {
    runToplevel = true;
    continue;
  }
  if (arg === "--start-lisp") {
    runStartLisp = true;
    continue;
  }
  if (arg === "--modules") {
    modulesPath = args[++i];
    continue;
  }
  if (arg.startsWith("--")) {
    console.error(`Unknown option: ${arg}`);
    process.exit(2);
  }
  rest.push(arg);
}
if (runToplevel && runStartLisp) {
  console.error("--run and --start-lisp are mutually exclusive");
  process.exit(2);
}
const imagePath = rest[0];
if (!imagePath) {
  console.error("Usage: node doc/wasm/js/load-image.mjs [--run|--start-lisp] [--modules bundle.json] /path/to/ccl.image");
  process.exit(2);
}

let modulesBundle = null;
let modulesIndexBytes = null;
let modulesHandle = null;
let modulesReader = null;
let modulesFd = null;
const constPoolEntries = new Map();
const constPoolById = new Map();
const constPoolSpanRefCounts = new Map();
const constPoolSpanCache = new Map();
const constPoolByIdCache = new Map();
const constPoolDecodeInFlight = new Set();
let constPoolSharedBlobInfo = null;
let constPoolSharedBlobRaw = null;
const constPoolSpanKey = (offset, storedLength, encoding, rawLength) =>
  `${offset >>> 0}:${storedLength >>> 0}:${encoding ?? "raw"}:${rawLength >>> 0}`;
const constPoolsInstalled = new Set();
if (modulesPath) {
  modulesBundle = JSON.parse(await fs.readFile(modulesPath, "utf-8"));
  if (typeof modulesBundle?.index === "string" && modulesBundle.index.length > 0) {
    const indexPath = path.resolve(path.dirname(modulesPath), modulesBundle.index);
    modulesIndexBytes = await fs.readFile(indexPath);
  }
  const resolvedBundle = await resolveBundleEntries({
    bundle: modulesBundle,
    indexBytes: modulesIndexBytes,
  });
  if (Number.isFinite(modulesBundle?.constPoolBlobOffset) && Number.isFinite(modulesBundle?.constPoolBlobLength)) {
    constPoolSharedBlobInfo = {
      offset: modulesBundle.constPoolBlobOffset >>> 0,
      length: modulesBundle.constPoolBlobLength >>> 0,
      storedLength: Number.isFinite(modulesBundle?.constPoolBlobStoredLength)
        ? (modulesBundle.constPoolBlobStoredLength >>> 0)
        : (modulesBundle.constPoolBlobLength >>> 0),
      encoding: modulesBundle?.constPoolBlobEncoding ?? null,
    };
  }
  for (const entry of Array.isArray(resolvedBundle?.modules) ? resolvedBundle.modules : []) {
    if (!Number.isFinite(entry?.entryIndex)) continue;
    if (!Number.isFinite(entry?.constPoolOffset) || !Number.isFinite(entry?.constPoolLength)) continue;
    const length = entry.constPoolLength >>> 0;
    const storedLength = storedLengthFor(entry, "constPoolLength", "constPoolStoredLength");
    if (length === 0 || storedLength === 0) continue;
    const encoding = entry.constPoolEncoding ?? null;
    const key = constPoolSpanKey(entry.constPoolOffset, storedLength, encoding, length);
    const info = {
      offset: entry.constPoolOffset >>> 0,
      length,
      storedLength,
      encoding,
      key,
      id: Number.isFinite(entry?.constPoolId) ? (entry.constPoolId >>> 0) : null,
      baseId: Number.isFinite(entry?.constPoolDeltaBaseId) ? (entry.constPoolDeltaBaseId >>> 0) : null,
      deltaOp: entry?.constPoolDeltaOp ?? null,
    };
    constPoolEntries.set(entry.entryIndex >>> 0, info);
    if (info.id != null && !constPoolById.has(info.id)) {
      constPoolById.set(info.id, info);
    }
    constPoolSpanRefCounts.set(key, (constPoolSpanRefCounts.get(key) ?? 0) + 1);
  }
  if (modulesBundle?.binary) {
    const binPath = path.resolve(path.dirname(modulesPath), modulesBundle.binary);
    modulesHandle = await fs.open(binPath, "r");
    modulesFd = fsSync.openSync(binPath, "r");
    modulesReader = async (offset, length) => {
      const size = length >>> 0;
      if (size === 0) return new Uint8Array(0);
      const buffer = Buffer.allocUnsafe(size);
      let total = 0;
      while (total < size) {
        const { bytesRead } = await modulesHandle.read(
          buffer,
          total,
          size - total,
          (offset >>> 0) + total,
        );
        if (bytesRead === 0) break;
        total += bytesRead;
      }
      if (total !== size) {
        throw new Error(`short read on compiled modules: expected ${size}, got ${total}`);
      }
      return buffer;
    };
  }
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

let kernelExports = null;

function decodeConstPoolForInfo(info) {
  if (!info) return null;
  if (info.id != null && constPoolByIdCache.has(info.id)) {
    return constPoolByIdCache.get(info.id);
  }
  if (info.id != null) {
    if (constPoolDecodeInFlight.has(info.id)) {
      return null;
    }
    constPoolDecodeInFlight.add(info.id);
  }

  try {
    const shouldCache = (constPoolSpanRefCounts.get(info.key) ?? 0) > 1;
    let decodedBytes = null;
    if (shouldCache && constPoolSpanCache.has(info.key)) {
      decodedBytes = constPoolSpanCache.get(info.key);
    } else {
      if (constPoolSharedBlobInfo) {
        if (!constPoolSharedBlobRaw) {
          const sharedStored = Buffer.allocUnsafe(constPoolSharedBlobInfo.storedLength);
          let total = 0;
          while (total < constPoolSharedBlobInfo.storedLength) {
            const bytesRead = fsSync.readSync(
              modulesFd,
              sharedStored,
              total,
              constPoolSharedBlobInfo.storedLength - total,
              constPoolSharedBlobInfo.offset + total,
            );
            if (bytesRead === 0) break;
            total += bytesRead;
          }
          if (total !== constPoolSharedBlobInfo.storedLength) return null;
          constPoolSharedBlobRaw = decodeBundleBytesSync(
            sharedStored,
            constPoolSharedBlobInfo.encoding,
            constPoolSharedBlobInfo.length,
            "const pool shared blob",
            zlib,
          );
        }
        const start = info.offset >>> 0;
        const end = start + info.storedLength;
        if (end > constPoolSharedBlobRaw.length) return null;
        decodedBytes = decodeBundleBytesSync(
          constPoolSharedBlobRaw.subarray(start, end),
          info.encoding,
          info.length,
          "const pool",
          zlib,
        );
      } else {
        const bytes = Buffer.allocUnsafe(info.storedLength);
        let total = 0;
        while (total < info.storedLength) {
          const bytesRead = fsSync.readSync(modulesFd, bytes, total, info.storedLength - total, info.offset + total);
          if (bytesRead === 0) break;
          total += bytesRead;
        }
        if (total !== info.storedLength) return null;
        decodedBytes = decodeBundleBytesSync(bytes, info.encoding, info.length, "const pool", zlib);
      }
      if (shouldCache) {
        constPoolSpanCache.set(info.key, decodedBytes);
      }
    }

    if (info.baseId != null) {
      if (info.deltaOp !== "xor") return null;
      const baseInfo = constPoolById.get(info.baseId);
      if (!baseInfo) return null;
      const baseBytes = decodeConstPoolForInfo(baseInfo);
      if (!baseBytes || baseBytes.length !== decodedBytes.length) return null;
      const out = Buffer.allocUnsafe(decodedBytes.length);
      for (let i = 0; i < decodedBytes.length; i++) {
        out[i] = decodedBytes[i] ^ baseBytes[i];
      }
      decodedBytes = out;
    }

    if (info.id != null) {
      constPoolByIdCache.set(info.id, decodedBytes);
    }
    return decodedBytes;
  } catch (_e) {
    return null;
  } finally {
    if (info.id != null) constPoolDecodeInFlight.delete(info.id);
  }
}

function installConstPoolOnDemand(entryIndexRaw) {
  if (!kernelExports || modulesFd == null) return 0;
  const entryIndex = entryIndexRaw >>> 0;
  if (constPoolsInstalled.has(entryIndex)) return 1;

  const info = constPoolEntries.get(entryIndex);
  if (!info) return 0;
  const decodedBytes = decodeConstPoolForInfo(info);
  if (!decodedBytes) return 0;

  const rc = installConstPoolBytes({
    kernelExports,
    memory: runtime.memory,
    entryIndex,
    constPoolBytes: decodedBytes,
  });
  if (rc === 0) return 0;

  constPoolsInstalled.add(entryIndex);
  return 1;
}

const kernel = await instantiateWasm(
  kernelBytes,
  createCclImports({
    memory: runtime.memory,
    subprimsTable: runtime.subprimsTable,
    microkernel,
    extra: {
      ccl: {
        wasm_host_install_const_pool: installConstPoolOnDemand,
      },
    },
  }),
);
kernelExports = kernel.instance.exports;

let subprims = null;
let subprimsMap = null;
if (runToplevel || runStartLisp) {
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
      extra: {
        ccl: {
          wasm_host_install_const_pool: installConstPoolOnDemand,
          ...kernel.instance.exports,
        },
      },
    }),
  );

  installSubprimsTable({
    table: runtime.subprimsTable,
    subprimsMap,
    providers: [{ exports: kernel.instance.exports }, { exports: subprims.instance.exports }],
  });

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

if (typeof kernel.instance.exports.wasm_get_lisp_nil !== "function") {
  fail("kernel missing export wasm_get_lisp_nil");
}

const bootIndex = 200;
function installBootEntry() {
  const bootEntry = kernel.instance.exports.wasm_boot_entry;
  if (typeof bootEntry !== "function") {
    fail("kernel missing export wasm_boot_entry");
  }
  if (runtime.subprimsTable.length <= bootIndex) {
    runtime.subprimsTable.grow(bootIndex - runtime.subprimsTable.length + 1);
  }
  runtime.subprimsTable.set(bootIndex, bootEntry);
}

if (runStartLisp) {
  if (typeof kernel.instance.exports.wasm_ccl_load_image !== "function") {
    fail("kernel missing export wasm_ccl_load_image");
  }
  if (typeof kernel.instance.exports.wasm_ccl_start_lisp !== "function") {
    fail("kernel missing export wasm_ccl_start_lisp");
  }
  installBootEntry();
  try {
    const rc = kernel.instance.exports.wasm_ccl_load_image(blobBase, imageLen);
    const nil = kernel.instance.exports.wasm_get_lisp_nil() >>> 0;
    console.log(`wasm_ccl_load_image rc=${rc} lisp_nil=0x${nil.toString(16)}`);
    if (modulesBundle) {
      const { installed, count, failed } = await installCompiledModulesFromBundle({
        bundle: modulesBundle,
        binaryReader: modulesReader,
        indexBytes: modulesIndexBytes,
        kernel,
        memory: runtime.memory,
        subprimsTable: runtime.subprimsTable,
        microkernel,
        strict: false,
        installConstPools: false,
      });
      console.log(`compiled modules installed from bundle ${installed}/${count} (failed ${failed})`);
    }
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
  if (typeof kernel.instance.exports.wasm_set_subprims_ready === "function") {
    kernel.instance.exports.wasm_set_subprims_ready(1);
  }
  try {
    const rc = kernel.instance.exports.wasm_ccl_start_lisp();
    console.log(`wasm_ccl_start_lisp rc=${rc}`);
  } catch (e) {
    console.error(`wasm_ccl_start_lisp trapped: ${e}`);
    process.exit(4);
  }
} else {
  if (typeof kernel.instance.exports.wasm_ccl_load_image !== "function") {
    fail("kernel missing export wasm_ccl_load_image");
  }
  try {
    const rc = kernel.instance.exports.wasm_ccl_load_image(blobBase, imageLen);
    const nil = kernel.instance.exports.wasm_get_lisp_nil() >>> 0;
    console.log(`wasm_ccl_load_image rc=${rc} lisp_nil=0x${nil.toString(16)}`);
    if (modulesBundle) {
      const { installed, count, failed } = await installCompiledModulesFromBundle({
        bundle: modulesBundle,
        binaryReader: modulesReader,
        indexBytes: modulesIndexBytes,
        kernel,
        memory: runtime.memory,
        subprimsTable: runtime.subprimsTable,
        microkernel,
        strict: false,
        installConstPools: false,
      });
      console.log(`compiled modules installed from bundle ${installed}/${count} (failed ${failed})`);
    }
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
}

if (runToplevel) {
  const runToplevelFn = kernel.instance.exports.wasm_run_toplevel;
  if (typeof runToplevelFn !== "function") {
    fail("kernel missing export wasm_run_toplevel");
  }
  if (typeof kernel.instance.exports.wasm_set_subprims_ready === "function") {
    kernel.instance.exports.wasm_set_subprims_ready(1);
  }
  installBootEntry();

  try {
    const rc = runToplevelFn();
    console.log(`wasm_run_toplevel rc=${rc}`);
  } catch (e) {
    console.error(`wasm_run_toplevel trapped: ${e}`);
    process.exit(4);
  }
}

if (modulesHandle) {
  await modulesHandle.close();
}
if (modulesFd != null) {
  fsSync.closeSync(modulesFd);
}
