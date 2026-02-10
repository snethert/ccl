#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

function fail(msg) {
  console.error(`FAIL: ${msg}`);
  process.exit(1);
}

function findDefunBounds(source, fnName) {
  const anchor = `(defun ${fnName}`;
  const start = source.indexOf(anchor);
  if (start < 0) {
    return null;
  }
  let i = start;
  let depth = 0;
  let inString = false;
  while (i < source.length) {
    const ch = source[i];
    if (inString) {
      if (ch === "\\" && (i + 1) < source.length) {
        i += 2;
        continue;
      }
      if (ch === "\"") {
        inString = false;
      }
      i += 1;
      continue;
    }
    if (ch === ";") {
      while (i < source.length && source[i] !== "\n") {
        i += 1;
      }
      continue;
    }
    if (ch === "\"") {
      inString = true;
      i += 1;
      continue;
    }
    if (ch === "(") {
      depth += 1;
    } else if (ch === ")") {
      depth -= 1;
      if (depth === 0) {
        return { start, end: i + 1 };
      }
      if (depth < 0) {
        fail(`unbalanced parens while parsing ${fnName}`);
      }
    }
    i += 1;
  }
  fail(`unterminated defun while parsing ${fnName}`);
}

function rewriteCompatBoundaryReturnEpilogue(source, fnName) {
  const bounds = findDefunBounds(source, fnName);
  if (!bounds) {
    fail(`missing function: ${fnName}`);
  }
  const block = source.slice(bounds.start, bounds.end);
  const rewritten = block.replace(
    /\(when\s+\(wasm2-returning-p xfer\)\n\s+\(wasm2-emit :set-arg-z\)\n\s+\(wasm2-emit :set-nargs 1\)\n\s+\(wasm2-emit :return\)\)/,
    `(when (wasm2-returning-p xfer)
      (wasm2-emit :return-constant)
      (wasm2-emit :return))`,
  );
  if (rewritten === block) {
    return { source, changed: false };
  }
  return {
    source: `${source.slice(0, bounds.start)}${rewritten}${source.slice(bounds.end)}`,
    changed: true,
  };
}

function main() {
  const scriptDir = path.dirname(fileURLToPath(import.meta.url));
  const rootDir = path.resolve(scriptDir, "..", "..");
  const wasm2Path = path.join(rootDir, "compiler/WASM/wasm2.lisp");
  if (!fs.existsSync(wasm2Path)) {
    fail("missing compiler/WASM/wasm2.lisp");
  }

  const original = fs.readFileSync(wasm2Path, "utf8");
  let source = original;
  let changed = false;

  for (const fnName of [
    "wasm2-emit-compat-boundary-subprim-binary-call",
    "wasm2-emit-compat-boundary-subprim-unary-call",
  ]) {
    const step = rewriteCompatBoundaryReturnEpilogue(source, fnName);
    source = step.source;
    changed = changed || step.changed;
  }

  if (!changed) {
    console.log("PASS: no deterministic speed-prune changes required");
    return;
  }

  fs.writeFileSync(wasm2Path, source, "utf8");
  console.log("PASS: applied deterministic speed-prune changes to compiler/WASM/wasm2.lisp");
}

main();
