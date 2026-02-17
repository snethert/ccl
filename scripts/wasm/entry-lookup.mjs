#!/usr/bin/env node
/**
 * entry-lookup.mjs — Map WASM entry indices to function names and module info.
 *
 * Usage:
 *   node scripts/wasm/entry-lookup.mjs <entry-index>
 *   node scripts/wasm/entry-lookup.mjs <entry-index> --extract   # extract WASM module to stdout
 *   node scripts/wasm/entry-lookup.mjs --list                    # list all entries
 *   node scripts/wasm/entry-lookup.mjs --range <start> <end>     # list range
 *
 * Searches all module bundles in build/wasm32/modules/ for the given entry index.
 */

import { readFileSync, readdirSync, writeFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { decodeModuleBundleIndexV2 } from "./lib/module-bundle-v2.mjs";

const __filename = fileURLToPath(import.meta.url);
const REPO_ROOT = join(dirname(__filename), "../..");
const MODULES_DIR = join(REPO_ROOT, "build/wasm32/modules");

function loadBundle(jsonPath) {
  const meta = JSON.parse(readFileSync(jsonPath, "utf-8"));
  const baseName = jsonPath.replace(/\.json$/, "");
  const bundleName = jsonPath.split("/").pop().replace(/\.json$/, "");
  const result = { meta, bundleName, jsonPath, modules: [], nameMap: new Map() };

  if (meta.version === 2 && meta.index) {
    // V2 format — decode the binary index
    const idxPath = join(dirname(jsonPath), meta.index);
    const idxBytes = readFileSync(idxPath);
    const decoded = decodeModuleBundleIndexV2(idxBytes, {
      templatePrefix: meta.exportNameTemplatePrefix,
    });
    result.modules = decoded.modules;
    result.binPath = join(dirname(jsonPath), meta.binary);

    // If functions array has names, build name map
    if (meta.functions && meta.functions.length > 0) {
      for (const fn of meta.functions) {
        result.nameMap.set(fn.entryIndex, fn.name);
      }
    }
  } else if (meta.modules) {
    // V1 inline format
    result.modules = meta.modules;
    result.binPath = meta.binary ? join(dirname(jsonPath), meta.binary) : null;
    if (meta.functions) {
      for (const fn of meta.functions) {
        result.nameMap.set(fn.entryIndex, fn.name);
      }
    }
  }

  return result;
}

function loadAllBundles() {
  const bundles = [];
  const files = readdirSync(MODULES_DIR).filter(
    (f) => f.endsWith(".json") && f.startsWith("wasm-")
  );
  for (const f of files) {
    try {
      bundles.push(loadBundle(join(MODULES_DIR, f)));
    } catch (e) {
      // skip unreadable bundles
    }
  }
  return bundles;
}

function findEntry(bundles, entryIndex) {
  for (const bundle of bundles) {
    const mod = bundle.modules.find((m) => m.entryIndex === entryIndex);
    if (mod) {
      const name = bundle.nameMap.get(entryIndex) || null;
      return { bundle, module: mod, name };
    }
  }
  return null;
}

function formatEntry(entryIndex, mod, name, bundleName) {
  const parts = [`entry ${entryIndex}`];
  if (name) parts.push(`name: ${name}`);
  parts.push(`export: ${mod.exportName}`);
  parts.push(`bundle: ${bundleName}`);
  parts.push(`offset: ${mod.offset}, length: ${mod.length}`);
  if (mod.constPoolId != null) {
    parts.push(`constPool: id=${mod.constPoolId} offset=${mod.constPoolOffset} len=${mod.constPoolLength}`);
  }
  if (mod.moduleVersion != null) parts.push(`version: ${mod.moduleVersion}`);
  return parts.join(" | ");
}

function main() {
  const args = process.argv.slice(2);

  if (args.length === 0 || args.includes("--help") || args.includes("-h")) {
    console.error("Usage:");
    console.error("  node entry-lookup.mjs <entry-index>           # look up single entry");
    console.error("  node entry-lookup.mjs <entry-index> --extract # extract WASM bytes");
    console.error("  node entry-lookup.mjs --list                  # list all entries");
    console.error("  node entry-lookup.mjs --range <start> <end>   # list entry range");
    console.error("  node entry-lookup.mjs --search <pattern>      # search by name");
    process.exit(1);
  }

  const bundles = loadAllBundles();

  if (args[0] === "--list") {
    for (const bundle of bundles) {
      for (const mod of bundle.modules) {
        const name = bundle.nameMap.get(mod.entryIndex) || "";
        console.log(formatEntry(mod.entryIndex, mod, name, bundle.bundleName));
      }
    }
    return;
  }

  if (args[0] === "--range") {
    const start = parseInt(args[1], 10);
    const end = parseInt(args[2], 10);
    if (isNaN(start) || isNaN(end)) {
      console.error("Usage: --range <start> <end>");
      process.exit(1);
    }
    for (const bundle of bundles) {
      for (const mod of bundle.modules) {
        if (mod.entryIndex >= start && mod.entryIndex <= end) {
          const name = bundle.nameMap.get(mod.entryIndex) || "";
          console.log(formatEntry(mod.entryIndex, mod, name, bundle.bundleName));
        }
      }
    }
    return;
  }

  if (args[0] === "--search") {
    const pattern = (args[1] || "").toUpperCase();
    if (!pattern) {
      console.error("Usage: --search <pattern>");
      process.exit(1);
    }
    for (const bundle of bundles) {
      for (const [entryIndex, name] of bundle.nameMap) {
        if (name.toUpperCase().includes(pattern)) {
          const mod = bundle.modules.find((m) => m.entryIndex === entryIndex);
          if (mod) {
            console.log(formatEntry(entryIndex, mod, name, bundle.bundleName));
          }
        }
      }
    }
    return;
  }

  // Single entry lookup
  const entryIndex = parseInt(args[0], 10);
  if (isNaN(entryIndex)) {
    console.error(`Invalid entry index: ${args[0]}`);
    process.exit(1);
  }

  const result = findEntry(bundles, entryIndex);
  if (!result) {
    console.error(`Entry ${entryIndex} not found in any bundle.`);

    // Show nearby entries for context
    const nearby = [];
    for (const bundle of bundles) {
      for (const mod of bundle.modules) {
        if (Math.abs(mod.entryIndex - entryIndex) <= 5) {
          const name = bundle.nameMap.get(mod.entryIndex) || "";
          nearby.push({ entryIndex: mod.entryIndex, mod, name, bundleName: bundle.bundleName });
        }
      }
    }
    if (nearby.length > 0) {
      console.error("\nNearby entries:");
      nearby.sort((a, b) => a.entryIndex - b.entryIndex);
      for (const n of nearby) {
        console.error("  " + formatEntry(n.entryIndex, n.mod, n.name, n.bundleName));
      }
    }
    process.exit(1);
  }

  const { bundle, module: mod, name } = result;
  console.log(formatEntry(entryIndex, mod, name, bundle.bundleName));

  if (args.includes("--extract")) {
    // Extract WASM module bytes to a file
    if (!bundle.binPath) {
      console.error("No binary file path available for extraction.");
      process.exit(1);
    }
    const bin = readFileSync(bundle.binPath);
    const wasmBytes = bin.subarray(mod.offset, mod.offset + mod.length);
    const outPath = `/tmp/entry-${entryIndex}.wasm`;
    writeFileSync(outPath, wasmBytes);
    console.log(`Extracted ${wasmBytes.length} bytes to ${outPath}`);
  }
}

main();
