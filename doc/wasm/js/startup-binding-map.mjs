import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { BOOTSTRAP_L0_CONTRACT_V1 } from "./bootstrap-l0-contract.mjs";

export const STARTUP_BINDING_MAP_SCHEMA_V1 = "startup_binding_map_v1";
const STARTUP_BINDING_MAP_GENERATOR_V1 = "startup_binding_map_generator_v1";

const FIXNUM_MIN = -0x20000000; // -536870912
const FIXNUM_MAX = 0x1fffffff; // 536870911

const BINDING_FORM_PATTERN = /\((defparameter|defvar|def-standard-initial-binding)\s+([^\s()]+)(?:\s+(\([^()\s]+\)|'[^()\s]+|[^()\s]+))?/giu;

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

function normalizeSymbolName(value) {
  let token = normalizeToken(value);
  if (!token) return "";
  if (token.startsWith("'")) token = token.slice(1);
  const colon = token.lastIndexOf(":");
  if (colon >= 0) token = token.slice(colon + 1);
  return token.toUpperCase();
}

function makeSymbolKey(packageName, symbolName) {
  const pkg = normalizePackageName(packageName);
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

async function collectLispFilesRecursive(dir) {
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
      out.push(...await collectLispFilesRecursive(fullPath));
      continue;
    }
    if (entry.isFile() && entry.name.toLowerCase().endsWith(".lisp")) {
      out.push(fullPath);
    }
  }
  return out;
}

async function scanBindingDefinitions(repoRoot) {
  const level1Dir = path.join(repoRoot, "level-1");
  const files = await collectLispFilesRecursive(level1Dir);
  const definitions = new Map();

  for (const filePath of files) {
    let text = "";
    try {
      text = await fs.readFile(filePath, "utf8");
    } catch {
      continue;
    }
    BINDING_FORM_PATTERN.lastIndex = 0;
    let match = null;
    while ((match = BINDING_FORM_PATTERN.exec(text)) !== null) {
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

function buildFunctionIndex(functionEntries) {
  const byName = new Map();
  for (const entry of Array.isArray(functionEntries) ? functionEntries : []) {
    const name = normalizeSymbolName(entry?.name ?? "");
    if (!name || !Number.isFinite(entry?.entryIndex) || entry.entryIndex < 0) continue;
    const index = entry.entryIndex >>> 0;
    const existing = byName.get(name);
    if (!existing) {
      byName.set(name, {
        ambiguous: false,
        entry_index: index,
        alternatives: [index],
      });
      continue;
    }
    if (!existing.alternatives.includes(index)) {
      existing.alternatives.push(index);
      existing.alternatives.sort((a, b) => a - b);
    }
    if (existing.entry_index !== index) {
      existing.ambiguous = true;
    }
  }
  return byName;
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
    const fnName = normalizeSymbolName(inner);
    if (!fnName) {
      return {
        availability: "deferred",
        initializer: {
          kind: "deferred",
          reason: "invalid-call-form",
          detail: token,
        },
      };
    }
    const resolved = functionIndex.get(fnName);
    if (!resolved) {
      return {
        availability: "deferred",
        initializer: {
          kind: "deferred",
          reason: "initializer-function-unresolved",
          detail: inner,
        },
      };
    }
    if (resolved.ambiguous) {
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
        function_name: fnName,
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

function summarizeEntries(entries) {
  const counts = {
    total_entries: 0,
    literal_entries: 0,
    entry_backed_entries: 0,
    deferred_entries: 0,
    unsupported_entries: 0,
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
  }
  return counts;
}

export function summarizeStartupBindingMapArtifact(artifact) {
  return summarizeEntries(Array.isArray(artifact?.entries) ? artifact.entries : []);
}

export function normalizeStartupBindingMapArtifact(artifact) {
  if (!artifact || typeof artifact !== "object") return null;
  const entries = Array.isArray(artifact.entries) ? artifact.entries : [];
  return {
    schema_version: STARTUP_BINDING_MAP_SCHEMA_V1,
    generator: STARTUP_BINDING_MAP_GENERATOR_V1,
    contract_id: typeof artifact.contract_id === "string" ? artifact.contract_id : null,
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
  const definitions = await scanBindingDefinitions(rootDir);

  const entries = [];
  for (const item of requiredSpecialVariables) {
    const packageName = normalizePackageName(item?.packageName ?? "");
    const symbolName = normalizeSymbolName(item?.symbolName ?? "");
    if (!packageName || !symbolName) continue;
    const symbolKey = makeSymbolKey(packageName, symbolName);
    const definition = definitions.get(symbolKey) ?? null;

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

    entries.push({
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
    });
  }

  return {
    schema_version: STARTUP_BINDING_MAP_SCHEMA_V1,
    generator: STARTUP_BINDING_MAP_GENERATOR_V1,
    contract_id: typeof contract?.id === "string" ? contract.id : null,
    entries,
    counts: summarizeEntries(entries),
  };
}
