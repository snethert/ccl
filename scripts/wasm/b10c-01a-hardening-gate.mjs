#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

function fail(message) {
  console.error(`FAIL: ${message}`);
  process.exit(1);
}

function assert(condition, message) {
  if (!condition) fail(message);
}

function readUtf8(rootDir, relPath) {
  const fullPath = path.join(rootDir, relPath);
  if (!fs.existsSync(fullPath)) {
    fail(`missing required file: ${relPath}`);
  }
  return fs.readFileSync(fullPath, "utf8");
}

function readJson(rootDir, relPath) {
  const fullPath = path.join(rootDir, relPath);
  if (!fs.existsSync(fullPath)) {
    fail(`missing required artifact: ${relPath}`);
  }
  return JSON.parse(fs.readFileSync(fullPath, "utf8"));
}

function requirePresent(text, regex, label) {
  assert(regex.test(text), `missing expected invariant: ${label}`);
}

function requireAbsent(text, regex, label) {
  assert(!regex.test(text), `forbidden regression detected: ${label}`);
}

function countMatches(text, regex) {
  const matches = text.match(regex);
  return matches ? matches.length : 0;
}

function requireCount(text, regex, expected, label) {
  const actual = countMatches(text, regex);
  assert(actual === expected, `${label}: expected ${expected}, found ${actual}`);
}

function runArmRetirementAudit(rootDir) {
  const cmd = path.join(rootDir, "scripts/wasm/arm-retirement-audit.sh");
  const res = spawnSync(cmd, ["--strict"], {
    cwd: rootDir,
    stdio: "pipe",
    encoding: "utf8",
  });
  process.stdout.write(res.stdout ?? "");
  process.stderr.write(res.stderr ?? "");
  assert(res.status === 0, "arm-retirement strict audit failed");
}

function gateA01ToA08(rootDir, wasmArch, wasm2) {
  runArmRetirementAudit(rootDir);

  requireAbsent(wasmArch, /require\s+"ARM-ARCH"/, 'compiler/WASM/wasm-arch.lisp: require "ARM-ARCH"');
  requireAbsent(wasmArch, /\*arm-target-arch\*/, "compiler/WASM/wasm-arch.lisp: *arm-target-arch*");
  requireAbsent(wasmArch, /\*arm-subprims\*/, "compiler/WASM/wasm-arch.lisp: *arm-subprims*");
  requireAbsent(wasmArch, /shadowing-import/i, "compiler/WASM/wasm-arch.lisp: ARM shadowing-import bridge");
  requirePresent(
    wasmArch,
    /\(defparameter\s+\*wasm-subprim-names\*/,
    "compiler/WASM/wasm-arch.lisp: wasm-owned subprim name table",
  );
  requirePresent(
    wasmArch,
    /\(defun\s+wasm-build-subprims-table\b/,
    "compiler/WASM/wasm-arch.lisp: wasm-owned subprim table builder",
  );
  requirePresent(
    wasmArch,
    /\(setf\s+\*wasm-subprims\*\s+\(wasm-build-subprims-table\)\)/,
    "compiler/WASM/wasm-arch.lisp: wasm-owned subprim table install",
  );
  requireAbsent(wasm2, /\barm::/i, "compiler/WASM/wasm2.lisp: arm:: namespace usage");
}

function gateA02ToA03(allSmoke, fixnumAddSmoke) {
  requirePresent(
    allSmoke,
    /\.\/fixnum-add-smoke\.mjs/,
    "doc/wasm/js/all-smoke.mjs: fixnum-add smoke lane registration",
  );
  requirePresent(
    allSmoke,
    /\.\/fixnum-overflow-smoke\.mjs/,
    "doc/wasm/js/all-smoke.mjs: fixnum-overflow smoke lane registration",
  );
  requirePresent(
    allSmoke,
    /\.\/compiler-smoke\.mjs/,
    "doc/wasm/js/all-smoke.mjs: compiler smoke lane registration",
  );
  requirePresent(
    fixnumAddSmoke,
    /args\.includes\("--perf-checkpoint"\)/,
    "doc/wasm/js/fixnum-add-smoke.mjs: perf-checkpoint mode",
  );
  requirePresent(
    fixnumAddSmoke,
    /"--perf-samples"/,
    "doc/wasm/js/fixnum-add-smoke.mjs: --perf-samples option",
  );
  requirePresent(
    fixnumAddSmoke,
    /"--perf-budget-delta-ns"/,
    "doc/wasm/js/fixnum-add-smoke.mjs: --perf-budget-delta-ns option",
  );
  requirePresent(
    fixnumAddSmoke,
    /"--perf-max-direct-helper-calls-per-op"/,
    "doc/wasm/js/fixnum-add-smoke.mjs: direct helper-call bound option",
  );
  requirePresent(
    fixnumAddSmoke,
    /wasm_return_fixnum_add/,
    "doc/wasm/js/fixnum-add-smoke.mjs: dynamic helper-call accounting",
  );
}

function gateA09ToA13(wasm2) {
  requirePresent(
    wasm2,
    /\(defun\s+wasm2-emit-hot-direct-fixnum-binary-op\b/,
    "A-09 direct binary fixnum lowering helper",
  );
  requirePresent(
    wasm2,
    /\(defun\s+wasm2-emit-hot-direct-fixnum-unary-op\b/,
    "A-09 direct unary fixnum lowering helper",
  );
  requirePresent(
    wasm2,
    /\(defun\s+wasm2-emit-compat-fallback-fixnum-binary-op\b/,
    "A-09 compat fallback binary helper",
  );
  requirePresent(
    wasm2,
    /\(defun\s+wasm2-emit-compat-fallback-fixnum-unary-op\b/,
    "A-09 compat fallback unary helper",
  );
  requirePresent(
    wasm2,
    /:fixnum-add\s+\(wasm2-emit-fixnum-binary-op\s+body\s+:fixnum-add\s+:return-fixnum-add\)/,
    "A-10 fixnum-add direct-lane dispatch",
  );
  requirePresent(
    wasm2,
    /:fixnum-sub\s+\(wasm2-emit-fixnum-binary-op\s+body\s+:fixnum-sub\s+:return-fixnum-sub\)/,
    "A-10 fixnum-sub direct-lane dispatch",
  );
  requirePresent(
    wasm2,
    /:fixnum-mul\s+\(wasm2-emit-fixnum-binary-op\s+body\s+:fixnum-mul\s+:return-fixnum-mul\)/,
    "A-10 fixnum-mul direct-lane dispatch",
  );
  requirePresent(
    wasm2,
    /:fixnum-logand\s+\(wasm2-emit-fixnum-binary-op\s+body\s+:fixnum-logand\s+:return-fixnum-logand\)/,
    "A-10 fixnum-logand direct-lane dispatch",
  );
  requirePresent(
    wasm2,
    /:fixnum-logior\s+\(wasm2-emit-fixnum-binary-op\s+body\s+:fixnum-logior\s+:return-fixnum-logior\)/,
    "A-10 fixnum-logior direct-lane dispatch",
  );
  requirePresent(
    wasm2,
    /:fixnum-logxor\s+\(wasm2-emit-fixnum-binary-op\s+body\s+:fixnum-logxor\s+:return-fixnum-logxor\)/,
    "A-10 fixnum-logxor direct-lane dispatch",
  );
  requirePresent(
    wasm2,
    /:fixnum-lognot\s+\(wasm2-emit-fixnum-unary-op\s+body\s+:fixnum-lognot\s+:return-fixnum-lognot\)/,
    "A-11 fixnum-lognot direct-lane dispatch",
  );
  requirePresent(
    wasm2,
    /:fixnum-neg\s+\(wasm2-emit-fixnum-unary-op\s+body\s+:fixnum-neg\s+:return-fixnum-neg\)/,
    "A-11 fixnum-neg direct-lane dispatch",
  );
  requirePresent(
    wasm2,
    /:fixnum-ash\s+\(wasm2-emit-fixnum-binary-op\s+body\s+:fixnum-ash\s+:return-fixnum-ash\)/,
    "A-12 fixnum-ash direct-lane dispatch",
  );
  requirePresent(
    wasm2,
    /\(defparameter\s+\*wasm2-no-spill-fixnum-compat-op-keys\*/,
    "A-13 compat spill classification table",
  );
  requirePresent(
    wasm2,
    /\(defun\s+wasm2-validate-spill-discipline\b/,
    "A-13 spill-discipline validator",
  );

  requirePresent(
    wasm2,
    /\(defparameter\s+\*wasm2-compat-boundary-subprim-map\*/,
    "A-15 compat-boundary subprim map",
  );
  requirePresent(
    wasm2,
    /\(defun\s+wasm2-compat-boundary-subprim-fixnum\b/,
    "A-15 compat-boundary lookup function",
  );
  requireAbsent(
    wasm2,
    /\(wasm2-subprim-fixnum\s+'\.SPbuiltin-(?:div|negate|ash)\b/,
    "A-15 direct default lookup of compat-only .SPbuiltin-{div,negate,ash}",
  );
}

function gateA19Active(wasm2) {
  requirePresent(
    wasm2,
    /\(defun\s+wasm2-emit-misc-ref-fallback-local\b/,
    "A-19 shared .SPmisc-ref fallback helper",
  );
  requirePresent(
    wasm2,
    /\(defun\s+wasm2-emit-misc-slot-ref-with-subtag-guard\b/,
    "A-19 guarded direct misc-ref helper",
  );

  const miscSetLookups = countMatches(
    wasm2,
    /\(wasm2-subprim-fixnum\s+'\.SPmisc-set\)/g,
  );
  assert(
    miscSetLookups === 1,
    `expected exactly one shared .SPmisc-set fallback lookup, found ${miscSetLookups}`,
  );

  const miscRefLookups = countMatches(
    wasm2,
    /\(wasm2-subprim-fixnum\s+'\.SPmisc-ref\)/g,
  );
  assert(
    miscRefLookups === 1,
    `A-19 active baseline requires exactly one shared .SPmisc-ref fallback lookup, found ${miscRefLookups}`,
  );

  const subtagMiscRefLookups = countMatches(
    wasm2,
    /\(wasm2-subprim-fixnum\s+'\.SPsubtag-misc-ref\)/g,
  );
  assert(
    subtagMiscRefLookups === 1,
    `A-19 active baseline requires 1 .SPsubtag-misc-ref lookup, found ${subtagMiscRefLookups}`,
  );

  const subtagMiscSetLookups = countMatches(
    wasm2,
    /\(wasm2-subprim-fixnum\s+'\.SPsubtag-misc-set\)/g,
  );
  assert(
    subtagMiscSetLookups === 2,
    `A-19 active baseline requires 2 .SPsubtag-misc-set lookups, found ${subtagMiscSetLookups}`,
  );
}

function gateA14ToA16(rootDir, wasm2, kernelStubs, subprimsProvider) {
  const a17Path = "doc/wasm/tickets/evidence/bpl-10/b10c-01a-17-fixnum-add-checkpoint-2026-02-10.json";
  const a18Path = "doc/wasm/tickets/evidence/bpl-10/b10c-01a-18-misc-set-fallback-checkpoint-2026-02-10.json";
  const a17 = readJson(rootDir, a17Path);
  const a18 = readJson(rootDir, a18Path);

  requirePresent(
    kernelStubs,
    /Compatibility-only fixnum return helpers\./,
    "A-14 compatibility-only helper policy in wasm-kernel-stubs.c",
  );
  requirePresent(
    wasm2,
    /Deliberately avoid hard-mapping simple fixnum IR to fixed compatibility/,
    "A-14 no hard-mapping of simple fixnum IR to compat entry slots",
  );
  for (const compatEntrySymbol of [
    "\\+wasm-fixnum-add-entry-index\\+",
    "\\+wasm-fixnum-sub-entry-index\\+",
    "\\+wasm-fixnum-mul-entry-index\\+",
    "\\+wasm-fixnum-ash-entry-index\\+",
    "\\+wasm-fixnum-logand-entry-index\\+",
    "\\+wasm-fixnum-logior-entry-index\\+",
    "\\+wasm-fixnum-logxor-entry-index\\+",
    "\\+wasm-fixnum-lognot-entry-index\\+",
    "\\+wasm-fixnum-neg-entry-index\\+",
  ]) {
    requireCount(
      wasm2,
      new RegExp(compatEntrySymbol, "g"),
      1,
      `A-14 compat entry constant usage ${compatEntrySymbol}`,
    );
  }
  requirePresent(
    subprimsProvider,
    /wasm_call_compat_math_builtin\s*\(/,
    "A-15 provider compat math builtin dispatcher",
  );
  requirePresent(
    subprimsProvider,
    /wasm_call_compat_math_builtin\(tcr,\s*WASM_BUILTIN_DIV,\s*2\)/,
    "A-15 provider compat dispatch for divide",
  );
  requirePresent(
    subprimsProvider,
    /wasm_call_compat_math_builtin\(tcr,\s*WASM_BUILTIN_NEGATE,\s*1\)/,
    "A-15 provider compat dispatch for negate",
  );
  requirePresent(
    subprimsProvider,
    /wasm_call_compat_math_builtin\(tcr,\s*WASM_BUILTIN_ASH,\s*2\)/,
    "A-15 provider compat dispatch for ash",
  );

  assert((a17?.options?.perfSamples ?? null) === 3, "A-17 checkpoint perfSamples must equal 3");
  assert((a17?.options?.perfBudgetDeltaNs ?? null) === 0, "A-17 checkpoint perfBudgetDeltaNs must equal 0");
  assert(
    (a17?.options?.perfMaxDirectHelperCallsPerOp ?? null) === 0,
    "A-17 checkpoint perfMaxDirectHelperCallsPerOp must equal 0",
  );
  assert((a17?.repeatability?.sampleCount ?? null) === 3, "A-17 repeatability sampleCount must equal 3");
  assert(a17?.repeatability?.allSamplesWithinBudget === true, "A-17 repeatability must be fully in budget");

  const directCallsPerOpDynamic = a17?.lanes?.afterDirect?.dynamicPath?.callsPerOperation?.wasm_return_fixnum_add;
  const directCallsPerOpBound = a17?.bounds?.directFixnumAddCallsPerOp;
  const directCallsPerOp = Number.isFinite(directCallsPerOpDynamic)
    ? directCallsPerOpDynamic
    : directCallsPerOpBound;
  assert(
    Number.isFinite(directCallsPerOp),
    "A-17 direct lane wasm_return_fixnum_add calls/op must be present and finite",
  );
  assert(directCallsPerOp === 0, "A-17 direct lane wasm_return_fixnum_add calls/op must remain 0");
  assert(
    a17?.bounds?.withinDirectFixnumAddBound === true,
    "A-17 direct lane helper-call bound flag must be true",
  );
  assert(
    (a17?.bounds?.maxDirectFixnumAddCallsPerOp ?? null) === 0,
    "A-17 direct lane helper-call bound must remain 0",
  );

  const miscSetCallsPerOp = a18?.dynamicPath?.miscSetCallsPerOperation;
  assert(
    Number.isFinite(miscSetCallsPerOp) && miscSetCallsPerOp > 0,
    "A-18 checkpoint misc-set calls/op must be finite and positive",
  );
  assert(miscSetCallsPerOp <= 1, "A-18 checkpoint misc-set calls/op must be <= 1");
  assert(a18?.bounds?.withinBound === true, "A-18 checkpoint bound flag must be true");
  assert((a18?.bounds?.maxMiscSetCallsPerOp ?? null) === 1, "A-18 max misc-set calls/op bound must be 1");
}

function main() {
  const scriptDir = path.dirname(fileURLToPath(import.meta.url));
  const rootDir = path.resolve(scriptDir, "..", "..");

  const wasmArchPath = "compiler/WASM/wasm-arch.lisp";
  const wasm2Path = "compiler/WASM/wasm2.lisp";
  const allSmokePath = "doc/wasm/js/all-smoke.mjs";
  const fixnumAddSmokePath = "doc/wasm/js/fixnum-add-smoke.mjs";
  const kernelStubsPath = "lisp-kernel/wasm-kernel-stubs.c";
  const subprimsProviderPath = "lisp-kernel/wasm-subprims-provider.c";
  const wasmArch = readUtf8(rootDir, wasmArchPath);
  const wasm2 = readUtf8(rootDir, wasm2Path);
  const allSmoke = readUtf8(rootDir, allSmokePath);
  const fixnumAddSmoke = readUtf8(rootDir, fixnumAddSmokePath);
  const kernelStubs = readUtf8(rootDir, kernelStubsPath);
  const subprimsProvider = readUtf8(rootDir, subprimsProviderPath);

  gateA01ToA08(rootDir, wasmArch, wasm2);
  gateA02ToA03(allSmoke, fixnumAddSmoke);
  gateA09ToA13(wasm2);
  gateA19Active(wasm2);
  gateA14ToA16(rootDir, wasm2, kernelStubs, subprimsProvider);

  console.log("PASS: B10C-01A-01..A-16 hardening gate");
  console.log("  - A-01..A-08 static invariants: clean");
  console.log("  - A-02..A-03 gate/metric lanes: clean");
  console.log("  - A-09..A-13 emission/fallback boundaries: clean");
  console.log("  - A-19 active baseline: clean");
  console.log("  - A-14..A-16 evidence discipline: clean");
}

main();
