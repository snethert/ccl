import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { BOOTSTRAP_L0_CONTRACT_V1 } from "./bootstrap-l0-contract.mjs";

export const STARTUP_BINDING_MAP_SCHEMA_V1 = "startup_binding_map_v1";
const STARTUP_BINDING_MAP_GENERATOR_V1 = "startup_binding_map_generator_v1";
const STARTUP_BINDING_MAP_COVERAGE_SCHEMA_V1 = "startup_binding_map_coverage_v1";

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
    level0_source_scan: coverage.level0_source_scan ?? null,
    level0_function_bindings: coverage.level0_function_bindings ?? null,
    runtime_function_metadata: coverage.runtime_function_metadata ?? null,
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
  const runtimeBindingStats = {
    emitted_entries: 0,
    entry_backed: 0,
    deferred: 0,
    unsupported: 0,
    skipped_non_symbol_designators: 0,
    skipped_duplicate_symbol_keys: 0,
  };

  for (const item of requiredSpecialVariables) {
    const packageName = canonicalizePackageName(item?.packageName ?? "");
    const symbolName = normalizeSymbolName(item?.symbolName ?? "");
    if (!packageName || !symbolName) continue;
    const symbolKey = makeSymbolKey(packageName, symbolName);
    const definition = specialDefinitions.get(symbolKey) ?? null;

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

    const entry = {
      binding_class: "special-variable",
      target_cell: "vcell",
      package_name: packageName,
      symbol_name: symbolName,
      symbol_key: symbolKey,
      source: typeof item?.source === "string" ? item.source : null,
      require_non_nil: Boolean(item?.requireNonNil),
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
