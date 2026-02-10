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
  requireAbsent(wasm2, /\barm::/i, "compiler/WASM/wasm2.lisp: arm:: namespace usage");
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

  const miscSetLookups = countMatches(
    wasm2,
    /\(wasm2-subprim-fixnum\s+'\.SPmisc-set\)/g,
  );
  assert(
    miscSetLookups === 1,
    `expected exactly one shared .SPmisc-set fallback lookup, found ${miscSetLookups}`,
  );
}

function gateA14ToA16(rootDir) {
  const a17Path = "doc/wasm/tickets/evidence/bpl-10/b10c-01a-17-fixnum-add-checkpoint-2026-02-10.json";
  const a18Path = "doc/wasm/tickets/evidence/bpl-10/b10c-01a-18-misc-set-fallback-checkpoint-2026-02-10.json";
  const a17 = readJson(rootDir, a17Path);
  const a18 = readJson(rootDir, a18Path);

  assert((a17?.options?.perfSamples ?? null) === 3, "A-17 checkpoint perfSamples must equal 3");
  assert((a17?.options?.perfBudgetDeltaNs ?? null) === 0, "A-17 checkpoint perfBudgetDeltaNs must equal 0");
  assert((a17?.repeatability?.sampleCount ?? null) === 3, "A-17 repeatability sampleCount must equal 3");
  assert(a17?.repeatability?.allSamplesWithinBudget === true, "A-17 repeatability must be fully in budget");

  const directCallsPerOp =
    a17?.lanes?.afterDirect?.dynamicPath?.callsPerOperation?.wasm_return_fixnum_add ?? 0;
  assert(directCallsPerOp === 0, "A-17 direct lane wasm_return_fixnum_add calls/op must remain 0");

  const miscSetCallsPerOp = a18?.dynamicPath?.miscSetCallsPerOperation;
  assert(
    Number.isFinite(miscSetCallsPerOp) && miscSetCallsPerOp > 0,
    "A-18 checkpoint misc-set calls/op must be finite and positive",
  );
  assert(miscSetCallsPerOp <= 1, "A-18 checkpoint misc-set calls/op must be <= 1");
}

function main() {
  const scriptDir = path.dirname(fileURLToPath(import.meta.url));
  const rootDir = path.resolve(scriptDir, "..", "..");

  const wasmArchPath = "compiler/WASM/wasm-arch.lisp";
  const wasm2Path = "compiler/WASM/wasm2.lisp";
  const wasmArch = readUtf8(rootDir, wasmArchPath);
  const wasm2 = readUtf8(rootDir, wasm2Path);

  gateA01ToA08(rootDir, wasmArch, wasm2);
  gateA09ToA13(wasm2);
  gateA14ToA16(rootDir);

  console.log("PASS: B10C-01A-01..A-16 hardening gate");
  console.log("  - A-01..A-08 static invariants: clean");
  console.log("  - A-09..A-13 emission/fallback boundaries: clean");
  console.log("  - A-14..A-16 evidence discipline: clean");
}

main();
