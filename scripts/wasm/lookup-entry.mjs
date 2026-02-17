#!/usr/bin/env node
/**
 * Lookup WASM entry indices → function names.
 *
 * Usage:
 *   node scripts/wasm/lookup-entry.mjs 856
 *   node scripts/wasm/lookup-entry.mjs 0x358
 *   node scripts/wasm/lookup-entry.mjs 856 1123 489
 *   echo "CALL 00000358" | node scripts/wasm/lookup-entry.mjs --stdin
 *
 * Searches both boot and runtime module manifests.
 */

import { readFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createInterface } from "node:readline";

const __dirname = dirname(fileURLToPath(import.meta.url));
const repoRoot = join(__dirname, "../..");
const modulesDir = join(repoRoot, "build/wasm32/modules");

const BOOT_MANIFEST = join(modulesDir, "wasm-boot-modules.json");
const RUNTIME_MANIFEST = join(modulesDir, "wasm-runtime-modules.json");

function loadManifest(path) {
  if (!existsSync(path)) return null;
  try {
    return JSON.parse(readFileSync(path, "utf-8"));
  } catch {
    return null;
  }
}

function buildIndex(manifest, source) {
  const map = new Map();
  if (!manifest?.functions) return map;
  for (const fn of manifest.functions) {
    if (Number.isFinite(fn?.entryIndex)) {
      map.set(fn.entryIndex, { name: fn.name ?? "<unnamed>", source });
    }
  }
  return map;
}

function parseEntryIndex(s) {
  const trimmed = s.trim();
  if (trimmed.startsWith("0x") || trimmed.startsWith("0X")) {
    return parseInt(trimmed, 16);
  }
  if (/^[0-9a-fA-F]{5,}$/.test(trimmed)) {
    // 5+ hex digits without prefix — treat as hex (matches CALL output format)
    return parseInt(trimmed, 16);
  }
  const n = parseInt(trimmed, 10);
  return Number.isFinite(n) ? n : NaN;
}

// Build combined index
const bootManifest = loadManifest(BOOT_MANIFEST);
const runtimeManifest = loadManifest(RUNTIME_MANIFEST);
const index = new Map([
  ...buildIndex(bootManifest, "boot"),
  ...buildIndex(runtimeManifest, "runtime"),
]);

function lookup(entryIndex) {
  const entry = index.get(entryIndex);
  const hex = "0x" + entryIndex.toString(16).padStart(4, "0");
  if (entry) {
    return `${entryIndex} (${hex})  ${entry.name}  [${entry.source}]`;
  }
  return `${entryIndex} (${hex})  <not found>`;
}

// Extract entry indices from a line of trace output
function extractFromLine(line) {
  const results = [];
  // Match "CALL XXXXXXXX" pattern from trace output
  const callMatch = line.match(/CALL\s+([0-9a-fA-F]{8})/g);
  if (callMatch) {
    for (const m of callMatch) {
      const hex = m.replace(/^CALL\s+/, "");
      const n = parseInt(hex, 16);
      if (Number.isFinite(n)) results.push(n);
    }
  }
  // Match "LEG=XXXXXXXX" pattern from old trace format
  const legMatch = line.match(/LEG=([0-9a-fA-F]{8})/g);
  if (legMatch) {
    for (const m of legMatch) {
      const hex = m.replace(/^LEG=/, "");
      const n = parseInt(hex, 16);
      if (Number.isFinite(n)) results.push(n);
    }
  }
  // Match "entry=NNNN" pattern
  const entryMatch = line.match(/entry=(\d+)/g);
  if (entryMatch) {
    for (const m of entryMatch) {
      const n = parseInt(m.replace(/^entry=/, ""), 10);
      if (Number.isFinite(n)) results.push(n);
    }
  }
  return results;
}

const args = process.argv.slice(2);

if (args.includes("-h") || args.includes("--help")) {
  console.log("Usage: lookup-entry.mjs [--stdin] [entry_index ...]");
  console.log("");
  console.log("  entry_index   Decimal or hex (0x prefix or 5+ hex digits)");
  console.log("  --stdin       Read trace output from stdin, annotate entry indices");
  console.log("");
  console.log(`Boot manifest:    ${existsSync(BOOT_MANIFEST) ? "found" : "MISSING"} (${BOOT_MANIFEST})`);
  console.log(`Runtime manifest: ${existsSync(RUNTIME_MANIFEST) ? "found" : "MISSING"} (${RUNTIME_MANIFEST})`);
  console.log(`Total entries indexed: ${index.size}`);
  process.exit(0);
}

if (args.includes("--stdin")) {
  // Pipe mode: read lines, annotate any entry indices found
  const rl = createInterface({ input: process.stdin });
  for await (const line of rl) {
    const indices = extractFromLine(line);
    if (indices.length > 0) {
      const names = indices.map((n) => {
        const entry = index.get(n);
        return entry ? entry.name : `<${n}>`;
      });
      console.log(`${line}  → ${names.join(", ")}`);
    } else {
      console.log(line);
    }
  }
} else if (args.length === 0) {
  console.error("Usage: lookup-entry.mjs [--stdin] [entry_index ...]");
  console.error("  Try: lookup-entry.mjs 856");
  process.exit(1);
} else {
  // Direct lookup mode
  for (const arg of args) {
    const n = parseEntryIndex(arg);
    if (Number.isNaN(n)) {
      console.log(`${arg}  <invalid>`);
    } else {
      console.log(lookup(n));
    }
  }
}
