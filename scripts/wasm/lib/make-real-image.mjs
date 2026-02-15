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
  collectBootstrapState,
  formatBootstrapState,
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
import {
  FILE_MODE_CREATE,
  FILE_MODE_READ,
  FILE_MODE_TRUNCATE,
  FILE_MODE_WRITE,
} from "./persist-service.mjs";

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
const diagConstPoolInstallEnabled = process.env.CCL_WASM_DIAG_PREINSTALL_ATTEMPTS === "1";
const diagConstPoolContinueOnThrowEnabled = process.env.CCL_WASM_DIAG_PREINSTALL_CONTINUE_ON_THROW === "1";
function logConstPoolInstallDiag({
  phase,
  entryIndex,
  status = null,
  reason = null,
  installRc = null,
  installOk = null,
  info = null,
  errorMessage = null,
}) {
  if (!diagConstPoolInstallEnabled) return;
  const payload = {
    schema_version: "const_pool_install_attempt_v1",
    phase: typeof phase === "string" && phase.length > 0 ? phase : "unknown",
    entry_index: Number.isInteger(entryIndex) ? (entryIndex >>> 0) : null,
    status: typeof status === "string" && status.length > 0 ? status : null,
    reason: typeof reason === "string" && reason.length > 0 ? reason : null,
    install_rc: Number.isInteger(installRc) ? (installRc >>> 0) : null,
    install_ok: typeof installOk === "boolean" ? installOk : null,
    const_pool_id: Number.isInteger(info?.id) ? (info.id >>> 0) : null,
    const_pool_offset: Number.isInteger(info?.offset) ? (info.offset >>> 0) : null,
    const_pool_length: Number.isInteger(info?.length) ? (info.length >>> 0) : null,
    const_pool_stored_length: Number.isInteger(info?.storedLength) ? (info.storedLength >>> 0) : null,
    const_pool_encoding: typeof info?.encoding === "string" && info.encoding.length > 0 ? info.encoding : "raw",
    error_message: typeof errorMessage === "string" && errorMessage.length > 0 ? errorMessage : null,
  };
  console.error(`CONST_POOL_INSTALL_ATTEMPT ${JSON.stringify(payload)}`);
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
  console.log("  --kernel PATH       wasmcl.wasm path (default: build/wasm32/kernel/wasmcl.wasm)");
  console.log("  --subprims PATH     subprims.wasm path (default: build/wasm32/subprims/subprims.wasm)");
  console.log("  --subprims-map PATH subprims-map.json path (default: build/wasm32/subprims-map.json)");
  console.log("  --bootstrap-boundary-report PATH  Optional JSON state/diff report");
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
      case "--kernel":
        out.kernel = argv[++i];
        break;
      case "--subprims":
        out.subprims = argv[++i];
        break;
      case "--subprims-map":
        out.subprimsMap = argv[++i];
        break;
      case "--bootstrap-boundary-report":
        out.bootstrapBoundaryReport = argv[++i];
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

const BOOTSTRAP_STATE_PREFIX = "BOOTSTRAP_STATE_JSON ";

function parseBootstrapStateLines(text) {
  const states = [];
  for (const line of String(text ?? "").split(/\r?\n/)) {
    if (!line.startsWith(BOOTSTRAP_STATE_PREFIX)) continue;
    const payload = line.slice(BOOTSTRAP_STATE_PREFIX.length).trim();
    if (!payload) continue;
    try {
      states.push(JSON.parse(payload));
    } catch (_err) {
      // Ignore malformed lines and continue parsing others.
    }
  }
  return states;
}

function bootstrapDiff(beforeState, afterState) {
  if (!beforeState || !afterState) return [];
  const fields = [
    "nil",
    "commonLispPackage",
    "toplevelSymbol",
    "toplfuncRaw",
    "toplfuncEntryIndex",
    "toplfuncSubtag",
  ];
  const diffs = [];
  for (const field of fields) {
    const before = beforeState[field];
    const after = afterState[field];
    if (before !== after) {
      diffs.push({ field, before, after });
    }
  }
  return diffs;
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
const buildProvenancePath = args.buildProvenance
  ? path.resolve(args.buildProvenance)
  : null;
const bootstrapBoundaryReportPath = args.bootstrapBoundaryReport
  ? path.resolve(args.bootstrapBoundaryReport)
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

async function collectBootstrapStatesFromImage({
  label,
  scriptDirPath,
  repoRootPath,
  imagePathToCheck,
  runtimeModulesPath,
  mode = "start-lisp",
}) {
  const loadImageScriptPath = path.join(scriptDirPath, "load-image.mjs");
  const childArgs = [
    loadImageScriptPath,
    "--mode",
    mode,
    "--bootstrap-contract",
    "off",
    "--bootstrap-state-json",
    "--modules",
    runtimeModulesPath,
  ];
  if (mode === "start-lisp") {
    childArgs.push("--stdin-text", "(quit)\n", "--close-stdin");
  }
  childArgs.push(imagePathToCheck);

  const result = await runNodeScript(childArgs, { cwd: repoRootPath });
  if (result.code !== 0) {
    const details = [result.stdout, result.stderr]
      .filter((part) => part && part.trim().length > 0)
      .join("\n")
      .trim();
    throw new Error(
      `${label} bootstrap state probe failed (exit=${result.code}${result.signal ? ` signal=${result.signal}` : ""})` +
      (details ? `\n${details}` : ""),
    );
  }
  const states = parseBootstrapStateLines(`${result.stdout}\n${result.stderr}`);
  if (!states.length) {
    throw new Error(`${label} bootstrap state probe returned no state lines`);
  }
  return states;
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
if (traceEnabled) {
  const fasloadDiagSource = [
    '(in-package "CCL")',
    '(format t "~&FASLOAD-DIAG begin~%")',
    '(multiple-value-bind (value condition)',
    '    (ignore-errors (%fasload "level-1.lafsl"))',
    '  (format t "~&FASLOAD-DIAG value=~S~%" value)',
    '  (if condition',
    '      (progn',
    '        (format t "~&FASLOAD-DIAG condition-type=~S~%" (type-of condition))',
    '        (format t "~&FASLOAD-DIAG condition=~A~%" condition))',
    '      (format t "~&FASLOAD-DIAG condition=nil~%")))',
    '(format t "~&FASLOAD-DIAG end~%")',
    "",
  ].join("\n");
  addNamedBytes(
    namedBytes,
    "scripts/wasm/fasload-diag.lisp",
    new TextEncoder().encode(fasloadDiagSource),
  );
}
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
function runPreToplevelFunctionDesignatorGateOrFail() {
  /* No-op: RESTORE-LISP-POINTERS makes pre-toplevel symbol gating unnecessary. */
}
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
const DEFAULT_CONST_POOL_DIAG_ENTRIES = Object.freeze([4412]);
function parseConstPoolDiagEntries(rawValue) {
  const parsed = new Set();
  const text = String(rawValue ?? "").trim();
  if (!text) {
    for (const value of DEFAULT_CONST_POOL_DIAG_ENTRIES) {
      parsed.add(value >>> 0);
    }
    return parsed;
  }
  for (const part of text.split(",")) {
    const value = Number(part.trim());
    if (!Number.isInteger(value) || value < 0) continue;
    parsed.add(value >>> 0);
  }
  if (parsed.size === 0) {
    for (const value of DEFAULT_CONST_POOL_DIAG_ENTRIES) {
      parsed.add(value >>> 0);
    }
  }
  return parsed;
}
const CONST_POOL_DIAG_ENTRIES = parseConstPoolDiagEntries(
  process.env.CCL_WASM_CONST_POOL_DIAG_ENTRY,
);
const constPoolProbeInFlight = new Set();
const CONST_POOL_ERROR_NAMES = new Map([
  [0, "none"],
  [1, "symbol-read"],
  [2, "symbol-package-missing"],
  [3, "symbol-intern"],
  [4, "symbol-bad-tag"],
  [5, "symbol-intern-unavailable"],
  [6, "symbol-intern-throw"],
  [7, "symbol-intern-non-symbol"],
  [8, "function-udf"],
  [9, "function-bad-tag"],
  [10, "symbol-missing"],
]);

function hexSample(bytesLike, maxBytes = 64) {
  if (!bytesLike || bytesLike.length === 0) return "";
  const bytes = bytesLike instanceof Uint8Array ? bytesLike : Uint8Array.from(bytesLike);
  const limit = Math.min(Math.max(maxBytes | 0, 0), bytes.length);
  if (limit <= 0) return "";
  return Array.from(bytes.subarray(0, limit), (b) => b.toString(16).padStart(2, "0")).join("");
}

function readConstPoolRawSample(info, maxBytes = 64) {
  const sampleLen = Math.min(Math.max(maxBytes | 0, 0), info?.storedLength >>> 0);
  if (!Number.isFinite(sampleLen) || sampleLen <= 0) return new Uint8Array(0);
  if (constPoolSharedBlobInfo && constPoolSharedBlobRaw) {
    const start = (info.offset >>> 0) - (constPoolSharedBlobInfo.offset >>> 0);
    const end = start + sampleLen;
    if (start >= 0 && end <= constPoolSharedBlobRaw.length) {
      return constPoolSharedBlobRaw.subarray(start, end);
    }
  }
  if (compiledModulesFd == null) return new Uint8Array(0);
  const out = Buffer.allocUnsafe(sampleLen);
  const read = fsSync.readSync(compiledModulesFd, out, 0, sampleLen, info.offset >>> 0);
  if (read <= 0) return new Uint8Array(0);
  return out.subarray(0, read);
}

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
  if (!kernelExports || compiledModulesFd == null) return 0;
  const entryIndex = entryIndexRaw >>> 0;
  if (constPoolsInstalled.has(entryIndex)) {
    logConstPoolInstallDiag({
      phase: "host-install-const-pool",
      entryIndex,
      status: "already-installed",
      reason: "const-pool-already-installed",
    });
    return 1;
  }

  const info = constPoolEntries.get(entryIndex);
  if (!info) {
    logConstPoolInstallDiag({
      phase: "host-install-const-pool",
      entryIndex,
      status: "missing",
      reason: "const-pool-entry-missing",
    });
    return 0;
  }
  logConstPoolInstallDiag({
    phase: "host-install-const-pool",
    entryIndex,
    status: "begin",
    reason: "attempt-install",
    info,
  });
  const decodedBytes = decodeConstPoolForInfo(info);
  if (!decodedBytes) {
    logConstPoolInstallDiag({
      phase: "host-install-const-pool",
      entryIndex,
      status: "missing",
      reason: "const-pool-decode-missing",
      info,
    });
    return 0;
  }
  const shouldProbe = traceEnabled &&
    CONST_POOL_DIAG_ENTRIES.has(entryIndex) &&
    !constPoolProbeInFlight.has(entryIndex);
  if (shouldProbe) {
    constPoolProbeInFlight.add(entryIndex);
    const rawSample = readConstPoolRawSample(info, 64);
    const bootPhase = typeof kernelExports.wasm_boot_get_phase === "function"
      ? (kernelExports.wasm_boot_get_phase() >>> 0)
      : null;
    trace(
      `diag-const-pool entry=${entryIndex} boot_phase=${bootPhase == null ? "n/a" : formatBootPhase(bootPhase)}`,
    );
    trace(
      `diag-const-pool entry=${entryIndex}` +
      ` offset=${info.offset >>> 0}` +
      ` length=${info.length >>> 0}` +
      ` storedLength=${info.storedLength >>> 0}` +
      ` encoding=${info.encoding ?? "raw"}` +
      ` constPoolId=${info.id == null ? "null" : (info.id >>> 0)}` +
      ` baseId=${info.baseId == null ? "null" : (info.baseId >>> 0)}` +
      ` deltaOp=${info.deltaOp ?? "null"}` +
      ` raw64=${hexSample(rawSample, 64)}` +
      ` decoded64=${hexSample(decodedBytes, 64)}`,
    );
  }
  let payloadBytes = decodedBytes;
  let rewrite = null;
  try {
    try {
      rewrite = rewriteConstPoolFunctionDesignators(decodedBytes, {
        resolver: bootstrapFunctionResolver,
        entryIndex,
        requiredResolveOrFailNames: startupRequiredPreToplevelDesignators,
        deferredAllowedNames: startupDeferredPreToplevelDesignators,
        symbolToEntryFunctionNames: startupSymbolToEntryPreToplevelDesignators,
        symbolPackageOverrides: STARTUP_SYMBOL_PACKAGE_OVERRIDES_CANONICAL_V1,
      });
      payloadBytes = rewrite.bytes;
    } catch (_err) {
      payloadBytes = decodedBytes;
    }
    if ((rewrite?.deferredUnresolvedCount ?? 0) > 0) {
      const diagnostics = Array.isArray(rewrite?.deferredUnresolved) ? rewrite.deferredUnresolved : [];
      for (const item of diagnostics) {
        console.log(
          `STARTUP_CONSTPOOL_FUNCTION_GATE ${JSON.stringify({
            schema_version: "startup_constpool_function_gate_v1",
            phase: "pre-toplevel",
            status: "deferred",
            mode: "strict",
            entry_index: entryIndex >>> 0,
            const_index: Number.isFinite(item?.constIndex) ? (item.constIndex >>> 0) : null,
            symbol_name: item?.name ?? null,
            package_name: item?.packageName ?? null,
            policy_class: item?.policyClass ?? "deferred-allowed",
            binding_state: item?.bindingState ?? "deferred-symbolic-function-designator",
            reason: item?.reason ?? "missing",
          })}`,
        );
      }
    }
    if ((rewrite?.requiredUnresolvedCount ?? 0) > 0) {
      const diagnostics = Array.isArray(rewrite?.requiredUnresolved) ? rewrite.requiredUnresolved : [];
      for (const item of diagnostics) {
        console.error(
          `STARTUP_CONSTPOOL_FUNCTION_GATE ${JSON.stringify({
            schema_version: "startup_constpool_function_gate_v1",
            phase: "pre-toplevel",
            status: "fail",
            mode: "strict",
            entry_index: entryIndex >>> 0,
            const_index: Number.isFinite(item?.constIndex) ? (item.constIndex >>> 0) : null,
            symbol_name: item?.name ?? null,
            package_name: item?.packageName ?? null,
            policy_class: item?.policyClass ?? "required-resolve-or-fail",
            binding_state: item?.bindingState ?? "unresolved-required-function-designator",
            reason: item?.reason ?? "missing",
          })}`,
        );
      }
      fail(
        `startup const-pool function gate failed for entry ${entryIndex}: unresolved required designators=` +
        diagnostics.map((item) => String(item?.name ?? "").trim()).filter(Boolean).join(","),
      );
    }

    if (shouldProbe && payloadBytes !== decodedBytes) {
      trace(`diag-const-pool entry=${entryIndex} rewritten64=${hexSample(payloadBytes, 64)}`);
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
    const installOk = rc !== 0 && (nilValue == null || rc !== nilValue);
    if (!installOk) {
      logConstPoolInstallDiag({
        phase: "host-install-const-pool",
        entryIndex,
        status: "result",
        reason: "const-pool-install-returned-nil-or-zero",
        installRc: rc >>> 0,
        installOk,
        info,
      });
      return 0;
    }

    constPoolsInstalled.add(entryIndex);
    logConstPoolInstallDiag({
      phase: "host-install-const-pool",
      entryIndex,
      status: "result",
      reason: "const-pool-install-succeeded",
      installRc: rc >>> 0,
      installOk,
      info,
    });
    return 1;
  } catch (error) {
    const errorMessage = error instanceof Error
      ? error.message
      : String(error ?? "");
    logConstPoolInstallDiag({
      phase: "host-install-const-pool",
      entryIndex,
      status: "throw",
      reason: "const-pool-install-threw",
      info,
      errorMessage,
    });
    if (diagConstPoolContinueOnThrowEnabled) {
      logConstPoolInstallDiag({
        phase: "host-install-const-pool",
        entryIndex,
        status: "result",
        reason: "const-pool-install-threw-continued-by-env",
        installOk: false,
        info,
        errorMessage,
      });
      return 0;
    }
    throw error;
  } finally {
    if (shouldProbe) {
      constPoolProbeInFlight.delete(entryIndex);
    }
  }
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

const SPECREF_FAILURE_STAGE_NAMES = new Map([
  [0, "none"],
  [1, "tcr-null"],
  [2, "symbol-fulltag"],
  [3, "symbol-subtag"],
  [4, "binding-index-tag"],
  [5, "tlb-limit-tag"],
  [6, "tlb-pointer-null"],
]);
const KEYWORD_BIND_STAGE_NAMES = new Map([
  [0, "none"],
  [1, "tcr-null"],
  [2, "raw-tag"],
  [3, "negative-count"],
  [4, "fn-not-misc"],
  [5, "keyvec-not-misc"],
  [6, "keyvec-length-range"],
  [7, "stack-null"],
  [255, "done"],
]);
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
  bootCompiledModuleRegistry !== bootCompiledModuleRegistryNil;
if (traceEnabled) {
  trace(
    `boot-registry snapshot raw=0x${bootCompiledModuleRegistry.toString(16)}` +
    ` nil=0x${bootCompiledModuleRegistryNil.toString(16)}` +
    ` has_snapshot=${hasBootCompiledModuleRegistrySnapshot ? 1 : 0}`,
  );
}

if (process.env.CCL_WASM_DIAG_START_LISP_BEFORE_MODULE_INSTALL === "1") {
  if (typeof ex.wasm_ccl_start_lisp !== "function") {
    fail("kernel missing wasm_ccl_start_lisp for CCL_WASM_DIAG_START_LISP_BEFORE_MODULE_INSTALL");
  }
  if (typeof ex.wasm_set_subprims_ready === "function") {
    ex.wasm_set_subprims_ready(1);
  }
  const pendingBefore = typeof ex.wasm_pending_throw_p === "function"
    ? (ex.wasm_pending_throw_p() >>> 0)
    : null;
  const rc = ex.wasm_ccl_start_lisp() >>> 0;
  const pendingAfter = typeof ex.wasm_pending_throw_p === "function"
    ? (ex.wasm_pending_throw_p() >>> 0)
    : null;
  const pendingRaw = typeof ex.wasm_pending_throw_raw === "function"
    ? (ex.wasm_pending_throw_raw() >>> 0)
    : null;
  trace(
    `diag start_lisp_before_module_install rc=0x${rc.toString(16)}` +
    (pendingBefore == null ? "" : ` pending_before=${pendingBefore}`) +
    (pendingAfter == null ? "" : ` pending_after=${pendingAfter}`) +
    (pendingRaw == null ? "" : ` pending_raw=0x${pendingRaw.toString(16)}`),
  );
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
runPreToplevelFunctionDesignatorGateOrFail();

const diagRunToplevelEarly = process.env.CCL_WASM_DIAG_RUN_TOPLEVEL_EARLY === "1";
const diagRunToplevelEarlyOnly = process.env.CCL_WASM_DIAG_RUN_TOPLEVEL_EARLY_ONLY === "1";
if (diagRunToplevelEarly) {
  if (typeof ex.wasm_run_toplevel !== "function") {
    fail("kernel missing wasm_run_toplevel for CCL_WASM_DIAG_RUN_TOPLEVEL_EARLY");
  }
  const pendingBefore = typeof ex.wasm_pending_throw_p === "function"
    ? (ex.wasm_pending_throw_p() >>> 0)
    : null;
  trace(`diag early_toplevel pre pending=${pendingBefore == null ? "n/a" : pendingBefore}`);
  const rc = ex.wasm_run_toplevel() | 0;
  const pendingAfter = typeof ex.wasm_pending_throw_p === "function"
    ? (ex.wasm_pending_throw_p() >>> 0)
    : null;
  const pendingRaw = typeof ex.wasm_pending_throw_raw === "function"
    ? (ex.wasm_pending_throw_raw() >>> 0)
    : null;
  trace(
    `diag early_toplevel post rc=${rc}` +
    (pendingAfter == null ? "" : ` pending=${pendingAfter}`) +
    (pendingRaw == null ? "" : ` pending_raw=0x${pendingRaw.toString(16)}`),
  );
  if (diagRunToplevelEarlyOnly) {
    trace("diag early_toplevel complete; exiting early (CCL_WASM_DIAG_RUN_TOPLEVEL_EARLY_ONLY=1)");
    process.exit(0);
  }
}
const diagPreFasloadToplfuncEntryRaw = process.env.CCL_WASM_DIAG_PRE_FASLOAD_TOPLFUNC_ENTRY;
if (diagPreFasloadToplfuncEntryRaw != null && diagPreFasloadToplfuncEntryRaw !== "") {
  if (typeof ex.wasm_set_toplfunc_entry !== "function") {
    fail("kernel missing wasm_set_toplfunc_entry for CCL_WASM_DIAG_PRE_FASLOAD_TOPLFUNC_ENTRY");
  }
  const parsed = Number(diagPreFasloadToplfuncEntryRaw);
  if (!Number.isInteger(parsed) || parsed < 0) {
    fail(`invalid CCL_WASM_DIAG_PRE_FASLOAD_TOPLFUNC_ENTRY=${JSON.stringify(diagPreFasloadToplfuncEntryRaw)}`);
  }
  const setRc = ex.wasm_set_toplfunc_entry(parsed >>> 0) | 0;
  trace(`diag pre_fasload_set_toplfunc entry=${parsed} rc=${setRc}`);
  if (setRc !== 0) {
    fail(`wasm_set_toplfunc_entry(${parsed}) failed during pre-fasload diag: rc=${setRc}`);
  }

  if (process.env.CCL_WASM_DIAG_RUN_TOPLEVEL_AFTER_PRESET === "1") {
    if (typeof ex.wasm_run_toplevel !== "function") {
      fail("kernel missing wasm_run_toplevel for CCL_WASM_DIAG_RUN_TOPLEVEL_AFTER_PRESET");
    }
    const prePending = typeof ex.wasm_pending_throw_p === "function"
      ? (ex.wasm_pending_throw_p() >>> 0)
      : null;
    const runRc = ex.wasm_run_toplevel() | 0;
    const postPending = typeof ex.wasm_pending_throw_p === "function"
      ? (ex.wasm_pending_throw_p() >>> 0)
      : null;
    const postPendingRaw = typeof ex.wasm_pending_throw_raw === "function"
      ? (ex.wasm_pending_throw_raw() >>> 0)
      : null;
    trace(
      `diag pre_fasload_toplevel_run rc=${runRc}` +
      (prePending == null ? "" : ` pre_pending=${prePending}`) +
      (postPending == null ? "" : ` post_pending=${postPending}`) +
      (postPendingRaw == null ? "" : ` post_pending_raw=0x${postPendingRaw.toString(16)}`),
    );
  }
}
if (process.env.CCL_WASM_DIAG_START_LISP_ONCE === "1") {
  if (typeof ex.wasm_ccl_start_lisp !== "function") {
    fail("kernel missing wasm_ccl_start_lisp for CCL_WASM_DIAG_START_LISP_ONCE");
  }
  const pendingBefore = typeof ex.wasm_pending_throw_p === "function"
    ? (ex.wasm_pending_throw_p() >>> 0)
    : null;
  const rc = ex.wasm_ccl_start_lisp() >>> 0;
  const pendingAfter = typeof ex.wasm_pending_throw_p === "function"
    ? (ex.wasm_pending_throw_p() >>> 0)
    : null;
  const pendingRaw = typeof ex.wasm_pending_throw_raw === "function"
    ? (ex.wasm_pending_throw_raw() >>> 0)
    : null;
  trace(
    `diag start_lisp_once rc=0x${rc.toString(16)}` +
    (pendingBefore == null ? "" : ` pending_before=${pendingBefore}`) +
    (pendingAfter == null ? "" : ` pending_after=${pendingAfter}`) +
    (pendingRaw == null ? "" : ` pending_raw=0x${pendingRaw.toString(16)}`),
  );
}
const encoder = new TextEncoder();

const L0_PROBE_STATUS = Object.freeze({
  OK: 0,
  ARG_INVALID: 1,
  PACKAGE_MISSING: 2,
  SYMBOL_MISSING: 3,
  SYMBOL_NOT_SYMBOL: 4,
  SYMBOL_INVALID: 5,
  PACKAGE_NOT_PACKAGE: 6,
});

const L0_PROBE_STATUS_NAMES = new Map([
  [L0_PROBE_STATUS.OK, "ok"],
  [L0_PROBE_STATUS.ARG_INVALID, "arg-invalid"],
  [L0_PROBE_STATUS.PACKAGE_MISSING, "package-missing"],
  [L0_PROBE_STATUS.SYMBOL_MISSING, "symbol-missing"],
  [L0_PROBE_STATUS.SYMBOL_NOT_SYMBOL, "symbol-not-symbol"],
  [L0_PROBE_STATUS.SYMBOL_INVALID, "symbol-invalid"],
  [L0_PROBE_STATUS.PACKAGE_NOT_PACKAGE, "package-not-package"],
]);

const WASM_SYMBOL_TARGET_CELL = Object.freeze({
  VCELL: 1,
  FCELL: 2,
});

const WASM_SYMBOL_CELL_INITIALIZER_KIND = Object.freeze({
  LITERAL_FIXNUM: 1,
  LITERAL_NIL: 2,
  ENTRY_FUNCTION: 3,
  LITERAL_SYMBOL: 4,
  LITERAL_KEYWORD: 5,
});

const LITERAL_SYMBOL_KEYWORD_RUNTIME_GUARDS = Object.freeze({
  "literal-symbol": Object.freeze({
    initializer_label: "symbol literal",
    optional_defer_reason: "initializer-kind-not-supported",
    required_exports: Object.freeze([
      "wasm_set_symbol_cell_initializer",
      "wasm_probe_symbol",
    ]),
  }),
  "literal-keyword": Object.freeze({
    initializer_label: "keyword literal",
    optional_defer_reason: "initializer-kind-not-supported",
    required_exports: Object.freeze([
      "wasm_set_symbol_cell_initializer",
      "wasm_probe_symbol",
    ]),
  }),
});

function l0ProbeStatusName(status) {
  return L0_PROBE_STATUS_NAMES.get(status >>> 0) ?? `status-${status >>> 0}`;
}

function startupSymbolResolutionReasonForProbeStatus(status) {
  switch (status >>> 0) {
    case L0_PROBE_STATUS.PACKAGE_MISSING:
      return "package-missing";
    case L0_PROBE_STATUS.SYMBOL_MISSING:
      return "symbol-missing";
    case L0_PROBE_STATUS.ARG_INVALID:
      return "arg-invalid";
    case L0_PROBE_STATUS.SYMBOL_NOT_SYMBOL:
      return "symbol-not-symbol";
    case L0_PROBE_STATUS.SYMBOL_INVALID:
      return "symbol-invalid";
    case L0_PROBE_STATUS.PACKAGE_NOT_PACKAGE:
      return "package-not-package";
    default:
      return "probe-status-not-ok";
  }
}






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
const pendingThrowProbe = typeof ex.wasm_pending_throw_p === "function"
  ? () => (ex.wasm_pending_throw_p() >>> 0)
  : null;
const pendingThrowRawProbe = typeof ex.wasm_pending_throw_raw === "function"
  ? () => (ex.wasm_pending_throw_raw() >>> 0)
  : null;

/* Startup symbol resolution build removed — RESTORE-LISP-POINTERS handles fixup. */


/* Startup binding map removed — RESTORE-LISP-POINTERS (called after image
   load) rehashes package tables so normal Lisp symbol resolution works.
   No pre-binding or contract assertion needed. */
setBootPhaseOrFail(WASM_BOOT_PHASE.L0_READY, { reason: "restore-lisp-pointers-complete" });

const runBoundaryProbes = process.env.CCL_WASM_RUN_BOUNDARY_PROBES === "1";
const boundaryProbeOnly = process.env.CCL_WASM_BOUNDARY_PROBE_ONLY === "1";
const boundaryProbeStrict = process.env.CCL_WASM_BOUNDARY_PROBES_STRICT === "1";
if (runBoundaryProbes) {
  if (typeof ex.wasm_probe_foreign_call1 !== "function") {
    fail("kernel missing wasm_probe_foreign_call1 for boundary probes");
  }
  const boundaryProbeScratch = sharedProbeUtf8Scratch;
  const runBoundaryProbe = (name, mode, arg) => {
    boundaryProbeScratch.reset();
    if (typeof ex.wasm_clear_pending_throw === "function") {
      ex.wasm_clear_pending_throw();
    }
    const argMem = boundaryProbeScratch.allocUtf8(String(arg ?? ""), encoder);
    const rc = ex.wasm_probe_foreign_call1(
      mode >>> 0,
      argMem.ptr >>> 0,
      argMem.len >>> 0,
    ) | 0;
    const pending = pendingThrowProbe ? pendingThrowProbe() : null;
    const pendingRaw = pendingThrowRawProbe ? pendingThrowRawProbe() : null;
    const pendingName = pendingRaw != null && null;
    console.log(
      `boundary_probe name=${name} mode=${mode} rc=${rc}` +
      (pending == null ? "" : ` pending=${pending}`) +
      (pendingRaw == null ? "" : ` pending_raw=0x${pendingRaw.toString(16)}`) +
      (pendingName ? ` pending_symbol=${JSON.stringify(pendingName)}` : ""),
    );
    return { rc, pending };
  };

  const identityProbe = runBoundaryProbe("identity", 1, "wasm-boundary-identity");
  if (boundaryProbeStrict && (identityProbe.rc !== 0 || identityProbe.pending !== 0)) {
    fail(`boundary identity probe expected rc=0 pending=0, got rc=${identityProbe.rc} pending=${identityProbe.pending}`);
  } else if (identityProbe.rc !== 0 || identityProbe.pending !== 0) {
    console.warn(`WARN: boundary identity probe non-clean (set CCL_WASM_BOUNDARY_PROBES_STRICT=1 to enforce) rc=${identityProbe.rc} pending=${identityProbe.pending}`);
  }

  const errorProbe = runBoundaryProbe("error", 2, "wasm-boundary-error");
  if (boundaryProbeStrict && (errorProbe.rc !== -7 || errorProbe.pending !== 1)) {
    fail(`boundary error probe expected rc=-7 pending=1, got rc=${errorProbe.rc} pending=${errorProbe.pending}`);
  } else if (errorProbe.rc !== -7 || errorProbe.pending !== 1) {
    console.warn(`WARN: boundary error probe shape changed (set CCL_WASM_BOUNDARY_PROBES_STRICT=1 to enforce) rc=${errorProbe.rc} pending=${errorProbe.pending}`);
  }

  if (typeof ex.wasm_clear_pending_throw === "function") {
    ex.wasm_clear_pending_throw();
  }
  runBoundaryProbe("fasload.target", 0, "level-1.lafsl");
  runBoundaryProbe("fasload.missing", 0, "__missing__/missing.lafsl");

  if (typeof ex.wasm_clear_pending_throw === "function") {
    ex.wasm_clear_pending_throw();
  }
  if (boundaryProbeOnly) {
    trace("boundary probes complete; exiting early (CCL_WASM_BOUNDARY_PROBE_ONLY=1)");
    process.exit(0);
  }
}
const skipRequiredFasloads = process.env.CCL_WASM_SKIP_REQUIRED_FASLOADS === "1";
if (skipRequiredFasloads && traceEnabled) {
  trace("skipping required fasload sequence (CCL_WASM_SKIP_REQUIRED_FASLOADS=1)");
}
const classifyBoundaryUnresolvedFunction = (specrefDiag) => {
  if (!specrefDiag || typeof specrefDiag !== "object") return null;
  const symbolName = typeof specrefDiag.arg_z_symbol === "string"
    ? specrefDiag.arg_z_symbol.trim()
    : "";
  if (!symbolName) return null;
  if (Number.isInteger(specrefDiag.nfn_entry) && specrefDiag.nfn_entry >= 0) return null;
  return {
    symbol_name: symbolName,
    nfn_entry: Number.isInteger(specrefDiag.nfn_entry) ? specrefDiag.nfn_entry : null,
    nfn_owner: typeof specrefDiag.nfn_owner === "string" ? specrefDiag.nfn_owner : null,
    nargs_raw: Number.isInteger(specrefDiag.nargs_raw) ? (specrefDiag.nargs_raw >>> 0) : null,
  };
};
const probeRequiredCallableSymbolState = (packageName, symbolName) => {
  if (
    typeof ex.wasm_probe_symbol !== "function" ||
    typeof ex.wasm_probe_symbol_fcell !== "function" ||
    typeof ex.wasm_probe_last_status !== "function"
  ) {
    return {
      package_name: packageName,
      symbol_name: symbolName,
      status: "probe-exports-missing",
    };
  }
  const nil = typeof ex.wasm_get_lisp_nil === "function"
    ? (ex.wasm_get_lisp_nil() >>> 0)
    : 0;
  const boundaryDiagScratch = sharedProbeUtf8Scratch;
  boundaryDiagScratch.reset();
  const nameMem = boundaryDiagScratch.allocUtf8(String(symbolName ?? ""), encoder);
  const pkgMem = boundaryDiagScratch.allocUtf8(String(packageName ?? ""), encoder);
  const symbolRaw = ex.wasm_probe_symbol(
    nameMem.ptr >>> 0,
    nameMem.len >>> 0,
    pkgMem.ptr >>> 0,
    pkgMem.len >>> 0,
  ) >>> 0;
  const symbolStatus = ex.wasm_probe_last_status() >>> 0;
  if (symbolStatus !== L0_PROBE_STATUS.OK || symbolRaw === 0 || symbolRaw === nil) {
    return {
      package_name: packageName,
      symbol_name: symbolName,
      status: "symbol-unresolved",
      symbol_status: symbolStatus,
      symbol_status_name: l0ProbeStatusName(symbolStatus),
      symbol_raw: `0x${symbolRaw.toString(16)}`,
    };
  }
  const fcellRaw = ex.wasm_probe_symbol_fcell(symbolRaw >>> 0) >>> 0;
  const fcellStatus = ex.wasm_probe_last_status() >>> 0;
  const entryIndex = -1;
  return {
    package_name: packageName,
    symbol_name: symbolName,
    status: "ok",
    symbol_status: symbolStatus,
    symbol_status_name: l0ProbeStatusName(symbolStatus),
    symbol_raw: `0x${symbolRaw.toString(16)}`,
    fcell_status: fcellStatus,
    fcell_status_name: l0ProbeStatusName(fcellStatus),
    fcell_raw: `0x${fcellRaw.toString(16)}`,
    fcell_entry_index: entryIndex >= 0 ? (entryIndex >>> 0) : null,
  };
};
const captureRequiredFasloadBoundaryState = ({
  stage,
  faslIndex,
  faslPath,
  rc = null,
  trapMessage = null,
} = {}) => {
  const pending = pendingThrowProbe ? pendingThrowProbe() : null;
  const pendingRaw = pendingThrowRawProbe ? pendingThrowRawProbe() : null;
  const pendingSymbol = pendingRaw != null && null;
  const bootPhaseRaw = typeof ex.wasm_boot_get_phase === "function"
    ? (ex.wasm_boot_get_phase() >>> 0)
    : null;
  return {
    schema_version: "required_fasload_boundary_diag_v1",
    stage: String(stage ?? ""),
    phase: "pre-runtime-required-fasload",
    fasl_index: Number.isInteger(faslIndex) ? (faslIndex >>> 0) : null,
    first_required_fasload: faslIndex === 0,
    path: typeof faslPath === "string" ? faslPath : null,
    rc: Number.isInteger(rc) ? rc : null,
    pending_throw: pending,
    pending_throw_raw: pendingRaw == null ? null : `0x${pendingRaw.toString(16)}`,
    pending_symbol: pendingSymbol ?? null,
    boot_phase: bootPhaseRaw == null ? null : formatBootPhase(bootPhaseRaw),
    required_callable_probes: [
      probeRequiredCallableSymbolState("CCL", "%FASLOAD"),
      probeRequiredCallableSymbolState("CCL", "%FASL-OPEN"),
      probeRequiredCallableSymbolState("CCL", "%SIMPLE-FASL-OPEN"),
    ],
    trap_message: trapMessage,
  };
};
const boundaryAutobindEnabled = process.env.CCL_WASM_BOUNDARY_AUTOBIND !== "0";
const boundaryAutobindMethodFallbackEnabled = process.env.CCL_WASM_BOUNDARY_AUTOBIND_METHOD_FALLBACK === "1";
const parseBoundaryAutobindSymbolSet = (rawValue, fallbackSymbols = []) => {
  const out = new Set();
  const values = [];
  if (typeof rawValue === "string" && rawValue.trim()) {
    values.push(...rawValue.split(","));
  } else {
    values.push(...fallbackSymbols);
  }
  for (const value of values) {
    const key = String(value ?? "").trim().toUpperCase();
    if (key) out.add(key);
  }
  return out;
};
const boundaryAutobindMethodFallbackDenylist = parseBoundaryAutobindSymbolSet(
  process.env.CCL_WASM_BOUNDARY_AUTOBIND_METHOD_FALLBACK_DENYLIST,
  ["STREAM-UNREAD-CHAR"],
);
const boundaryAutobindMethodFallbackAllowlist = parseBoundaryAutobindSymbolSet(
  process.env.CCL_WASM_BOUNDARY_AUTOBIND_METHOD_FALLBACK_ALLOWLIST,
  [],
);
const parseBoundaryAutobindEntryOverrides = (raw) => {
  const out = new Map();
  const text = String(raw ?? "").trim();
  if (!text) return out;
  const parts = text.split(/[,\s]+/).map((part) => part.trim()).filter(Boolean);
  for (const part of parts) {
    const eq = part.indexOf("=");
    if (eq <= 0 || eq >= (part.length - 1)) continue;
    const key = part.slice(0, eq).trim().toUpperCase();
    if (!key) continue;
    const valueText = part.slice(eq + 1).trim();
    if (!valueText) continue;
    const valueNum = Number.parseInt(valueText, 10);
    if (!Number.isInteger(valueNum) || valueNum < 0) continue;
    out.set(key, valueNum >>> 0);
  }
  return out;
};
const boundaryAutobindEntryOverrides = parseBoundaryAutobindEntryOverrides(
  process.env.CCL_WASM_BOUNDARY_AUTOBIND_ENTRY_OVERRIDES,
);
const boundaryAutobindMethodFallbackAllowed = (symbolNameUpper) => {
  if (!boundaryAutobindMethodFallbackEnabled) return false;
  if (boundaryAutobindMethodFallbackDenylist.has(symbolNameUpper)) return false;
  if (boundaryAutobindMethodFallbackAllowlist.size > 0 && !boundaryAutobindMethodFallbackAllowlist.has(symbolNameUpper)) {
    return false;
  }
  return true;
};
const boundaryAutobindSampleSymbolsEnabled = process.env.CCL_WASM_BOUNDARY_AUTOBIND_SAMPLE_SYMBOLS !== "0";
const boundaryAutobindAttemptedSymbolsByEpoch = new Map();
let boundaryAutobindEpoch = 0;
const boundaryConstPoolRecoveryAttemptedEntries = new Set();
/* Startup binding map autobind removed — RESTORE-LISP-POINTERS handles symbol resolution. */
const traceBoundaryAutobindProbe = () => {};
const tryAutobindBoundaryUnresolvedFunction = () => false;
const tryAutobindBoundaryCandidates = (unresolvedFunction, specrefDiag) => {
  const attemptedSymbols = [];
  if (tryAutobindBoundaryUnresolvedFunction(unresolvedFunction)) {
    attemptedSymbols.push(String(unresolvedFunction?.symbol_name ?? "").trim().toUpperCase());
  }
  if (!boundaryAutobindSampleSymbolsEnabled) {
    return attemptedSymbols.length > 0;
  }
  const sampleSymbols = Array.isArray(specrefDiag?.const_pool_sample_symbols)
    ? specrefDiag.const_pool_sample_symbols
    : [];
  for (const rawSymbol of sampleSymbols) {
    const symbolName = String(rawSymbol ?? "").trim();
    if (!symbolName) continue;
    const symbolUp = symbolName.toUpperCase();
    if (attemptedSymbols.includes(symbolUp)) continue;
    if (tryAutobindBoundaryUnresolvedFunction({ symbol_name: symbolName })) {
      attemptedSymbols.push(symbolUp);
    }
  }
  return attemptedSymbols.length > 0;
};
const tryRecoverBoundaryConstPoolEntry = (specrefDiag) => {
  const constPoolEntry = Number(specrefDiag?.const_pool_entry);
  if (!Number.isInteger(constPoolEntry) || constPoolEntry < 0) {
    if (traceEnabled) {
      trace(`boundary-const-pool-recovery skipped entry=${String(specrefDiag?.const_pool_entry ?? "n/a")}`);
    }
    return false;
  }
  const entryIndex = constPoolEntry >>> 0;
  if (boundaryConstPoolRecoveryAttemptedEntries.has(entryIndex)) {
    if (traceEnabled) {
      trace(`boundary-const-pool-recovery skipped-already-attempted entry=${entryIndex}`);
    }
    return false;
  }
  boundaryConstPoolRecoveryAttemptedEntries.add(entryIndex);
  const status = installConstPoolOnDemand(entryIndex);
  if (traceEnabled) {
    trace(`boundary-const-pool-recovery entry=${entryIndex} status=${status}`);
  }
  if (status === 1) {
    boundaryAutobindEpoch = (boundaryAutobindEpoch + 1) >>> 0;
  }
  return status === 1;
};
const requiredFasloadQueue = skipRequiredFasloads ? [] : requiredFasls;
for (let faslIndex = 0; faslIndex < requiredFasloadQueue.length; faslIndex++) {
  const faslPath = requiredFasloadQueue[faslIndex];
  if (faslIndex === 0) {
    console.error(`REQUIRED_FASLOAD_BOUNDARY_DIAG_BEFORE ${JSON.stringify(captureRequiredFasloadBoundaryState({
      stage: "before-call",
      faslIndex,
      faslPath,
    }))}`);
  }
  if (traceEnabled && pendingThrowProbe) {
    trace(`fasload pre path=${faslPath} pending=${pendingThrowProbe()}`);
  }
  const fasloadPathScratch = sharedProbeUtf8Scratch;
  fasloadPathScratch.reset();
  const faslMem = fasloadPathScratch.allocUtf8(String(faslPath ?? ""), encoder);
  let faslRc = 0;
  try {
    faslRc = ex.wasm_fasload_path(faslMem.ptr >>> 0, faslMem.len >>> 0) | 0;
  } catch (err) {
    const trapStack = typeof err?.stack === "string"
      ? err.stack.split("\n").slice(0, 12).join(" | ")
      : null;
    if (traceEnabled && trapStack) {
      trace(`fasload trap stack=${JSON.stringify(trapStack)}`);
    }
    if (faslIndex === 0) {
      console.error(`REQUIRED_FASLOAD_BOUNDARY_DIAG_AFTER ${JSON.stringify(captureRequiredFasloadBoundaryState({
        stage: "after-trap",
        faslIndex,
        faslPath,
        rc: null,
        trapMessage: err?.message ?? String(err),
      }))}`);
    }
    const specrefDiag = null;
    const unresolvedFunction = classifyBoundaryUnresolvedFunction(specrefDiag);
    const boundaryReason = unresolvedFunction
      ? "required-fasload-unresolved-function-symbol"
      : "required-fasload-trap";
    const pending = pendingThrowProbe ? pendingThrowProbe() : null;
    const pendingRaw = pendingThrowRawProbe ? pendingThrowRawProbe() : null;
    const pendingSymbol = pendingRaw != null && null;
    const bootPhaseRaw = typeof ex.wasm_boot_get_phase === "function"
      ? (ex.wasm_boot_get_phase() >>> 0)
      : null;
    console.error(`REQUIRED_FASLOAD_BOUNDARY ${JSON.stringify({
      schema_version: "required_fasload_boundary_v1",
      status: "fail",
      phase: "pre-runtime-required-fasload",
      fasl_index: faslIndex >>> 0,
      first_required_fasload: faslIndex === 0,
      path: faslPath,
      rc: null,
      pending_throw: pending,
      pending_throw_raw: pendingRaw == null ? null : `0x${pendingRaw.toString(16)}`,
      pending_symbol: pendingSymbol ?? null,
      boot_phase: bootPhaseRaw == null ? null : formatBootPhase(bootPhaseRaw),
      reason: boundaryReason,
      unresolved_function_symbol: unresolvedFunction,
      trap_message: err?.message ?? String(err),
      trap_stack: trapStack,
    })}`);
    const autobindApplied = tryAutobindBoundaryCandidates(unresolvedFunction, specrefDiag);
    const constPoolRecovered = tryRecoverBoundaryConstPoolEntry(specrefDiag);
    if (autobindApplied || constPoolRecovered) {
      if (typeof ex.wasm_clear_pending_throw === "function") {
        ex.wasm_clear_pending_throw();
      }
      faslIndex = Math.max(-1, (faslIndex | 0) - 1);
      continue;
    }
    fail(`wasm_fasload_path(${faslPath}) trapped: ${err?.message ?? err}`);
  }
  if (traceEnabled && pendingThrowProbe) {
    const pendingRaw = pendingThrowRawProbe ? pendingThrowRawProbe() : null;
    const pendingName = pendingRaw != null && null;
    trace(
      `fasload post path=${faslPath} rc=${faslRc} pending=${pendingThrowProbe()}` +
      (pendingRaw == null ? "" : ` pending_raw=0x${pendingRaw.toString(16)}`) +
      (pendingName ? ` pending_symbol=${JSON.stringify(pendingName)}` : ""),
    );
  }
  if (faslIndex === 0) {
    console.error(`REQUIRED_FASLOAD_BOUNDARY_DIAG_AFTER ${JSON.stringify(captureRequiredFasloadBoundaryState({
      stage: faslRc === 0 ? "after-rc-ok" : "after-rc-fail",
      faslIndex,
      faslPath,
      rc: faslRc,
    }))}`);
  }
  if (faslRc !== 0) {
    const specrefDiag = null;
    const unresolvedFunction = classifyBoundaryUnresolvedFunction(specrefDiag);
    const boundaryReason = unresolvedFunction
      ? "required-fasload-unresolved-function-symbol"
      : "required-fasload-failed";
    const pending = pendingThrowProbe ? pendingThrowProbe() : null;
    const pendingRaw = pendingThrowRawProbe ? pendingThrowRawProbe() : null;
    const pendingSymbol = pendingRaw != null && null;
    const bootPhaseRaw = typeof ex.wasm_boot_get_phase === "function"
      ? (ex.wasm_boot_get_phase() >>> 0)
      : null;
    console.error(`REQUIRED_FASLOAD_BOUNDARY ${JSON.stringify({
      schema_version: "required_fasload_boundary_v1",
      status: "fail",
      phase: "pre-runtime-required-fasload",
      fasl_index: faslIndex >>> 0,
      first_required_fasload: faslIndex === 0,
      path: faslPath,
      rc: faslRc,
      pending_throw: pending,
      pending_throw_raw: pendingRaw == null ? null : `0x${pendingRaw.toString(16)}`,
      pending_symbol: pendingSymbol ?? null,
      boot_phase: bootPhaseRaw == null ? null : formatBootPhase(bootPhaseRaw),
      reason: boundaryReason,
      unresolved_function_symbol: unresolvedFunction,
    })}`);
    const autobindApplied = tryAutobindBoundaryCandidates(unresolvedFunction, specrefDiag);
    const constPoolRecovered = tryRecoverBoundaryConstPoolEntry(specrefDiag);
    if (autobindApplied || constPoolRecovered) {
      if (typeof ex.wasm_clear_pending_throw === "function") {
        ex.wasm_clear_pending_throw();
      }
      faslIndex = Math.max(-1, (faslIndex | 0) - 1);
      continue;
    }
    if (traceEnabled) {
      const nargsRaw = typeof ex.wasm_get_nargs === "function" ? (ex.wasm_get_nargs() >>> 0) : null;
      const nargsCount = (nargsRaw != null && (nargsRaw & 0x7) === 0)
        ? (nargsRaw >> 3)
        : null;
      trace(`fasload failure nargs_raw=${nargsRaw == null ? "n/a" : `0x${nargsRaw.toString(16)}`} count=${nargsCount == null ? "n/a" : nargsCount}`);
      if (typeof ex.wasm_vsp_ref === "function" && Number.isFinite(nargsCount) && nargsCount > 0) {
        const dumpCount = Math.min(nargsCount, 8);
        for (let i = 0; i < dumpCount; i++) {
          const value = ex.wasm_vsp_ref(i >>> 0) >>> 0;
          const subtag = null;
          const symbolName = null;
          trace(
            `fasload failure vsp[${i}]=0x${value.toString(16)} subtag=${subtag == null ? "n/a" : subtag}` +
            (symbolName ? ` symbol=${JSON.stringify(symbolName)}` : ""),
          );
        }
      }
      const registerReaders = [
        ["arg_z", ex.wasm_get_arg_z],
        ["arg_y", ex.wasm_get_arg_y],
        ["nfn", ex.wasm_get_nfn],
        ["nargs", ex.wasm_get_nargs],
      ];
      for (const [name, reader] of registerReaders) {
        if (typeof reader !== "function") continue;
        const value = reader() >>> 0;
        const subtag = null;
        const symbolName = null;
        trace(
          `fasload failure reg ${name}=0x${value.toString(16)} subtag=${subtag == null ? "n/a" : subtag}` +
          (symbolName ? ` symbol=${JSON.stringify(symbolName)}` : ""),
        );
      }
      if (typeof ex.wasm_get_lisp_nil === "function") {
        const nilValue = ex.wasm_get_lisp_nil() >>> 0;
        trace(`fasload failure lisp_nil=0x${nilValue.toString(16)}`);
      }
      if (typeof ex.wasm_run_script_with_output === "function") {
        if (typeof ex.wasm_clear_pending_throw === "function") {
          ex.wasm_clear_pending_throw();
        }
        const diagPath = "scripts/wasm/fasload-diag.lisp";
        const diagPathScratch = sharedProbeUtf8Scratch;
        diagPathScratch.reset();
        const diagPathMem = diagPathScratch.allocUtf8(String(diagPath ?? ""), encoder);
        const diagRc = ex.wasm_run_script_with_output(diagPathMem.ptr >>> 0, diagPathMem.len >>> 0, 0, 0) | 0;
        trace(`fasload diag script rc=${diagRc}`);
      }
    }
    fail(`wasm_fasload_path(${faslPath}) returned ${faslRc}`);
  }
  if (faslIndex === 0) {
    const bootPhaseRaw = typeof ex.wasm_boot_get_phase === "function"
      ? (ex.wasm_boot_get_phase() >>> 0)
      : null;
    console.log(`REQUIRED_FASLOAD_BOUNDARY ${JSON.stringify({
      schema_version: "required_fasload_boundary_v1",
      status: "pass",
      phase: "pre-runtime-required-fasload",
      fasl_index: 0,
      first_required_fasload: true,
      path: faslPath,
      rc: faslRc,
      boot_phase: bootPhaseRaw == null ? null : formatBootPhase(bootPhaseRaw),
      reason: "first-required-fasload-crossed",
    })}`);
  }
}
if (!skipRequiredFasloads && requiredFasls.length > 0) {
  setBootPhaseOrFail(WASM_BOOT_PHASE.RUNTIME, { reason: "post-required-fasload-boundary" });
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

let preSaveBootstrapState = null;
try {
  preSaveBootstrapState = collectBootstrapState({ kernelExports: ex });
  console.log(`bootstrap_boundary pre-save ${formatBootstrapState(preSaveBootstrapState)}`);
} catch (err) {
  console.warn(`WARN: unable to capture pre-save bootstrap state: ${err?.message ?? err}`);
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

let boundaryReport = null;
try {
  const candidateStates = await collectBootstrapStatesFromImage({
    label: "emitted root.image candidate",
    scriptDirPath: scriptDir,
    repoRootPath: root,
    imagePathToCheck: tempOutputPath,
    runtimeModulesPath: modulesPath,
    mode: "start-lisp",
  });
  const reloadedPreStart = candidateStates.find((item) => item?.phase === "pre-start") ?? null;
  const reloadedPostStart = candidateStates.find((item) => item?.phase === "post-start") ?? null;
  if (reloadedPreStart) {
    console.log(`bootstrap_boundary reload-pre ${formatBootstrapState(reloadedPreStart)}`);
  }
  if (reloadedPostStart) {
    console.log(`bootstrap_boundary reload-post ${formatBootstrapState(reloadedPostStart)}`);
  }
  const preVsReloadDiff = bootstrapDiff(preSaveBootstrapState, reloadedPreStart);
  if (preVsReloadDiff.length) {
    for (const item of preVsReloadDiff) {
      console.log(`bootstrap_boundary diff ${item.field}: ${item.before} -> ${item.after}`);
    }
  } else if (preSaveBootstrapState && reloadedPreStart) {
    console.log("bootstrap_boundary diff: no pre-save vs reload-pre differences");
  }
  boundaryReport = {
    generatedAt: new Date().toISOString(),
    sourceImage: displayPath(bootImagePath),
    emittedCandidate: displayPath(tempOutputPath),
    preSaveState: preSaveBootstrapState,
    reloadPreStartState: reloadedPreStart,
    reloadPostStartState: reloadedPostStart,
    preSaveVsReloadPreDiff: preVsReloadDiff,
  };
} catch (err) {
  console.warn(`WARN: bootstrap boundary probe failed: ${err?.message ?? err}`);
}

if (bootstrapBoundaryReportPath && boundaryReport) {
  await fs.mkdir(path.dirname(bootstrapBoundaryReportPath), { recursive: true });
  await fs.writeFile(bootstrapBoundaryReportPath, canonicalJson(boundaryReport));
  console.log(`Wrote bootstrap boundary report to ${bootstrapBoundaryReportPath}`);
}

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
