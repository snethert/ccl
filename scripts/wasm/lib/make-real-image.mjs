/*
 * Build a real WASM root image by running make-real-image.lisp inside the
 * wasm kernel (Node host, no WASI). This avoids needing a native wasm32 CCL.
 *
 * Usage:
 *   node doc/wasm/js/make-real-image.mjs
 *   node doc/wasm/js/make-real-image.mjs --output /path/to/root.image
 *   node doc/wasm/js/make-real-image.mjs --boot-image /path/to/wasm-boot.image
 *
 * Prereqs:
 *  - wasm-boot.image (cross-xload-level-0 :wasm32)
 *  - level-1.lafsl + l1-fasls/*.lafsl + bin/*.lafsl (cross-compile)
 */

import fsSync from "node:fs";
import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import * as zlib from "node:zlib";

import { KERNEL_OP_STREAM_OPEN, createMicrokernel } from "./microkernel.mjs";
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
import {
  STARTUP_FUNCTION_DESIGNATOR_POLICY_V1,
  STARTUP_SYMBOL_TO_ENTRY_FUNCTION_DESIGNATORS_PRE_TOPLEVEL_V1,
} from "./bootstrap-contract.mjs";
import {
  BOOTSTRAP_RESOLVER_PHASE_BOOTSTRAP,
  createBootstrapFunctionResolver,
  registerResolverFunctionsFromBundle,
  STARTUP_SYMBOL_PACKAGE_OVERRIDES_CANONICAL_V1,
  rewriteConstPoolFunctionDesignators,
} from "./bootstrap-function-resolver.mjs";
import { FILE_MODE_READ } from "./persist-service.mjs";

function fail(msg) {
  console.error(`FAIL: ${msg}`);
  process.exit(1);
}

const traceEnabled = process.env.CCL_WASM_TRACE === "1";
function trace(msg) {
  if (traceEnabled) {
    console.error(`[make-real-image] ${msg}`);
  }
}
const WASM_BOOT_PHASE = Object.freeze({
  EARLY: 0,
  L0_READY: 1,
  RUNTIME: 2,
});

const WASM_BOOT_PHASE_NAMES = new Map([
  [WASM_BOOT_PHASE.EARLY, "EARLY"],
  [WASM_BOOT_PHASE.L0_READY, "L0_READY"],
  [WASM_BOOT_PHASE.RUNTIME, "RUNTIME"],
]);

function formatBootPhase(phase) {
  const code = phase >>> 0;
  return `${code}:${WASM_BOOT_PHASE_NAMES.get(code) ?? "UNKNOWN"}`;
}

function normalizeDesignatorNameSet(values) {
  const out = new Set();
  for (const value of Array.isArray(values) ? values : []) {
    if (typeof value !== "string") continue;
    const normalized = value.trim().toUpperCase();
    if (!normalized) continue;
    out.add(normalized);
  }
  return out;
}

function usage() {
  console.log("Usage: node doc/wasm/js/make-real-image.mjs [options]");
  console.log("");
  console.log("Options:");
  console.log("  --boot-image PATH   Boot image path (default: wasm-boot.image)");
  console.log("  --output PATH       Host output path (default: build/wasm32/images/root.image)");
  console.log("  --manifest-out PATH Root image manifest path (default: <output>.manifest.json)");
  console.log("  --build-provenance PATH Optional JSON object merged into manifest build.provenance");
  console.log("  --wasm-output PATH  Path inside wasm persistence (default: build/wasm32/images/root.image)");
  console.log("  --modules PATH      Compiled modules bundle (default: build/wasm32/modules/wasm-runtime-modules.json)");
  console.log("  --boot-modules PATH Level-0 compiled modules bundle (optional)");
  console.log("  --kernel PATH       wasmcl.wasm path (default: build/wasm32/kernel/wasmcl.wasm)");
  console.log("  --subprims PATH     subprims.wasm path (default: build/wasm32/subprims/subprims.wasm)");
  console.log("  --subprims-map PATH subprims-map.json path (default: build/wasm32/subprims-map.json)");
  console.log("  -h, --help          Show this help");
}

function parseArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    switch (arg) {
      case "-h":
      case "--help":
        out.help = true;
        break;
      case "--boot-image":
        out.bootImage = argv[++i];
        break;
      case "--output":
        out.output = argv[++i];
        break;
      case "--manifest-out":
        out.manifestOut = argv[++i];
        break;
      case "--build-provenance":
        out.buildProvenance = argv[++i];
        break;
      case "--wasm-output":
        out.wasmOutput = argv[++i];
        break;
      case "--modules":
        out.modules = argv[++i];
        break;
      case "--boot-modules":
        out.bootModules = argv[++i];
        break;
      case "--kernel":
        out.kernel = argv[++i];
        break;
      case "--subprims":
        out.subprims = argv[++i];
        break;
      case "--subprims-map":
        out.subprimsMap = argv[++i];
        break;
      default:
        if (arg.startsWith("--")) {
          fail(`Unknown option: ${arg}`);
        }
    }
  }
  return out;
}

function toPosix(p) {
  return p.split(path.sep).join("/");
}

function sortJson(value) {
  if (Array.isArray(value)) {
    return value.map(sortJson);
  }
  if (value && typeof value === "object") {
    const out = {};
    for (const key of Object.keys(value).sort()) {
      out[key] = sortJson(value[key]);
    }
    return out;
  }
  return value;
}

function canonicalJson(value) {
  return `${JSON.stringify(sortJson(value))}\n`;
}

async function loadBuildProvenance(provenancePath) {
  if (!provenancePath) return null;
  let parsed = null;
  try {
    parsed = JSON.parse(await fs.readFile(provenancePath, "utf8"));
  } catch (err) {
    fail(`Unable to read --build-provenance JSON at ${provenancePath}: ${err?.message ?? err}`);
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    fail(`--build-provenance must contain a JSON object: ${provenancePath}`);
  }
  return parsed;
}

function runShellScript(scriptPath, args, { cwd = process.cwd(), timeoutMs = 300000 } = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(scriptPath, args, {
      cwd,
      stdio: ["ignore", "inherit", "inherit"],
    });
    let timedOut = false;
    const timer = setTimeout(() => {
      timedOut = true;
      child.kill("SIGKILL");
    }, timeoutMs);
    child.on("error", (err) => {
      clearTimeout(timer);
      reject(err);
    });
    child.on("close", (code, signal) => {
      clearTimeout(timer);
      if (timedOut) {
        reject(new Error(`timed out after ${timeoutMs}ms`));
        return;
      }
      resolve({ code: code == null ? null : (code | 0), signal: signal ?? null });
    });
  });
}

function runNodeScript(args, { cwd = process.cwd(), timeoutMs = 180000 } = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, args, {
      cwd,
      stdio: ["ignore", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";
    let timedOut = false;
    const timer = setTimeout(() => {
      timedOut = true;
      child.kill("SIGKILL");
    }, timeoutMs);

    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.on("error", (err) => {
      clearTimeout(timer);
      reject(err);
    });
    child.on("close", (code, signal) => {
      clearTimeout(timer);
      if (timedOut) {
        reject(new Error(`timed out after ${timeoutMs}ms`));
        return;
      }
      resolve({
        code: code == null ? null : (code | 0),
        signal: signal ?? null,
        stdout,
        stderr,
      });
    });
  });
}

function sha256Hex(bytes) {
  return crypto.createHash("sha256").update(bytes).digest("hex");
}

function alignUp(value, align) {
  return (value + (align - 1)) & ~(align - 1);
}

function allocScratch(memory, size) {
  const pageSize = 65536;
  const aligned = alignUp(size, 16);
  const base = memory.buffer.byteLength;
  const pages = Math.ceil(aligned / pageSize);
  if (pages > 0) {
    memory.grow(pages);
  }
  return base;
}

function copyBytesToScratch(memory, bytes) {
  const base = allocScratch(memory, bytes.length);
  new Uint8Array(memory.buffer, base, bytes.length).set(bytes);
  return base >>> 0;
}

function createUtf8ScratchArena(memory, { initialCapacity = 4096 } = {}) {
  const baseCapacity = alignUp(Math.max(Math.trunc(initialCapacity), 16), 16);
  let ptr = 0;
  let capacity = 0;
  let offset = 0;

  const ensureCapacity = (neededTotalBytes) => {
    const required = alignUp(Math.max(Math.trunc(neededTotalBytes), 1), 16);
    if (ptr !== 0 && required <= capacity) return;
    let nextCapacity = capacity > 0 ? capacity : baseCapacity;
    while (nextCapacity < required) {
      nextCapacity <<= 1;
    }
    ptr = allocScratch(memory, nextCapacity);
    capacity = nextCapacity;
    offset = 0;
  };

  const allocBytes = (bytes) => {
    if (!(bytes instanceof Uint8Array) || bytes.length === 0) {
      return { ptr: 0, len: 0 };
    }
    const needed = alignUp(bytes.length, 16);
    ensureCapacity(offset + needed);
    const outPtr = (ptr + offset) >>> 0;
    new Uint8Array(memory.buffer, outPtr, bytes.length).set(bytes);
    offset += needed;
    return { ptr: outPtr, len: bytes.length >>> 0 };
  };

  return {
    reset() {
      offset = 0;
    },
    allocUtf8(text, utf8) {
      if (!utf8 || typeof utf8.encode !== "function") {
        throw new Error("utf8 scratch arena requires a TextEncoder-compatible instance");
      }
      const bytes = utf8.encode(String(text ?? ""));
      return allocBytes(bytes);
    },
  };
}

function addNamedBytes(map, name, bytes) {
  const norm = toPosix(name);
  const variants = new Set([norm, `./${norm}`]);
  const upper = norm.toUpperCase();
  variants.add(upper);
  variants.add(`./${upper}`);
  for (const key of variants) {
    map.set(key, bytes);
  }
}

async function addFile(map, filePath, relName) {
  const bytes = await fs.readFile(filePath);
  addNamedBytes(map, relName, bytes);
}

async function collectFasls(map, dirPath, relDir) {
  let entries;
  try {
    entries = await fs.readdir(dirPath, { withFileTypes: true });
  } catch (_e) {
    fail(`Missing directory: ${dirPath}`);
  }
  for (const entry of entries) {
    if (!entry.isFile()) continue;
    if (!entry.name.endsWith(".lafsl")) continue;
    const relName = path.posix.join(relDir, entry.name);
    const fullPath = path.join(dirPath, entry.name);
    await addFile(map, fullPath, relName);
  }
}

async function fileExists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch (_e) {
    return false;
  }
}

const args = parseArgs(process.argv.slice(2));
if (args.help) {
  usage();
  process.exit(0);
}

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(scriptDir, "../../..");

// Use environment variables for build directories (default: build/wasm32/)
const buildDir = process.env.CCL_WASM_BUILD_DIR ?? path.join(root, "build/wasm32");
const imagesDir = process.env.CCL_WASM_IMAGES_DIR ?? path.join(buildDir, "images");
const modulesDir = process.env.CCL_WASM_MODULES_DIR ?? path.join(buildDir, "modules");
const kernelDir = process.env.CCL_WASM_KERNEL_DIR ?? path.join(buildDir, "kernel");
const subprimsDir = process.env.CCL_WASM_SUBPRIMS_DIR ?? path.join(buildDir, "subprims");

const defaultBootImage = path.join(buildDir, "wasm-boot.image");
const defaultOutput = path.join(imagesDir, "root.image");
const defaultWasmOutput = "build/wasm32/images/root.image";
// Policy: keep compiled modules external by default (JSON + .bin sidecar)
// instead of embedding them in the saved heap image.
const defaultModules = path.join(modulesDir, "wasm-runtime-modules.json");
const kernelPath = args.kernel ?? path.join(kernelDir, "wasmcl.wasm");
const subprimsPath = args.subprims ?? path.join(subprimsDir, "subprims.wasm");
const subprimsMapPath = args.subprimsMap ?? path.join(buildDir, "subprims-map.json");
const bootImagePath = args.bootImage ?? defaultBootImage;
const outputPath = args.output ?? defaultOutput;
const manifestOutPath = args.manifestOut ?? `${outputPath}.manifest.json`;
const wasmOutputPath = args.wasmOutput ?? defaultWasmOutput;
const modulesPath = args.modules ?? defaultModules;
const bootModulesPath = args.bootModules ?? null;
const buildProvenancePath = args.buildProvenance
  ? path.resolve(args.buildProvenance)
  : null;
const buildProvenance = await loadBuildProvenance(buildProvenancePath);

function displayPath(filePath) {
  const absolute = path.resolve(filePath);
  const rel = path.relative(root, absolute);
  if (!rel.startsWith("..") && !path.isAbsolute(rel)) {
    return toPosix(rel);
  }
  return toPosix(absolute);
}

async function assertBootstrapSanity({
  label,
  scriptDirPath,
  repoRootPath,
  imagePathToCheck,
  runtimeModulesPath,
  mode = "start-lisp",
}) {
  const loadImageScriptPath = path.join(scriptDirPath, "load-image.mjs");
  const result = await runNodeScript(
    [
      loadImageScriptPath,
      "--mode",
      mode,
      "--bootstrap-contract",
      "strict",
      "--modules",
      runtimeModulesPath,
      "--stdin-text",
      "(quit)\n",
      "--close-stdin",
      imagePathToCheck,
    ],
    { cwd: repoRootPath },
  );
  if (result.code !== 0) {
    const details = [result.stdout, result.stderr]
      .filter((part) => part && part.trim().length > 0)
      .join("\n")
      .trim();
    throw new Error(
      `${label} bootstrap sanity failed (exit=${result.code}${result.signal ? ` signal=${result.signal}` : ""})` +
      (details ? `\n${details}` : ""),
    );
  }
}

trace("resolved input paths");

if (!(await fileExists(kernelPath))) {
  fail(`Missing kernel: ${kernelPath}`);
}
if (!(await fileExists(subprimsPath))) {
  fail(`Missing subprims: ${subprimsPath}`);
}
if (!(await fileExists(subprimsMapPath))) {
  fail(`Missing subprims map: ${subprimsMapPath}`);
}
if (!(await fileExists(bootImagePath))) {
  const bootScript = path.join(root, "scripts/wasm/build-wasm-boot.sh");
  if (!(await fileExists(bootScript))) {
    fail(`Missing boot image: ${bootImagePath} (and build script not found: ${bootScript})`);
  }
  console.error(`Boot image not found at ${bootImagePath} — building automatically...`);
  const bootResult = await runShellScript(bootScript, [], { cwd: root });
  if (bootResult.code !== 0) {
    fail(`boot image build failed (exit ${bootResult.code})`);
  }
  if (!(await fileExists(bootImagePath))) {
    fail(`boot image build succeeded but ${bootImagePath} still missing`);
  }
}
if (!(await fileExists(modulesPath))) {
  fail(`Missing compiled modules bundle: ${modulesPath} (run scripts/wasm/compile-wasm-fasls.sh --modules-out ${modulesPath})`);
}
if (bootModulesPath && !(await fileExists(bootModulesPath))) {
  fail(`Missing boot modules bundle: ${bootModulesPath} (run scripts/wasm/build-wasm-boot.sh --boot-modules-out ${bootModulesPath})`);
}

const level1Path = path.join(root, "level-1.lafsl");
if (!(await fileExists(level1Path))) {
  fail(`Missing level-1.lafsl (run scripts/wasm/compile-wasm-fasls.sh)`);
}

const l1Dir = path.join(root, "l1-fasls");
const binDir = path.join(root, "bin");
if (!(await fileExists(l1Dir))) {
  fail(`Missing directory: ${l1Dir}`);
}
if (!(await fileExists(binDir))) {
  fail(`Missing directory: ${binDir}`);
}

const namedBytes = new Map();

await addFile(namedBytes, level1Path, "level-1.lafsl");
await collectFasls(namedBytes, l1Dir, "l1-fasls");
await collectFasls(namedBytes, binDir, "bin");
await addFile(namedBytes, path.join(root, "scripts/wasm/make-real-image.lisp"), "scripts/wasm/make-real-image.lisp");
trace("loaded named bytes");

const requiredBin = ["lists.lafsl", "sequences.lafsl", "hash.lafsl", "defstruct.lafsl", "dll-node.lafsl", "chars.lafsl", "dumplisp.lafsl"];
for (const name of requiredBin) {
  const rel = path.posix.join("bin", name);
  if (!namedBytes.has(rel) && !namedBytes.has(rel.toUpperCase())) {
    fail(`Missing required fasl: ${rel} (run scripts/wasm/compile-wasm-fasls.sh)`);
  }
}

const kernelBytes = await fs.readFile(kernelPath);
const subprimsBytes = await fs.readFile(subprimsPath);
const subprimsMap = JSON.parse(await fs.readFile(subprimsMapPath, "utf-8"));
const bootBytes = await fs.readFile(bootImagePath);
const compiledModulesManifestBytes = await fs.readFile(modulesPath);
const compiledModulesBundle = JSON.parse(compiledModulesManifestBytes.toString("utf-8"));
/* Startup binding map removed — RESTORE-LISP-POINTERS handles symbol fixup.
   The bootstrap function resolver is kept because it is used for const-pool
   function designator resolution (a separate concern from the binding map). */
const bootstrapFunctionResolver = createBootstrapFunctionResolver({
  phase: BOOTSTRAP_RESOLVER_PHASE_BOOTSTRAP,
});
const startupRequiredPreToplevelDesignators = normalizeDesignatorNameSet(
  STARTUP_FUNCTION_DESIGNATOR_POLICY_V1?.phases?.["pre-toplevel"]?.requiredResolveOrFail ?? [],
);
const startupDeferredPreToplevelDesignators = normalizeDesignatorNameSet(
  STARTUP_FUNCTION_DESIGNATOR_POLICY_V1?.phases?.["pre-toplevel"]?.deferredAllowed ?? [],
);
const startupSymbolToEntryPreToplevelDesignators = normalizeDesignatorNameSet(
  STARTUP_SYMBOL_TO_ENTRY_FUNCTION_DESIGNATORS_PRE_TOPLEVEL_V1,
);
const resolverRegistration = registerResolverFunctionsFromBundle(
  bootstrapFunctionResolver,
  compiledModulesBundle,
  { source: "runtime-modules-manifest.functions" },
);
trace(
  `bootstrap resolver registered: +${resolverRegistration.registered} names (ignored=${resolverRegistration.ignored}, unique=${resolverRegistration.uniqueNames}, ambiguous=${resolverRegistration.ambiguous})`,
);
trace("loaded kernel/subprims/boot/modules assets");
let compiledModulesIndexBytes = null;
let compiledModulesHandle = null;
let compiledModulesReader = null;
let compiledModulesFd = null;
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
const bootConstPoolData = new Map(); /* entry_index → Uint8Array (pre-read boot const pools) */

if (typeof compiledModulesBundle?.index === "string" && compiledModulesBundle.index.length > 0) {
  const indexPath = path.join(path.dirname(modulesPath), compiledModulesBundle.index);
  if (!(await fileExists(indexPath))) {
    fail(`Missing compiled modules index: ${indexPath}`);
  }
  compiledModulesIndexBytes = await fs.readFile(indexPath);
}
if (compiledModulesIndexBytes == null) {
  fail(`Compiled modules bundle is missing index metadata: ${modulesPath}`);
}
const resolvedBundle = await resolveBundleEntries({
  bundle: compiledModulesBundle,
  indexBytes: compiledModulesIndexBytes,
});
if (Number.isFinite(compiledModulesBundle?.constPoolBlobOffset) && Number.isFinite(compiledModulesBundle?.constPoolBlobLength)) {
  constPoolSharedBlobInfo = {
    offset: compiledModulesBundle.constPoolBlobOffset >>> 0,
    length: compiledModulesBundle.constPoolBlobLength >>> 0,
    storedLength: Number.isFinite(compiledModulesBundle?.constPoolBlobStoredLength)
      ? (compiledModulesBundle.constPoolBlobStoredLength >>> 0)
      : (compiledModulesBundle.constPoolBlobLength >>> 0),
    encoding: compiledModulesBundle?.constPoolBlobEncoding ?? null,
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
if (compiledModulesBundle?.binary) {
  const binPath = path.join(path.dirname(modulesPath), compiledModulesBundle.binary);
  if (!(await fileExists(binPath))) {
    fail(`Missing compiled modules binary: ${binPath}`);
  }
  compiledModulesHandle = await fs.open(binPath, "r");
  compiledModulesFd = fsSync.openSync(binPath, "r");
  compiledModulesReader = async (offset, length) => {
    const size = length >>> 0;
    if (size === 0) return new Uint8Array(0);
    const buffer = Buffer.allocUnsafe(size);
    let total = 0;
    while (total < size) {
      const { bytesRead } = await compiledModulesHandle.read(
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
if (compiledModulesFd == null) {
  fail(`Compiled modules bundle is missing binary metadata: ${modulesPath}`);
}
trace("compiled modules reader initialized");

const runtime = createSharedCclRuntime({
  memoryInitialPages: 256,
  subprimsTableInitial: 256,
  createMemory: true,
});
const sharedProbeUtf8Scratch = createUtf8ScratchArena(runtime.memory, { initialCapacity: 4096 });
trace("runtime initialized");

const decoder = new TextDecoder("utf-8");
const microkernel = createMicrokernel({
  memory: runtime.memory,
  asyncStdin: true,
  persistence: true,
  namedBytes,
  runtimeBridge: traceEnabled ? {
    emit: (message) => {
      try {
        trace(`runtime-event ${JSON.stringify(message)}`);
      } catch {
        trace("runtime-event [unserializable]");
      }
      return true;
    },
  } : null,
  traceRequests: traceEnabled ? (event) => {
    if (!event || typeof event !== "object") return;
    if (event.phase === "stream_open_named") {
      trace(`stream-open named name=${JSON.stringify(event.name)} found=${event.found ? "yes" : "no"}`);
      return;
    }
    if (event.phase === "stream_open_file") {
      trace(`stream-open file path=${JSON.stringify(event.path)} mode=${event.modeFlags >>> 0}`);
      return;
    }
    if (event.phase === "done" && event.op === KERNEL_OP_STREAM_OPEN && (event.result | 0) < 0) {
      trace(`stream-open result=${event.result | 0}`);
      return;
    }
    if (event.phase === "done" && (event.result | 0) < 0) {
      trace(`kernel-request op=${event.op ?? "?"} result=${event.result | 0}`);
    }
  } : null,
  writeStdout: (bytes) => process.stdout.write(decoder.decode(bytes)),
  writeStderr: (bytes) => process.stderr.write(decoder.decode(bytes)),
});
trace("microkernel initialized");

if (!microkernel.persistence) {
  fail("missing persistence service");
}
const ensure = microkernel.persistence.ensureDirs(wasmOutputPath);
if (!ensure.ok) {
  fail(`persistence ensureDirs failed for ${wasmOutputPath}`);
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
              compiledModulesFd,
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
          const bytesRead = fsSync.readSync(
            compiledModulesFd,
            bytes,
            total,
            info.storedLength - total,
            info.offset + total,
          );
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
  if (!kernelExports) return 0;
  const entryIndex = entryIndexRaw >>> 0;
  if (constPoolsInstalled.has(entryIndex)) return 1;

  trace(`const-pool on-demand entry=${entryIndex}`);

  /* Check boot module pre-read const pools first */
  const bootBytes = bootConstPoolData.get(entryIndex);
  if (bootBytes) {
    trace(`const-pool on-demand boot hit entry=${entryIndex} size=${bootBytes.length}`);
    const rc = installConstPoolBytes({
      kernelExports,
      memory: runtime.memory,
      entryIndex,
      constPoolBytes: bootBytes,
    });
    const nilValue = typeof kernelExports.wasm_get_lisp_nil === "function"
      ? (kernelExports.wasm_get_lisp_nil() >>> 0)
      : null;
    if (rc !== 0 && (nilValue == null || (rc >>> 0) !== nilValue)) {
      constPoolsInstalled.add(entryIndex);
      trace(`const-pool on-demand boot OK entry=${entryIndex}`);
      return 1;
    }
    trace(`const-pool on-demand boot FAILED entry=${entryIndex} rc=0x${(rc >>> 0).toString(16)}`);
    /* Boot const pool install failed; fall through to level-1 check */
  }

  if (compiledModulesFd == null) return 0;

  const info = constPoolEntries.get(entryIndex);
  if (!info) return 0;

  const decodedBytes = decodeConstPoolForInfo(info);
  if (!decodedBytes) return 0;

  let payloadBytes = decodedBytes;
  try {
    const rewrite = rewriteConstPoolFunctionDesignators(decodedBytes, {
      resolver: bootstrapFunctionResolver,
      entryIndex,
      requiredResolveOrFailNames: startupRequiredPreToplevelDesignators,
      deferredAllowedNames: startupDeferredPreToplevelDesignators,
      symbolToEntryFunctionNames: startupSymbolToEntryPreToplevelDesignators,
      symbolPackageOverrides: STARTUP_SYMBOL_PACKAGE_OVERRIDES_CANONICAL_V1,
    });
    payloadBytes = rewrite.bytes;
    if ((rewrite?.requiredUnresolvedCount ?? 0) > 0) {
      const names = (rewrite.requiredUnresolved ?? [])
        .map((item) => String(item?.name ?? "").trim())
        .filter(Boolean)
        .join(",");
      fail(`startup const-pool function gate failed for entry ${entryIndex}: unresolved=${names}`);
    }
  } catch (err) {
    if (err?.message?.startsWith?.("FAIL:")) throw err;
    payloadBytes = decodedBytes;
  }

  const rc = installConstPoolBytes({
    kernelExports,
    memory: runtime.memory,
    entryIndex,
    constPoolBytes: payloadBytes,
  });
  const nilValue = typeof kernelExports.wasm_get_lisp_nil === "function"
    ? (kernelExports.wasm_get_lisp_nil() >>> 0)
    : null;
  if (rc === 0 || (nilValue != null && rc === nilValue)) return 0;

  constPoolsInstalled.add(entryIndex);
  return 1;
}

const hostDesignatorDecoder = new TextDecoder("utf-8");
function decodeHostDesignatorString(rawPtr, rawLen) {
  const ptr = rawPtr >>> 0;
  const len = rawLen >>> 0;
  if (ptr === 0 || len === 0) return "";
  try {
    return hostDesignatorDecoder.decode(new Uint8Array(runtime.memory.buffer, ptr, len));
  } catch {
    return "";
  }
}

function resolveFunctionDesignatorEntryFromHost(namePtr, nameLen, packagePtr, packageLen) {
  const name = decodeHostDesignatorString(namePtr, nameLen);
  if (!name) return -1;
  const packageName = decodeHostDesignatorString(packagePtr, packageLen);
  const resolution = bootstrapFunctionResolver.resolveFunctionDesignator({ name, packageName });
  if (!resolution?.ok) return -1;
  return (resolution.entryIndex >>> 0) | 0;
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
        wasm_host_resolve_function_designator_entry: resolveFunctionDesignatorEntryFromHost,
      },
    },
  }),
);
kernelExports = kernel.instance.exports;
trace("kernel instantiated");

const subprims = await instantiateWasm(
  subprimsBytes,
  createCclImports({
    memory: runtime.memory,
    subprimsTable: runtime.subprimsTable,
    microkernel,
    extra: {
      ccl: {
        wasm_host_install_const_pool: installConstPoolOnDemand,
        wasm_host_resolve_function_designator_entry: resolveFunctionDesignatorEntryFromHost,
        ...kernel.instance.exports,
      },
    },
  }),
);
trace("subprims instantiated");
const subex = subprims.instance.exports;

installSubprimsTable({
  table: runtime.subprimsTable,
  subprimsMap,
  providers: [{ exports: kernel.instance.exports }, { exports: subprims.instance.exports }],
});
trace("subprims table installed");

const imageLen = bootBytes.byteLength >>> 0;
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

const ex = kernel.instance.exports;

function setBootPhaseOrFail(phase, { reason } = {}) {
  if (typeof ex.wasm_boot_set_phase !== "function" || typeof ex.wasm_boot_get_phase !== "function") {
    fail("kernel missing wasm_boot_set_phase/wasm_boot_get_phase exports");
  }
  ex.wasm_boot_set_phase(phase >>> 0);
  const observed = ex.wasm_boot_get_phase() >>> 0;
  if ((observed >>> 0) !== (phase >>> 0)) {
    fail(`wasm_boot_set_phase(${phase >>> 0}) did not stick (observed=${observed >>> 0})`);
  }
  trace(
    `boot-phase set phase=${formatBootPhase(observed)}` +
    (reason ? ` reason=${reason}` : ""),
  );
}

setBootPhaseOrFail(WASM_BOOT_PHASE.EARLY, { reason: "kernel-startup" });

if (typeof ex.wasm_set_cstack_bounds !== "function") {
  fail("kernel missing wasm_set_cstack_bounds");
}
const cstackBase = runtime.memory.buffer.byteLength;
ex.wasm_set_cstack_bounds(cstackBase, cstackSize);

const blobBase = (cstackBase - cstackSize - imageLen) & ~15;
if (blobBase < 0) {
  fail("not enough memory to place boot image below cstack");
}
new Uint8Array(runtime.memory.buffer).set(bootBytes, blobBase);

if (typeof ex.wasm_ccl_load_image !== "function") {
  fail("kernel missing wasm_ccl_load_image");
}
ex.wasm_ccl_load_image(blobBase, imageLen);
trace("boot image loaded");

/* Mark subprims ready so RESTORE-LISP-POINTERS (and fasload) can dispatch
   through the subprim table. */
if (typeof ex.wasm_set_subprims_ready === "function") {
  ex.wasm_set_subprims_ready(1);
}
if (typeof ex.wasm_restore_lisp_pointers !== "function") {
  fail("kernel missing wasm_restore_lisp_pointers");
}
/* Try to call RESTORE-LISP-POINTERS now.  In a boot image the function is
   not yet defined (rc=-3) because it is part of level-1.  That is OK —
   the boot image hash tables are freshly built and valid.  We will call
   it again after fasls are loaded to rehash any tables that were built
   during FASL loading. */
const earlyRestoreRc = ex.wasm_restore_lisp_pointers() | 0;
if (earlyRestoreRc === 0) {
  trace("RESTORE-LISP-POINTERS complete (early)");
} else if (earlyRestoreRc === -3) {
  trace("RESTORE-LISP-POINTERS not yet defined in boot image (deferred to post-fasload)");
} else {
  fail(`wasm_restore_lisp_pointers failed: rc=${earlyRestoreRc}`);
}

const bootCompiledModuleRegistryNil = typeof ex.wasm_get_lisp_nil === "function"
  ? (ex.wasm_get_lisp_nil() >>> 0)
  : 0;
const bootCompiledModuleRegistry = typeof ex.wasm_get_compiled_module_registry === "function"
  ? (ex.wasm_get_compiled_module_registry() >>> 0)
  : 0;
const hasBootCompiledModuleRegistrySnapshot =
  bootCompiledModuleRegistry !== 0 &&
  bootCompiledModuleRegistry !== bootCompiledModuleRegistryNil &&
  (bootCompiledModuleRegistry & 0x7) === 0x5;  /* fulltag_cons — must be a real cons, not unbound marker */
if (traceEnabled) {
  trace(
    `boot-registry snapshot raw=0x${bootCompiledModuleRegistry.toString(16)}` +
    ` nil=0x${bootCompiledModuleRegistryNil.toString(16)}` +
    ` has_snapshot=${hasBootCompiledModuleRegistrySnapshot ? 1 : 0}`,
  );
}

/* Install boot (level-0) compiled modules first, so that level-0 function
   table entries (e.g. %FASLOAD) are populated before wasm_fasload_path is
   called.  These come from cross-xload-level-0 via build-wasm-boot.sh. */
if (bootModulesPath) {
  const bootBundleJson = JSON.parse(await fs.readFile(bootModulesPath, "utf-8"));
  let bootIndexBytes = null;
  let bootBinaryReader = null;
  if (typeof bootBundleJson?.index === "string" && bootBundleJson.index.length > 0) {
    const bootIndexPath = path.join(path.dirname(bootModulesPath), bootBundleJson.index);
    bootIndexBytes = await fs.readFile(bootIndexPath);
  }
  const bootResolved = await resolveBundleEntries({
    bundle: bootBundleJson,
    indexBytes: bootIndexBytes,
  });
  if (bootBundleJson?.binary) {
    const bootBinPath = path.join(path.dirname(bootModulesPath), bootBundleJson.binary);
    const bootFd = await fs.open(bootBinPath, "r");
    bootBinaryReader = async (offset, length) => {
      const size = length >>> 0;
      if (size === 0) return new Uint8Array(0);
      const buffer = Buffer.allocUnsafe(size);
      let total = 0;
      while (total < size) {
        const { bytesRead } = await bootFd.read(buffer, total, size - total, (offset >>> 0) + total);
        if (bytesRead === 0) break;
        total += bytesRead;
      }
      if (total !== size) throw new Error(`short read on boot modules: expected ${size}, got ${total}`);
      return buffer;
    };
    const bootInstall = await installCompiledModulesFromBundle({
      bundle: bootResolved,
      binaryReader: bootBinaryReader,
      indexBytes: bootIndexBytes,
      kernel: ex,
      memory: runtime.memory,
      subprimsTable: runtime.subprimsTable,
      microkernel,
      strict: false,
      installConstPools: false,
      verbose: traceEnabled,
    });
    trace(`boot modules bundle installed ${bootInstall.installed}/${bootInstall.count}`);
    if (bootInstall.installed === 0 && bootInstall.count > 0) {
      trace("WARNING: boot modules bundle had entries but none were installed");
    }
    /* Pre-read boot const pool data into memory for on-demand installation.
       Boot const pools are in a separate binary from level-1, so we read them
       now and cache in bootConstPoolData before closing the FD. */
    const bootModules = Array.isArray(bootResolved?.modules) ? bootResolved.modules : [];
    let bootConstPoolCount = 0;
    for (const entry of bootModules) {
      if (!Number.isFinite(entry?.entryIndex)) continue;
      if (!Number.isFinite(entry?.constPoolOffset) || !Number.isFinite(entry?.constPoolLength)) continue;
      const cpLen = entry.constPoolLength >>> 0;
      if (cpLen === 0) continue;
      const cpOff = entry.constPoolOffset >>> 0;
      const storedLen = Number.isFinite(entry?.constPoolStoredLength)
        ? (entry.constPoolStoredLength >>> 0) : cpLen;
      const buf = Buffer.allocUnsafe(storedLen);
      let total = 0;
      while (total < storedLen) {
        const { bytesRead } = await bootFd.read(buf, total, storedLen - total, cpOff + total);
        if (bytesRead === 0) break;
        total += bytesRead;
      }
      if (total === storedLen) {
        let decoded = buf;
        const enc = entry?.constPoolEncoding ?? null;
        if (enc && typeof decodeBundleBytesSync === "function") {
          try {
            decoded = decodeBundleBytesSync(buf, enc, cpLen, "boot const pool", zlib);
          } catch (_e) { /* use raw */ }
        }
        bootConstPoolData.set(entry.entryIndex >>> 0, decoded);
        bootConstPoolCount++;
      }
    }
    trace(`boot const pools pre-read: ${bootConstPoolCount}`);
    await bootFd.close();
  } else {
    trace("boot modules bundle has no binary — skipping");
  }
} else {
  trace("no boot modules bundle provided (--boot-modules)");
}

const bundleInstall = await installCompiledModulesFromBundle({
  bundle: compiledModulesBundle,
  binaryReader: compiledModulesReader,
  indexBytes: compiledModulesIndexBytes,
  kernel: ex,
  memory: runtime.memory,
  subprimsTable: runtime.subprimsTable,
  microkernel,
  strict: false,
  installConstPools: false,
});
trace(`compiled module bundle installed ${bundleInstall.installed}/${bundleInstall.count}`);
if (bundleInstall.count === 0) {
  fail("compiled modules bundle is empty; refusing to proceed");
}
if (bundleInstall.installed === 0) {
  fail("compiled modules bundle did not install any modules");
}
if (bundleInstall.failed) {
  console.log(`compiled modules skipped: ${bundleInstall.failed}`);
}

const registryInstall = await installCompiledModulesFromRegistry({
  kernel: ex,
  memory: runtime.memory,
  subprimsTable: runtime.subprimsTable,
  microkernel,
  ...(hasBootCompiledModuleRegistrySnapshot
    ? {
      registry: bootCompiledModuleRegistry,
      nil: bootCompiledModuleRegistryNil,
    }
    : {}),
});
trace(
  `compiled module registry install pass complete` +
  ` source=${hasBootCompiledModuleRegistrySnapshot ? "boot-snapshot" : "current-registry"}` +
  ` installed=${registryInstall.installed}/${registryInstall.count}`,
);

const encoder = new TextEncoder();




const requiredFasls = [
  "l1-fasls/l1-cl-package.lafsl",
  "l1-fasls/l1-utils.lafsl",
  "l1-fasls/l1-init.lafsl",
  "l1-fasls/l1-symhash.lafsl",
  "l1-fasls/l1-numbers.lafsl",
  "l1-fasls/l1-aprims.lafsl",
  "l1-fasls/l1-callbacks.lafsl",
  "l1-fasls/l1-sort.lafsl",
  "bin/lists.lafsl",
  "bin/sequences.lafsl",
  "l1-fasls/l1-dcode.lafsl",
  "l1-fasls/l1-clos-boot.lafsl",
  "bin/hash.lafsl",
  "l1-fasls/l1-clos.lafsl",
  "bin/defstruct.lafsl",
  "bin/dll-node.lafsl",
  "l1-fasls/l1-unicode.lafsl",
  "l1-fasls/l1-streams.lafsl",
  "l1-fasls/linux-files.lafsl",
  "bin/chars.lafsl",
  "l1-fasls/l1-files.lafsl",
  "l1-fasls/l1-typesys.lafsl",
  "l1-fasls/sysutils.lafsl",
  "l1-fasls/l1-lisp-threads.lafsl",
  "l1-fasls/l1-application.lafsl",
  "l1-fasls/l1-processes.lafsl",
  "l1-fasls/l1-io.lafsl",
  "l1-fasls/l1-reader.lafsl",
  "l1-fasls/l1-readloop.lafsl",
  "l1-fasls/l1-readloop-lds.lafsl",
  "l1-fasls/l1-error-system.lafsl",
  "l1-fasls/l1-events.lafsl",
  "l1-fasls/l1-format.lafsl",
  "l1-fasls/l1-sysio.lafsl",
  "l1-fasls/l1-pathnames.lafsl",
  "l1-fasls/l1-boot-lds.lafsl",
  "l1-fasls/l1-boot-1.lafsl",
  "l1-fasls/l1-boot-2.lafsl",
  "l1-fasls/l1-boot-3.lafsl",
  "bin/dumplisp.lafsl",
];
if (typeof ex.wasm_fasload_path !== "function") {
  fail("kernel missing wasm_fasload_path");
}

setBootPhaseOrFail(WASM_BOOT_PHASE.L0_READY, { reason: "restore-lisp-pointers-complete" });

/* Execute level-0 cold-boot initialization before FASL loading.
   This runs *XLOAD-COLD-LOAD-FUNCTIONS* (initializes *FASL-API*,
   PATHNAME-ENCODING-NAME, *PACKAGE-REFS*, etc.), sets up system locks,
   populates early class cells, resizes package hash tables, and
   updates binding indices.  Effects are baked into root.image. */
if (typeof ex.wasm_run_cold_boot_init !== "function") {
  fail("kernel missing wasm_run_cold_boot_init — rebuild kernel");
}
const coldBootRc = ex.wasm_run_cold_boot_init() | 0;
if (coldBootRc !== 0) {
  fail(`wasm_run_cold_boot_init returned ${coldBootRc}`);
}
trace("cold-boot-init complete");

for (const faslPath of requiredFasls) {
  sharedProbeUtf8Scratch.reset();
  const faslMem = sharedProbeUtf8Scratch.allocUtf8(faslPath, encoder);
  let faslRc;
  try {
    faslRc = ex.wasm_fasload_path(faslMem.ptr >>> 0, faslMem.len >>> 0) | 0;
  } catch (err) {
    fail(`wasm_fasload_path(${faslPath}) trapped: ${err?.message ?? err}\n${err?.stack ?? ''}`);
  }
  if (faslRc !== 0) {
    fail(`wasm_fasload_path(${faslPath}) returned ${faslRc}`);
  }
  trace(`fasload ${faslPath} ok`);
}
if (requiredFasls.length > 0) {
  setBootPhaseOrFail(WASM_BOOT_PHASE.RUNTIME, { reason: "post-required-fasloads" });
}

/* Now that level-1 fasls have been loaded, RESTORE-LISP-POINTERS should be
   defined.  Call it to rehash any package hash tables that were modified
   during FASL loading.  This ensures INTERN/FIND-SYMBOL work correctly
   at runtime. */
const postFasloadRestoreRc = ex.wasm_restore_lisp_pointers() | 0;
if (postFasloadRestoreRc === 0) {
  trace("RESTORE-LISP-POINTERS complete (post-fasload)");
} else {
  trace(`RESTORE-LISP-POINTERS post-fasload rc=${postFasloadRestoreRc} (non-fatal)`);
}

if (typeof ex.wasm_reset_root_image_runtime_state !== "function") {
  fail("kernel missing wasm_reset_root_image_runtime_state");
}
const resetRc = ex.wasm_reset_root_image_runtime_state() | 0;
if (resetRc !== 0) {
  fail(`wasm_reset_root_image_runtime_state returned ${resetRc}`);
}
trace("root image runtime state reset");

const toplevelEntryIndex = Array.isArray(compiledModulesBundle?.functions)
  ? (compiledModulesBundle.functions.find((entry) => entry?.name === "TOPLEVEL-LOOP")?.entryIndex ?? null)
  : null;
if (!Number.isFinite(toplevelEntryIndex)) {
  fail("compiled modules bundle missing TOPLEVEL-LOOP entry index");
}
if (typeof ex.wasm_set_toplfunc_entry !== "function") {
  fail("kernel missing wasm_set_toplfunc_entry");
}
const setToplfuncRc = ex.wasm_set_toplfunc_entry(toplevelEntryIndex >>> 0) | 0;
if (setToplfuncRc !== 0) {
  fail(`wasm_set_toplfunc_entry(${toplevelEntryIndex}) returned ${setToplfuncRc}`);
}

const imagePathBytes = encoder.encode(wasmOutputPath);
const imagePathPtr = copyBytesToScratch(runtime.memory, imagePathBytes);
if (typeof ex.wasm_save_image_direct !== "function") {
  fail("kernel missing wasm_save_image_direct");
}
trace(`invoking wasm_save_image_direct for ${wasmOutputPath}`);
const saveRc = ex.wasm_save_image_direct(
  imagePathPtr,
  imagePathBytes.length >>> 0,
  0,
) | 0;
if (saveRc !== 0) {
  console.warn(`WARN: wasm_save_image_direct returned ${saveRc}; attempting to read persisted image anyway`);
}
trace("wasm_save_image_direct completed");
const effectiveWasmOutputPath = wasmOutputPath;

const openRes = microkernel.persistence.openFile(effectiveWasmOutputPath, FILE_MODE_READ);
if (!openRes?.ok) {
  fail(`failed to open ${effectiveWasmOutputPath} in persistence store`);
}
const handle = openRes.value;
const chunks = [];
for (;;) {
  const part = handle.read(1 << 20);
  if (!part || part.length === 0) break;
  chunks.push(Buffer.from(part));
}
handle.close();
const persistedBytes = Buffer.concat(chunks);
await fs.mkdir(path.dirname(outputPath), { recursive: true });
const tempOutputPath = `${outputPath}.tmp-${process.pid}-${Date.now()}`;
await fs.writeFile(tempOutputPath, persistedBytes);

try {
  await assertBootstrapSanity({
    label: "source wasm-boot.image",
    scriptDirPath: scriptDir,
    repoRootPath: root,
    imagePathToCheck: bootImagePath,
    runtimeModulesPath: modulesPath,
    mode: "boot-only",
  });
  await assertBootstrapSanity({
    label: "emitted root.image candidate",
    scriptDirPath: scriptDir,
    repoRootPath: root,
    imagePathToCheck: tempOutputPath,
    runtimeModulesPath: modulesPath,
  });
  await fs.rename(tempOutputPath, outputPath);
} catch (err) {
  try {
    await fs.unlink(tempOutputPath);
  } catch (_cleanupErr) {
    // Ignore cleanup errors; preserve original failure context.
  }
  fail(`bootstrap sanity check failed; manifest not updated: ${err?.message ?? err}`);
}

const compiledModulesBinaryPath = path.join(path.dirname(modulesPath), compiledModulesBundle.binary);
const compiledModulesBinaryBytes = await fs.readFile(compiledModulesBinaryPath);
const bootEntryIndex = 200;
const manifest = {
  $schema: "./root-image-manifest.schema.json",
  schemaVersion: 1,
  generatedAt: new Date().toISOString(),
  build: {
    tool: "doc/wasm/js/make-real-image.mjs",
    nodeVersion: process.version,
    platform: process.platform,
    arch: process.arch,
    ...(buildProvenance ? { provenance: buildProvenance } : {}),
  },
  policy: {
    expectedLoaderMode: "start-lisp",
    entrypointIndex: bootEntryIndex,
    compiledModulesRequired: true,
  },
  artifacts: {
    rootImage: {
      path: displayPath(outputPath),
      bytes: persistedBytes.length,
      sha256: sha256Hex(persistedBytes),
    },
    runtimeModulesManifest: {
      path: displayPath(modulesPath),
      bytes: compiledModulesManifestBytes.length,
      sha256: sha256Hex(compiledModulesManifestBytes),
      format: compiledModulesBundle?.format ?? null,
      moduleCount: Number.isFinite(compiledModulesBundle?.moduleCount)
        ? (compiledModulesBundle.moduleCount >>> 0)
        : null,
      constPoolCount: Number.isFinite(compiledModulesBundle?.constPoolCount)
        ? (compiledModulesBundle.constPoolCount >>> 0)
        : null,
    },
    runtimeModulesBinary: {
      path: displayPath(compiledModulesBinaryPath),
      bytes: compiledModulesBinaryBytes.length,
      sha256: sha256Hex(compiledModulesBinaryBytes),
    },
    runtimeModulesIndex: {
      path: displayPath(path.join(path.dirname(modulesPath), compiledModulesBundle.index)),
      bytes: compiledModulesIndexBytes.length,
      sha256: sha256Hex(compiledModulesIndexBytes),
    },
    kernelWasm: {
      path: displayPath(kernelPath),
      bytes: kernelBytes.length,
      sha256: sha256Hex(kernelBytes),
    },
    subprimsWasm: {
      path: displayPath(subprimsPath),
      bytes: subprimsBytes.length,
      sha256: sha256Hex(subprimsBytes),
    },
  },
};

await fs.mkdir(path.dirname(manifestOutPath), { recursive: true });
await fs.writeFile(manifestOutPath, canonicalJson(manifest));

if (compiledModulesHandle) {
  await compiledModulesHandle.close();
}
if (compiledModulesFd != null) {
  fsSync.closeSync(compiledModulesFd);
}

console.log(`Wrote ${persistedBytes.length} bytes to ${outputPath}`);
console.log(`Wrote manifest to ${manifestOutPath}`);
