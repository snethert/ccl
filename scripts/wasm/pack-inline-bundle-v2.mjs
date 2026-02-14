#!/usr/bin/env node

import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";

import {
  encodeModuleBundleIndexV2,
  MODULE_BUNDLE_V2_DEFAULT_TEMPLATE_PREFIX,
  MODULE_BUNDLE_V2_FORMAT,
  MODULE_BUNDLE_V2_VERSION,
} from "../../doc/wasm/js/module-bundle-v2.mjs";
import {
  normalizeStartupBindingMapArtifact,
  summarizeStartupBindingMapArtifact,
} from "../../doc/wasm/js/startup-binding-map.mjs";

function usage() {
  console.log("Usage:");
  console.log("  node scripts/wasm/pack-inline-bundle-v2.mjs --manifest PATH [--out-manifest PATH] [--out-binary PATH] [--out-index PATH]");
  console.log("  node scripts/wasm/pack-inline-bundle-v2.mjs --manifest PATH --in-place");
}

function parseArgs(argv) {
  const opts = {
    manifest: null,
    outManifest: null,
    outBinary: null,
    outIndex: null,
    inPlace: false,
    templatePrefix: MODULE_BUNDLE_V2_DEFAULT_TEMPLATE_PREFIX,
  };

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--manifest") {
      opts.manifest = argv[++i] ?? null;
      continue;
    }
    if (arg === "--out-manifest") {
      opts.outManifest = argv[++i] ?? null;
      continue;
    }
    if (arg === "--out-binary") {
      opts.outBinary = argv[++i] ?? null;
      continue;
    }
    if (arg === "--out-index") {
      opts.outIndex = argv[++i] ?? null;
      continue;
    }
    if (arg === "--template-prefix") {
      opts.templatePrefix = argv[++i] ?? "";
      continue;
    }
    if (arg === "--in-place") {
      opts.inPlace = true;
      continue;
    }
    if (arg === "-h" || arg === "--help") {
      usage();
      process.exit(0);
    }
    throw new Error(`Unknown argument: ${arg}`);
  }

  if (!opts.manifest) throw new Error("Missing required --manifest PATH");
  if (opts.inPlace && (opts.outManifest || opts.outBinary || opts.outIndex)) {
    throw new Error("--in-place cannot be combined with --out-manifest, --out-binary, or --out-index");
  }
  if (!opts.templatePrefix) opts.templatePrefix = MODULE_BUNDLE_V2_DEFAULT_TEMPLATE_PREFIX;
  return opts;
}

function toPosixPath(p) {
  return p.split(path.sep).join(path.posix.sep);
}

function asBuffer(bytes, fieldName) {
  if (bytes instanceof Uint8Array) return Buffer.from(bytes);
  if (Array.isArray(bytes)) return Buffer.from(bytes);
  throw new Error(`${fieldName} must be a byte array`);
}

function normalizeGcRootPolicyModes(raw) {
  const out = new Map();
  if (!raw || typeof raw !== "object") return out;
  for (const [key, value] of Object.entries(raw)) {
    const entryIndex = Number.parseInt(String(key), 10);
    if (!Number.isFinite(entryIndex) || entryIndex < 0) continue;
    if (!Number.isFinite(value) || value < 0) continue;
    out.set(entryIndex >>> 0, value >>> 0);
  }
  return out;
}

function normalizeGcRootBoundaryOpsList(rawOps) {
  if (!Array.isArray(rawOps)) return [];
  const out = [];
  const seen = new Set();
  for (const op of rawOps) {
    if (typeof op !== "string") continue;
    if (op.length === 0 || seen.has(op)) continue;
    seen.add(op);
    out.push(op);
  }
  return out;
}

function normalizeGcRootBoundaryOps(raw) {
  const out = new Map();
  if (!raw || typeof raw !== "object") return out;
  for (const [key, value] of Object.entries(raw)) {
    const entryIndex = Number.parseInt(String(key), 10);
    if (!Number.isFinite(entryIndex) || entryIndex < 0) continue;
    const ops = normalizeGcRootBoundaryOpsList(value);
    if (ops.length === 0) continue;
    out.set(entryIndex >>> 0, ops);
  }
  return out;
}

function readSpan(fd, offset, length, fieldName) {
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
  if (total !== size) {
    throw new Error(`short read for ${fieldName}: expected ${size}, got ${total}`);
  }
  return out;
}

function defaultBundleSibling(outManifestPath, ext) {
  const parsed = path.parse(outManifestPath);
  return path.join(parsed.dir, `${parsed.name}${ext}`);
}

function deriveOutputPaths(opts, manifestPath) {
  if (opts.inPlace) {
    const parsed = path.parse(manifestPath);
    return {
      manifestPath,
      binaryPath: path.join(parsed.dir, `${parsed.name}.bin`),
      indexPath: path.join(parsed.dir, `${parsed.name}.idx`),
    };
  }

  const outManifest = path.resolve(opts.outManifest ?? manifestPath);
  const outBinary = path.resolve(opts.outBinary ?? defaultBundleSibling(outManifest, ".bin"));
  const outIndex = path.resolve(opts.outIndex ?? defaultBundleSibling(outManifest, ".idx"));
  return {
    manifestPath: outManifest,
    binaryPath: outBinary,
    indexPath: outIndex,
  };
}

async function writeFileAtomically(filePath, bytes) {
  await fsp.mkdir(path.dirname(filePath), { recursive: true });
  const tmp = `${filePath}.tmp`;
  await fsp.writeFile(tmp, bytes);
  await fsp.rename(tmp, filePath);
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  const inputManifestPath = path.resolve(opts.manifest);
  const inputManifestDir = path.dirname(inputManifestPath);
  const manifest = JSON.parse(await fsp.readFile(inputManifestPath, "utf8"));

  if (!Array.isArray(manifest?.modules)) {
    throw new Error("Input manifest must contain a top-level modules array of inline modules");
  }

  const output = deriveOutputPaths(opts, inputManifestPath);
  const outputManifestDir = path.dirname(output.manifestPath);
  const chunks = [];
  const outModules = [];
  const outConstPools = [];
  const constPoolIdBySig = new Map();
  const gcRootPolicyModes = normalizeGcRootPolicyModes(manifest?.gcRootPolicyModes);
  const gcRootBoundaryOps = normalizeGcRootBoundaryOps(manifest?.gcRootBoundaryOps);
  let offset = 0;
  let inputBinaryFd = null;

  const needsBinaryInput = manifest.modules.some((entry) => {
    if (entry?.moduleBytes == null) return true;
    if (entry?.constPoolBytes != null) return false;
    return Number.isFinite(entry?.constPoolOffset) && Number.isFinite(entry?.constPoolLength)
      && ((entry.constPoolLength >>> 0) > 0);
  });

  const inputBinaryPath = needsBinaryInput
    ? path.resolve(inputManifestDir, manifest?.binary ?? "")
    : null;
  if (needsBinaryInput) {
    if (!manifest?.binary || typeof manifest.binary !== "string") {
      throw new Error('Input manifest with offset-based modules must provide top-level "binary"');
    }
    if (!fs.existsSync(inputBinaryPath)) {
      throw new Error(`Missing input binary: ${inputBinaryPath}`);
    }
    inputBinaryFd = fs.openSync(inputBinaryPath, "r");
  }

  try {
    for (const entry of manifest.modules) {
      const entryIndex = entry?.entryIndex >>> 0;
      if (!Number.isFinite(entry?.entryIndex)) {
        throw new Error("module entry missing numeric entryIndex");
      }
      if (typeof entry?.exportName !== "string" || entry.exportName.length === 0) {
        throw new Error(`module ${entryIndex} missing exportName`);
      }

      let moduleBytes;
      if (entry?.moduleBytes != null) {
        moduleBytes = asBuffer(entry.moduleBytes, `module ${entryIndex} moduleBytes`);
      } else {
        if (!inputBinaryFd) {
          throw new Error(`module ${entryIndex} missing moduleBytes and no input binary is open`);
        }
        if (!Number.isFinite(entry?.offset) || !Number.isFinite(entry?.length)) {
          throw new Error(`module ${entryIndex} missing offset/length for binary span`);
        }
        moduleBytes = readSpan(
          inputBinaryFd,
          entry.offset >>> 0,
          entry.length >>> 0,
          `module ${entryIndex} module span`,
        );
      }
      if (moduleBytes.length === 0) {
        throw new Error(`module ${entryIndex} has empty moduleBytes`);
      }

      const gcMode = Number.isFinite(entry?.gcRootPolicyMode)
        ? (entry.gcRootPolicyMode >>> 0)
        : gcRootPolicyModes.get(entryIndex);
      if (gcMode != null) {
        gcRootPolicyModes.set(entryIndex, gcMode >>> 0);
      }
      const boundaryOps = normalizeGcRootBoundaryOpsList(entry?.gcRootBoundaryOps);
      if (boundaryOps.length > 0) {
        gcRootBoundaryOps.set(entryIndex, boundaryOps);
      }

      const moduleRecord = {
        exportName: entry.exportName,
        entryIndex,
        moduleVersion: Number.isFinite(entry?.moduleVersion) ? (entry.moduleVersion >>> 0) : 1,
        offset,
        length: moduleBytes.length >>> 0,
      };
      chunks.push(moduleBytes);
      offset += moduleBytes.length;

      let constPoolBytes = null;
      if (entry?.constPoolBytes != null) {
        constPoolBytes = asBuffer(entry.constPoolBytes, `module ${entryIndex} constPoolBytes`);
      } else if (Number.isFinite(entry?.constPoolOffset) && Number.isFinite(entry?.constPoolLength)
          && ((entry.constPoolLength >>> 0) > 0)) {
        if (!inputBinaryFd) {
          throw new Error(`module ${entryIndex} const pool span requires input binary`);
        }
        constPoolBytes = readSpan(
          inputBinaryFd,
          entry.constPoolOffset >>> 0,
          entry.constPoolLength >>> 0,
          `module ${entryIndex} const pool span`,
        );
      }

      if (constPoolBytes && constPoolBytes.length > 0) {
        const hash = crypto.createHash("sha256").update(constPoolBytes).digest("hex");
        const sig = `${constPoolBytes.length}:${hash}`;
        let constPoolId = constPoolIdBySig.get(sig);
        if (constPoolId == null) {
          constPoolId = outConstPools.length;
          constPoolIdBySig.set(sig, constPoolId);
          outConstPools.push({
            id: constPoolId,
            offset,
            length: constPoolBytes.length >>> 0,
          });
          chunks.push(constPoolBytes);
          offset += constPoolBytes.length;
        }
        moduleRecord.constPoolId = constPoolId;
      }

      outModules.push(moduleRecord);
    }
  } finally {
    if (inputBinaryFd != null) {
      fs.closeSync(inputBinaryFd);
    }
  }

  const binaryBytes = Buffer.concat(chunks);
  const indexBytes = encodeModuleBundleIndexV2({
    modules: outModules,
    constPools: outConstPools,
    templatePrefix: opts.templatePrefix,
  });

  const outManifest = {
    format: MODULE_BUNDLE_V2_FORMAT,
    version: MODULE_BUNDLE_V2_VERSION,
    binary: toPosixPath(path.relative(outputManifestDir, output.binaryPath)),
    index: toPosixPath(path.relative(outputManifestDir, output.indexPath)),
    exportNameTemplatePrefix: opts.templatePrefix,
    moduleCount: outModules.length,
    constPoolCount: outConstPools.length,
    functions: Array.isArray(manifest?.functions) ? manifest.functions : [],
  };
  let startupBindingMap = normalizeStartupBindingMapArtifact(manifest?.startupBindingMap ?? null);
  if (!startupBindingMap) {
    throw new Error("Manifest missing startupBindingMap artifact; source-scope startup map is required at pack time");
  }
  outManifest.startupBindingMap = startupBindingMap;
  if (gcRootPolicyModes.size > 0) {
    outManifest.gcRootPolicyModes = Object.fromEntries(
      [...gcRootPolicyModes.entries()]
        .sort((a, b) => ((a[0] >>> 0) - (b[0] >>> 0)))
        .map(([entryIndex, mode]) => [String(entryIndex >>> 0), mode >>> 0]),
    );
  }
  if (gcRootBoundaryOps.size > 0) {
    outManifest.gcRootBoundaryOps = Object.fromEntries(
      [...gcRootBoundaryOps.entries()]
        .sort((a, b) => ((a[0] >>> 0) - (b[0] >>> 0)))
        .map(([entryIndex, ops]) => [String(entryIndex >>> 0), ops]),
    );
  }

  await writeFileAtomically(output.binaryPath, binaryBytes);
  await writeFileAtomically(output.indexPath, indexBytes);
  await writeFileAtomically(output.manifestPath, `${JSON.stringify(outManifest)}\n`);

  const startupCounts = summarizeStartupBindingMapArtifact(startupBindingMap);
  console.log(`modules: ${outModules.length}`);
  console.log(`const pools: ${outConstPools.length}`);
  console.log(
    "startup binding map:" +
    ` total=${startupCounts.total_entries}` +
    ` literal=${startupCounts.literal_entries}` +
    ` entry-backed=${startupCounts.entry_backed_entries}` +
    ` deferred=${startupCounts.deferred_entries}` +
    ` unsupported=${startupCounts.unsupported_entries}`,
  );
  console.log(`binary bytes: ${binaryBytes.length}`);
  console.log(`index bytes: ${indexBytes.length}`);
  console.log(`manifest: ${output.manifestPath}`);
  console.log(`binary: ${output.binaryPath}`);
  console.log(`index: ${output.indexPath}`);
}

main().catch((err) => {
  console.error(`FAIL: ${err.message}`);
  process.exit(1);
});
