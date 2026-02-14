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
import { BOOTSTRAP_L0_CONTRACT_V1 } from "./bootstrap-l0-contract.mjs";
import {
  BOOTSTRAP_RESOLVER_PHASE_BOOTSTRAP,
  createBootstrapFunctionResolver,
  registerResolverFunctionsFromBundle,
  STARTUP_SYMBOL_PACKAGE_OVERRIDES_CANONICAL_V1,
  rewriteConstPoolFunctionDesignators,
} from "./bootstrap-function-resolver.mjs";
import {
  normalizeStartupBindingMapArtifact,
  summarizeStartupBindingMapArtifact,
  augmentStartupBindingMapArtifactWithContractConstPoolFunctions as
    augmentStartupBindingMapArtifactWithContractConstPoolFunctionsFromBuilder,
} from "./startup-binding-map.mjs";
import { FILE_MODE_READ } from "./persist-service.mjs";

const STARTUP_SYMBOL_SCOPE_SCHEMA_V1 = "startup_symbol_scope_v1";
const STARTUP_SYMBOL_SCOPE_FIELD_SCHEMA_VERSION = "schema_version";
const STARTUP_SYMBOL_SCOPE_FIELD_GENERATOR_VERSION = "generator_version";
const STARTUP_SYMBOL_SCOPE_FIELD_INPUTS = "inputs";
const STARTUP_SYMBOL_SCOPE_FIELD_GENERATED_AT_UTC = "generated_at_utc";
const STARTUP_SYMBOL_RESOLUTION_SCHEMA_V1 = "startup_symbol_resolution_v1";
const STARTUP_SYMBOL_RESOLUTION_FIELD_SCHEMA_VERSION = "schema_version";
const STARTUP_SYMBOL_RESOLUTION_FIELD_GENERATOR_VERSION = "generator_version";
const STARTUP_SYMBOL_RESOLUTION_STATUS = Object.freeze({
  RESOLVED: "resolved",
  UNRESOLVED: "unresolved",
  PROBE_ERROR: "probe-error",
  INVALID_INPUT: "invalid-input",
});
const STARTUP_SYMBOL_RESOLUTION_COUNTER_FIELDS = Object.freeze([
  "total",
  "resolved",
  "unresolved",
  "probe_error",
  "invalid_input",
  "function_capable",
  "vcell_bound",
  "required_unresolved",
  "optional_unresolved",
]);
const STARTUP_SYMBOL_REQUIRED_CLASS = Object.freeze({
  REQUIRED_CALLABLE: "required-callable",
  REQUIRED_SPECIAL: "required-special",
  OPTIONAL: "optional",
  NONE: "none",
});
const REQUIRED_SPECIAL_ALLOWED_INITIALIZER_KINDS = Object.freeze(new Set([
  "literal-fixnum",
  "literal-nil",
  "literal-symbol",
  "literal-keyword",
]));
const STARTUP_SYMBOL_REQUIRED_CLASS_MAPPING_TABLE = Object.freeze([
  ["contract-required-callable", STARTUP_SYMBOL_REQUIRED_CLASS.REQUIRED_CALLABLE],
  ["contract-required-special", STARTUP_SYMBOL_REQUIRED_CLASS.REQUIRED_SPECIAL],
  ["bindable-symbol", STARTUP_SYMBOL_REQUIRED_CLASS.OPTIONAL],
  ["non-bindable-symbol", STARTUP_SYMBOL_REQUIRED_CLASS.NONE],
]);

function startupSymbolBindingKey(packageName, symbolName) {
  const packageToken = String(packageName ?? "").trim().toUpperCase();
  const symbolToken = String(symbolName ?? "").trim().toUpperCase();
  if (!packageToken || !symbolToken) return null;
  return `${packageToken}::${symbolToken}`;
}

function startupSymbolRequiredClass({
  symbolRecord,
  packageName,
  symbolName,
  requiredCallableKeys,
  requiredSpecialKeys,
}) {
  const symbolKey = startupSymbolBindingKey(packageName, symbolName);
  const bindable = Boolean(symbolRecord?.bindable);
  for (const [rule, requiredClass] of STARTUP_SYMBOL_REQUIRED_CLASS_MAPPING_TABLE) {
    if (rule === "contract-required-callable" && symbolKey && requiredCallableKeys.has(symbolKey)) {
      return requiredClass;
    }
    if (rule === "contract-required-special" && symbolKey && requiredSpecialKeys.has(symbolKey)) {
      return requiredClass;
    }
    if (rule === "bindable-symbol" && bindable) {
      return requiredClass;
    }
    if (rule === "non-bindable-symbol") {
      return requiredClass;
    }
  }
  return STARTUP_SYMBOL_REQUIRED_CLASS.NONE;
}

function createStartupSymbolResolutionCounters() {
  return Object.fromEntries(
    STARTUP_SYMBOL_RESOLUTION_COUNTER_FIELDS.map((field) => [field, 0]),
  );
}

function incrementStartupSymbolResolutionUnresolvedCounters(counters, requiredClass) {
  if (!counters || typeof counters !== "object") return;
  switch (requiredClass) {
    case STARTUP_SYMBOL_REQUIRED_CLASS.REQUIRED_CALLABLE:
    case STARTUP_SYMBOL_REQUIRED_CLASS.REQUIRED_SPECIAL:
      counters.required_unresolved++;
      break;
    case STARTUP_SYMBOL_REQUIRED_CLASS.OPTIONAL:
      counters.optional_unresolved++;
      break;
    default:
      break;
  }
}

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

function bindingStateForGateFailure(reason) {
  switch (reason) {
    case "ambiguous":
      return "ambiguous-function-designator";
    case "phase-disabled":
      return "resolver-phase-disabled";
    case "missing-name":
      return "invalid-function-designator";
    default:
      return "unresolved-required-function-designator";
  }
}

function validateStartupSymbolScopeArtifact(scopeArtifactRaw) {
  if (
    !scopeArtifactRaw ||
    typeof scopeArtifactRaw !== "object" ||
    Array.isArray(scopeArtifactRaw)
  ) {
    return {
      ok: false,
      reason: "invalid-object",
      schemaVersion: null,
    };
  }
  const schemaVersion = scopeArtifactRaw[STARTUP_SYMBOL_SCOPE_FIELD_SCHEMA_VERSION];
  if (schemaVersion !== STARTUP_SYMBOL_SCOPE_SCHEMA_V1) {
    return {
      ok: false,
      reason: "invalid-schema",
      schemaVersion: typeof schemaVersion === "string" ? schemaVersion : null,
    };
  }
  const generatorVersion = scopeArtifactRaw[STARTUP_SYMBOL_SCOPE_FIELD_GENERATOR_VERSION];
  if (typeof generatorVersion !== "string" || generatorVersion.trim() === "") {
    return {
      ok: false,
      reason: "missing-generator-version",
      schemaVersion,
    };
  }
  return {
    ok: true,
    reason: null,
    schemaVersion,
  };
}

function usage() {
  console.log("Usage: node doc/wasm/js/make-real-image.mjs [options]");
  console.log("");
  console.log("Options:");
  console.log("  --boot-image PATH   Boot image path (default: wasm-boot.image)");
  console.log("  --output PATH       Host output path (default: doc/wasm/root.image)");
  console.log("  --manifest-out PATH Root image manifest path (default: <output>.manifest.json)");
  console.log("  --build-provenance PATH Optional JSON object merged into manifest build.provenance");
  console.log("  --wasm-output PATH  Path inside wasm persistence (default: doc/wasm/root.image)");
  console.log("  --modules PATH      Compiled modules bundle (default: doc/wasm/wasm-runtime-modules.json)");
  console.log("  --kernel PATH       wasmcl.wasm path (default: doc/wasm/js/wasmcl.wasm)");
  console.log("  --subprims PATH     subprims.wasm path (default: doc/wasm/js/subprims.wasm)");
  console.log("  --subprims-map PATH subprims-map.json path (default: doc/wasm/subprims-map.json)");
  console.log("  --startup-symbol-scope PATH  Startup symbol scope JSON artifact override");
  console.log("  --startup-symbol-resolution-out PATH  Optional startup symbol resolution artifact output");
  console.log("  --startup-symbol-contract PATH  Optional startup symbol contract JSON artifact override");
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
      case "--startup-symbol-scope":
        out.startupSymbolScope = argv[++i];
        break;
      case "--startup-symbol-resolution-out":
        out.startupSymbolResolutionOut = argv[++i];
        break;
      case "--startup-symbol-contract":
        out.startupSymbolContract = argv[++i];
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

function canonicalizeStartupSymbolScopeForIdentityHash(scopeArtifactRaw) {
  if (
    !scopeArtifactRaw ||
    typeof scopeArtifactRaw !== "object" ||
    Array.isArray(scopeArtifactRaw)
  ) {
    return scopeArtifactRaw;
  }

  const canonicalScope = { ...scopeArtifactRaw };
  const inputsRaw = scopeArtifactRaw[STARTUP_SYMBOL_SCOPE_FIELD_INPUTS];
  if (inputsRaw && typeof inputsRaw === "object" && !Array.isArray(inputsRaw)) {
    const canonicalInputs = { ...inputsRaw };
    delete canonicalInputs[STARTUP_SYMBOL_SCOPE_FIELD_GENERATED_AT_UTC];
    canonicalScope[STARTUP_SYMBOL_SCOPE_FIELD_INPUTS] = canonicalInputs;
  }

  // Identity hash canonical JSON uses lexicographic object-key ordering.
  // Arrays with semantic order constraints are emitted sorted by producers.
  return sortJson(canonicalScope);
}

function startupSymbolScopeIdentityHash(scopeArtifactRaw) {
  const canonicalBytes = Buffer.from(
    canonicalJson(canonicalizeStartupSymbolScopeForIdentityHash(scopeArtifactRaw)),
    "utf8",
  );
  return sha256Hex(canonicalBytes);
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
const defaultBootImage = path.join(root, "wasm-boot.image");
const defaultOutput = path.join(root, "doc/wasm/root.image");
const defaultWasmOutput = "doc/wasm/root.image";
// Policy: keep compiled modules external by default (JSON + .bin sidecar)
// instead of embedding them in the saved heap image.
const defaultModules = path.join(root, "doc/wasm/wasm-runtime-modules.json");
const kernelPath = args.kernel ?? path.join(root, "doc/wasm/js/wasmcl.wasm");
const subprimsPath = args.subprims ?? path.join(root, "doc/wasm/js/subprims.wasm");
const subprimsMapPath = args.subprimsMap ?? path.join(root, "doc/wasm/subprims-map.json");
const bootImagePath = args.bootImage ?? defaultBootImage;
const outputPath = args.output ?? defaultOutput;
const manifestOutPath = args.manifestOut ?? `${outputPath}.manifest.json`;
const wasmOutputPath = args.wasmOutput ?? defaultWasmOutput;
const modulesPath = args.modules ?? defaultModules;
const buildProvenancePath = args.buildProvenance
  ? path.resolve(args.buildProvenance)
  : null;
const startupSymbolScopePath = args.startupSymbolScope
  ? path.resolve(args.startupSymbolScope)
  : null;
const startupSymbolResolutionOutPath = args.startupSymbolResolutionOut
  ? path.resolve(args.startupSymbolResolutionOut)
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
  fail(`Missing boot image: ${bootImagePath} (run scripts/wasm/build-wasm-boot.sh)`);
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
let startupSymbolScopeOverrideRaw = null;
const hasStartupSymbolScopeOverride = typeof startupSymbolScopePath === "string" &&
  startupSymbolScopePath.length > 0;
if (hasStartupSymbolScopeOverride) {
  try {
    startupSymbolScopeOverrideRaw = JSON.parse(await fs.readFile(startupSymbolScopePath, "utf-8"));
  } catch (err) {
    fail(
      `Unable to read --startup-symbol-scope JSON at ${startupSymbolScopePath}: ${err?.message ?? err}`,
    );
  }
}
const startupSymbolPipelineRecord = Object.freeze({
  schema_version: "startup_symbol_pipeline_v1",
  mode: "source_scope_v1",
  legacy_enabled: false,
});
console.log(`STARTUP_SYMBOL_PIPELINE ${JSON.stringify(startupSymbolPipelineRecord)}`);
function startupSymbolPipelineHardFail(reason, details = {}) {
  const record = {
    schema_version: "startup_symbol_pipeline_assert_v1",
    mode: startupSymbolPipelineRecord.mode,
    status: "fail",
    policy: "hard-fail",
    reason,
    ...details,
  };
  console.error(`STARTUP_SYMBOL_PIPELINE_ASSERT ${JSON.stringify(record)}`);
  fail(`startup symbol pipeline hard-fail: ${reason}`);
}
const embeddedStartupBindingMapRaw = hasStartupSymbolScopeOverride
  ? startupSymbolScopeOverrideRaw
  : null;
if (
  traceEnabled &&
  embeddedStartupBindingMapRaw &&
  typeof embeddedStartupBindingMapRaw === "object" &&
  !Array.isArray(embeddedStartupBindingMapRaw)
) {
  trace(
    `startup symbol scope identity hash=${startupSymbolScopeIdentityHash(embeddedStartupBindingMapRaw)} (generated_at_utc excluded)`,
  );
}
const embeddedStartupBindingMap = normalizeStartupBindingMapArtifact(
  embeddedStartupBindingMapRaw,
);
if (
  startupSymbolPipelineRecord.mode === "source_scope_v1" &&
  startupSymbolPipelineRecord.legacy_enabled === false
) {
  if (embeddedStartupBindingMapRaw == null) {
    startupSymbolPipelineHardFail("startup-symbol-scope-missing", {
      fallback_rejected: "buildStartupBindingMapArtifact",
    });
  }
  const scopeValidation = validateStartupSymbolScopeArtifact(embeddedStartupBindingMapRaw);
  if (!scopeValidation.ok) {
    startupSymbolPipelineHardFail("startup-symbol-scope-invalid-schema", {
      expected_schema_version: STARTUP_SYMBOL_SCOPE_SCHEMA_V1,
      actual_schema_version: scopeValidation.schemaVersion,
      validation_reason: scopeValidation.reason,
      fallback_rejected: "buildStartupBindingMapArtifact",
    });
  }
}
let startupBindingMapArtifact = embeddedStartupBindingMap;
let startupBindingMapSource = hasStartupSymbolScopeOverride
  ? `--startup-symbol-scope:${displayPath(startupSymbolScopePath)}`
  : "startup-symbol-scope-required";
let startupBindingMapBuildSummary = null;
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
  const requiredNames = Array.from(startupRequiredPreToplevelDesignators.values());
  if (requiredNames.length === 0) return;

  const failures = [];
  for (const symbolName of requiredNames) {
    const resolution = bootstrapFunctionResolver.resolveFunctionDesignator({ name: symbolName });
    const ok = Boolean(resolution?.ok);
    const reason = ok ? null : (resolution?.reason ?? "missing");
    const record = {
      schema_version: "startup_function_designator_gate_v1",
      phase: "pre-toplevel",
      status: ok ? "pass" : "fail",
      mode: "strict",
      symbol_name: symbolName,
      entry_index: ok ? (resolution.entryIndex >>> 0) : null,
      resolved_entry_index: ok ? (resolution.entryIndex >>> 0) : null,
      source: ok ? (resolution.source ?? null) : null,
      binding_state: ok ? "resolved-entry-function" : bindingStateForGateFailure(reason),
      reason,
    };
    if (ok) {
      console.log(`STARTUP_FUNCTION_DESIGNATOR_GATE ${JSON.stringify(record)}`);
      continue;
    }
    failures.push(record);
    console.error(`STARTUP_FUNCTION_DESIGNATOR_GATE ${JSON.stringify(record)}`);
  }

  if (failures.length > 0) {
    const sample = failures
      .map((item) => `${item.symbol_name}:${item.reason}`)
      .slice(0, 8)
      .join(", ");
    fail(`pre-toplevel function designator gate failed: count=${failures.length} sample=[${sample}]`);
  }
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
const startupBindingMapConstPoolBindings = new Map();
const startupBindingMapDeferredApplied = new Set();
const CONST_POOL_DIAG_ENTRY = 4412;
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
  memoryInitialPages: 512,
  subprimsTableInitial: 256,
  createMemory: true,
});
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

function normalizeConstPoolDefinitionAnchor(definition) {
  const definitionEntryIndex = Number(definition?.entry_index);
  const definitionConstIndex = Number(definition?.const_index);
  if (!Number.isInteger(definitionEntryIndex) || definitionEntryIndex < 0) return null;
  if (!Number.isInteger(definitionConstIndex) || definitionConstIndex < 0) return null;
  return {
    definition_entry_index: definitionEntryIndex >>> 0,
    definition_const_index: definitionConstIndex >>> 0,
    const_pool_depth: Number.isInteger(definition?.const_pool_depth)
      ? (definition.const_pool_depth >>> 0)
      : null,
  };
}

function collectConstPoolDefinitionAnchors(entry) {
  const anchors = [];
  const seen = new Set();
  const pushAnchor = (definition) => {
    const normalized = normalizeConstPoolDefinitionAnchor(definition);
    if (!normalized) return;
    const key = `${normalized.definition_entry_index}:${normalized.definition_const_index}`;
    if (seen.has(key)) return;
    seen.add(key);
    anchors.push(normalized);
  };
  pushAnchor(entry?.definition);
  for (const alias of Array.isArray(entry?.definition_aliases) ? entry.definition_aliases : []) {
    pushAnchor(alias);
  }
  return anchors;
}

function buildStartupBindingMapConstPoolBindingIndex(mapArtifact) {
  startupBindingMapConstPoolBindings.clear();
  startupBindingMapDeferredApplied.clear();
  for (const entry of Array.isArray(mapArtifact?.entries) ? mapArtifact.entries : []) {
    if (String(entry?.target_cell ?? "").toLowerCase() !== "fcell") continue;
    if (String(entry?.availability ?? "").toLowerCase() !== "entry-backed") continue;
    if (String(entry?.initializer?.kind ?? "").toLowerCase() !== "entry-function") continue;
    const resolvedEntryIndex = Number(entry?.initializer?.entry_index);
    if (!Number.isInteger(resolvedEntryIndex) || resolvedEntryIndex < 0) continue;
    const anchors = collectConstPoolDefinitionAnchors(entry);
    for (const anchor of anchors) {
      const key = anchor.definition_entry_index >>> 0;
      const bucket = startupBindingMapConstPoolBindings.get(key) ?? [];
      bucket.push({
        definition_entry_index: anchor.definition_entry_index >>> 0,
        definition_const_index: anchor.definition_const_index >>> 0,
        resolved_entry_index: resolvedEntryIndex >>> 0,
        symbol_key: typeof entry?.symbol_key === "string" ? entry.symbol_key : null,
        symbol_name: typeof entry?.symbol_name === "string" ? entry.symbol_name : null,
        package_name: typeof entry?.package_name === "string" ? entry.package_name : null,
        const_pool_depth: Number.isInteger(anchor.const_pool_depth)
          ? (anchor.const_pool_depth >>> 0)
          : null,
      });
      startupBindingMapConstPoolBindings.set(key, bucket);
    }
  }
}

const STARTUP_BINDING_MAP_PREINSTALL_MAX_ENTRIES_DEFAULT = 1500;
function startupBindingMapPreinstallLimit() {
  const raw = String(
    process.env.CCL_WASM_STARTUP_BINDING_MAP_PREINSTALL_MAX_ENTRIES ?? "",
  ).trim();
  if (!raw) {
    return {
      value: STARTUP_BINDING_MAP_PREINSTALL_MAX_ENTRIES_DEFAULT,
      source: "default",
    };
  }
  const parsed = Number(raw);
  if (Number.isInteger(parsed) && parsed > 0) {
    return {
      value: parsed >>> 0,
      source: "env",
    };
  }
  return {
    value: STARTUP_BINDING_MAP_PREINSTALL_MAX_ENTRIES_DEFAULT,
    source: "default-invalid-env",
  };
}

function planStartupBindingMapPreinstallConstPools({
  contract = BOOTSTRAP_L0_CONTRACT_V1,
  mapArtifact = null,
} = {}) {
  const contractRootEntryIndices = [];
  const contractRootSet = new Set();
  for (const requiredPool of Array.isArray(contract?.requiredConstPools) ? contract.requiredConstPools : []) {
    const entryIndex = Number(requiredPool?.entryIndex);
    if (!Number.isInteger(entryIndex) || entryIndex < 0) continue;
    const normalizedEntryIndex = entryIndex >>> 0;
    if (contractRootSet.has(normalizedEntryIndex)) continue;
    contractRootSet.add(normalizedEntryIndex);
    contractRootEntryIndices.push(normalizedEntryIndex);
  }
  contractRootEntryIndices.sort((a, b) => a - b);

  const artifactShadowEntryIndices = [];
  const artifactShadowEntrySet = new Set();
  const rawArtifactShadowEntryIndices = mapArtifact?.startup_shadow_table?.preinstall_const_pool_entries;
  for (const value of Array.isArray(rawArtifactShadowEntryIndices) ? rawArtifactShadowEntryIndices : []) {
    const entryIndex = Number(value);
    if (!Number.isInteger(entryIndex) || entryIndex < 0) continue;
    const normalizedEntryIndex = entryIndex >>> 0;
    if (artifactShadowEntrySet.has(normalizedEntryIndex)) continue;
    artifactShadowEntrySet.add(normalizedEntryIndex);
    artifactShadowEntryIndices.push(normalizedEntryIndex);
  }
  artifactShadowEntryIndices.sort((a, b) => a - b);

  const missingContractRootEntries = [];
  for (const entryIndex of contractRootEntryIndices) {
    if (!artifactShadowEntrySet.has(entryIndex)) {
      missingContractRootEntries.push(entryIndex);
    }
  }
  const preinstallLimit = startupBindingMapPreinstallLimit();
  const budget = {
    max_preinstall: preinstallLimit.value >>> 0,
    required_roots: contractRootEntryIndices.length >>> 0,
    required_anchors: 0,
    fixed_margin: 0,
    over_by: 0,
  };
  for (const entryIndex of artifactShadowEntryIndices) {
    if (!contractRootSet.has(entryIndex)) {
      budget.required_anchors = (budget.required_anchors + 1) >>> 0;
    }
  }
  const budgetFormulaBase = (budget.required_roots + budget.required_anchors) >>> 0;
  budget.fixed_margin = budget.max_preinstall > budgetFormulaBase
    ? ((budget.max_preinstall - budgetFormulaBase) >>> 0)
    : 0;
  budget.over_by = artifactShadowEntryIndices.length > budget.max_preinstall
    ? ((artifactShadowEntryIndices.length - budget.max_preinstall) >>> 0)
    : 0;

  let status = "ok";
  let reason = null;
  if (!(mapArtifact?.startup_shadow_table && typeof mapArtifact.startup_shadow_table === "object")) {
    status = "fail";
    reason = "startup-shadow-table-missing";
  } else if (artifactShadowEntryIndices.length === 0) {
    status = "fail";
    reason = "startup-shadow-table-empty-preinstall-entries";
  } else if (missingContractRootEntries.length > 0) {
    status = "fail";
    reason = "startup-shadow-table-missing-contract-root-entries";
  } else if (budget.over_by > 0) {
    status = "fail";
    reason = "preinstall-budget-exceeded";
  }

  const orderedEntryIndices = artifactShadowEntryIndices;
  return {
    entryIndices: orderedEntryIndices,
    summary: {
      schema_version: "startup_binding_map_preinstall_plan_v3",
      status,
      phase: "pre-fasload",
      contract_id: contract?.id ?? null,
      source: "artifact-startup-shadow-table",
      reason,
      budget,
      contract_required_const_pool_entries: contractRootEntryIndices.length >>> 0,
      contract_required_const_pool_entry_indices: contractRootEntryIndices,
      missing_contract_root_entries: missingContractRootEntries,
      closure_const_pool_binding_buckets: startupBindingMapConstPoolBindings.size >>> 0,
      startup_shadow_table_entries: artifactShadowEntryIndices.length >>> 0,
      startup_shadow_table_entry_count: Number.isInteger(mapArtifact?.startup_shadow_table?.preinstall_const_pool_entry_count)
        ? (mapArtifact.startup_shadow_table.preinstall_const_pool_entry_count >>> 0)
        : null,
      startup_shadow_table_binding_entry_count: Number.isInteger(mapArtifact?.startup_shadow_table?.binding_entry_count)
        ? (mapArtifact.startup_shadow_table.binding_entry_count >>> 0)
        : null,
      startup_shadow_table_entry_backed_binding_count: Number.isInteger(mapArtifact?.startup_shadow_table?.entry_backed_binding_count)
        ? (mapArtifact.startup_shadow_table.entry_backed_binding_count >>> 0)
        : null,
      startup_shadow_table_preinstall_max_entries: budget.max_preinstall,
      startup_shadow_table_preinstall_max_entries_source: preinstallLimit.source,
      startup_shadow_table_preinstall_entries_over_limit: budget.over_by,
      total_const_pool_entries: orderedEntryIndices.length >>> 0,
    },
  };
}

function applyStartupBindingMapDeferredBindingsForConstPoolEntry(entryIndexRaw, { reason = "const-pool-install" } = {}) {
  if (!kernelExports) return;
  const entryIndex = entryIndexRaw >>> 0;
  const bindings = startupBindingMapConstPoolBindings.get(entryIndex);
  if (!Array.isArray(bindings) || bindings.length === 0) return;

  const ex = kernelExports;
  const hasRequiredExports = (
    typeof ex.wasm_const_pool_ref === "function" &&
    typeof ex.wasm_probe_symbol_vcell === "function" &&
    typeof ex.wasm_probe_symbol_fcell === "function" &&
    typeof ex.wasm_probe_last_status === "function" &&
    typeof ex.wasm_debug_function_entry_index === "function" &&
    typeof ex.wasm_set_raw_symbol_cell_initializer === "function"
  );
  if (!hasRequiredExports) return;

  const OK_STATUS = 0;
  const nil = typeof ex.wasm_get_lisp_nil === "function"
    ? (ex.wasm_get_lisp_nil() >>> 0)
    : 0x4000001;
  const probeStatus = () => (ex.wasm_probe_last_status() >>> 0);
  let applied = 0;
  let skippedAlreadyBound = 0;
  let skippedNilRef = 0;
  let skippedNonSymbol = 0;
  let applyFailed = 0;

  for (const binding of bindings) {
    const applyKey = `${entryIndex}:${binding.definition_const_index >>> 0}:${binding.resolved_entry_index >>> 0}`;
    if (startupBindingMapDeferredApplied.has(applyKey)) {
      skippedAlreadyBound++;
      continue;
    }

    const rawSymbol = ex.wasm_const_pool_ref(entryIndex, binding.definition_const_index >>> 0) >>> 0;
    if (rawSymbol === 0 || rawSymbol === nil) {
      skippedNilRef++;
      continue;
    }

    ex.wasm_probe_symbol_vcell(rawSymbol >>> 0);
    if (probeStatus() !== OK_STATUS) {
      skippedNonSymbol++;
      continue;
    }

    const beforeFcell = ex.wasm_probe_symbol_fcell(rawSymbol >>> 0) >>> 0;
    const beforeFcellStatus = probeStatus();
    if (beforeFcellStatus === OK_STATUS) {
      const beforeEntry = ex.wasm_debug_function_entry_index(beforeFcell >>> 0) | 0;
      const desiredEntry = Number.isInteger(binding?.resolved_entry_index)
        ? (binding.resolved_entry_index >>> 0)
        : null;
      if (beforeEntry >= 0 && desiredEntry != null && (beforeEntry >>> 0) === desiredEntry) {
        startupBindingMapDeferredApplied.add(applyKey);
        skippedAlreadyBound++;
        continue;
      }
    }

    ex.wasm_set_raw_symbol_cell_initializer(
      rawSymbol >>> 0,
      WASM_SYMBOL_TARGET_CELL.FCELL,
      WASM_SYMBOL_CELL_INITIALIZER_KIND.ENTRY_FUNCTION,
      0,
      binding.resolved_entry_index >>> 0,
      0,
      0,
      0,
      0,
    );
    if (probeStatus() !== OK_STATUS) {
      applyFailed++;
      continue;
    }

    const afterFcell = ex.wasm_probe_symbol_fcell(rawSymbol >>> 0) >>> 0;
    if (probeStatus() !== OK_STATUS) {
      applyFailed++;
      continue;
    }
    const afterEntry = ex.wasm_debug_function_entry_index(afterFcell >>> 0) | 0;
    if (afterEntry < 0) {
      applyFailed++;
      continue;
    }

    startupBindingMapDeferredApplied.add(applyKey);
    applied++;
  }

  if (applied > 0 || applyFailed > 0) {
    console.log(`STARTUP_BINDING_MAP_APPLY_DEFERRED ${JSON.stringify({
      schema_version: "startup_binding_map_apply_deferred_v1",
      status: applyFailed > 0 ? "partial" : "ok",
      reason,
      const_pool_entry_index: entryIndex >>> 0,
      candidate_bindings: bindings.length >>> 0,
      applied_count: applied >>> 0,
      skipped_already_bound: skippedAlreadyBound >>> 0,
      skipped_nil_ref: skippedNilRef >>> 0,
      skipped_non_symbol: skippedNonSymbol >>> 0,
      apply_failed: applyFailed >>> 0,
    })}`);
  }
}

function installConstPoolOnDemand(entryIndexRaw) {
  if (!kernelExports || compiledModulesFd == null) return 0;
  const entryIndex = entryIndexRaw >>> 0;
  if (constPoolsInstalled.has(entryIndex)) return 1;

  const info = constPoolEntries.get(entryIndex);
  if (!info) return 0;
  const decodedBytes = decodeConstPoolForInfo(info);
  if (!decodedBytes) return 0;
  const shouldProbe = traceEnabled &&
    entryIndex === CONST_POOL_DIAG_ENTRY &&
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
    if (shouldProbe) {
      const readDebug = (fnName) => (typeof kernelExports[fnName] === "function"
        ? (kernelExports[fnName]() >>> 0)
        : null);
      const debugError = readDebug("wasm_debug_const_pool_error");
      const debugNameLen = readDebug("wasm_debug_const_pool_symbol_name_len");
      const debugPkgLen = readDebug("wasm_debug_const_pool_symbol_pkg_len");
      const debugPhase = readDebug("wasm_debug_const_pool_phase");
      const debugIndex = readDebug("wasm_debug_const_pool_index");
      const debugTag = readDebug("wasm_debug_const_pool_tag");
      const debugOffset = readDebug("wasm_debug_const_pool_offset");
      const pendingThrow = readDebug("wasm_pending_throw_raw");
      const bootPhase = typeof kernelExports.wasm_boot_get_phase === "function"
        ? (kernelExports.wasm_boot_get_phase() >>> 0)
        : null;
      const pendingThrowSubtag = pendingThrow != null && typeof kernelExports.wasm_debug_misc_subtag === "function"
        ? (kernelExports.wasm_debug_misc_subtag(pendingThrow >>> 0) | 0)
        : null;
      trace(
        `diag-const-pool entry=${entryIndex}` +
        ` install_rc=0x${rc.toString(16)}` +
        ` lisp_nil=${nilValue == null ? "n/a" : `0x${nilValue.toString(16)}`}` +
        ` debug_error=${debugError == null ? "n/a" : `${debugError}:${CONST_POOL_ERROR_NAMES.get(debugError) ?? "unknown"}`}` +
        ` debug_name_len=${debugNameLen == null ? "n/a" : debugNameLen}` +
        ` debug_pkg_len=${debugPkgLen == null ? "n/a" : debugPkgLen}` +
        ` debug_phase=${debugPhase == null ? "n/a" : debugPhase}` +
        ` debug_index=${debugIndex == null ? "n/a" : debugIndex}` +
        ` debug_tag=${debugTag == null ? "n/a" : debugTag}` +
        ` debug_offset=${debugOffset == null ? "n/a" : debugOffset}` +
        ` boot_phase=${bootPhase == null ? "n/a" : formatBootPhase(bootPhase)}` +
        ` pending_throw=${pendingThrow == null ? "n/a" : `0x${pendingThrow.toString(16)}`}` +
        ` pending_throw_subtag=${pendingThrowSubtag == null ? "n/a" : pendingThrowSubtag}` +
        ` install_ok=${installOk ? 1 : 0}`,
      );
      if (typeof kernelExports.wasm_const_pool_ref === "function") {
        const rows = [];
        for (let i = 0; i < 16; i++) {
          const obj = kernelExports.wasm_const_pool_ref(entryIndex >>> 0, i >>> 0) >>> 0;
          rows.push(`${i}:0x${obj.toString(16)}`);
        }
        trace(`diag-const-pool entry=${entryIndex} refs=${rows.join(" | ")}`);
      }
    }
    if (!installOk) return 0;

    constPoolsInstalled.add(entryIndex);
    applyStartupBindingMapDeferredBindingsForConstPoolEntry(entryIndex, { reason: "const-pool-install" });
    return 1;
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
const debugReadSpecrefFailure = (label) => {
  if (!traceEnabled || typeof subex.wasm_debug_specref_failure_stage !== "function") {
    return null;
  }
  try {
    const stage = subex.wasm_debug_specref_failure_stage() >>> 0;
    const stageName = SPECREF_FAILURE_STAGE_NAMES.get(stage) ?? "unknown";
    const read = (name) => (typeof subex[name] === "function" ? (subex[name]() >>> 0) : 0);
    const symbolRaw = read("wasm_debug_specref_failure_symbol_raw");
    const symbolFulltag = read("wasm_debug_specref_failure_symbol_fulltag");
    const symbolHeader = read("wasm_debug_specref_failure_symbol_header");
    const symbolSubtag = read("wasm_debug_specref_failure_symbol_subtag");
    trace(
      `debug-specref-failure label=${label}` +
      ` stage=${stage}:${stageName}` +
      ` tcr=0x${read("wasm_debug_specref_failure_tcr_raw").toString(16)}` +
      ` symbol=0x${symbolRaw.toString(16)}` +
      ` symbol_fulltag=${symbolFulltag}` +
      ` symbol_header=0x${symbolHeader.toString(16)}` +
      ` symbol_subtag=${symbolSubtag}` +
      ` binding_index=0x${read("wasm_debug_specref_failure_binding_index_raw").toString(16)}` +
      ` binding_index_tag=${read("wasm_debug_specref_failure_binding_index_tag")}` +
      ` limit=0x${read("wasm_debug_specref_failure_limit_raw").toString(16)}` +
      ` limit_tag=${read("wasm_debug_specref_failure_limit_tag")}` +
      ` tlb_pointer=0x${read("wasm_debug_specref_failure_tlb_pointer_raw").toString(16)}`,
    );

    const readKernel = (fnName) => (typeof ex[fnName] === "function" ? (ex[fnName]() >>> 0) : 0);
    const argZ = readKernel("wasm_get_arg_z");
    const argY = readKernel("wasm_get_arg_y");
    const nfn = readKernel("wasm_get_nfn");
    const nargs = readKernel("wasm_get_nargs");
    const nfnEntry = typeof ex.wasm_debug_function_entry_index === "function"
      ? (ex.wasm_debug_function_entry_index(nfn >>> 0) | 0)
      : -1;
    const symbolName = (obj) => {
      if (typeof ex.wasm_debug_copy_symbol_name !== "function") return null;
      const len = ex.wasm_debug_copy_symbol_name(obj >>> 0, 0, 0) >>> 0;
      if (len === 0) return null;
      const ptr = allocScratch(runtime.memory, len);
      const copied = ex.wasm_debug_copy_symbol_name(obj >>> 0, ptr >>> 0, len) >>> 0;
      if (copied === 0) return null;
      try {
        return decoder.decode(new Uint8Array(runtime.memory.buffer, ptr >>> 0, Math.min(len, copied)));
      } catch {
        return null;
      }
    };
    const ownerName = (fnObj) => {
      if (typeof ex.wasm_debug_find_symbol_by_fcell_raw !== "function") return null;
      const owner = ex.wasm_debug_find_symbol_by_fcell_raw(fnObj >>> 0) >>> 0;
      if (owner === 0 || owner === 0x4000001) return null;
      return symbolName(owner >>> 0);
    };
    const objSubtag = (obj) => (typeof ex.wasm_debug_misc_subtag === "function"
      ? (ex.wasm_debug_misc_subtag(obj >>> 0) | 0)
      : -1);
    const argZSymbol = symbolName(argZ) ?? null;
    const argYSymbol = symbolName(argY) ?? null;
    const nfnOwner = ownerName(nfn) ?? null;
    trace(
      `debug-specref-context label=${label}` +
      ` arg_z=0x${argZ.toString(16)} arg_z_subtag=${objSubtag(argZ)}` +
      ` arg_y=0x${argY.toString(16)} arg_y_subtag=${objSubtag(argY)}` +
      ` nfn=0x${nfn.toString(16)} nfn_subtag=${objSubtag(nfn)} nfn_entry=${nfnEntry}` +
      ` nargs_raw=0x${nargs.toString(16)}` +
      (argZSymbol ? ` arg_z_symbol=${JSON.stringify(argZSymbol)}` : "") +
      (argYSymbol ? ` arg_y_symbol=${JSON.stringify(argYSymbol)}` : "") +
      (nfnOwner ? ` nfn_owner=${JSON.stringify(nfnOwner)}` : ""),
    );

    if (typeof ex.wasm_debug_const_pool_entry === "function") {
      const constEntry = ex.wasm_debug_const_pool_entry() >>> 0;
      trace(
        `debug-specref-const-pool label=${label}` +
        ` entry=${constEntry}` +
        ` phase=${(typeof ex.wasm_debug_const_pool_phase === "function" ? (ex.wasm_debug_const_pool_phase() >>> 0) : 0)}` +
        ` index=${(typeof ex.wasm_debug_const_pool_index === "function" ? (ex.wasm_debug_const_pool_index() >>> 0) : 0)}` +
        ` tag=${(typeof ex.wasm_debug_const_pool_tag === "function" ? (ex.wasm_debug_const_pool_tag() >>> 0) : 0)}` +
        ` offset=${(typeof ex.wasm_debug_const_pool_offset === "function" ? (ex.wasm_debug_const_pool_offset() >>> 0) : 0)}`,
      );
      if (typeof ex.wasm_const_pool_ref === "function") {
        const rows = [];
        for (let i = 0; i < 6; i++) {
          const obj = ex.wasm_const_pool_ref(constEntry >>> 0, i >>> 0) >>> 0;
          const subtag = objSubtag(obj);
          const name = symbolName(obj) ?? ownerName(obj);
          rows.push(`${i}:0x${obj.toString(16)}:subtag=${subtag}${name ? `:${name}` : ""}`);
        }
        trace(`debug-specref-const-pool-sample label=${label} ${rows.join(" | ")}`);
      }
    }
    return {
      label,
      stage,
      stage_name: stageName,
      symbol_raw: symbolRaw >>> 0,
      symbol_fulltag: symbolFulltag >>> 0,
      symbol_subtag: symbolSubtag >>> 0,
      arg_z: argZ >>> 0,
      arg_y: argY >>> 0,
      nfn: nfn >>> 0,
      nfn_entry: nfnEntry,
      nargs_raw: nargs >>> 0,
      arg_z_symbol: argZSymbol,
      arg_y_symbol: argYSymbol,
      nfn_owner: nfnOwner,
    };
  } catch (err) {
    trace(`debug-specref-failure label=${label} error=${err?.message ?? err}`);
    return null;
  }
};
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

const debugReadSymbolState = (label, symbolReader) => {
  if (!traceEnabled || typeof symbolReader !== "function" || typeof ex.wasm_debug_symbol_vcell_raw !== "function") {
    return;
  }
  try {
    const sym = symbolReader() >>> 0;
    const vcell = ex.wasm_debug_symbol_vcell_raw(sym >>> 0) >>> 0;
    const fcell = typeof ex.wasm_debug_symbol_fcell_raw === "function"
      ? (ex.wasm_debug_symbol_fcell_raw(sym >>> 0) >>> 0)
      : 0;
    let symName = null;
    if (typeof ex.wasm_debug_copy_symbol_name === "function") {
      const len = ex.wasm_debug_copy_symbol_name(sym >>> 0, 0, 0) >>> 0;
      if (len > 0) {
        const ptr = allocScratch(runtime.memory, len);
        const copied = ex.wasm_debug_copy_symbol_name(sym >>> 0, ptr >>> 0, len) >>> 0;
        if (copied > 0) {
          symName = decoder.decode(new Uint8Array(runtime.memory.buffer, ptr >>> 0, Math.min(len, copied)));
        }
      }
    }
    trace(
      `debug-symbol-state label=${label}` +
      ` sym=0x${sym.toString(16)}` +
      ` vcell=0x${vcell.toString(16)}` +
      ` fcell=0x${fcell.toString(16)}` +
      (symName ? ` name=${JSON.stringify(symName)}` : ""),
    );
  } catch (err) {
    trace(`debug-symbol-state label=${label} error=${err?.message ?? err}`);
  }
};

const debugReadNamedCclSymbolState = (label, symbolName) => {
  if (!traceEnabled ||
      typeof ex.wasm_debug_find_symbol_ccl_raw !== "function" ||
      typeof ex.wasm_debug_symbol_vcell_raw !== "function") {
    return;
  }
  try {
    const nameBytes = new TextEncoder().encode(symbolName);
    const namePtr = allocScratch(runtime.memory, nameBytes.length);
    new Uint8Array(runtime.memory.buffer, namePtr >>> 0, nameBytes.length).set(nameBytes);
    const sym = ex.wasm_debug_find_symbol_ccl_raw(namePtr >>> 0, nameBytes.length >>> 0) >>> 0;
    const vcell = ex.wasm_debug_symbol_vcell_raw(sym >>> 0) >>> 0;
    const fcell = typeof ex.wasm_debug_symbol_fcell_raw === "function"
      ? (ex.wasm_debug_symbol_fcell_raw(sym >>> 0) >>> 0)
      : 0;
    const vcellEntry = typeof ex.wasm_debug_function_entry_index === "function"
      ? (ex.wasm_debug_function_entry_index(vcell >>> 0) | 0)
      : null;
    const fcellEntry = typeof ex.wasm_debug_function_entry_index === "function"
      ? (ex.wasm_debug_function_entry_index(fcell >>> 0) | 0)
      : null;
    const vcellCallAbi = (
      Number.isInteger(vcellEntry) &&
      vcellEntry >= 0 &&
      typeof ex.wasm_get_entry_call_abi === "function"
    )
      ? (ex.wasm_get_entry_call_abi(vcellEntry >>> 0) >>> 0)
      : null;
    const fcellCallAbi = (
      Number.isInteger(fcellEntry) &&
      fcellEntry >= 0 &&
      typeof ex.wasm_get_entry_call_abi === "function"
    )
      ? (ex.wasm_get_entry_call_abi(fcellEntry >>> 0) >>> 0)
      : null;
    let fcellOwner = null;
    if (typeof ex.wasm_debug_find_symbol_by_fcell_raw === "function" &&
        typeof ex.wasm_debug_copy_symbol_name === "function" &&
        fcell !== 0) {
      const owner = ex.wasm_debug_find_symbol_by_fcell_raw(fcell >>> 0) >>> 0;
      if (owner !== 0) {
        const ownerLen = ex.wasm_debug_copy_symbol_name(owner >>> 0, 0, 0) >>> 0;
        if (ownerLen > 0) {
          const ownerPtr = allocScratch(runtime.memory, ownerLen);
          const ownerCopied = ex.wasm_debug_copy_symbol_name(owner >>> 0, ownerPtr >>> 0, ownerLen) >>> 0;
          if (ownerCopied > 0) {
            fcellOwner = decoder.decode(
              new Uint8Array(runtime.memory.buffer, ownerPtr >>> 0, Math.min(ownerLen, ownerCopied)),
            );
          }
        }
      }
    }
    trace(
      `debug-symbol-state label=${label}` +
      ` sym=0x${sym.toString(16)}` +
      ` vcell=0x${vcell.toString(16)}` +
      ` fcell=0x${fcell.toString(16)}` +
      (vcellEntry == null ? "" : ` vcell_entry=${vcellEntry}`) +
      (fcellEntry == null ? "" : ` fcell_entry=${fcellEntry}`) +
      (vcellCallAbi == null ? "" : ` vcell_call_abi=${vcellCallAbi}`) +
      (fcellCallAbi == null ? "" : ` fcell_call_abi=${fcellCallAbi}`) +
      (fcellOwner ? ` fcell_owner=${JSON.stringify(fcellOwner)}` : "") +
      ` name=${JSON.stringify(symbolName)}`,
    );
  } catch (err) {
    trace(`debug-symbol-state label=${label} name=${JSON.stringify(symbolName)} error=${err?.message ?? err}`);
  }
};

const debugReadNamedAnySymbolState = (label, symbolName) => {
  if (!traceEnabled ||
      typeof ex.wasm_debug_find_symbol_any_raw !== "function" ||
      typeof ex.wasm_debug_symbol_vcell_raw !== "function") {
    return;
  }
  try {
    const nameBytes = new TextEncoder().encode(symbolName);
    const namePtr = allocScratch(runtime.memory, nameBytes.length);
    new Uint8Array(runtime.memory.buffer, namePtr >>> 0, nameBytes.length).set(nameBytes);
    const sym = ex.wasm_debug_find_symbol_any_raw(namePtr >>> 0, nameBytes.length >>> 0) >>> 0;
    const vcell = ex.wasm_debug_symbol_vcell_raw(sym >>> 0) >>> 0;
    const fcell = typeof ex.wasm_debug_symbol_fcell_raw === "function"
      ? (ex.wasm_debug_symbol_fcell_raw(sym >>> 0) >>> 0)
      : 0;
    trace(
      `debug-symbol-state label=${label}` +
      ` sym=0x${sym.toString(16)}` +
      ` vcell=0x${vcell.toString(16)}` +
      ` fcell=0x${fcell.toString(16)}` +
      ` name=${JSON.stringify(symbolName)}`,
    );
  } catch (err) {
    trace(`debug-symbol-state label=${label} name=${JSON.stringify(symbolName)} error=${err?.message ?? err}`);
  }
};

const debugReadNamedCclListState = (label, symbolName) => {
  if (!traceEnabled ||
      typeof ex.wasm_debug_find_symbol_ccl_raw !== "function" ||
      typeof ex.wasm_debug_symbol_vcell_raw !== "function" ||
      typeof ex.wasm_debug_list_length_bounded !== "function") {
    return;
  }
  try {
    const nameBytes = new TextEncoder().encode(symbolName);
    const namePtr = allocScratch(runtime.memory, nameBytes.length);
    new Uint8Array(runtime.memory.buffer, namePtr >>> 0, nameBytes.length).set(nameBytes);
    const sym = ex.wasm_debug_find_symbol_ccl_raw(namePtr >>> 0, nameBytes.length >>> 0) >>> 0;
    const vcell = ex.wasm_debug_symbol_vcell_raw(sym >>> 0) >>> 0;
    const listLen = ex.wasm_debug_list_length_bounded(vcell >>> 0, 65536) | 0;
    trace(
      `debug-list-state label=${label}` +
      ` sym=0x${sym.toString(16)}` +
      ` vcell=0x${vcell.toString(16)}` +
      ` list_len=${listLen}` +
      ` name=${JSON.stringify(symbolName)}`,
    );
  } catch (err) {
    trace(`debug-list-state label=${label} name=${JSON.stringify(symbolName)} error=${err?.message ?? err}`);
  }
};

const debugDumpNamedCclFunctionListEntries = (label, symbolName, maxItems = 12) => {
  if (!traceEnabled ||
      typeof ex.wasm_debug_find_symbol_ccl_raw !== "function" ||
      typeof ex.wasm_debug_symbol_vcell_raw !== "function" ||
      typeof ex.wasm_debug_cons_car_raw !== "function" ||
      typeof ex.wasm_debug_cons_cdr_raw !== "function" ||
      typeof ex.wasm_debug_list_length_bounded !== "function" ||
      typeof ex.wasm_debug_function_entry_index !== "function") {
    return;
  }
  try {
    const lispNil = typeof ex.wasm_get_lisp_nil === "function"
      ? (ex.wasm_get_lisp_nil() >>> 0)
      : 0x4000001;
    const nameBytes = new TextEncoder().encode(symbolName);
    const namePtr = allocScratch(runtime.memory, nameBytes.length);
    new Uint8Array(runtime.memory.buffer, namePtr >>> 0, nameBytes.length).set(nameBytes);
    const sym = ex.wasm_debug_find_symbol_ccl_raw(namePtr >>> 0, nameBytes.length >>> 0) >>> 0;
    let cursor = ex.wasm_debug_symbol_vcell_raw(sym >>> 0) >>> 0;
    const listLen = ex.wasm_debug_list_length_bounded(cursor >>> 0, 65536) | 0;
    const rows = [];
    for (let i = 0; i < maxItems; i++) {
      const car = ex.wasm_debug_cons_car_raw(cursor >>> 0) >>> 0;
      const cdr = ex.wasm_debug_cons_cdr_raw(cursor >>> 0) >>> 0;
      if (car === lispNil && cdr === lispNil) break;
      const entry = ex.wasm_debug_function_entry_index(car >>> 0) | 0;
      let ownerName = null;
      if (typeof ex.wasm_debug_find_symbol_by_fcell_raw === "function" &&
          typeof ex.wasm_debug_copy_symbol_name === "function") {
        const ownerSym = ex.wasm_debug_find_symbol_by_fcell_raw(car >>> 0) >>> 0;
        if (ownerSym !== 0 && ownerSym !== lispNil) {
          const nameLen = ex.wasm_debug_copy_symbol_name(ownerSym >>> 0, 0, 0) >>> 0;
          if (nameLen > 0) {
            const namePtr = allocScratch(runtime.memory, nameLen);
            const copied = ex.wasm_debug_copy_symbol_name(ownerSym >>> 0, namePtr >>> 0, nameLen) >>> 0;
            if (copied > 0) {
              ownerName = decoder.decode(new Uint8Array(runtime.memory.buffer, namePtr >>> 0, Math.min(nameLen, copied)));
            }
          }
        }
      }
      rows.push(`${i}:${entry}:${`0x${car.toString(16)}`}${ownerName ? `:${ownerName}` : ""}`);
      cursor = cdr >>> 0;
      if (cursor === lispNil) break;
    }
    trace(
      `debug-list-entries label=${label}` +
      ` name=${JSON.stringify(symbolName)}` +
      ` list_len=${listLen}` +
      ` entries=[${rows.join(",")}]`,
    );
  } catch (err) {
    trace(`debug-list-entries label=${label} name=${JSON.stringify(symbolName)} error=${err?.message ?? err}`);
  }
};

const debugReadFasloadBoundarySymbols = (label) => {
  debugReadSymbolState(`${label}.fasl-api`, ex.wasm_debug_find_symbol_fasl_api_raw);
  debugReadSymbolState(`${label}.fasl-dispatch-table`, ex.wasm_debug_find_symbol_fasl_dispatch_table_raw);
  debugReadNamedCclSymbolState(`${label}.pct-fasload-verbose`, "*%FASLOAD-VERBOSE*");
  debugReadNamedCclSymbolState(`${label}.pct-fasload`, "*FASLOAD*");
  debugReadNamedCclSymbolState(`${label}.fn-fasload`, "%FASLOAD");
  debugReadNamedCclSymbolState(`${label}.fn-fasl-open`, "%FASL-OPEN");
  debugReadNamedCclSymbolState(`${label}.fn-simple-fasl-open`, "%SIMPLE-FASL-OPEN");
  debugReadNamedCclSymbolState(`${label}.fn-cons-population`, "%CONS-POPULATION");
  debugReadNamedCclSymbolState(`${label}.fn-make-read-write-lock`, "MAKE-READ-WRITE-LOCK");
  debugReadNamedCclSymbolState(`${label}.fn-map-areas`, "%MAP-AREAS");
  debugReadNamedCclSymbolState(`${label}.fn-set-binding-index`, "%SET-BINDING-INDEX");
  debugReadNamedCclSymbolState(`${label}.fn-current-tcr`, "%CURRENT-TCR");
  debugReadNamedCclSymbolState(`${label}.fn-set-tcr-toplevel-function`, "%SET-TCR-TOPLEVEL-FUNCTION");
  debugReadNamedCclSymbolState(`${label}.fn-make-vector-output-stream`, "MAKE-VECTOR-OUTPUT-STREAM");
  debugReadNamedCclSymbolState(`${label}.fn-percent-make-vector-output-stream`, "%MAKE-VECTOR-OUTPUT-STREAM");
  debugReadNamedCclSymbolState(`${label}.fn-make-uarray-1`, "MAKE-UARRAY-1");
  debugReadNamedCclSymbolState(`${label}.fn-make-array`, "MAKE-ARRAY");
  debugReadNamedCclSymbolState(`${label}.fn-class-has-forward-referenced-superclass-p`, "CLASS-HAS-A-FORWARD-REFERENCED-SUPERCLASS-P");
  debugReadNamedAnySymbolState(`${label}.sym-class-has-forward-referenced-superclass-p`, "CLASS-HAS-A-FORWARD-REFERENCED-SUPERCLASS-P");
  debugReadNamedCclSymbolState(`${label}.pct-toplevel-function`, "%TOPLEVEL-FUNCTION%");
  debugReadNamedCclSymbolState(`${label}.sym-toplevel`, "TOPLEVEL");
  debugReadNamedAnySymbolState(`${label}.sym-stream-pathname`, "STREAM-PATHNAME");
  debugReadNamedCclSymbolState(`${label}.sym-percent-std-device-component`, "%STD-DEVICE-COMPONENT");
  debugReadNamedAnySymbolState(`${label}.sym-keyword-package`, "*KEYWORD-PACKAGE*");
  debugReadNamedAnySymbolState(`${label}.sym-default`, "DEFAULT");
  debugReadNamedAnySymbolState(`${label}.sym-keyword`, "KEYWORD");
  debugReadSymbolState(`${label}.sym-intern-pkgtable`, ex.wasm_debug_find_symbol_intern_pkgtable_raw);
  debugReadSymbolState(`${label}.sym-intern-scan`, ex.wasm_debug_find_symbol_intern_scan_raw);
  debugReadNamedAnySymbolState(`${label}.sym-intern-any`, "INTERN");
  debugReadNamedCclSymbolState(`${label}.wasm-startup-step`, "*WASM-STARTUP-STEP*");
  debugReadNamedCclSymbolState(`${label}.xload-startup-file`, "*XLOAD-STARTUP-FILE*");
  debugReadNamedCclListState(`${label}.xload-cold-load-functions`, "*XLOAD-COLD-LOAD-FUNCTIONS*");
  debugReadNamedCclListState(`${label}.xload-cold-load-documentation`, "*XLOAD-COLD-LOAD-DOCUMENTATION*");
  debugDumpNamedCclFunctionListEntries(`${label}.xload-cold-load-functions`, "*XLOAD-COLD-LOAD-FUNCTIONS*");
};

const debugReadToplfuncState = (label) => {
  if (!traceEnabled || typeof ex.wasm_debug_get_nrs_toplfunc_raw !== "function") {
    return;
  }
  try {
    const obj = ex.wasm_debug_get_nrs_toplfunc_raw() >>> 0;
    const entry = typeof ex.wasm_debug_function_entry_index === "function"
      ? (ex.wasm_debug_function_entry_index(obj >>> 0) | 0)
      : null;
    let ownerName = null;
    if (typeof ex.wasm_debug_find_symbol_by_fcell_raw === "function" &&
        typeof ex.wasm_debug_copy_symbol_name === "function") {
      const ownerSym = ex.wasm_debug_find_symbol_by_fcell_raw(obj >>> 0) >>> 0;
      if (ownerSym !== 0 && ownerSym !== 0x4000001) {
        const len = ex.wasm_debug_copy_symbol_name(ownerSym >>> 0, 0, 0) >>> 0;
        if (len > 0) {
          const ptr = allocScratch(runtime.memory, len);
          const copied = ex.wasm_debug_copy_symbol_name(ownerSym >>> 0, ptr >>> 0, len) >>> 0;
          if (copied > 0) {
            ownerName = decoder.decode(new Uint8Array(runtime.memory.buffer, ptr >>> 0, Math.min(len, copied)));
          }
        }
      }
    }
    trace(
      `debug-toplfunc label=${label}` +
      ` obj=0x${obj.toString(16)}` +
      (entry == null ? "" : ` entry=${entry}`) +
      (ownerName ? ` owner_symbol=${JSON.stringify(ownerName)}` : ""),
    );
  } catch (err) {
    trace(`debug-toplfunc label=${label} error=${err?.message ?? err}`);
  }
};

const debugReadLastToplevelThrow = (label) => {
  if (!traceEnabled || typeof ex.wasm_debug_get_last_toplevel_throw !== "function") {
    return;
  }
  try {
    const thrown = ex.wasm_debug_get_last_toplevel_throw() >>> 0;
    const argZ = typeof ex.wasm_debug_get_last_toplevel_arg_z === "function"
      ? (ex.wasm_debug_get_last_toplevel_arg_z() >>> 0)
      : 0;
    const argY = typeof ex.wasm_debug_get_last_toplevel_arg_y === "function"
      ? (ex.wasm_debug_get_last_toplevel_arg_y() >>> 0)
      : 0;
    const nfn = typeof ex.wasm_debug_get_last_toplevel_nfn === "function"
      ? (ex.wasm_debug_get_last_toplevel_nfn() >>> 0)
      : 0;
    const nargs = typeof ex.wasm_debug_get_last_toplevel_nargs === "function"
      ? (ex.wasm_debug_get_last_toplevel_nargs() >>> 0)
      : 0;
    const topfn = typeof ex.wasm_debug_get_last_toplevel_topfn === "function"
      ? (ex.wasm_debug_get_last_toplevel_topfn() >>> 0)
      : 0;
    const topfnEntry = typeof ex.wasm_debug_function_entry_index === "function"
      ? (ex.wasm_debug_function_entry_index(topfn >>> 0) | 0)
      : null;
    const resolveOwnerName = (obj) => {
      if (typeof ex.wasm_debug_find_symbol_by_fcell_raw !== "function" ||
          typeof ex.wasm_debug_copy_symbol_name !== "function") {
        return null;
      }
      const ownerSym = ex.wasm_debug_find_symbol_by_fcell_raw(obj >>> 0) >>> 0;
      if (ownerSym === 0 || ownerSym === 0x4000001) return null;
      const len = ex.wasm_debug_copy_symbol_name(ownerSym >>> 0, 0, 0) >>> 0;
      if (len === 0) return null;
      const ptr = allocScratch(runtime.memory, len);
      const copied = ex.wasm_debug_copy_symbol_name(ownerSym >>> 0, ptr >>> 0, len) >>> 0;
      if (copied === 0) return null;
      return decoder.decode(new Uint8Array(runtime.memory.buffer, ptr >>> 0, Math.min(len, copied)));
    };
    const topfnOwner = resolveOwnerName(topfn >>> 0);
    const nfnOwner = resolveOwnerName(nfn >>> 0);
    trace(
      `debug-last-toplevel-throw label=${label}` +
      ` throw=${thrown}` +
      ` topfn=0x${topfn.toString(16)}` +
      (topfnEntry == null ? "" : ` topfn_entry=${topfnEntry}`) +
      (topfnOwner ? ` topfn_owner=${JSON.stringify(topfnOwner)}` : "") +
      ` arg_z=0x${argZ.toString(16)}` +
      ` arg_y=0x${argY.toString(16)}` +
      ` nfn=0x${nfn.toString(16)}` +
      (nfnOwner ? ` nfn_owner=${JSON.stringify(nfnOwner)}` : "") +
      ` nargs=0x${nargs.toString(16)}`,
    );
  } catch (err) {
    trace(`debug-last-toplevel-throw label=${label} error=${err?.message ?? err}`);
  }
};

debugReadFasloadBoundarySymbols("post-boot");
debugReadToplfuncState("post-boot");

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
  debugReadToplfuncState("post-start-lisp-before-module-install");
  debugReadLastToplevelThrow("post-start-lisp-before-module-install");
  debugReadFasloadBoundarySymbols("post-start-lisp-before-module-install");
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
debugReadFasloadBoundarySymbols("post-bundle");
debugReadToplfuncState("post-bundle");
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
debugReadFasloadBoundarySymbols("post-registry");
debugReadToplfuncState("post-registry");
runPreToplevelFunctionDesignatorGateOrFail();

if (typeof kernel.instance.exports.wasm_set_subprims_ready === "function") {
  kernel.instance.exports.wasm_set_subprims_ready(1);
}
const diagRunToplevelEarly = process.env.CCL_WASM_DIAG_RUN_TOPLEVEL_EARLY === "1";
const diagRunToplevelEarlyOnly = process.env.CCL_WASM_DIAG_RUN_TOPLEVEL_EARLY_ONLY === "1";
if (diagRunToplevelEarly) {
  if (typeof ex.wasm_run_toplevel !== "function") {
    fail("kernel missing wasm_run_toplevel for CCL_WASM_DIAG_RUN_TOPLEVEL_EARLY");
  }
  const pendingBefore = typeof ex.wasm_pending_throw_p === "function"
    ? (ex.wasm_pending_throw_p() >>> 0)
    : null;
  debugReadToplfuncState("pre-early-toplevel");
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
  debugReadToplfuncState("post-early-toplevel");
  debugReadLastToplevelThrow("post-early-toplevel");
  debugReadFasloadBoundarySymbols("post-early-toplevel");
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
  debugReadToplfuncState("post-pre-fasload-set-toplfunc");
  debugReadFasloadBoundarySymbols("post-pre-fasload-set-toplfunc");

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
    debugReadToplfuncState("post-pre-fasload-toplevel-run");
    debugReadFasloadBoundarySymbols("post-pre-fasload-toplevel-run");
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
  debugReadToplfuncState("post-start-lisp-once");
  debugReadLastToplevelThrow("post-start-lisp-once");
  debugReadFasloadBoundarySymbols("post-start-lisp-once");
  debugReadSpecrefFailure("post-start-lisp-once");
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

function buildStartupSymbolResolutionArtifact({
  scopeArtifact,
  resolverSource,
  contract = BOOTSTRAP_L0_CONTRACT_V1,
} = {}) {
  const startedAtMs = Date.now();
  const counters = createStartupSymbolResolutionCounters();
  const records = [];
  const symbols = Array.isArray(scopeArtifact?.symbols) ? scopeArtifact.symbols : [];
  const symbolResolverSource = "hybrid";
  const scopeHash = (
    scopeArtifact &&
    typeof scopeArtifact === "object" &&
    !Array.isArray(scopeArtifact)
  )
    ? startupSymbolScopeIdentityHash(scopeArtifact)
    : null;
  const hasResolverExports = (
    typeof ex.wasm_get_lisp_nil === "function" &&
    typeof ex.wasm_probe_symbol === "function" &&
    typeof ex.wasm_probe_symbol_fcell === "function" &&
    typeof ex.wasm_probe_symbol_vcell === "function" &&
    typeof ex.wasm_probe_last_status === "function" &&
    typeof ex.wasm_debug_function_entry_index === "function"
  );
  const requiredCallableKeys = new Set(
    (Array.isArray(contract?.requiredCallables) ? contract.requiredCallables : [])
      .map((entry) => startupSymbolBindingKey(entry?.packageName, entry?.symbolName))
      .filter((key) => typeof key === "string" && key.length > 0),
  );
  const requiredSpecialKeys = new Set(
    (Array.isArray(contract?.requiredSpecialVariables) ? contract.requiredSpecialVariables : [])
      .map((entry) => startupSymbolBindingKey(entry?.packageName, entry?.symbolName))
      .filter((key) => typeof key === "string" && key.length > 0),
  );

  if (!hasResolverExports) {
    return {
      artifact: {
        schema_version: STARTUP_SYMBOL_RESOLUTION_SCHEMA_V1,
        generator_version: "startup_symbol_resolution_generator_v1",
        resolver_source: resolverSource ?? null,
        inputs_hash: scopeHash,
        symbols: records,
        counts: counters,
        duration_ms: (Date.now() - startedAtMs) | 0,
      },
      summary: {
        schema_version: STARTUP_SYMBOL_RESOLUTION_SCHEMA_V1,
        status: "skip",
        reason: "resolver-exports-missing",
        resolver_source: resolverSource ?? null,
        inputs_hash: scopeHash,
        counts: counters,
        duration_ms: (Date.now() - startedAtMs) | 0,
      },
    };
  }

  const nil = ex.wasm_get_lisp_nil() >>> 0;
  const probeStatus = () => (ex.wasm_probe_last_status() >>> 0);
  const utf8 = new TextEncoder();
  const scratchUtf8 = (text) => {
    const bytes = utf8.encode(String(text ?? ""));
    if (bytes.length === 0) return { ptr: 0, len: 0 };
    const ptr = copyBytesToScratch(runtime.memory, bytes);
    return { ptr, len: bytes.length >>> 0 };
  };
  const toHex = (value) => `0x${(value >>> 0).toString(16)}`;

  for (const symbolRecord of symbols) {
    counters.total++;
    const packageName = String(symbolRecord?.package_name ?? "").trim();
    const symbolName = String(symbolRecord?.symbol_name ?? "").trim();
    const symbolKey = String(symbolRecord?.key ?? "").trim() || (
      packageName && symbolName
        ? `${packageName.toUpperCase()}::${symbolName.toUpperCase()}`
        : null
    );
    const requiredClass = startupSymbolRequiredClass({
      symbolRecord,
      packageName,
      symbolName,
      requiredCallableKeys,
      requiredSpecialKeys,
    });

    if (!packageName || !symbolName) {
      counters.invalid_input++;
      records.push({
        key: symbolKey,
        package_name: packageName || null,
        symbol_name: symbolName || null,
        status: STARTUP_SYMBOL_RESOLUTION_STATUS.INVALID_INPUT,
        resolver_source: symbolResolverSource,
        required_class: requiredClass,
        reason: packageName ? "empty-symbol-name" : "empty-package-name",
        symbol_raw: null,
        probe_status: null,
        probe_status_name: null,
        fcell_raw: null,
        fentry: null,
        vcell_raw: null,
        vcell_bound: false,
      });
      continue;
    }

    const symbolNameMem = scratchUtf8(symbolName);
    const packageNameMem = scratchUtf8(packageName);
    const symbolRaw = ex.wasm_probe_symbol(
      symbolNameMem.ptr >>> 0,
      symbolNameMem.len >>> 0,
      packageNameMem.ptr >>> 0,
      packageNameMem.len >>> 0,
    ) >>> 0;
    const symbolStatus = probeStatus();

    if (symbolStatus !== L0_PROBE_STATUS.OK) {
      const unresolvedProbe = (
        symbolStatus === L0_PROBE_STATUS.PACKAGE_MISSING ||
        symbolStatus === L0_PROBE_STATUS.SYMBOL_MISSING
      );
      const status = unresolvedProbe
        ? STARTUP_SYMBOL_RESOLUTION_STATUS.UNRESOLVED
        : STARTUP_SYMBOL_RESOLUTION_STATUS.PROBE_ERROR;
      if (unresolvedProbe) {
        counters.unresolved++;
        incrementStartupSymbolResolutionUnresolvedCounters(counters, requiredClass);
      }
      else counters.probe_error++;
      records.push({
        key: symbolKey,
        package_name: packageName,
        symbol_name: symbolName,
        status,
        resolver_source: symbolResolverSource,
        required_class: requiredClass,
        reason: startupSymbolResolutionReasonForProbeStatus(symbolStatus),
        symbol_raw: toHex(symbolRaw),
        probe_status: symbolStatus,
        probe_status_name: l0ProbeStatusName(symbolStatus),
        fcell_raw: null,
        fentry: null,
        vcell_raw: null,
        vcell_bound: false,
      });
      continue;
    }

    if (symbolRaw === 0 || symbolRaw === nil) {
      counters.unresolved++;
      incrementStartupSymbolResolutionUnresolvedCounters(counters, requiredClass);
      records.push({
        key: symbolKey,
        package_name: packageName,
        symbol_name: symbolName,
        status: STARTUP_SYMBOL_RESOLUTION_STATUS.UNRESOLVED,
        resolver_source: symbolResolverSource,
        required_class: requiredClass,
        reason: "symbol-missing",
        symbol_raw: toHex(symbolRaw),
        probe_status: symbolStatus,
        probe_status_name: l0ProbeStatusName(symbolStatus),
        fcell_raw: null,
        fentry: null,
        vcell_raw: null,
        vcell_bound: false,
      });
      continue;
    }

    const fcellRaw = ex.wasm_probe_symbol_fcell(symbolRaw >>> 0) >>> 0;
    const fcellStatus = probeStatus();
    const fentry = fcellStatus === L0_PROBE_STATUS.OK
      ? (ex.wasm_debug_function_entry_index(fcellRaw >>> 0) | 0)
      : -1;
    const vcellRaw = ex.wasm_probe_symbol_vcell(symbolRaw >>> 0) >>> 0;
    const vcellStatus = probeStatus();
    const vcellBound = (
      vcellStatus === L0_PROBE_STATUS.OK &&
      vcellRaw !== 0 &&
      vcellRaw !== nil
    );
    counters.resolved++;
    if (fentry >= 0) {
      counters.function_capable++;
    }
    if (vcellBound) {
      counters.vcell_bound++;
    }
    records.push({
      key: symbolKey,
      package_name: packageName,
      symbol_name: symbolName,
      status: STARTUP_SYMBOL_RESOLUTION_STATUS.RESOLVED,
      resolver_source: symbolResolverSource,
      required_class: requiredClass,
      reason: null,
      symbol_raw: toHex(symbolRaw),
      probe_status: symbolStatus,
      probe_status_name: l0ProbeStatusName(symbolStatus),
      fcell_raw: fcellStatus === L0_PROBE_STATUS.OK ? toHex(fcellRaw) : null,
      fentry: fentry >= 0 ? (fentry >>> 0) : null,
      vcell_raw: vcellStatus === L0_PROBE_STATUS.OK ? toHex(vcellRaw) : null,
      vcell_bound: vcellBound,
    });
  }

  const artifact = {
    schema_version: STARTUP_SYMBOL_RESOLUTION_SCHEMA_V1,
    generator_version: "startup_symbol_resolution_generator_v1",
    resolver_source: resolverSource ?? null,
    inputs_hash: scopeHash,
    symbols: records,
    counts: counters,
    duration_ms: (Date.now() - startedAtMs) | 0,
  };
  return {
    artifact,
    summary: {
      schema_version: artifact.schema_version,
      status: "ok",
      resolver_source: artifact.resolver_source,
      inputs_hash: artifact.inputs_hash,
      counts: artifact.counts,
      duration_ms: artifact.duration_ms,
    },
  };
}

function buildStartupBindingMapBuildSummary({
  mapArtifact,
  mapSource,
  contract = BOOTSTRAP_L0_CONTRACT_V1,
} = {}) {
  const counts = summarizeStartupBindingMapArtifact(mapArtifact);
  const constantCoverage =
    mapArtifact?.coverage?.required_special_variable_bindings ?? null;
  return {
    schema_version: "startup_binding_map_build_v1",
    status: "ok",
    phase: "pre-fasload",
    source: mapSource ?? null,
    map_schema_version: mapArtifact?.schema_version ?? null,
    contract_id: contract?.id ?? null,
    counts: {
      total_entries: counts.total_entries,
      literal_entries: counts.literal_entries,
      deferred_entries: counts.deferred_entries,
      unsupported_entries: counts.unsupported_entries,
      entry_backed_entries: counts.entry_backed_entries,
      vcell_entries: counts.vcell_entries ?? null,
      fcell_entries: counts.fcell_entries ?? null,
      special_variable_entries: counts.special_variable_entries ?? null,
      function_entries: counts.function_entries ?? null,
    },
    constants: constantCoverage,
    startup_shadow_table: mapArtifact?.startup_shadow_table ?? null,
    coverage: mapArtifact?.coverage ?? null,
  };
}

function augmentStartupBindingMapArtifactWithContractConstPoolFunctions({
  mapArtifact,
  contract = BOOTSTRAP_L0_CONTRACT_V1,
  resolver = null,
} = {}) {
  const resolveFunctionDesignator = ({ packageName, symbolName, name } = {}) => {
    const resolvedSymbolName = String(symbolName ?? name ?? "").trim();
    let resolverResult = null;
    if (resolver && typeof resolver.resolveFunctionDesignator === "function") {
      resolverResult = resolver.resolveFunctionDesignator({
        name: resolvedSymbolName,
        packageName,
      });
    } else if (typeof resolver === "function") {
      resolverResult = resolver({
        name: resolvedSymbolName,
        symbolName: resolvedSymbolName,
        packageName,
      });
    } else {
      return {
        ok: false,
        reason: "resolver-unavailable",
        source: null,
        key: null,
        alternatives: [],
      };
    }
    if (resolverResult?.ok) {
      return {
        ok: true,
        entryIndex: resolverResult.entryIndex >>> 0,
        source: resolverResult.source ?? null,
        key: resolverResult.key ?? null,
      };
    }
    if (resolverResult?.reason === "ambiguous") {
      return {
        ok: false,
        reason: "ambiguous",
        source: resolverResult.source ?? null,
        key: resolverResult.key ?? null,
        alternatives: Array.isArray(resolverResult.alternatives)
          ? resolverResult.alternatives.slice()
          : [],
      };
    }
    return {
      ok: false,
      reason: resolverResult?.reason ?? "missing",
      source: resolverResult?.source ?? null,
      key: resolverResult?.key ?? null,
      alternatives: Array.isArray(resolverResult?.alternatives)
        ? resolverResult.alternatives.slice()
        : [],
    };
  };
  return augmentStartupBindingMapArtifactWithContractConstPoolFunctionsFromBuilder({
    mapArtifact,
    contract,
    resolveFunctionDesignator,
    functions: Array.isArray(compiledModulesBundle?.functions) ? compiledModulesBundle.functions : [],
    getConstPoolBytesForEntry: (entryIndexRaw) => {
      const entryIndex = entryIndexRaw >>> 0;
      const info = constPoolEntries.get(entryIndex);
      if (!info) return null;
      return decodeConstPoolForInfo(info);
    },
  });
}

function applyStartupBindingMapOrFail({
  mapArtifact,
  mapSource,
  contract = BOOTSTRAP_L0_CONTRACT_V1,
} = {}) {
  const entries = Array.isArray(mapArtifact?.entries) ? mapArtifact.entries : [];
  const counts = summarizeStartupBindingMapArtifact(mapArtifact);
  const failures = [];

  const requiredExports = [
    "wasm_get_lisp_nil",
    "wasm_probe_symbol",
    "wasm_probe_symbol_fcell",
    "wasm_probe_symbol_vcell",
    "wasm_probe_last_status",
    "wasm_debug_function_entry_index",
  ];
  for (const name of requiredExports) {
    if (typeof ex[name] !== "function") {
      fail(`kernel missing ${name} for startup binding map application`);
    }
  }

  const nil = ex.wasm_get_lisp_nil() >>> 0;
  const probeStatus = () => (ex.wasm_probe_last_status() >>> 0);
  const utf8 = new TextEncoder();
  const scratchUtf8 = (text) => {
    const bytes = utf8.encode(String(text ?? ""));
    if (bytes.length === 0) return { ptr: 0, len: 0 };
    const ptr = copyBytesToScratch(runtime.memory, bytes);
    return { ptr, len: bytes.length >>> 0 };
  };
  const toHex = (value) => `0x${(value >>> 0).toString(16)}`;
  const isNilLike = (value) => {
    const raw = value >>> 0;
    return raw === 0 || raw === nil;
  };
  const resolveRequiredCallableEntryFromBootstrapResolver = (packageName, symbolName) => {
    const runtimeProbeFallback = () => {
      const requiredProbeExports = (
        typeof ex.wasm_probe_symbol === "function" &&
        typeof ex.wasm_probe_symbol_fcell === "function" &&
        typeof ex.wasm_probe_last_status === "function" &&
        typeof ex.wasm_debug_function_entry_index === "function"
      );
      if (!requiredProbeExports) {
        return {
          ok: false,
          reason: "runtime-probe-exports-missing",
          source: null,
          key: null,
        };
      }
      const nameBytes = utf8.encode(String(symbolName ?? ""));
      const pkgBytes = utf8.encode(String(packageName ?? ""));
      const namePtr = nameBytes.length > 0 ? copyBytesToScratch(runtime.memory, nameBytes) : 0;
      const pkgPtr = pkgBytes.length > 0 ? copyBytesToScratch(runtime.memory, pkgBytes) : 0;
      const symbolRaw = ex.wasm_probe_symbol(
        namePtr >>> 0,
        nameBytes.length >>> 0,
        pkgPtr >>> 0,
        pkgBytes.length >>> 0,
      ) >>> 0;
      const symbolStatus = probeStatus();
      if (symbolStatus !== L0_PROBE_STATUS.OK || symbolRaw === 0 || symbolRaw === nil) {
        return {
          ok: false,
          reason: "runtime-symbol-unresolved",
          source: null,
          key: null,
          symbol_status: symbolStatus,
        };
      }
      const fcellRaw = ex.wasm_probe_symbol_fcell(symbolRaw >>> 0) >>> 0;
      const fcellStatus = probeStatus();
      if (fcellStatus !== L0_PROBE_STATUS.OK || fcellRaw === 0 || fcellRaw === nil) {
        return {
          ok: false,
          reason: "runtime-fcell-unresolved",
          source: null,
          key: null,
          symbol_status: symbolStatus,
          fcell_status: fcellStatus,
        };
      }
      const entryIndex = ex.wasm_debug_function_entry_index(fcellRaw >>> 0) | 0;
      if (entryIndex < 0) {
        return {
          ok: false,
          reason: "runtime-fcell-non-function",
          source: null,
          key: null,
          symbol_status: symbolStatus,
          fcell_status: fcellStatus,
        };
      }
      return {
        ok: true,
        entry_index: entryIndex >>> 0,
        source: "runtime-fcell-probe",
        key: "runtime-symbol-fcell",
      };
    };

    if (!bootstrapFunctionResolver || typeof bootstrapFunctionResolver.resolveFunctionDesignator !== "function") {
      const fallback = runtimeProbeFallback();
      if (fallback.ok) return fallback;
      return {
        ok: false,
        reason: "resolver-unavailable",
        source: null,
        key: null,
        fallback_reason: fallback.reason ?? null,
      };
    }
    const resolution = bootstrapFunctionResolver.resolveFunctionDesignator({
      name: symbolName,
      packageName,
    });
    if (resolution?.ok) {
      return {
        ok: true,
        entry_index: resolution.entryIndex >>> 0,
        source: resolution.source ?? null,
        key: resolution.key ?? null,
      };
    }
    if ((resolution?.reason ?? "") === "ambiguous") {
      return {
        ok: false,
        reason: "ambiguous",
        source: resolution?.source ?? null,
        key: resolution?.key ?? null,
        alternatives: Array.isArray(resolution?.alternatives)
          ? resolution.alternatives.slice()
          : [],
      };
    }
    const fallback = runtimeProbeFallback();
    if (fallback.ok) return fallback;
    return {
      ok: false,
      reason: resolution?.reason ?? "missing",
      source: resolution?.source ?? null,
      key: resolution?.key ?? null,
      fallback_reason: fallback.reason ?? null,
    };
  };
  const normalizeTargetCell = (value) => {
    const token = String(value ?? "").trim().toLowerCase();
    return token === "fcell" ? "fcell" : "vcell";
  };
  const makeSymbolBindingKey = (targetCell, packageName, symbolName) => (
    `${normalizeTargetCell(targetCell)}:${String(packageName ?? "").trim().toUpperCase()}::${String(symbolName ?? "").trim().toUpperCase()}`
  );
  const readConstPoolAnchor = (entry) => {
    const definition = (
      entry?.definition &&
      typeof entry.definition === "object" &&
      !Array.isArray(entry.definition)
    )
      ? entry.definition
      : null;
    const entryIndex = Number(definition?.entry_index);
    const constIndex = Number(definition?.const_index);
    if (!Number.isInteger(entryIndex) || entryIndex < 0) return null;
    if (!Number.isInteger(constIndex) || constIndex < 0) return null;
    return {
      entry_index: entryIndex >>> 0,
      const_index: constIndex >>> 0,
      const_tag: Number.isFinite(definition?.const_tag) ? (definition.const_tag >>> 0) : null,
      const_pool_depth: Number.isFinite(definition?.const_pool_depth)
        ? (definition.const_pool_depth >>> 0)
        : null,
      const_pool_source: typeof definition?.const_pool_source === "string"
        ? definition.const_pool_source
        : null,
    };
  };
  const requiredCallableKeys = new Set(
    (Array.isArray(contract?.requiredCallables) ? contract.requiredCallables : [])
      .map((item) => `${String(item?.packageName ?? "").trim().toUpperCase()}::${String(item?.symbolName ?? "").trim().toUpperCase()}`)
      .filter((key) => key !== "::"),
  );
  const requiredCallableCoverage = new Map();
  for (const symbolKey of requiredCallableKeys.values()) {
    requiredCallableCoverage.set(symbolKey, {
      entry_count: 0,
      required_class_entry_count: 0,
      sample: null,
    });
  }
  for (const entry of entries) {
    if (normalizeTargetCell(entry?.target_cell ?? null) !== "fcell") continue;
    const packageName = String(entry?.package_name ?? "").trim().toUpperCase();
    const symbolName = String(entry?.symbol_name ?? "").trim().toUpperCase();
    if (!packageName || !symbolName) continue;
    const symbolKey = `${packageName}::${symbolName}`;
    if (!requiredCallableCoverage.has(symbolKey)) continue;
    const coverage = requiredCallableCoverage.get(symbolKey);
    const requiredClass = String(
      entry?.definition?.required_class ?? entry?.required_class ?? "",
    ).trim().toLowerCase();
    coverage.entry_count++;
    if (requiredClass === STARTUP_SYMBOL_REQUIRED_CLASS.REQUIRED_CALLABLE) {
      coverage.required_class_entry_count++;
    }
    if (coverage.sample == null) {
      coverage.sample = {
        availability: String(entry?.availability ?? "deferred"),
        initializer_kind: String(entry?.initializer?.kind ?? ""),
        initializer_entry_index: Number.isInteger(entry?.initializer?.entry_index)
          ? (entry.initializer.entry_index >>> 0)
          : null,
        required_class: requiredClass || null,
      };
    }
  }
  for (const [symbolKey, coverage] of requiredCallableCoverage.entries()) {
    if (coverage.entry_count === 0) {
      failures.push({
        symbol_key: symbolKey,
        target_cell: "fcell",
        reason: "required-callable-binding-missing-from-map",
        required_policy: "required-callable-contract-missing",
      });
      continue;
    }
    if (coverage.required_class_entry_count === 0) {
      failures.push({
        symbol_key: symbolKey,
        target_cell: "fcell",
        reason: "required-callable-binding-class-mismatch",
        required_policy: "required-callable-contract-demoted",
        entry_count: coverage.entry_count,
        sample: coverage.sample,
      });
    }
  }

  let eligibleEntries = 0;
  let appliedCount = 0;
  let skippedAlreadyBound = 0;
  let requiredUninitialized = 0;
  let skippedSymbolUnresolved = 0;
  let symbolAnchorCandidates = 0;
  let symbolAnchorAttempts = 0;
  let symbolAnchorResolved = 0;
  let symbolAnchorUnresolved = 0;
  let symbolAnchorExportMissing = 0;
  let symbolAnchorConstPoolRefMissing = 0;
  let optionalDeferredMissingExport = 0;
  const optionalDeferredEntries = [];
  const targetCounts = {
    vcell: {
      eligible_entries: 0,
      applied_count: 0,
      skipped_already_bound: 0,
      skipped_symbol_unresolved: 0,
      required_non_nil_unavailable: 0,
      optional_deferred_missing_export: 0,
    },
    fcell: {
      eligible_entries: 0,
      applied_count: 0,
      skipped_already_bound: 0,
      skipped_symbol_unresolved: 0,
      required_non_nil_unavailable: 0,
      optional_deferred_missing_export: 0,
    },
  };
  // Artifact-owned startup: apply map entries directly; required const-pool refs are gate-only.
  const appliedSymbolBindingKeys = new Set();
  // exact package+name probe only; no symbol-name-only fallback.
  const probeSymbolByName = (nameMem, pkgMem) => {
    const raw = ex.wasm_probe_symbol(
      nameMem.ptr >>> 0,
      nameMem.len >>> 0,
      pkgMem.ptr >>> 0,
      pkgMem.len >>> 0,
    ) >>> 0;
    const status = probeStatus();
    return { raw, status };
  };

  for (const entry of entries) {
    const packageName = String(entry?.package_name ?? "").trim();
    const symbolName = String(entry?.symbol_name ?? "").trim();
    const targetCell = normalizeTargetCell(entry?.target_cell ?? null);
    const bindingClass = String(entry?.binding_class ?? "").trim().toLowerCase() || null;
    const requireNonNil = Boolean(entry?.require_non_nil);
    const availability = String(entry?.availability ?? "deferred");
    const initializer = entry?.initializer ?? {};
    const initializerKind = String(initializer?.kind ?? "");
    const initializerReason = String(initializer?.reason ?? "").trim().toLowerCase();
    const requiredClass = String(
      entry?.definition?.required_class ?? entry?.required_class ?? "",
    ).trim().toLowerCase();
    const requiredBinding = requireNonNil || (
      requiredClass === STARTUP_SYMBOL_REQUIRED_CLASS.REQUIRED_CALLABLE ||
      requiredClass === STARTUP_SYMBOL_REQUIRED_CLASS.REQUIRED_SPECIAL
    );
    const resolutionStatus = String(
      entry?.definition?.resolution_status ?? entry?.resolution_status ?? "",
    ).trim().toLowerCase();
    const requiredUnresolvedDeferred = initializerReason === "required-symbol-unresolved" || (
      (
        requiredClass === STARTUP_SYMBOL_REQUIRED_CLASS.REQUIRED_CALLABLE ||
        requiredClass === STARTUP_SYMBOL_REQUIRED_CLASS.REQUIRED_SPECIAL
      ) &&
      resolutionStatus === STARTUP_SYMBOL_RESOLUTION_STATUS.UNRESOLVED
    );
    const bindingKey = makeSymbolBindingKey(targetCell, packageName, symbolName);
    if (bindingKey && appliedSymbolBindingKeys.has(bindingKey)) {
      continue;
    }

    const eligible = availability === "literal" || availability === "entry-backed";
    if (!eligible) {
      // required unresolved is fatal pre-gate; optional unresolved remains deferred with reason.
      if (requiredUnresolvedDeferred) {
        requiredUninitialized++;
        targetCounts[targetCell].required_non_nil_unavailable++;
        failures.push({
          package_name: packageName || null,
          symbol_name: symbolName || null,
          target_cell: targetCell,
          binding_class: bindingClass,
          reason: "required-symbol-unresolved",
          availability,
          initializer_kind: initializerKind || null,
          initializer_reason: initializer?.reason ?? null,
          required_class: requiredClass || null,
          resolution_status: resolutionStatus || null,
        });
        continue;
      }
      if (requireNonNil) {
        requiredUninitialized++;
        targetCounts[targetCell].required_non_nil_unavailable++;
        failures.push({
          package_name: packageName || null,
          symbol_name: symbolName || null,
          target_cell: targetCell,
          binding_class: bindingClass,
          reason: "required-non-nil-initializer-unavailable",
          availability,
          initializer_kind: initializerKind || null,
          initializer_reason: initializer?.reason ?? null,
        });
      }
      continue;
    }
    eligibleEntries++;
    targetCounts[targetCell].eligible_entries++;

    if (requiredClass === STARTUP_SYMBOL_REQUIRED_CLASS.REQUIRED_CALLABLE) {
      if (targetCell !== "fcell") {
        failures.push({
          package_name: packageName || null,
          symbol_name: symbolName || null,
          target_cell: targetCell,
          binding_class: bindingClass,
          reason: "missing-kernel-export",
          required_policy: "required-target-cell-mismatch",
          export_name: "initializer-target-mismatch",
          initializer_kind: initializerKind || null,
          expected_target_cell: "fcell",
        });
        continue;
      }
      if (initializerKind !== "entry-function") {
        failures.push({
          package_name: packageName || null,
          symbol_name: symbolName || null,
          target_cell: targetCell,
          binding_class: bindingClass,
          reason: "initializer-kind-unsupported-at-apply",
          required_policy: "required-callable-initializer-kind-mismatch",
          initializer_kind: initializerKind || null,
          expected_initializer_kind: "entry-function",
        });
        continue;
      }
    }
    if (requiredClass === STARTUP_SYMBOL_REQUIRED_CLASS.REQUIRED_SPECIAL) {
      if (targetCell !== "vcell") {
        failures.push({
          package_name: packageName || null,
          symbol_name: symbolName || null,
          target_cell: targetCell,
          binding_class: bindingClass,
          reason: "missing-kernel-export",
          required_policy: "required-target-cell-mismatch",
          export_name: "initializer-target-mismatch",
          initializer_kind: initializerKind || null,
          expected_target_cell: "vcell",
        });
        continue;
      }
      if (!REQUIRED_SPECIAL_ALLOWED_INITIALIZER_KINDS.has(initializerKind)) {
        failures.push({
          package_name: packageName || null,
          symbol_name: symbolName || null,
          target_cell: targetCell,
          binding_class: bindingClass,
          reason: "initializer-kind-unsupported-at-apply",
          required_policy: "required-special-initializer-kind-mismatch",
          initializer_kind: initializerKind || null,
          expected_initializer_kind: "literal-fixnum|literal-nil|literal-symbol|literal-keyword",
        });
        continue;
      }
    }

    if (!packageName || !symbolName) {
      failures.push({
        package_name: packageName || null,
        symbol_name: symbolName || null,
        target_cell: targetCell,
        binding_class: bindingClass,
        reason: packageName ? "entry-missing-symbol-name" : "entry-missing-package-name",
      });
      continue;
    }

    const nameMem = scratchUtf8(symbolName);
    const pkgMem = scratchUtf8(packageName);
    const symbolProbe = probeSymbolByName(nameMem, pkgMem);
    let symbolRaw = symbolProbe.raw >>> 0;
    let symbolStatus = symbolProbe.status >>> 0;
    let symbolResolved = symbolStatus === L0_PROBE_STATUS.OK && symbolRaw !== 0 && symbolRaw !== nil;
    const symbolAnchor = readConstPoolAnchor(entry);
    let symbolAnchorRaw = null;
    let symbolAnchorStatus = null;
    let symbolAnchorAttempted = false;
    if (symbolAnchor) {
      symbolAnchorCandidates++;
    }
    if (!symbolResolved && symbolAnchor) {
      if (typeof ex.wasm_const_pool_ref !== "function") {
        symbolAnchorExportMissing++;
      } else if (!constPoolsInstalled.has(symbolAnchor.entry_index >>> 0)) {
        symbolAnchorConstPoolRefMissing++;
      } else {
        symbolAnchorAttempted = true;
        symbolAnchorAttempts++;
        const anchoredRaw = ex.wasm_const_pool_ref(
          symbolAnchor.entry_index >>> 0,
          symbolAnchor.const_index >>> 0,
        ) >>> 0;
        const anchoredStatus = probeStatus();
        symbolAnchorRaw = anchoredRaw >>> 0;
        symbolAnchorStatus = anchoredStatus >>> 0;
        if (
          symbolAnchorStatus !== L0_PROBE_STATUS.OK ||
          symbolAnchorRaw === 0 ||
          symbolAnchorRaw === nil
        ) {
          symbolAnchorConstPoolRefMissing++;
        } else {
          const reprobe = probeSymbolByName(nameMem, pkgMem);
          symbolRaw = reprobe.raw >>> 0;
          symbolStatus = reprobe.status >>> 0;
          symbolResolved = symbolStatus === L0_PROBE_STATUS.OK && symbolRaw !== 0 && symbolRaw !== nil;
          if (symbolResolved) symbolAnchorResolved++;
          else symbolAnchorUnresolved++;
        }
      }
    }
    if (!symbolResolved) {
      skippedSymbolUnresolved++;
      targetCounts[targetCell].skipped_symbol_unresolved++;
      if (requireNonNil) {
        failures.push({
          package_name: packageName || null,
          symbol_name: symbolName || null,
          target_cell: targetCell,
          binding_class: bindingClass,
          reason: "required-symbol-unresolved",
          probe_status: symbolStatus,
          probe_status_name: l0ProbeStatusName(symbolStatus),
          symbol_raw: toHex(symbolRaw),
          symbol_anchor: symbolAnchor ? {
            entry_index: symbolAnchor.entry_index >>> 0,
            const_index: symbolAnchor.const_index >>> 0,
            const_tag: symbolAnchor.const_tag,
            const_pool_depth: symbolAnchor.const_pool_depth,
            const_pool_source: symbolAnchor.const_pool_source,
            const_pool_entry_installed: constPoolsInstalled.has(symbolAnchor.entry_index >>> 0),
            attempted: symbolAnchorAttempted,
            anchor_ref_raw: symbolAnchorRaw == null ? null : toHex(symbolAnchorRaw),
            anchor_probe_status: symbolAnchorStatus,
            anchor_probe_status_name: symbolAnchorStatus == null
              ? null
              : l0ProbeStatusName(symbolAnchorStatus),
            export_missing: typeof ex.wasm_const_pool_ref !== "function",
          } : null,
        });
      }
      continue;
    }

    let beforeCell = 0;
    let beforeCellStatus = L0_PROBE_STATUS.OK;
    if (symbolResolved && targetCell === "fcell") {
      beforeCell = ex.wasm_probe_symbol_fcell(symbolRaw >>> 0) >>> 0;
      beforeCellStatus = probeStatus();
    } else if (symbolResolved) {
      beforeCell = ex.wasm_probe_symbol_vcell(symbolRaw >>> 0) >>> 0;
      beforeCellStatus = probeStatus();
    } else {
      beforeCell = nil;
      beforeCellStatus = L0_PROBE_STATUS.SYMBOL_MISSING;
    }
    if (symbolResolved && beforeCellStatus !== L0_PROBE_STATUS.OK) {
      failures.push({
        package_name: packageName || null,
        symbol_name: symbolName || null,
        target_cell: targetCell,
        binding_class: bindingClass,
        reason: "target-cell-probe-failed-before-apply",
        probe_status: beforeCellStatus,
        probe_status_name: l0ProbeStatusName(beforeCellStatus),
        symbol_raw: toHex(symbolRaw),
      });
      continue;
    }
    if (symbolResolved && targetCell === "fcell") {
      const beforeEntry = ex.wasm_debug_function_entry_index(beforeCell >>> 0) | 0;
      const desiredEntry = initializerKind === "entry-function" && Number.isInteger(initializer?.entry_index)
        ? (initializer.entry_index >>> 0)
        : null;
      if (requiredClass === STARTUP_SYMBOL_REQUIRED_CLASS.REQUIRED_CALLABLE) {
        const resolverEntry = resolveRequiredCallableEntryFromBootstrapResolver(packageName, symbolName);
        if (!resolverEntry.ok) {
          failures.push({
            package_name: packageName || null,
            symbol_name: symbolName || null,
            target_cell: targetCell,
            binding_class: bindingClass,
            reason: "required-callable-unverified-by-bootstrap-resolver",
            initializer_kind: initializerKind || null,
            initializer_entry_index: desiredEntry,
            resolver_reason: resolverEntry.reason ?? null,
            resolver_source: resolverEntry.source ?? null,
            resolver_key: resolverEntry.key ?? null,
            fcell_raw: toHex(beforeCell),
            fcell_entry_index: beforeEntry,
          });
          continue;
        }
        if (desiredEntry == null || (desiredEntry >>> 0) !== (resolverEntry.entry_index >>> 0)) {
          failures.push({
            package_name: packageName || null,
            symbol_name: symbolName || null,
            target_cell: targetCell,
            binding_class: bindingClass,
            reason: "required-callable-entry-mismatch-with-bootstrap-resolver",
            initializer_kind: initializerKind || null,
            initializer_entry_index: desiredEntry,
            resolver_entry_index: resolverEntry.entry_index >>> 0,
            resolver_source: resolverEntry.source ?? null,
            resolver_key: resolverEntry.key ?? null,
            fcell_raw: toHex(beforeCell),
            fcell_entry_index: beforeEntry,
          });
          continue;
        }
      }
      if (beforeEntry >= 0 && desiredEntry != null && (beforeEntry >>> 0) === desiredEntry) {
        skippedAlreadyBound++;
        targetCounts[targetCell].skipped_already_bound++;
        continue;
      }
    } else if (symbolResolved && !isNilLike(beforeCell)) {
      skippedAlreadyBound++;
      targetCounts[targetCell].skipped_already_bound++;
      continue;
    }

    const initializerTargetCell = targetCell === "fcell"
      ? WASM_SYMBOL_TARGET_CELL.FCELL
      : WASM_SYMBOL_TARGET_CELL.VCELL;

    let missingExport = null;
    let initializerRuntimeGuard = null;
    switch (initializerKind) {
      case "literal-fixnum":
      case "literal-nil":
        if (targetCell !== "vcell") {
          missingExport = "initializer-target-mismatch";
        } else {
          missingExport = typeof ex.wasm_set_symbol_cell_initializer !== "function"
            ? "wasm_set_symbol_cell_initializer"
            : null;
        }
        break;
      case "literal-symbol":
      case "literal-keyword": {
        initializerRuntimeGuard = LITERAL_SYMBOL_KEYWORD_RUNTIME_GUARDS[initializerKind] ?? null;
        if (targetCell !== "vcell") {
          missingExport = "initializer-target-mismatch";
        } else if (!initializerRuntimeGuard) {
          missingExport = "initializer-kind-not-supported";
        } else {
          for (const exportName of initializerRuntimeGuard.required_exports) {
            if (typeof ex[exportName] !== "function") {
              missingExport = exportName;
              break;
            }
          }
        }
        break;
      }
      case "entry-function":
        missingExport = typeof ex.wasm_set_symbol_cell_initializer !== "function"
          ? "wasm_set_symbol_cell_initializer"
          : null;
        break;
      default:
        missingExport = null;
        break;
    }
    if (missingExport) {
      const optionalDeferReason = initializerRuntimeGuard?.optional_defer_reason
        ?? "initializer-kind-not-supported";
      if (!requiredBinding) {
        optionalDeferredMissingExport++;
        targetCounts[targetCell].optional_deferred_missing_export++;
        optionalDeferredEntries.push({
          package_name: packageName || null,
          symbol_name: symbolName || null,
          target_cell: targetCell,
          binding_class: bindingClass,
          reason: optionalDeferReason,
          optional_policy: "optional-initializer-kind-not-supported-defer",
          export_name: missingExport,
          initializer_kind: initializerKind || null,
          initializer_label: initializerRuntimeGuard?.initializer_label ?? null,
          apply_method: "name-symbol",
        });
        continue;
      }
      failures.push({
        package_name: packageName || null,
        symbol_name: symbolName || null,
        target_cell: targetCell,
        binding_class: bindingClass,
        reason: "missing-kernel-export",
        required_policy: "required-missing-kernel-export",
        export_name: missingExport,
        initializer_kind: initializerKind || null,
        initializer_label: initializerRuntimeGuard?.initializer_label ?? null,
        optional_defer_reason: optionalDeferReason,
        apply_method: "name-symbol",
      });
      continue;
    }

    switch (initializerKind) {
      case "literal-fixnum": {
        const value = Number(initializer?.fixnum_value);
        if (!Number.isInteger(value)) {
          failures.push({
            package_name: packageName || null,
            symbol_name: symbolName || null,
            target_cell: targetCell,
            binding_class: bindingClass,
            reason: "initializer-invalid-fixnum",
            initializer_kind: initializerKind,
            initializer_value: initializer?.fixnum_value ?? null,
          });
          continue;
        }
        ex.wasm_set_symbol_cell_initializer(
          nameMem.ptr >>> 0,
          nameMem.len >>> 0,
          pkgMem.ptr >>> 0,
          pkgMem.len >>> 0,
          initializerTargetCell >>> 0,
          WASM_SYMBOL_CELL_INITIALIZER_KIND.LITERAL_FIXNUM,
          value | 0,
          0,
          0,
          0,
          0,
          0,
        );
        break;
      }
      case "literal-nil":
        ex.wasm_set_symbol_cell_initializer(
          nameMem.ptr >>> 0,
          nameMem.len >>> 0,
          pkgMem.ptr >>> 0,
          pkgMem.len >>> 0,
          initializerTargetCell >>> 0,
          WASM_SYMBOL_CELL_INITIALIZER_KIND.LITERAL_NIL,
          0,
          0,
          0,
          0,
          0,
          0,
        );
        break;
      case "literal-symbol": {
        const literalPackageName = String(
          initializer?.literal_package_name ??
          initializer?.value_package_name ??
          initializer?.package_name ??
          initializer?.package ??
          "",
        ).trim();
        const literalSymbolName = String(
          initializer?.literal_symbol_name ??
          initializer?.value_symbol_name ??
          initializer?.symbol_name ??
          initializer?.name ??
          "",
        ).trim();
        if (!literalPackageName || !literalSymbolName) {
          failures.push({
            package_name: packageName || null,
            symbol_name: symbolName || null,
            target_cell: targetCell,
            binding_class: bindingClass,
            reason: "initializer-invalid-literal-symbol",
            initializer_kind: initializerKind,
            initializer_package_name: literalPackageName || null,
            initializer_symbol_name: literalSymbolName || null,
          });
          continue;
        }
        const literalNameMem = scratchUtf8(literalSymbolName);
        const literalPkgMem = scratchUtf8(literalPackageName);
        ex.wasm_set_symbol_cell_initializer(
          nameMem.ptr >>> 0,
          nameMem.len >>> 0,
          pkgMem.ptr >>> 0,
          pkgMem.len >>> 0,
          initializerTargetCell >>> 0,
          WASM_SYMBOL_CELL_INITIALIZER_KIND.LITERAL_SYMBOL,
          0,
          0,
          literalNameMem.ptr >>> 0,
          literalNameMem.len >>> 0,
          literalPkgMem.ptr >>> 0,
          literalPkgMem.len >>> 0,
        );
        break;
      }
      case "literal-keyword": {
        const literalKeywordName = String(
          initializer?.literal_keyword_name ??
          initializer?.keyword_name ??
          initializer?.value_keyword_name ??
          initializer?.value_symbol_name ??
          initializer?.symbol_name ??
          initializer?.name ??
          "",
        ).trim();
        if (!literalKeywordName) {
          failures.push({
            package_name: packageName || null,
            symbol_name: symbolName || null,
            target_cell: targetCell,
            binding_class: bindingClass,
            reason: "initializer-invalid-literal-keyword",
            initializer_kind: initializerKind,
            initializer_symbol_name: literalKeywordName || null,
          });
          continue;
        }
        const literalKeywordMem = scratchUtf8(literalKeywordName);
        const literalKeywordPkgMem = scratchUtf8("KEYWORD");
        ex.wasm_set_symbol_cell_initializer(
          nameMem.ptr >>> 0,
          nameMem.len >>> 0,
          pkgMem.ptr >>> 0,
          pkgMem.len >>> 0,
          initializerTargetCell >>> 0,
          WASM_SYMBOL_CELL_INITIALIZER_KIND.LITERAL_KEYWORD,
          0,
          0,
          literalKeywordMem.ptr >>> 0,
          literalKeywordMem.len >>> 0,
          literalKeywordPkgMem.ptr >>> 0,
          literalKeywordPkgMem.len >>> 0,
        );
        break;
      }
      case "entry-function": {
        const entryIndex = Number(initializer?.entry_index);
        if (!Number.isInteger(entryIndex) || entryIndex < 0) {
          failures.push({
            package_name: packageName || null,
            symbol_name: symbolName || null,
            target_cell: targetCell,
            binding_class: bindingClass,
            reason: "initializer-invalid-entry-index",
            initializer_kind: initializerKind,
            initializer_value: initializer?.entry_index ?? null,
          });
          continue;
        }
        ex.wasm_set_symbol_cell_initializer(
          nameMem.ptr >>> 0,
          nameMem.len >>> 0,
          pkgMem.ptr >>> 0,
          pkgMem.len >>> 0,
          initializerTargetCell >>> 0,
          WASM_SYMBOL_CELL_INITIALIZER_KIND.ENTRY_FUNCTION,
          0,
          entryIndex >>> 0,
          0,
          0,
          0,
          0,
        );
        break;
      }
      default:
        failures.push({
          package_name: packageName || null,
          symbol_name: symbolName || null,
          target_cell: targetCell,
          binding_class: bindingClass,
          reason: "initializer-kind-unsupported-at-apply",
          initializer_kind: initializerKind || null,
        });
        continue;
    }

    const applyStatus = probeStatus();
    if (applyStatus !== L0_PROBE_STATUS.OK) {
      const unresolvedApplyAllowed = !requireNonNil && (
        applyStatus === L0_PROBE_STATUS.SYMBOL_MISSING ||
        applyStatus === L0_PROBE_STATUS.PACKAGE_MISSING
      );
      if (unresolvedApplyAllowed) {
        skippedSymbolUnresolved++;
        targetCounts[targetCell].skipped_symbol_unresolved++;
        continue;
      }
      failures.push({
        package_name: packageName || null,
        symbol_name: symbolName || null,
        target_cell: targetCell,
        binding_class: bindingClass,
        reason: "apply-status-not-ok",
        probe_status: applyStatus,
        probe_status_name: l0ProbeStatusName(applyStatus),
        initializer_kind: initializerKind || null,
        apply_method: "name-symbol",
      });
      continue;
    }

    if (!symbolResolved) {
      skippedSymbolUnresolved++;
      targetCounts[targetCell].skipped_symbol_unresolved++;
      if (requireNonNil) {
        failures.push({
          package_name: packageName || null,
          symbol_name: symbolName || null,
          target_cell: targetCell,
          binding_class: bindingClass,
          reason: "required-symbol-unresolved-after-apply",
          probe_status: symbolStatus,
          probe_status_name: l0ProbeStatusName(symbolStatus),
          symbol_raw: toHex(symbolRaw),
        });
      }
      continue;
    }

    if (targetCell === "fcell") {
      const afterFcell = ex.wasm_probe_symbol_fcell(symbolRaw >>> 0) >>> 0;
      const afterFcellStatus = probeStatus();
      if (afterFcellStatus !== L0_PROBE_STATUS.OK) {
        failures.push({
          package_name: packageName || null,
          symbol_name: symbolName || null,
          target_cell: targetCell,
          binding_class: bindingClass,
          reason: "fcell-probe-failed-after-apply",
          probe_status: afterFcellStatus,
          probe_status_name: l0ProbeStatusName(afterFcellStatus),
          symbol_raw: toHex(symbolRaw),
        });
        continue;
      }
      const afterEntry = ex.wasm_debug_function_entry_index(afterFcell >>> 0) | 0;
      if (afterEntry < 0) {
        failures.push({
          package_name: packageName || null,
          symbol_name: symbolName || null,
          target_cell: targetCell,
          binding_class: bindingClass,
          reason: "fcell-still-non-callable-after-apply",
          initializer_kind: initializerKind || null,
          fcell_raw: toHex(afterFcell),
          fcell_entry_index: afterEntry,
        });
        continue;
      }
    } else {
      const afterVcell = ex.wasm_probe_symbol_vcell(symbolRaw >>> 0) >>> 0;
      const afterVcellStatus = probeStatus();
      if (afterVcellStatus !== L0_PROBE_STATUS.OK) {
        failures.push({
          package_name: packageName || null,
          symbol_name: symbolName || null,
          target_cell: targetCell,
          binding_class: bindingClass,
          reason: "vcell-probe-failed-after-apply",
          probe_status: afterVcellStatus,
          probe_status_name: l0ProbeStatusName(afterVcellStatus),
          symbol_raw: toHex(symbolRaw),
        });
        continue;
      }
      if (requireNonNil && isNilLike(afterVcell)) {
        failures.push({
          package_name: packageName || null,
          symbol_name: symbolName || null,
          target_cell: targetCell,
          binding_class: bindingClass,
          reason: "vcell-still-nil-after-apply",
          initializer_kind: initializerKind || null,
          vcell_raw: toHex(afterVcell),
        });
        continue;
      }
    }
    appliedCount++;
    targetCounts[targetCell].applied_count++;
    if (bindingKey) {
      appliedSymbolBindingKeys.add(bindingKey);
    }
  }

  const applySummary = {
    schema_version: "startup_binding_map_apply_v1",
    status: failures.length > 0 ? "fail" : "pass",
    phase: "pre-fasload",
    source: mapSource ?? null,
    map_schema_version: mapArtifact?.schema_version ?? null,
    contract_id: contract?.id ?? null,
    constants: mapArtifact?.coverage?.required_special_variable_bindings ?? null,
    coverage: mapArtifact?.coverage ?? null,
    counts: {
      total_entries: counts.total_entries,
      literal_entries: counts.literal_entries,
      entry_backed_entries: counts.entry_backed_entries,
      deferred_entries: counts.deferred_entries,
      unsupported_entries: counts.unsupported_entries,
      vcell_entries: counts.vcell_entries ?? null,
      fcell_entries: counts.fcell_entries ?? null,
      special_variable_entries: counts.special_variable_entries ?? null,
      function_entries: counts.function_entries ?? null,
      eligible_entries: eligibleEntries,
      unique_bindings_applied: appliedSymbolBindingKeys.size,
      required_non_nil_unavailable: requiredUninitialized,
      applied_count: appliedCount,
      skipped_already_bound: skippedAlreadyBound,
      skipped_symbol_unresolved: skippedSymbolUnresolved,
      optional_deferred_missing_export: optionalDeferredMissingExport,
      artifact_owned_constants: true,
      symbol_anchor: {
        candidate_entries: symbolAnchorCandidates,
        attempted: symbolAnchorAttempts,
        resolved_by_anchor: symbolAnchorResolved,
        unresolved_after_anchor: symbolAnchorUnresolved,
        export_missing: symbolAnchorExportMissing,
        const_pool_ref_missing: symbolAnchorConstPoolRefMissing,
      },
      failed_count: failures.length,
      target_counts: targetCounts,
    },
    first_failure: failures.length > 0 ? failures[0] : null,
    first_optional_deferred_missing_export: optionalDeferredEntries.length > 0
      ? optionalDeferredEntries[0]
      : null,
  };
  if (failures.length > 0) {
    console.error(`STARTUP_BINDING_MAP_APPLY ${JSON.stringify(applySummary)}`);
    fail(`pre-fasload startup binding map apply failed: ${failures.length} requirement(s)`);
  }
  console.log(`STARTUP_BINDING_MAP_APPLY ${JSON.stringify(applySummary)}`);
  return applySummary;
}

function assertL0BootstrapContractOrFail(contract = BOOTSTRAP_L0_CONTRACT_V1) {
  const requiredExports = [
    "wasm_get_lisp_nil",
    "wasm_probe_package",
    "wasm_probe_symbol",
    "wasm_probe_symbol_fcell",
    "wasm_probe_symbol_vcell",
    "wasm_probe_last_status",
    "wasm_debug_function_entry_index",
  ];
  for (const name of requiredExports) {
    if (typeof ex[name] !== "function") {
      fail(`kernel missing ${name} for pre-fasload L0 contract gate`);
    }
  }

  const nil = ex.wasm_get_lisp_nil() >>> 0;
  const miscSubtag = typeof ex.wasm_debug_misc_subtag === "function"
    ? (value) => (ex.wasm_debug_misc_subtag(value >>> 0) | 0)
    : () => null;
  const utf8 = new TextEncoder();
  const scratchUtf8 = (text) => {
    const bytes = utf8.encode(String(text ?? ""));
    if (bytes.length === 0) return { ptr: 0, len: 0 };
    const ptr = copyBytesToScratch(runtime.memory, bytes);
    return { ptr, len: bytes.length >>> 0 };
  };
  const probeStatus = () => (ex.wasm_probe_last_status() >>> 0);
  const readDebug = (name) => (typeof ex[name] === "function" ? (ex[name]() >>> 0) : null);

  const probePackage = (packageName) => {
    const normalizedPackageName = String(packageName ?? "").trim();
    if (!normalizedPackageName) {
      const status = L0_PROBE_STATUS.PACKAGE_MISSING;
      return {
        raw: 0,
        status,
        statusName: l0ProbeStatusName(status),
        subtag: miscSubtag(0),
        isNil: true,
        packageName: normalizedPackageName,
      };
    }
    const pkgMem = scratchUtf8(normalizedPackageName);
    const raw = ex.wasm_probe_package(pkgMem.ptr >>> 0, pkgMem.len >>> 0) >>> 0;
    const status = probeStatus();
    return {
      raw,
      status,
      statusName: l0ProbeStatusName(status),
      subtag: miscSubtag(raw),
      isNil: raw === nil,
      packageName: normalizedPackageName,
    };
  };

  const probeSymbol = ({ packageName, symbolName }) => {
    const normalizedPackageName = String(packageName ?? "").trim();
    const normalizedSymbolName = String(symbolName ?? "").trim();
    if (!normalizedPackageName || !normalizedSymbolName) {
      const status = !normalizedPackageName
        ? L0_PROBE_STATUS.PACKAGE_MISSING
        : L0_PROBE_STATUS.SYMBOL_MISSING;
      return {
        raw: 0,
        status,
        statusName: l0ProbeStatusName(status),
        subtag: miscSubtag(0),
        isNil: true,
        packageName: normalizedPackageName,
        symbolName: normalizedSymbolName,
      };
    }
    const nameMem = scratchUtf8(normalizedSymbolName);
    const pkgMem = scratchUtf8(normalizedPackageName);
    const raw = ex.wasm_probe_symbol(
      nameMem.ptr >>> 0,
      nameMem.len >>> 0,
      pkgMem.ptr >>> 0,
      pkgMem.len >>> 0,
    ) >>> 0;
    const status = probeStatus();
    return {
      raw,
      status,
      statusName: l0ProbeStatusName(status),
      subtag: miscSubtag(raw),
      isNil: raw === nil,
      packageName: normalizedPackageName,
      symbolName: normalizedSymbolName,
    };
  };

  const failures = [];
  const recordFailure = (kind, details) => {
    failures.push({
      schema_version: "bootstrap_l0_gate_v1",
      contract_id: contract?.id ?? "bootstrap-l0-contract-unknown",
      status: "fail",
      check_kind: kind,
      ...details,
    });
  };

  const requiredConstPools = Array.isArray(contract?.requiredConstPools)
    ? contract.requiredConstPools
    : [];
  if (requiredConstPools.length > 0 && typeof ex.wasm_const_pool_ref !== "function") {
    fail("kernel missing wasm_const_pool_ref for pre-fasload L0 const-pool gate");
  }

  for (const item of requiredConstPools) {
    const entryIndex = item?.entryIndex >>> 0;
    const refs = Array.isArray(item?.requiredRefs) ? item.requiredRefs : [];
    for (const rawRef of refs) {
      const constIndex = rawRef >>> 0;
      const raw = ex.wasm_const_pool_ref(entryIndex, constIndex) >>> 0;
      if (raw !== 0 && raw !== nil) continue;
      const debugError = readDebug("wasm_debug_const_pool_error");
      const debugNameLen = readDebug("wasm_debug_const_pool_symbol_name_len");
      const debugPkgLen = readDebug("wasm_debug_const_pool_symbol_pkg_len");
      const debugPhase = readDebug("wasm_debug_const_pool_phase");
      const debugOffset = readDebug("wasm_debug_const_pool_offset");
      const debugIndex = readDebug("wasm_debug_const_pool_index");
      const debugTag = readDebug("wasm_debug_const_pool_tag");
      const bootPhase = typeof ex.wasm_boot_get_phase === "function"
        ? (ex.wasm_boot_get_phase() >>> 0)
        : null;
      recordFailure("const-pool", {
        entry_index: entryIndex,
        const_index: constIndex,
        source: item?.source ?? null,
        reason: "const-pool-ref-nil",
        ref_raw: `0x${raw.toString(16)}`,
        lisp_nil: `0x${nil.toString(16)}`,
        boot_phase: bootPhase == null ? null : formatBootPhase(bootPhase),
        debug_error: debugError,
        debug_error_name: debugError == null ? null : (CONST_POOL_ERROR_NAMES.get(debugError) ?? "unknown"),
        debug_name_len: debugNameLen,
        debug_pkg_len: debugPkgLen,
        debug_phase: debugPhase,
        debug_index: debugIndex,
        debug_tag: debugTag,
        debug_offset: debugOffset,
      });
    }
  }

  for (const item of Array.isArray(contract?.requiredPackages) ? contract.requiredPackages : []) {
    const packageName = item?.packageName ?? "";
    const anchorSymbol = item?.anchorSymbol ?? "";
    if (anchorSymbol) {
      const probe = probeSymbol({
        packageName,
        symbolName: anchorSymbol,
      });
      if (probe.status === L0_PROBE_STATUS.PACKAGE_MISSING || probe.raw === 0 || probe.isNil) {
        recordFailure("package", {
          package_name: packageName || null,
          anchor_symbol: anchorSymbol || null,
          reason: probe.status === L0_PROBE_STATUS.PACKAGE_MISSING ? "package-missing" : "anchor-symbol-unresolved",
          probe_status: probe.status,
          probe_status_name: probe.statusName,
          probe_raw: `0x${probe.raw.toString(16)}`,
        });
      }
      continue;
    }

    const probe = probePackage(packageName);
    if (probe.status !== L0_PROBE_STATUS.OK || probe.raw === 0 || probe.isNil) {
      recordFailure("package", {
        package_name: packageName || null,
        reason: probe.status === L0_PROBE_STATUS.PACKAGE_MISSING ? "package-missing" : "package-invalid",
        probe_status: probe.status,
        probe_status_name: probe.statusName,
        probe_raw: `0x${probe.raw.toString(16)}`,
      });
    }
  }

  for (const item of Array.isArray(contract?.requiredSymbols) ? contract.requiredSymbols : []) {
    const probe = probeSymbol(item);
    if (probe.status !== L0_PROBE_STATUS.OK || probe.raw === 0 || probe.isNil) {
      recordFailure("symbol", {
        package_name: item?.packageName ?? null,
        symbol_name: item?.symbolName ?? null,
        source: item?.source ?? null,
        reason: "symbol-unresolved",
        probe_status: probe.status,
        probe_status_name: probe.statusName,
        probe_raw: `0x${probe.raw.toString(16)}`,
      });
    }
  }

  for (const item of Array.isArray(contract?.requiredCallables) ? contract.requiredCallables : []) {
    const symProbe = probeSymbol(item);
    if (symProbe.status !== L0_PROBE_STATUS.OK || symProbe.raw === 0 || symProbe.isNil) {
      recordFailure("callable", {
        package_name: item?.packageName ?? null,
        symbol_name: item?.symbolName ?? null,
        reason: "callable-symbol-unresolved",
        probe_status: symProbe.status,
        probe_status_name: symProbe.statusName,
        symbol_raw: `0x${symProbe.raw.toString(16)}`,
      });
      continue;
    }

    const fcellRaw = ex.wasm_probe_symbol_fcell(symProbe.raw >>> 0) >>> 0;
    const fcellStatus = probeStatus();
    const entryIndex = ex.wasm_debug_function_entry_index(fcellRaw >>> 0) | 0;
    if (fcellStatus !== L0_PROBE_STATUS.OK || entryIndex < 0) {
      recordFailure("callable", {
        package_name: item?.packageName ?? null,
        symbol_name: item?.symbolName ?? null,
        reason: fcellStatus !== L0_PROBE_STATUS.OK ? "fcell-probe-failed" : "fcell-not-callable",
        probe_status: fcellStatus,
        probe_status_name: l0ProbeStatusName(fcellStatus),
        symbol_raw: `0x${symProbe.raw.toString(16)}`,
        fcell_raw: `0x${fcellRaw.toString(16)}`,
        fcell_entry_index: entryIndex,
      });
    }
  }

  for (const item of Array.isArray(contract?.requiredSpecialVariables) ? contract.requiredSpecialVariables : []) {
    const symProbe = probeSymbol(item);
    if (symProbe.status !== L0_PROBE_STATUS.OK || symProbe.raw === 0 || symProbe.isNil) {
      recordFailure("special", {
        package_name: item?.packageName ?? null,
        symbol_name: item?.symbolName ?? null,
        reason: "special-symbol-unresolved",
        probe_status: symProbe.status,
        probe_status_name: symProbe.statusName,
        symbol_raw: `0x${symProbe.raw.toString(16)}`,
      });
      continue;
    }

    const vcellRaw = ex.wasm_probe_symbol_vcell(symProbe.raw >>> 0) >>> 0;
    const vcellStatus = probeStatus();
    const nonNilRequired = Boolean(item?.requireNonNil);
    const isNil = vcellRaw === 0 || vcellRaw === nil;
    if (vcellStatus !== L0_PROBE_STATUS.OK || (nonNilRequired && isNil)) {
      recordFailure("special", {
        package_name: item?.packageName ?? null,
        symbol_name: item?.symbolName ?? null,
        reason: vcellStatus !== L0_PROBE_STATUS.OK ? "vcell-probe-failed" : "vcell-nil",
        probe_status: vcellStatus,
        probe_status_name: l0ProbeStatusName(vcellStatus),
        symbol_raw: `0x${symProbe.raw.toString(16)}`,
        vcell_raw: `0x${vcellRaw.toString(16)}`,
        vcell_subtag: miscSubtag(vcellRaw),
      });
    }
  }

  if (failures.length > 0) {
    for (const failure of failures) {
      console.error(`L0_BOOTSTRAP_CONTRACT ${JSON.stringify(failure)}`);
    }
    fail(`pre-fasload L0 bootstrap contract failed: ${failures.length} requirement(s)`);
  }

  console.log(`L0_BOOTSTRAP_CONTRACT ${JSON.stringify({
    schema_version: "bootstrap_l0_gate_v1",
    contract_id: contract?.id ?? "bootstrap-l0-contract-unknown",
    status: "pass",
    counts: {
      packages: Array.isArray(contract?.requiredPackages) ? contract.requiredPackages.length : 0,
      const_pools: Array.isArray(contract?.requiredConstPools) ? contract.requiredConstPools.length : 0,
      symbols: Array.isArray(contract?.requiredSymbols) ? contract.requiredSymbols.length : 0,
      callables: Array.isArray(contract?.requiredCallables) ? contract.requiredCallables.length : 0,
      special_variables: Array.isArray(contract?.requiredSpecialVariables) ? contract.requiredSpecialVariables.length : 0,
    },
  })}`);
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
const kernelDebugSymbolName = typeof ex.wasm_debug_copy_symbol_name === "function"
  ? (obj) => {
    const len = ex.wasm_debug_copy_symbol_name(obj >>> 0, 0, 0) >>> 0;
    if (len === 0) return null;
    const ptr = allocScratch(runtime.memory, len);
    const copied = ex.wasm_debug_copy_symbol_name(obj >>> 0, ptr >>> 0, len) >>> 0;
    if (copied === 0) return null;
    try {
      return decoder.decode(new Uint8Array(runtime.memory.buffer, ptr >>> 0, Math.min(len, copied)));
    } catch {
      return null;
    }
  }
  : null;

// Resolver stage: consume startup scope after runtime exports are available
// and before startup binding map synthesis/build.
const startupSymbolResolutionBuild = buildStartupSymbolResolutionArtifact({
  scopeArtifact: embeddedStartupBindingMapRaw,
  resolverSource: startupBindingMapSource,
});
console.log(`STARTUP_SYMBOL_RESOLUTION_BUILD ${JSON.stringify(startupSymbolResolutionBuild.summary)}`);
if (startupSymbolResolutionOutPath) {
  try {
    await fs.mkdir(path.dirname(startupSymbolResolutionOutPath), { recursive: true });
    await fs.writeFile(
      startupSymbolResolutionOutPath,
      `${JSON.stringify(startupSymbolResolutionBuild.artifact)}\n`,
      "utf8",
    );
  } catch (err) {
    fail(
      `Unable to write --startup-symbol-resolution-out JSON at ${startupSymbolResolutionOutPath}: ${err?.message ?? err}`,
    );
  }
}

if (process.env.CCL_WASM_DIAG_REQUIRED_CALLABLE_RESOLVER === "1") {
  const requiredCallableRows = [];
  const nil = typeof ex.wasm_get_lisp_nil === "function"
    ? (ex.wasm_get_lisp_nil() >>> 0)
    : 0;
  const canProbeRuntimeEntry = (
    typeof ex.wasm_probe_symbol === "function" &&
    typeof ex.wasm_probe_symbol_fcell === "function" &&
    typeof ex.wasm_probe_last_status === "function" &&
    typeof ex.wasm_debug_function_entry_index === "function"
  );
  const probeStatus = () => (typeof ex.wasm_probe_last_status === "function"
    ? (ex.wasm_probe_last_status() >>> 0)
    : -1);
  const probeRuntimeCallableEntry = (packageName, symbolName) => {
    if (!canProbeRuntimeEntry) {
      return {
        ok: false,
        reason: "probe-exports-missing",
      };
    }
    const nameBytes = encoder.encode(String(symbolName ?? ""));
    const pkgBytes = encoder.encode(String(packageName ?? ""));
    const namePtr = nameBytes.length > 0 ? copyBytesToScratch(runtime.memory, nameBytes) : 0;
    const pkgPtr = pkgBytes.length > 0 ? copyBytesToScratch(runtime.memory, pkgBytes) : 0;
    const sym = ex.wasm_probe_symbol(
      namePtr >>> 0,
      nameBytes.length >>> 0,
      pkgPtr >>> 0,
      pkgBytes.length >>> 0,
    ) >>> 0;
    const symbolStatus = probeStatus();
    if (symbolStatus !== 0 || sym === 0 || sym === nil) {
      return {
        ok: false,
        reason: "symbol-unresolved",
        symbol_status: symbolStatus,
      };
    }
    const fcell = ex.wasm_probe_symbol_fcell(sym >>> 0) >>> 0;
    const fcellStatus = probeStatus();
    if (fcellStatus !== 0 || fcell === 0 || fcell === nil) {
      return {
        ok: false,
        reason: "fcell-unresolved",
        symbol_status: symbolStatus,
        fcell_status: fcellStatus,
      };
    }
    const entryIndex = ex.wasm_debug_function_entry_index(fcell >>> 0) | 0;
    if (entryIndex < 0) {
      return {
        ok: false,
        reason: "fcell-non-function",
        symbol_status: symbolStatus,
        fcell_status: fcellStatus,
      };
    }
    return {
      ok: true,
      entry_index: entryIndex >>> 0,
      symbol_status: symbolStatus,
      fcell_status: fcellStatus,
    };
  };

  for (const item of Array.isArray(BOOTSTRAP_L0_CONTRACT_V1?.requiredCallables)
    ? BOOTSTRAP_L0_CONTRACT_V1.requiredCallables
    : []) {
    const packageName = String(item?.packageName ?? "").trim();
    const symbolName = String(item?.symbolName ?? "").trim();
    const withPackage = bootstrapFunctionResolver.resolveFunctionDesignator({
      name: symbolName,
      packageName,
    });
    const nameOnly = bootstrapFunctionResolver.resolveFunctionDesignator({
      name: symbolName,
    });
    const runtimeProbe = probeRuntimeCallableEntry(packageName, symbolName);
    requiredCallableRows.push({
      symbol_key: `${packageName.toUpperCase()}::${symbolName.toUpperCase()}`,
      with_package: withPackage?.ok
        ? {
          ok: true,
          entry_index: withPackage.entryIndex >>> 0,
          source: withPackage.source ?? null,
          key: withPackage.key ?? null,
        }
        : {
          ok: false,
          reason: withPackage?.reason ?? "missing",
          source: withPackage?.source ?? null,
          key: withPackage?.key ?? null,
        },
      name_only: nameOnly?.ok
        ? {
          ok: true,
          entry_index: nameOnly.entryIndex >>> 0,
          source: nameOnly.source ?? null,
          key: nameOnly.key ?? null,
        }
        : {
          ok: false,
          reason: nameOnly?.reason ?? "missing",
          source: nameOnly?.source ?? null,
          key: nameOnly?.key ?? null,
        },
      runtime_probe: runtimeProbe,
    });
  }
  console.log(`STARTUP_REQUIRED_CALLABLE_RESOLVER ${JSON.stringify({
    schema_version: "startup_required_callable_resolver_diag_v1",
    rows: requiredCallableRows,
  })}`);
}

// Build startup binding map only after resolver completion.
const startupBindingMapFunctionAugmentation =
  augmentStartupBindingMapArtifactWithContractConstPoolFunctions({
    mapArtifact: startupBindingMapArtifact,
    contract: BOOTSTRAP_L0_CONTRACT_V1,
    resolver: bootstrapFunctionResolver,
  });
if (startupBindingMapFunctionAugmentation?.mapArtifact) {
  startupBindingMapArtifact = startupBindingMapFunctionAugmentation.mapArtifact;
}
if (startupBindingMapFunctionAugmentation?.changed) {
  startupBindingMapSource = `${startupBindingMapSource}+contract-required-const-pool-functions`;
}
startupBindingMapBuildSummary = buildStartupBindingMapBuildSummary({
  mapArtifact: startupBindingMapArtifact,
  mapSource: startupBindingMapSource,
  contract: BOOTSTRAP_L0_CONTRACT_V1,
});
console.log(`STARTUP_BINDING_MAP_BUILD ${JSON.stringify(startupBindingMapBuildSummary)}`);
if (process.env.CCL_WASM_DIAG_REQUIRED_CALLABLE_BINDINGS === "1") {
  const requiredCallableKeys = new Set(
    (Array.isArray(BOOTSTRAP_L0_CONTRACT_V1?.requiredCallables) ? BOOTSTRAP_L0_CONTRACT_V1.requiredCallables : [])
      .map((item) => `${String(item?.packageName ?? "").trim().toUpperCase()}::${String(item?.symbolName ?? "").trim().toUpperCase()}`)
      .filter((key) => key !== "::"),
  );
  const requiredCallableRows = [];
  for (const entry of Array.isArray(startupBindingMapArtifact?.entries) ? startupBindingMapArtifact.entries : []) {
    const packageName = String(entry?.package_name ?? "").trim().toUpperCase();
    const symbolName = String(entry?.symbol_name ?? "").trim().toUpperCase();
    if (!packageName || !symbolName) continue;
    const symbolKey = `${packageName}::${symbolName}`;
    if (!requiredCallableKeys.has(symbolKey)) continue;
    requiredCallableRows.push({
      symbol_key: symbolKey,
      target_cell: String(entry?.target_cell ?? "").trim().toLowerCase() || null,
      binding_class: String(entry?.binding_class ?? "").trim().toLowerCase() || null,
      availability: String(entry?.availability ?? "").trim().toLowerCase() || null,
      required_class: String(entry?.definition?.required_class ?? entry?.required_class ?? "").trim().toLowerCase() || null,
      initializer_kind: String(entry?.initializer?.kind ?? "").trim().toLowerCase() || null,
      initializer_entry_index: Number.isInteger(entry?.initializer?.entry_index)
        ? (entry.initializer.entry_index >>> 0)
        : null,
      source: typeof entry?.source === "string" ? entry.source : null,
    });
  }
  const presentRequiredKeys = new Set(requiredCallableRows.map((row) => row.symbol_key));
  const missingRequiredKeys = Array.from(requiredCallableKeys.values()).filter((key) => !presentRequiredKeys.has(key));
  console.log(`STARTUP_REQUIRED_CALLABLE_BINDINGS ${JSON.stringify({
    schema_version: "startup_required_callable_bindings_diag_v1",
    source: startupBindingMapSource,
    total_rows: requiredCallableRows.length >>> 0,
    rows: requiredCallableRows,
    missing_required_callable_keys: missingRequiredKeys,
  })}`);
}
buildStartupBindingMapConstPoolBindingIndex(startupBindingMapArtifact);
const startupBindingMapPreinstallPlan = planStartupBindingMapPreinstallConstPools({
  contract: BOOTSTRAP_L0_CONTRACT_V1,
  mapArtifact: startupBindingMapArtifact,
});
let startupBindingMapPreinstallInstalled = 0;
let startupBindingMapPreinstallMissing = 0;
if (startupBindingMapPreinstallPlan.summary?.status !== "ok") {
  const startupBindingMapPreinstallSummary = {
    ...startupBindingMapPreinstallPlan.summary,
    requested_count: startupBindingMapPreinstallPlan.entryIndices.length >>> 0,
    installed_count: startupBindingMapPreinstallInstalled >>> 0,
    missing_count: startupBindingMapPreinstallMissing >>> 0,
  };
  console.error(`STARTUP_BINDING_MAP_PREINSTALL ${JSON.stringify(startupBindingMapPreinstallSummary)}`);
  fail(`pre-fasload startup binding map preinstall failed: ${startupBindingMapPreinstallPlan.summary?.reason ?? "invalid-plan"}`);
}
for (const entryIndex of startupBindingMapPreinstallPlan.entryIndices) {
  if (installConstPoolOnDemand(entryIndex >>> 0) === 1) {
    startupBindingMapPreinstallInstalled++;
  } else {
    startupBindingMapPreinstallMissing++;
  }
}
for (const installedEntryIndex of Array.from(constPoolsInstalled.values()).sort((a, b) => a - b)) {
  applyStartupBindingMapDeferredBindingsForConstPoolEntry(installedEntryIndex, {
    reason: "startup-map-index-backfill",
  });
}
const startupBindingMapPreinstallSummary = {
  ...startupBindingMapPreinstallPlan.summary,
  requested_count: startupBindingMapPreinstallPlan.entryIndices.length >>> 0,
  installed_count: startupBindingMapPreinstallInstalled >>> 0,
  missing_count: startupBindingMapPreinstallMissing >>> 0,
};
console.log(`STARTUP_BINDING_MAP_PREINSTALL ${JSON.stringify(startupBindingMapPreinstallSummary)}`);

const startupBindingMapApplySummary = applyStartupBindingMapOrFail({
  mapArtifact: startupBindingMapArtifact,
  mapSource: startupBindingMapSource,
  contract: BOOTSTRAP_L0_CONTRACT_V1,
});
assertL0BootstrapContractOrFail(BOOTSTRAP_L0_CONTRACT_V1);
setBootPhaseOrFail(WASM_BOOT_PHASE.L0_READY, { reason: "pre-fasload-contract-pass" });

const runBoundaryProbes = process.env.CCL_WASM_RUN_BOUNDARY_PROBES === "1";
const boundaryProbeOnly = process.env.CCL_WASM_BOUNDARY_PROBE_ONLY === "1";
const boundaryProbeStrict = process.env.CCL_WASM_BOUNDARY_PROBES_STRICT === "1";
if (runBoundaryProbes) {
  if (typeof ex.wasm_probe_foreign_call1 !== "function") {
    fail("kernel missing wasm_probe_foreign_call1 for boundary probes");
  }
  const runBoundaryProbe = (name, mode, arg) => {
    if (typeof ex.wasm_clear_pending_throw === "function") {
      ex.wasm_clear_pending_throw();
    }
    const bytes = encoder.encode(arg);
    const ptr = copyBytesToScratch(runtime.memory, bytes);
    const rc = ex.wasm_probe_foreign_call1(mode >>> 0, ptr, bytes.length >>> 0) | 0;
    const pending = pendingThrowProbe ? pendingThrowProbe() : null;
    const pendingRaw = pendingThrowRawProbe ? pendingThrowRawProbe() : null;
    const pendingName = pendingRaw != null && kernelDebugSymbolName ? kernelDebugSymbolName(pendingRaw) : null;
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
const requiredFasloadQueue = skipRequiredFasloads ? [] : requiredFasls;
for (let faslIndex = 0; faslIndex < requiredFasloadQueue.length; faslIndex++) {
  const faslPath = requiredFasloadQueue[faslIndex];
  if (traceEnabled && pendingThrowProbe) {
    trace(`fasload pre path=${faslPath} pending=${pendingThrowProbe()}`);
  }
  if (typeof subex.wasm_debug_reset_specref_failure === "function") {
    subex.wasm_debug_reset_specref_failure();
  }
  const faslBytes = encoder.encode(faslPath);
  const faslPtr = copyBytesToScratch(runtime.memory, faslBytes);
  let faslRc = 0;
  try {
    faslRc = ex.wasm_fasload_path(faslPtr, faslBytes.length >>> 0) | 0;
  } catch (err) {
    const specrefDiag = debugReadSpecrefFailure(`fasload trap path=${faslPath}`);
    const unresolvedFunction = classifyBoundaryUnresolvedFunction(specrefDiag);
    const boundaryReason = unresolvedFunction
      ? "required-fasload-unresolved-function-symbol-after-unified-startup-binding-map-apply"
      : "required-fasload-trap-after-unified-startup-binding-map-apply";
    const pending = pendingThrowProbe ? pendingThrowProbe() : null;
    const pendingRaw = pendingThrowRawProbe ? pendingThrowRawProbe() : null;
    const pendingSymbol = pendingRaw != null && kernelDebugSymbolName ? kernelDebugSymbolName(pendingRaw) : null;
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
      startup_binding_map: {
        source: startupBindingMapSource,
        build: startupBindingMapBuildSummary,
        apply: startupBindingMapApplySummary,
      },
    })}`);
    fail(`wasm_fasload_path(${faslPath}) trapped: ${err?.message ?? err}`);
  }
  if (traceEnabled && pendingThrowProbe) {
    const pendingRaw = pendingThrowRawProbe ? pendingThrowRawProbe() : null;
    const pendingName = pendingRaw != null && kernelDebugSymbolName ? kernelDebugSymbolName(pendingRaw) : null;
    trace(
      `fasload post path=${faslPath} rc=${faslRc} pending=${pendingThrowProbe()}` +
      (pendingRaw == null ? "" : ` pending_raw=0x${pendingRaw.toString(16)}`) +
      (pendingName ? ` pending_symbol=${JSON.stringify(pendingName)}` : ""),
    );
  }
  if (faslRc !== 0) {
    const specrefDiag = debugReadSpecrefFailure(`fasload rc=${faslRc} path=${faslPath}`);
    const unresolvedFunction = classifyBoundaryUnresolvedFunction(specrefDiag);
    const boundaryReason = unresolvedFunction
      ? "required-fasload-unresolved-function-symbol-after-unified-startup-binding-map-apply"
      : "required-fasload-failed-after-unified-startup-binding-map-apply";
    const pending = pendingThrowProbe ? pendingThrowProbe() : null;
    const pendingRaw = pendingThrowRawProbe ? pendingThrowRawProbe() : null;
    const pendingSymbol = pendingRaw != null && kernelDebugSymbolName ? kernelDebugSymbolName(pendingRaw) : null;
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
      startup_binding_map: {
        source: startupBindingMapSource,
        build: startupBindingMapBuildSummary,
        apply: startupBindingMapApplySummary,
      },
    })}`);
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
          const subtag = typeof ex.wasm_debug_misc_subtag === "function"
            ? (ex.wasm_debug_misc_subtag(value >>> 0) | 0)
            : null;
          const symbolName = kernelDebugSymbolName ? kernelDebugSymbolName(value >>> 0) : null;
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
        const subtag = typeof ex.wasm_debug_misc_subtag === "function"
          ? (ex.wasm_debug_misc_subtag(value >>> 0) | 0)
          : null;
        const symbolName = kernelDebugSymbolName ? kernelDebugSymbolName(value >>> 0) : null;
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
        const diagPathBytes = encoder.encode(diagPath);
        const diagPathPtr = copyBytesToScratch(runtime.memory, diagPathBytes);
        const diagRc = ex.wasm_run_script_with_output(diagPathPtr, diagPathBytes.length >>> 0, 0, 0) | 0;
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
      startup_binding_map: {
        source: startupBindingMapSource,
        build: startupBindingMapBuildSummary,
        apply: startupBindingMapApplySummary,
      },
    })}`);
  }
}
if (!skipRequiredFasloads && requiredFasls.length > 0) {
  setBootPhaseOrFail(WASM_BOOT_PHASE.RUNTIME, { reason: "post-required-fasload-boundary" });
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
