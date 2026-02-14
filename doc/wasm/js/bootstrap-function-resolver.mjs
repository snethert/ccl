/*
 * Bootstrap function designator resolver.
 *
 * Ownership model:
 * - bootstrap phase: host metadata may resolve function designators to entry indices.
 * - canonical-lisp phase: host resolver is disabled; Lisp namespace/canonicalization owns resolution.
 */

const PHASE_BOOTSTRAP = "bootstrap";
const PHASE_CANONICAL_LISP = "canonical-lisp";
const POLICY_REQUIRED_RESOLVE_OR_FAIL = "required-resolve-or-fail";
const POLICY_DEFERRED_ALLOWED = "deferred-allowed";
const POLICY_NONCRITICAL = "noncritical";

const textDecoder = new TextDecoder("utf-8");
const textEncoder = new TextEncoder();

const STARTUP_SYMBOL_PACKAGE_OVERRIDES_V1 = Object.freeze({
  TOPLEVEL: Object.freeze({
    toPackageName: "CCL",
    fromPackageNames: Object.freeze(["KEYWORD"]),
  }),
});

const STARTUP_PRE_FASLOAD_PACKAGE_FALLBACKS_TO_CCL_V1 = new Set([
  "INSPECTOR",
  "SWINK",
  "ANSI-LOOP",
  "ARCH",
  "X86",
]);
const STARTUP_ENABLE_PRE_FASLOAD_PACKAGE_FALLBACK =
  process.env.CCL_WASM_PRE_FASLOAD_PACKAGE_FALLBACK !== "0";
const STARTUP_ENABLE_UNRESOLVED_FUNCTION_DESIGNATOR_COERCION =
  process.env.CCL_WASM_UNRESOLVED_FUNCTION_DESIGNATOR_COERCION !== "0";

function asU8(bytes) {
  if (bytes instanceof Uint8Array) return bytes;
  if (bytes instanceof ArrayBuffer) return new Uint8Array(bytes);
  if (ArrayBuffer.isView(bytes)) return new Uint8Array(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  return Uint8Array.from(bytes ?? []);
}

function normalizePhase(value) {
  if (value === PHASE_CANONICAL_LISP) return PHASE_CANONICAL_LISP;
  return PHASE_BOOTSTRAP;
}

function normalizeFunctionName(name) {
  if (typeof name !== "string") return "";
  return name.trim();
}

function normalizePackageName(name) {
  if (typeof name !== "string") return "";
  return name.trim();
}

function uppercaseKey(value) {
  return String(value ?? "").toUpperCase();
}

function normalizeDesignatorNameSet(names) {
  if (!names) return null;
  if (names instanceof Set) {
    const out = new Set();
    for (const name of names) {
      const key = uppercaseKey(normalizeFunctionName(name));
      if (key) out.add(key);
    }
    return out;
  }
  if (!Array.isArray(names)) return null;
  const out = new Set();
  for (const name of names) {
    const key = uppercaseKey(normalizeFunctionName(name));
    if (key) out.add(key);
  }
  return out;
}

function normalizeSymbolPackageOverrides(overrides) {
  if (!overrides) return null;
  const entries = overrides instanceof Map
    ? Array.from(overrides.entries())
    : Object.entries(overrides);
  const out = new Map();
  for (const [rawName, rawSpec] of entries) {
    const nameKey = uppercaseKey(normalizeFunctionName(rawName));
    if (!nameKey) continue;
    if (!rawSpec || typeof rawSpec !== "object") continue;
    const target = normalizePackageName(rawSpec.toPackageName ?? rawSpec.to ?? "");
    if (!target) continue;
    const from = normalizeDesignatorNameSet(rawSpec.fromPackageNames ?? rawSpec.from ?? null);
    out.set(nameKey, {
      toPackageName: target,
      fromPackageNames: from,
    });
  }
  return out.size ? out : null;
}

function resolveSymbolPackageOverride(name, packageName, overrideMap) {
  if (!overrideMap) return null;
  const spec = overrideMap.get(uppercaseKey(normalizeFunctionName(name)));
  if (!spec) return null;
  const current = uppercaseKey(normalizePackageName(packageName));
  if (spec.fromPackageNames && !spec.fromPackageNames.has(current)) {
    return null;
  }
  const target = normalizePackageName(spec.toPackageName);
  if (!target) return null;
  if (uppercaseKey(target) === current) return null;
  return target;
}

function resolvePreFasloadSymbolPackageFallback(packageName) {
  if (!STARTUP_ENABLE_PRE_FASLOAD_PACKAGE_FALLBACK) return null;
  const packageKey = uppercaseKey(normalizePackageName(packageName));
  if (!packageKey) return null;
  if (STARTUP_PRE_FASLOAD_PACKAGE_FALLBACKS_TO_CCL_V1.has(packageKey)) {
    return "CCL";
  }
  return null;
}

function classifyFunctionDesignatorPolicy(name, requiredNameSet, deferredNameSet) {
  const key = uppercaseKey(normalizeFunctionName(name));
  if (key && requiredNameSet?.has(key)) {
    return POLICY_REQUIRED_RESOLVE_OR_FAIL;
  }
  if (key && deferredNameSet?.has(key)) {
    return POLICY_DEFERRED_ALLOWED;
  }
  return POLICY_NONCRITICAL;
}

function unresolvedBindingStateForPolicy(policyClass) {
  switch (policyClass) {
    case POLICY_REQUIRED_RESOLVE_OR_FAIL:
      return "unresolved-required-function-designator";
    case POLICY_DEFERRED_ALLOWED:
      return "deferred-symbolic-function-designator";
    default:
      return "unresolved-function-designator";
  }
}

function makeRecord(entryIndex) {
  return {
    entryIndex: entryIndex >>> 0,
    ambiguous: false,
    alternatives: [],
  };
}

function addLookupRecord(map, key, entryIndex) {
  if (!key) return;
  const idx = entryIndex >>> 0;
  const existing = map.get(key);
  if (!existing) {
    map.set(key, makeRecord(idx));
    return;
  }
  if (!existing.ambiguous && existing.entryIndex === idx) {
    return;
  }
  if (!existing.alternatives.includes(idx)) {
    existing.alternatives.push(idx);
  }
  if (!existing.ambiguous) {
    existing.alternatives.push(existing.entryIndex);
  }
  existing.alternatives = Array.from(new Set(existing.alternatives)).sort((a, b) => a - b);
  existing.ambiguous = true;
  existing.entryIndex = 0;
}

function readU32LE(bytes, state, fieldName) {
  if ((state.offset + 4) > bytes.length) {
    throw new Error(`const-pool truncated while reading ${fieldName}`);
  }
  const o = state.offset;
  const value = (
    (bytes[o]) |
    (bytes[o + 1] << 8) |
    (bytes[o + 2] << 16) |
    (bytes[o + 3] << 24)
  ) >>> 0;
  state.offset += 4;
  return value;
}

function readUleb32(bytes, state, fieldName) {
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

function readSleb32Raw(bytes, state, fieldName) {
  let shift = 0;
  let value = 0;
  let byte = 0;
  for (let i = 0; i < 5; i++) {
    if (state.offset >= bytes.length) {
      throw new Error(`const-pool truncated while reading ${fieldName}`);
    }
    byte = bytes[state.offset++];
    value |= (byte & 0x7f) << shift;
    shift += 7;
    if ((byte & 0x80) === 0) {
      if (shift < 32 && (byte & 0x40)) {
        value |= (~0 << shift);
      }
      return value >>> 0;
    }
  }
  throw new Error(`const-pool malformed sleb32 in ${fieldName}`);
}

function readNat(bytes, state, version, fieldName) {
  if (version >= 2) return readUleb32(bytes, state, fieldName);
  return readU32LE(bytes, state, fieldName);
}

function readSpan(bytes, state, size, fieldName) {
  const len = size >>> 0;
  if ((state.offset + len) > bytes.length) {
    throw new Error(`const-pool truncated while reading ${fieldName}`);
  }
  const start = state.offset;
  const end = start + len;
  state.offset = end;
  return bytes.subarray(start, end);
}

function skipConstPoolEntry(bytes, state, version, tag, entryIndex) {
  switch (tag) {
    case 6: { /* fixnum */
      if (version >= 2) {
        readSleb32Raw(bytes, state, `entry[${entryIndex}] fixnum`);
      } else {
        readU32LE(bytes, state, `entry[${entryIndex}] fixnum`);
      }
      return null;
    }
    case 10: /* character */
      readNat(bytes, state, version, `entry[${entryIndex}] character`);
      return null;
    case 11: /* single-float */
      readU32LE(bytes, state, `entry[${entryIndex}] single-float`);
      return null;
    case 12: /* double-float */
    case 13: /* int64 */
    case 14: /* uint64 */
      readU32LE(bytes, state, `entry[${entryIndex}] hi`);
      readU32LE(bytes, state, `entry[${entryIndex}] lo`);
      return null;
    case 15: { /* bignum */
      const digits = readNat(bytes, state, version, `entry[${entryIndex}] bignum digits`);
      for (let i = 0; i < digits; i++) {
        readU32LE(bytes, state, `entry[${entryIndex}] bignum digit[${i}]`);
      }
      return null;
    }
    case 1: /* symbol */
    case 4: { /* function */
      const nameLen = readNat(bytes, state, version, `entry[${entryIndex}] name length`);
      const nameBytes = readSpan(bytes, state, nameLen, `entry[${entryIndex}] name bytes`);
      const pkgLen = readNat(bytes, state, version, `entry[${entryIndex}] package length`);
      const pkgBytes = readSpan(bytes, state, pkgLen, `entry[${entryIndex}] package bytes`);
      return {
        name: textDecoder.decode(nameBytes),
        packageName: pkgLen > 0 ? textDecoder.decode(pkgBytes) : "",
      };
    }
    case 2: { /* string */
      const len = readNat(bytes, state, version, `entry[${entryIndex}] string length`);
      readSpan(bytes, state, len, `entry[${entryIndex}] string bytes`);
      return null;
    }
    case 3: /* vector */
    case 5: { /* function-vector */
      const count = readNat(bytes, state, version, `entry[${entryIndex}] vector count`);
      for (let i = 0; i < count; i++) {
        readNat(bytes, state, version, `entry[${entryIndex}] vector index[${i}]`);
      }
      return null;
    }
    case 16: /* entry-function */
      readNat(bytes, state, version, `entry[${entryIndex}] entry-function index`);
      return null;
    case 9: { /* gvector */
      readNat(bytes, state, version, `entry[${entryIndex}] gvector subtag`);
      const count = readNat(bytes, state, version, `entry[${entryIndex}] gvector count`);
      for (let i = 0; i < count; i++) {
        readNat(bytes, state, version, `entry[${entryIndex}] gvector index[${i}]`);
      }
      return null;
    }
    case 7: { /* package */
      const len = readNat(bytes, state, version, `entry[${entryIndex}] package length`);
      readSpan(bytes, state, len, `entry[${entryIndex}] package bytes`);
      return null;
    }
    case 8: /* cons */
      readNat(bytes, state, version, `entry[${entryIndex}] cons car`);
      readNat(bytes, state, version, `entry[${entryIndex}] cons cdr`);
      return null;
    default:
      throw new Error(`const-pool entry[${entryIndex}] has unsupported tag ${tag}`);
  }
}

function encodeU32LE(value) {
  const v = value >>> 0;
  return Uint8Array.from([
    v & 0xff,
    (v >>> 8) & 0xff,
    (v >>> 16) & 0xff,
    (v >>> 24) & 0xff,
  ]);
}

function encodeUleb32(value) {
  const out = [];
  let remaining = value >>> 0;
  do {
    let byte = remaining & 0x7f;
    remaining >>>= 7;
    if (remaining !== 0) byte |= 0x80;
    out.push(byte);
  } while (remaining !== 0);
  return Uint8Array.from(out);
}

function encodeNat(value, version) {
  if (version >= 2) return encodeUleb32(value);
  return encodeU32LE(value);
}

function concatBytes(chunks) {
  let total = 0;
  for (const chunk of chunks) {
    total += chunk.length;
  }
  const out = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    out.set(chunk, offset);
    offset += chunk.length;
  }
  return out;
}

function encodeEntryFunctionPayload(version, resolvedEntryIndex) {
  return concatBytes([
    encodeNat(16, version),
    encodeNat(resolvedEntryIndex >>> 0, version),
  ]);
}

function encodeSymbolPayload(version, name, packageName) {
  const nameBytes = textEncoder.encode(normalizeFunctionName(name));
  const pkgBytes = textEncoder.encode(normalizePackageName(packageName));
  return concatBytes([
    encodeNat(1, version),
    encodeNat(nameBytes.length >>> 0, version),
    nameBytes,
    encodeNat(pkgBytes.length >>> 0, version),
    pkgBytes,
  ]);
}

export function createBootstrapFunctionResolver({
  phase = PHASE_BOOTSTRAP,
  allowAmbiguous = false,
} = {}) {
  const exact = new Map();
  const upper = new Map();
  let currentPhase = normalizePhase(phase);
  const stats = {
    registered: 0,
    ignored: 0,
    ambiguous: 0,
    uniqueNames: 0,
  };

  function registerNameVariants(rawName, entryIndex) {
    const name = normalizeFunctionName(rawName);
    if (!name) {
      stats.ignored++;
      return;
    }
    const idx = entryIndex >>> 0;
    addLookupRecord(exact, name, idx);
    addLookupRecord(upper, uppercaseKey(name), idx);
    stats.registered++;
  }

  function registerFunctions(entries, { source = "bundle.functions" } = {}) {
    if (!Array.isArray(entries)) {
      return {
        source,
        registered: 0,
        ignored: 0,
        ambiguous: stats.ambiguous,
        uniqueNames: stats.uniqueNames,
      };
    }

    const beforeRegistered = stats.registered;
    const beforeIgnored = stats.ignored;
    for (const entry of entries) {
      if (!entry || typeof entry.name !== "string" || !Number.isFinite(entry.entryIndex)) {
        stats.ignored++;
        continue;
      }
      registerNameVariants(entry.name, entry.entryIndex);
    }

    let ambiguousCount = 0;
    for (const record of exact.values()) {
      if (record.ambiguous) ambiguousCount++;
    }
    stats.ambiguous = ambiguousCount;
    stats.uniqueNames = exact.size;

    return {
      source,
      registered: stats.registered - beforeRegistered,
      ignored: stats.ignored - beforeIgnored,
      ambiguous: stats.ambiguous,
      uniqueNames: stats.uniqueNames,
    };
  }

  function resolveByKey(rawKey) {
    const key = normalizeFunctionName(rawKey);
    if (!key) return null;

    const exactRecord = exact.get(key);
    if (exactRecord) {
      if (exactRecord.ambiguous && !allowAmbiguous) {
        return {
          ok: false,
          reason: "ambiguous",
          key,
          alternatives: exactRecord.alternatives.slice(),
        };
      }
      const resolvedEntry = exactRecord.ambiguous
        ? (exactRecord.alternatives[0] >>> 0)
        : (exactRecord.entryIndex >>> 0);
      return { ok: true, reason: "metadata", key, entryIndex: resolvedEntry };
    }

    const upperRecord = upper.get(uppercaseKey(key));
    if (upperRecord) {
      if (upperRecord.ambiguous && !allowAmbiguous) {
        return {
          ok: false,
          reason: "ambiguous",
          key: uppercaseKey(key),
          alternatives: upperRecord.alternatives.slice(),
        };
      }
      const resolvedEntry = upperRecord.ambiguous
        ? (upperRecord.alternatives[0] >>> 0)
        : (upperRecord.entryIndex >>> 0);
      return { ok: true, reason: "metadata-uppercase", key: uppercaseKey(key), entryIndex: resolvedEntry };
    }

    return null;
  }

  function resolveFunctionDesignator({ name, packageName = "" } = {}) {
    if (currentPhase !== PHASE_BOOTSTRAP) {
      return { ok: false, reason: "phase-disabled", phase: currentPhase };
    }

    const fnName = normalizeFunctionName(name);
    if (!fnName) {
      return { ok: false, reason: "missing-name" };
    }

    const pkg = normalizePackageName(packageName);
    const keyCandidates = [];
    if (pkg) {
      keyCandidates.push(`${pkg}::${fnName}`);
      keyCandidates.push(`${pkg}:${fnName}`);
    }
    keyCandidates.push(fnName);

    let ambiguousResult = null;
    for (const key of keyCandidates) {
      const result = resolveByKey(key);
      if (!result) continue;
      if (result.ok) {
        return {
          ok: true,
          entryIndex: result.entryIndex >>> 0,
          source: result.reason,
          key: result.key,
          phase: currentPhase,
        };
      }
      if (result.reason === "ambiguous" && !ambiguousResult) {
        ambiguousResult = result;
      }
    }

    if (ambiguousResult) {
      return {
        ok: false,
        reason: "ambiguous",
        key: ambiguousResult.key,
        alternatives: ambiguousResult.alternatives ?? [],
        phase: currentPhase,
      };
    }
    return { ok: false, reason: "missing", phase: currentPhase };
  }

  function setPhase(nextPhase) {
    currentPhase = normalizePhase(nextPhase);
    return currentPhase;
  }

  function getPhase() {
    return currentPhase;
  }

  function snapshot() {
    return {
      phase: currentPhase,
      allowAmbiguous: Boolean(allowAmbiguous),
      registered: stats.registered,
      ignored: stats.ignored,
      ambiguous: stats.ambiguous,
      uniqueNames: stats.uniqueNames,
    };
  }

  return {
    registerFunctions,
    resolveFunctionDesignator,
    setPhase,
    getPhase,
    snapshot,
  };
}

export function registerResolverFunctionsFromBundle(resolver, bundle, opts = {}) {
  if (!resolver || typeof resolver.registerFunctions !== "function") {
    return {
      source: "bundle.functions",
      registered: 0,
      ignored: 0,
      ambiguous: 0,
      uniqueNames: 0,
    };
  }
  const functions = Array.isArray(bundle?.functions) ? bundle.functions : [];
  return resolver.registerFunctions(functions, opts);
}

export function rewriteConstPoolFunctionDesignators(
  constPoolBytes,
  {
    resolver = null,
    entryIndex = 0,
    requiredResolveOrFailNames = null,
    deferredAllowedNames = null,
    symbolPackageOverrides = null,
    symbolToEntryFunctionNames = null,
    maxDiagnostics = 64,
  } = {},
) {
  const bytes = asU8(constPoolBytes);
  const requiredNameSet = normalizeDesignatorNameSet(requiredResolveOrFailNames);
  const deferredNameSet = normalizeDesignatorNameSet(deferredAllowedNames);
  const symbolPackageOverrideMap = normalizeSymbolPackageOverrides(symbolPackageOverrides);
  const symbolToEntryFunctionNameSet = normalizeDesignatorNameSet(symbolToEntryFunctionNames);
  if (!resolver || typeof resolver.resolveFunctionDesignator !== "function" || bytes.length === 0) {
    return {
      bytes,
      changed: false,
      changedCount: 0,
      scannedFunctionEntries: 0,
      unresolvedCount: 0,
      requiredResolvedCount: 0,
      requiredUnresolvedCount: 0,
      deferredResolvedCount: 0,
      deferredUnresolvedCount: 0,
      noncriticalUnresolvedCount: 0,
      symbolPackageRewriteCount: 0,
      symbolPackageRewrites: [],
      symbolFunctionDesignatorRewriteCount: 0,
      symbolFunctionDesignatorRewrites: [],
      rewrites: [],
      unresolved: [],
      requiredResolved: [],
      requiredUnresolved: [],
      deferredResolved: [],
      deferredUnresolved: [],
      noncriticalUnresolved: [],
    };
  }

  const state = { offset: 0 };
  let version;
  let count;
  if (bytes.length >= 8 &&
      bytes[0] === 1 &&
      bytes[1] === 0 &&
      bytes[2] === 0 &&
      bytes[3] === 0) {
    version = readU32LE(bytes, state, "version");
    count = readU32LE(bytes, state, "count");
  } else {
    version = readUleb32(bytes, state, "version");
    count = readUleb32(bytes, state, "count");
  }
  if (version !== 1 && version !== 2) {
    throw new Error(`unsupported const-pool version: ${version}`);
  }

  const headerEnd = state.offset;
  const entries = new Array(count);
  let changedCount = 0;
  let scannedFunctionEntries = 0;
  let unresolvedCount = 0;
  const rewrites = [];
  const unresolved = [];
  let requiredResolvedCount = 0;
  let requiredUnresolvedCount = 0;
  let deferredResolvedCount = 0;
  let deferredUnresolvedCount = 0;
  let noncriticalUnresolvedCount = 0;
  let symbolPackageRewriteCount = 0;
  const symbolPackageRewrites = [];
  let symbolFunctionDesignatorRewriteCount = 0;
  const symbolFunctionDesignatorRewrites = [];
  const requiredResolved = [];
  const requiredUnresolved = [];
  const deferredResolved = [];
  const deferredUnresolved = [];
  const noncriticalUnresolved = [];

  for (let i = 0; i < count; i++) {
    const start = state.offset;
    const tag = readNat(bytes, state, version, `entry[${i}] tag`);
    const functionInfo = skipConstPoolEntry(bytes, state, version, tag, i);
    const end = state.offset;
    let replacement = null;

    if (tag === 4) {
      scannedFunctionEntries++;
      const name = functionInfo?.name ?? "";
      const packageName = functionInfo?.packageName ?? "";
      const normalizedName = uppercaseKey(normalizeFunctionName(name));
      const normalizedPackageName = uppercaseKey(normalizePackageName(packageName));
      if (
        normalizedName === "NIL" &&
        (normalizedPackageName === "COMMON-LISP" || normalizedPackageName === "CL" || normalizedPackageName === "")
      ) {
        replacement = encodeSymbolPayload(version, "NIL", "COMMON-LISP");
        changedCount++;
        if (rewrites.length < maxDiagnostics) {
          rewrites.push({
            constIndex: i >>> 0,
            name,
            packageName,
            resolvedEntryIndex: null,
            source: "literal-nil-function-designator-coercion",
            policyClass: POLICY_NONCRITICAL,
            bindingState: "coerced-nil-symbol-designator",
          });
        }
        entries[i] = {
          start,
          end,
          replacement,
        };
        continue;
      }
      const policyClass = classifyFunctionDesignatorPolicy(name, requiredNameSet, deferredNameSet);
      const isRequired = policyClass === POLICY_REQUIRED_RESOLVE_OR_FAIL;
      const isDeferred = policyClass === POLICY_DEFERRED_ALLOWED;
      const resolution = resolver.resolveFunctionDesignator({
        name,
        packageName,
        ownerEntryIndex: entryIndex >>> 0,
        constPoolIndex: i >>> 0,
      });
      if (resolution?.ok) {
        replacement = encodeEntryFunctionPayload(version, resolution.entryIndex >>> 0);
        changedCount++;
        if (rewrites.length < maxDiagnostics) {
          rewrites.push({
            constIndex: i >>> 0,
            name,
            packageName,
            resolvedEntryIndex: resolution.entryIndex >>> 0,
            source: resolution.source ?? "metadata",
            policyClass,
            bindingState: "resolved-entry-function",
          });
        }
        if (isRequired) {
          requiredResolvedCount++;
          if (requiredResolved.length < maxDiagnostics) {
            requiredResolved.push({
              constIndex: i >>> 0,
              name,
              packageName,
              resolvedEntryIndex: resolution.entryIndex >>> 0,
              source: resolution.source ?? "metadata",
              policyClass,
              bindingState: "resolved-entry-function",
            });
          }
        } else if (isDeferred) {
          deferredResolvedCount++;
          if (deferredResolved.length < maxDiagnostics) {
            deferredResolved.push({
              constIndex: i >>> 0,
              name,
              packageName,
              resolvedEntryIndex: resolution.entryIndex >>> 0,
              source: resolution.source ?? "metadata",
              policyClass,
              bindingState: "resolved-entry-function",
            });
          }
        }
      } else {
        if (!isRequired && STARTUP_ENABLE_UNRESOLVED_FUNCTION_DESIGNATOR_COERCION) {
          const fallbackPackageName = resolvePreFasloadSymbolPackageFallback(packageName);
          const coercedPackageName = (
            normalizedPackageName === "COMMON-LISP" || normalizedPackageName === "CL"
          )
            ? "COMMON-LISP"
            : (fallbackPackageName ?? packageName);
          replacement = encodeSymbolPayload(version, name, coercedPackageName);
          changedCount++;
          if (rewrites.length < maxDiagnostics) {
            rewrites.push({
              constIndex: i >>> 0,
              name,
              packageName,
              resolvedEntryIndex: null,
              source: "unresolved-function-designator-coercion",
              policyClass,
              bindingState: "coerced-symbol-designator",
              coercedPackageName,
              reason: resolution?.reason ?? "missing",
            });
          }
          entries[i] = {
            start,
            end,
            replacement,
          };
          continue;
        }
        unresolvedCount++;
        const bindingState = unresolvedBindingStateForPolicy(policyClass);
        if (unresolved.length < maxDiagnostics) {
          unresolved.push({
            constIndex: i >>> 0,
            name,
            packageName,
            reason: resolution?.reason ?? "missing",
            policyClass,
            bindingState,
          });
        }
        if (isRequired) {
          requiredUnresolvedCount++;
          if (requiredUnresolved.length < maxDiagnostics) {
            requiredUnresolved.push({
              constIndex: i >>> 0,
              name,
              packageName,
              reason: resolution?.reason ?? "missing",
              policyClass,
              bindingState,
            });
          }
        } else if (isDeferred) {
          deferredUnresolvedCount++;
          if (deferredUnresolved.length < maxDiagnostics) {
            deferredUnresolved.push({
              constIndex: i >>> 0,
              name,
              packageName,
              reason: resolution?.reason ?? "missing",
              policyClass,
              bindingState,
            });
          }
        } else {
          noncriticalUnresolvedCount++;
          if (noncriticalUnresolved.length < maxDiagnostics) {
            noncriticalUnresolved.push({
              constIndex: i >>> 0,
              name,
              packageName,
              reason: resolution?.reason ?? "missing",
              policyClass,
              bindingState,
            });
          }
        }
      }
    } else if (tag === 1 && (symbolPackageOverrideMap || symbolToEntryFunctionNameSet)) {
      const name = functionInfo?.name ?? "";
      const packageName = functionInfo?.packageName ?? "";
      const packageNameKey = uppercaseKey(normalizePackageName(packageName));
      const overriddenPackageName = resolveSymbolPackageOverride(name, packageName, symbolPackageOverrideMap);
      const fallbackPackageName = resolvePreFasloadSymbolPackageFallback(packageName);
      const effectivePackageName = overriddenPackageName ?? fallbackPackageName ?? packageName;
      const symbolNameKey = uppercaseKey(normalizeFunctionName(name));
      const rewriteSymbolToEntry = Boolean(
        symbolToEntryFunctionNameSet?.has(symbolNameKey) &&
        packageNameKey !== "KEYWORD"
      );

      if (rewriteSymbolToEntry) {
        const resolution = resolver.resolveFunctionDesignator({
          name,
          packageName: effectivePackageName,
          ownerEntryIndex: entryIndex >>> 0,
          constPoolIndex: i >>> 0,
        });
        if (resolution?.ok) {
          replacement = encodeEntryFunctionPayload(version, resolution.entryIndex >>> 0);
          changedCount++;
          symbolFunctionDesignatorRewriteCount++;
          if (symbolFunctionDesignatorRewrites.length < maxDiagnostics) {
            symbolFunctionDesignatorRewrites.push({
              constIndex: i >>> 0,
              name,
              packageName: effectivePackageName,
              resolvedEntryIndex: resolution.entryIndex >>> 0,
              source: resolution.source ?? "metadata",
              bindingState: "resolved-entry-function-from-symbol",
            });
          }
        }
      }

      if (!replacement && overriddenPackageName && packageNameKey !== "KEYWORD") {
        replacement = encodeSymbolPayload(version, name, effectivePackageName);
        changedCount++;
        symbolPackageRewriteCount++;
        if (symbolPackageRewrites.length < maxDiagnostics) {
          symbolPackageRewrites.push({
            constIndex: i >>> 0,
            name,
            fromPackageName: packageName,
            toPackageName: effectivePackageName,
            source: "symbol-package-override",
            bindingState: "canonicalized-symbol-package",
          });
        }
      }

      if (!replacement && fallbackPackageName && packageNameKey !== "KEYWORD") {
        replacement = encodeSymbolPayload(version, name, effectivePackageName);
        changedCount++;
        symbolPackageRewriteCount++;
        if (symbolPackageRewrites.length < maxDiagnostics) {
          symbolPackageRewrites.push({
            constIndex: i >>> 0,
            name,
            fromPackageName: packageName,
            toPackageName: effectivePackageName,
            source: "pre-fasload-package-fallback",
            bindingState: "canonicalized-symbol-package",
          });
        }
      }
    }

    entries[i] = {
      start,
      end,
      replacement,
    };
  }

  if (changedCount === 0) {
    return {
      bytes,
      changed: false,
      changedCount,
      scannedFunctionEntries,
      unresolvedCount,
      requiredResolvedCount,
      requiredUnresolvedCount,
      deferredResolvedCount,
      deferredUnresolvedCount,
      noncriticalUnresolvedCount,
      symbolPackageRewriteCount,
      symbolPackageRewrites,
      symbolFunctionDesignatorRewriteCount,
      symbolFunctionDesignatorRewrites,
      rewrites,
      unresolved,
      requiredResolved,
      requiredUnresolved,
      deferredResolved,
      deferredUnresolved,
      noncriticalUnresolved,
    };
  }

  const chunks = [bytes.subarray(0, headerEnd)];
  for (const entry of entries) {
    if (entry.replacement) {
      chunks.push(entry.replacement);
    } else {
      chunks.push(bytes.subarray(entry.start, entry.end));
    }
  }
  if (state.offset < bytes.length) {
    chunks.push(bytes.subarray(state.offset));
  }
  const rewrittenBytes = concatBytes(chunks);

  return {
    bytes: rewrittenBytes,
    changed: true,
    changedCount,
    scannedFunctionEntries,
    unresolvedCount,
    requiredResolvedCount,
    requiredUnresolvedCount,
    deferredResolvedCount,
    deferredUnresolvedCount,
    noncriticalUnresolvedCount,
    symbolPackageRewriteCount,
    symbolPackageRewrites,
    symbolFunctionDesignatorRewriteCount,
    symbolFunctionDesignatorRewrites,
    rewrites,
    unresolved,
    requiredResolved,
    requiredUnresolved,
    deferredResolved,
    deferredUnresolved,
    noncriticalUnresolved,
  };
}

export const BOOTSTRAP_RESOLVER_PHASE_BOOTSTRAP = PHASE_BOOTSTRAP;
export const BOOTSTRAP_RESOLVER_PHASE_CANONICAL_LISP = PHASE_CANONICAL_LISP;
export const CONST_POOL_FUNCTION_POLICY_REQUIRED_RESOLVE_OR_FAIL = POLICY_REQUIRED_RESOLVE_OR_FAIL;
export const CONST_POOL_FUNCTION_POLICY_DEFERRED_ALLOWED = POLICY_DEFERRED_ALLOWED;
export const CONST_POOL_FUNCTION_POLICY_NONCRITICAL = POLICY_NONCRITICAL;
export const STARTUP_SYMBOL_PACKAGE_OVERRIDES_CANONICAL_V1 = STARTUP_SYMBOL_PACKAGE_OVERRIDES_V1;
