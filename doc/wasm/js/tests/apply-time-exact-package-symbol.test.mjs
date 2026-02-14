import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const TEST_DIR = path.dirname(fileURLToPath(import.meta.url));
const MAKE_REAL_IMAGE_PATH = path.resolve(TEST_DIR, "../make-real-image.mjs");

function extractBlock(source, startMarker, endMarker) {
  const start = source.indexOf(startMarker);
  assert.notEqual(start, -1, `missing start marker: ${startMarker}`);
  const end = source.indexOf(endMarker, start);
  assert.notEqual(end, -1, `missing end marker: ${endMarker}`);
  return source.slice(start, end);
}

function summarizeStartupBindingMapArtifactStub(mapArtifact) {
  const entries = Array.isArray(mapArtifact?.entries) ? mapArtifact.entries : [];
  let literalEntries = 0;
  let entryBackedEntries = 0;
  let deferredEntries = 0;
  let unsupportedEntries = 0;
  let vcellEntries = 0;
  let fcellEntries = 0;
  let specialVariableEntries = 0;
  let functionEntries = 0;
  for (const entry of entries) {
    const availability = String(entry?.availability ?? "").trim().toLowerCase();
    if (availability === "literal") literalEntries++;
    else if (availability === "entry-backed") entryBackedEntries++;
    else if (availability === "deferred") deferredEntries++;
    else unsupportedEntries++;

    const targetCell = String(entry?.target_cell ?? "").trim().toLowerCase();
    if (targetCell === "fcell") fcellEntries++;
    else vcellEntries++;

    const bindingClass = String(entry?.binding_class ?? "").trim().toLowerCase();
    if (bindingClass === "function") functionEntries++;
    else if (bindingClass === "special-variable") specialVariableEntries++;
  }
  return {
    total_entries: entries.length,
    literal_entries: literalEntries,
    deferred_entries: deferredEntries,
    unsupported_entries: unsupportedEntries,
    entry_backed_entries: entryBackedEntries,
    vcell_entries: vcellEntries,
    fcell_entries: fcellEntries,
    special_variable_entries: specialVariableEntries,
    function_entries: functionEntries,
  };
}

function loadApplyHelpers() {
  const source = fs.readFileSync(MAKE_REAL_IMAGE_PATH, "utf8");
  const startupResolutionBlock = extractBlock(
    source,
    "const STARTUP_SYMBOL_RESOLUTION_STATUS = Object.freeze({",
    "function fail(msg) {",
  );
  const probeStatusBlock = extractBlock(
    source,
    "const L0_PROBE_STATUS = Object.freeze({",
    "function buildStartupSymbolResolutionArtifact({",
  );
  const applyBlock = extractBlock(
    source,
    "function applyStartupBindingMapOrFail({",
    "function assertL0BootstrapContractOrFail(contract = BOOTSTRAP_L0_CONTRACT_V1) {",
  );

  const factory = new Function(
    "deps",
    `const summarizeStartupBindingMapArtifact = deps.summarizeStartupBindingMapArtifact;
const fail = deps.fail;
const ex = deps.ex;
const runtime = deps.runtime;
const copyBytesToScratch = deps.copyBytesToScratch;
const constPoolsInstalled = deps.constPoolsInstalled;
const BOOTSTRAP_L0_CONTRACT_V1 = deps.contract;
${startupResolutionBlock}
${probeStatusBlock}
${applyBlock}
return {
  applyStartupBindingMapOrFail,
  L0_PROBE_STATUS,
  WASM_SYMBOL_CELL_INITIALIZER_KIND,
};`,
  );
  return factory;
}

function createApplyHarness({ presentSymbols = [], disableSetSymbolCellInitializer = false } = {}) {
  const STATUS = {
    OK: 0,
    ARG_INVALID: 1,
    PACKAGE_MISSING: 2,
    SYMBOL_MISSING: 3,
  };

  let nextPtr = 4096;
  const scratchBytes = new Map();
  const runtime = { memory: {} };
  const copyBytesToScratch = (_memory, bytes) => {
    const ptr = nextPtr >>> 0;
    nextPtr = (nextPtr + bytes.length + 8) >>> 0;
    scratchBytes.set(ptr, Uint8Array.from(bytes));
    return ptr;
  };
  const readUtf8 = (ptr, len) => {
    if (!ptr || !len) return "";
    const bytes = scratchBytes.get(ptr >>> 0);
    if (!bytes) return "";
    return Buffer.from(bytes.slice(0, len >>> 0)).toString("utf8");
  };
  const normalizeKey = (packageName, symbolName) => (
    `${String(packageName ?? "").trim().toUpperCase()}::${String(symbolName ?? "").trim().toUpperCase()}`
  );

  const symbolByKey = new Map();
  const keyByRaw = new Map();
  const vcellByRaw = new Map();
  let nextSymbolRaw = 0x1000;
  const internSymbol = (packageName, symbolName) => {
    const key = normalizeKey(packageName, symbolName);
    const existing = symbolByKey.get(key);
    if (existing != null) return existing >>> 0;
    const raw = nextSymbolRaw >>> 0;
    nextSymbolRaw = (nextSymbolRaw + 4) >>> 0;
    symbolByKey.set(key, raw);
    keyByRaw.set(raw, key);
    vcellByRaw.set(raw, 0);
    return raw;
  };
  for (const symbol of presentSymbols) {
    internSymbol(symbol?.packageName, symbol?.symbolName);
  }

  let lastStatus = STATUS.OK;
  const probeCalls = [];
  const initializerCalls = [];

  const ex = {
    wasm_get_lisp_nil() {
      return 0;
    },
    wasm_probe_symbol(namePtr, nameLen, packagePtr, packageLen) {
      const symbolName = readUtf8(namePtr, nameLen).trim();
      const packageName = readUtf8(packagePtr, packageLen).trim();
      probeCalls.push({ packageName, symbolName });
      if (!packageName || !symbolName) {
        lastStatus = STATUS.ARG_INVALID;
        return 0;
      }
      const key = normalizeKey(packageName, symbolName);
      const raw = symbolByKey.get(key);
      if (raw == null) {
        const packagePrefix = `${String(packageName).toUpperCase()}::`;
        const packageKnown = Array.from(symbolByKey.keys()).some((item) => item.startsWith(packagePrefix));
        lastStatus = packageKnown ? STATUS.SYMBOL_MISSING : STATUS.PACKAGE_MISSING;
        return 0;
      }
      lastStatus = STATUS.OK;
      return raw >>> 0;
    },
    wasm_probe_symbol_fcell() {
      lastStatus = STATUS.OK;
      return 0;
    },
    wasm_probe_symbol_vcell(symbolRaw) {
      lastStatus = STATUS.OK;
      return (vcellByRaw.get(symbolRaw >>> 0) ?? 0) >>> 0;
    },
    wasm_probe_last_status() {
      return lastStatus >>> 0;
    },
    wasm_debug_function_entry_index() {
      return -1;
    },
  };
  if (!disableSetSymbolCellInitializer) {
    ex.wasm_set_symbol_cell_initializer = (
      namePtr,
      nameLen,
      packagePtr,
      packageLen,
      targetCell,
      initializerKind,
      _fixnumValue,
      _entryIndex,
      literalNamePtr,
      literalNameLen,
      literalPackagePtr,
      literalPackageLen,
    ) => {
      const targetSymbolName = readUtf8(namePtr, nameLen).trim();
      const targetPackageName = readUtf8(packagePtr, packageLen).trim();
      const literalSymbolName = readUtf8(literalNamePtr, literalNameLen).trim();
      const literalPackageName = readUtf8(literalPackagePtr, literalPackageLen).trim();
      initializerCalls.push({
        targetPackageName,
        targetSymbolName,
        targetCell: targetCell >>> 0,
        initializerKind: initializerKind >>> 0,
        literalPackageName,
        literalSymbolName,
      });
      const targetKey = normalizeKey(targetPackageName, targetSymbolName);
      const targetRaw = symbolByKey.get(targetKey);
      if (targetRaw == null) {
        lastStatus = STATUS.SYMBOL_MISSING;
        return 0;
      }
      // Mark target as initialized to a non-nil value for post-apply vcell probe.
      vcellByRaw.set(targetRaw >>> 0, 0x70000000 | ((initializerKind >>> 0) & 0xffff));
      lastStatus = STATUS.OK;
      return 0;
    };
  }

  return {
    ex,
    runtime,
    copyBytesToScratch,
    probeCalls,
    initializerCalls,
    keyByRaw,
  };
}

const applyHelpersFactory = loadApplyHelpers();

function runApply(entries, presentSymbols, harnessOptions = {}) {
  const harness = createApplyHarness({ presentSymbols, ...harnessOptions });
  const helpers = applyHelpersFactory({
    summarizeStartupBindingMapArtifact: summarizeStartupBindingMapArtifactStub,
    fail: (msg) => {
      throw new Error(msg);
    },
    ex: harness.ex,
    runtime: harness.runtime,
    copyBytesToScratch: harness.copyBytesToScratch,
    constPoolsInstalled: new Set(),
    contract: { id: "unit-contract" },
  });

  const mapArtifact = {
    schema_version: "startup_binding_map_v1",
    coverage: {
      required_special_variable_bindings: 0,
    },
    entries,
  };
  const summary = helpers.applyStartupBindingMapOrFail({
    mapArtifact,
    mapSource: "unit-test",
    contract: { id: "unit-contract" },
  });
  return {
    summary,
    helpers,
    probeCalls: harness.probeCalls,
    initializerCalls: harness.initializerCalls,
    keyByRaw: harness.keyByRaw,
  };
}

function makeLiteralSymbolEntry({ packageName, symbolName, literalPackageName, literalSymbolName }) {
  return {
    package_name: packageName,
    symbol_name: symbolName,
    target_cell: "vcell",
    binding_class: "special-variable",
    require_non_nil: false,
    availability: "literal",
    initializer: {
      kind: "literal-symbol",
      literal_package_name: literalPackageName,
      literal_symbol_name: literalSymbolName,
    },
  };
}

function makeLiteralKeywordEntry({ packageName, symbolName, literalKeywordName }) {
  return {
    package_name: packageName,
    symbol_name: symbolName,
    target_cell: "vcell",
    binding_class: "special-variable",
    require_non_nil: false,
    availability: "literal",
    initializer: {
      kind: "literal-keyword",
      literal_keyword_name: literalKeywordName,
    },
  };
}

test("apply-time literal-symbol uses exact package+name probe only (no fallback)", () => {
  const entry = makeLiteralSymbolEntry({
    packageName: "WRONGPKG",
    symbolName: "TARGET",
    literalPackageName: "VALUEPKG",
    literalSymbolName: "VALUE",
  });
  const { summary, probeCalls, initializerCalls } = runApply(
    [entry],
    [{ packageName: "RIGHTPKG", symbolName: "TARGET" }],
  );

  assert.equal(summary.status, "pass");
  assert.equal(summary.counts.applied_count, 0);
  assert.equal(summary.counts.skipped_symbol_unresolved, 1);
  assert.equal(initializerCalls.length, 0);
  assert.deepEqual(probeCalls, [{ packageName: "WRONGPKG", symbolName: "TARGET" }]);
});

test("apply-time literal-keyword uses exact package+name probe only (no fallback)", () => {
  const entry = makeLiteralKeywordEntry({
    packageName: "NOT-KEYWORD",
    symbolName: "MODE",
    literalKeywordName: "FAST",
  });
  const { summary, probeCalls, initializerCalls } = runApply(
    [entry],
    [{ packageName: "KEYWORD", symbolName: "MODE" }],
  );

  assert.equal(summary.status, "pass");
  assert.equal(summary.counts.applied_count, 0);
  assert.equal(summary.counts.skipped_symbol_unresolved, 1);
  assert.equal(initializerCalls.length, 0);
  assert.deepEqual(probeCalls, [{ packageName: "NOT-KEYWORD", symbolName: "MODE" }]);
});

test("apply-time literal-symbol applies when exact package+name matches", () => {
  const entry = makeLiteralSymbolEntry({
    packageName: "APP",
    symbolName: "ACTIVE-SYMBOL",
    literalPackageName: "VALUEPKG",
    literalSymbolName: "VALUE",
  });
  const { summary, helpers, initializerCalls } = runApply(
    [entry],
    [{ packageName: "APP", symbolName: "ACTIVE-SYMBOL" }],
  );

  assert.equal(summary.status, "pass");
  assert.equal(summary.counts.applied_count, 1);
  assert.equal(initializerCalls.length, 1);
  assert.deepEqual(initializerCalls[0], {
    targetPackageName: "APP",
    targetSymbolName: "ACTIVE-SYMBOL",
    targetCell: 1,
    initializerKind: helpers.WASM_SYMBOL_CELL_INITIALIZER_KIND.LITERAL_SYMBOL,
    literalPackageName: "VALUEPKG",
    literalSymbolName: "VALUE",
  });
});

test("apply-time literal-keyword applies when exact package+name matches", () => {
  const entry = makeLiteralKeywordEntry({
    packageName: "APP",
    symbolName: "MODE",
    literalKeywordName: "FAST",
  });
  const { summary, helpers, initializerCalls } = runApply(
    [entry],
    [{ packageName: "APP", symbolName: "MODE" }],
  );

  assert.equal(summary.status, "pass");
  assert.equal(summary.counts.applied_count, 1);
  assert.equal(initializerCalls.length, 1);
  assert.deepEqual(initializerCalls[0], {
    targetPackageName: "APP",
    targetSymbolName: "MODE",
    targetCell: 1,
    initializerKind: helpers.WASM_SYMBOL_CELL_INITIALIZER_KIND.LITERAL_KEYWORD,
    literalPackageName: "KEYWORD",
    literalSymbolName: "FAST",
  });
});

test("required literal-symbol missing-kernel-export fails explicitly", () => {
  const entry = {
    ...makeLiteralSymbolEntry({
      packageName: "APP",
      symbolName: "MANDATORY",
      literalPackageName: "VALUEPKG",
      literalSymbolName: "VALUE",
    }),
    require_non_nil: true,
  };
  const errors = [];
  const originalError = console.error;
  console.error = (...args) => {
    errors.push(args.map(String).join(" "));
    originalError(...args);
  };
  try {
    assert.throws(
      () => runApply([entry], [{ packageName: "APP", symbolName: "MANDATORY" }], {
        disableSetSymbolCellInitializer: true,
      }),
      /pre-fasload startup binding map apply failed/,
    );
  } finally {
    console.error = originalError;
  }

  assert.ok(
    errors.some((line) => line.includes("\"reason\":\"missing-kernel-export\"")),
    "expected missing-kernel-export failure reason in STARTUP_BINDING_MAP_APPLY log",
  );
});

test("optional literal-keyword missing-kernel-export defer uses initializer-kind-not-supported reason", () => {
  const entry = makeLiteralKeywordEntry({
    packageName: "APP",
    symbolName: "OPTIONAL-MODE",
    literalKeywordName: "FAST",
  });
  const { summary, initializerCalls } = runApply(
    [entry],
    [{ packageName: "APP", symbolName: "OPTIONAL-MODE" }],
    { disableSetSymbolCellInitializer: true },
  );

  assert.equal(summary.status, "pass");
  assert.equal(summary.counts.optional_deferred_missing_export, 1);
  assert.equal(summary.counts.applied_count, 0);
  assert.equal(initializerCalls.length, 0);
  assert.equal(
    summary.first_optional_deferred_missing_export?.reason,
    "initializer-kind-not-supported",
  );
  assert.equal(
    summary.first_optional_deferred_missing_export?.optional_policy,
    "optional-initializer-kind-not-supported-defer",
  );
  assert.equal(
    summary.first_optional_deferred_missing_export?.export_name,
    "wasm_set_symbol_cell_initializer",
  );
});
