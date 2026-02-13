import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { BOOTSTRAP_L0_CONTRACT_V1 } from "./bootstrap-l0-contract.mjs";

export const STARTUP_BINDING_MAP_SCHEMA_V1 = "startup_binding_map_v1";
const STARTUP_BINDING_MAP_GENERATOR_V1 = "startup_binding_map_generator_v1";
const STARTUP_BINDING_MAP_COVERAGE_SCHEMA_V1 = "startup_binding_map_coverage_v1";
const UTF8_DECODER = new TextDecoder("utf-8");

const FIXNUM_MIN = -0x20000000; // -536870912
const FIXNUM_MAX = 0x1fffffff; // 536870911

const SPECIAL_BINDING_FORM_PATTERN = /\((defparameter|defvar|def-standard-initial-binding)\s+([^\s()]+)(?:\s+(\([^()\s]+\)|'[^()\s]+|[^()\s]+))?/giu;
const LEVEL0_FUNCTION_FORM_PATTERN = /\((defun|defmacro|define-compiler-macro|defsetf|define-setf-expander)\s+([^\s()]+|\([^()]+\))/giu;
const IN_PACKAGE_PATTERN = /\(in-package\s+("[^"]+"|[^\s()]+)\s*\)/giu;

const LEVEL0_DEFAULT_PACKAGE = "CCL";
const PACKAGE_ALIASES = Object.freeze({
  CL: "COMMON-LISP",
  CCL: "CCL",
  "COMMON-LISP": "COMMON-LISP",
  "COMMON-LISP-USER": "COMMON-LISP-USER",
  KEYWORD: "KEYWORD",
});

function toPosixPath(value) {
  return String(value ?? "").split(path.sep).join(path.posix.sep);
}

function normalizeToken(value) {
  if (typeof value !== "string") return "";
  return value.trim();
}

function normalizePackageName(value) {
  return normalizeToken(value).toUpperCase();
}

function canonicalizePackageName(value) {
  const normalized = normalizePackageName(value);
  if (!normalized) return "";
  return PACKAGE_ALIASES[normalized] ?? normalized;
}

function normalizeSymbolName(value) {
  let token = normalizeToken(value);
  if (!token) return "";
  if (token.startsWith("'")) token = token.slice(1);
  const colon = token.lastIndexOf(":");
  if (colon >= 0) token = token.slice(colon + 1);
  return token.toUpperCase();
}

function makeSymbolKey(packageName, symbolName) {
  const pkg = canonicalizePackageName(packageName);
  const sym = normalizeSymbolName(symbolName);
  if (!pkg || !sym) return "";
  return `${pkg}::${sym}`;
}

function countLinesBefore(text, index) {
  const head = text.slice(0, Math.max(0, index | 0));
  let lines = 1;
  for (let i = 0; i < head.length; i++) {
    if (head.charCodeAt(i) === 10) lines++;
  }
  return lines;
}

async function collectLispFiles(dir, { recursive = true } = {}) {
  const out = [];
  let entries = [];
  try {
    entries = await fs.readdir(dir, { withFileTypes: true });
  } catch {
    return out;
  }
  entries.sort((a, b) => a.name.localeCompare(b.name));
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (recursive) {
        out.push(...await collectLispFiles(fullPath, { recursive }));
      }
      continue;
    }
    if (entry.isFile() && entry.name.toLowerCase().endsWith(".lisp")) {
      out.push(fullPath);
    }
  }
  return out;
}

function parseInPackageToken(token, fallbackPackage = LEVEL0_DEFAULT_PACKAGE) {
  let value = normalizeToken(token);
  if (!value) return canonicalizePackageName(fallbackPackage);
  if (value.startsWith("'")) value = value.slice(1);
  if (value.startsWith('"') && value.endsWith('"') && value.length >= 2) {
    value = value.slice(1, -1);
  }
  if (value.startsWith(":")) value = value.slice(1);
  const canonical = canonicalizePackageName(value);
  if (!canonical) return canonicalizePackageName(fallbackPackage);
  return canonical;
}

function parseFunctionDesignatorToken(token, fallbackPackage = LEVEL0_DEFAULT_PACKAGE) {
  let value = normalizeToken(token);
  if (!value) return null;
  if (value.startsWith("'")) value = value.slice(1);
  if (!value || value.startsWith("(") || value.startsWith("#")) {
    return null;
  }

  let packageName = canonicalizePackageName(fallbackPackage);
  let symbolToken = value;

  const doubleColon = value.indexOf("::");
  if (doubleColon > 0) {
    packageName = canonicalizePackageName(value.slice(0, doubleColon));
    symbolToken = value.slice(doubleColon + 2);
  } else {
    const singleColon = value.indexOf(":");
    if (singleColon === 0) {
      packageName = "KEYWORD";
      symbolToken = value.slice(1);
    } else if (singleColon > 0) {
      packageName = canonicalizePackageName(value.slice(0, singleColon));
      symbolToken = value.slice(singleColon + 1);
    }
  }

  const symbolName = normalizeSymbolName(symbolToken);
  if (!symbolName || !packageName) return null;
  return {
    package_name: packageName,
    symbol_name: symbolName,
    symbol_key: makeSymbolKey(packageName, symbolName),
    designator_token: value,
  };
}

function createFunctionRecord(entryIndex) {
  const idx = entryIndex >>> 0;
  return {
    ambiguous: false,
    entry_index: idx,
    alternatives: [idx],
  };
}

function addFunctionRecord(map, key, entryIndex) {
  if (!key) return;
  const idx = entryIndex >>> 0;
  const existing = map.get(key);
  if (!existing) {
    map.set(key, createFunctionRecord(idx));
    return;
  }
  if (!existing.alternatives.includes(idx)) {
    existing.alternatives.push(idx);
    existing.alternatives.sort((a, b) => a - b);
  }
  if (existing.entry_index !== idx) {
    existing.ambiguous = true;
  }
}

async function scanSpecialBindingDefinitions(repoRoot) {
  const level1Dir = path.join(repoRoot, "level-1");
  const files = await collectLispFiles(level1Dir, { recursive: true });
  const definitions = new Map();

  for (const filePath of files) {
    let text = "";
    try {
      text = await fs.readFile(filePath, "utf8");
    } catch {
      continue;
    }
    SPECIAL_BINDING_FORM_PATTERN.lastIndex = 0;
    let match = null;
    while ((match = SPECIAL_BINDING_FORM_PATTERN.exec(text)) !== null) {
      const formKind = normalizeToken(match[1]).toLowerCase();
      const symbolToken = normalizeToken(match[2]);
      const initToken = normalizeToken(match[3] ?? "");
      const symbolName = normalizeSymbolName(symbolToken);
      if (!symbolName) continue;
      const key = makeSymbolKey("CCL", symbolName);
      if (!key) continue;
      definitions.set(key, {
        form_kind: formKind,
        symbol_token: symbolToken,
        init_token: initToken || null,
        file: toPosixPath(path.relative(repoRoot, filePath)),
        line: countLinesBefore(text, match.index),
      });
    }
  }

  return definitions;
}

function collectInPackageEvents(text, fallbackPackage = LEVEL0_DEFAULT_PACKAGE) {
  const out = [];
  IN_PACKAGE_PATTERN.lastIndex = 0;
  let match = null;
  while ((match = IN_PACKAGE_PATTERN.exec(text)) !== null) {
    out.push({
      index: match.index >>> 0,
      package_name: parseInPackageToken(match[1], fallbackPackage),
    });
  }
  out.sort((a, b) => (a.index >>> 0) - (b.index >>> 0));
  return out;
}

async function scanLevel0FunctionDesignators(repoRoot) {
  const level0Dir = path.join(repoRoot, "level-0");
  const files = await collectLispFiles(level0Dir, { recursive: false });
  const definitions = new Map();
  const stats = {
    files_scanned: 0,
    forms_scanned: 0,
    symbol_designators: 0,
    non_symbol_designators: 0,
    duplicate_symbol_designators: 0,
    unique_symbol_designators: 0,
  };

  for (const filePath of files) {
    let text = "";
    try {
      text = await fs.readFile(filePath, "utf8");
    } catch {
      continue;
    }
    stats.files_scanned++;

    const packageEvents = collectInPackageEvents(text, LEVEL0_DEFAULT_PACKAGE);
    let currentPackage = LEVEL0_DEFAULT_PACKAGE;
    let packageCursor = 0;
    LEVEL0_FUNCTION_FORM_PATTERN.lastIndex = 0;
    let match = null;
    while ((match = LEVEL0_FUNCTION_FORM_PATTERN.exec(text)) !== null) {
      stats.forms_scanned++;
      while (packageCursor < packageEvents.length && packageEvents[packageCursor].index <= match.index) {
        currentPackage = packageEvents[packageCursor].package_name || currentPackage;
        packageCursor++;
      }

      const formKind = normalizeToken(match[1]).toLowerCase();
      const token = normalizeToken(match[2]);
      const parsed = parseFunctionDesignatorToken(token, currentPackage);
      if (!parsed || !parsed.symbol_key) {
        stats.non_symbol_designators++;
        continue;
      }
      stats.symbol_designators++;

      const existing = definitions.get(parsed.symbol_key);
      if (!existing) {
        definitions.set(parsed.symbol_key, {
          form_kind: formKind,
          file: toPosixPath(path.relative(repoRoot, filePath)),
          line: countLinesBefore(text, match.index),
          designator_token: token,
          package_name: parsed.package_name,
          symbol_name: parsed.symbol_name,
          symbol_key: parsed.symbol_key,
          duplicates: 0,
        });
      } else {
        existing.duplicates = (existing.duplicates >>> 0) + 1;
        stats.duplicate_symbol_designators++;
      }
    }
  }

  stats.unique_symbol_designators = definitions.size;
  return { definitions, stats };
}

function buildFunctionIndex(functionEntries) {
  const byName = new Map();
  const bySymbolKey = new Map();
  const stats = {
    input_entries: 0,
    indexed_entries: 0,
    non_symbol_designator_entries: 0,
    unique_names: 0,
    ambiguous_names: 0,
    unique_symbol_keys: 0,
    ambiguous_symbol_keys: 0,
  };

  for (const entry of Array.isArray(functionEntries) ? functionEntries : []) {
    stats.input_entries++;
    if (!Number.isFinite(entry?.entryIndex) || entry.entryIndex < 0) continue;
    const parsed = parseFunctionDesignatorToken(entry?.name ?? "", LEVEL0_DEFAULT_PACKAGE);
    if (!parsed || !parsed.symbol_name || !parsed.symbol_key) {
      stats.non_symbol_designator_entries++;
      continue;
    }
    const index = entry.entryIndex >>> 0;
    addFunctionRecord(byName, parsed.symbol_name, index);
    addFunctionRecord(bySymbolKey, parsed.symbol_key, index);
    stats.indexed_entries++;
  }

  let ambiguousNames = 0;
  for (const record of byName.values()) {
    if (record.ambiguous) ambiguousNames++;
  }
  let ambiguousSymbolKeys = 0;
  for (const record of bySymbolKey.values()) {
    if (record.ambiguous) ambiguousSymbolKeys++;
  }
  stats.unique_names = byName.size;
  stats.ambiguous_names = ambiguousNames;
  stats.unique_symbol_keys = bySymbolKey.size;
  stats.ambiguous_symbol_keys = ambiguousSymbolKeys;

  return { byName, bySymbolKey, stats };
}

function resolveFunctionEntry({ packageName, symbolName }, functionIndex) {
  const packageKey = canonicalizePackageName(packageName);
  const symbolKey = normalizeSymbolName(symbolName);
  if (!symbolKey) {
    return {
      status: "missing",
      reason: "missing-symbol-name",
    };
  }

  const fullKey = makeSymbolKey(packageKey, symbolKey);
  if (fullKey) {
    const exact = functionIndex?.bySymbolKey?.get(fullKey) ?? null;
    if (exact) {
      if (exact.ambiguous) {
        return {
          status: "ambiguous",
          reason: "function-metadata-ambiguous",
          alternatives: exact.alternatives.slice(),
          match_key: "symbol-key",
        };
      }
      return {
        status: "resolved",
        entry_index: exact.entry_index >>> 0,
        match_key: "symbol-key",
      };
    }
  }

  const byName = functionIndex?.byName?.get(symbolKey) ?? null;
  if (!byName) {
    return {
      status: "missing",
      reason: "function-metadata-unresolved",
    };
  }
  if (byName.ambiguous) {
    return {
      status: "ambiguous",
      reason: "function-metadata-ambiguous",
      alternatives: byName.alternatives.slice(),
      match_key: "symbol-name",
    };
  }
  return {
    status: "resolved",
    entry_index: byName.entry_index >>> 0,
    match_key: "symbol-name",
  };
}

function classifyInitializerToken(initToken, functionIndex) {
  const token = normalizeToken(initToken);
  if (!token) {
    return {
      availability: "deferred",
      initializer: {
        kind: "deferred",
        reason: "no-initform",
      },
    };
  }

  if (/^[+-]?\d+$/u.test(token)) {
    const value = Number.parseInt(token, 10);
    if (!Number.isSafeInteger(value)) {
      return {
        availability: "unsupported",
        initializer: {
          kind: "unsupported",
          reason: "integer-not-safe",
          detail: token,
        },
      };
    }
    if (value < FIXNUM_MIN || value > FIXNUM_MAX) {
      return {
        availability: "unsupported",
        initializer: {
          kind: "unsupported",
          reason: "fixnum-range",
          detail: token,
        },
      };
    }
    return {
      availability: "literal",
      initializer: {
        kind: "literal-fixnum",
        fixnum_value: value | 0,
      },
    };
  }

  const upper = token.toUpperCase();
  if (upper === "NIL") {
    return {
      availability: "literal",
      initializer: {
        kind: "literal-nil",
      },
    };
  }

  if (token.startsWith("(") && token.endsWith(")")) {
    const inner = normalizeToken(token.slice(1, -1));
    if (!inner || /\s/u.test(inner)) {
      return {
        availability: "deferred",
        initializer: {
          kind: "deferred",
          reason: "nontrivial-call-form",
          detail: token,
        },
      };
    }
    const parsed = parseFunctionDesignatorToken(inner, LEVEL0_DEFAULT_PACKAGE);
    if (!parsed) {
      return {
        availability: "deferred",
        initializer: {
          kind: "deferred",
          reason: "invalid-call-form",
          detail: token,
        },
      };
    }
    const resolved = resolveFunctionEntry({
      packageName: parsed.package_name,
      symbolName: parsed.symbol_name,
    }, functionIndex);
    if (resolved.status === "missing") {
      return {
        availability: "deferred",
        initializer: {
          kind: "deferred",
          reason: "initializer-function-unresolved",
          detail: inner,
        },
      };
    }
    if (resolved.status === "ambiguous") {
      return {
        availability: "unsupported",
        initializer: {
          kind: "unsupported",
          reason: "initializer-function-ambiguous",
          detail: inner,
          alternatives: resolved.alternatives.slice(),
        },
      };
    }
    return {
      availability: "entry-backed",
      initializer: {
        kind: "entry-function",
        function_name: parsed.symbol_name,
        entry_index: resolved.entry_index >>> 0,
      },
    };
  }

  if (upper === "T" || token.startsWith(":") || token.startsWith("'")) {
    return {
      availability: "unsupported",
      initializer: {
        kind: "unsupported",
        reason: "literal-kind-unsupported",
        detail: token,
      },
    };
  }

  return {
    availability: "deferred",
    initializer: {
      kind: "deferred",
      reason: "non-literal-initform",
      detail: token,
    },
  };
}

function classifyFunctionBindingInitializer(symbolSpec, functionIndex) {
  const resolved = resolveFunctionEntry(symbolSpec, functionIndex);
  if (resolved.status === "resolved") {
    return {
      availability: "entry-backed",
      initializer: {
        kind: "entry-function",
        function_name: normalizeSymbolName(symbolSpec?.symbolName ?? ""),
        entry_index: resolved.entry_index >>> 0,
        match_key: resolved.match_key ?? null,
      },
      resolution_status: "resolved",
    };
  }
  if (resolved.status === "ambiguous") {
    return {
      availability: "unsupported",
      initializer: {
        kind: "unsupported",
        reason: resolved.reason ?? "function-metadata-ambiguous",
        alternatives: Array.isArray(resolved.alternatives) ? resolved.alternatives.slice() : [],
        match_key: resolved.match_key ?? null,
      },
      resolution_status: "ambiguous",
    };
  }
  return {
    availability: "deferred",
    initializer: {
      kind: "deferred",
      reason: resolved.reason ?? "function-metadata-unresolved",
      match_key: resolved.match_key ?? null,
    },
    resolution_status: "missing",
  };
}

function normalizeEntryTargetCell(entry) {
  const explicit = normalizeToken(entry?.target_cell).toLowerCase();
  if (explicit === "vcell" || explicit === "fcell") return explicit;
  const bindingClass = normalizeToken(entry?.binding_class).toLowerCase();
  if (bindingClass === "function") return "fcell";
  return "vcell";
}

function normalizeEntryBindingClass(entry) {
  const explicit = normalizeToken(entry?.binding_class).toLowerCase();
  if (explicit === "special-variable" || explicit === "function") return explicit;
  const target = normalizeEntryTargetCell(entry);
  return target === "fcell" ? "function" : "special-variable";
}

function summarizeEntries(entries) {
  const counts = {
    total_entries: 0,
    literal_entries: 0,
    entry_backed_entries: 0,
    deferred_entries: 0,
    unsupported_entries: 0,
    vcell_entries: 0,
    fcell_entries: 0,
    special_variable_entries: 0,
    function_entries: 0,
  };
  for (const entry of Array.isArray(entries) ? entries : []) {
    counts.total_entries++;
    switch (entry?.availability) {
      case "literal":
        counts.literal_entries++;
        break;
      case "entry-backed":
        counts.entry_backed_entries++;
        break;
      case "unsupported":
        counts.unsupported_entries++;
        break;
      case "deferred":
      default:
        counts.deferred_entries++;
        break;
    }
    const targetCell = normalizeEntryTargetCell(entry);
    if (targetCell === "fcell") counts.fcell_entries++;
    else counts.vcell_entries++;

    const bindingClass = normalizeEntryBindingClass(entry);
    if (bindingClass === "function") counts.function_entries++;
    else counts.special_variable_entries++;
  }
  return counts;
}

function normalizeCoverageObject(coverage) {
  if (!coverage || typeof coverage !== "object" || Array.isArray(coverage)) return null;
  return {
    schema_version: STARTUP_BINDING_MAP_COVERAGE_SCHEMA_V1,
    required_special_variable_bindings: coverage.required_special_variable_bindings ?? null,
    level0_source_scan: coverage.level0_source_scan ?? null,
    level0_function_bindings: coverage.level0_function_bindings ?? null,
    runtime_function_metadata: coverage.runtime_function_metadata ?? null,
    contract_required_const_pool_function_bindings:
      coverage.contract_required_const_pool_function_bindings ?? null,
  };
}

export function summarizeStartupBindingMapArtifact(artifact) {
  return summarizeEntries(Array.isArray(artifact?.entries) ? artifact.entries : []);
}

export function normalizeStartupBindingMapArtifact(artifact) {
  if (!artifact || typeof artifact !== "object") return null;
  const rawEntries = Array.isArray(artifact.entries) ? artifact.entries : [];
  const entries = rawEntries.map((entry) => {
    const targetCell = normalizeEntryTargetCell(entry);
    const bindingClass = normalizeEntryBindingClass(entry);
    const packageName = canonicalizePackageName(entry?.package_name ?? "");
    const symbolName = normalizeSymbolName(entry?.symbol_name ?? "");
    const symbolKey = makeSymbolKey(packageName, symbolName);
    return {
      ...entry,
      binding_class: bindingClass,
      target_cell: targetCell,
      package_name: packageName,
      symbol_name: symbolName,
      symbol_key: symbolKey || (typeof entry?.symbol_key === "string" ? entry.symbol_key : ""),
      require_non_nil: Boolean(entry?.require_non_nil),
    };
  });
  return {
    schema_version: STARTUP_BINDING_MAP_SCHEMA_V1,
    generator: STARTUP_BINDING_MAP_GENERATOR_V1,
    contract_id: typeof artifact.contract_id === "string" ? artifact.contract_id : null,
    coverage: normalizeCoverageObject(artifact.coverage),
    entries,
    counts: summarizeEntries(entries),
  };
}

function readConstPoolU32LE(bytes, state, fieldName) {
  if ((state.offset + 4) > bytes.length) {
    throw new Error(`const-pool truncated while reading ${fieldName}`);
  }
  const o = state.offset;
  const value = (
    bytes[o] |
    (bytes[o + 1] << 8) |
    (bytes[o + 2] << 16) |
    (bytes[o + 3] << 24)
  ) >>> 0;
  state.offset += 4;
  return value;
}

function readConstPoolUleb32(bytes, state, fieldName) {
  let value = 0;
  let shift = 0;
  for (let i = 0; i < 5; i++) {
    if (state.offset >= bytes.length) {
      throw new Error(`const-pool truncated while reading ${fieldName}`);
    }
    const byte = bytes[state.offset++];
    value |= (byte & 0x7f) << shift;
    if ((byte & 0x80) === 0) {
      return value >>> 0;
    }
    shift += 7;
  }
  throw new Error(`const-pool malformed uleb32 in ${fieldName}`);
}

function readConstPoolSleb32Raw(bytes, state, fieldName) {
  for (let i = 0; i < 5; i++) {
    if (state.offset >= bytes.length) {
      throw new Error(`const-pool truncated while reading ${fieldName}`);
    }
    const byte = bytes[state.offset++];
    if ((byte & 0x80) === 0) {
      return;
    }
  }
  throw new Error(`const-pool malformed sleb32 in ${fieldName}`);
}

function readConstPoolNat(bytes, state, version, fieldName) {
  if (version >= 2) return readConstPoolUleb32(bytes, state, fieldName);
  return readConstPoolU32LE(bytes, state, fieldName);
}

function readConstPoolSpan(bytes, state, len, fieldName) {
  const n = len >>> 0;
  if ((state.offset + n) > bytes.length) {
    throw new Error(`const-pool truncated while reading ${fieldName}`);
  }
  const start = state.offset;
  state.offset += n;
  return bytes.subarray(start, start + n);
}

function parseConstPoolSymbolRefsFromBytes(bytesLike, entryIndex = 0) {
  const refs = [];
  const bytes = bytesLike instanceof Uint8Array
    ? bytesLike
    : (bytesLike == null ? null : Uint8Array.from(bytesLike));
  if (!(bytes instanceof Uint8Array) || bytes.length < 2) {
    return {
      refs,
      byConstIndex: new Map(),
      error: null,
      count: 0,
      version: null,
    };
  }

  const state = { offset: 0 };
  let version = 0;
  let count = 0;
  try {
    if (
      bytes.length >= 8 &&
      bytes[0] === 1 &&
      bytes[1] === 0 &&
      bytes[2] === 0 &&
      bytes[3] === 0
    ) {
      version = readConstPoolU32LE(bytes, state, `entry=${entryIndex} version`);
      count = readConstPoolU32LE(bytes, state, `entry=${entryIndex} count`);
    } else {
      version = readConstPoolUleb32(bytes, state, `entry=${entryIndex} version`);
      count = readConstPoolUleb32(bytes, state, `entry=${entryIndex} count`);
    }
    if (version !== 1 && version !== 2) {
      throw new Error(`unsupported const-pool version ${version}`);
    }
    for (let i = 0; i < count; i++) {
      const tag = readConstPoolNat(bytes, state, version, `entry=${entryIndex} const=${i} tag`);
      switch (tag) {
        case 6:
          if (version >= 2) readConstPoolSleb32Raw(bytes, state, `entry=${entryIndex} const=${i} fixnum`);
          else readConstPoolU32LE(bytes, state, `entry=${entryIndex} const=${i} fixnum`);
          break;
        case 10:
          readConstPoolNat(bytes, state, version, `entry=${entryIndex} const=${i} character`);
          break;
        case 11:
          readConstPoolU32LE(bytes, state, `entry=${entryIndex} const=${i} single-float`);
          break;
        case 12:
        case 13:
        case 14:
          readConstPoolU32LE(bytes, state, `entry=${entryIndex} const=${i} hi`);
          readConstPoolU32LE(bytes, state, `entry=${entryIndex} const=${i} lo`);
          break;
        case 15: {
          const digits = readConstPoolNat(bytes, state, version, `entry=${entryIndex} const=${i} bignum digits`);
          for (let j = 0; j < digits; j++) {
            readConstPoolU32LE(bytes, state, `entry=${entryIndex} const=${i} bignum digit=${j}`);
          }
          break;
        }
        case 1:
        case 4: {
          const nameLen = readConstPoolNat(bytes, state, version, `entry=${entryIndex} const=${i} name len`);
          const nameBytes = readConstPoolSpan(bytes, state, nameLen, `entry=${entryIndex} const=${i} name bytes`);
          const pkgLen = readConstPoolNat(bytes, state, version, `entry=${entryIndex} const=${i} pkg len`);
          const pkgBytes = readConstPoolSpan(bytes, state, pkgLen, `entry=${entryIndex} const=${i} pkg bytes`);
          let symbolName = "";
          let packageName = "";
          try {
            symbolName = normalizeSymbolName(UTF8_DECODER.decode(nameBytes));
          } catch {
            symbolName = "";
          }
          try {
            packageName = canonicalizePackageName(
              pkgLen > 0 ? UTF8_DECODER.decode(pkgBytes) : "",
            );
          } catch {
            packageName = "";
          }
          refs.push({
            entry_index: entryIndex >>> 0,
            const_index: i >>> 0,
            tag: tag >>> 0,
            symbol_name: symbolName,
            package_name: packageName,
          });
          break;
        }
        case 2: {
          const len = readConstPoolNat(bytes, state, version, `entry=${entryIndex} const=${i} string len`);
          readConstPoolSpan(bytes, state, len, `entry=${entryIndex} const=${i} string bytes`);
          break;
        }
        case 3:
        case 5: {
          const n = readConstPoolNat(bytes, state, version, `entry=${entryIndex} const=${i} vector count`);
          for (let j = 0; j < n; j++) {
            readConstPoolNat(bytes, state, version, `entry=${entryIndex} const=${i} vector index=${j}`);
          }
          break;
        }
        case 16:
          readConstPoolNat(bytes, state, version, `entry=${entryIndex} const=${i} entry-function`);
          break;
        case 9: {
          readConstPoolNat(bytes, state, version, `entry=${entryIndex} const=${i} gvector subtag`);
          const n = readConstPoolNat(bytes, state, version, `entry=${entryIndex} const=${i} gvector count`);
          for (let j = 0; j < n; j++) {
            readConstPoolNat(bytes, state, version, `entry=${entryIndex} const=${i} gvector index=${j}`);
          }
          break;
        }
        case 7: {
          const len = readConstPoolNat(bytes, state, version, `entry=${entryIndex} const=${i} package len`);
          readConstPoolSpan(bytes, state, len, `entry=${entryIndex} const=${i} package bytes`);
          break;
        }
        case 8:
          readConstPoolNat(bytes, state, version, `entry=${entryIndex} const=${i} cons car`);
          readConstPoolNat(bytes, state, version, `entry=${entryIndex} const=${i} cons cdr`);
          break;
        default:
          throw new Error(`unsupported const-pool tag ${tag} at entry=${entryIndex} const=${i}`);
      }
    }
  } catch (err) {
    return {
      refs: [],
      byConstIndex: new Map(),
      error: err?.message ?? String(err),
      count: count >>> 0,
      version: version >>> 0,
    };
  }

  const byConstIndex = new Map();
  for (const ref of refs) {
    byConstIndex.set(ref.const_index >>> 0, ref);
  }
  return {
    refs,
    byConstIndex,
    error: null,
    count: count >>> 0,
    version: version >>> 0,
  };
}

function resolveFunctionFromMetadata(functionIndex, { packageName, symbolName }) {
  const resolved = resolveFunctionEntry({ packageName, symbolName }, functionIndex);
  if (resolved.status === "resolved") {
    return {
      ok: true,
      entryIndex: resolved.entry_index >>> 0,
      reason: null,
      key: resolved.match_key ?? null,
      source: "runtime-modules-metadata",
    };
  }
  if (resolved.status === "ambiguous") {
    return {
      ok: false,
      entryIndex: null,
      reason: "ambiguous",
      key: resolved.match_key ?? null,
      source: "runtime-modules-metadata",
      alternatives: Array.isArray(resolved.alternatives) ? resolved.alternatives.slice() : [],
    };
  }
  return {
    ok: false,
    entryIndex: null,
    reason: resolved.reason ?? "missing",
    key: resolved.match_key ?? null,
    source: "runtime-modules-metadata",
  };
}

export function augmentStartupBindingMapArtifactWithContractConstPoolFunctions({
  mapArtifact,
  contract = BOOTSTRAP_L0_CONTRACT_V1,
  functions = [],
  resolveFunctionDesignator = null,
  getConstPoolBytesForEntry = null,
} = {}) {
  const stats = {
    schema_version: "startup_binding_map_contract_const_pool_function_build_v3",
    status: "ok",
    enabled: false,
    required_pool_count: 0,
    required_ref_count: 0,
    required_callable_count: 0,
    required_special_count: 0,
    seed_ref_count: 0,
    seed_symbol_ref_count: 0,
    seed_callable_count: 0,
    seed_refs_non_symbol: 0,
    symbol_refs_examined: 0,
    symbol_refs_non_symbol: 0,
    symbol_refs_named: 0,
    symbol_refs_filtered_non_callable: 0,
    symbol_refs_filtered_keyword: 0,
    resolver_resolved: 0,
    resolver_unresolved: 0,
    resolver_ambiguous: 0,
    resolver_symbol_name_fallback_skipped: 0,
    resolver_keyword_package_skipped: 0,
    const_pool_entries_requested: 0,
    const_pool_entries_available: 0,
    const_pool_entries_missing: 0,
    const_pool_decode_failures: 0,
    const_pool_decode_error_sample: null,
    transitive_const_pool_entries_scanned: 0,
    transitive_const_pool_refs_queued: 0,
    transitive_callable_refs_queued: 0,
    transitive_const_pool_refs_non_symbol: 0,
    transitive_const_pool_refs_filtered_keyword: 0,
    transitive_const_pool_refs_filtered_non_callable: 0,
    emitted_entries: 0,
    upgraded_existing_entries: 0,
    symbol_anchor_candidates: 0,
    symbol_anchor_candidates_required_special: 0,
    symbol_anchor_candidates_non_special: 0,
    symbol_anchor_entry_upgrades: 0,
    symbol_anchor_existing_preserved: 0,
    required_special_anchors_present: 0,
    required_special_anchors_missing: 0,
    skipped_existing_entry_backed: 0,
    skipped_duplicate_refs: 0,
    missing_const_pool_provider: false,
  };

  const requiredConstPools = Array.isArray(contract?.requiredConstPools)
    ? contract.requiredConstPools
    : [];
  stats.required_pool_count = requiredConstPools.length >>> 0;

  const requiredRefs = [];
  const seenRequiredRefKeys = new Set();
  for (const pool of requiredConstPools) {
    const entryIndex = Number(pool?.entryIndex);
    if (!Number.isInteger(entryIndex) || entryIndex < 0) continue;
    for (const rawRef of Array.isArray(pool?.requiredRefs) ? pool.requiredRefs : []) {
      const constIndex = Number(rawRef);
      if (!Number.isInteger(constIndex) || constIndex < 0) continue;
      const key = `${entryIndex >>> 0}:${constIndex >>> 0}`;
      if (seenRequiredRefKeys.has(key)) continue;
      seenRequiredRefKeys.add(key);
      requiredRefs.push({
        entry_index: entryIndex >>> 0,
        const_index: constIndex >>> 0,
      });
    }
  }
  stats.required_ref_count = requiredRefs.length >>> 0;

  const requiredCallables = Array.isArray(contract?.requiredCallables)
    ? contract.requiredCallables
    : [];
  stats.required_callable_count = requiredCallables.length >>> 0;
  const requiredSpecialVariables = Array.isArray(contract?.requiredSpecialVariables)
    ? contract.requiredSpecialVariables
    : [];
  const requiredSpecialSymbolKeys = new Set();
  for (const item of requiredSpecialVariables) {
    const symbolKey = makeSymbolKey(item?.packageName ?? "", item?.symbolName ?? "");
    if (!symbolKey) continue;
    requiredSpecialSymbolKeys.add(symbolKey);
  }
  stats.required_special_count = requiredSpecialSymbolKeys.size >>> 0;

  if (requiredRefs.length === 0 && requiredCallables.length === 0) {
    return { changed: false, mapArtifact, stats };
  }

  const canLoadConstPools = typeof getConstPoolBytesForEntry === "function";
  if (!canLoadConstPools && requiredRefs.length > 0) {
    stats.status = "degraded";
    stats.missing_const_pool_provider = true;
  }

  stats.enabled = true;
  stats.seed_ref_count = requiredRefs.length >>> 0;

  const functionIndex = buildFunctionIndex(functions);
  const hasCallableMetadata = ({ packageName, symbolName }) => {
    const normalizedSymbol = normalizeSymbolName(symbolName);
    if (!normalizedSymbol) return false;
    const normalizedPackage = canonicalizePackageName(packageName);
    if (normalizedPackage) {
      const symbolKey = makeSymbolKey(normalizedPackage, normalizedSymbol);
      if (!symbolKey) return false;
      return functionIndex.bySymbolKey.has(symbolKey);
    }
    return functionIndex.byName.has(normalizedSymbol);
  };

  const resolver = typeof resolveFunctionDesignator === "function"
    ? ({ packageName, symbolName }) => {
      const resolved = resolveFunctionDesignator({
        name: normalizeSymbolName(symbolName),
        packageName: canonicalizePackageName(packageName),
      });
      if (resolved?.ok) {
        return {
          ok: true,
          entryIndex: resolved.entryIndex >>> 0,
          reason: null,
          key: resolved.key ?? null,
          source: resolved.source ?? null,
        };
      }
      return {
        ok: false,
        entryIndex: null,
        reason: resolved?.reason ?? "missing",
        key: resolved?.key ?? null,
        source: resolved?.source ?? null,
        alternatives: Array.isArray(resolved?.alternatives) ? resolved.alternatives.slice() : [],
      };
    }
    : (spec) => resolveFunctionFromMetadata(functionIndex, spec);

  const entries = Array.isArray(mapArtifact?.entries) ? mapArtifact.entries.map((entry) => ({ ...entry })) : [];
  const functionEntryIndexBySymbolKey = new Map();
  for (let i = 0; i < entries.length; i++) {
    const entry = entries[i];
    const targetCell = normalizeEntryTargetCell(entry);
    if (targetCell !== "fcell") continue;
    const packageName = canonicalizePackageName(entry?.package_name ?? "");
    const symbolName = normalizeSymbolName(entry?.symbol_name ?? "");
    const symbolKey = makeSymbolKey(packageName, symbolName);
    if (!symbolKey) continue;
    functionEntryIndexBySymbolKey.set(symbolKey, i);
  }

  const parsedConstPoolByEntry = new Map();
  const loadConstPoolRefs = (entryIndexRaw) => {
    const entryIndex = entryIndexRaw >>> 0;
    if (parsedConstPoolByEntry.has(entryIndex)) {
      return parsedConstPoolByEntry.get(entryIndex);
    }
    stats.const_pool_entries_requested++;
    let bytes = null;
    try {
      bytes = getConstPoolBytesForEntry(entryIndex);
    } catch (_err) {
      bytes = null;
    }
    const byteView = bytes instanceof Uint8Array
      ? bytes
      : (bytes == null ? null : Uint8Array.from(bytes));
    if (!(byteView instanceof Uint8Array) || byteView.length === 0) {
      stats.const_pool_entries_missing++;
      const empty = {
        refs: [],
        byConstIndex: new Map(),
        available: false,
      };
      parsedConstPoolByEntry.set(entryIndex, empty);
      return empty;
    }
    stats.const_pool_entries_available++;
    const parsed = parseConstPoolSymbolRefsFromBytes(byteView, entryIndex);
    if (parsed.error) {
      stats.const_pool_decode_failures++;
      if (stats.const_pool_decode_error_sample == null) {
        stats.const_pool_decode_error_sample = parsed.error;
      }
      const failed = {
        refs: [],
        byConstIndex: new Map(),
        available: true,
      };
      parsedConstPoolByEntry.set(entryIndex, failed);
      return failed;
    }
    const loaded = {
      refs: parsed.refs,
      byConstIndex: parsed.byConstIndex,
      available: true,
    };
    parsedConstPoolByEntry.set(entryIndex, loaded);
    return loaded;
  };

  const pendingRefs = [];
  const seenRefKeys = new Set();
  const seenSyntheticSymbolKeys = new Set();
  const enqueueRef = (ref, depth = 0, { source = "contract-required-const-pool-ref" } = {}) => {
    const entryIndex = Number(ref?.entry_index);
    const constIndex = Number(ref?.const_index);
    if (!Number.isInteger(entryIndex) || entryIndex < 0 || !Number.isInteger(constIndex) || constIndex < 0) {
      return false;
    }
    const key = `${entryIndex >>> 0}:${constIndex >>> 0}`;
    if (seenRefKeys.has(key)) {
      stats.skipped_duplicate_refs++;
      return false;
    }
    seenRefKeys.add(key);
    pendingRefs.push({
      entry_index: entryIndex >>> 0,
      const_index: constIndex >>> 0,
      package_name: canonicalizePackageName(ref.package_name ?? ""),
      symbol_name: normalizeSymbolName(ref.symbol_name ?? ""),
      tag: Number.isFinite(ref.tag) ? (ref.tag >>> 0) : null,
      depth: Math.max(0, depth | 0),
      source,
    });
    return true;
  };
  const enqueueCallableSeed = ({ package_name, symbol_name } = {}) => {
    const packageName = canonicalizePackageName(package_name);
    const symbolName = normalizeSymbolName(symbol_name);
    if (!symbolName) return false;
    const key = `${packageName}::${symbolName}`;
    if (seenSyntheticSymbolKeys.has(key)) {
      stats.skipped_duplicate_refs++;
      return false;
    }
    seenSyntheticSymbolKeys.add(key);
    pendingRefs.push({
      entry_index: null,
      const_index: null,
      package_name: packageName,
      symbol_name: symbolName,
      tag: null,
      depth: 0,
      source: "contract-required-callable",
    });
    return true;
  };

  if (canLoadConstPools) {
    for (const required of requiredRefs) {
      const poolRefs = loadConstPoolRefs(required.entry_index);
      const parsedRef = poolRefs.byConstIndex.get(required.const_index >>> 0);
      if (!parsedRef) {
        stats.seed_refs_non_symbol++;
        continue;
      }
      if (enqueueRef(parsedRef, 0, { source: "contract-required-const-pool-ref" })) {
        stats.seed_symbol_ref_count++;
      }
    }
  }

  for (const item of requiredCallables) {
    if (enqueueCallableSeed({
      package_name: item?.packageName ?? "",
      symbol_name: item?.symbolName ?? "",
    })) {
      stats.seed_callable_count++;
    }
  }

  const definitionDepth = (definition) => {
    if (!definition || typeof definition !== "object") return Number.MAX_SAFE_INTEGER;
    const depth = Number(definition.const_pool_depth);
    if (!Number.isInteger(depth) || depth < 0) return Number.MAX_SAFE_INTEGER;
    return depth >>> 0;
  };
  const hasConstPoolDefinition = (definition) => (
    definition &&
    typeof definition === "object" &&
    Number.isInteger(definition.entry_index) &&
    definition.entry_index >= 0 &&
    Number.isInteger(definition.const_index) &&
    definition.const_index >= 0
  );
  const shouldPreferDefinition = (existingDefinition, candidateDefinition) => {
    const candidateValid = hasConstPoolDefinition(candidateDefinition);
    if (!candidateValid) return false;
    const existingValid = hasConstPoolDefinition(existingDefinition);
    if (!existingValid) return true;
    const existingDepth = definitionDepth(existingDefinition);
    const candidateDepth = definitionDepth(candidateDefinition);
    if (candidateDepth < existingDepth) return true;
    if (candidateDepth > existingDepth) return false;
    const existingEntryIndex = existingDefinition.entry_index >>> 0;
    const candidateEntryIndex = candidateDefinition.entry_index >>> 0;
    if (candidateEntryIndex < existingEntryIndex) return true;
    if (candidateEntryIndex > existingEntryIndex) return false;
    return (candidateDefinition.const_index >>> 0) < (existingDefinition.const_index >>> 0);
  };
  const symbolAnchorBySymbolKey = new Map();
  const recordSymbolAnchor = (symbolKey, candidateDefinition) => {
    if (!symbolKey || !hasConstPoolDefinition(candidateDefinition)) return;
    const existing = symbolAnchorBySymbolKey.get(symbolKey) ?? null;
    if (!existing || shouldPreferDefinition(existing, candidateDefinition)) {
      symbolAnchorBySymbolKey.set(symbolKey, {
        entry_index: candidateDefinition.entry_index >>> 0,
        const_index: candidateDefinition.const_index >>> 0,
        const_tag: Number.isFinite(candidateDefinition.const_tag)
          ? (candidateDefinition.const_tag >>> 0)
          : null,
        const_pool_depth: Number.isFinite(candidateDefinition.const_pool_depth)
          ? (candidateDefinition.const_pool_depth >>> 0)
          : 0,
        const_pool_source: typeof candidateDefinition.const_pool_source === "string"
          ? candidateDefinition.const_pool_source
          : "contract-required-const-pool-ref",
      });
    }
  };

  const scannedResolvedEntries = new Set();
  let cursor = 0;
  while (cursor < pendingRefs.length) {
    const ref = pendingRefs[cursor++];
    stats.symbol_refs_examined++;
    const symbolName = normalizeSymbolName(ref.symbol_name);
    if (!symbolName) {
      stats.symbol_refs_non_symbol++;
      continue;
    }
    stats.symbol_refs_named++;
    const packageName = canonicalizePackageName(ref.package_name);
    const refDefinition = hasConstPoolDefinition(ref)
      ? {
        entry_index: ref.entry_index >>> 0,
        const_index: ref.const_index >>> 0,
        const_tag: ref.tag,
        const_pool_depth: Math.max(0, ref.depth | 0),
        const_pool_source: typeof ref.source === "string" && ref.source.length > 0
          ? ref.source
          : "contract-required-const-pool-ref",
      }
      : null;
    if (packageName === "KEYWORD") {
      stats.resolver_keyword_package_skipped++;
      stats.symbol_refs_filtered_keyword++;
      continue;
    }
    const packageForSymbolKey = packageName || "CCL";
    const refSymbolKey = makeSymbolKey(packageForSymbolKey, symbolName);
    if (refSymbolKey && refDefinition) {
      recordSymbolAnchor(refSymbolKey, refDefinition);
    }
    const isRequiredCallableSeed = ref.source === "contract-required-callable";
    if (!isRequiredCallableSeed && !hasCallableMetadata({ packageName, symbolName })) {
      stats.symbol_refs_filtered_non_callable++;
      continue;
    }

    const resolution = resolver({ packageName, symbolName });
    if (!resolution?.ok) {
      if (resolution?.reason === "ambiguous") stats.resolver_ambiguous++;
      else stats.resolver_unresolved++;
      continue;
    }
    if (packageName && resolution?.key !== "symbol-key") {
      stats.resolver_symbol_name_fallback_skipped++;
      continue;
    }
    stats.resolver_resolved++;
    const resolvedEntryIndex = resolution.entryIndex >>> 0;

    const resolvedPackageName = packageForSymbolKey;
    const symbolKey = makeSymbolKey(resolvedPackageName, symbolName);
    if (!symbolKey) continue;
    const definition = refDefinition ? {
      ...refDefinition,
    } : null;
    const source = typeof ref.source === "string" && ref.source.length > 0
      ? ref.source
      : (definition ? "contract-required-const-pool-ref" : "contract-required-callable");

    const existingIndex = functionEntryIndexBySymbolKey.get(symbolKey);
    if (existingIndex != null) {
      const existing = entries[existingIndex];
      const existingAvailability = String(existing?.availability ?? "").toLowerCase();
      const existingInitializerKind = String(existing?.initializer?.kind ?? "").toLowerCase();
      const existingEntryIndex = Number(existing?.initializer?.entry_index);
      const replaceDefinition = shouldPreferDefinition(existing?.definition ?? null, definition);
      const definitionSatisfied = !replaceDefinition;
      if (
        existingAvailability === "entry-backed" &&
        existingInitializerKind === "entry-function" &&
        Number.isInteger(existingEntryIndex) &&
        (existingEntryIndex >>> 0) === resolvedEntryIndex &&
        definitionSatisfied
      ) {
        stats.skipped_existing_entry_backed++;
      } else {
        entries[existingIndex] = {
          ...existing,
          binding_class: "function",
          target_cell: "fcell",
          package_name: resolvedPackageName,
          symbol_name: symbolName,
          symbol_key: symbolKey,
          source,
          require_non_nil: false,
          definition: replaceDefinition ? definition : (existing?.definition ?? null),
          availability: "entry-backed",
          initializer: {
            kind: "entry-function",
            function_name: symbolName,
            entry_index: resolvedEntryIndex,
            match_key: resolution?.key ?? null,
            source: resolution?.source ?? null,
          },
        };
        stats.upgraded_existing_entries++;
      }
    } else {
      const entry = {
        binding_class: "function",
        target_cell: "fcell",
        package_name: resolvedPackageName,
        symbol_name: symbolName,
        symbol_key: symbolKey,
        source,
        require_non_nil: false,
        definition,
        availability: "entry-backed",
        initializer: {
          kind: "entry-function",
          function_name: symbolName,
          entry_index: resolvedEntryIndex,
          match_key: resolution?.key ?? null,
          source: resolution?.source ?? null,
        },
      };
      functionEntryIndexBySymbolKey.set(symbolKey, entries.length);
      entries.push(entry);
      stats.emitted_entries++;
    }

    if (!canLoadConstPools || scannedResolvedEntries.has(resolvedEntryIndex)) continue;
    scannedResolvedEntries.add(resolvedEntryIndex);
    const transitive = loadConstPoolRefs(resolvedEntryIndex);
    if (!transitive.available) continue;
    stats.transitive_const_pool_entries_scanned++;
    stats.transitive_const_pool_refs_queued += transitive.refs.length >>> 0;
    for (const item of transitive.refs) {
      const transitiveSymbolName = normalizeSymbolName(item?.symbol_name ?? "");
      const transitivePackageName = canonicalizePackageName(item?.package_name ?? "");
      if (!transitiveSymbolName) {
        stats.transitive_const_pool_refs_non_symbol++;
        continue;
      }
      if (transitivePackageName === "KEYWORD") {
        stats.transitive_const_pool_refs_filtered_keyword++;
        continue;
      }
      if (!hasCallableMetadata({ packageName: transitivePackageName, symbolName: transitiveSymbolName })) {
        stats.transitive_const_pool_refs_filtered_non_callable++;
        continue;
      }
      if (enqueueRef({
        ...item,
        package_name: transitivePackageName,
        symbol_name: transitiveSymbolName,
      }, (ref.depth | 0) + 1, { source: "contract-required-const-pool-ref" })) {
        stats.transitive_callable_refs_queued++;
      }
    }
  }

  stats.symbol_anchor_candidates = symbolAnchorBySymbolKey.size >>> 0;
  let requiredSpecialAnchorCandidates = 0;
  for (const symbolKey of symbolAnchorBySymbolKey.keys()) {
    if (requiredSpecialSymbolKeys.has(symbolKey)) {
      requiredSpecialAnchorCandidates++;
    }
  }
  stats.symbol_anchor_candidates_required_special = requiredSpecialAnchorCandidates >>> 0;
  stats.symbol_anchor_candidates_non_special =
    Math.max(0, (symbolAnchorBySymbolKey.size - requiredSpecialAnchorCandidates) | 0) >>> 0;

  const entryIndexBySymbolKey = new Map();
  for (let i = 0; i < entries.length; i++) {
    const entry = entries[i];
    const packageName = canonicalizePackageName(entry?.package_name ?? "");
    const symbolName = normalizeSymbolName(entry?.symbol_name ?? "");
    const symbolKey = makeSymbolKey(packageName, symbolName);
    if (!symbolKey || entryIndexBySymbolKey.has(symbolKey)) continue;
    entryIndexBySymbolKey.set(symbolKey, i);
  }

  for (const [symbolKey, candidateDefinition] of symbolAnchorBySymbolKey.entries()) {
    const existingIndex = entryIndexBySymbolKey.get(symbolKey);
    if (existingIndex == null) continue;
    const entry = entries[existingIndex];
    const existingDefinition = (
      entry?.definition &&
      typeof entry.definition === "object" &&
      !Array.isArray(entry.definition)
    )
      ? entry.definition
      : null;
    const replaceDefinition = shouldPreferDefinition(existingDefinition, candidateDefinition);
    if (!replaceDefinition && hasConstPoolDefinition(existingDefinition)) {
      stats.symbol_anchor_existing_preserved++;
      continue;
    }
    const mergedDefinition = {
      ...(existingDefinition ?? {}),
      entry_index: candidateDefinition.entry_index >>> 0,
      const_index: candidateDefinition.const_index >>> 0,
      const_tag: Number.isFinite(candidateDefinition.const_tag)
        ? (candidateDefinition.const_tag >>> 0)
        : null,
      const_pool_depth: Number.isFinite(candidateDefinition.const_pool_depth)
        ? (candidateDefinition.const_pool_depth >>> 0)
        : 0,
      const_pool_source: typeof candidateDefinition.const_pool_source === "string"
        ? candidateDefinition.const_pool_source
        : "contract-required-const-pool-ref",
    };
    entries[existingIndex] = {
      ...entry,
      definition: mergedDefinition,
    };
    stats.symbol_anchor_entry_upgrades++;
  }

  let requiredSpecialAnchorsPresent = 0;
  let requiredSpecialAnchorsMissing = 0;
  for (const symbolKey of requiredSpecialSymbolKeys.values()) {
    const entryIndex = entryIndexBySymbolKey.get(symbolKey);
    const entry = entryIndex == null ? null : entries[entryIndex];
    if (hasConstPoolDefinition(entry?.definition)) requiredSpecialAnchorsPresent++;
    else requiredSpecialAnchorsMissing++;
  }
  stats.required_special_anchors_present = requiredSpecialAnchorsPresent >>> 0;
  stats.required_special_anchors_missing = requiredSpecialAnchorsMissing >>> 0;

  const coverage = mapArtifact?.coverage && typeof mapArtifact.coverage === "object"
    ? { ...mapArtifact.coverage }
    : {};
  coverage.contract_required_const_pool_function_bindings = stats;
  const nextArtifact = {
    ...(mapArtifact ?? {}),
    schema_version: mapArtifact?.schema_version ?? STARTUP_BINDING_MAP_SCHEMA_V1,
    generator: mapArtifact?.generator ?? STARTUP_BINDING_MAP_GENERATOR_V1,
    contract_id: mapArtifact?.contract_id ?? (typeof contract?.id === "string" ? contract.id : null),
    coverage,
    entries,
    counts: summarizeEntries(entries),
  };
  return {
    changed: (stats.emitted_entries + stats.upgraded_existing_entries + stats.symbol_anchor_entry_upgrades) > 0,
    mapArtifact: nextArtifact,
    stats,
  };
}

export async function buildStartupBindingMapArtifact({
  repoRoot,
  contract = BOOTSTRAP_L0_CONTRACT_V1,
  functions = [],
} = {}) {
  const scriptDir = path.dirname(fileURLToPath(import.meta.url));
  const rootDir = path.resolve(repoRoot ?? path.resolve(scriptDir, "../../.."));
  const requiredSpecialVariables = Array.isArray(contract?.requiredSpecialVariables)
    ? contract.requiredSpecialVariables
    : [];
  const functionIndex = buildFunctionIndex(functions);
  const specialDefinitions = await scanSpecialBindingDefinitions(rootDir);
  const level0Scan = await scanLevel0FunctionDesignators(rootDir);

  const entries = [];
  const entryBySymbolKey = new Map();
  const level0BindingStats = {
    discovered_symbols: level0Scan.stats.unique_symbol_designators >>> 0,
    emitted_entries: 0,
    entry_backed: 0,
    deferred: 0,
    unsupported: 0,
  };
  const requiredSpecialBindingStats = {
    required_contract_items: requiredSpecialVariables.length >>> 0,
    emitted_entries: 0,
    skipped_invalid_contract_items: 0,
    definition_found: 0,
    definition_missing: 0,
    availability: {
      literal: 0,
      entry_backed: 0,
      deferred: 0,
      unsupported: 0,
    },
    require_non_nil: 0,
    require_non_nil_with_initializer: 0,
    require_non_nil_without_initializer: 0,
  };
  const runtimeBindingStats = {
    emitted_entries: 0,
    entry_backed: 0,
    deferred: 0,
    unsupported: 0,
    skipped_non_symbol_designators: 0,
    skipped_duplicate_symbol_keys: 0,
  };

  // Contract-required specials/constants are emitted as explicit vcell bindings.
  for (const item of requiredSpecialVariables) {
    const packageName = canonicalizePackageName(item?.packageName ?? "");
    const symbolName = normalizeSymbolName(item?.symbolName ?? "");
    if (!packageName || !symbolName) {
      requiredSpecialBindingStats.skipped_invalid_contract_items++;
      continue;
    }
    const symbolKey = makeSymbolKey(packageName, symbolName);
    const definition = specialDefinitions.get(symbolKey) ?? null;
    if (definition) requiredSpecialBindingStats.definition_found++;
    else requiredSpecialBindingStats.definition_missing++;

    let availability = "deferred";
    let initializer = {
      kind: "deferred",
      reason: "definition-not-found",
    };
    if (definition?.init_token) {
      const classified = classifyInitializerToken(definition.init_token, functionIndex);
      availability = classified.availability;
      initializer = classified.initializer;
    } else if (definition && !definition.init_token) {
      initializer = {
        kind: "deferred",
        reason: "no-initform",
      };
    }
    switch (availability) {
      case "literal":
      case "entry-backed":
      case "unsupported":
        requiredSpecialBindingStats.availability[availability]++;
        break;
      case "deferred":
      default:
        requiredSpecialBindingStats.availability.deferred++;
        break;
    }
    const requireNonNil = Boolean(item?.requireNonNil);
    if (requireNonNil) {
      requiredSpecialBindingStats.require_non_nil++;
      if (availability === "literal" || availability === "entry-backed") {
        requiredSpecialBindingStats.require_non_nil_with_initializer++;
      } else {
        requiredSpecialBindingStats.require_non_nil_without_initializer++;
      }
    }

    const entry = {
      binding_class: "special-variable",
      target_cell: "vcell",
      package_name: packageName,
      symbol_name: symbolName,
      symbol_key: symbolKey,
      source: typeof item?.source === "string" ? item.source : null,
      require_non_nil: requireNonNil,
      definition: definition ? {
        form_kind: definition.form_kind,
        file: definition.file,
        line: definition.line >>> 0,
        init_token: definition.init_token,
      } : null,
      availability,
      initializer,
    };
    entries.push(entry);
    entryBySymbolKey.set(symbolKey, entry);
    requiredSpecialBindingStats.emitted_entries++;
  }

  for (const definition of level0Scan.definitions.values()) {
    const symbolKey = definition.symbol_key;
    if (!symbolKey || entryBySymbolKey.has(symbolKey)) {
      continue;
    }

    const classified = classifyFunctionBindingInitializer({
      packageName: definition.package_name,
      symbolName: definition.symbol_name,
    }, functionIndex);
    switch (classified.availability) {
      case "entry-backed":
        level0BindingStats.entry_backed++;
        break;
      case "unsupported":
        level0BindingStats.unsupported++;
        break;
      case "deferred":
      default:
        level0BindingStats.deferred++;
        break;
    }
    level0BindingStats.emitted_entries++;

    const entry = {
      binding_class: "function",
      target_cell: "fcell",
      package_name: definition.package_name,
      symbol_name: definition.symbol_name,
      symbol_key: symbolKey,
      source: "level-0-source-scan",
      require_non_nil: false,
      definition: {
        form_kind: definition.form_kind,
        file: definition.file,
        line: definition.line >>> 0,
        designator_token: definition.designator_token,
        duplicates: definition.duplicates >>> 0,
      },
      availability: classified.availability,
      initializer: classified.initializer,
    };
    entries.push(entry);
    entryBySymbolKey.set(symbolKey, entry);
  }

  const coverage = {
    schema_version: STARTUP_BINDING_MAP_COVERAGE_SCHEMA_V1,
    required_special_variable_bindings: requiredSpecialBindingStats,
    level0_source_scan: level0Scan.stats,
    level0_function_bindings: level0BindingStats,
    runtime_function_metadata: {
      ...functionIndex.stats,
      ...runtimeBindingStats,
    },
  };

  return {
    schema_version: STARTUP_BINDING_MAP_SCHEMA_V1,
    generator: STARTUP_BINDING_MAP_GENERATOR_V1,
    contract_id: typeof contract?.id === "string" ? contract.id : null,
    coverage,
    entries,
    counts: summarizeEntries(entries),
  };
}
