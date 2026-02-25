#!/usr/bin/env node

/**
 * merge-singleton-modules.mjs — Phase 2C: Merge singleton WASM modules
 *
 * Reads a V2 module bundle, identifies singleton modules (one entry per unique
 * binary), groups them into batches, merges each batch with wasm-merge, and
 * writes an updated V2 bundle.
 *
 * Already-merged modules (multiple entries sharing the same binary) are kept
 * as-is. Const pools are unaffected — they remain separate per entry.
 *
 * Usage:
 *   node scripts/wasm/merge-singleton-modules.mjs \
 *     --manifest build/wasm32/modules/wasm-boot-modules.json \
 *     --in-place [--batch-size 100]
 */

import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";
import os from "node:os";
import { execFileSync } from "node:child_process";

import {
  decodeModuleBundleIndexV2,
  encodeModuleBundleIndexV2,
  MODULE_BUNDLE_V2_DEFAULT_TEMPLATE_PREFIX,
  MODULE_BUNDLE_V2_FORMAT,
  MODULE_BUNDLE_V2_VERSION,
} from "./lib/module-bundle-v2.mjs";

const WASM_MERGE = "/usr/local/bin/wasm-merge";

function usage() {
  console.log("Usage:");
  console.log("  node scripts/wasm/merge-singleton-modules.mjs --manifest PATH --in-place [--batch-size N]");
  console.log("  node scripts/wasm/merge-singleton-modules.mjs --manifest PATH --out-manifest PATH --out-binary PATH --out-index PATH [--batch-size N]");
}

function parseArgs(argv) {
  const opts = {
    manifest: null,
    outManifest: null,
    outBinary: null,
    outIndex: null,
    inPlace: false,
    batchSize: 100,
    templatePrefix: MODULE_BUNDLE_V2_DEFAULT_TEMPLATE_PREFIX,
  };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--manifest") { opts.manifest = argv[++i] ?? null; continue; }
    if (arg === "--out-manifest") { opts.outManifest = argv[++i] ?? null; continue; }
    if (arg === "--out-binary") { opts.outBinary = argv[++i] ?? null; continue; }
    if (arg === "--out-index") { opts.outIndex = argv[++i] ?? null; continue; }
    if (arg === "--in-place") { opts.inPlace = true; continue; }
    if (arg === "--batch-size") {
      const v = Number.parseInt(argv[++i] ?? "", 10);
      if (!Number.isInteger(v) || v < 2) throw new Error("--batch-size must be >= 2");
      opts.batchSize = v;
      continue;
    }
    if (arg === "--template-prefix") { opts.templatePrefix = argv[++i] ?? ""; continue; }
    if (arg === "-h" || arg === "--help") { usage(); process.exit(0); }
    throw new Error(`Unknown argument: ${arg}`);
  }
  if (!opts.manifest) throw new Error("Missing required --manifest PATH");
  if (opts.inPlace && (opts.outManifest || opts.outBinary || opts.outIndex)) {
    throw new Error("--in-place cannot be combined with explicit output paths");
  }
  if (!opts.templatePrefix) opts.templatePrefix = MODULE_BUNDLE_V2_DEFAULT_TEMPLATE_PREFIX;
  return opts;
}

function toPosixPath(p) {
  return p.split(path.sep).join(path.posix.sep);
}

function readSpan(fd, offset, length) {
  const size = length >>> 0;
  const start = offset >>> 0;
  if (size === 0) return Buffer.alloc(0);
  const out = Buffer.allocUnsafe(size);
  let total = 0;
  while (total < size) {
    const n = fs.readSync(fd, out, total, size - total, start + total);
    if (n === 0) break;
    total += n;
  }
  if (total !== size) throw new Error(`short read: expected ${size}, got ${total} at offset ${start}`);
  return out;
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  const manifestPath = path.resolve(opts.manifest);
  const manifestDir = path.dirname(manifestPath);
  const manifest = JSON.parse(await fsp.readFile(manifestPath, "utf8"));

  if (manifest?.format !== MODULE_BUNDLE_V2_FORMAT) {
    throw new Error(`Unsupported format: ${manifest?.format}`);
  }

  const templatePrefix =
    typeof manifest?.exportNameTemplatePrefix === "string" && manifest.exportNameTemplatePrefix.length > 0
      ? manifest.exportNameTemplatePrefix
      : opts.templatePrefix;

  const inputBinaryPath = path.resolve(manifestDir, manifest.binary);
  const inputIndexPath = manifest?.index
    ? path.resolve(manifestDir, manifest.index)
    : inputBinaryPath.replace(/\.bin$/, ".idx");

  const indexBytes = fs.readFileSync(inputIndexPath);
  const decoded = decodeModuleBundleIndexV2(indexBytes, { templatePrefix });
  const modules = decoded.modules;
  const constPools = decoded.constPools ?? [];

  console.error(`[merge] Input: ${modules.length} entries, ${constPools.length} const pools`);

  // Group entries by their binary span
  const spanToEntries = new Map();
  for (const entry of modules) {
    const key = `${entry.offset}:${entry.length}`;
    if (!spanToEntries.has(key)) spanToEntries.set(key, []);
    spanToEntries.get(key).push(entry);
  }

  // Partition into already-merged (multi-entry) and singletons
  const alreadyMerged = []; // groups of entries sharing a binary
  const singletons = [];    // entries with unique binary
  for (const [, entries] of spanToEntries) {
    if (entries.length > 1) {
      alreadyMerged.push(entries);
    } else {
      singletons.push(entries[0]);
    }
  }

  console.error(`[merge] Already merged: ${alreadyMerged.length} groups (${alreadyMerged.reduce((s, g) => s + g.length, 0)} entries)`);
  console.error(`[merge] Singletons to merge: ${singletons.length}`);

  if (singletons.length < 2) {
    console.error(`[merge] Nothing to merge (need at least 2 singletons)`);
    process.exit(0);
  }

  // Create temp directory for wasm-merge work
  const tmpDir = await fsp.mkdtemp(path.join(os.tmpdir(), "ccl-wasm-merge-"));

  const inFd = fs.openSync(inputBinaryPath, "r");

  // Sort singletons by entryIndex
  singletons.sort((a, b) => a.entryIndex - b.entryIndex);

  // Identify entry-index ranges occupied by already-merged groups.
  // Singletons must only be batched within contiguous "gaps" between these
  // ranges, otherwise the V2 delta-encoded offsets can't be non-decreasing.
  const mergedRanges = [];
  for (const group of alreadyMerged) {
    const indices = group.map(e => e.entryIndex).sort((a, b) => a - b);
    mergedRanges.push({ min: indices[0], max: indices[indices.length - 1] });
  }
  mergedRanges.sort((a, b) => a.min - b.min);

  // Partition singletons into segments: each segment falls entirely between
  // (or before/after) merged group ranges.
  const segments = [[]];
  let rangeIdx = 0;
  for (const entry of singletons) {
    // Advance past any merged ranges that end before this entry
    while (rangeIdx < mergedRanges.length && mergedRanges[rangeIdx].max < entry.entryIndex) {
      rangeIdx++;
      segments.push([]); // start a new segment after crossing a merged range
    }
    segments[segments.length - 1].push(entry);
  }

  // Build batches from segments, respecting batch size
  const batches = [];
  for (const seg of segments) {
    for (let i = 0; i < seg.length; i += opts.batchSize) {
      batches.push(seg.slice(i, i + opts.batchSize));
    }
  }

  console.error(`[merge] ${batches.length} merge batches (batch size ${opts.batchSize})`);

  // Process each batch
  const mergedBatches = []; // { bytes: Buffer, entries: Entry[] }
  let mergedCount = 0;
  let failedBatches = 0;
  const fallbackSingletons = [];

  for (let batchIdx = 0; batchIdx < batches.length; batchIdx++) {
    const batch = batches[batchIdx];
    if (batch.length < 2) {
      // Single entry, keep as singleton
      fallbackSingletons.push(...batch);
      continue;
    }

    const batchDir = path.join(tmpDir, `batch-${batchIdx}`);
    await fsp.mkdir(batchDir, { recursive: true });

    // Extract each module to a temp .wasm file
    const mergeArgs = [];
    for (const entry of batch) {
      const wasmBytes = readSpan(inFd, entry.offset, entry.length);
      const fname = `${entry.exportName}.wasm`;
      const fpath = path.join(batchDir, fname);
      fs.writeFileSync(fpath, wasmBytes);
      mergeArgs.push(fpath, entry.exportName);
    }

    const outPath = path.join(batchDir, "merged.wasm");
    mergeArgs.push("--enable-multimemory", "-o", outPath);

    try {
      execFileSync(WASM_MERGE, mergeArgs, {
        stdio: ["pipe", "pipe", "pipe"],
        timeout: 120000,
        maxBuffer: 64 * 1024 * 1024,
      });
      const mergedBytes = fs.readFileSync(outPath);
      mergedBatches.push({ bytes: mergedBytes, entries: batch });
      mergedCount += batch.length;

      if ((batchIdx + 1) % 5 === 0 || batchIdx === batches.length - 1) {
        console.error(`[merge] batch ${batchIdx + 1}/${batches.length}: merged ${batch.length} -> 1 (${mergedBytes.length} bytes)`);
      }
    } catch (e) {
      console.error(`[merge] WARNING: batch ${batchIdx} failed (${batch.length} modules), falling back to individual: ${(e.stderr ?? e.message).toString().substring(0, 200)}`);
      failedBatches++;
      fallbackSingletons.push(...batch);
    }

    // Clean up batch dir
    await fsp.rm(batchDir, { recursive: true, force: true });
  }

  fs.closeSync(inFd);

  console.error(`[merge] Merged: ${mergedCount} singletons into ${mergedBatches.length} groups`);
  if (failedBatches > 0) {
    console.error(`[merge] Failed batches: ${failedBatches} (${fallbackSingletons.length} entries kept as singletons)`);
  }

  // Rebuild binary. V2 index requires non-decreasing offsets when entries are
  // sorted by entryIndex. We achieve this by processing entries in entryIndex
  // order and writing each group's binary the first time we encounter it.
  const inFd2 = fs.openSync(inputBinaryPath, "r");
  const chunks = [];
  let writeOffset = 0;

  // Build a map from entryIndex → group descriptor
  const entryToGroup = new Map();
  let groupId = 0;

  for (const group of alreadyMerged) {
    const gid = groupId++;
    const rep = group[0];
    const descriptor = { gid, sourceOffset: rep.offset, sourceLength: rep.length, bytes: null, written: false, outOffset: 0, outLength: 0 };
    for (const entry of group) entryToGroup.set(entry.entryIndex, descriptor);
  }

  for (const { bytes, entries } of mergedBatches) {
    const gid = groupId++;
    const descriptor = { gid, sourceOffset: null, sourceLength: null, bytes, written: false, outOffset: 0, outLength: 0 };
    for (const entry of entries) entryToGroup.set(entry.entryIndex, descriptor);
  }

  for (const entry of fallbackSingletons) {
    const gid = groupId++;
    const descriptor = { gid, sourceOffset: entry.offset, sourceLength: entry.length, bytes: null, written: false, outOffset: 0, outLength: 0 };
    entryToGroup.set(entry.entryIndex, descriptor);
  }

  // Process all entries sorted by entryIndex — write each group's binary on first encounter
  const sortedEntries = [...modules].sort((a, b) => a.entryIndex - b.entryIndex);
  const entryUpdates = new Map();

  for (const entry of sortedEntries) {
    const group = entryToGroup.get(entry.entryIndex);
    if (!group) throw new Error(`No group for entry ${entry.entryIndex}`);

    if (!group.written) {
      const binaryBytes = group.bytes ?? readSpan(inFd2, group.sourceOffset, group.sourceLength);
      group.outOffset = writeOffset;
      group.outLength = binaryBytes.length;
      chunks.push(binaryBytes);
      writeOffset += binaryBytes.length;
      group.written = true;
    }

    entryUpdates.set(entry.entryIndex, { offset: group.outOffset, length: group.outLength });
  }

  // Write const pools (read from original binary, update offsets)
  const constPoolUpdates = new Map();
  for (const pool of constPools) {
    const storedLength = pool.storedLength ?? pool.length;
    const poolBytes = readSpan(inFd2, pool.offset, storedLength);
    const newOffset = writeOffset;
    chunks.push(poolBytes);
    writeOffset += poolBytes.length;
    constPoolUpdates.set(pool.id, { offset: newOffset });
  }

  fs.closeSync(inFd2);

  // Build output entries sorted by entryIndex
  const outModules = modules
    .map((entry) => {
      const update = entryUpdates.get(entry.entryIndex);
      if (!update) throw new Error(`Missing update for entry ${entry.entryIndex}`);
      const out = {
        exportName: entry.exportName,
        entryIndex: entry.entryIndex,
        moduleVersion: entry.moduleVersion ?? 1,
        offset: update.offset,
        length: update.length,
      };
      // Preserve stored length / encoding only for non-merged modules
      // Merged modules are raw (wasm-merge output is uncompressed)
      if (entry.moduleStoredLength != null && update.length === entry.length) {
        // This entry wasn't re-merged, might still have compression
        // Actually, we always re-read the raw bytes, so no compression
      }
      if (entry.constPoolId != null) {
        out.constPoolId = entry.constPoolId;
      }
      return out;
    })
    .sort((a, b) => a.entryIndex - b.entryIndex);

  // Build output const pools with updated offsets
  const outConstPools = constPools.map((pool) => {
    const update = constPoolUpdates.get(pool.id);
    if (!update) throw new Error(`Missing update for const pool ${pool.id}`);
    const out = {
      id: pool.id,
      offset: update.offset,
      length: pool.length,
    };
    if (pool.storedLength != null && pool.storedLength !== pool.length) {
      out.storedLength = pool.storedLength;
    }
    if (pool.encoding) out.encoding = pool.encoding;
    if (pool.deltaBaseId != null) {
      out.deltaBaseId = pool.deltaBaseId;
      out.deltaOp = pool.deltaOp;
    }
    return out;
  });

  // Write output files
  const binaryBytes = Buffer.concat(chunks);
  const newIndexBytes = encodeModuleBundleIndexV2({
    modules: outModules,
    constPools: outConstPools,
    templatePrefix,
  });

  // Derive output paths
  let outManifestPath, outBinaryPath, outIndexPath;
  if (opts.inPlace) {
    outManifestPath = manifestPath;
    outBinaryPath = inputBinaryPath;
    outIndexPath = inputIndexPath;
  } else {
    outManifestPath = path.resolve(opts.outManifest ?? manifestPath);
    outBinaryPath = path.resolve(opts.outBinary ?? inputBinaryPath);
    outIndexPath = path.resolve(opts.outIndex ?? inputIndexPath);
  }

  // Write atomically via temp files
  const tmpBin = `${outBinaryPath}.merge-tmp`;
  const tmpIdx = `${outIndexPath}.merge-tmp`;
  const tmpManifest = `${outManifestPath}.merge-tmp`;

  await fsp.writeFile(tmpBin, binaryBytes);
  await fsp.writeFile(tmpIdx, newIndexBytes);

  // Count final unique binaries
  const finalSpans = new Set();
  for (const m of outModules) {
    finalSpans.add(`${m.offset}:${m.length}`);
  }

  const outManifest = {
    format: MODULE_BUNDLE_V2_FORMAT,
    version: MODULE_BUNDLE_V2_VERSION,
    binary: toPosixPath(path.relative(path.dirname(outManifestPath), outBinaryPath)),
    index: toPosixPath(path.relative(path.dirname(outManifestPath), outIndexPath)),
    exportNameTemplatePrefix: templatePrefix,
    moduleCount: outModules.length,
    constPoolCount: outConstPools.length,
  };
  // Preserve functions, gcRootPolicyModes, gcRootBoundaryOps from input
  if (Array.isArray(manifest?.functions)) outManifest.functions = manifest.functions;
  if (manifest?.gcRootPolicyModes) outManifest.gcRootPolicyModes = manifest.gcRootPolicyModes;
  if (manifest?.gcRootBoundaryOps) outManifest.gcRootBoundaryOps = manifest.gcRootBoundaryOps;
  // Preserve shared const pool blob info if present
  if (manifest?.constPoolBlobOffset != null) {
    outManifest.constPoolBlobOffset = manifest.constPoolBlobOffset;
    outManifest.constPoolBlobLength = manifest.constPoolBlobLength;
    if (manifest.constPoolBlobStoredLength != null) outManifest.constPoolBlobStoredLength = manifest.constPoolBlobStoredLength;
    if (manifest.constPoolBlobEncoding != null) outManifest.constPoolBlobEncoding = manifest.constPoolBlobEncoding;
  }

  await fsp.writeFile(tmpManifest, `${JSON.stringify(outManifest)}\n`);

  // Atomic rename
  await fsp.rename(tmpBin, outBinaryPath);
  await fsp.rename(tmpIdx, outIndexPath);
  await fsp.rename(tmpManifest, outManifestPath);

  // Clean up temp dir
  await fsp.rm(tmpDir, { recursive: true, force: true });

  const inputSize = (await fsp.stat(inputBinaryPath).catch(() => ({ size: 0 }))).size || binaryBytes.length;

  console.log(`format: v2`);
  console.log(`entries: ${outModules.length}`);
  console.log(`unique binaries: ${finalSpans.size} (was ${spanToEntries.size})`);
  console.log(`already merged groups: ${alreadyMerged.length}`);
  console.log(`new merged groups: ${mergedBatches.length}`);
  console.log(`fallback singletons: ${fallbackSingletons.length}`);
  console.log(`const pools: ${outConstPools.length}`);
  console.log(`binary bytes: ${binaryBytes.length}`);
  console.log(`index bytes: ${newIndexBytes.length}`);
  console.log(`instantiations: ${finalSpans.size} (was ${spanToEntries.size})`);
  console.log(`manifest: ${outManifestPath}`);
  console.log(`binary: ${outBinaryPath}`);
  console.log(`index: ${outIndexPath}`);
}

main().catch((err) => {
  console.error(`FAIL: ${err.message}`);
  if (err.stack) console.error(err.stack);
  process.exit(1);
});
