/*
 * Node helper: load a CCL heap image into the WASM32 kernel (no WASI).
 *
 * This exercises the in-memory boot image path.
 * Default mode is boot-only; `--start-lisp` enters via the post-load entrypoint.
 *
 * Usage:
 *   node doc/wasm/js/load-image.mjs /path/to/ccl.image
 *   node doc/wasm/js/load-image.mjs --mode start-lisp --modules bundle.json /path/to/ccl.image
 *   node doc/wasm/js/load-image.mjs --mode run-toplevel --modules bundle.json /path/to/ccl.image
 *   node doc/wasm/js/load-image.mjs --manifest doc/wasm/root.image.manifest.json --mode start-lisp
 */

import fsSync from "node:fs";
import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";
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
import {
  collectBootstrapState,
  validateBootstrapContract,
  formatBootstrapState,
} from "./bootstrap-contract.mjs";
import { emitSyntheticIpcArtifacts } from "./ipc-conformance.mjs";
import { runStartupGate } from "./startup-gate.mjs";

function fail(msg) {
  console.error(`FAIL: ${msg}`);
  process.exit(1);
}

const traceEnabled = process.env.CCL_WASM_TRACE === "1";
function trace(msg) {
  if (traceEnabled) {
    console.error(`[load-image] ${msg}`);
  }
}

function usage() {
  console.error("Usage:");
  console.error("  node doc/wasm/js/load-image.mjs [options] /path/to/ccl.image");
  console.error("");
  console.error("Modes:");
  console.error("  --mode boot-only|start-lisp|run-toplevel");
  console.error("  --start-lisp   (alias for --mode start-lisp)");
  console.error("  --run          (alias for --mode run-toplevel)");
  console.error("");
  console.error("Options:");
  console.error("  --modules PATH             compiled modules manifest");
  console.error("  --manifest PATH            root image manifest for hash validation");
  console.error("  --strict-modules           fail on any bundle module install error");
  console.error("  --allow-partial-modules    allow bundle module install failures");
  console.error("  --stdin-script PATH        feed file bytes to stdin before start");
  console.error("  --stdin-text TEXT          feed UTF-8 text to stdin before start");
  console.error("  --close-stdin              close stdin after preload");
  console.error("  --expect-rc N              expected return code for start/toplevel entry");
  console.error("  --bootstrap-contract MODE  strict|warn|off (default: strict)");
  console.error("  --bootstrap-state-json     emit machine-readable bootstrap states");
}

function parseArgs(argv) {
  const out = {
    mode: "boot-only",
    modulesPath: null,
    manifestPath: null,
    strictModules: null,
    stdinScriptPath: null,
    stdinText: null,
    closeStdin: null,
    expectRc: null,
    bootstrapContract: "strict",
    bootstrapStateJson: false,
    imagePath: null,
  };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    switch (arg) {
      case "--mode": {
        const value = argv[++i];
        if (!value || value.startsWith("--")) {
          fail("--mode requires a value");
        }
        out.mode = String(value);
        break;
      }
      case "--run":
        out.mode = "run-toplevel";
        break;
      case "--start-lisp":
        out.mode = "start-lisp";
        break;
      case "--modules": {
        const value = argv[++i];
        if (!value || value.startsWith("--")) {
          fail("--modules requires a path");
        }
        out.modulesPath = value;
        break;
      }
      case "--manifest": {
        const value = argv[++i];
        if (!value || value.startsWith("--")) {
          fail("--manifest requires a path");
        }
        out.manifestPath = value;
        break;
      }
      case "--strict-modules":
        out.strictModules = true;
        break;
      case "--allow-partial-modules":
        out.strictModules = false;
        break;
      case "--stdin-script": {
        const value = argv[++i];
        if (!value || value.startsWith("--")) {
          fail("--stdin-script requires a path");
        }
        out.stdinScriptPath = value;
        break;
      }
      case "--stdin-text": {
        const value = argv[++i];
        if (value == null) {
          fail("--stdin-text requires a value");
        }
        out.stdinText = value;
        break;
      }
      case "--close-stdin":
        out.closeStdin = true;
        break;
      case "--expect-rc": {
        const value = Number.parseInt(String(argv[++i] ?? ""), 10);
        if (!Number.isInteger(value)) {
          fail("--expect-rc requires an integer");
        }
        out.expectRc = value | 0;
        break;
      }
      case "--bootstrap-contract": {
        const value = String(argv[++i] ?? "");
        if (!value || value.startsWith("--")) {
          fail("--bootstrap-contract requires strict|warn|off");
        }
        out.bootstrapContract = value.toLowerCase();
        break;
      }
      case "--bootstrap-state-json":
        out.bootstrapStateJson = true;
        break;
      case "-h":
      case "--help":
        usage();
        process.exit(0);
      default:
        if (arg.startsWith("--")) {
          fail(`Unknown option: ${arg}`);
        }
        if (out.imagePath) {
          fail(`Unexpected extra argument: ${arg}`);
        }
        out.imagePath = arg;
        break;
    }
  }
  if (!["boot-only", "start-lisp", "run-toplevel"].includes(out.mode)) {
    fail(`Invalid --mode: ${out.mode}`);
  }
  if (!["strict", "warn", "off"].includes(out.bootstrapContract)) {
    fail(`Invalid --bootstrap-contract: ${out.bootstrapContract}`);
  }
  if (out.stdinScriptPath && out.stdinText != null) {
    fail("--stdin-script and --stdin-text are mutually exclusive");
  }
  return out;
}

function sha256Hex(bytes) {
  return crypto.createHash("sha256").update(bytes).digest("hex");
}

const options = parseArgs(process.argv.slice(2));
const ipcConformanceId = process.env.CCL_IPC_CONFORMANCE_ID ?? null;
const ipcLaneId = process.env.CCL_IPC_LANE_ID ?? null;
const bridgeInjectedFailureCode = /^RPL03-E\d{3}$/.test(String(process.env.CCL_UI_BRIDGE_TEST_INJECT_FAILURE ?? ""))
  ? String(process.env.CCL_UI_BRIDGE_TEST_INJECT_FAILURE)
  : null;
const ipcInjectedFailureCode = /^RPL03-E\d{3}$/.test(String(process.env.CCL_IPC_TEST_INJECT_FAILURE ?? ""))
  ? String(process.env.CCL_IPC_TEST_INJECT_FAILURE)
  : null;
const forcedBridgeFallback = String(process.env.CCL_UI_BRIDGE_TEST_FORCE_FALLBACK ?? "") === "1";
const injectedFailureCode = bridgeInjectedFailureCode ?? ipcInjectedFailureCode;
if (injectedFailureCode || forcedBridgeFallback) {
  emitSyntheticIpcArtifacts({
    defaultLaneClass: "headless_runtime",
    laneId: ipcLaneId,
    conformanceId: ipcConformanceId,
    source: "doc/wasm/js/load-image.mjs",
    failureCode: injectedFailureCode ?? "RPL03-E008",
    failureMessage: forcedBridgeFallback
      ? "forced bridge fallback blocked by no-silent-fallback policy"
      : null,
  });
  process.exit(1);
}
const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDir, "../../..");

let manifest = null;
if (options.manifestPath) {
  const manifestPath = path.resolve(options.manifestPath);
  manifest = JSON.parse(await fs.readFile(manifestPath, "utf8"));
}

if (!options.imagePath && manifest?.artifacts?.rootImage?.path) {
  options.imagePath = path.resolve(repoRoot, manifest.artifacts.rootImage.path);
}
if (!options.modulesPath && manifest?.artifacts?.runtimeModulesManifest?.path) {
  options.modulesPath = path.resolve(repoRoot, manifest.artifacts.runtimeModulesManifest.path);
}
if (!options.imagePath) {
  usage();
  process.exit(2);
}
if (manifest?.policy?.expectedLoaderMode && manifest.policy.expectedLoaderMode !== options.mode) {
  fail(`Manifest expects loader mode ${manifest.policy.expectedLoaderMode}, got ${options.mode}`);
}
const strictModules = options.strictModules ?? (options.mode === "start-lisp");
const closeStdin = options.closeStdin ?? Boolean(options.stdinScriptPath || options.stdinText != null);
const runStartLisp = options.mode === "start-lisp";
const runToplevel = options.mode === "run-toplevel";

function resolveManifestArtifactPath(value) {
  if (typeof value !== "string" || value.length === 0) return null;
  if (path.isAbsolute(value)) return value;
  return path.resolve(repoRoot, value);
}

function assertManifestHash(label, bytes, manifestPathValue) {
  if (!manifest) return;
  if (typeof manifestPathValue !== "string" || manifestPathValue.length === 0) {
    fail(`Manifest missing ${label} path`);
  }
  const expected = String(manifestPathValue);
  const recorded = manifest?.artifacts?.[label]?.sha256;
  if (!recorded) {
    fail(`Manifest missing ${label} sha256`);
  }
  const actual = sha256Hex(bytes);
  if (actual !== recorded) {
    fail(`${label} hash mismatch for ${expected}: expected ${recorded}, got ${actual}`);
  }
}

const imagePath = path.resolve(options.imagePath);
let modulesPath = options.modulesPath ? path.resolve(options.modulesPath) : null;

let modulesBundle = null;
let modulesIndexBytes = null;
let modulesHandle = null;
let modulesReader = null;
let modulesFd = null;
let modulesManifestBytes = null;
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
  modulesManifestBytes = await fs.readFile(modulesPath);
  assertManifestHash(
    "runtimeModulesManifest",
    modulesManifestBytes,
    manifest?.artifacts?.runtimeModulesManifest?.path,
  );
  modulesBundle = JSON.parse(modulesManifestBytes.toString("utf-8"));
  if (typeof modulesBundle?.index === "string" && modulesBundle.index.length > 0) {
    const indexPath = path.resolve(path.dirname(modulesPath), modulesBundle.index);
    modulesIndexBytes = await fs.readFile(indexPath);
    assertManifestHash(
      "runtimeModulesIndex",
      modulesIndexBytes,
      manifest?.artifacts?.runtimeModulesIndex?.path,
    );
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
    const modulesBinaryBytes = await fs.readFile(binPath);
    assertManifestHash(
      "runtimeModulesBinary",
      modulesBinaryBytes,
      manifest?.artifacts?.runtimeModulesBinary?.path,
    );
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
assertManifestHash("kernelWasm", kernelBytes, manifest?.artifacts?.kernelWasm?.path);

const imageBytes = await fs.readFile(imagePath);
const imageLen = imageBytes.byteLength >>> 0;
assertManifestHash("rootImage", imageBytes, manifest?.artifacts?.rootImage?.path);

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

const stdinParts = [];
if (options.stdinScriptPath) {
  const stdinPath = path.resolve(options.stdinScriptPath);
  stdinParts.push(await fs.readFile(stdinPath));
}
if (options.stdinText != null) {
  stdinParts.push(new TextEncoder().encode(options.stdinText));
}
if (stdinParts.length > 0) {
  const total = stdinParts.reduce((sum, bytes) => sum + bytes.length, 0);
  const merged = new Uint8Array(total);
  let offset = 0;
  for (const chunk of stdinParts) {
    merged.set(chunk, offset);
    offset += chunk.length;
  }
  microkernel.feedStdin(merged);
  console.log(`stdin preload bytes=${merged.length}`);
}
if (closeStdin) {
  microkernel.closeStdin();
  console.log("stdin closed");
}

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
  if (!kernelExports || modulesFd == null) {
    trace(`const-pool install skipped: entry=${entryIndexRaw >>> 0} kernel/modules unavailable`);
    return 0;
  }
  const entryIndex = entryIndexRaw >>> 0;
  if (constPoolsInstalled.has(entryIndex)) {
    trace(`const-pool already installed: entry=${entryIndex}`);
    return 1;
  }

  const info = constPoolEntries.get(entryIndex);
  if (!info) {
    trace(`const-pool missing metadata: entry=${entryIndex}`);
    return 0;
  }
  trace(
    `const-pool decode: entry=${entryIndex} offset=${info.offset} stored=${info.storedLength} raw=${info.length} encoding=${info.encoding ?? "raw"}`,
  );
  const decodedBytes = decodeConstPoolForInfo(info);
  if (!decodedBytes) {
    trace(`const-pool decode failed: entry=${entryIndex}`);
    return 0;
  }

  const rc = installConstPoolBytes({
    kernelExports,
    memory: runtime.memory,
    entryIndex,
    constPoolBytes: decodedBytes,
  });
  if (rc === 0) {
    trace(`const-pool install failed: entry=${entryIndex}`);
    return 0;
  }

  constPoolsInstalled.add(entryIndex);
  trace(`const-pool installed: entry=${entryIndex}`);
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
  assertManifestHash("subprimsWasm", subprimsBytes, manifest?.artifacts?.subprimsWasm?.path);
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

function resetRootImageRuntimeStateIfAvailable() {
  const resetFn = kernel.instance.exports.wasm_reset_root_image_runtime_state;
  if (typeof resetFn !== "function") return;
  const rc = resetFn() | 0;
  if (rc !== 0) {
    fail(`wasm_reset_root_image_runtime_state returned ${rc}`);
  }
  console.log(`wasm_reset_root_image_runtime_state rc=${rc}`);
}

function runBootstrapContract(phase, { requireToplfunc = (phase === "pre-start") } = {}) {
  let state = null;
  try {
    state = collectBootstrapState({ kernelExports: kernel.instance.exports });
  } catch (err) {
    const message = err?.message ?? String(err);
    if (options.bootstrapStateJson) {
      console.log(`BOOTSTRAP_STATE_JSON ${JSON.stringify({ phase, collectError: message })}`);
    }
    if (options.bootstrapContract === "off") {
      return null;
    }
    if (options.bootstrapContract === "warn") {
      console.warn(`WARN: ${message}`);
      return null;
    }
    fail(message);
  }

  if (options.bootstrapStateJson && state) {
    console.log(`BOOTSTRAP_STATE_JSON ${JSON.stringify({ phase, ...state })}`);
  }
  if (options.bootstrapContract === "off") return state;

  const failures = validateBootstrapContract(state, { phase, requireToplfunc });
  if (!failures.length) {
    console.log(`bootstrap_contract ${phase} ok ${formatBootstrapState(state)}`);
    return state;
  }

  const message = `${phase} bootstrap contract failed: ${failures.join("; ")} | ${formatBootstrapState(state)}`;
  if (options.bootstrapContract === "warn") {
    console.warn(`WARN: ${message}`);
    return state;
  }
  fail(message);
}

function runStartupGateOrFail() {
  const result = runStartupGate({ source: "doc/wasm/js/load-image.mjs" });
  if (result.status === "pass") return;
  if (result.status === "invalid_summary") {
    console.error("FAIL: [RPL01-E011] startup-gate diagnostics payload is malformed");
  }
  process.exit(6);
}

let entryRc = null;

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
    resetRootImageRuntimeStateIfAvailable();
    if (modulesBundle) {
      const { installed, count, failed } = await installCompiledModulesFromBundle({
        bundle: modulesBundle,
        binaryReader: modulesReader,
        indexBytes: modulesIndexBytes,
        kernel,
        memory: runtime.memory,
        subprimsTable: runtime.subprimsTable,
        microkernel,
        strict: strictModules,
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
    runStartupGateOrFail();
    runBootstrapContract("pre-start", { requireToplfunc: true });
  } catch (e) {
    console.error(`wasm_ccl_load_image trapped: ${e}`);
    process.exit(3);
  }
  if (typeof kernel.instance.exports.wasm_set_subprims_ready === "function") {
    kernel.instance.exports.wasm_set_subprims_ready(1);
  }
  try {
    const rc = kernel.instance.exports.wasm_ccl_start_lisp();
    entryRc = rc | 0;
    console.log(`wasm_ccl_start_lisp rc=${rc}`);
    runBootstrapContract("post-start", { requireToplfunc: false });
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
    resetRootImageRuntimeStateIfAvailable();
    if (modulesBundle) {
      const { installed, count, failed } = await installCompiledModulesFromBundle({
        bundle: modulesBundle,
        binaryReader: modulesReader,
        indexBytes: modulesIndexBytes,
        kernel,
        memory: runtime.memory,
        subprimsTable: runtime.subprimsTable,
        microkernel,
        strict: strictModules,
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
    if (runToplevel) {
      runStartupGateOrFail();
    }
    runBootstrapContract("pre-start", { requireToplfunc: true });
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
    entryRc = rc | 0;
    console.log(`wasm_run_toplevel rc=${rc}`);
  } catch (e) {
    console.error(`wasm_run_toplevel trapped: ${e}`);
    process.exit(4);
  }
}

if (options.expectRc != null) {
  if (entryRc == null) {
    fail("--expect-rc requires --mode start-lisp or --mode run-toplevel");
  }
  if ((entryRc | 0) !== (options.expectRc | 0)) {
    console.error(`FAIL: entry rc mismatch: expected ${options.expectRc | 0}, got ${entryRc | 0}`);
    process.exit(5);
  }
}

emitSyntheticIpcArtifacts({
  defaultLaneClass: "headless_runtime",
  laneId: ipcLaneId,
  conformanceId: ipcConformanceId,
  source: "doc/wasm/js/load-image.mjs",
});

if (modulesHandle) {
  await modulesHandle.close();
}
if (modulesFd != null) {
  fsSync.closeSync(modulesFd);
}
