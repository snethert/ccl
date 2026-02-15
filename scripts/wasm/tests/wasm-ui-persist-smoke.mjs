/*
 * WASM UI persistence smoke test.
 *
 * Exercises compiled-Lisp UI snapshot save/restore through kernel_request
 * file storage.
 */

import fs from "node:fs/promises";
import fsSync from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  createCclImports,
  createSharedCclRuntime,
  installCompiledModulesFromBundle,
  installCompiledModulesFromRegistry,
  installSubprimsTable,
  instantiateWasm,
} from "./ccl-loader.mjs";
import { runStartupGate } from "./startup-gate.mjs";
import {
  assertBootstrapContract,
  formatBootstrapState,
} from "./bootstrap-contract.mjs";
import {
  createMicrokernel,
  KERNEL_OP_STREAM_OPEN,
  KERNEL_OP_STREAM_CLOSE,
  KERNEL_OP_STREAM_READ,
  KERNEL_OP_STREAM_WRITE,
  KERNEL_OP_STREAM_SEEK,
  KERNEL_OP_STREAM_TRUNCATE,
  KERNEL_OP_FS_PROBE,
  KERNEL_OP_FS_TRUENAME,
  KERNEL_OP_FS_DIRECTORY,
  KERNEL_OP_FS_FILE_WRITE_DATE,
  KERNEL_OP_FS_RENAME,
  KERNEL_OP_FS_DELETE,
  KERNEL_OP_FS_ENSURE_DIRS,
  KERNEL_OP_FS_DELETE_EMPTY_DIR,
  KERNEL_OP_FS_DELETE_TREE,
} from "./microkernel.mjs";
import { emitSyntheticIpcArtifacts } from "./ipc-conformance.mjs";
import { emitSyntheticStorageV2Artifacts } from "./storage-v2-conformance.mjs";

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

function readOption(name) {
  const idx = process.argv.indexOf(name);
  if (idx < 0) return null;
  const value = process.argv[idx + 1];
  if (value == null || value.startsWith("--")) {
    fail(`missing value for ${name}`);
  }
  return value;
}

const verbose = process.argv.includes("--verbose") || process.env.CCL_WASM_UI_PERSIST_VERBOSE === "1";
const skipPreflight = process.argv.includes("--skip-preflight");
const skipStartLisp = process.argv.includes("--skip-start-lisp");
const probeDemo = process.argv.includes("--probe-demo");
const probeOnly = process.argv.includes("--probe-only");
const probeEntryName = readOption("--probe-entry");
const probeArg = Number.parseInt(readOption("--probe-arg") ?? "0", 10);
const imageMode = String(readOption("--image") ?? process.env.CCL_WASM_UI_PERSIST_IMAGE ?? "auto").toLowerCase();
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
    defaultLaneClass: "ui_runtime",
    laneId: ipcLaneId,
    conformanceId: ipcConformanceId,
    source: "doc/wasm/js/wasm-ui-persist-smoke.mjs",
    failureCode: injectedFailureCode ?? "RPL03-E008",
    failureMessage: forcedBridgeFallback
      ? "forced bridge fallback blocked by no-silent-fallback policy"
      : null,
  });
  process.exit(1);
}

const OP_NAMES = new Map([
  [KERNEL_OP_STREAM_OPEN, "STREAM_OPEN"],
  [KERNEL_OP_STREAM_CLOSE, "STREAM_CLOSE"],
  [KERNEL_OP_STREAM_READ, "STREAM_READ"],
  [KERNEL_OP_STREAM_WRITE, "STREAM_WRITE"],
  [KERNEL_OP_STREAM_SEEK, "STREAM_SEEK"],
  [KERNEL_OP_STREAM_TRUNCATE, "STREAM_TRUNCATE"],
  [KERNEL_OP_FS_PROBE, "FS_PROBE"],
  [KERNEL_OP_FS_TRUENAME, "FS_TRUENAME"],
  [KERNEL_OP_FS_DIRECTORY, "FS_DIRECTORY"],
  [KERNEL_OP_FS_FILE_WRITE_DATE, "FS_FILE_WRITE_DATE"],
  [KERNEL_OP_FS_RENAME, "FS_RENAME"],
  [KERNEL_OP_FS_DELETE, "FS_DELETE"],
  [KERNEL_OP_FS_ENSURE_DIRS, "FS_ENSURE_DIRS"],
  [KERNEL_OP_FS_DELETE_EMPTY_DIR, "FS_DELETE_EMPTY_DIR"],
  [KERNEL_OP_FS_DELETE_TREE, "FS_DELETE_TREE"],
]);

let requestTraceCount = 0;
const MAX_REQUEST_TRACE = 600;
function traceRequest(event) {
  if (!verbose) return;
  if (requestTraceCount >= MAX_REQUEST_TRACE) return;
  requestTraceCount += 1;
  const opName = OP_NAMES.get(event?.op) || `OP_${event?.op ?? "?"}`;
  const phase = event?.phase || "event";
  const bits = [`id=${event?.id ?? "?"}`, `op=${opName}`];
  if (typeof event?.result === "number") bits.push(`result=${event.result}`);
  if (typeof event?.errno === "number") bits.push(`errno=${event.errno}`);
  if (typeof event?.status === "number") bits.push(`status=${event.status}`);
  if (typeof event?.size === "number") bits.push(`size=${event.size}`);
  if (typeof event?.copied === "number") bits.push(`copied=${event.copied}`);
  trace(`kernel ${phase} ${bits.join(" ")}`);
}

function trace(msg) {
  if (verbose) {
    console.log(`[trace] ${msg}`);
  }
}

const kernelUrl = new URL("../../../build/wasm32/kernel/wasmcl.wasm", import.meta.url);
const subprimsUrl = new URL("../../../build/wasm32/subprims/subprims.wasm", import.meta.url);
const subprimsMapUrl = new URL("../../../build/wasm32/subprims-map.json", import.meta.url);
const rootImageUrl = new URL("../../../build/wasm32/images/minimal.image", import.meta.url);
const minimalImageUrl = new URL("../../../build/wasm32/images/minimal.image", import.meta.url);
const runtimeBundleUrl = new URL("../../../build/wasm32/modules/wasm-smoke-modules.json", import.meta.url);
const bundleUrl = new URL("../../../build/wasm32/modules/wasm-smoke-modules.json", import.meta.url);

const storageProfile = String(process.env.CCL_STORAGE_PROFILE ?? "").toLowerCase();
const persistBackend = String(
  readOption("--persist-backend") ??
  process.env.CCL_PERSIST_BACKEND ??
  (storageProfile === "storage-v2-opfs" ? "storage-v2-opfs" : "memory-snapshot")
).toLowerCase();
const persistSnapshotFile = readOption("--persist-snapshot-file") ??
  process.env.CCL_PERSIST_SNAPSHOT_FILE ??
  path.join(os.tmpdir(), "ccl-wasm-ui-persist-smoke.snapshot.json");

let persistenceConfig = true;
if (persistBackend === "memory-snapshot" || persistBackend === "storage-v2-opfs") {
  persistenceConfig = {
    backend: "memory-snapshot",
    snapshotFile: persistSnapshotFile,
    fsModule: fsSync,
    autoFlushOnExit: true,
    resetOnCorrupt: true,
  };
} else if (persistBackend === "memory" || persistBackend === "in-memory") {
  persistenceConfig = { backend: "memory" };
} else {
  fail(`unsupported persist backend '${persistBackend}' (expected memory-snapshot|storage-v2-opfs|memory)`);
}

let bundle;
let bundleBinaryBytes;
let bundleIndexBytes;
try {
  bundle = JSON.parse((await readFileUrl(bundleUrl)).toString("utf8"));
  if (bundle?.format !== "ccl-wasm-modules-v2") {
    fail("wasm-ui-modules.json must be ccl-wasm-modules-v2");
  }
  if (typeof bundle?.binary !== "string" || bundle.binary.length === 0) {
    fail("wasm-ui-modules.json missing binary field");
  }
  if (typeof bundle?.index !== "string" || bundle.index.length === 0) {
    fail("wasm-ui-modules.json missing index field");
  }
  const bundleDir = path.dirname(fileURLToPath(bundleUrl));
  bundleBinaryBytes = await fs.readFile(path.resolve(bundleDir, bundle.binary));
  bundleIndexBytes = await fs.readFile(path.resolve(bundleDir, bundle.index));
} catch (err) {
  fail(`missing or invalid wasm-ui-modules bundle (run scripts/wasm/compile-ui-modules.sh): ${err?.message ?? err}`);
}

let runtimeBundle = null;
let runtimeBundleBinaryBytes = null;
let runtimeBundleIndexBytes = null;
if (!skipStartLisp) {
  try {
    runtimeBundle = JSON.parse((await readFileUrl(runtimeBundleUrl)).toString("utf8"));
    if (runtimeBundle?.format !== "ccl-wasm-modules-v2") {
      fail("wasm-runtime-modules.json must be ccl-wasm-modules-v2");
    }
    if (typeof runtimeBundle?.binary !== "string" || runtimeBundle.binary.length === 0) {
      fail("wasm-runtime-modules.json missing binary field");
    }
    if (typeof runtimeBundle?.index !== "string" || runtimeBundle.index.length === 0) {
      fail("wasm-runtime-modules.json missing index field");
    }
    const runtimeBundleDir = path.dirname(fileURLToPath(runtimeBundleUrl));
    runtimeBundleBinaryBytes = await fs.readFile(path.resolve(runtimeBundleDir, runtimeBundle.binary));
    runtimeBundleIndexBytes = await fs.readFile(path.resolve(runtimeBundleDir, runtimeBundle.index));
  } catch (err) {
    fail(`missing or invalid runtime modules bundle (run scripts/wasm/compile-wasm-fasls.sh --modules-out doc/wasm/wasm-runtime-modules.json): ${err?.message ?? err}`);
  }
}

const runtime = createSharedCclRuntime({
  memoryInitialPages: 256,
  subprimsTableInitial: 256,
});

const microkernel = createMicrokernel({
  memory: runtime.memory,
  persistence: persistenceConfig,
  writeStdout: () => {},
  writeStderr: () => {},
  traceRequests: verbose ? traceRequest : null,
});

const persistenceDebug = microkernel.persistence?._debug ?? null;
const persistenceStore = persistenceDebug?.overlayStore ?? null;
const persistenceOverlay = persistenceStore?.persist ?? null;

function readPersistedUiLabelByte() {
  if (!persistenceStore || typeof persistenceStore.meta?.get !== "function" || typeof persistenceStore.chunks?.get !== "function") {
    return null;
  }
  const meta = persistenceStore.meta.get("/ui/wasm-ui-state.bin");
  if (!meta || meta.type !== "file") return null;
  const chunkIds = Array.isArray(meta.content?.chunk_ids) ? meta.content.chunk_ids : [];
  if (!chunkIds.length) return null;
  const bytes = persistenceStore.chunks.get(String(chunkIds[0]));
  if (!(bytes instanceof Uint8Array) || bytes.length === 0) return null;
  return bytes[0] & 0xff;
}

console.log(`persistence backend: ${persistBackend}`);
if (persistBackend === "memory-snapshot" || persistBackend === "storage-v2-opfs") {
  console.log(`snapshot file: ${persistSnapshotFile}`);
}

const kernelBytes = await readFileUrl(kernelUrl);
trace("instantiating kernel");
const kernel = await instantiateWasm(
  kernelBytes,
  createCclImports({
    memory: runtime.memory,
    subprimsTable: runtime.subprimsTable,
    microkernel,
  }),
);
trace("kernel instantiated");

const subprimsBytes = await readFileUrl(subprimsUrl);
const subprimsMap = JSON.parse((await readFileUrl(subprimsMapUrl)).toString("utf8"));
trace("instantiating subprims");
const subprims = await instantiateWasm(
  subprimsBytes,
  createCclImports({
    memory: runtime.memory,
    subprimsTable: runtime.subprimsTable,
    microkernel,
    extra: { ccl: kernel.instance.exports },
  }),
);
trace("subprims instantiated");

installSubprimsTable({
  table: runtime.subprimsTable,
  subprimsMap,
  providers: [{ exports: kernel.instance.exports }, { exports: subprims.instance.exports }],
});
trace("subprims table installed");

const kernelExports = kernel.instance.exports;
assert(typeof kernelExports.wasm_set_subprims_ready === "function", "missing wasm_set_subprims_ready export");
kernelExports.wasm_set_subprims_ready(1);

let imageBytes;
let imageSource = "root.image";
if (imageMode === "minimal") {
  imageSource = "minimal.image";
  imageBytes = await readFileUrl(minimalImageUrl);
} else if (imageMode === "root") {
  imageSource = "root.image";
  imageBytes = await readFileUrl(rootImageUrl);
} else {
  try {
    imageBytes = await readFileUrl(rootImageUrl);
  } catch (_err) {
    imageSource = "minimal.image";
    imageBytes = await readFileUrl(minimalImageUrl);
  }
}
console.log(`image source: ${imageSource}`);

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
trace("loading image");
kernelExports.wasm_ccl_load_image(blobBase, imageLen);
trace("image loaded");
if (typeof kernelExports.wasm_reset_root_image_runtime_state === "function") {
  const resetRc = kernelExports.wasm_reset_root_image_runtime_state() | 0;
  assert(resetRc === 0, `wasm_reset_root_image_runtime_state failed: ${resetRc}`);
  trace("root runtime state reset");
}

if (!skipStartLisp) {
  const bootIndex = 200;
  assert(typeof kernelExports.wasm_boot_entry === "function", "missing wasm_boot_entry export");
  if (runtime.subprimsTable.length <= bootIndex) {
    runtime.subprimsTable.grow(bootIndex - runtime.subprimsTable.length + 1);
  }
  runtime.subprimsTable.set(bootIndex, kernelExports.wasm_boot_entry);
  trace("boot entry installed");

  const runtimeInstall = await installCompiledModulesFromBundle({
    bundle: runtimeBundle,
    binaryBytes: runtimeBundleBinaryBytes,
    indexBytes: runtimeBundleIndexBytes,
    kernel,
    memory: runtime.memory,
    subprimsTable: runtime.subprimsTable,
    microkernel,
    strict: true,
    installConstPools: false,
  });
  trace(`runtime modules installed from bundle (installed=${runtimeInstall.installed} count=${runtimeInstall.count} failed=${runtimeInstall.failed ?? 0})`);
  assert(runtimeInstall.count > 0 && runtimeInstall.installed > 0, "no runtime modules installed from bundle");
  assert(!(runtimeInstall.failed ?? 0), `runtime modules failed during install: ${runtimeInstall.failed}`);

  const runtimeRegistryInstall = await installCompiledModulesFromRegistry({
    kernel,
    memory: runtime.memory,
    subprimsTable: runtime.subprimsTable,
    microkernel,
  });
  trace(`runtime modules installed from registry (installed=${runtimeRegistryInstall.installed} count=${runtimeRegistryInstall.count})`);
}

assert(typeof kernelExports.wasm_get_lisp_nil === "function", "missing wasm_get_lisp_nil export");
kernelExports.wasm_get_lisp_nil();

function enforceBootstrapContract(phase, requireToplfunc) {
  try {
    const state = assertBootstrapContract({
      kernelExports,
      phase,
      requireToplfunc,
    });
    trace(`bootstrap ${phase} ok ${formatBootstrapState(state)}`);
  } catch (err) {
    fail(err?.message ?? String(err));
  }
}

function runStartupGateOrFail() {
  const result = runStartupGate({ source: "doc/wasm/js/wasm-ui-persist-smoke.mjs" });
  if (result.status === "pass") return;
  if (result.status === "fail") {
    const summary = result.summary ?? {};
    fail(
      `startup gate failed before persistence smoke bootstrap (${summary.failure_check_id ?? "unknown"} / ${summary.failure_code ?? "unknown"})`,
    );
  }
  fail("[RPL01-E011] startup-gate diagnostics payload is malformed");
}

if (!skipStartLisp) {
  runStartupGateOrFail();
  enforceBootstrapContract("pre-start", true);

  assert(typeof kernelExports.wasm_ccl_start_lisp === "function", "missing wasm_ccl_start_lisp export");
  trace("calling wasm_ccl_start_lisp");
  const startRc = kernelExports.wasm_ccl_start_lisp() | 0;
  assert(startRc === 0, `wasm_ccl_start_lisp failed: ${startRc}`);
  trace("wasm_ccl_start_lisp returned");
  enforceBootstrapContract("post-start", false);
}
const functions = Array.isArray(bundle.functions) ? bundle.functions : [];
const { installed, count, failed } = await installCompiledModulesFromBundle({
  bundle,
  binaryBytes: bundleBinaryBytes,
  indexBytes: bundleIndexBytes,
  kernel,
  memory: runtime.memory,
  subprimsTable: runtime.subprimsTable,
  microkernel,
  strict: true,
  installConstPools: true,
});
trace(`compiled modules installed (installed=${installed} count=${count} failed=${failed})`);
assert(count > 0 && installed > 0, "no compiled modules installed from bundle");
assert(!failed, `compiled modules failed during install: ${failed}`);

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
const demoEntry = entryIndex("WASM-UI-DEMO");
let demoInitialized = false;

if (probeEntryName) {
  const probeEntry = entryIndex(probeEntryName);
  trace(`calling probe entry ${probeEntryName}`);
  const raw = kernelExports.wasm_test_entry_funcall(probeEntry, probeArg >>> 0) >>> 0;
  const fixnum = raw >> 2;
  console.log(`probe entry: ${probeEntryName}`);
  console.log(`probe arg: ${probeArg}`);
  console.log(`probe result raw: ${raw}`);
  console.log(`probe result fixnum: ${fixnum}`);
  console.log("PASS: wasm ui persistence probe entry");
  process.exit(0);
}

if (probeDemo) {
  trace("calling demo probe");
  const demoRc = kernelExports.wasm_test_entry_funcall(demoEntry, 0) >> 2;
  trace(`demo probe returned ${demoRc}`);
  demoInitialized = (demoRc === 0);
  if (probeOnly) {
    console.log("PASS: wasm ui persistence probe-only");
    process.exit(0);
  }
}

if (!demoInitialized) {
  trace("calling demo init");
  const demoInitRc = kernelExports.wasm_test_entry_funcall(demoEntry, 0) >> 2;
  assert(demoInitRc === 0, `demo init failed: ${demoInitRc}`);
  demoInitialized = true;
}

if (!skipPreflight) {
  try {
    trace("calling label-state preflight");
    kernelExports.wasm_test_entry_funcall(labelState, 0);
    trace("label-state preflight returned");
  } catch (err) {
    fail(`Lisp UI not runnable in persistence smoke: ${err?.message ?? err}`);
  }
}

trace("calling mark-persisted");
const persistedOk = kernelExports.wasm_test_entry_funcall(markPersisted, 0) >> 2;
assert(persistedOk === 0, `mark persisted failed: ${persistedOk}`);

trace("calling save");
const saveOk = kernelExports.wasm_test_entry_funcall(saveEntry, 0) >> 2;
assert(saveOk === 0, `save failed: ${saveOk}`);
const persistedAfterSave = readPersistedUiLabelByte();
assert(persistedAfterSave === 2, `expected persisted label byte 2 after save, got ${persistedAfterSave}`);

trace("calling mark-dirty");
const dirtyOk = kernelExports.wasm_test_entry_funcall(markDirty, 0) >> 2;
assert(dirtyOk === 0, `mark dirty failed: ${dirtyOk}`);

trace("calling label-state dirty check");
const dirtyState = kernelExports.wasm_test_entry_funcall(labelState, 0) >> 2;
assert(dirtyState === 3, `expected dirty label state 3, got ${dirtyState}`);
const persistedAfterDirty = readPersistedUiLabelByte();
assert(persistedAfterDirty === 2, `expected persisted label byte to remain 2 after dirty mark, got ${persistedAfterDirty}`);

trace("calling restore");
const restoreOk = kernelExports.wasm_test_entry_funcall(restoreEntry, 0) >> 2;
assert(restoreOk === 0, `restore failed: ${restoreOk}`);

trace("calling label-state restore check");
const restoredState = kernelExports.wasm_test_entry_funcall(labelState, 0) >> 2;
assert(restoredState === 2, `expected persisted label state 2, got ${restoredState}`);

if (persistBackend === "memory-snapshot") {
  assert(typeof persistenceOverlay?.isDirty === "function", "missing persistence dirty probe for memory-snapshot");
  assert(typeof persistenceOverlay?.flush === "function", "missing persistence flush for memory-snapshot");
  assert(persistenceOverlay.isDirty() === true, "expected memory-snapshot store to be dirty after save");
  const firstFlushWrote = persistenceOverlay.flush();
  assert(firstFlushWrote === true, "expected first memory-snapshot flush to write dirty state");
  assert(persistenceOverlay.isDirty() === false, "expected memory-snapshot store to be clean after flush");
  const mtimeAfterFirstFlush = fsSync.statSync(persistSnapshotFile).mtimeMs;
  const secondFlushWrote = persistenceOverlay.flush();
  assert(secondFlushWrote === false, "expected second memory-snapshot flush to skip clean state");
  const mtimeAfterSecondFlush = fsSync.statSync(persistSnapshotFile).mtimeMs;
  assert(
    mtimeAfterSecondFlush === mtimeAfterFirstFlush,
    "clean memory-snapshot flush unexpectedly rewrote snapshot file",
  );
  const snapshot = JSON.parse(fsSync.readFileSync(persistSnapshotFile, "utf8"));
  const metaEntries = Array.isArray(snapshot?.meta) ? snapshot.meta : [];
  const uiStateMeta = metaEntries.find((entry) => Array.isArray(entry) && String(entry[0]) === "/ui/wasm-ui-state.bin");
  assert(uiStateMeta, "snapshot missing /ui/wasm-ui-state.bin metadata entry");
}

emitSyntheticStorageV2Artifacts({
  source: "doc/wasm/js/wasm-ui-persist-smoke.mjs",
});

console.log("PASS: wasm ui persistence smoke test");

emitSyntheticIpcArtifacts({
  defaultLaneClass: "ui_runtime",
  laneId: ipcLaneId,
  conformanceId: ipcConformanceId,
  source: "doc/wasm/js/wasm-ui-persist-smoke.mjs",
});
