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
 *  - build/wasm32/level-1.lafsl + build/wasm32/l1-fasls/*.lafsl + build/wasm32/bin/*.lafsl (cross-compile)
 */

/* DIAGNOSTIC: Increase stack trace depth for WASM debugging */
Error.stackTraceLimit = 200;

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
  fillNullTableSlots,
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
import { WASM_BOOT_ENTRY_INDEX } from "./abi-constants.mjs";
import { createInspector } from "./tcr-inspector.mjs";

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
  console.log("  --boot-modules PATH Level-0 compiled modules bundle (default: build/wasm32/modules/wasm-boot-modules.json)");
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
      case "--no-fasload":
        out.noFasload = true;
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
  // crypto.Hash.update() throws for buffers > ~2 GiB.
  // Feed in 64 MiB chunks for large inputs.
  const hash = crypto.createHash("sha256");
  const CHUNK = 64 * 1024 * 1024;
  if (bytes.length <= CHUNK) {
    hash.update(bytes);
  } else {
    for (let off = 0; off < bytes.length; off += CHUNK) {
      hash.update(bytes.subarray(off, Math.min(off + CHUNK, bytes.length)));
    }
  }
  return hash.digest("hex");
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
const defaultBootModules = path.join(modulesDir, "wasm-boot-modules.json");
const kernelPath = args.kernel ?? path.join(kernelDir, "wasmcl.wasm");
const subprimsPath = args.subprims ?? path.join(subprimsDir, "subprims.wasm");
const subprimsMapPath = args.subprimsMap ?? path.join(buildDir, "subprims-map.json");
const bootImagePath = args.bootImage ?? defaultBootImage;
const outputPath = args.output ?? defaultOutput;
const manifestOutPath = args.manifestOut ?? `${outputPath}.manifest.json`;
const wasmOutputPath = args.wasmOutput ?? defaultWasmOutput;
const modulesPath = args.modules ?? defaultModules;
const bootModulesPath = args.bootModules ?? defaultBootModules;
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


trace("resolved input paths");

if (!(await fileExists(kernelPath))) {
  fail(`Missing kernel: ${kernelPath}`);
}
if (!(await fileExists(subprimsPath))) {
  fail(`Missing subprims: ${subprimsPath}`);
}
if (!(await fileExists(subprimsMapPath))) {
  const genScript = path.join(root, "scripts/wasm/generate_subprims_artifacts.py");
  if (!(await fileExists(genScript))) {
    fail(`Missing subprims map: ${subprimsMapPath} (and generator not found: ${genScript})`);
  }
  console.error(`Subprims map not found at ${subprimsMapPath} — generating automatically...`);
  const genResult = await runShellScript("python3", [genScript], { cwd: root });
  if (genResult.code !== 0) {
    fail(`subprims artifact generation failed (exit ${genResult.code})`);
  }
  if (!(await fileExists(subprimsMapPath))) {
    fail(`subprims artifact generation succeeded but ${subprimsMapPath} still missing`);
  }
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

const level1Path = path.join(buildDir, "level-1.lafsl");
if (!(await fileExists(level1Path))) {
  fail(`Missing ${level1Path} (run scripts/wasm/compile-wasm-fasls.sh)`);
}

const l1Dir = path.join(buildDir, "l1-fasls");
const binDir = path.join(buildDir, "bin");
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
  subprimsTableInitial: 512,
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



let _cpInstallCount = 0;
let _cpSkipCount = 0;
function installConstPoolOnDemand(entryIndexRaw) {
  if (!kernelExports) return 0;
  const entryIndex = entryIndexRaw >>> 0;
  if (constPoolsInstalled.has(entryIndex)) return 1;

  _cpInstallCount++;
  if (_cpInstallCount % 10000 === 0) {
    console.error(`[progress] const-pool installs: ${_cpInstallCount} (skipped: ${_cpSkipCount}) latest entry=${entryIndex}`);
  }
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

installSubprimsTable({
  table: runtime.subprimsTable,
  subprimsMap,
  providers: [{ exports: kernel.instance.exports }, { exports: subprims.instance.exports }],
});
trace("subprims table installed");

const imageLen = bootBytes.byteLength >>> 0;
const pageSize = 65536;
const cstackSize = 1 << 20;
const reserve = 4058 * (1 << 20);  // Must exceed kernel's reserved_area_size (3994 MB / 3.9 GB)
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

const blobBaseRaw = cstackBase - cstackSize - imageLen;
const blobBase = blobBaseRaw - (blobBaseRaw % 16);  // align down to 16 (no bitwise — safe for >2GB)
if (blobBase < 0) {
  fail("not enough memory to place boot image below cstack");
}
new Uint8Array(runtime.memory.buffer).set(bootBytes, blobBase);

if (typeof ex.wasm_ccl_load_image !== "function") {
  fail("kernel missing wasm_ccl_load_image");
}
/* Diagnostic: verify boot image placement and integrity before loading */
{
  const mem = new Uint8Array(runtime.memory.buffer);
  const sig = mem.slice(blobBase + imageLen - 16, blobBase + imageLen);
  console.error(`DIAG boot image: blobBase=0x${blobBase.toString(16)} imageLen=${imageLen} memSize=0x${runtime.memory.buffer.byteLength.toString(16)} cstackBase=0x${cstackBase.toString(16)}`);
  console.error(`DIAG boot image trailer (last 16 bytes): ${Array.from(sig).map(b => b.toString(16).padStart(2,'0')).join(' ')}`);
  const hdr = mem.slice(blobBase, blobBase + 16);
  console.error(`DIAG boot image header (first 16 bytes): ${Array.from(hdr).map(b => b.toString(16).padStart(2,'0')).join(' ')}`);
}
try {
  ex.wasm_ccl_load_image(blobBase, imageLen);
} catch (e) {
  console.error(`wasm_ccl_load_image failed: ${e.message}`);
  console.error(e.stack);
  process.exit(1);
}
console.error("[stage] boot image loaded");

/* Mark subprims ready so RESTORE-LISP-POINTERS (and fasload) can dispatch
   through the subprim table. */
if (typeof ex.wasm_set_subprims_ready === "function") {
  ex.wasm_set_subprims_ready(1);
}
/* Enable funcall tracing when CCL_WASM_TRACE is set.
   Level 1: entry index for each LEGACY call.
   Level 2: also print arg registers (very verbose). */
if (traceEnabled && typeof ex.wasm_set_trace_funcall === "function") {
  const traceLevel = parseInt(process.env.CCL_WASM_TRACE_FUNCALL ?? "1", 10);
  ex.wasm_set_trace_funcall(traceLevel > 0 ? traceLevel : 1);
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

console.error("[stage] installing compiled modules...");
/* Boot entry indices — collected after boot module installation so that the
   compiled-modules bundle (which shares the same entry index space) does not
   overwrite boot module WASM code with unrelated runtime functions. */
const bootEntryIndices = new Set();
let bootModuleEntries = []; /* saved for startup-plan.json emission */
let bootNamedFunctions = []; /* saved for startup-plan.json namedFunctions */
let bootBinaryPath = null; /* saved for modules.bin emission */

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
    bootBinaryPath = bootBinPath;
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
      strict: true,
      installConstPools: true,
      verbose: traceEnabled,
    });
    for (const entry of bootInstall.entries) {
      if (Number.isFinite(entry?.entryIndex)) {
        bootEntryIndices.add(entry.entryIndex >>> 0);
        /* Track that const pool was installed during module installation
           (installConstPoolBytes doesn't update constPoolsInstalled). */
        if (Number.isFinite(entry?.constPoolLength) && entry.constPoolLength > 0) {
          constPoolsInstalled.add(entry.entryIndex >>> 0);
        }
      }
    }
    bootModuleEntries = Array.isArray(bootResolved?.modules) ? bootResolved.modules : [];
    bootNamedFunctions = Array.isArray(bootBundleJson?.functions) ? bootBundleJson.functions : [];
    trace(`boot modules bundle installed ${bootInstall.installed}/${bootInstall.count}, ${bootEntryIndices.size} entry indices reserved`);
    if (bootInstall.installed === 0 && bootInstall.count > 0) {
      fail("boot modules bundle had entries but none were installed");
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
  installConstPools: true,
  excludeEntries: bootEntryIndices.size > 0 ? bootEntryIndices : null,
});
/* NOTE: Do NOT optimistically mark runtime const pools as installed here.
   installCompiledModulesFromBundle runs before FASL loading, so symbols
   referenced by runtime const pools (e.g. RUNTIME-COMMAND--POLL-FRAME) are
   not yet interned — they would resolve to placeholders.  The proactive
   install pass (below, after all FASLs are loaded) installs them with
   correctly-interned symbols and marks constPoolsInstalled at that point. */
console.error(`[stage] compiled modules: ${bundleInstall.installed}/${bundleInstall.count} installed, ${bundleInstall.failed || 0} failed, ${bundleInstall.excluded || 0} skipped (boot)`);
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

/* ── Fix function object entry points in boot image ────────────────────
   During cross-loading, function objects get UDF stub code vectors
   (entry 131).  Module installation puts the correct WASM code into
   the function TABLE, but the Lisp-side function OBJECTS still reference
   entry 131.  When l1-dcode evaluates (defvar *unset-fin-code*
   (uvref #'unset-fin-trampoline 1)), it reads the stale slot and every
   GF created from that point inherits the UDF entry.
   Fix: scan Lisp memory for symbol headers, match pnames against named
   functions, and UPDATE the existing function objects IN PLACE — only
   changing slot 0 (entrypoint) and slot 1 (code vector) to the correct
   entry index while preserving all other slots.  No new memory is
   allocated, so function object structure and slot count are preserved. */

/* Critical symbols whose LispObj word-offsets are captured during image fixup
   so the invariant gate can patch their fcells directly in JS. */
const criticalSymNames = new Set(["RUNTIME-BRIDGE-PUMP-COMMANDS", "%ERR-DISP"]);
const criticalSymAddrs = new Map();   // name → word index into mem32

{
  const SYMBOL_HDR = 0x0000073A;   // (7 << 8) | subtag_symbol
  const FULLTAG_MISC = 6;
  const SUBTAG_FUNCTION = 0x2A;    // subtag_function = 42

  const miscAllocFn = (typeof ex.wasm_misc_alloc === "function" &&
                       typeof ex.wasm_get_current_tcr === "function")
    ? (subtag, count) => {
        const tcr = ex.wasm_get_current_tcr();
        if (!tcr) return 0;
        return ex.wasm_misc_alloc(tcr, subtag, count) >>> 0;
      }
    : null;

  // Collect named functions for image fixup.
  // IMPORTANT: only use BOOT module entries here.  Runtime (level-1) module
  // entries must NOT override boot stubs during image fixup because their
  // initialization (defvar, defclass, etc.) hasn't run yet — that happens
  // later during FASL loading.  FASL loading will naturally replace boot
  // stubs with the runtime implementations alongside their initialization.
  const allNamedFunctions = [
    ...bootNamedFunctions,
  ];

  const rebindMap = new Map();
  for (const e of allNamedFunctions) {
    if (!e?.name || !Number.isFinite(e?.entryIndex)) continue;
    if (e.name.startsWith("(:INTERNAL")) continue;
    rebindMap.set(e.name, {
      entryIndex: e.entryIndex,
      fnSlots: Number.isFinite(e?.fnSlots) ? e.fnSlots : 3,
    });
  }

  // Bootstrap stubs: map GFs/functions that aren't standalone WASM modules
  // to their bootstrap/early equivalents so FASL loading can proceed.
  const bootstrapStubs = {
    "PREPARE-TO-DESTRUCTURE": "%EARLY-PREPARE-TO-DESTRUCTURE",
    "RECORD-SOURCE-FILE": "BOOTSTRAPPING-RECORD-SOURCE-FILE",
    "SET-DOCUMENTATION": "%PUT-DOCUMENTATION",
    "CONDITION-P": "FALSE",  // default method returns nil
    "RECURSIVE-LOCK": "FALSE",  // class not yet defined; return nil (safe on single-threaded WASM)
  };
  let stubsAdded = 0;
  for (const [gfName, earlyName] of Object.entries(bootstrapStubs)) {
    if (rebindMap.has(gfName)) continue; // already has a direct entry
    const earlyEntry = rebindMap.get(earlyName);
    if (earlyEntry !== undefined) {
      rebindMap.set(gfName, earlyEntry);
      stubsAdded++;
    }
  }
  if (stubsAdded > 0) {
    console.error(`[stage] added ${stubsAdded} bootstrap stubs to rebind map`);
  }

  if (rebindMap.size > 0) {
    const mem32 = new Uint32Array(runtime.memory.buffer);
    const totalWords = mem32.length;
    const scanStart = 0x400000 >>> 2;
    let symbolCount = 0, patched = 0, allocated = 0, skippedNoFn = 0;
    const remaining = new Map(rebindMap);

    for (let w = scanStart; w < totalWords && (remaining.size > 0 || criticalSymAddrs.size < criticalSymNames.size); w += 2) {
      if (mem32[w] !== SYMBOL_HDR) continue;
      symbolCount++;

      const pnameTagged = mem32[w + 1];
      if ((pnameTagged & 7) !== FULLTAG_MISC) continue;
      const pnameUntagged = (pnameTagged - FULLTAG_MISC) >>> 0;
      const pnameWordIdx = pnameUntagged >>> 2;
      if (pnameWordIdx < 1 || pnameWordIdx >= totalWords) continue;

      const pnameHdr = mem32[pnameWordIdx];
      const pnameSubtag = pnameHdr & 0xFF;
      const pnameCount = pnameHdr >>> 8;
      if (pnameCount < 1 || pnameCount > 255) continue;
      const dataPos = pnameWordIdx + 1;

      let name = "";
      if (pnameSubtag === 0x36) {
        // SIMPLE-BASE-STRING (subtag 0x36): 4 ASCII chars packed per word
        const dataWords = ((pnameCount + 3) >>> 2);
        if (dataPos + dataWords > totalWords) continue;
        for (let i = 0; i < pnameCount; i++) {
          const wordOff = i >>> 2;
          const byteOff = i & 3;
          name += String.fromCharCode((mem32[dataPos + wordOff] >>> (byteOff * 8)) & 0xFF);
        }
      } else {
        // SIMPLE-GENERAL-STRING (subtag 0x5A): 1 char per word
        if (dataPos + pnameCount > totalWords) continue;
        for (let i = 0; i < pnameCount; i++) {
          name += String.fromCharCode(mem32[dataPos + i] & 0xFFFF);
        }
      }

      /* Capture critical symbol addresses during the walk — these are used
         by the invariant gate later to patch fcells directly in JS. */
      if (criticalSymNames.has(name) && !criticalSymAddrs.has(name)) {
        criticalSymAddrs.set(name, w);
      }

      const info = remaining.get(name);
      if (info === undefined) continue;
      const entryIdx = info.entryIndex;
      const fnSlots = info.fnSlots;

      // Read the symbol's fcell (word +3 from header)
      const fcellTagged = mem32[w + 3];
      if ((fcellTagged & 7) !== FULLTAG_MISC) { skippedNoFn++; remaining.delete(name); continue; }
      const fnUntagged = (fcellTagged - FULLTAG_MISC) >>> 0;
      const fnWordIdx = fnUntagged >>> 2;
      if (fnWordIdx < 1 || fnWordIdx >= totalWords - 1) { skippedNoFn++; remaining.delete(name); continue; }

      const fnHdr = mem32[fnWordIdx];
      const fnSubtag = fnHdr & 0xFF;

      if (fnSubtag === SUBTAG_FUNCTION) {
        // Existing function object: update entry points in place, preserve other slots
        mem32[fnWordIdx + 1] = entryIdx << 2;  // slot 0: entrypoint (fixnum)
        mem32[fnWordIdx + 2] = entryIdx << 2;  // slot 1: code vector (fixnum)
        patched++;
      } else if (miscAllocFn) {
        // UDF pseudofunction or other non-function: allocate new function object
        // in the Lisp heap (via wasm_misc_alloc) so it survives image save.
        const fnTagged = miscAllocFn(SUBTAG_FUNCTION, fnSlots);
        if (fnTagged !== 0 && (fnTagged & 7) === FULLTAG_MISC) {
          const m = new Uint32Array(runtime.memory.buffer);
          const fw = ((fnTagged - FULLTAG_MISC) >>> 0) >>> 2;
          m[fw + 1] = entryIdx << 2;   // slot 0: entrypoint (fixnum)
          m[fw + 2] = entryIdx << 2;   // slot 1: code vector (fixnum)
          m[w + 3] = fnTagged;          // patch symbol fcell
          allocated++;
        }
      } else {
        skippedNoFn++;
      }
      remaining.delete(name);
    }
    console.error(`[stage] image fixup: ${patched} in-place + ${allocated} new-alloc / ${rebindMap.size} total (${symbolCount} syms, ${skippedNoFn} skipped, ${remaining.size} unmatched)`);

    /* UDF pseudofunction fcells (entry 131) are left as-is.  The C kernel's
       UDF check (fn_value == nrs_UDF.vcell) catches these and signals XFUNBND.
       The pending_throw pre-check in wasm_call_function_or_symbol prevents the
       error-handler cascade that the old FALSE-patching was trying to avoid.
       Each real definition loaded from FASLs later overwrites the UDF fcell. */
  } else {
    console.error("[stage] WARN: image fixup skipped — no named functions available");
  }
}

const requiredFasls = args.noFasload ? [] : [
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
  "l1-fasls/l1-error-signal.lafsl",
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
if (!args.noFasload && typeof ex.wasm_fasload_path !== "function") {
  fail("kernel missing wasm_fasload_path");
}

setBootPhaseOrFail(WASM_BOOT_PHASE.L0_READY, { reason: "restore-lisp-pointers-complete" });

/* Enable funcall tracing if requested via CCL_WASM_TRACE_FUNCALL env var.
   Level 1: print entry index on each funcall.
   Level 2: also print arg_z, arg_y, nargs registers.
   Useful for diagnosing infinite loops during cold-boot-init. */
if (process.env.CCL_WASM_TRACE_FUNCALL) {
  const level = parseInt(process.env.CCL_WASM_TRACE_FUNCALL, 10) || 0;
  if (level > 0 && typeof ex.wasm_set_trace_funcall === "function") {
    ex.wasm_set_trace_funcall(level);
    trace(`funcall trace enabled at level ${level}`);
  }
}

/* Fill null table slots with a trap stub so that call_indirect on an
   uninstalled entry produces a diagnosable Lisp XNOTFUN error instead
   of an opaque RuntimeError: unreachable. */
{
  const trapFn = subprims.instance.exports._SPentry_not_installed;
  if (typeof trapFn === "function") {
    const { filled } = fillNullTableSlots({ subprimsTable: runtime.subprimsTable, trapFn });
    console.error(`[stage] filled ${filled} null table slots with trap stub`);
  } else {
    console.error("[stage] WARN: _SPentry_not_installed not found in subprims — null table slots unguarded");
  }
}

/* Validate builtin-functions vector entry indices (diagnostic output
   goes to stderr via wasm_host_log for cross-referencing with manifests). */
if (typeof ex.wasm_validate_builtin_entries === "function") {
  const count = ex.wasm_validate_builtin_entries() >>> 0;
  console.error(`[stage] validated ${count} builtin function entries`);
}

/* Execute level-0 cold-boot initialization before FASL loading.
   This runs *XLOAD-COLD-LOAD-FUNCTIONS* (initializes *FASL-API*,
   PATHNAME-ENCODING-NAME, *PACKAGE-REFS*, etc.), sets up system locks,
   populates early class cells, resizes package hash tables, and
   updates binding indices.  Effects are baked into root.image. */
if (typeof ex.wasm_run_cold_boot_init !== "function") {
  fail("kernel missing wasm_run_cold_boot_init — rebuild kernel");
}
console.error(`[stage] cold-boot-init starting (const-pool installs so far: ${_cpInstallCount}, skipped: ${_cpSkipCount})`);
const coldBootRc = ex.wasm_run_cold_boot_init() | 0;
if (coldBootRc !== 0) {
  fail(`wasm_run_cold_boot_init returned ${coldBootRc}`);
}
trace("cold-boot-init complete");

/* Reset diagnostic counters so FASL-phase errors get full verbose
   diagnostics (cold-boot-init consumed some of the quota). */
{
  const spEx = subprims.instance.exports;
  if (typeof spEx.wasm_reset_ksignalerr_counters === "function") {
    spEx.wasm_reset_ksignalerr_counters();
  }
  if (typeof ex.wasm_reset_debug_counters === "function") {
    ex.wasm_reset_debug_counters();
  }
}

if (!args.noFasload) {
/* Pre-FASL invariant: verify bootstrap definitions of %DEFVAR and
   %KERNEL-RESTART took effect during cold-boot-init.  Without these,
   every FASL load will abort with WASM_XFUNBND. */
if (typeof ex.wasm_check_symbol_fbound === "function") {
  for (const name of ["%DEFVAR", "%KERNEL-RESTART"]) {
    const nameBytes = encoder.encode(name);
    const namePtr = ex.malloc(nameBytes.length);
    if (namePtr) {
      new Uint8Array(runtime.memory.buffer).set(nameBytes, namePtr);
      const rc = ex.wasm_check_symbol_fbound(namePtr, nameBytes.length) | 0;
      if (typeof ex.free === "function") ex.free(namePtr);
      if (rc <= 0) {
        fail(`${name} is ${rc === 0 ? "UDF (unbound)" : "not found"} after cold-boot-init — bootstrap definition missing from level-0`);
      }
      trace(`pre-FASL check: ${name} is fbound`);
    }
  }
} else {
  console.error("[warn] wasm_check_symbol_fbound not available — skipping pre-FASL invariant check");
}

for (const faslPath of requiredFasls) {
  sharedProbeUtf8Scratch.reset();
  const faslMem = sharedProbeUtf8Scratch.allocUtf8(faslPath, encoder);
  let faslRc;
  try {
    faslRc = ex.wasm_fasload_path(faslMem.ptr >>> 0, faslMem.len >>> 0) | 0;
  } catch (err) {
    /* JS-level post-crash diagnostics — dump TCR state, faslstate memory,
       and vstack without needing a kernel rebuild. */
    try {
      const mem = runtime.memory;
      const inspect = createInspector(ex, mem);

      /* 1. Dump all GPRs, spill stack, vstack, catch frames via inspector */
      inspect.dumpAll();

      /* 2. Read arg_z (the faulty object) dynamically from GPR[4] */
      const argZ = inspect.getGPR(4);  /* REG_ARG_Z */
      console.error(`[fasload-diag] arg_z=0x${argZ.toString(16).padStart(8,"0")}`);

      /* 3. Dump cons cell contents if arg_z is cons-tagged (fulltag 5) */
      if ((argZ & 7) === 5) {
        const base = argZ & ~7;
        const dv = new DataView(mem.buffer);
        const car = dv.getUint32(base + 4, true);
        const cdr = dv.getUint32(base, true);
        console.error(`[fasload-diag] cons@0x${argZ.toString(16)}: car=0x${car.toString(16).padStart(8,"0")} cdr=0x${cdr.toString(16).padStart(8,"0")}`);
      }

      /* 4. Helper: describe a misc object from its tagged pointer */
      const FT_NAMES = ["fix","nil","nhdr","imm","fix","cons","misc","ihdr"];
      const SUBTAG_NAMES = {
        0x02: "pseudofn", 0x0a: "ratio", 0x1a: "complex",
        0x22: "catch", 0x2a: "function", 0x32: "stream", 0x3a: "symbol",
        0x42: "lock", 0x4a: "hash-vec", 0x52: "pool", 0x5a: "weak",
        0x62: "package", 0x6a: "slot-vec", 0x72: "instance", 0x7a: "struct",
        0x82: "istruct", 0x8a: "value-cell", 0x92: "xfunction",
        0xea: "arrayH", 0xf2: "vectorH", 0xfa: "simple-vector",
      };
      const memLimit = mem.buffer.byteLength;
      function descMisc(ptr) {
        if ((ptr & 7) !== 6 || ptr < 0x100 || ptr >= memLimit) return null;
        const hdr = new DataView(mem.buffer).getUint32(ptr - 6, true);
        const st = hdr & 0xFF, cnt = hdr >>> 8;
        return { ptr, st, cnt, name: SUBTAG_NAMES[st] || `st=0x${st.toString(16)}` };
      }

      /* 5a. Helper: read a simple-base-string (subtag 0xBF) as JS string.
         WASM32 uses 32-bit characters (4 bytes each). cnt = char count. */
      const SUBTAG_SBS = 0xBF;       /* simple-base-string */
      const SUBTAG_SYMBOL = 0x3A;    /* symbol */
      const SUBTAG_FUNCTION = 0x2a;  /* function */
      function readBaseString(ptr) {
        if ((ptr & 7) !== 6 || ptr < 0x100 || ptr >= memLimit) return null;
        const dv = new DataView(mem.buffer);
        const hdr = dv.getUint32(ptr - 6, true);
        const st = hdr & 0xFF, cnt = hdr >>> 8;
        if (st !== SUBTAG_SBS) return null;
        const dataStart = ptr - 2;  /* misc_data_offset */
        /* Try 32-bit chars first (WASM32 uses 32-bit char encoding) */
        const chars = [];
        for (let i = 0; i < Math.min(cnt, 64); i++) {
          const c = dv.getUint32(dataStart + i * 4, true);
          if (c === 0) break;  /* stop at null */
          chars.push(c & 0xFF);
        }
        if (chars.length > 0) return String.fromCharCode(...chars);
        /* Fallback: try 8-bit chars */
        const bytes = new Uint8Array(mem.buffer, dataStart, Math.min(cnt, 128));
        return String.fromCharCode(...bytes.filter(b => b !== 0));
      }

      /* 5b. Helper: read a symbol's name (pname is element 0) */
      function readSymbolName(symPtr) {
        if ((symPtr & 7) !== 6 || symPtr < 0x100 || symPtr >= memLimit) return null;
        const dv = new DataView(mem.buffer);
        const hdr = dv.getUint32(symPtr - 6, true);
        if ((hdr & 0xFF) !== SUBTAG_SYMBOL) return null;
        const pname = dv.getUint32(symPtr - 2, true);  /* element 0 = pname */
        return readBaseString(pname);
      }

      /* 5c. Helper: read a function's name from lfun-info (element 3) */
      function readFunctionName(fnPtr) {
        if ((fnPtr & 7) !== 6 || fnPtr < 0x100 || fnPtr >= memLimit) return null;
        const dv = new DataView(mem.buffer);
        const hdr = dv.getUint32(fnPtr - 6, true);
        if ((hdr & 0xFF) !== SUBTAG_FUNCTION) return null;
        const cnt = hdr >>> 8;
        if (cnt < 4) return null;
        /* Element 3 = lfun-info. Could be a symbol or a simple-vector. */
        const lfunInfo = dv.getUint32(fnPtr - 2 + 3 * 4, true);
        /* If it's a symbol, read its name */
        if ((lfunInfo & 7) === 6) {
          const infoHdr = dv.getUint32(lfunInfo - 6, true);
          const infoSt = infoHdr & 0xFF;
          if (infoSt === SUBTAG_SYMBOL) return readSymbolName(lfunInfo);
          /* If it's a simple-vector, element 0 is often the name */
          if (infoSt === 0xFA) { /* simple-vector */
            const nameSlot = dv.getUint32(lfunInfo - 2, true);
            if ((nameSlot & 7) === 6) return readSymbolName(nameSlot);
          }
        }
        return `lfun-info@0x${lfunInfo.toString(16)}`;
      }

      /* 5d. Identify Rfn (current function) */
      const rfn = inspect.getGPR(11);  /* REG_RFN */
      const rfnInfo = descMisc(rfn);
      const rfnName = readFunctionName(rfn);
      if (rfnInfo) {
        console.error(`[fasload-diag] Rfn=0x${rfn.toString(16)}: ${rfnInfo.name} count=${rfnInfo.cnt} name=${rfnName || "?"}`);
        if (rfnInfo.st === 0x2a) {
          const dBase = rfn - 2;
          for (let i = 0; i < Math.min(rfnInfo.cnt, 6); i++) {
            const elem = new DataView(mem.buffer).getUint32(dBase + i * 4, true);
            let extra = "";
            if ((elem & 7) === 6) {
              const n = readSymbolName(elem);
              if (n) extra = ` sym=${n}`;
              else {
                const f = readFunctionName(elem);
                if (f) extra = ` fn=${f}`;
              }
            }
            console.error(`    Rfn[${i}] = 0x${elem.toString(16).padStart(8,"0")} (ft=${FT_NAMES[elem & 7]})${extra}`);
          }
        }
      }

      /* 5e. Walk spill stack for interesting objects: symbols, functions */
      console.error(`[fasload-diag] spill stack symbols/functions:`);
      const spillSp2 = inspect.getField("wasm_spill_sp");
      const spillLimit2 = inspect.getField("wasm_spill_limit");
      const spillUsed2 = (spillLimit2 - spillSp2) / 4;
      for (let i = 0; i < Math.min(40, spillUsed2); i++) {
        const a = spillSp2 + i * 4;
        if (a + 4 > memLimit) break;
        const w = new DataView(mem.buffer).getUint32(a, true);
        if ((w & 7) === 6 && w > 0x100 && w < memLimit) {
          const hdr = new DataView(mem.buffer).getUint32(w - 6, true);
          const st = hdr & 0xFF;
          if (st === SUBTAG_SYMBOL) {
            const name = readSymbolName(w);
            if (name) console.error(`    [${i}] 0x${a.toString(16)}: sym ${name}`);
          } else if (st === SUBTAG_FUNCTION) {
            const name = readFunctionName(w);
            if (name) console.error(`    [${i}] 0x${a.toString(16)}: fn ${name}`);
          }
        }
      }

      /* 6. Scan vstack for faslstate (15-element istruct, subtag 0x82) — once */
      const vsp = inspect.getGPR(10);  /* REG_VSP */
      const FASLSTATE_FIELDS = [
        "istruct-cell", "faslfname", "faslevec", "faslecnt", "faslfd",
        "faslval", "faslstr", "oldfaslstr", "faslerr", "iobuffer",
        "bufcount", "faslversion", "faslepush", "faslgsymbols", "fasldispatch"
      ];
      let foundFaslstate = false;
      for (let off = 0; off < 256 && !foundFaslstate; off += 4) {
        const addr = vsp + off;
        if (addr + 4 > memLimit) break;
        const word = new DataView(mem.buffer).getUint32(addr, true);
        const info = (word & 7) === 6 ? descMisc(word) : null;
        if (info && info.st === 0x82 && info.cnt === 15) {
          foundFaslstate = true;
          console.error(`[fasload-diag] faslstate @0x${word.toString(16)} (vsp+${off}):`);
          const dataBase = word - 2;
          for (let i = 0; i < 15; i++) {
            const elem = new DataView(mem.buffer).getUint32(dataBase + i * 4, true);
            const ft = elem & 7;
            let extra = "";
            /* Describe misc-tagged fields */
            if (ft === 6) {
              const ei = descMisc(elem);
              if (ei) extra = ` [${ei.name} cnt=${ei.cnt}]`;
            }
            console.error(`    [${i}] ${FASLSTATE_FIELDS[i].padEnd(14)} = 0x${elem.toString(16).padStart(8,"0")} (ft=${FT_NAMES[ft]})${extra}`);
          }
        }
      }

      /* 6b. Read iobuffer internals to understand FASL stream state */
      if (foundFaslstate) {
        /* The faslstate was found; re-read specific slots */
        /* Slot 9 = iobuffer (macptr), slot 10 = bufcount, slot 6 = faslstr */
        const fsBase = (function() {
          /* re-find faslstate ptr from vsp scan */
          for (let off = 0; off < 256; off += 4) {
            const addr = vsp + off;
            if (addr + 4 > memLimit) break;
            const w = new DataView(mem.buffer).getUint32(addr, true);
            if ((w & 7) === 6 && w > 0x100 && w < memLimit) {
              const h = new DataView(mem.buffer).getUint32(w - 6, true);
              if ((h & 0xFF) === 0x82 && (h >>> 8) === 15) return w;
            }
          }
          return 0;
        })();
        if (fsBase) {
          const dv = new DataView(mem.buffer);
          const iobuf = dv.getUint32(fsBase - 2 + 9 * 4, true);  /* slot 9 = iobuffer */
          const bufcnt = dv.getUint32(fsBase - 2 + 10 * 4, true); /* slot 10 = bufcount */
          console.error(`[fasload-diag] iobuffer=0x${iobuf.toString(16)} bufcount=${bufcnt >> 2}`);
          /* If iobuffer is a macptr, read the raw address it wraps */
          if ((iobuf & 7) === 6 && iobuf > 0x100 && iobuf < memLimit) {
            const iobHdr = dv.getUint32(iobuf - 6, true);
            if ((iobHdr & 0xFF) === 0x1F) { /* subtag_macptr */
              const rawAddr = dv.getUint32(iobuf - 2, true);
              console.error(`[fasload-diag] iobuffer macptr raw addr = 0x${rawAddr.toString(16).padStart(8,"0")}`);
              /* The raw addr points to the buffer. First 4 bytes = current read pos ptr */
              const curPos = dv.getUint32(rawAddr, true);
              console.error(`[fasload-diag] buffer cur-pos ptr = 0x${curPos.toString(16).padStart(8,"0")}`);
              const dataStart = rawAddr + 4;
              console.error(`[fasload-diag] buffer data start = 0x${dataStart.toString(16).padStart(8,"0")}`);
              /* Dump first 32 bytes of the buffer data */
              const preview = [];
              for (let i = 0; i < 32 && dataStart + i < memLimit; i++) {
                preview.push(new Uint8Array(mem.buffer)[dataStart + i].toString(16).padStart(2, "0"));
              }
              console.error(`[fasload-diag] buffer data: ${preview.join(" ")}`);
            }
          }
        }
      }

      /* 7. Dump memory around the bad object for context (16 words) */
      if (argZ > 0x100 && argZ < memLimit) {
        const dumpBase = (argZ & ~7) - 16;
        console.error(`[fasload-diag] mem dump around obj 0x${argZ.toString(16)}:`);
        for (let i = 0; i < 16; i++) {
          const a = dumpBase + i * 4;
          if (a >= 0 && a + 4 <= memLimit) {
            const w = new DataView(mem.buffer).getUint32(a, true);
            const marker = (a === (argZ & ~7)) ? " <-- untag(obj)" : "";
            console.error(`    0x${a.toString(16)}: 0x${w.toString(16).padStart(8,"0")}${marker}`);
          }
        }
      }

      /* 8. Dump spill stack context (top 16) */
      console.error(`[fasload-diag] spill stack (top 16):`);
      const spillSp = inspect.getField("wasm_spill_sp");
      const spillLimit = inspect.getField("wasm_spill_limit");
      const spillUsed = (spillLimit - spillSp) / 4;
      for (let i = 0; i < Math.min(16, spillUsed); i++) {
        const a = spillSp + i * 4;
        if (a + 4 <= memLimit) {
          const w = new DataView(mem.buffer).getUint32(a, true);
          const info = (w & 7) === 6 ? descMisc(w) : null;
          const extra = info ? ` [${info.name} cnt=${info.cnt}]` : "";
          console.error(`    [${i}] 0x${a.toString(16)}: 0x${w.toString(16).padStart(8,"0")} (ft=${FT_NAMES[w & 7]})${extra}`);
        }
      }
    } catch (diagErr) {
      console.error(`[fasload-diag] diagnostic failed: ${diagErr?.message ?? diagErr}`);
    }
    fail(`wasm_fasload_path(${faslPath}) trapped: ${err?.message ?? err}\n${err?.stack ?? ''}`);
  }
  if (faslRc !== 0) {
    /* Non-trap failure — dump TCR state for diagnosis */
    try {
      const mem = runtime.memory;
      const inspect = createInspector(ex, mem);
      console.error(`[fasload-rc] wasm_fasload_path(${faslPath}) returned ${faslRc}`);
      inspect.dumpAll();
    } catch (diagErr) {
      console.error(`[fasload-rc-diag] failed: ${diagErr?.message ?? diagErr}`);
    }
    fail(`wasm_fasload_path(${faslPath}) returned ${faslRc}`);
  }
  trace(`fasload ${faslPath} ok`);
}
if (requiredFasls.length > 0) {
  setBootPhaseOrFail(WASM_BOOT_PHASE.RUNTIME, { reason: "post-required-fasloads" });
}
} else {
  /* --no-fasload: L1 baked into boot image via xfasload cross-compiler */
  console.error("[stage] --no-fasload: L1 baked into boot image, skipping FASL loading");
  setBootPhaseOrFail(WASM_BOOT_PHASE.RUNTIME, { reason: "l1-baked-in" });
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

/* Phase 2A: Proactive const pool installation.
   At this point the full standard library is loaded — all packages exist,
   all symbols are interned, all functions are defined.  Install every
   remaining const pool so the saved image contains complete Lisp state.
   At launch time, zero const pool callbacks will fire.

   NOTE: Some entries may fail due to heap exhaustion (no GC is safe here
   because compacting GC invalidates package hash tables and
   RESTORE-LISP-POINTERS may not be available during early boot).
   Failed entries are logged but not fatal — the pre-save GC (below) will
   free memory, and any remaining pools will be installed on-demand at
   launch time by load-image.mjs. */
{
  const allEntries = new Set([
    ...bootConstPoolData.keys(),
    ...constPoolEntries.keys(),
  ]);
  let proactiveInstalled = 0;
  let proactiveSkipped = 0;
  let proactiveFailed = 0;
  for (const entryIndex of allEntries) {
    if (constPoolsInstalled.has(entryIndex)) {
      proactiveSkipped++;
      continue;
    }
    const rc = installConstPoolOnDemand(entryIndex);
    if (rc !== 0) {
      proactiveInstalled++;
    } else {
      proactiveFailed++;
      if (proactiveFailed <= 5) {
        console.error(`[stage] proactive const-pool install failed for entry=${entryIndex} (will install on-demand at launch)`);
      }
    }
  }
  console.error(
    `[stage] proactive const-pool install: ${proactiveInstalled} installed,` +
    ` ${proactiveSkipped} already done,` +
    ` ${constPoolsInstalled.size} total baked into image`
  );
}

/* Phase 2B: Force-rebind all WASM-compiled runtime functions.
   FASL loading silently fails to bind xfunction objects (subtag-xfunction = 0x92)
   because %defun's (typep named-fn 'function) check rejects them.  Additionally,
   early const pool install can synthesize placeholder symbols that
   wasm_set_symbol_function_entry (package-table lookup) would miss.
   wasm_force_rebind_scan does a full heap scan and unconditionally binds every
   symbol object whose pname matches a table entry — catching both the canonical
   symbol and any const-pool-synthesized placeholders.
   This runs BEFORE image save; it is NOT a launch-time repair. */
{
  const enc2 = new TextEncoder();
  const runtimeFns = (compiledModulesBundle?.functions ?? [])
    .filter(fn => fn?.name && Number.isFinite(fn.entryIndex)
                  && !bootEntryIndices.has(fn.entryIndex >>> 0));

  if (runtimeFns.length === 0) {
    fail("force-rebind: no runtime functions found in compiled modules bundle");
  }
  if (typeof ex.wasm_force_rebind_scan !== "function") {
    fail("kernel missing wasm_force_rebind_scan");
  }

  // Encode all name strings up front
  const allNameBytes = runtimeFns.map(fn => enc2.encode(fn.name));
  const tableSize = runtimeFns.length * 12;   // 12 bytes per entry: name_offset u32, name_len u32, entry_index u32
  const namesSize = allNameBytes.reduce((s, b) => s + b.length, 0);

  // Grow WASM linear memory to hold the repair table + name strings.
  // After allocScratch the buffer reference changes — always use runtime.memory.buffer.
  const tableBase = allocScratch(runtime.memory, tableSize + namesSize);
  const mem8 = new Uint8Array(runtime.memory.buffer);
  const memDV = new DataView(runtime.memory.buffer);

  // Write name strings contiguously after the table, then back-fill table entries.
  let nameWriteOff = tableBase + tableSize;
  for (let i = 0; i < runtimeFns.length; i++) {
    const nb = allNameBytes[i];
    mem8.set(nb, nameWriteOff);
    const eBase = tableBase + i * 12;
    memDV.setUint32(eBase,     nameWriteOff,          true);  // name_offset
    memDV.setUint32(eBase + 4, nb.length,             true);  // name_len
    memDV.setUint32(eBase + 8, runtimeFns[i].entryIndex >>> 0, true);  // entry_index
    nameWriteOff += nb.length;
  }

  const rebound = ex.wasm_force_rebind_scan(tableBase >>> 0, runtimeFns.length >>> 0) | 0;
  console.error(`[stage] force-rebind: ${rebound} symbols rebound (${runtimeFns.length} runtime entries)`);
  if (rebound < 0) {
    fail(`wasm_force_rebind_scan failed: rc=${rebound}`);
  }
}

/* Invariant gate deferred: critical symbol fcells are patched AFTER the
   pre-toplfunc GC so wasm_set_symbol_function_entry allocates function
   objects in the Lisp heap (via wasm_misc_alloc).  Objects allocated via
   C malloc are outside the Lisp heap areas and are NOT serialized into
   root.image — the old JS-side invariant gate had this bug. */

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
/* GC before setting toplfunc: FASL loading generates temporary objects
   (reader buffers, condition objects from %KERNEL-RESTART UDF errors, etc.)
   that are never collected because the C kernel stubs do not trigger GC on
   allocation pressure.  In a native CCL build this garbage is collected
   implicitly throughout; here we must do it explicitly.  This also compacts
   the heap so the saved image contains only live data. */
if (typeof ex.wasm_trigger_gc === "function") {
  const gcFreed = ex.wasm_trigger_gc() | 0;
  console.error(`[stage] pre-toplfunc GC freed ${gcFreed} bytes`);
}

/* Invariant gate: patch ALL runtime symbol fcells using the C kernel's
   wasm_set_symbol_function_entry.  FASL loading silently fails to bind
   xfunction objects (subtag_xfunction = 0x92) because %defun's
   (typep named-fn 'function) check rejects them.  Force-rebind catches
   many but not all (pname heap scan misses ~40% of symbols).  This pass
   uses package-based lookup + heap scan fallback, patching in place when
   a valid function object already exists.
   Must run AFTER the GC (which frees heap space for new allocations). */
if (typeof ex.wasm_set_symbol_function_entry === "function") {
  const allRuntimeFns = (compiledModulesBundle?.functions ?? [])
    .filter(f => f?.name && Number.isFinite(f.entryIndex)
                 && !bootEntryIndices.has(f.entryIndex >>> 0));
  let gateOk = 0, gateFail = 0;
  for (const fn of allRuntimeFns) {
    const nameBytes = encoder.encode(fn.name);
    const namePtr = ex.malloc(nameBytes.length);
    if (!namePtr) { gateFail++; continue; }
    new Uint8Array(runtime.memory.buffer).set(nameBytes, namePtr);
    const rc = ex.wasm_set_symbol_function_entry(namePtr, nameBytes.length, fn.entryIndex, 0) | 0;
    if (typeof ex.free === "function") ex.free(namePtr);
    if (rc === 0) { gateOk++; } else { gateFail++; }
  }
  console.error(`[invariant] fcell gate: ${gateOk} set, ${gateFail} not found (${allRuntimeFns.length} runtime entries)`);
}

const setToplfuncRc = ex.wasm_set_toplfunc_entry(toplevelEntryIndex >>> 0) | 0;
if (setToplfuncRc !== 0) {
  fail(`wasm_set_toplfunc_entry(${toplevelEntryIndex}) returned ${setToplfuncRc}`);
}

/* Const pools are installed in the heap from FASL loading.
   The kernel no longer clears nrs_WASM_CONST_POOLS during reset, so they
   will be persisted in the saved image for zero-cost deterministic launch.
   The GC mark phase now roots nrs_WASM_CONST_POOLS.vcell so pool vectors
   survive collection. */
console.error(
  `[stage] const pools: ${constPoolsInstalled.size} installed (pre-baked in image),` +
  ` memory ${(runtime.memory.buffer.byteLength / (1024*1024)).toFixed(0)} MB`
);

/* Free JS-side const pool caches — no longer needed. */
bootConstPoolData.clear();

/* GC before save — the kernel's mark phase now roots the const-pools table
   through nrs_WASM_CONST_POOLS.vcell, so pool vectors survive collection
   while FASL-loading garbage is reclaimed. */

/* Pre-save GC: compact the heap to reduce image size.
   The kernel's gc-common.c now handles const pool marking and forwarding
   for out-of-area pool tables (NRS symbols are in nilreg, not the area chain). */
console.error(`[stage] running pre-save GC...`);

const preGcMem = runtime.memory.buffer.byteLength;
const gcFreed = ex.wasm_trigger_gc();
const postGcMem = runtime.memory.buffer.byteLength;
console.error(`[stage] GC freed ${gcFreed} bytes (memory: ${preGcMem} -> ${postGcMem})`);

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
let persistedBytes = Buffer.concat(chunks);
console.error(`[save-image-diag] persisted image size: ${persistedBytes.length} bytes (${(persistedBytes.length / (1024*1024)).toFixed(1)} MiB)`);

// CCL image signature constants (little-endian uint32):
//   sig0 = 0x4F70656E ('Open')  → LE bytes: 6E 65 70 4F
//   sig1 = 0x4D434C49 ('MCLI')  → LE bytes: 49 4C 43 4D
//   sig2 = 0x6D616765 ('mage')  → LE bytes: 65 67 61 6D
//   sig3 = 0x46696C65 ('File')  → LE bytes: 65 6C 69 46
const IMAGE_SIG0 = 0x4F70656E;
const IMAGE_SIG1 = 0x4D434C49;
const IMAGE_SIG2 = 0x6D616765;

if (persistedBytes.length >= 16) {
  const first16 = persistedBytes.subarray(0, 16);
  const last16 = persistedBytes.subarray(persistedBytes.length - 16);
  console.error(`[save-image-diag] first 16 bytes: ${Buffer.from(first16).toString("hex").match(/../g).join(" ")}`);
  console.error(`[save-image-diag] last 16 bytes:  ${Buffer.from(last16).toString("hex").match(/../g).join(" ")}`);

  // Check for trailer: 3 signature uint32s (LE) followed by int32 delta
  const dv = new DataView(persistedBytes.buffer, persistedBytes.byteOffset, persistedBytes.length);
  const tailOff = persistedBytes.length - 16;
  const hasTrailer = tailOff >= 0 &&
    dv.getUint32(tailOff, true) === IMAGE_SIG0 &&
    dv.getUint32(tailOff + 4, true) === IMAGE_SIG1 &&
    dv.getUint32(tailOff + 8, true) === IMAGE_SIG2;

  if (hasTrailer) {
    const delta = dv.getInt32(tailOff + 12, true);
    console.error(`[save-image-diag] trailer present at offset ${tailOff}, delta=${delta}`);
  } else {
    console.error(`[save-image-diag] trailer NOT found at end of image — appending fixup trailer`);
    // Find header position: scan from start for sig0+sig1+sig2 on a page boundary.
    // Only match the first 3 sigs (same as the trailer); sig3 may differ
    // on WASM32 (observed 0xFFFFFFF0 instead of 0x46696C65).
    let headerPos = -1;
    for (let off = 0; off <= Math.min(persistedBytes.length - 16, 65536); off += 4096) {
      if (dv.getUint32(off, true) === IMAGE_SIG0 &&
          dv.getUint32(off + 4, true) === IMAGE_SIG1 &&
          dv.getUint32(off + 8, true) === IMAGE_SIG2) {
        headerPos = off;
        console.error(`[save-image-diag] header found at offset ${off}, sig3=0x${dv.getUint32(off + 12, true).toString(16).padStart(8, "0")}`);
        break;
      }
    }
    if (headerPos >= 0) {
      // Construct trailer: sig0, sig1, sig2, delta
      // delta = header_pos - eof_pos  (negative, pointing backward)
      const eofPos = persistedBytes.length + 16; // after appending trailer
      const delta = headerPos - eofPos;
      const trailer = Buffer.alloc(16);
      trailer.writeUint32LE(IMAGE_SIG0, 0);
      trailer.writeUint32LE(IMAGE_SIG1, 4);
      trailer.writeUint32LE(IMAGE_SIG2, 8);
      // For images > 2 GiB the delta exceeds int32 range; write as
      // uint32 two's complement.  The C loader cannot load > 2 GiB
      // images anyway (lisp_lseek int32 overflow), so best-effort.
      trailer.writeUint32LE(delta >>> 0, 12);
      persistedBytes = Buffer.concat([persistedBytes, trailer]);
      console.error(`[save-image-diag] appended trailer: headerPos=${headerPos} eofPos=${eofPos} delta=${delta} (u32=0x${(delta >>> 0).toString(16)})`);
      console.error(`[save-image-diag] fixed image size: ${persistedBytes.length} bytes`);
    } else {
      console.error(`[save-image-diag] ERROR: could not find image header — cannot fix trailer`);
    }
  }
}
await fs.mkdir(path.dirname(outputPath), { recursive: true });
const tempOutputPath = `${outputPath}.tmp-${process.pid}-${Date.now()}`;
await fs.writeFile(tempOutputPath, persistedBytes);

await fs.rename(tempOutputPath, outputPath);

const compiledModulesBinaryPath = path.join(path.dirname(modulesPath), compiledModulesBundle.binary);
const compiledModulesBinaryBytes = await fs.readFile(compiledModulesBinaryPath);
const bootEntryIndex = WASM_BOOT_ENTRY_INDEX;
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

/* Phase 2B: Emit startup-plan.json and modules.bin.
   The startup plan is a flat function-table map that tells the deterministic
   launcher exactly which WASM function goes into each table slot.  modules.bin
   is a flat concatenation of all WASM module binaries (boot + runtime) with
   offsets recorded in the plan. */
{
  const startupPlanEntries = [];

  /* Subprim entries (indices 0..subprimsMap.symbols.length-1).
     Each symbol name maps to the corresponding table index. */
  const spExports = subprims.instance.exports;
  for (let i = 0; i < subprimsMap.symbols.length; i++) {
    const sym = subprimsMap.symbols[i];
    const provider = typeof spExports[sym] === "function" ? "subprims"
      : typeof ex[sym] === "function" ? "kernel" : null;
    if (provider) {
      startupPlanEntries.push({ index: i, source: provider, export: sym });
    }
  }

  /* Build modules.bin from boot + runtime module binaries with deduplication.
     Many entries share binary data at the same source offset (V2 bundle dedup).
     We detect shared spans and map them to the same modules.bin offset. */
  const bootBinBytes = bootBinaryPath ? await fs.readFile(bootBinaryPath) : null;
  let modulesBinOffset = 0;
  const modulesBinChunks = [];
  const spanDedup = new Map(); /* "srcBin:srcOffset:storedLen" → modulesBinOffset */

  function addModuleEntry(entry, srcBinLabel, srcBinBytes) {
    if (!Number.isFinite(entry?.entryIndex)) return;
    const idx = entry.entryIndex >>> 0;
    const srcOffset = entry.offset >>> 0;
    const moduleLen = entry.length >>> 0;
    const storedLen = Number.isFinite(entry?.moduleStoredLength)
      ? (entry.moduleStoredLength >>> 0) : moduleLen;
    const encoding = entry.moduleEncoding || undefined;
    const dedupKey = `${srcBinLabel}:${srcOffset}:${storedLen}`;

    let binOffset;
    if (spanDedup.has(dedupKey)) {
      binOffset = spanDedup.get(dedupKey);
    } else {
      binOffset = modulesBinOffset;
      spanDedup.set(dedupKey, binOffset);
      if (srcBinBytes && srcOffset + storedLen <= srcBinBytes.length) {
        modulesBinChunks.push(srcBinBytes.subarray(srcOffset, srcOffset + storedLen));
      }
      modulesBinOffset += storedLen;
    }

    startupPlanEntries.push({
      index: idx,
      source: "modules",
      offset: binOffset,
      length: moduleLen,
      storedLength: storedLen !== moduleLen ? storedLen : undefined,
      encoding,
      export: entry.exportName || "fn",
    });
  }

  /* Boot module entries — from hoisted bootModuleEntries (resolved bundle). */
  for (const entry of bootModuleEntries) {
    addModuleEntry(entry, "boot", bootBinBytes);
  }

  /* Runtime module entries — from resolvedBundle.modules. */
  const runtimeModules = Array.isArray(resolvedBundle?.modules) ? resolvedBundle.modules : [];
  for (const entry of runtimeModules) {
    if (!Number.isFinite(entry?.entryIndex)) continue;
    if (bootEntryIndices.has(entry.entryIndex >>> 0)) continue;
    addModuleEntry(entry, "runtime", compiledModulesBinaryBytes);
  }

  /* Sort entries by table index. */
  startupPlanEntries.sort((a, b) => a.index - b.index);

  /* Remove undefined fields for cleaner JSON. */
  const cleanEntries = startupPlanEntries.map(e => {
    const o = { index: e.index, source: e.source, export: e.export };
    if (e.source === "modules") {
      o.offset = e.offset;
      o.length = e.length;
      if (e.storedLength !== undefined) o.storedLength = e.storedLength;
      if (e.encoding !== undefined) o.encoding = e.encoding;
    }
    return o;
  });

  const startupPlan = {
    schemaVersion: 1,
    generatedAt: new Date().toISOString(),
    memory: {
      initialPages: runtime.memory.buffer.byteLength / 65536,
      imageSize: persistedBytes.length,
    },
    constPools: { baked: true, count: constPoolsInstalled.size },
    functionTable: {
      size: runtime.subprimsTable.length,
      entries: cleanEntries,
    },
    toplevelIndex: toplevelEntryIndex,
    /* Named function→entryIndex mappings for UDF binding repair at launch. */
    namedFunctions: [
      ...(Array.isArray(compiledModulesBundle?.functions)
        ? compiledModulesBundle.functions
            .filter(e => e?.name && Number.isFinite(e?.entryIndex))
            .map(e => ({ name: e.name, entryIndex: e.entryIndex >>> 0 }))
        : []),
      ...bootNamedFunctions
        .filter(e => e?.name && Number.isFinite(e?.entryIndex))
        .map(e => ({ name: e.name, entryIndex: e.entryIndex >>> 0 })),
    ],
    artifacts: {
      rootImage: { sha256: manifest.artifacts.rootImage.sha256 },
      kernelWasm: { sha256: manifest.artifacts.kernelWasm.sha256 },
      subprimsWasm: { sha256: manifest.artifacts.subprimsWasm.sha256 },
    },
  };

  const startupPlanPath = path.resolve(path.dirname(outputPath), "startup-plan.json");
  await fs.writeFile(startupPlanPath, JSON.stringify(startupPlan, null, 2));
  console.error(`[stage] startup-plan.json: ${cleanEntries.length} entries, table size ${runtime.subprimsTable.length}`);

  /* Write modules.bin — flat concatenation of all module binaries. */
  if (modulesBinChunks.length > 0) {
    const modulesBinPath = path.resolve(path.dirname(outputPath), "modules.bin");
    const modulesBinBuf = Buffer.concat(modulesBinChunks);
    await fs.writeFile(modulesBinPath, modulesBinBuf);
    startupPlan.artifacts.modulesBin = { sha256: sha256Hex(modulesBinBuf), bytes: modulesBinBuf.length };
    /* Re-write plan with modules.bin hash. */
    await fs.writeFile(startupPlanPath, JSON.stringify(startupPlan, null, 2));
    console.error(`[stage] modules.bin: ${modulesBinBuf.length} bytes (${(modulesBinBuf.length / (1024*1024)).toFixed(1)} MiB), ${modulesBinChunks.length} modules`);
  }
}

if (compiledModulesHandle) {
  await compiledModulesHandle.close();
}
if (compiledModulesFd != null) {
  fsSync.closeSync(compiledModulesFd);
}

console.log(`Wrote ${persistedBytes.length} bytes to ${outputPath}`);
console.log(`Wrote manifest to ${manifestOutPath}`);
