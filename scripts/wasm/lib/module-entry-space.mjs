import fs from "node:fs/promises";
import path from "node:path";

import { resolveBundleEntries } from "./ccl-loader.mjs";

function toEntryIndex(value) {
  return Number.isFinite(value) ? (value >>> 0) : null;
}

function nameMapForBundle(bundle, resolved) {
  const out = new Map();
  for (const fn of Array.isArray(bundle?.functions) ? bundle.functions : []) {
    const idx = toEntryIndex(fn?.entryIndex);
    if (idx == null) continue;
    const name = typeof fn?.name === "string" && fn.name.length > 0
      ? fn.name
      : (typeof fn?.exportName === "string" && fn.exportName.length > 0 ? fn.exportName : null);
    if (name && !out.has(idx)) out.set(idx, name);
  }
  for (const mod of Array.isArray(resolved?.modules) ? resolved.modules : []) {
    const idx = toEntryIndex(mod?.entryIndex);
    if (idx == null || out.has(idx)) continue;
    const name = typeof mod?.exportName === "string" && mod.exportName.length > 0
      ? mod.exportName
      : null;
    if (name) out.set(idx, name);
  }
  return out;
}

function buildEntryIndexSet(resolved) {
  const out = new Set();
  for (const mod of Array.isArray(resolved?.modules) ? resolved.modules : []) {
    const idx = toEntryIndex(mod?.entryIndex);
    if (idx != null) out.add(idx);
  }
  return out;
}

function moduleMapForResolved(resolved) {
  const out = new Map();
  for (const mod of Array.isArray(resolved?.modules) ? resolved.modules : []) {
    const idx = toEntryIndex(mod?.entryIndex);
    if (idx != null && !out.has(idx)) out.set(idx, mod);
  }
  return out;
}

function maxEntryIndex(resolved) {
  let max = 0;
  for (const mod of Array.isArray(resolved?.modules) ? resolved.modules : []) {
    const idx = toEntryIndex(mod?.entryIndex);
    if (idx != null && idx > max) max = idx;
  }
  return max;
}

export async function loadBundleEntrySpaceFromManifest(manifestPath) {
  const absolutePath = path.resolve(manifestPath);
  const bundle = JSON.parse(await fs.readFile(absolutePath, "utf-8"));
  let indexBytes = null;
  if (typeof bundle?.index === "string" && bundle.index.length > 0) {
    const indexPath = path.join(path.dirname(absolutePath), bundle.index);
    indexBytes = await fs.readFile(indexPath);
  }
  const resolved = await resolveBundleEntries({ bundle, indexBytes });
  return entrySpaceFromBundle(bundle, resolved, {
    path: absolutePath,
    indexBytes,
  });
}

export function entrySpaceFromBundle(bundle, resolved, extra = {}) {
  return {
    ...extra,
    bundle,
    resolved,
    entryIndices: buildEntryIndexSet(resolved),
    entryNames: nameMapForBundle(bundle, resolved),
    moduleMap: moduleMapForResolved(resolved),
    maxEntryIndex: maxEntryIndex(resolved),
    binaryPath: typeof bundle?.binary === "string" && extra?.path
      ? path.join(path.dirname(path.resolve(extra.path)), bundle.binary)
      : null,
  };
}

export function computeNextEntryIndex(entrySpace, sidecarValue = null) {
  const bundleNext = ((entrySpace?.maxEntryIndex ?? 0) >>> 0) + 1;
  const sidecarNext = Number.isFinite(sidecarValue) && sidecarValue > 0
    ? (sidecarValue >>> 0)
    : 0;
  return Math.max(bundleNext, sidecarNext) >>> 0;
}

function moduleDescriptor(moduleEntry) {
  if (!moduleEntry) return null;
  return JSON.stringify({
    exportName: moduleEntry.exportName ?? null,
    moduleVersion: toEntryIndex(moduleEntry.moduleVersion),
    length: toEntryIndex(moduleEntry.length),
    storedLength: toEntryIndex(moduleEntry.moduleStoredLength ?? moduleEntry.length),
    moduleEncoding: moduleEntry.moduleEncoding ?? null,
    constPoolLength: toEntryIndex(moduleEntry.constPoolLength),
    constPoolStoredLength: toEntryIndex(moduleEntry.constPoolStoredLength ?? moduleEntry.constPoolLength),
    constPoolEncoding: moduleEntry.constPoolEncoding ?? null,
  });
}

async function readModuleBytes(entrySpace, moduleEntry) {
  const binaryPath = entrySpace?.binaryPath;
  if (!binaryPath || !moduleEntry) return null;
  const offset = toEntryIndex(moduleEntry.offset);
  const storedLength = toEntryIndex(moduleEntry.moduleStoredLength ?? moduleEntry.length);
  if (offset == null || storedLength == null || storedLength === 0) return null;
  const fh = await fs.open(binaryPath, "r");
  try {
    const buffer = Buffer.allocUnsafe(storedLength);
    let total = 0;
    while (total < storedLength) {
      const { bytesRead } = await fh.read(buffer, total, storedLength - total, offset + total);
      if (bytesRead === 0) break;
      total += bytesRead;
    }
    if (total !== storedLength) {
      throw new Error(`short read from ${binaryPath}: expected ${storedLength}, got ${total}`);
    }
    return buffer;
  } finally {
    await fh.close();
  }
}

async function modulesSharePayload(lhs, rhs, entryIndex) {
  const lhsModule = lhs?.moduleMap?.get(entryIndex) ?? null;
  const rhsModule = rhs?.moduleMap?.get(entryIndex) ?? null;
  if (!lhsModule || !rhsModule) return false;
  if (moduleDescriptor(lhsModule) !== moduleDescriptor(rhsModule)) return false;
  const [lhsBytes, rhsBytes] = await Promise.all([
    readModuleBytes(lhs, lhsModule),
    readModuleBytes(rhs, rhsModule),
  ]);
  if (lhsBytes == null || rhsBytes == null) return true;
  return Buffer.compare(lhsBytes, rhsBytes) === 0;
}

export async function findEntrySpaceConflicts(
  lhs,
  rhs,
  sampleLimit = 8,
  { excludeRhsEntries = null } = {},
) {
  const conflicts = [];
  const lhsEntries = lhs?.entryIndices instanceof Set ? lhs.entryIndices : new Set();
  const rhsEntries = rhs?.entryIndices instanceof Set ? rhs.entryIndices : new Set();
  const excluded = excludeRhsEntries instanceof Set
    ? excludeRhsEntries
    : new Set(Array.isArray(excludeRhsEntries) ? excludeRhsEntries : []);
  for (const idx of rhsEntries) {
    if (excluded.has(idx)) continue;
    if (!lhsEntries.has(idx)) continue;
    if (await modulesSharePayload(lhs, rhs, idx)) continue;
    conflicts.push({
      entryIndex: idx >>> 0,
      lhsName: lhs?.entryNames?.get(idx) ?? null,
      rhsName: rhs?.entryNames?.get(idx) ?? null,
    });
  }
  conflicts.sort((a, b) => a.entryIndex - b.entryIndex);
  return {
    total: conflicts.length,
    conflicts,
    samples: conflicts.slice(0, Math.max(1, sampleLimit >>> 0)),
  };
}

export function formatEntrySpaceConflictSummary(conflictInfo, lhsLabel = "boot", rhsLabel = "runtime") {
  const total = conflictInfo?.total ?? 0;
  const samples = Array.isArray(conflictInfo?.samples) ? conflictInfo.samples : [];
  if (total === 0) {
    return `${lhsLabel}/${rhsLabel} entry spaces are disjoint`;
  }
  const sampleText = samples.map((item) => {
    const lhsName = item?.lhsName ?? "?";
    const rhsName = item?.rhsName ?? "?";
    return `${item.entryIndex}: ${lhsLabel}=${lhsName}, ${rhsLabel}=${rhsName}`;
  }).join("; ");
  return `${total} overlapping entry indices (${sampleText})`;
}

function usage() {
  console.error("Usage:");
  console.error("  node module-entry-space.mjs next-entry-index --boot-manifest PATH [--sidecar PATH]");
  console.error("  node module-entry-space.mjs assert-disjoint --boot-manifest PATH --runtime-manifest PATH");
}

function parseArgs(argv) {
  const out = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    switch (arg) {
      case "--boot-manifest":
        out.bootManifest = argv[++i];
        break;
      case "--runtime-manifest":
        out.runtimeManifest = argv[++i];
        break;
      case "--sidecar":
        out.sidecar = argv[++i];
        break;
      default:
        out._.push(arg);
        break;
    }
  }
  return out;
}

async function readSidecarValue(sidecarPath) {
  if (!sidecarPath) return null;
  const raw = (await fs.readFile(sidecarPath, "utf-8")).trim();
  if (!raw) return null;
  const parsed = Number.parseInt(raw, 10);
  return Number.isFinite(parsed) ? parsed : null;
}

async function main(argv) {
  const args = parseArgs(argv);
  const command = args._[0] ?? "";
  switch (command) {
    case "next-entry-index": {
      if (!args.bootManifest) {
        usage();
        process.exit(2);
      }
      const entrySpace = await loadBundleEntrySpaceFromManifest(args.bootManifest);
      const sidecarValue = await readSidecarValue(args.sidecar);
      console.log(computeNextEntryIndex(entrySpace, sidecarValue));
      return;
    }
    case "assert-disjoint": {
      if (!args.bootManifest || !args.runtimeManifest) {
        usage();
        process.exit(2);
      }
      const [bootEntrySpace, runtimeEntrySpace] = await Promise.all([
        loadBundleEntrySpaceFromManifest(args.bootManifest),
        loadBundleEntrySpaceFromManifest(args.runtimeManifest),
      ]);
      const conflicts = await findEntrySpaceConflicts(
        bootEntrySpace,
        runtimeEntrySpace,
        8,
        { excludeRhsEntries: bootEntrySpace.entryIndices },
      );
      if (conflicts.total > 0) {
        console.error(formatEntrySpaceConflictSummary(conflicts, "boot", "runtime"));
        process.exit(1);
      }
      console.log("ok");
      return;
    }
    default:
      usage();
      process.exit(2);
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main(process.argv.slice(2)).catch((error) => {
    console.error(error?.stack || String(error));
    process.exit(1);
  });
}
