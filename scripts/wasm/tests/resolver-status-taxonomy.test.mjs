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

function loadResolverHelpers() {
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

  const factory = new Function(
    `${startupResolutionBlock}\n${probeStatusBlock}\n` +
      "return {" +
      " STARTUP_SYMBOL_RESOLUTION_STATUS," +
      " STARTUP_SYMBOL_RESOLUTION_COUNTER_FIELDS," +
      " STARTUP_SYMBOL_REQUIRED_CLASS," +
      " startupSymbolBindingKey," +
      " startupSymbolRequiredClass," +
      " createStartupSymbolResolutionCounters," +
      " incrementStartupSymbolResolutionUnresolvedCounters," +
      " L0_PROBE_STATUS," +
      " startupSymbolResolutionReasonForProbeStatus," +
      " l0ProbeStatusName" +
      " };",
  );
  return factory();
}

const helpers = loadResolverHelpers();

test("resolver status taxonomy includes probe-error and invalid-input", () => {
  const values = Object.values(helpers.STARTUP_SYMBOL_RESOLUTION_STATUS).sort();
  assert.deepEqual(values, ["invalid-input", "probe-error", "resolved", "unresolved"]);
});

test("resolution counters include required_unresolved and optional_unresolved", () => {
  const fields = helpers.STARTUP_SYMBOL_RESOLUTION_COUNTER_FIELDS;
  assert.ok(fields.includes("required_unresolved"));
  assert.ok(fields.includes("optional_unresolved"));

  const counters = helpers.createStartupSymbolResolutionCounters();
  for (const field of fields) {
    assert.equal(counters[field], 0, `counter ${field} should initialize to zero`);
  }
});

test("unresolved counter split increments required_unresolved and optional_unresolved", () => {
  const counters = helpers.createStartupSymbolResolutionCounters();

  helpers.incrementStartupSymbolResolutionUnresolvedCounters(
    counters,
    helpers.STARTUP_SYMBOL_REQUIRED_CLASS.REQUIRED_CALLABLE,
  );
  helpers.incrementStartupSymbolResolutionUnresolvedCounters(
    counters,
    helpers.STARTUP_SYMBOL_REQUIRED_CLASS.REQUIRED_SPECIAL,
  );
  helpers.incrementStartupSymbolResolutionUnresolvedCounters(
    counters,
    helpers.STARTUP_SYMBOL_REQUIRED_CLASS.OPTIONAL,
  );
  helpers.incrementStartupSymbolResolutionUnresolvedCounters(
    counters,
    helpers.STARTUP_SYMBOL_REQUIRED_CLASS.NONE,
  );

  assert.equal(counters.required_unresolved, 2);
  assert.equal(counters.optional_unresolved, 1);
});

test("required-class mapping prefers contract-required classes", () => {
  const callable = helpers.startupSymbolRequiredClass({
    symbolRecord: { bindable: true },
    packageName: "ccl",
    symbolName: "func",
    requiredCallableKeys: new Set(["CCL::FUNC"]),
    requiredSpecialKeys: new Set(),
  });
  assert.equal(callable, helpers.STARTUP_SYMBOL_REQUIRED_CLASS.REQUIRED_CALLABLE);

  const special = helpers.startupSymbolRequiredClass({
    symbolRecord: { bindable: true },
    packageName: "ccl",
    symbolName: "*var*",
    requiredCallableKeys: new Set(),
    requiredSpecialKeys: new Set(["CCL::*VAR*"]),
  });
  assert.equal(special, helpers.STARTUP_SYMBOL_REQUIRED_CLASS.REQUIRED_SPECIAL);

  const optional = helpers.startupSymbolRequiredClass({
    symbolRecord: { bindable: true },
    packageName: "pkg",
    symbolName: "sym",
    requiredCallableKeys: new Set(),
    requiredSpecialKeys: new Set(),
  });
  assert.equal(optional, helpers.STARTUP_SYMBOL_REQUIRED_CLASS.OPTIONAL);

  const none = helpers.startupSymbolRequiredClass({
    symbolRecord: { bindable: false },
    packageName: "pkg",
    symbolName: "sym",
    requiredCallableKeys: new Set(),
    requiredSpecialKeys: new Set(),
  });
  assert.equal(none, helpers.STARTUP_SYMBOL_REQUIRED_CLASS.NONE);
});

test("probe statuses map to resolver reasons", () => {
  assert.equal(
    helpers.startupSymbolResolutionReasonForProbeStatus(helpers.L0_PROBE_STATUS.PACKAGE_MISSING),
    "package-missing",
  );
  assert.equal(
    helpers.startupSymbolResolutionReasonForProbeStatus(helpers.L0_PROBE_STATUS.SYMBOL_MISSING),
    "symbol-missing",
  );
  assert.equal(
    helpers.startupSymbolResolutionReasonForProbeStatus(helpers.L0_PROBE_STATUS.ARG_INVALID),
    "arg-invalid",
  );
  assert.equal(
    helpers.startupSymbolResolutionReasonForProbeStatus(helpers.L0_PROBE_STATUS.SYMBOL_NOT_SYMBOL),
    "symbol-not-symbol",
  );
  assert.equal(
    helpers.startupSymbolResolutionReasonForProbeStatus(helpers.L0_PROBE_STATUS.SYMBOL_INVALID),
    "symbol-invalid",
  );
  assert.equal(
    helpers.startupSymbolResolutionReasonForProbeStatus(helpers.L0_PROBE_STATUS.PACKAGE_NOT_PACKAGE),
    "package-not-package",
  );
  assert.equal(helpers.startupSymbolResolutionReasonForProbeStatus(255), "probe-status-not-ok");
  assert.equal(helpers.l0ProbeStatusName(255), "status-255");
});
