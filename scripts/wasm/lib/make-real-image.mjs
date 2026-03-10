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

const FT_NAMES = ["fix", "nil", "nhdr", "imm", "fix", "cons", "misc", "ihdr"];
const FULLTAG_CONS = 0x5;
const FULLTAG_MISC = 0x6;
const SUBTAG_PSEUDOFUNCTION = 0x02;
const SUBTAG_MACPTR = 0x1F;
const SUBTAG_FUNCTION = 0x2A;
const SUBTAG_SYMBOL = 0x3A;
const SUBTAG_HASH_VECTOR = 0x4A;
const SUBTAG_SGS = 0x5A;
const SUBTAG_PACKAGE = 0x62;
const SUBTAG_ISTRUCT = 0x82;
const SUBTAG_XFUNCTION = 0x92;
const SUBTAG_SBS = 0xBF;
const SUBTAG_SIMPLE_VECTOR = 0xFA;
const SUBTAG_NAMES = {
  [SUBTAG_PSEUDOFUNCTION]: "pseudofn",
  [SUBTAG_FUNCTION]: "function",
  [SUBTAG_SYMBOL]: "symbol",
  [SUBTAG_HASH_VECTOR]: "hash-vec",
  [SUBTAG_SGS]: "string",
  [SUBTAG_PACKAGE]: "package",
  [SUBTAG_ISTRUCT]: "istruct",
  [SUBTAG_XFUNCTION]: "xfunction",
  [SUBTAG_SBS]: "string",
  [SUBTAG_SIMPLE_VECTOR]: "simple-vector",
};

function createRuntimeObjectReader(memory, { compiledFunctionByEntryIndex = null, nilValue = null } = {}) {
  const inBounds = (ptr) => Number.isFinite(ptr) && ptr >= 0x100 && ptr < memory.buffer.byteLength;
  const isFixnum = (value) => (value & 0x3) === 0;

  function dv() {
    return new DataView(memory.buffer);
  }

  function descMisc(ptr) {
    if ((ptr & 0x7) !== FULLTAG_MISC || !inBounds(ptr)) return null;
    const header = dv().getUint32(ptr - FULLTAG_MISC, true);
    const st = header & 0xFF;
    return {
      ptr: ptr >>> 0,
      header: header >>> 0,
      st,
      cnt: header >>> 8,
      name: SUBTAG_NAMES[st] ?? `st=0x${st.toString(16)}`,
    };
  }

  function readMiscElement(ptr, index) {
    const info = descMisc(ptr);
    if (!info || index < 0 || index >= info.cnt) return null;
    return dv().getUint32(ptr - 2 + index * 4, true) >>> 0;
  }

  function readCons(ptr) {
    if ((ptr & 0x7) !== FULLTAG_CONS || !inBounds(ptr & ~0x7)) return null;
    const base = ptr & ~0x7;
    return {
      car: dv().getUint32(base + 4, true) >>> 0,
      cdr: dv().getUint32(base, true) >>> 0,
    };
  }

  function readBaseString(ptr) {
    const info = descMisc(ptr);
    if (!info || (info.st !== SUBTAG_SBS && info.st !== SUBTAG_SGS)) return null;
    const chars = [];
    const reader = dv();
    const dataStart = ptr - 2;
    for (let i = 0; i < Math.min(info.cnt, 128); i++) {
      const word = reader.getUint32(dataStart + i * 4, true);
      const ch = info.st === SUBTAG_SBS ? (word & 0xFF) : (word & 0xFFFF);
      if (ch === 0) break;
      chars.push(ch);
    }
    if (chars.length > 0) return String.fromCharCode(...chars);
    if (info.st === SUBTAG_SBS) {
      const bytes = new Uint8Array(memory.buffer, dataStart, Math.min(info.cnt, 128));
      return String.fromCharCode(...bytes.filter((b) => b !== 0));
    }
    return "";
  }

  function readSymbolName(symPtr) {
    const info = descMisc(symPtr);
    if (!info || info.st !== SUBTAG_SYMBOL) return null;
    const pname = readMiscElement(symPtr, 0);
    return pname == null ? null : readBaseString(pname);
  }

  function readFunctionEntryIndex(fnPtr) {
    const info = descMisc(fnPtr);
    if (!info || ![SUBTAG_FUNCTION, SUBTAG_PSEUDOFUNCTION, SUBTAG_XFUNCTION].includes(info.st)) {
      return null;
    }
    const rawEntry = readMiscElement(fnPtr, 0);
    if (rawEntry == null || !isFixnum(rawEntry)) return null;
    return rawEntry >>> 2;
  }

  function readFunctionName(fnPtr) {
    const info = descMisc(fnPtr);
    if (!info || ![SUBTAG_FUNCTION, SUBTAG_PSEUDOFUNCTION, SUBTAG_XFUNCTION].includes(info.st)) {
      return null;
    }
    if (info.cnt >= 4) {
      const lfunInfo = readMiscElement(fnPtr, 3);
      if ((lfunInfo & 0x7) === FULLTAG_MISC && inBounds(lfunInfo)) {
        const lfunHdr = dv().getUint32(lfunInfo - FULLTAG_MISC, true);
        const lfunSubtag = lfunHdr & 0xFF;
        if (lfunSubtag === SUBTAG_SYMBOL) {
          return readSymbolName(lfunInfo);
        }
        if (lfunSubtag === SUBTAG_SIMPLE_VECTOR) {
          const nameSlot = readMiscElement(lfunInfo, 0);
          if ((nameSlot & 0x7) === FULLTAG_MISC) {
            return readSymbolName(nameSlot);
          }
        }
      }
    }
    const entryIndex = readFunctionEntryIndex(fnPtr);
    const bundleFn = entryIndex != null ? compiledFunctionByEntryIndex?.get(entryIndex) : null;
    return bundleFn?.name ?? null;
  }

  function readSymbolFunctionEntryIndex(symPtr) {
    const info = descMisc(symPtr);
    if (!info || info.st !== SUBTAG_SYMBOL) return null;
    const fcell = readMiscElement(symPtr, 2);
    return fcell == null ? null : readFunctionEntryIndex(fcell);
  }

  function readPackageName(pkgPtr) {
    const info = descMisc(pkgPtr);
    if (!info || info.st !== SUBTAG_PACKAGE || info.cnt === 0) return null;
    for (let i = 0; i < Math.min(info.cnt, 8); i++) {
      const slot = readMiscElement(pkgPtr, i);
      if ((slot & 0x7) !== FULLTAG_CONS) continue;
      const head = readCons(slot)?.car ?? 0;
      const name = readBaseString(head) ?? readSymbolName(head);
      if (name) return name;
    }
    return null;
  }

  function describeValue(value, depth = 0) {
    const raw = value >>> 0;
    if (nilValue != null && raw === (nilValue >>> 0)) return "NIL";
    if (isFixnum(raw)) return `fixnum=${raw >> 2}`;
    const ft = raw & 0x7;
    if (ft === FULLTAG_CONS) {
      if (depth > 0) return `cons@0x${raw.toString(16)}`;
      const cell = readCons(raw);
      if (!cell) return `cons@0x${raw.toString(16)}`;
      return `cons(car=${describeValue(cell.car, depth + 1)}, cdr=${describeValue(cell.cdr, depth + 1)})`;
    }
    if (ft !== FULLTAG_MISC) return `0x${raw.toString(16)}`;
    const info = descMisc(raw);
    if (!info) return `misc@0x${raw.toString(16)}`;
    switch (info.st) {
      case SUBTAG_SBS:
      case SUBTAG_SGS: {
        const text = readBaseString(raw);
        return `string ${JSON.stringify(text ?? "")}`;
      }
      case SUBTAG_SYMBOL:
        return `symbol ${readSymbolName(raw) ?? `@0x${raw.toString(16)}`}`;
      case SUBTAG_FUNCTION:
      case SUBTAG_PSEUDOFUNCTION:
      case SUBTAG_XFUNCTION: {
        const entryIndex = readFunctionEntryIndex(raw);
        const name = readFunctionName(raw);
        return `${info.name} ${name ?? `@0x${raw.toString(16)}`}` +
          (entryIndex != null ? ` entry=${entryIndex}` : "");
      }
      case SUBTAG_PACKAGE:
        return `package ${readPackageName(raw) ?? `@0x${raw.toString(16)}`}`;
      default:
        return `${info.name} cnt=${info.cnt}`;
    }
  }

  function dumpFunction(fnPtr, label, maxElems = 8) {
    const info = descMisc(fnPtr);
    if (!info || ![SUBTAG_FUNCTION, SUBTAG_PSEUDOFUNCTION, SUBTAG_XFUNCTION].includes(info.st)) return;
    const name = readFunctionName(fnPtr);
    const entryIndex = readFunctionEntryIndex(fnPtr);
    console.error(
      `[${label}] 0x${fnPtr.toString(16)} ${info.name} count=${info.cnt}` +
      (name ? ` name=${name}` : "") +
      (entryIndex != null ? ` entry=${entryIndex}` : ""),
    );
    for (let i = 0; i < Math.min(info.cnt, maxElems); i++) {
      const elem = readMiscElement(fnPtr, i);
      console.error(
        `    [${i}] 0x${elem.toString(16).padStart(8, "0")} ` +
        `(${describeValue(elem, 1)})`,
      );
    }
  }

  function dumpObjectSlots(ptr, label, maxElems = 8) {
    const info = descMisc(ptr);
    if (!info || info.cnt === 0) return;
    console.error(`[${label}] 0x${ptr.toString(16)} ${info.name} count=${info.cnt}`);
    for (let i = 0; i < Math.min(info.cnt, maxElems); i++) {
      const elem = readMiscElement(ptr, i);
      console.error(`    [${i}] 0x${elem.toString(16).padStart(8, "0")} (${describeValue(elem, 1)})`);
    }
  }

  function describeCallable(ptr) {
    const info = descMisc(ptr);
    if (!info) {
      return { ptr: ptr >>> 0, kind: "other", name: null, entryIndex: null, summary: describeValue(ptr) };
    }
    if (info.st === SUBTAG_SYMBOL) {
      return {
        ptr: ptr >>> 0,
        kind: "symbol",
        name: readSymbolName(ptr),
        entryIndex: readSymbolFunctionEntryIndex(ptr),
        summary: describeValue(ptr),
      };
    }
    if ([SUBTAG_FUNCTION, SUBTAG_PSEUDOFUNCTION, SUBTAG_XFUNCTION].includes(info.st)) {
      return {
        ptr: ptr >>> 0,
        kind: info.name,
        name: readFunctionName(ptr),
        entryIndex: readFunctionEntryIndex(ptr),
        summary: describeValue(ptr),
      };
    }
    return {
      ptr: ptr >>> 0,
      kind: info.name,
      name: null,
      entryIndex: null,
      summary: describeValue(ptr),
    };
  }

  return {
    descMisc,
    describeCallable,
    describeValue,
    dumpFunction,
    dumpObjectSlots,
    readCons,
    readMiscElement,
    readFunctionEntryIndex,
    readFunctionName,
    readPackageName,
    readSymbolName,
  };
}

function dumpFasloadFailureContext({
  ex,
  runtime,
  faslPath,
  label,
  detail,
  compiledFunctionByEntryIndex,
}) {
  const mem = runtime.memory;
  const inspect = createInspector(ex, mem);
  const nilValue = typeof ex.wasm_get_lisp_nil === "function" ? (ex.wasm_get_lisp_nil() >>> 0) : null;
  const reader = createRuntimeObjectReader(mem, { compiledFunctionByEntryIndex, nilValue });

  console.error(`[${label}] ${faslPath}: ${detail}`);
  inspect.dumpAll();

  const regs = [
    ["arg_x", 6],
    ["arg_y", 5],
    ["arg_z", 4],
    ["nfn", 9],
    ["Rfn", 11],
  ];
  for (const [name, index] of regs) {
    const value = inspect.getGPR(index) >>> 0;
    console.error(`[${label}] ${name}=0x${value.toString(16).padStart(8, "0")} (${reader.describeValue(value)})`);
  }

  reader.dumpFunction(inspect.getGPR(9) >>> 0, `${label} nfn`);
  reader.dumpFunction(inspect.getGPR(11) >>> 0, `${label} Rfn`);

  for (const [name, index] of [["arg_x", 6], ["arg_y", 5], ["arg_z", 4]]) {
    const value = inspect.getGPR(index) >>> 0;
    reader.dumpObjectSlots(value, `${label} ${name}`, 8);
  }

  if (typeof ex.wasm_lookup_symbol_value === "function") {
    const debugSymbols = [
      "*%WASM-FASLOAD-CURRENT-FILE%*",
      "*%WASM-FASLOAD-CURRENT-BLOCK%*",
      "*%WASM-FASLOAD-CURRENT-OP%*",
      "*%WASM-FASLOAD-CURRENT-POS%*",
      "*%WASM-FASLOAD-CURRENT-VERSION%*",
      "*%WASM-FASLOAD-CURRENT-DISPATCH%*",
      "*%WASM-FASLOAD-CURRENT-EVEC-COUNT%*",
      "*%WASM-FASLOAD-CURRENT-VALUE%*",
      "*%WASM-FASLOAD-CURRENT-LFUNCALL-TARGET%*",
      "*%WASM-FASLOAD-CURRENT-LFUNCALL-RESULT%*",
      "*COMMON-LISP-PACKAGE*",
      "*CCL-PACKAGE*",
      "%ALL-PACKAGES%",
      "*%WASM-LAST-ENSURE-SIMPLE-STRING-ARG%*",
      "*%WASM-LAST-ADD-SYMBOL-PNAME%*",
      "*%WASM-LAST-ADD-SYMBOL-PACKAGE%*",
      "*%WASM-LAST-ADD-SYMBOL-INTERNAL-IDX%*",
      "*%WASM-LAST-ADD-SYMBOL-EXTERNAL-IDX%*",
      "*%WASM-LAST-ADD-SYMBOL-FORCE-EXPORT%*",
    ];
    sharedProbeUtf8Scratch.reset();
    let currentLfuncallTarget = 0;
    for (const symbolName of debugSymbols) {
      const symMem = sharedProbeUtf8Scratch.allocUtf8(symbolName, encoder);
      const value = ex.wasm_lookup_symbol_value(symMem.ptr >>> 0, symMem.len >>> 0) >>> 0;
      if (value === 0) continue;
      console.error(`[${label}] ${symbolName}=0x${value.toString(16).padStart(8, "0")} (${reader.describeValue(value)})`);
      reader.dumpFunction(value, `${label} ${symbolName}`, 8);
      reader.dumpObjectSlots(value, `${label} ${symbolName}`, 8);
      if (symbolName === "*%WASM-FASLOAD-CURRENT-LFUNCALL-TARGET%*") {
        currentLfuncallTarget = value >>> 0;
      }
    }
    const targetEntryIndex = reader.readFunctionEntryIndex(currentLfuncallTarget);
    if (targetEntryIndex != null && typeof ex.wasm_const_pool_ref === "function") {
      console.error(`[${label}] lfuncall target const-pool entry=${targetEntryIndex}`);
      for (let slot = 0; slot < 24; slot++) {
        try {
          const value = ex.wasm_const_pool_ref(targetEntryIndex >>> 0, slot >>> 0) >>> 0;
          console.error(
            `    [${slot}] 0x${value.toString(16).padStart(8, "0")} ` +
            `(${reader.describeValue(value)})`,
          );
          reader.dumpObjectSlots(value, `${label} lfuncall-target const[${slot}]`, 6);
        } catch (e) {
          console.error(
            `    [${slot}] TRAP ${(e?.constructor?.name ?? "Error")}: ${(e?.message ?? "").slice(0, 120)}`,
          );
          break;
        }
      }
    }
  }

  const spillSp = inspect.getField("wasm_spill_sp");
  const spillLimit = inspect.getField("wasm_spill_limit");
  const spillUsed = (spillLimit - spillSp) / 4;
  console.error(`[${label}] spill stack symbols/functions:`);
  for (let i = 0; i < Math.min(40, spillUsed); i++) {
    const addr = spillSp + i * 4;
    const word = new DataView(mem.buffer).getUint32(addr, true) >>> 0;
    const callable = reader.describeCallable(word);
    if (callable.name) {
      console.error(`    [${i}] 0x${addr.toString(16)} ${callable.kind} ${callable.name}`);
    }
  }

  const vsp = inspect.getGPR(10) >>> 0;
  console.error(`[${label}] first VSP words:`);
  for (let i = 0; i < 8; i++) {
    const addr = vsp + i * 4;
    if (addr + 4 > mem.buffer.byteLength) break;
    const word = new DataView(mem.buffer).getUint32(addr, true) >>> 0;
    const info = reader.descMisc(word);
    const miscDetail = info ? ` st=0x${info.st.toString(16)} cnt=${info.cnt}` : "";
    console.error(
      `    [${i}] 0x${addr.toString(16)} = 0x${word.toString(16).padStart(8, "0")} ` +
      `(${reader.describeValue(word)})${miscDetail}`,
    );
    reader.dumpObjectSlots(word, `${label} vsp[${i}]`, 6);
  }
  for (let off = 0; off < 256; off += 4) {
    const addr = vsp + off;
    if (addr + 4 > mem.buffer.byteLength) break;
    const word = new DataView(mem.buffer).getUint32(addr, true) >>> 0;
    const info = reader.descMisc(word);
    if (info && info.st === SUBTAG_ISTRUCT && info.cnt === 15) {
      console.error(`[${label}] faslstate @0x${word.toString(16)} (vsp+${off})`);
      reader.dumpObjectSlots(word, `${label} faslstate`, 15);
      break;
    }
  }
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

/* Set the runtime nil value in subprims.  The compile-time nil_value constant
   (0x04000001 from arm-constants.h) does not match the runtime lisp_nil address
   in WASM linear memory.  Must be called before any subprim execution. */
if (typeof subprims.instance.exports.wasm_set_subprims_nil === "function") {
  const nilVal = ex.wasm_get_lisp_nil() >>> 0;
  console.error(`[stage] setting subprims nil to 0x${nilVal.toString(16)}`);
  subprims.instance.exports.wasm_set_subprims_nil(nilVal);
} else {
  console.error("[stage] WARNING: wasm_set_subprims_nil not found in subprims exports");
}

/* Mark subprims ready so RESTORE-LISP-POINTERS (and fasload) can dispatch
   through the subprim table. */
if (typeof ex.wasm_set_subprims_ready === "function") {
  ex.wasm_set_subprims_ready(1);
}
if (typeof ex.wasm_restore_lisp_pointers !== "function") {
  fail("kernel missing wasm_restore_lisp_pointers");
}
/* RESTORE-LISP-POINTERS is NOT called here.  The function object exists in
   the boot image's fcell but its WASM function table entry has not been
   populated yet (compiled modules are loaded later).  Calling it now would
   trap with "table index is out of bounds".
   The boot image's hash tables are freshly built and valid — no rehash needed.
   We call RESTORE-LISP-POINTERS after fasls are loaded (post-fasload). */
trace("RESTORE-LISP-POINTERS deferred to post-fasload (function table not yet populated)");

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
      clearEntryFnCache: true,
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
  installConstPools: false,
  excludeEntries: bootEntryIndices.size > 0 ? bootEntryIndices : null,
});
/* Runtime const pools stay deferred/on-demand.  Installing them here runs in
   EARLY boot and can still synthesize non-canonical symbol objects for
   package/function designators.  Cold-boot/FASL code installs pools on demand,
   and the remaining pools are materialized later once startup is canonical. */
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

const compiledFunctionByEntryIndex = new Map();
for (const fn of [
  ...bootNamedFunctions,
  ...(Array.isArray(compiledModulesBundle?.functions) ? compiledModulesBundle.functions : []),
]) {
  if (!Number.isFinite(fn?.entryIndex)) continue;
  compiledFunctionByEntryIndex.set(fn.entryIndex >>> 0, fn);
}

function maxEntryIndexByName(functions) {
  const maxByName = new Map();
  for (const fn of functions) {
    if (!fn?.name || !Number.isFinite(fn.entryIndex)) continue;
    const entryIndex = fn.entryIndex >>> 0;
    const prev = maxByName.get(fn.name);
    if (prev == null || entryIndex > prev) {
      maxByName.set(fn.name, entryIndex);
    }
  }
  return maxByName;
}

const bootNamedFunctionMaxEntryByName = maxEntryIndexByName(bootNamedFunctions);
const runtimeNamedFunctionMaxEntryByName = maxEntryIndexByName(
  Array.isArray(compiledModulesBundle?.functions) ? compiledModulesBundle.functions : [],
);

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
    const newSlots = Number.isFinite(e?.fnSlots) ? e.fnSlots : 3;
    const existing = rebindMap.get(e.name);
    // Keep the entry with the highest fnSlots — duplicate entries without
    // fnSlots (defaulting to 3) must not overwrite one that has the real count.
    if (existing && existing.fnSlots >= newSlots && existing.entryIndex === e.entryIndex) continue;
    rebindMap.set(e.name, {
      entryIndex: e.entryIndex,
      fnSlots: existing ? Math.max(existing.fnSlots, newSlots) : newSlots,
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
    const seenNames = new Set();
    let duplicateMatches = 0;

    for (let w = scanStart; w < totalWords; w += 2) {
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

      const info = rebindMap.get(name);
      if (info === undefined) continue;
      if (seenNames.has(name)) {
        duplicateMatches++;
      } else {
        seenNames.add(name);
      }
      const entryIdx = info.entryIndex;
      const fnSlots = info.fnSlots;

      // Read the symbol's fcell (word +3 from header)
      const fcellTagged = mem32[w + 3];
      if ((fcellTagged & 7) !== FULLTAG_MISC) { skippedNoFn++; continue; }
      const fnUntagged = (fcellTagged - FULLTAG_MISC) >>> 0;
      const fnWordIdx = fnUntagged >>> 2;
      if (fnWordIdx < 1 || fnWordIdx >= totalWords - 1) { skippedNoFn++; continue; }

      const fnHdr = mem32[fnWordIdx];
      const fnSubtag = fnHdr & 0xFF;

      if (fnSubtag === SUBTAG_FUNCTION) {
        const existingCount = fnHdr >>> 8;
        if (existingCount >= fnSlots) {
          // Existing function object has enough slots: patch entry points in place
          mem32[fnWordIdx + 1] = entryIdx << 2;  // slot 0: entrypoint (fixnum)
          mem32[fnWordIdx + 2] = entryIdx << 2;  // slot 1: code vector (fixnum)
          patched++;
        } else if (miscAllocFn) {
          // Existing function too small (e.g. 3-slot UDF stub for a closure that
          // needs 7+ slots for closed-over variables).  Allocate correctly-sized
          // replacement so compiled WASM code can access nfn[3+] safely.
          const fnTagged = miscAllocFn(SUBTAG_FUNCTION, fnSlots);
          if (fnTagged !== 0 && (fnTagged & 7) === FULLTAG_MISC) {
            const m = new Uint32Array(runtime.memory.buffer);
            const fw = ((fnTagged - FULLTAG_MISC) >>> 0) >>> 2;
            m[fw + 1] = entryIdx << 2;   // slot 0: entrypoint (fixnum)
            m[fw + 2] = entryIdx << 2;   // slot 1: code vector (fixnum)
            // Copy any existing slots beyond 0,1 (e.g. lfun-info, lfun-bits)
            for (let s = 2; s < existingCount && s < fnSlots; s++) {
              m[fw + 1 + s] = mem32[fnWordIdx + 1 + s];
            }
            m[w + 3] = fnTagged;          // patch symbol fcell
            allocated++;
          } else {
            // Allocation failed — patch in place as best we can
            mem32[fnWordIdx + 1] = entryIdx << 2;
            mem32[fnWordIdx + 2] = entryIdx << 2;
            patched++;
          }
        } else {
          // No allocator — patch in place as best we can
          mem32[fnWordIdx + 1] = entryIdx << 2;
          mem32[fnWordIdx + 2] = entryIdx << 2;
          patched++;
        }
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
    }
    const unmatched = rebindMap.size - seenNames.size;
    console.error(
      `[stage] image fixup: ${patched} in-place + ${allocated} new-alloc / ${rebindMap.size} total ` +
      `(${symbolCount} syms, ${skippedNoFn} skipped, ${duplicateMatches} duplicates, ${unmatched} unmatched)`,
    );

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

/* Diagnostic: check a few FASL-referenced entry indices in the function table */
{
  const table = runtime.subprimsTable;
  const trapFn = subprims.instance.exports._SPentry_not_installed;
  const testEntries = [1492, 1493, 1494, 1495, 202, 215, 979, 1000];
  for (const idx of testEntries) {
    if (idx >= table.length) {
      console.error(`[table-check] entry ${idx}: OUT OF BOUNDS (table.length=${table.length})`);
    } else {
      const fn = table.get(idx);
      const isTrap = fn === trapFn;
      const isNull = fn === null;
      console.error(`[table-check] entry ${idx}: ${isNull ? "NULL" : isTrap ? "TRAP STUB" : typeof fn === "function" ? "INSTALLED" : String(fn)}`);
    }
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
const COLD_LOAD_C_MAX = 128;
const COLD_LOAD_MAX_PASSES = 5;
const PRE_FASL_JS_ENTRY_NAMES = new Set();
const DISALLOWED_LOCK_CALLABLE_NAMES = new Set(["RECURSIVE-LOCK-PTR", "READ-WRITE-LOCK-PTR"]);
const protectedBootSymbolSpecs = [
  { lookupNames: ["%LOCK-RECURSIVE-LOCK-PTR"], manifestName: "%LOCK-RECURSIVE-LOCK-PTR" },
  { lookupNames: ["%UNLOCK-RECURSIVE-LOCK-PTR"], manifestName: "%UNLOCK-RECURSIVE-LOCK-PTR" },
  { lookupNames: ["%LOCK-RECURSIVE-LOCK-OBJECT"], manifestName: "%LOCK-RECURSIVE-LOCK-OBJECT" },
  { lookupNames: ["%UNLOCK-RECURSIVE-LOCK-OBJECT"], manifestName: "%UNLOCK-RECURSIVE-LOCK-OBJECT" },
  { lookupNames: ["%TRY-RECURSIVE-LOCK-OBJECT"], manifestName: "%TRY-RECURSIVE-LOCK-OBJECT" },
  { lookupNames: ["READ-LOCK-RWLOCK"], manifestName: "READ-LOCK-RWLOCK" },
  { lookupNames: ["WRITE-LOCK-RWLOCK"], manifestName: "WRITE-LOCK-RWLOCK" },
  { lookupNames: ["UNLOCK-RWLOCK"], manifestName: "UNLOCK-RWLOCK" },
  { lookupNames: ["%%LOCK-OWNER", "%LOCK-OWNER"], manifestName: "%%LOCK-OWNER" },
  { lookupNames: ["READ-LOCK-HASH-TABLE"], manifestName: "READ-LOCK-HASH-TABLE" },
  { lookupNames: ["WRITE-LOCK-HASH-TABLE"], manifestName: "WRITE-LOCK-HASH-TABLE" },
  { lookupNames: ["UNLOCK-HASH-TABLE"], manifestName: "UNLOCK-HASH-TABLE" },
];
const preFaslBootstrapAliasSpecs = [
  {
    symbolName: "PREPARE-TO-DESTRUCTURE",
    targetName: "%EARLY-PREPARE-TO-DESTRUCTURE",
  },
];
const protectedBootSymbolNames = new Set(
  protectedBootSymbolSpecs.map((spec) => spec.manifestName),
);
let coldLoadSkipSet = null;

function loadColdLoadSkipSet() {
  if (coldLoadSkipSet) {
    return coldLoadSkipSet;
  }
  coldLoadSkipSet = new Set();
  try {
    const skipPath = path.join(
      path.dirname(fileURLToPath(import.meta.url)),
      "../../../build/wasm32/cold-load-skip.txt",
    );
    const skipData = fsSync.readFileSync(skipPath, "utf8");
    for (const line of skipData.split("\n")) {
      const n = parseInt(line.trim(), 10);
      if (!Number.isNaN(n)) {
        coldLoadSkipSet.add(n);
      }
    }
  } catch {
    /* file missing = no skips */
  }
  return coldLoadSkipSet;
}

function coldLoadRange(startIndex, endIndex) {
  const indices = [];
  for (let i = startIndex; i < endIndex; i++) {
    indices.push(i);
  }
  return indices;
}

function dedupeIndices(indices) {
  return [...new Set(indices.filter((idx) => Number.isFinite(idx) && idx >= 0))];
}

function selectColdLoadEntriesByName(entries, names) {
  if (!(names instanceof Set) || names.size === 0) return [];
  return dedupeIndices(
    entries
      .filter((entry) => entry?.name && names.has(entry.name))
      .map((entry) => entry.index),
  ).sort((a, b) => a - b);
}

function drainColdLoadEntries({
  stageLabel,
  indices = null,
  startIndex = 0,
  endIndex = Number.MAX_SAFE_INTEGER,
  maxPasses = COLD_LOAD_MAX_PASSES,
}) {
  if (typeof ex.wasm_cold_load_count !== "function" ||
      typeof ex.wasm_cold_load_run_one !== "function") {
    console.error(`[stage] ${stageLabel}: cold-load JS helpers unavailable`);
    return null;
  }

  const total = ex.wasm_cold_load_count() | 0;
  const stopIndex = Math.min(total, endIndex);
  const initialPending = indices
    ? [...indices].filter((idx, pos, all) => idx >= 0 && idx < total && all.indexOf(idx) === pos)
    : coldLoadRange(startIndex, stopIndex);
  if (initialPending.length === 0) {
    console.error(`[stage] ${stageLabel}: no pending entries (snapshot=${total})`);
    return { total, attempted: 0, remaining: [] };
  }

  const skipSet = loadColdLoadSkipSet();
  const spEx = subprims.instance.exports;
  const hasFuel = typeof spEx.wasm_set_funcall_fuel === "function";
  let failed = initialPending;
  let totalOk = 0;
  let totalErr = 0;
  let totalTrapped = 0;
  let totalSkipped = 0;

  console.error(
    `[stage] ${stageLabel}: ${failed.length} entries pending (snapshot=${total}, skip=${skipSet.size}, hasFuel=${hasFuel})`,
  );

  for (let pass = 1; pass <= maxPasses && failed.length > 0; pass++) {
    let passOk = 0;
    let passErr = 0;
    let passTrapped = 0;
    let passSkipped = 0;
    const nextFailed = [];

    console.error(`[stage] ${stageLabel} pass ${pass}: starting ${failed.length} entries`);
    for (const idx of failed) {
      if (skipSet.has(idx)) {
        passSkipped++;
        continue;
      }
      try {
        if (hasFuel) {
          spEx.wasm_set_funcall_fuel(100000);
        }
        const rc = ex.wasm_cold_load_run_one(idx) | 0;
        if (hasFuel) {
          spEx.wasm_set_funcall_fuel(-1);
        }
        if (rc === 0) {
          passOk++;
        } else if (rc === 1) {
          passSkipped++;
        } else {
          passErr++;
          nextFailed.push(idx);
        }
      } catch (e) {
        if (hasFuel) {
          spEx.wasm_set_funcall_fuel(-1);
        }
        if (typeof ex.wasm_recover_after_trap === "function") {
          ex.wasm_recover_after_trap();
        }
        passTrapped++;
        nextFailed.push(idx);
      }
    }

    totalOk += passOk;
    totalErr += passErr;
    totalTrapped += passTrapped;
    totalSkipped += passSkipped;
    console.error(
      `[stage] ${stageLabel} pass ${pass}: ${passOk} ok, ${passErr} lisp-err, ${passTrapped} trapped, ${passSkipped} skipped`,
    );
    failed = nextFailed;
    if (passOk === 0) {
      break;
    }
  }

  console.error(
    `[stage] ${stageLabel}: ${totalOk} ok, ${totalErr} lisp-err, ${totalTrapped} trapped, ${totalSkipped} skipped, ${failed.length} remaining`,
  );
  return {
    total,
    attempted: initialPending.length,
    remaining: failed,
  };
}

function describeSymbolValue(name, value, reader) {
  return `${name}=${reader.describeValue(value)}`;
}

function bootstrapColdLoadUntilFaslApi({
  stageLabel,
  entries,
}) {
  if (typeof ex.wasm_cold_load_count !== "function" ||
      typeof ex.wasm_cold_load_run_one !== "function") {
    console.error(`[stage] ${stageLabel}: cold-load JS helpers unavailable`);
    return { attemptedIndices: [], completedIndices: [], remainingIndices: [] };
  }
  const faslApiValue = lookupSymbolValue("*FASL-API*");
  const nilValue = typeof ex.wasm_get_lisp_nil === "function"
    ? (ex.wasm_get_lisp_nil() >>> 0)
    : null;
  const reader = createRuntimeObjectReader(runtime.memory, { compiledFunctionByEntryIndex, nilValue });
  const faslApiReady = () => {
    const value = lookupSymbolValue("*FASL-API*");
    return value !== 0 && (nilValue == null || value !== nilValue);
  };
  const attemptedIndices = [];
  const completedIndices = [];
  const remainingIndices = [];
  let lispErrCount = 0;
  let trappedCount = 0;
  let skippedCount = 0;

  if (faslApiReady()) {
    console.error(
      `[stage] ${stageLabel}: already ready ` +
      `(${describeSymbolValue("*FASL-API*", faslApiValue, reader)})`,
    );
    return { attemptedIndices, completedIndices, remainingIndices };
  }

  const pendingEntries = [...entries].sort((a, b) => a.index - b.index);
  const spEx = subprims.instance.exports;
  const hasFuel = typeof spEx.wasm_set_funcall_fuel === "function";

  console.error(
    `[stage] ${stageLabel}: *FASL-API* is NIL; draining cold-load prefix until it initializes`,
  );
  for (const entry of pendingEntries) {
    if (faslApiReady()) break;
    attemptedIndices.push(entry.index);
    console.error(
      `[stage] ${stageLabel}: idx=${entry.index} kind=${entry.kind}` +
      (entry.name ? ` name=${entry.name}` : "") +
      (entry.entryIndex != null ? ` entry=${entry.entryIndex}` : ""),
    );
    try {
      if (hasFuel) {
        spEx.wasm_set_funcall_fuel(100000);
      }
      const rc = ex.wasm_cold_load_run_one(entry.index) | 0;
      if (hasFuel) {
        spEx.wasm_set_funcall_fuel(-1);
      }
      if (rc === 0) {
        completedIndices.push(entry.index);
      } else if (rc === 1) {
        skippedCount++;
        completedIndices.push(entry.index);
      } else {
        lispErrCount++;
        remainingIndices.push(entry.index);
        console.error(
          `[stage] ${stageLabel}: cold-load idx ${entry.index} returned rc=${rc}; continuing bootstrap search`,
        );
      }
    } catch (e) {
      if (hasFuel) {
        spEx.wasm_set_funcall_fuel(-1);
      }
      if (typeof ex.wasm_recover_after_trap === "function") {
        ex.wasm_recover_after_trap();
      }
      trappedCount++;
      remainingIndices.push(entry.index);
      console.error(
        `[stage] ${stageLabel}: cold-load idx ${entry.index} trapped before *FASL-API* init: ` +
        `${e?.message ?? e}; continuing bootstrap search`,
      );
    }
  }

  const finalFaslApiValue = lookupSymbolValue("*FASL-API*");
  if (!faslApiReady()) {
    fail(
      `${stageLabel}: *FASL-API* still NIL after ${attemptedIndices.length} cold-load entries ` +
      `(${describeSymbolValue("*FASL-API*", finalFaslApiValue, reader)}; ` +
      `${lispErrCount} lisp-err, ${trappedCount} trapped, ${skippedCount} skipped)`,
    );
  }
  console.error(
    `[stage] ${stageLabel}: ready after ${attemptedIndices.length} entries ` +
    `(${describeSymbolValue("*FASL-API*", finalFaslApiValue, reader)}; ` +
    `${lispErrCount} lisp-err, ${trappedCount} trapped, ${skippedCount} skipped, ` +
    `${remainingIndices.length} deferred)`,
  );
  return { attemptedIndices, completedIndices, remainingIndices };
}

function selectRebindEntries(namedFunctions) {
  const dedup = new Map();
  for (const fn of namedFunctions) {
    if (!fn?.name || !Number.isFinite(fn.entryIndex) || fn.name.startsWith("(:INTERNAL")) {
      continue;
    }
    const fnSlots = Number.isFinite(fn.fnSlots) ? fn.fnSlots : 3;
    const existing = dedup.get(fn.name);
    if (!existing ||
        fnSlots > existing.fnSlots ||
        (fnSlots === existing.fnSlots && fn.entryIndex > existing.entryIndex)) {
      dedup.set(fn.name, {
        entryIndex: fn.entryIndex >>> 0,
        fnSlots,
      });
    }
  }
  return [...dedup.entries()].map(([name, info]) => ({ name, ...info }));
}

function runForceRebindScan({ stageLabel, namedFunctions }) {
  if (namedFunctions.length === 0) {
    fail(`${stageLabel}: no functions found for heap scan`);
  }
  if (typeof ex.wasm_force_rebind_scan !== "function") {
    fail("kernel missing wasm_force_rebind_scan");
  }

  const enc = new TextEncoder();
  const allNameBytes = namedFunctions.map((fn) => enc.encode(fn.name));
  const tableSize = namedFunctions.length * 16;
  const namesSize = allNameBytes.reduce((sum, bytes) => sum + bytes.length, 0);
  const tableBase = allocScratch(runtime.memory, tableSize + namesSize);
  const mem8 = new Uint8Array(runtime.memory.buffer);
  const memDV = new DataView(runtime.memory.buffer);

  let nameWriteOff = tableBase + tableSize;
  for (let i = 0; i < namedFunctions.length; i++) {
    const nb = allNameBytes[i];
    mem8.set(nb, nameWriteOff);
    const eBase = tableBase + i * 16;
    memDV.setUint32(eBase,      nameWriteOff,                        true);
    memDV.setUint32(eBase + 4,  nb.length,                           true);
    memDV.setUint32(eBase + 8,  namedFunctions[i].entryIndex >>> 0,  true);
    memDV.setUint32(eBase + 12, (namedFunctions[i].fnSlots ?? 3) >>> 0, true);
    nameWriteOff += nb.length;
  }

  const rebound = ex.wasm_force_rebind_scan(tableBase >>> 0, namedFunctions.length >>> 0) | 0;
  console.error(`[stage] ${stageLabel}: ${rebound} symbols rebound (${namedFunctions.length} entries)`);
  if (rebound < 0) {
    fail(`${stageLabel}: wasm_force_rebind_scan failed: rc=${rebound}`);
  }
  return rebound;
}

const runtimeRebindFns = selectRebindEntries(
  (compiledModulesBundle?.functions ?? [])
    .filter((fn) => fn?.name && Number.isFinite(fn.entryIndex)
                    && !bootEntryIndices.has(fn.entryIndex >>> 0)
                    && !protectedBootSymbolNames.has(fn.name)),
);

/*
 * Bootstrap package helpers in level-0/nfasload are intentionally simpler
 * than their late runtime counterparts.  Rebinding these before required FASLs
 * load pulls in package-local nickname machinery too early and breaks the
 * pre-FASL SET-PACKAGE/FIND-PACKAGE path.
 */
const PRE_FASL_DEFERRED_RUNTIME_SYMBOL_NAMES = new Set([
  "PACKAGE-%LOCAL-NICKNAMES",
  "PACKAGE-%LOCALLY-NICKNAMED-BY",
]);

/*
 * Pre-FASL runtime rebinding must be stricter than the post-FASL repair pass.
 * wasm_force_rebind_scan matches by pname only and ignores package identity, so
 * rebinding late runtime names here can rewrite bootstrap/package-local symbols
 * inside boot const pools.  That is exactly how early SET-PACKAGE/%FIND-PKG
 * thunks end up seeing STRING/OR/CHARACTER rebound to late runtime entries.
 *
 * Keep the pre-FASL phase as an explicit allowlist.  The initial set is empty:
 * boot image fixup, protected lock repair, and exact bootstrap alias repair are
 * the only allowed pre-FASL fcell mutations.
 */
const PRE_FASL_RUNTIME_REBIND_SYMBOL_NAMES = new Set();

const preFaslRuntimeRebindFns = runtimeRebindFns.filter(
  (fn) =>
    PRE_FASL_RUNTIME_REBIND_SYMBOL_NAMES.has(fn.name) &&
    !PRE_FASL_DEFERRED_RUNTIME_SYMBOL_NAMES.has(fn.name),
);

function describeColdLoadSnapshotEntries() {
  if (typeof ex.wasm_cold_load_count !== "function" || typeof ex.wasm_cold_load_ref !== "function") {
    return [];
  }
  const nilValue = typeof ex.wasm_get_lisp_nil === "function" ? (ex.wasm_get_lisp_nil() >>> 0) : null;
  const reader = createRuntimeObjectReader(runtime.memory, { compiledFunctionByEntryIndex, nilValue });
  const total = ex.wasm_cold_load_count() | 0;
  const entries = [];
  for (let idx = 0; idx < total; idx++) {
    const fnPtr = ex.wasm_cold_load_ref(idx) >>> 0;
    const desc = reader.describeCallable(fnPtr);
    entries.push({
      index: idx,
      fnPtr,
      kind: desc.kind,
      name: desc.name,
      entryIndex: desc.entryIndex,
      summary: desc.summary,
    });
  }
  return entries;
}

function logColdLoadEntries(entries, { stageLabel, startIndex = 0, count = 16 } = {}) {
  if (!Array.isArray(entries) || entries.length === 0) return;
  const start = Math.max(0, startIndex | 0);
  const end = Math.min(entries.length, start + Math.max(0, count | 0));
  console.error(`[stage] ${stageLabel}: cold-load entries ${start}..${Math.max(start, end - 1)} of ${entries.length}`);
  for (let i = start; i < end; i++) {
    const entry = entries[i];
    console.error(
      `  [${entry.index}] kind=${entry.kind}` +
      (entry.name ? ` name=${entry.name}` : "") +
      (entry.entryIndex != null ? ` entry=${entry.entryIndex}` : "") +
      ` ptr=0x${entry.fnPtr.toString(16)} ${entry.summary}`,
    );
  }
}

function lookupSymbolFunctionValue(name) {
  const nameBytes = encoder.encode(name);
  const namePtr = ex.malloc(nameBytes.length);
  if (!namePtr) {
    fail(`lookupSymbolFunctionValue: malloc failed for ${name}`);
  }
  new Uint8Array(runtime.memory.buffer).set(nameBytes, namePtr);
  try {
    return ex.wasm_lookup_symbol_function(namePtr, nameBytes.length) >>> 0;
  } finally {
    if (typeof ex.free === "function") {
      ex.free(namePtr);
    }
  }
}

function lookupSymbolValue(name) {
  if (typeof ex.wasm_lookup_symbol_value !== "function") {
    fail("kernel missing wasm_lookup_symbol_value");
  }
  const nameBytes = encoder.encode(name);
  const namePtr = ex.malloc(nameBytes.length);
  if (!namePtr) {
    fail(`lookupSymbolValue: malloc failed for ${name}`);
  }
  new Uint8Array(runtime.memory.buffer).set(nameBytes, namePtr);
  try {
    return ex.wasm_lookup_symbol_value(namePtr, nameBytes.length) >>> 0;
  } finally {
    if (typeof ex.free === "function") {
      ex.free(namePtr);
    }
  }
}

function setSymbolFunctionEntry(name, entryIndex, slot = 0) {
  const nameBytes = encoder.encode(name);
  const namePtr = ex.malloc(nameBytes.length);
  if (!namePtr) {
    fail(`setSymbolFunctionEntry: malloc failed for ${name}`);
  }
  new Uint8Array(runtime.memory.buffer).set(nameBytes, namePtr);
  try {
    return ex.wasm_set_symbol_function_entry(
      namePtr,
      nameBytes.length,
      entryIndex >>> 0,
      slot >>> 0,
    ) | 0;
  } finally {
    if (typeof ex.free === "function") {
      ex.free(namePtr);
    }
  }
}

function expectedBootEntryForSpec(spec) {
  const expectedEntry = bootNamedFunctionMaxEntryByName.get(spec.manifestName);
  if (!Number.isFinite(expectedEntry)) {
    fail(`boot manifest missing ${spec.manifestName}`);
  }
  return expectedEntry >>> 0;
}

function expectedRuntimeEntryByName(name) {
  const expectedEntry = runtimeNamedFunctionMaxEntryByName.get(name);
  if (!Number.isFinite(expectedEntry)) {
    fail(`runtime manifest missing ${name}`);
  }
  return expectedEntry >>> 0;
}

function resolveProtectedBootSymbol(spec) {
  for (const name of spec.lookupNames) {
    const value = lookupSymbolFunctionValue(name);
    if (value !== 0) {
      return { lookupName: name, value };
    }
  }
  return { lookupName: spec.lookupNames[0], value: 0 };
}

function rebindProtectedBootSymbols(stageLabel) {
  if (typeof ex.wasm_set_symbol_function_entry !== "function") {
    fail("kernel missing wasm_set_symbol_function_entry");
  }
  console.error(`[stage] ${stageLabel}: repairing ${protectedBootSymbolSpecs.length} boot-owned symbols`);
  let rebound = 0;
  for (const spec of protectedBootSymbolSpecs) {
    const expectedEntry = expectedBootEntryForSpec(spec);
    let reboundAny = false;
    for (const name of spec.lookupNames) {
      const rc = setSymbolFunctionEntry(name, expectedEntry, 0);
      if (rc === 0) {
        rebound++;
        reboundAny = true;
      } else if (rc !== -1) {
        fail(`${stageLabel}: ${name} rebind failed rc=${rc}`);
      }
    }
    if (!reboundAny) {
      fail(`${stageLabel}: ${spec.lookupNames[0]} not found for repair`);
    }
  }
  console.error(`[stage] ${stageLabel}: rebound ${rebound} exact symbol bindings`);
}

function runProtectedBootSymbolGate(stageLabel) {
  if (typeof ex.wasm_lookup_symbol_function !== "function") {
    fail("kernel missing wasm_lookup_symbol_function");
  }
  const nilValue = typeof ex.wasm_get_lisp_nil === "function" ? (ex.wasm_get_lisp_nil() >>> 0) : null;
  const reader = createRuntimeObjectReader(runtime.memory, { compiledFunctionByEntryIndex, nilValue });

  console.error(`[stage] ${stageLabel}: checking ${protectedBootSymbolSpecs.length} boot-owned symbols`);
  for (const spec of protectedBootSymbolSpecs) {
    const expectedEntry = expectedBootEntryForSpec(spec);
    const resolved = resolveProtectedBootSymbol(spec);
    if (resolved.value === 0) {
      fail(`${stageLabel}: ${spec.lookupNames[0]} not found`);
    }
    const callable = reader.describeCallable(resolved.value);
    console.error(
      `[stage] ${stageLabel}: ${spec.lookupNames[0]} via=${resolved.lookupName} ` +
      `callable=${callable.name ?? callable.kind} entry=${callable.entryIndex ?? "?"} expected=${expectedEntry}`,
    );
    if (!Number.isFinite(callable.entryIndex)) {
      fail(`${stageLabel}: ${spec.lookupNames[0]} is not a compiled function`);
    }
    if (callable.name && DISALLOWED_LOCK_CALLABLE_NAMES.has(callable.name)) {
      fail(`${stageLabel}: ${spec.lookupNames[0]} resolved to disallowed ${callable.name}`);
    }
    if ((callable.entryIndex >>> 0) !== (expectedEntry >>> 0)) {
      fail(
        `${stageLabel}: ${spec.lookupNames[0]} resolved to entry ${callable.entryIndex}, ` +
        `expected boot entry ${expectedEntry}`,
      );
    }
  }
}

function rebindPreFaslBootstrapAliases(stageLabel) {
  if (typeof ex.wasm_set_symbol_function_entry !== "function") {
    fail("kernel missing wasm_set_symbol_function_entry");
  }
  console.error(`[stage] ${stageLabel}: repairing ${preFaslBootstrapAliasSpecs.length} bootstrap aliases`);
  let rebound = 0;
  for (const spec of preFaslBootstrapAliasSpecs) {
    const targetEntry = expectedRuntimeEntryByName(spec.targetName);
    const rc = setSymbolFunctionEntry(spec.symbolName, targetEntry, 0);
    if (rc !== 0) {
      fail(`${stageLabel}: ${spec.symbolName} -> ${spec.targetName} failed rc=${rc}`);
    }
    rebound++;
  }
  console.error(`[stage] ${stageLabel}: rebound ${rebound} exact symbol bindings`);
}

function runPreFaslBootstrapAliasGate(stageLabel) {
  if (typeof ex.wasm_lookup_symbol_function !== "function") {
    fail("kernel missing wasm_lookup_symbol_function");
  }
  const nilValue = typeof ex.wasm_get_lisp_nil === "function" ? (ex.wasm_get_lisp_nil() >>> 0) : null;
  const reader = createRuntimeObjectReader(runtime.memory, { compiledFunctionByEntryIndex, nilValue });

  console.error(`[stage] ${stageLabel}: checking ${preFaslBootstrapAliasSpecs.length} bootstrap aliases`);
  for (const spec of preFaslBootstrapAliasSpecs) {
    const expectedEntry = expectedRuntimeEntryByName(spec.targetName);
    const value = lookupSymbolFunctionValue(spec.symbolName);
    if (value === 0) {
      fail(`${stageLabel}: ${spec.symbolName} not found`);
    }
    const callable = reader.describeCallable(value);
    console.error(
      `[stage] ${stageLabel}: ${spec.symbolName} ` +
      `callable=${callable.name ?? callable.kind} entry=${callable.entryIndex ?? "?"} ` +
      `expected=${expectedEntry} target=${spec.targetName}`,
    );
    if (!Number.isFinite(callable.entryIndex)) {
      fail(`${stageLabel}: ${spec.symbolName} is not a compiled function`);
    }
    if ((callable.entryIndex >>> 0) !== (expectedEntry >>> 0)) {
      fail(
        `${stageLabel}: ${spec.symbolName} resolved to entry ${callable.entryIndex}, ` +
        `expected ${spec.targetName} entry ${expectedEntry}`,
      );
    }
  }
}

function packageNamesFromList(listPtr, reader, nilValue, limit = 16) {
  const names = [];
  let cur = listPtr >>> 0;
  const seen = new Set();
  while (cur !== 0 && cur !== (nilValue >>> 0) && names.length < limit) {
    if (seen.has(cur)) {
      names.push("<cycle>");
      break;
    }
    seen.add(cur);
    const cell = reader.readCons(cur);
    if (!cell) {
      names.push(`<non-cons 0x${cur.toString(16)}>`);
      break;
    }
    const pkgName = reader.readPackageName(cell.car);
    names.push(pkgName ?? reader.describeValue(cell.car));
    cur = cell.cdr >>> 0;
  }
  if (cur !== 0 && cur !== (nilValue >>> 0) && names.length >= limit) {
    names.push("...");
  }
  return names;
}

function describeConsList(listPtr, reader, nilValue, limit = 16) {
  const values = [];
  let cur = listPtr >>> 0;
  const seen = new Set();
  while (cur !== 0 && cur !== (nilValue >>> 0) && values.length < limit) {
    if (seen.has(cur)) {
      values.push("<cycle>");
      break;
    }
    seen.add(cur);
    const cell = reader.readCons(cur);
    if (!cell) {
      values.push(`<non-cons 0x${cur.toString(16)}>`);
      break;
    }
    values.push(reader.describeValue(cell.car));
    cur = cell.cdr >>> 0;
  }
  if (cur !== 0 && cur !== (nilValue >>> 0) && values.length >= limit) {
    values.push("...");
  }
  return values;
}

function debugPackageObject(pkgPtr, reader, nilValue, label) {
  const info = reader.descMisc(pkgPtr);
  if (!info || info.st !== SUBTAG_PACKAGE) {
    console.error(`[${label}] not a package: ${reader.describeValue(pkgPtr)}`);
    return;
  }
  reader.dumpObjectSlots(pkgPtr, label, 8);
  for (let i = 0; i < Math.min(info.cnt, 8); i++) {
    const slot = reader.readMiscElement(pkgPtr, i);
    if ((slot & 0x7) !== FULLTAG_CONS) continue;
    const values = describeConsList(slot, reader, nilValue, 12);
    console.error(`[${label}] slot ${i} list: [${values.join(", ")}]`);
  }
}

function logPreFaslPackageState(stageLabel) {
  if (typeof ex.wasm_lookup_symbol_value !== "function") {
    return;
  }
  const nilValue = typeof ex.wasm_get_lisp_nil === "function" ? (ex.wasm_get_lisp_nil() >>> 0) : 0;
  const reader = createRuntimeObjectReader(runtime.memory, { compiledFunctionByEntryIndex, nilValue });
  const packageValue = lookupSymbolValue("*PACKAGE*");
  const allPackagesValue = lookupSymbolValue("%ALL-PACKAGES%");
  const allPackagesLockValue = lookupSymbolValue("%ALL-PACKAGES-LOCK%");
  const packageNames = packageNamesFromList(allPackagesValue, reader, nilValue, 12);
  const summary = packageNames.length > 0 ? packageNames.join(", ") : "<empty>";
  console.error(
    `[stage] ${stageLabel}: *PACKAGE*=${reader.describeValue(packageValue)} ` +
    `%ALL-PACKAGES%=${reader.describeValue(allPackagesValue)} ` +
    `%ALL-PACKAGES-LOCK%=${reader.describeValue(allPackagesLockValue)}`,
  );
  console.error(`[stage] ${stageLabel}: package names [${packageNames.length}] ${summary}`);
  for (const fnName of ["SET-PACKAGE", "FIND-PACKAGE", "%FIND-PKG", "PACKAGE-%LOCAL-NICKNAMES"]) {
    const callableValue = lookupSymbolFunctionValue(fnName);
    const callable = reader.describeCallable(callableValue);
    console.error(
      `[stage] ${stageLabel}: fn ${fnName}=${reader.describeValue(callableValue)} ` +
      `callable=${callable.name ?? callable.kind} entry=${callable.entryIndex ?? "?"}`,
    );
  }
  if (!packageNames.includes("CCL") || !packageNames.includes("COMMON-LISP")) {
    reader.dumpObjectSlots(packageValue, `${stageLabel} *PACKAGE*`, 8);
    const cell = reader.readCons(allPackagesValue);
    if (cell) {
      reader.dumpObjectSlots(cell.car, `${stageLabel} first-package`, 8);
    }
  }
}

function logPreRestoreLispPointersState() {
  if (typeof ex.wasm_lookup_symbol_value !== "function") {
    return;
  }
  const nilValue = typeof ex.wasm_get_lisp_nil === "function" ? (ex.wasm_get_lisp_nil() >>> 0) : 0;
  const reader = createRuntimeObjectReader(runtime.memory, { compiledFunctionByEntryIndex, nilValue });
  const trackedSymbols = [
    "*INTERACTIVE-STREAMS-INITIALIZED*",
    "*HEAP-IVECTORS*",
  ];
  for (const symbolName of trackedSymbols) {
    const vcellValue = lookupSymbolValue(symbolName);
    console.error(
      `[stage] pre-restore-lisp-pointers: vcell ${symbolName}=0x${vcellValue.toString(16).padStart(8, "0")} ` +
      `(${reader.describeValue(vcellValue)})`,
    );
    reader.dumpObjectSlots(vcellValue, `pre-restore ${symbolName}`, 8);
  }

  const reviveValue = lookupSymbolFunctionValue("%REVIVE-SYSTEM-LOCKS");
  const reviveCallable = reader.describeCallable(reviveValue);
  console.error(
    `[stage] pre-restore-lisp-pointers: fcell %REVIVE-SYSTEM-LOCKS=0x${reviveValue.toString(16).padStart(8, "0")} ` +
    `(${reader.describeValue(reviveValue)}) callable=${reviveCallable.name ?? reviveCallable.kind} ` +
    `entry=${reviveCallable.entryIndex ?? "?"}`,
  );
  reader.dumpFunction(reviveValue, "pre-restore %REVIVE-SYSTEM-LOCKS", 8);

  if (typeof ex.wasm_const_pool_ref === "function") {
    const restoreValue = lookupSymbolFunctionValue("RESTORE-LISP-POINTERS");
    const restoreEntry = reader.readFunctionEntryIndex(restoreValue);
    console.error(
      `[stage] pre-restore-lisp-pointers: RESTORE-LISP-POINTERS=0x${restoreValue.toString(16).padStart(8, "0")} ` +
      `(${reader.describeValue(restoreValue)}) entry=${restoreEntry ?? "?"}`,
    );
    if (restoreEntry != null) {
      for (let slot = 0; slot < 3; slot++) {
        const value = ex.wasm_const_pool_ref(restoreEntry >>> 0, slot >>> 0) >>> 0;
        console.error(
          `[stage] pre-restore-lisp-pointers: restore const[${slot}]=0x${value.toString(16).padStart(8, "0")} ` +
          `(${reader.describeValue(value)})`,
        );
        reader.dumpObjectSlots(value, `pre-restore restore const[${slot}]`, 8);
      }
    }
  }
}

console.error(`[stage] cold-boot-init starting (const-pool installs so far: ${_cpInstallCount}, skipped: ${_cpSkipCount})`);
if (typeof ex.wasm_heap_profile === "function") {
  console.error("[stage] pre-cold-boot heap profile:");
  ex.wasm_heap_profile();
}
const coldBootRc = ex.wasm_run_cold_boot_init() | 0;
if (coldBootRc !== 0) {
  fail(`wasm_run_cold_boot_init returned ${coldBootRc}`);
}
trace("cold-boot-init complete");
const coldLoadEntries = describeColdLoadSnapshotEntries();
logColdLoadEntries(coldLoadEntries, {
  stageLabel: "post-cold-boot snapshot near C/JS handoff",
  startIndex: Math.max(0, COLD_LOAD_C_MAX - 4),
  count: 16,
});
logPreFaslPackageState("pre-FASL package gate");
rebindProtectedBootSymbols("pre-FASL lock repair");
runProtectedBootSymbolGate("pre-FASL lock gate");

const preFaslBootstrap = bootstrapColdLoadUntilFaslApi({
  stageLabel: "pre-FASL bootstrap cold-load",
  entries: coldLoadEntries,
});
const preFaslBootstrapCompletedIndices = dedupeIndices(preFaslBootstrap.completedIndices);
const preFaslColdLoadIndices = dedupeIndices(
  selectColdLoadEntriesByName(coldLoadEntries, PRE_FASL_JS_ENTRY_NAMES)
    .filter((idx) => !preFaslBootstrapCompletedIndices.includes(idx)),
);
const preFaslColdLoad = preFaslColdLoadIndices.length > 0
  ? drainColdLoadEntries({
      stageLabel: "pre-FASL cold-load prefix",
      indices: preFaslColdLoadIndices,
      maxPasses: 3,
    })
  : { remaining: [] };
if (preFaslRuntimeRebindFns.length > 0) {
  runForceRebindScan({
    stageLabel: "pre-FASL force-rebind",
    namedFunctions: preFaslRuntimeRebindFns,
  });
} else {
  console.error("[stage] pre-FASL force-rebind: skipped (explicit allowlist empty)");
}
rebindPreFaslBootstrapAliases("pre-FASL bootstrap alias repair");
logPreFaslPackageState("post-pre-FASL rebind package gate");
runPreFaslBootstrapAliasGate("pre-FASL bootstrap alias gate");
runProtectedBootSymbolGate("post-rebind lock gate");
const preFaslRetry = drainColdLoadEntries({
  stageLabel: "pre-FASL cold-load retry",
  indices: preFaslColdLoad?.remaining ?? [],
  maxPasses: 3,
});
const preFaslRemaining = dedupeIndices([
  ...(preFaslBootstrap.remainingIndices ?? []),
  ...(preFaslRetry?.remaining ?? preFaslColdLoad?.remaining ?? []),
]);

/* Spill reset: trapped cold-load entries can leak spill pushes because WASM
   traps skip restore-locals cleanup.  Reset before FASL loading so the FASL
   phase starts with a clean spill stack. */
if (typeof ex.wasm_spill_reset === "function") {
  ex.wasm_spill_reset();
  trace("spill stack reset before FASL loading");
}

/* Reset diagnostic counters so FASL-phase errors get full verbose
   diagnostics (cold-boot-init and the pre-FASL cold-load prefix consume some
   of the quota). */
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

const hasFuncallErrCounter = typeof ex.wasm_get_funcall_error_count === "function";

const faslResults = { ok: [], fail: [], skip: [] };
for (const faslPath of requiredFasls) {
  /* Some WASM fasls are valid thin loaders into the module bundle, so size
     alone is not a safe reason to skip loading. */
  {
    const fullPath = path.join(buildDir, faslPath);
    try {
      const stat = fsSync.statSync(fullPath);
      if (stat.size < 100) {
        console.error(`[fasload] WARN ${faslPath} — only ${stat.size} bytes; attempting load anyway`);
      }
    } catch (_) { /* stat failed — try loading anyway */ }
  }
  sharedProbeUtf8Scratch.reset();
  const faslMem = sharedProbeUtf8Scratch.allocUtf8(faslPath, encoder);
  const errBefore = hasFuncallErrCounter ? ex.wasm_get_funcall_error_count() >>> 0 : -1;
  /* Clear any pending_throw from previous FASL failure so this FASL starts clean */
  if (typeof ex.wasm_clear_pending_throw === "function") {
    ex.wasm_clear_pending_throw();
  }
  let faslRc;
  try {
    faslRc = ex.wasm_fasload_path(faslMem.ptr >>> 0, faslMem.len >>> 0) | 0;
  } catch (err) {
    try {
      dumpFasloadFailureContext({
        ex,
        runtime,
        faslPath,
        label: "fasload-diag",
        detail: `trap: ${err?.message ?? err}`,
        compiledFunctionByEntryIndex,
      });
    } catch (diagErr) {
      console.error(`[fasload-diag] diagnostic failed: ${diagErr?.message ?? diagErr}`);
    }
    console.error(`[fasload] FAIL (trap): ${faslPath} — ${err?.message ?? err}`);
    faslResults.fail.push({ path: faslPath, reason: "trap", detail: err?.message ?? String(err) });
    continue;
  }
  if (faslRc !== 0) {
    try {
      dumpFasloadFailureContext({
        ex,
        runtime,
        faslPath,
        label: "fasload-rc",
        detail: `rc=${faslRc}`,
        compiledFunctionByEntryIndex,
      });
    } catch (diagErr) {
      console.error(`[fasload-rc-diag] failed: ${diagErr?.message ?? diagErr}`);
    }
    console.error(`[fasload] FAIL (rc=${faslRc}): ${faslPath}`);
    faslResults.fail.push({ path: faslPath, reason: "rc", detail: faslRc });
    continue;
  }
  const errAfter = hasFuncallErrCounter ? ex.wasm_get_funcall_error_count() >>> 0 : -1;
  const errDelta = (errBefore >= 0 && errAfter >= 0) ? errAfter - errBefore : -1;
  if (errDelta > 0) {
    console.error(`[fasload] ${faslPath} ok — funcall errors during load: ${errDelta} (total ${errAfter})`);
  } else {
    trace(`fasload ${faslPath} ok${errDelta === 0 ? " (0 funcall errors)" : ""}`);
  }
  faslResults.ok.push(faslPath);
}
/* FASL loading summary */
console.error(`\n[fasload-summary] ${faslResults.ok.length} ok, ${faslResults.fail.length} failed, ${faslResults.skip.length} skipped`);
if (faslResults.skip.length > 0) {
  console.error(`[fasload-summary] skipped: ${faslResults.skip.join(", ")}`);
}
if (faslResults.fail.length > 0) {
  console.error(`[fasload-summary] failed:`);
  for (const f of faslResults.fail) {
    console.error(`  ${f.path}: ${f.reason} — ${f.detail}`);
  }
}
if (faslResults.ok.length > 0) {
  console.error(`[fasload-summary] ok: ${faslResults.ok.join(", ")}`);
}
if (faslResults.fail.length > 0 && faslResults.ok.length === 0) {
  fail(`All ${faslResults.fail.length} FASLs failed to load`);
}
if (requiredFasls.length > 0) {
  setBootPhaseOrFail(WASM_BOOT_PHASE.RUNTIME, { reason: "post-required-fasloads" });
}
} else {
  /* --no-fasload: L1 baked into boot image via xfasload cross-compiler */
  console.error("[stage] --no-fasload: L1 baked into boot image, skipping FASL loading");
  setBootPhaseOrFail(WASM_BOOT_PHASE.RUNTIME, { reason: "l1-baked-in" });
}

const postFaslPending = [
  ...preFaslRemaining,
  ...coldLoadEntries
    .filter((entry) =>
      !preFaslBootstrapCompletedIndices.includes(entry.index) &&
      !preFaslColdLoadIndices.includes(entry.index))
    .map((entry) => entry.index),
];
const postFaslColdLoad = drainColdLoadEntries({
  stageLabel: "post-FASL cold-load tail",
  indices: dedupeIndices(postFaslPending),
});
if (postFaslColdLoad && typeof ex.wasm_spill_reset === "function") {
  ex.wasm_spill_reset();
  trace("spill stack reset after post-FASL cold-load tail");
}

/* Post-runtime-cold-load GC: the heap is now enormous (several GB) and mostly
   garbage from compiled-module instantiation and bootstrap work.  Compact it
   after the deferred cold-load tail completes so the snapshot pointers stay
   valid until the last JS-driven drain finishes. */
{
  console.error("[stage] post-runtime-cold-load GC...");
  const gcBefore = Date.now();
  ex.wasm_trigger_gc();
  const gcMs = Date.now() - gcBefore;
  console.error(`[stage] post-runtime-cold-load GC done (${gcMs} ms)`);
}

/* Heap profile — understand what's consuming space after GC compaction */
if (typeof ex.wasm_heap_profile === "function") {
  console.error("[stage] running heap profile...");
  const liveBytes = ex.wasm_heap_profile() >>> 0;
  console.error(`[stage] heap profile done: ${liveBytes} bytes (${(liveBytes / (1024*1024)).toFixed(1)} MiB) live`);
}

/* RESTORE-LISP-POINTERS deferred to after vcell repair (Phase 2D).
   It must run after force-rebind (fcells), late const-pool install,
   and vcell repair — otherwise it reads stale/unbound symbol values
   (e.g., *character-encodings* is unbound_marker if the synthesized
   symbol duplicate hasn't been repaired yet). */

/* Phase 2A: Const pool status.  Boot pools installed during module install.
   Runtime pools deferred to Phase 2C (after force-rebind, before save). */
{
  const allEntries = new Set([
    ...bootConstPoolData.keys(),
    ...constPoolEntries.keys(),
  ]);
  const alreadyInstalled = [...allEntries].filter(e => constPoolsInstalled.has(e)).length;
  console.error(
    `[stage] const-pool status: ${alreadyInstalled}/${allEntries.size} installed pre-Phase2C,` +
    ` ${allEntries.size - alreadyInstalled} deferred to Phase 2C`
  );
}

/* Runtime const pools may have been installed on-demand during FASL loading.
   Those early installs can legitimately contain NIL placeholders when a symbol
   or function designator was not available yet.  Phase 2C is therefore both
   the initial install point for deferred runtime pools and the canonical
   refresh point for any runtime pool that was installed before runtime was
   fully canonicalized. */
const runtimeConstPoolsInstalledBeforePhase2C = new Set(
  [...constPoolsInstalled].filter((entryIndex) => constPoolEntries.has(entryIndex)),
);

/* Phase 2B: Force-rebind all WASM-compiled runtime functions.
   FASL loading silently fails to bind xfunction objects (subtag-xfunction = 0x92)
   because %defun's (typep named-fn 'function) check rejects them.  Additionally,
   early const pool install can synthesize placeholder symbols that
   wasm_set_symbol_function_entry (package-table lookup) would miss.
   wasm_force_rebind_scan does a full heap scan and unconditionally binds every
   symbol object whose pname matches a table entry — catching both the canonical
   symbol and any const-pool-synthesized placeholders.
   This runs BEFORE image save; it is NOT a launch-time repair. */
runForceRebindScan({
  stageLabel: "force-rebind",
  namedFunctions: runtimeRebindFns,
});

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

/* Invariant gate — SKIPPED.
   The per-symbol wasm_set_symbol_function_entry call falls back to an
   O(N) heap scan for each unresolved symbol.  With ~4756 entries and a
   2 GB heap, this takes hours in interpreted WASM.
   force-rebind (above) already rebounds the runtime functions via its own
   heap scan; the remaining symbols resolve through the function table. */
console.error("[stage] invariant fcell gate SKIPPED");

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

/* Free JS-side boot const pool caches — no longer needed (boot pools are
   already installed and baked into the image). */
bootConstPoolData.clear();

/* Phase 2C: Install or refresh runtime const pools.
   Deferred from module-install time because wasm_intern_startup synthesized
   non-canonical symbol objects when called during pool install (depth > 0).
   Some runtime pools were also installed on-demand during FASL loading before
   all symbol/package state existed; those pools may contain NIL placeholders
   and must be refreshed here.  At this point cold-boot-init and FASL loading
   are done, so runtime const pools can be canonicalized before the image save.
   Class-refs are left as sentinel cons cells and resolved next. */
{
  let installed = 0, refreshed = 0, failed = 0, skipped = 0;
  for (const [entryIndex, info] of constPoolEntries) {
    const decoded = decodeConstPoolForInfo(info);
    if (!decoded || decoded.length === 0) { skipped++; continue; }
    const refresh = runtimeConstPoolsInstalledBeforePhase2C.has(entryIndex);
    try {
      const rc = installConstPoolBytes({
        kernelExports: ex,
        memory: runtime.memory,
        entryIndex,
        constPoolBytes: decoded,
      });
      const nilValue = ex.wasm_get_lisp_nil?.() >>> 0;
      if (nilValue != null && (rc >>> 0) === nilValue) {
        failed++;
      } else {
        constPoolsInstalled.add(entryIndex);
        if (refresh) {
          refreshed++;
        } else {
          installed++;
        }
      }
    } catch (e) {
      console.error(`[stage] late pool install entry ${entryIndex} error: ${e.message}`);
      failed++;
    }
    if ((installed + failed) % 500 === 0) {
      console.error(`[progress] late pool install: ${installed + failed}/${constPoolEntries.size}`);
    }
  }
  console.error(
    `[stage] late runtime const-pool install: ${installed} installed, ` +
    `${refreshed} refreshed, ${failed} failed, ${skipped} skipped (empty)`,
  );
}

/* Resolve class-ref sentinel cons cells in all pools.  The serializer now
   emits class-ref tags (tag 18) for named class objects instead of deep-copying
   their entire gvector graph.  The deserializer stored (symbol . sentinel)
   cons cells as placeholders.  This pass resolves them to actual class objects
   via FIND-CLASS, now that cold-boot-init has completed and all classes exist. */
if (typeof ex.wasm_const_pool_resolve_class_refs === "function") {
  const resolved = ex.wasm_const_pool_resolve_class_refs();
  console.error(`[stage] const pool class-ref resolution: ${resolved} refs resolved`);
} else {
  console.error(`[stage] const pool class-ref resolution: kernel missing export (skipped)`);
}

/* Phase 2D: Vcell repair pass — analogous to force-rebind (fcells).
   Synthesized symbol duplicates from const-pool install may have stale
   vcells (unbound_marker or NIL) while the canonical symbol (in the
   package table) was properly initialized by defvar.  This pass copies
   the canonical vcell to all duplicates. */
if (typeof ex.wasm_repair_vcell_scan === "function") {
  const vcellRepaired = ex.wasm_repair_vcell_scan() | 0;
  console.error(`[stage] vcell repair: ${vcellRepaired} symbols repaired`);
  if (vcellRepaired < 0) {
    fail(`wasm_repair_vcell_scan failed: rc=${vcellRepaired}`);
  }
} else {
  console.error(`[stage] vcell repair: kernel missing wasm_repair_vcell_scan (skipped)`);
}

/* Now call RESTORE-LISP-POINTERS.  All prerequisites are met:
   - Level-1 FASLs loaded (function is defined)
   - force-rebind done (function table entries patched)
   - Late const pools installed (all symbol refs canonical)
   - Vcell repair done (synthesized symbol duplicates have correct values)
   This rehashes package tables and runs fixup hooks for runtime correctness. */
logPreRestoreLispPointersState();
console.error("[stage] calling RESTORE-LISP-POINTERS...");
const rlpBefore = Date.now();
const postFasloadRestoreRc = ex.wasm_restore_lisp_pointers() | 0;
const rlpMs = Date.now() - rlpBefore;
console.error(`[stage] RESTORE-LISP-POINTERS rc=${postFasloadRestoreRc} (${rlpMs} ms)`);
if (postFasloadRestoreRc !== 0) {
  trace(`RESTORE-LISP-POINTERS rc=${postFasloadRestoreRc} (non-fatal)`);
}

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
/* Disable the Lisp save path — use C-level save_application directly.
   The Lisp %save-application-internal path requires a fully running
   top-level loop which we don't have during the build. */
const subprimsWasReady = typeof ex.wasm_set_subprims_ready === "function";
if (subprimsWasReady) {
  ex.wasm_set_subprims_ready(0);
}
trace(`invoking wasm_save_image_direct for ${wasmOutputPath}`);
const saveRc = ex.wasm_save_image_direct(
  imagePathPtr,
  imagePathBytes.length >>> 0,
  0,
) | 0;
if (subprimsWasReady) {
  ex.wasm_set_subprims_ready(1);
}
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

    /* Const pool bytes are NOT embedded in modules.bin — pools are pre-baked
       in the saved image and resolved at build time.  Only compiled function
       code goes into modules.bin.  This eliminates ~790 MB of const pool data. */

    const planEntry = {
      index: idx,
      source: "modules",
      offset: binOffset,
      length: moduleLen,
      storedLength: storedLen !== moduleLen ? storedLen : undefined,
      encoding,
      export: entry.exportName || "fn",
    };
    startupPlanEntries.push(planEntry);
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
    constPools: {
      baked: true,
      bakedCount: constPoolsInstalled.size,
    },
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
