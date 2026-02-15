import { BOOTSTRAP_L0_CONTRACT_V1 } from "./bootstrap-l0-contract.mjs";

export const STARTUP_BINDING_MAP_SCHEMA_V1 = "startup_binding_map_v1";
const STARTUP_BINDING_MAP_GENERATOR_V1 = "startup_binding_map_generator_v1";
const STARTUP_BINDING_MAP_COVERAGE_SCHEMA_V1 = "startup_binding_map_coverage_v1";
const STARTUP_SHADOW_TABLE_SCHEMA_V1 = "startup_shadow_table_v1";
const UTF8_DECODER = new TextDecoder("utf-8");
const STARTUP_BINDING_MAP_INPUT_CONTRACT_V1 = Object.freeze({
  // Active pipeline contract: scope artifact + resolution artifact are source of truth.
  // artifact-only active path: no JS source scan.
  mode: "artifact-only",
  scope_input: "scope artifact",
  resolution_input: "resolution artifact",
  source_scan_policy: "no JS source scan",
});
const STARTUP_SYMBOL_REQUIRED_CLASS = Object.freeze({
  REQUIRED_CALLABLE: "required-callable",
  REQUIRED_SPECIAL: "required-special",
  OPTIONAL: "optional",
  NONE: "none",
});
const STARTUP_SYMBOL_RESOLUTION_STATUS = Object.freeze({
  RESOLVED: "resolved",
  UNRESOLVED: "unresolved",
  PROBE_ERROR: "probe-error",
  INVALID_INPUT: "invalid-input",
});

const FIXNUM_MIN = -0x20000000; // -536870912
const FIXNUM_MAX = 0x1fffffff; // 536870911

const LEVEL0_DEFAULT_PACKAGE = "CCL";
const PACKAGE_ALIASES = Object.freeze({
  CL: "COMMON-LISP",
  CCL: "CCL",
  "COMMON-LISP": "COMMON-LISP",
  "COMMON-LISP-USER": "COMMON-LISP-USER",
  KEYWORD: "KEYWORD",
});

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

function parseSymbolKey(symbolKey) {
  const raw = normalizeToken(symbolKey);
  const separatorIndex = raw.indexOf("::");
  if (separatorIndex <= 0) return null;
  const packageName = canonicalizePackageName(raw.slice(0, separatorIndex));
  const symbolName = normalizeSymbolName(raw.slice(separatorIndex + 2));
  if (!packageName || !symbolName) return null;
  return {
    package_name: packageName,
    symbol_name: symbolName,
  };
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

function normalizeContractSpecialInitializerKind(value) {
  const kind = normalizeToken(value).toLowerCase();
  switch (kind) {
    case "literal-fixnum":
    case "literal-nil":
    case "literal-symbol":
    case "literal-keyword":
      return kind;
    default:
      return "";
  }
}

function classifyContractSpecialVariableInitializer(initializerSpec) {
  if (!initializerSpec || typeof initializerSpec !== "object" || Array.isArray(initializerSpec)) {
    return {
      availability: "unsupported",
      initializer: {
        kind: "unsupported",
        reason: "invalid-contract-initializer-object",
      },
    };
  }
  const kind = normalizeContractSpecialInitializerKind(initializerSpec.kind);
  if (!kind) {
    return {
      availability: "unsupported",
      initializer: {
        kind: "unsupported",
        reason: "invalid-contract-initializer-kind",
      },
    };
  }

  if (kind === "literal-fixnum") {
    const rawValue =
      initializerSpec.fixnum_value ??
      initializerSpec.fixnumValue ??
      initializerSpec.value ??
      null;
    let value = Number(rawValue);
    if (typeof rawValue === "string" && /^[+-]?\d+$/u.test(rawValue.trim())) {
      value = Number.parseInt(rawValue, 10);
    }
    if (!Number.isSafeInteger(value)) {
      return {
        availability: "unsupported",
        initializer: {
          kind: "unsupported",
          reason: "invalid-contract-fixnum",
          fixnum_value: rawValue,
        },
      };
    }
    if (value < FIXNUM_MIN || value > FIXNUM_MAX) {
      return {
        availability: "unsupported",
        initializer: {
          kind: "unsupported",
          reason: "contract-fixnum-range",
          fixnum_value: value,
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

  if (kind === "literal-nil") {
    return {
      availability: "literal",
      initializer: {
        kind: "literal-nil",
      },
    };
  }

  if (kind === "literal-symbol") {
    const literalPackageName = canonicalizePackageName(
      initializerSpec.literal_package_name ??
      initializerSpec.literalPackageName ??
      initializerSpec.package_name ??
      initializerSpec.packageName ??
      initializerSpec.package ??
      "",
    );
    const literalSymbolName = normalizeSymbolName(
      initializerSpec.literal_symbol_name ??
      initializerSpec.literalSymbolName ??
      initializerSpec.symbol_name ??
      initializerSpec.symbolName ??
      initializerSpec.name ??
      "",
    );
    if (!literalPackageName || !literalSymbolName) {
      return {
        availability: "unsupported",
        initializer: {
          kind: "unsupported",
          reason: "invalid-contract-literal-symbol",
        },
      };
    }
    return {
      availability: "literal",
      initializer: {
        kind: "literal-symbol",
        literal_package_name: literalPackageName,
        literal_symbol_name: literalSymbolName,
      },
    };
  }

  const literalKeywordName = normalizeSymbolName(
    initializerSpec.literal_keyword_name ??
    initializerSpec.literalKeywordName ??
    initializerSpec.keyword_name ??
    initializerSpec.keywordName ??
    initializerSpec.symbol_name ??
    initializerSpec.symbolName ??
    initializerSpec.name ??
    "",
  );
  if (!literalKeywordName) {
    return {
      availability: "unsupported",
      initializer: {
        kind: "unsupported",
        reason: "invalid-contract-literal-keyword",
      },
    };
  }
  return {
    availability: "literal",
    initializer: {
      kind: "literal-keyword",
      literal_keyword_name: literalKeywordName,
    },
  };
}

function makeEntryBindingKey(targetCell, symbolKey) {
  const normalizedTargetCell = normalizeToken(targetCell).toLowerCase() === "fcell"
    ? "fcell"
    : "vcell";
  if (!symbolKey) return "";
  return `${normalizedTargetCell}:${symbolKey}`;
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
    artifact_inputs: coverage.artifact_inputs ?? null,
    required_special_variable_bindings: coverage.required_special_variable_bindings ?? null,
    level0_source_scan: coverage.level0_source_scan ?? null,
    level0_function_bindings: coverage.level0_function_bindings ?? null,
    runtime_function_metadata: coverage.runtime_function_metadata ?? null,
    contract_required_const_pool_function_bindings:
      coverage.contract_required_const_pool_function_bindings ?? null,
  };
}

function normalizeStartupShadowTable(shadowTable) {
  if (!shadowTable || typeof shadowTable !== "object" || Array.isArray(shadowTable)) return null;
  const normalizedPreinstallEntries = [];
  const seenPreinstallEntries = new Set();
  for (const value of Array.isArray(shadowTable.preinstall_const_pool_entries)
    ? shadowTable.preinstall_const_pool_entries
    : []) {
    const entryIndex = Number(value);
    if (!Number.isInteger(entryIndex) || entryIndex < 0) continue;
    const normalized = entryIndex >>> 0;
    if (seenPreinstallEntries.has(normalized)) continue;
    seenPreinstallEntries.add(normalized);
    normalizedPreinstallEntries.push(normalized);
  }
  normalizedPreinstallEntries.sort((a, b) => a - b);
  return {
    schema_version: typeof shadowTable.schema_version === "string"
      ? shadowTable.schema_version
      : STARTUP_SHADOW_TABLE_SCHEMA_V1,
    phase: typeof shadowTable.phase === "string" ? shadowTable.phase : "pre-fasload",
    contract_id: typeof shadowTable.contract_id === "string" ? shadowTable.contract_id : null,
    preinstall_const_pool_entries: normalizedPreinstallEntries,
    preinstall_const_pool_entry_count: normalizedPreinstallEntries.length >>> 0,
    binding_entry_count: Number.isInteger(shadowTable.binding_entry_count)
      ? (shadowTable.binding_entry_count >>> 0)
      : 0,
    entry_backed_binding_count: Number.isInteger(shadowTable.entry_backed_binding_count)
      ? (shadowTable.entry_backed_binding_count >>> 0)
      : 0,
  };
}

function buildStartupShadowTable({
  contract = BOOTSTRAP_L0_CONTRACT_V1,
  entries = [],
  closureConstPoolEntryIndices = [],
} = {}) {
  const preinstallConstPoolEntries = new Set();
  for (const pool of Array.isArray(contract?.requiredConstPools) ? contract.requiredConstPools : []) {
    const entryIndex = Number(pool?.entryIndex);
    if (!Number.isInteger(entryIndex) || entryIndex < 0) continue;
    preinstallConstPoolEntries.add(entryIndex >>> 0);
  }
  for (const value of Array.isArray(closureConstPoolEntryIndices) ? closureConstPoolEntryIndices : []) {
    const entryIndex = Number(value);
    if (!Number.isInteger(entryIndex) || entryIndex < 0) continue;
    preinstallConstPoolEntries.add(entryIndex >>> 0);
  }

  let entryBackedBindingCount = 0;
  for (const entry of Array.isArray(entries) ? entries : []) {
    if (String(entry?.availability ?? "").toLowerCase() === "entry-backed") {
      entryBackedBindingCount++;
    }
  }

  return normalizeStartupShadowTable({
    schema_version: STARTUP_SHADOW_TABLE_SCHEMA_V1,
    phase: "pre-fasload",
    contract_id: typeof contract?.id === "string" ? contract.id : null,
    preinstall_const_pool_entries: Array.from(preinstallConstPoolEntries.values()).sort((a, b) => a - b),
    binding_entry_count: Array.isArray(entries) ? (entries.length >>> 0) : 0,
    entry_backed_binding_count: entryBackedBindingCount >>> 0,
  });
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
    startup_shadow_table: normalizeStartupShadowTable(artifact.startup_shadow_table),
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
    schema_version: "startup_binding_map_contract_const_pool_function_build_v4",
    status: "ok",
    enabled: false,
    required_pool_count: 0,
    required_ref_count: 0,
    required_callable_count: 0,
    required_special_count: 0,
    required_special_initializer_literal_count: 0,
    required_special_initializer_deferred_count: 0,
    required_special_initializer_unsupported_count: 0,
    required_special_entries_emitted: 0,
    required_special_entries_upgraded: 0,
    seed_ref_count: 0,
    seed_symbol_ref_count: 0,
    seed_callable_count: 0,
    seed_callable_bulk_enabled: false,
    seed_callable_bulk_count: 0,
    seed_callable_bulk_ambiguous_skipped: 0,
    seed_callable_bulk_invalid_symbol_key: 0,
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
    symbol_anchor_alias_total: 0,
    symbol_anchor_alias_entries_updated: 0,
    symbol_anchor_entry_upgrades: 0,
    symbol_anchor_existing_preserved: 0,
    required_special_anchors_present: 0,
    required_special_anchors_missing: 0,
    closure_callable_symbols: 0,
    closure_const_pool_entry_count: 0,
    closure_const_pool_entry_indices: [],
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
  const requiredSpecialBySymbolKey = new Map();
  for (const item of requiredSpecialVariables) {
    const packageName = canonicalizePackageName(item?.packageName ?? item?.package_name ?? "");
    const symbolName = normalizeSymbolName(item?.symbolName ?? item?.symbol_name ?? "");
    const symbolKey = makeSymbolKey(packageName, symbolName);
    if (!symbolKey) continue;
    const hasInitializer = (
      item &&
      typeof item === "object" &&
      !Array.isArray(item) &&
      Object.prototype.hasOwnProperty.call(item, "initializer")
    );
    const normalized = {
      package_name: packageName,
      symbol_name: symbolName,
      symbol_key: symbolKey,
      require_non_nil: Boolean(item?.requireNonNil ?? item?.require_non_nil),
      source: normalizeToken(item?.source ?? "") || "contract-required-special",
      has_initializer: hasInitializer,
      contract_initializer: hasInitializer
        ? classifyContractSpecialVariableInitializer(item?.initializer)
        : null,
    };
    const existing = requiredSpecialBySymbolKey.get(symbolKey);
    if (!existing) {
      requiredSpecialBySymbolKey.set(symbolKey, normalized);
      continue;
    }
    requiredSpecialBySymbolKey.set(symbolKey, {
      ...existing,
      require_non_nil: existing.require_non_nil || normalized.require_non_nil,
      has_initializer: existing.has_initializer || normalized.has_initializer,
      contract_initializer: existing.has_initializer
        ? existing.contract_initializer
        : normalized.contract_initializer,
    });
  }
  const requiredSpecialSymbolKeys = new Set(requiredSpecialBySymbolKey.keys());
  stats.required_special_count = requiredSpecialSymbolKeys.size >>> 0;
  for (const requiredSpecial of requiredSpecialBySymbolKey.values()) {
    const availability = requiredSpecial?.has_initializer
      ? String(requiredSpecial?.contract_initializer?.availability ?? "unsupported")
      : "deferred";
    if (availability === "literal") stats.required_special_initializer_literal_count++;
    else if (availability === "unsupported") stats.required_special_initializer_unsupported_count++;
    else stats.required_special_initializer_deferred_count++;
  }

  if (
    requiredRefs.length === 0 &&
    requiredCallables.length === 0 &&
    requiredSpecialSymbolKeys.size === 0
  ) {
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
      if (symbolKey && functionIndex.bySymbolKey.has(symbolKey)) {
        return true;
      }
    }
    return functionIndex.byName.has(normalizedSymbol);
  };

  const resolver = typeof resolveFunctionDesignator === "function"
    ? ({ packageName, symbolName, source = null }) => {
      const resolved = resolveFunctionDesignator({
        name: normalizeSymbolName(symbolName),
        packageName: canonicalizePackageName(packageName),
        source,
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
  const enqueueCallableSeed = (
    { package_name, symbol_name } = {},
    { source = "contract-required-callable" } = {},
  ) => {
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
      source,
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
    }, { source: "contract-required-callable" })) {
      stats.seed_callable_count++;
    }
  }

  // Legacy env toggle was removed in M-059.
  const enableBulkCallableSeeds = false;
  if (enableBulkCallableSeeds) {
    stats.seed_callable_bulk_enabled = true;
    const sortedSymbolKeys = Array.from(functionIndex.bySymbolKey.keys()).sort();
    for (const symbolKey of sortedSymbolKeys) {
      const record = functionIndex.bySymbolKey.get(symbolKey) ?? null;
      if (record?.ambiguous) {
        stats.seed_callable_bulk_ambiguous_skipped++;
        continue;
      }
      const parsed = parseSymbolKey(symbolKey);
      if (!parsed) {
        stats.seed_callable_bulk_invalid_symbol_key++;
        continue;
      }
      if (enqueueCallableSeed(parsed, { source: "runtime-function-metadata-bulk" })) {
        stats.seed_callable_bulk_count++;
      }
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
  const canonicalizeDefinition = (candidateDefinition) => ({
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
  const definitionAliasComparator = (a, b) => {
    const aDepth = definitionDepth(a);
    const bDepth = definitionDepth(b);
    if (aDepth < bDepth) return -1;
    if (aDepth > bDepth) return 1;
    const aEntry = a.entry_index >>> 0;
    const bEntry = b.entry_index >>> 0;
    if (aEntry < bEntry) return -1;
    if (aEntry > bEntry) return 1;
    return (a.const_index >>> 0) - (b.const_index >>> 0);
  };
  const normalizeDefinitionAliasList = (aliases) => {
    const byKey = new Map();
    for (const alias of Array.isArray(aliases) ? aliases : []) {
      if (!hasConstPoolDefinition(alias)) continue;
      const canonical = canonicalizeDefinition(alias);
      const key = `${canonical.entry_index}:${canonical.const_index}`;
      const existing = byKey.get(key);
      if (!existing || shouldPreferDefinition(existing, canonical)) {
        byKey.set(key, canonical);
      }
    }
    return Array.from(byKey.values()).sort(definitionAliasComparator);
  };
  const sameDefinitionAliasLists = (a, b) => {
    if (a.length !== b.length) return false;
    for (let i = 0; i < a.length; i++) {
      const left = a[i];
      const right = b[i];
      if ((left.entry_index >>> 0) !== (right.entry_index >>> 0)) return false;
      if ((left.const_index >>> 0) !== (right.const_index >>> 0)) return false;
      if ((left.const_pool_depth ?? null) !== (right.const_pool_depth ?? null)) return false;
      if ((left.const_tag ?? null) !== (right.const_tag ?? null)) return false;
      if ((left.const_pool_source ?? null) !== (right.const_pool_source ?? null)) return false;
    }
    return true;
  };
  const symbolAnchorBySymbolKey = new Map();
  const symbolAnchorAliasesBySymbolKey = new Map();
  const closureCallableSymbolKeys = new Set();
  const recordSymbolAnchor = (symbolKey, candidateDefinition) => {
    if (!symbolKey || !hasConstPoolDefinition(candidateDefinition)) return;
    const existing = symbolAnchorBySymbolKey.get(symbolKey) ?? null;
    if (!existing || shouldPreferDefinition(existing, candidateDefinition)) {
      symbolAnchorBySymbolKey.set(symbolKey, canonicalizeDefinition(candidateDefinition));
    }
  };
  const recordSymbolAnchorAlias = (symbolKey, candidateDefinition) => {
    if (!symbolKey || !hasConstPoolDefinition(candidateDefinition)) return;
    const aliasByKey = symbolAnchorAliasesBySymbolKey.get(symbolKey) ?? new Map();
    const canonical = canonicalizeDefinition(candidateDefinition);
    const aliasKey = `${canonical.entry_index}:${canonical.const_index}`;
    const existing = aliasByKey.get(aliasKey) ?? null;
    if (!existing || shouldPreferDefinition(existing, canonical)) {
      aliasByKey.set(aliasKey, canonical);
    }
    symbolAnchorAliasesBySymbolKey.set(symbolKey, aliasByKey);
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
      recordSymbolAnchorAlias(refSymbolKey, refDefinition);
    }
    const isRequiredCallableSeed = ref.source === "contract-required-callable";
    if (!isRequiredCallableSeed && !hasCallableMetadata({ packageName, symbolName })) {
      stats.symbol_refs_filtered_non_callable++;
      continue;
    }

    const resolution = resolver({ packageName, symbolName, source: ref.source ?? null });
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
    closureCallableSymbolKeys.add(symbolKey);
    const definition = refDefinition ? {
      ...refDefinition,
    } : null;
    const requiredCallableDefinition = isRequiredCallableSeed
      ? {
        ...(definition && typeof definition === "object" ? definition : {}),
        required_class: STARTUP_SYMBOL_REQUIRED_CLASS.REQUIRED_CALLABLE,
      }
      : definition;
    const source = typeof ref.source === "string" && ref.source.length > 0
      ? ref.source
      : (definition ? "contract-required-const-pool-ref" : "contract-required-callable");

    const existingIndex = functionEntryIndexBySymbolKey.get(symbolKey);
    if (existingIndex != null) {
      const existing = entries[existingIndex];
      const existingAvailability = String(existing?.availability ?? "").toLowerCase();
      const existingInitializerKind = String(existing?.initializer?.kind ?? "").toLowerCase();
      const existingEntryIndex = Number(existing?.initializer?.entry_index);
      const replaceDefinition = shouldPreferDefinition(existing?.definition ?? null, requiredCallableDefinition);
      const definitionSatisfied = !replaceDefinition;
      if (
        existingAvailability === "entry-backed" &&
        existingInitializerKind === "entry-function" &&
        Number.isInteger(existingEntryIndex) &&
        (existingEntryIndex >>> 0) === resolvedEntryIndex &&
        definitionSatisfied
      ) {
        if (isRequiredCallableSeed) {
          const existingDefinition = (
            existing?.definition &&
            typeof existing.definition === "object" &&
            !Array.isArray(existing.definition)
          )
            ? existing.definition
            : {};
          if (existingDefinition.required_class !== STARTUP_SYMBOL_REQUIRED_CLASS.REQUIRED_CALLABLE) {
            entries[existingIndex] = {
              ...existing,
              definition: {
                ...existingDefinition,
                required_class: STARTUP_SYMBOL_REQUIRED_CLASS.REQUIRED_CALLABLE,
              },
            };
            stats.upgraded_existing_entries++;
          } else {
            stats.skipped_existing_entry_backed++;
          }
        } else {
          stats.skipped_existing_entry_backed++;
        }
      } else {
        const existingDefinition = (
          existing?.definition &&
          typeof existing.definition === "object" &&
          !Array.isArray(existing.definition)
        )
          ? existing.definition
          : null;
        const nextDefinition = replaceDefinition
          ? requiredCallableDefinition
          : existingDefinition;
        const mergedDefinition = isRequiredCallableSeed
          ? {
            ...(nextDefinition && typeof nextDefinition === "object" ? nextDefinition : {}),
            required_class: STARTUP_SYMBOL_REQUIRED_CLASS.REQUIRED_CALLABLE,
          }
          : nextDefinition;
        entries[existingIndex] = {
          ...existing,
          binding_class: "function",
          target_cell: "fcell",
          package_name: resolvedPackageName,
          symbol_name: symbolName,
          symbol_key: symbolKey,
          source,
          require_non_nil: false,
          definition: mergedDefinition,
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
        definition: requiredCallableDefinition,
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

    // Troubleshooting note: keep full recursive closure enabled by default.
    // A depth cap can be reintroduced later as a targeted diagnostic toggle
    // when isolating memory/closure interactions, but it is intentionally not
    // active in normal pipeline behavior.
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
  let symbolAnchorAliasTotal = 0;
  for (const aliasByKey of symbolAnchorAliasesBySymbolKey.values()) {
    symbolAnchorAliasTotal += aliasByKey.size >>> 0;
  }
  stats.symbol_anchor_alias_total = symbolAnchorAliasTotal >>> 0;

  const entryIndexBySymbolKey = new Map();
  const entryIndexByTargetAndSymbolKey = new Map();
  for (let i = 0; i < entries.length; i++) {
    const entry = entries[i];
    const packageName = canonicalizePackageName(entry?.package_name ?? "");
    const symbolName = normalizeSymbolName(entry?.symbol_name ?? "");
    const symbolKey = makeSymbolKey(packageName, symbolName);
    if (!symbolKey) continue;
    if (!entryIndexBySymbolKey.has(symbolKey)) {
      entryIndexBySymbolKey.set(symbolKey, i);
    }
    const bindingKey = makeEntryBindingKey(normalizeEntryTargetCell(entry), symbolKey);
    if (bindingKey && !entryIndexByTargetAndSymbolKey.has(bindingKey)) {
      entryIndexByTargetAndSymbolKey.set(bindingKey, i);
    }
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

  for (const [symbolKey, aliasByKey] of symbolAnchorAliasesBySymbolKey.entries()) {
    const existingIndex = entryIndexBySymbolKey.get(symbolKey);
    if (existingIndex == null) continue;
    const entry = entries[existingIndex];
    const existingAliases = normalizeDefinitionAliasList(entry?.definition_aliases ?? []);
    const mergedAliases = normalizeDefinitionAliasList([
      ...(entry?.definition ? [entry.definition] : []),
      ...existingAliases,
      ...aliasByKey.values(),
    ]);
    if (mergedAliases.length === 0 || sameDefinitionAliasLists(existingAliases, mergedAliases)) {
      continue;
    }
    entries[existingIndex] = {
      ...entry,
      definition_aliases: mergedAliases,
    };
    stats.symbol_anchor_alias_entries_updated++;
  }

  const requiredSpecialSpecs = Array.from(requiredSpecialBySymbolKey.values())
    .sort((a, b) => a.symbol_key.localeCompare(b.symbol_key));
  for (const requiredSpecial of requiredSpecialSpecs) {
    const symbolKey = requiredSpecial.symbol_key;
    const bindingKey = makeEntryBindingKey("vcell", symbolKey);
    const existingIndex = entryIndexByTargetAndSymbolKey.get(bindingKey);
    const existing = existingIndex == null ? null : entries[existingIndex];
    let availability = "deferred";
    let initializer = {
      kind: "deferred",
      reason: "no-contract-initializer",
    };
    if (requiredSpecial.has_initializer) {
      availability = String(requiredSpecial?.contract_initializer?.availability ?? "unsupported");
      initializer = (
        requiredSpecial?.contract_initializer &&
        typeof requiredSpecial.contract_initializer === "object"
      )
        ? requiredSpecial.contract_initializer.initializer
        : {
          kind: "unsupported",
          reason: "invalid-contract-initializer",
        };
    } else if (
      existing?.initializer &&
      typeof existing.initializer === "object" &&
      !Array.isArray(existing.initializer)
    ) {
      const existingAvailability = String(existing?.availability ?? "deferred").toLowerCase();
      availability = (
        existingAvailability === "literal" ||
        existingAvailability === "entry-backed" ||
        existingAvailability === "unsupported"
      )
        ? existingAvailability
        : "deferred";
      initializer = existing.initializer;
    }

    const existingDefinition = (
      existing?.definition &&
      typeof existing.definition === "object" &&
      !Array.isArray(existing.definition)
    )
      ? existing.definition
      : {};
    const nextEntry = {
      ...(existing ?? {}),
      binding_class: "special-variable",
      target_cell: "vcell",
      package_name: requiredSpecial.package_name,
      symbol_name: requiredSpecial.symbol_name,
      symbol_key: symbolKey,
      source: requiredSpecial.source,
      require_non_nil: requiredSpecial.require_non_nil,
      definition: {
        ...existingDefinition,
        required_class: STARTUP_SYMBOL_REQUIRED_CLASS.REQUIRED_SPECIAL,
        contract_special: true,
      },
      availability,
      initializer,
    };
    if (existingIndex == null) {
      const nextIndex = entries.length;
      entries.push(nextEntry);
      entryIndexBySymbolKey.set(symbolKey, nextIndex);
      entryIndexByTargetAndSymbolKey.set(bindingKey, nextIndex);
      stats.required_special_entries_emitted++;
      continue;
    }
    entries[existingIndex] = nextEntry;
    stats.required_special_entries_upgraded++;
  }

  let requiredSpecialAnchorsPresent = 0;
  let requiredSpecialAnchorsMissing = 0;
  for (const symbolKey of requiredSpecialSymbolKeys.values()) {
    const entryIndex = entryIndexByTargetAndSymbolKey.get(makeEntryBindingKey("vcell", symbolKey))
      ?? entryIndexBySymbolKey.get(symbolKey);
    const entry = entryIndex == null ? null : entries[entryIndex];
    if (hasConstPoolDefinition(entry?.definition)) requiredSpecialAnchorsPresent++;
    else requiredSpecialAnchorsMissing++;
  }
  stats.required_special_anchors_present = requiredSpecialAnchorsPresent >>> 0;
  stats.required_special_anchors_missing = requiredSpecialAnchorsMissing >>> 0;
  const closureConstPoolEntryIndices = [];
  const seenClosureConstPoolEntryIndices = new Set();
  const collectClosureDefinitionEntryIndex = (definition) => {
    if (!hasConstPoolDefinition(definition)) return;
    const entryIndex = definition.entry_index >>> 0;
    if (seenClosureConstPoolEntryIndices.has(entryIndex)) return;
    seenClosureConstPoolEntryIndices.add(entryIndex);
    closureConstPoolEntryIndices.push(entryIndex);
  };
  for (const symbolKey of closureCallableSymbolKeys.values()) {
    const entryIndex = functionEntryIndexBySymbolKey.get(symbolKey);
    if (entryIndex == null) continue;
    const entry = entries[entryIndex];
    collectClosureDefinitionEntryIndex(entry?.definition ?? null);
    for (const alias of Array.isArray(entry?.definition_aliases) ? entry.definition_aliases : []) {
      collectClosureDefinitionEntryIndex(alias);
    }
  }
  closureConstPoolEntryIndices.sort((a, b) => a - b);
  stats.closure_callable_symbols = closureCallableSymbolKeys.size >>> 0;
  stats.closure_const_pool_entry_count = closureConstPoolEntryIndices.length >>> 0;
  stats.closure_const_pool_entry_indices = closureConstPoolEntryIndices;

  const coverage = mapArtifact?.coverage && typeof mapArtifact.coverage === "object"
    ? { ...mapArtifact.coverage }
    : {};
  coverage.required_special_variable_bindings = {
    schema_version: "startup_binding_map_required_special_variable_bindings_v1",
    required_special_count: stats.required_special_count >>> 0,
    initializer_literal_count: stats.required_special_initializer_literal_count >>> 0,
    initializer_deferred_count: stats.required_special_initializer_deferred_count >>> 0,
    initializer_unsupported_count: stats.required_special_initializer_unsupported_count >>> 0,
    emitted_entries: stats.required_special_entries_emitted >>> 0,
    upgraded_entries: stats.required_special_entries_upgraded >>> 0,
  };
  coverage.contract_required_const_pool_function_bindings = stats;
  const nextArtifact = {
    ...(mapArtifact ?? {}),
    schema_version: STARTUP_BINDING_MAP_SCHEMA_V1,
    generator: mapArtifact?.generator ?? STARTUP_BINDING_MAP_GENERATOR_V1,
    contract_id: mapArtifact?.contract_id ?? (typeof contract?.id === "string" ? contract.id : null),
    coverage,
    startup_shadow_table: buildStartupShadowTable({
      contract,
      entries,
      closureConstPoolEntryIndices,
    }),
    entries,
    counts: summarizeEntries(entries),
  };
  return {
    changed: (
      stats.emitted_entries +
      stats.upgraded_existing_entries +
      stats.required_special_entries_emitted +
      stats.required_special_entries_upgraded +
      stats.symbol_anchor_entry_upgrades +
      stats.symbol_anchor_alias_entries_updated
    ) > 0,
    mapArtifact: nextArtifact,
    stats,
  };
}

const ARTIFACT_FUNCTION_ROLE_HINTS = Object.freeze(new Set([
  "required-callable",
  "contract-required-callable",
  "callable",
  "function",
  "defun",
  "defmacro",
  "define-compiler-macro",
  "defsetf",
  "define-setf-expander",
]));
const ARTIFACT_SPECIAL_ROLE_HINTS = Object.freeze(new Set([
  "required-special",
  "contract-required-special",
  "special",
  "special-variable",
  "defparameter",
  "defvar",
  "def-standard-initial-binding",
]));

function normalizeRequiredClass(
  value,
  fallback = STARTUP_SYMBOL_REQUIRED_CLASS.NONE,
) {
  const normalized = normalizeToken(value).toLowerCase();
  switch (normalized) {
    case STARTUP_SYMBOL_REQUIRED_CLASS.REQUIRED_CALLABLE:
    case STARTUP_SYMBOL_REQUIRED_CLASS.REQUIRED_SPECIAL:
    case STARTUP_SYMBOL_REQUIRED_CLASS.OPTIONAL:
    case STARTUP_SYMBOL_REQUIRED_CLASS.NONE:
      return normalized;
    default:
      return fallback;
  }
}

function normalizeResolutionStatus(
  value,
  fallback = STARTUP_SYMBOL_RESOLUTION_STATUS.UNRESOLVED,
) {
  const normalized = normalizeToken(value).toLowerCase();
  switch (normalized) {
    case STARTUP_SYMBOL_RESOLUTION_STATUS.RESOLVED:
    case STARTUP_SYMBOL_RESOLUTION_STATUS.UNRESOLVED:
    case STARTUP_SYMBOL_RESOLUTION_STATUS.PROBE_ERROR:
    case STARTUP_SYMBOL_RESOLUTION_STATUS.INVALID_INPUT:
      return normalized;
    default:
      return fallback;
  }
}

function mergeSortedUniqueTokens(leftValues, rightValues) {
  const values = new Set();
  for (const value of Array.isArray(leftValues) ? leftValues : []) {
    const token = normalizeToken(value);
    if (!token) continue;
    values.add(token);
  }
  for (const value of Array.isArray(rightValues) ? rightValues : []) {
    const token = normalizeToken(value);
    if (!token) continue;
    values.add(token);
  }
  return Array.from(values.values()).sort((a, b) => a.localeCompare(b));
}

function normalizeScopeSymbolRecord(symbolRecord) {
  if (!symbolRecord || typeof symbolRecord !== "object" || Array.isArray(symbolRecord)) return null;
  const parsed = parseSymbolKey(symbolRecord.key ?? "");
  const packageName = canonicalizePackageName(symbolRecord.package_name ?? parsed?.package_name ?? "");
  const symbolName = normalizeSymbolName(symbolRecord.symbol_name ?? parsed?.symbol_name ?? "");
  const symbolKey = makeSymbolKey(packageName, symbolName);
  if (!symbolKey) return null;
  const roles = mergeSortedUniqueTokens(symbolRecord.roles ?? [], []);
  const provenanceCount = Array.isArray(symbolRecord.provenance)
    ? (symbolRecord.provenance.length >>> 0)
    : 0;
  return {
    key: symbolKey,
    package_name: packageName,
    symbol_name: symbolName,
    bindable: Boolean(symbolRecord.bindable),
    roles,
    provenance_count: provenanceCount,
  };
}

function normalizeResolutionSymbolRecord(symbolRecord) {
  if (!symbolRecord || typeof symbolRecord !== "object" || Array.isArray(symbolRecord)) return null;
  const parsed = parseSymbolKey(symbolRecord.key ?? "");
  const packageName = canonicalizePackageName(symbolRecord.package_name ?? parsed?.package_name ?? "");
  const symbolName = normalizeSymbolName(symbolRecord.symbol_name ?? parsed?.symbol_name ?? "");
  const symbolKey = makeSymbolKey(packageName, symbolName);
  if (!symbolKey) return null;
  const fentry = Number(symbolRecord.fentry);
  return {
    key: symbolKey,
    package_name: packageName,
    symbol_name: symbolName,
    status: normalizeResolutionStatus(symbolRecord.status),
    required_class: normalizeRequiredClass(symbolRecord.required_class),
    reason: typeof symbolRecord.reason === "string" ? symbolRecord.reason : null,
    resolver_source: typeof symbolRecord.resolver_source === "string"
      ? symbolRecord.resolver_source
      : null,
    fentry: Number.isInteger(fentry) && fentry >= 0 ? (fentry >>> 0) : null,
    vcell_bound: Boolean(symbolRecord.vcell_bound),
  };
}

function collectScopeSymbolsByKey(scopeArtifact) {
  const byKey = new Map();
  const stats = {
    input_symbols: 0,
    invalid_symbols: 0,
    duplicate_symbols: 0,
  };
  const symbols = Array.isArray(scopeArtifact?.symbols) ? scopeArtifact.symbols : [];
  stats.input_symbols = symbols.length >>> 0;
  for (const symbolRecord of symbols) {
    const normalized = normalizeScopeSymbolRecord(symbolRecord);
    if (!normalized) {
      stats.invalid_symbols++;
      continue;
    }
    const existing = byKey.get(normalized.key);
    if (!existing) {
      byKey.set(normalized.key, normalized);
      continue;
    }
    stats.duplicate_symbols++;
    byKey.set(normalized.key, {
      ...existing,
      bindable: existing.bindable || normalized.bindable,
      roles: mergeSortedUniqueTokens(existing.roles, normalized.roles),
      provenance_count: Math.max(existing.provenance_count >>> 0, normalized.provenance_count >>> 0),
    });
  }
  return { byKey, stats };
}

function resolutionStatusRank(status) {
  switch (normalizeResolutionStatus(status)) {
    case STARTUP_SYMBOL_RESOLUTION_STATUS.RESOLVED:
      return 4;
    case STARTUP_SYMBOL_RESOLUTION_STATUS.UNRESOLVED:
      return 3;
    case STARTUP_SYMBOL_RESOLUTION_STATUS.PROBE_ERROR:
      return 2;
    case STARTUP_SYMBOL_RESOLUTION_STATUS.INVALID_INPUT:
    default:
      return 1;
  }
}

function shouldPreferResolutionRecord(existing, candidate) {
  if (!existing) return true;
  const existingRank = resolutionStatusRank(existing.status);
  const candidateRank = resolutionStatusRank(candidate.status);
  if (candidateRank > existingRank) return true;
  if (candidateRank < existingRank) return false;
  const existingRequiredClass = normalizeRequiredClass(existing.required_class);
  const candidateRequiredClass = normalizeRequiredClass(candidate.required_class);
  if (
    existingRequiredClass === STARTUP_SYMBOL_REQUIRED_CLASS.NONE &&
    candidateRequiredClass !== STARTUP_SYMBOL_REQUIRED_CLASS.NONE
  ) {
    return true;
  }
  return false;
}

function collectResolutionSymbolsByKey(resolutionArtifact) {
  const byKey = new Map();
  const stats = {
    input_symbols: 0,
    invalid_symbols: 0,
    duplicate_symbols: 0,
  };
  const symbols = Array.isArray(resolutionArtifact?.symbols) ? resolutionArtifact.symbols : [];
  stats.input_symbols = symbols.length >>> 0;
  for (const symbolRecord of symbols) {
    const normalized = normalizeResolutionSymbolRecord(symbolRecord);
    if (!normalized) {
      stats.invalid_symbols++;
      continue;
    }
    const existing = byKey.get(normalized.key) ?? null;
    if (existing) {
      stats.duplicate_symbols++;
    }
    if (shouldPreferResolutionRecord(existing, normalized)) {
      byKey.set(normalized.key, normalized);
    }
  }
  return { byKey, stats };
}

function includeSymbolFromArtifacts({
  scopeRecord,
  requiredClass,
}) {
  if (requiredClass !== STARTUP_SYMBOL_REQUIRED_CLASS.NONE) return true;
  return Boolean(scopeRecord?.bindable);
}

function deriveRequiredClassFromArtifacts({
  scopeRecord,
  resolutionRecord,
}) {
  if (resolutionRecord) {
    return normalizeRequiredClass(resolutionRecord.required_class);
  }
  if (scopeRecord?.bindable) return STARTUP_SYMBOL_REQUIRED_CLASS.OPTIONAL;
  return STARTUP_SYMBOL_REQUIRED_CLASS.NONE;
}

const ARTIFACT_ENTRY_ROLE_CLASS = Object.freeze({
  CALLABLE: "callable",
  SPECIAL: "special",
  UNKNOWN: "unknown",
});

const ARTIFACT_ENTRY_FUNCTION_STATUS_ROWS = Object.freeze({
  [STARTUP_SYMBOL_RESOLUTION_STATUS.RESOLVED]: Object.freeze({
    target_cell: "fcell",
    binding_class: "function",
    availability: "entry-backed",
    initializer_kind: "entry-function",
  }),
  [STARTUP_SYMBOL_RESOLUTION_STATUS.UNRESOLVED]: Object.freeze({
    target_cell: "fcell",
    binding_class: "function",
    availability: "deferred",
    initializer_kind: "deferred",
  }),
  [STARTUP_SYMBOL_RESOLUTION_STATUS.PROBE_ERROR]: Object.freeze({
    target_cell: "fcell",
    binding_class: "function",
    availability: "deferred",
    initializer_kind: "deferred",
  }),
  [STARTUP_SYMBOL_RESOLUTION_STATUS.INVALID_INPUT]: Object.freeze({
    target_cell: "fcell",
    binding_class: "function",
    availability: "unsupported",
    initializer_kind: "unsupported",
  }),
});

const ARTIFACT_ENTRY_SPECIAL_STATUS_ROWS = Object.freeze({
  [STARTUP_SYMBOL_RESOLUTION_STATUS.RESOLVED]: Object.freeze({
    target_cell: "vcell",
    binding_class: "special-variable",
    availability: "deferred",
    initializer_kind: "deferred",
  }),
  [STARTUP_SYMBOL_RESOLUTION_STATUS.UNRESOLVED]: Object.freeze({
    target_cell: "vcell",
    binding_class: "special-variable",
    availability: "deferred",
    initializer_kind: "deferred",
  }),
  [STARTUP_SYMBOL_RESOLUTION_STATUS.PROBE_ERROR]: Object.freeze({
    target_cell: "vcell",
    binding_class: "special-variable",
    availability: "deferred",
    initializer_kind: "deferred",
  }),
  [STARTUP_SYMBOL_RESOLUTION_STATUS.INVALID_INPUT]: Object.freeze({
    target_cell: "vcell",
    binding_class: "special-variable",
    availability: "unsupported",
    initializer_kind: "unsupported",
  }),
});

const ARTIFACT_ENTRY_OPTIONAL_ROLE_ROWS = Object.freeze({
  [ARTIFACT_ENTRY_ROLE_CLASS.CALLABLE]: ARTIFACT_ENTRY_FUNCTION_STATUS_ROWS,
  [ARTIFACT_ENTRY_ROLE_CLASS.SPECIAL]: ARTIFACT_ENTRY_SPECIAL_STATUS_ROWS,
  [ARTIFACT_ENTRY_ROLE_CLASS.UNKNOWN]: ARTIFACT_ENTRY_SPECIAL_STATUS_ROWS,
});

const ARTIFACT_ENTRY_SYNTHESIS_MATRIX = Object.freeze({
  [STARTUP_SYMBOL_REQUIRED_CLASS.REQUIRED_CALLABLE]: ARTIFACT_ENTRY_FUNCTION_STATUS_ROWS,
  [STARTUP_SYMBOL_REQUIRED_CLASS.REQUIRED_SPECIAL]: ARTIFACT_ENTRY_SPECIAL_STATUS_ROWS,
  [STARTUP_SYMBOL_REQUIRED_CLASS.OPTIONAL]: ARTIFACT_ENTRY_OPTIONAL_ROLE_ROWS,
  [STARTUP_SYMBOL_REQUIRED_CLASS.NONE]: ARTIFACT_ENTRY_OPTIONAL_ROLE_ROWS,
});

function deriveArtifactRoleClass({
  scopeRecord,
  resolutionRecord,
}) {
  let hasCallableRole = false;
  let hasSpecialRole = false;
  const roleSet = new Set(
    (Array.isArray(scopeRecord?.roles) ? scopeRecord.roles : [])
      .map((role) => normalizeToken(role).toLowerCase())
      .filter((role) => role.length > 0),
  );
  for (const role of roleSet.values()) {
    if (ARTIFACT_FUNCTION_ROLE_HINTS.has(role)) hasCallableRole = true;
    if (ARTIFACT_SPECIAL_ROLE_HINTS.has(role)) hasSpecialRole = true;
    if (hasCallableRole && hasSpecialRole) break;
  }
  // Callable wins in mixed-role records so function-capable symbols keep fcell mapping.
  if (hasCallableRole) return ARTIFACT_ENTRY_ROLE_CLASS.CALLABLE;
  if (hasSpecialRole) return ARTIFACT_ENTRY_ROLE_CLASS.SPECIAL;
  const status = normalizeResolutionStatus(resolutionRecord?.status);
  if (status === STARTUP_SYMBOL_RESOLUTION_STATUS.RESOLVED) {
    if (Number.isInteger(resolutionRecord?.fentry) && resolutionRecord.fentry >= 0) {
      return ARTIFACT_ENTRY_ROLE_CLASS.CALLABLE;
    }
    if (resolutionRecord?.vcell_bound === true) {
      return ARTIFACT_ENTRY_ROLE_CLASS.SPECIAL;
    }
  }
  return ARTIFACT_ENTRY_ROLE_CLASS.UNKNOWN;
}

function unresolvedReasonForRequiredClass(requiredClass) {
  const normalized = normalizeRequiredClass(requiredClass);
  if (
    normalized === STARTUP_SYMBOL_REQUIRED_CLASS.REQUIRED_CALLABLE ||
    normalized === STARTUP_SYMBOL_REQUIRED_CLASS.REQUIRED_SPECIAL
  ) {
    return "required-symbol-unresolved";
  }
  return "optional-symbol-unresolved";
}

function lookupArtifactEntrySynthesisRow({
  roleClass,
  requiredClass,
  status,
}) {
  const normalizedRequiredClass = normalizeRequiredClass(requiredClass);
  const normalizedStatus = normalizeResolutionStatus(
    status,
    STARTUP_SYMBOL_RESOLUTION_STATUS.UNRESOLVED,
  );
  const requiredClassRows = ARTIFACT_ENTRY_SYNTHESIS_MATRIX[normalizedRequiredClass]
    ?? ARTIFACT_ENTRY_SYNTHESIS_MATRIX[STARTUP_SYMBOL_REQUIRED_CLASS.NONE];
  if (
    normalizedRequiredClass === STARTUP_SYMBOL_REQUIRED_CLASS.REQUIRED_CALLABLE ||
    normalizedRequiredClass === STARTUP_SYMBOL_REQUIRED_CLASS.REQUIRED_SPECIAL
  ) {
    return requiredClassRows[normalizedStatus]
      ?? requiredClassRows[STARTUP_SYMBOL_RESOLUTION_STATUS.UNRESOLVED];
  }
  const roleRows = requiredClassRows[roleClass] ?? requiredClassRows[ARTIFACT_ENTRY_ROLE_CLASS.UNKNOWN];
  return roleRows[normalizedStatus] ?? roleRows[STARTUP_SYMBOL_RESOLUTION_STATUS.UNRESOLVED];
}

function synthesizeArtifactEntryFromMatrix({
  symbolName,
  scopeRecord,
  requiredClass,
  resolutionRecord,
}) {
  const status = normalizeResolutionStatus(
    resolutionRecord?.status,
    STARTUP_SYMBOL_RESOLUTION_STATUS.UNRESOLVED,
  );
  const roleClass = deriveArtifactRoleClass({
    scopeRecord,
    resolutionRecord,
  });
  const matrixRow = lookupArtifactEntrySynthesisRow({
    roleClass,
    requiredClass,
    status,
  });
  if (matrixRow.initializer_kind === "entry-function") {
    if (
      Number.isInteger(resolutionRecord?.fentry) &&
      (resolutionRecord.fentry >>> 0) >= 0
    ) {
      return {
        binding_class: matrixRow.binding_class,
        target_cell: matrixRow.target_cell,
        availability: matrixRow.availability,
        initializer: {
          kind: "entry-function",
          function_name: symbolName,
          entry_index: resolutionRecord.fentry >>> 0,
        },
      };
    }
    return {
      binding_class: matrixRow.binding_class,
      target_cell: matrixRow.target_cell,
      availability: "deferred",
      initializer: {
        kind: "deferred",
        reason: "resolved-without-entry-backing",
      },
    };
  }
  if (matrixRow.initializer_kind === "unsupported") {
    return {
      binding_class: matrixRow.binding_class,
      target_cell: matrixRow.target_cell,
      availability: matrixRow.availability,
      initializer: {
        kind: "unsupported",
        reason: "invalid-input",
      },
    };
  }
  let deferredReason = "optional-symbol-unresolved";
  if (status === STARTUP_SYMBOL_RESOLUTION_STATUS.PROBE_ERROR) {
    deferredReason = "probe-error";
  } else if (status === STARTUP_SYMBOL_RESOLUTION_STATUS.RESOLVED) {
    deferredReason = "resolved-without-entry-backing";
  } else if (status === STARTUP_SYMBOL_RESOLUTION_STATUS.UNRESOLVED) {
    deferredReason = unresolvedReasonForRequiredClass(requiredClass);
  }
  if (matrixRow.initializer_kind === "deferred") {
    return {
      binding_class: matrixRow.binding_class,
      target_cell: matrixRow.target_cell,
      availability: matrixRow.availability,
      initializer: {
        kind: "deferred",
        reason: deferredReason,
      },
    };
  }
  return {
    binding_class: matrixRow.binding_class,
    target_cell: matrixRow.target_cell,
    availability: "unsupported",
    initializer: {
      kind: "unsupported",
      reason: "entry-synthesis-matrix-invalid",
    },
  };
}

export async function buildStartupBindingMapArtifact({
  repoRoot = null,
  contract = BOOTSTRAP_L0_CONTRACT_V1,
  functions = [],
  scopeArtifact = null,
  resolutionArtifact = null,
} = {}) {
  // Keep contract text colocated with the builder entrypoint for quick audits/grep checks.
  // Active inclusion source-of-truth: scope artifact + resolution artifact input only.
  // Active path policy: artifact-only, no JS source scan.
  void repoRoot;
  void functions;
  void STARTUP_BINDING_MAP_INPUT_CONTRACT_V1;

  const scopeSymbols = collectScopeSymbolsByKey(scopeArtifact);
  const resolutionSymbols = collectResolutionSymbolsByKey(resolutionArtifact);
  const symbolKeys = Array.from(new Set([
    ...scopeSymbols.byKey.keys(),
    ...resolutionSymbols.byKey.keys(),
  ])).sort((a, b) => a.localeCompare(b));

  const artifactStats = {
    scope_symbols_input: scopeSymbols.stats.input_symbols >>> 0,
    scope_symbols_invalid: scopeSymbols.stats.invalid_symbols >>> 0,
    scope_symbols_duplicate: scopeSymbols.stats.duplicate_symbols >>> 0,
    resolution_symbols_input: resolutionSymbols.stats.input_symbols >>> 0,
    resolution_symbols_invalid: resolutionSymbols.stats.invalid_symbols >>> 0,
    resolution_symbols_duplicate: resolutionSymbols.stats.duplicate_symbols >>> 0,
    keys_considered: symbolKeys.length >>> 0,
    keys_included: 0,
    skipped_unbindable_none: 0,
    missing_scope_records: 0,
    missing_resolution_records: 0,
  };

  const entries = [];
  for (const symbolKey of symbolKeys) {
    const scopeRecord = scopeSymbols.byKey.get(symbolKey) ?? null;
    const resolutionRecord = resolutionSymbols.byKey.get(symbolKey) ?? null;
    if (!scopeRecord) artifactStats.missing_scope_records++;
    if (!resolutionRecord) artifactStats.missing_resolution_records++;

    const requiredClass = deriveRequiredClassFromArtifacts({
      scopeRecord,
      resolutionRecord,
    });
    if (!includeSymbolFromArtifacts({ scopeRecord, requiredClass })) {
      artifactStats.skipped_unbindable_none++;
      continue;
    }

    const parsedKey = parseSymbolKey(symbolKey);
    const packageName = canonicalizePackageName(
      scopeRecord?.package_name ??
      resolutionRecord?.package_name ??
      parsedKey?.package_name ??
      "",
    );
    const symbolName = normalizeSymbolName(
      scopeRecord?.symbol_name ??
      resolutionRecord?.symbol_name ??
      parsedKey?.symbol_name ??
      "",
    );
    if (!packageName || !symbolName) continue;

    const synthesized = synthesizeArtifactEntryFromMatrix({
      symbolName,
      scopeRecord,
      resolutionRecord,
      requiredClass,
    });
    entries.push({
      binding_class: synthesized.binding_class,
      target_cell: synthesized.target_cell,
      package_name: packageName,
      symbol_name: symbolName,
      symbol_key: symbolKey,
      source: "scope artifact + resolution artifact",
      require_non_nil: false,
      definition: {
        source_of_truth: "scope artifact + resolution artifact",
        roles: Array.isArray(scopeRecord?.roles) ? scopeRecord.roles.slice() : [],
        bindable: scopeRecord?.bindable ?? null,
        scope_provenance_count: scopeRecord?.provenance_count ?? 0,
        required_class: requiredClass,
        resolution_status: normalizeResolutionStatus(resolutionRecord?.status),
        resolution_reason: resolutionRecord?.reason ?? null,
        resolver_source: resolutionRecord?.resolver_source ?? null,
      },
      availability: synthesized.availability,
      initializer: synthesized.initializer,
    });
    artifactStats.keys_included++;
  }

  const coverage = {
    schema_version: STARTUP_BINDING_MAP_COVERAGE_SCHEMA_V1,
    artifact_inputs: {
      schema_version: "startup_binding_map_artifact_inputs_v1",
      mode: STARTUP_BINDING_MAP_INPUT_CONTRACT_V1.mode,
      source_of_truth: "scope artifact + resolution artifact",
      scope_input: STARTUP_BINDING_MAP_INPUT_CONTRACT_V1.scope_input,
      resolution_input: STARTUP_BINDING_MAP_INPUT_CONTRACT_V1.resolution_input,
      source_scan_policy: STARTUP_BINDING_MAP_INPUT_CONTRACT_V1.source_scan_policy,
      ...artifactStats,
    },
    required_special_variable_bindings: null,
    level0_source_scan: null,
    level0_function_bindings: null,
    runtime_function_metadata: null,
  };

  return {
    schema_version: STARTUP_BINDING_MAP_SCHEMA_V1,
    generator: STARTUP_BINDING_MAP_GENERATOR_V1,
    contract_id: typeof contract?.id === "string" ? contract.id : null,
    coverage,
    startup_shadow_table: buildStartupShadowTable({
      contract,
      entries,
      closureConstPoolEntryIndices: [],
    }),
    entries,
    counts: summarizeEntries(entries),
  };
}
