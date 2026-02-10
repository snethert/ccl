#!/usr/bin/env node

import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";
import * as zlib from "node:zlib";

import {
  decodeModuleBundleIndexV2,
  encodeModuleBundleIndexV2,
  MODULE_BUNDLE_V2_DEFAULT_TEMPLATE_PREFIX,
  MODULE_BUNDLE_V2_FORMAT,
  MODULE_BUNDLE_V2_VERSION,
} from "../../doc/wasm/js/module-bundle-v2.mjs";

function usage() {
  console.log("Usage:");
  console.log("  node scripts/wasm/compact-runtime-modules.mjs --manifest PATH [--out-manifest PATH] [--out-binary PATH] [--out-index PATH]");
  console.log("  node scripts/wasm/compact-runtime-modules.mjs --manifest PATH --in-place");
  console.log("  node scripts/wasm/compact-runtime-modules.mjs --manifest PATH --in-place --compress-const-pools --compress-modules");
  console.log("  node scripts/wasm/compact-runtime-modules.mjs --manifest PATH --in-place --const-pool-encoding br --module-encoding gzip --brotli-quality 7");
  console.log("  node scripts/wasm/compact-runtime-modules.mjs --manifest PATH --in-place --const-pool-shared-blob --const-pool-shared-blob-encoding br");
  console.log("  node scripts/wasm/compact-runtime-modules.mjs --manifest PATH --in-place --strip-functions");
}

function parseArgs(argv) {
  const opts = {
    manifest: null,
    outManifest: null,
    outBinary: null,
    outIndex: null,
    inPlace: false,
    constPoolEncoding: null,
    moduleEncoding: null,
    brotliQuality: 5,
    constPoolDelta: true,
    constPoolDeltaMinBytes: 262144,
    constPoolSharedBlob: false,
    constPoolSharedBlobEncoding: null,
    stripFunctions: false,
    format: "v2",
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
    if (arg === "--in-place") {
      opts.inPlace = true;
      continue;
    }
    if (arg === "--compress-const-pools") {
      if (!opts.constPoolEncoding) opts.constPoolEncoding = "gzip";
      continue;
    }
    if (arg === "--no-compress-const-pools") {
      opts.constPoolEncoding = null;
      continue;
    }
    if (arg === "--const-pool-encoding") {
      opts.constPoolEncoding = normalizeEncoding(argv[++i] ?? null, "--const-pool-encoding");
      continue;
    }
    if (arg === "--compress-modules") {
      if (!opts.moduleEncoding) opts.moduleEncoding = "gzip";
      continue;
    }
    if (arg === "--no-compress-modules") {
      opts.moduleEncoding = null;
      continue;
    }
    if (arg === "--module-encoding") {
      opts.moduleEncoding = normalizeEncoding(argv[++i] ?? null, "--module-encoding");
      continue;
    }
    if (arg === "--brotli-quality") {
      const value = Number.parseInt(argv[++i] ?? "", 10);
      if (!Number.isInteger(value) || value < 0 || value > 11) {
        throw new Error("--brotli-quality must be an integer in [0,11]");
      }
      opts.brotliQuality = value;
      continue;
    }
    if (arg === "--const-pool-delta") {
      opts.constPoolDelta = true;
      continue;
    }
    if (arg === "--no-const-pool-delta") {
      opts.constPoolDelta = false;
      continue;
    }
    if (arg === "--const-pool-delta-min-bytes") {
      const value = Number.parseInt(argv[++i] ?? "", 10);
      if (!Number.isInteger(value) || value < 0) {
        throw new Error("--const-pool-delta-min-bytes must be a non-negative integer");
      }
      opts.constPoolDeltaMinBytes = value;
      continue;
    }
    if (arg === "--const-pool-shared-blob") {
      opts.constPoolSharedBlob = true;
      continue;
    }
    if (arg === "--no-const-pool-shared-blob") {
      opts.constPoolSharedBlob = false;
      continue;
    }
    if (arg === "--const-pool-shared-blob-encoding") {
      opts.constPoolSharedBlobEncoding = normalizeEncoding(argv[++i] ?? null, "--const-pool-shared-blob-encoding");
      continue;
    }
    if (arg === "--strip-functions") {
      opts.stripFunctions = true;
      continue;
    }
    if (arg === "--keep-functions") {
      opts.stripFunctions = false;
      continue;
    }
    if (arg === "--format") {
      opts.format = String(argv[++i] ?? "").toLowerCase();
      continue;
    }
    if (arg === "--template-prefix") {
      opts.templatePrefix = argv[++i] ?? "";
      continue;
    }
    if (arg === "-h" || arg === "--help") {
      usage();
      process.exit(0);
    }
    throw new Error(`Unknown argument: ${arg}`);
  }

  if (!opts.manifest) {
    throw new Error("Missing required --manifest PATH");
  }
  if (opts.inPlace && (opts.outManifest || opts.outBinary || opts.outIndex)) {
    throw new Error("--in-place cannot be combined with --out-manifest, --out-binary, or --out-index");
  }
  if (opts.format !== "v2") {
    throw new Error("Only --format v2 is currently supported");
  }
  if (opts.templatePrefix.length === 0) {
    opts.templatePrefix = MODULE_BUNDLE_V2_DEFAULT_TEMPLATE_PREFIX;
  }
  if (opts.constPoolSharedBlob && !opts.constPoolSharedBlobEncoding) {
    opts.constPoolSharedBlobEncoding = opts.constPoolEncoding ?? "gzip";
  }
  const brotliUsed =
    opts.constPoolEncoding === "br" ||
    opts.moduleEncoding === "br" ||
    opts.constPoolSharedBlobEncoding === "br";
  if (!brotliUsed && opts.brotliQuality !== 5) {
    throw new Error("--brotli-quality is only valid with --const-pool-encoding br, --module-encoding br, or --const-pool-shared-blob-encoding br");
  }
  return opts;
}

function normalizeEncoding(value, flagName) {
  if (value == null || value === "" || value === "raw" || value === "none") return null;
  const normalized = String(value).toLowerCase();
  if (normalized === "gzip" || normalized === "gz") return "gzip";
  if (normalized === "br" || normalized === "brotli") return "br";
  if (normalized === "deflate") return "deflate";
  if (normalized === "deflate-raw") return "deflate-raw";
  throw new Error(`${flagName} must be one of: raw, gzip, br, deflate, deflate-raw`);
}

function normalizeBinaryPath(manifestDir, binaryField) {
  if (typeof binaryField !== "string" || binaryField.length === 0) {
    throw new Error('Bundle manifest missing non-empty "binary" field');
  }
  return path.resolve(manifestDir, binaryField);
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

function defaultIndexPathFromBinary(binaryPath) {
  const parsed = path.parse(binaryPath);
  return path.join(parsed.dir, `${parsed.name}.idx`);
}

function resolveInputIndexPath(manifestDir, manifest, inputBinaryPath) {
  if (typeof manifest?.index === "string" && manifest.index.length > 0) {
    return path.resolve(manifestDir, manifest.index);
  }
  return defaultIndexPathFromBinary(inputBinaryPath);
}

function deriveOutputPaths(opts, manifestPath, manifest, inputBinaryPath) {
  if (opts.inPlace) {
    const inputIndexPath = resolveInputIndexPath(path.dirname(manifestPath), manifest, inputBinaryPath);
    return {
      finalManifestPath: manifestPath,
      finalBinaryPath: inputBinaryPath,
      finalIndexPath: inputIndexPath,
      tempManifestPath: `${manifestPath}.tmp`,
      tempBinaryPath: `${inputBinaryPath}.tmp`,
      tempIndexPath: `${inputIndexPath}.tmp`,
    };
  }

  const manifestDir = path.dirname(manifestPath);
  const manifestBase = path.basename(manifestPath, path.extname(manifestPath));
  const outManifestPath = path.resolve(
    opts.outManifest ? opts.outManifest : path.join(manifestDir, `${manifestBase}.compact.json`),
  );
  const outManifestDir = path.dirname(outManifestPath);

  const inBinBase = path.basename(manifest.binary, path.extname(manifest.binary));
  const outBinaryPath = path.resolve(
    opts.outBinary ? opts.outBinary : path.join(outManifestDir, `${inBinBase}.compact.bin`),
  );
  const outIndexPath = path.resolve(
    opts.outIndex ? opts.outIndex : path.join(outManifestDir, `${inBinBase}.compact.idx`),
  );

  return {
    finalManifestPath: outManifestPath,
    finalBinaryPath: outBinaryPath,
    finalIndexPath: outIndexPath,
    tempManifestPath: outManifestPath,
    tempBinaryPath: outBinaryPath,
    tempIndexPath: outIndexPath,
  };
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
  if (total !== size) {
    throw new Error(`short read: expected ${size}, got ${total} at offset ${start}`);
  }
  return out;
}

function writeSpan(fd, bytes, offset) {
  let total = 0;
  while (total < bytes.length) {
    const n = fs.writeSync(fd, bytes, total, bytes.length - total, offset + total);
    if (n === 0) throw new Error("short write");
    total += n;
  }
}

function encodeBytes(bytes, encoding, opts) {
  if (!encoding) {
    return { bytes, encoding: null };
  }
  switch (encoding) {
    case "gzip": {
      const encoded = zlib.gzipSync(bytes);
      return encoded.length < bytes.length
        ? { bytes: encoded, encoding: "gzip" }
        : { bytes, encoding: null };
    }
    case "br": {
      const encoded = zlib.brotliCompressSync(bytes, {
        params: { [zlib.constants.BROTLI_PARAM_QUALITY]: opts.brotliQuality },
      });
      return encoded.length < bytes.length
        ? { bytes: encoded, encoding: "br" }
        : { bytes, encoding: null };
    }
    case "deflate": {
      const encoded = zlib.deflateSync(bytes);
      return encoded.length < bytes.length
        ? { bytes: encoded, encoding: "deflate" }
        : { bytes, encoding: null };
    }
    case "deflate-raw": {
      const encoded = zlib.deflateRawSync(bytes);
      return encoded.length < bytes.length
        ? { bytes: encoded, encoding: "deflate-raw" }
        : { bytes, encoding: null };
    }
    default:
      throw new Error(`unsupported encoding: ${encoding}`);
  }
}

function decodeBytes(bytes, encoding, expectedLength) {
  if (!encoding) {
    if (Number.isFinite(expectedLength) && bytes.length !== (expectedLength >>> 0)) {
      throw new Error(`decoded length mismatch: expected ${expectedLength >>> 0}, got ${bytes.length}`);
    }
    return bytes;
  }
  let decoded;
  switch (encoding) {
    case "gzip":
      decoded = zlib.gunzipSync(bytes);
      break;
    case "br":
      decoded = zlib.brotliDecompressSync(bytes);
      break;
    case "deflate":
      decoded = zlib.inflateSync(bytes);
      break;
    case "deflate-raw":
      decoded = zlib.inflateRawSync(bytes);
      break;
    default:
      throw new Error(`unsupported encoding: ${encoding}`);
  }
  if (Number.isFinite(expectedLength) && decoded.length !== (expectedLength >>> 0)) {
    throw new Error(`decoded length mismatch: expected ${expectedLength >>> 0}, got ${decoded.length}`);
  }
  return decoded;
}

function toPosixPath(p) {
  return p.split(path.sep).join(path.posix.sep);
}

function resolveConstPoolSharedBlobInfo(manifest) {
  if (!Number.isFinite(manifest?.constPoolBlobOffset) || !Number.isFinite(manifest?.constPoolBlobLength)) {
    return null;
  }
  const offset = manifest.constPoolBlobOffset >>> 0;
  const length = manifest.constPoolBlobLength >>> 0;
  const storedLength = Number.isFinite(manifest?.constPoolBlobStoredLength)
    ? (manifest.constPoolBlobStoredLength >>> 0)
    : length;
  const encoding = normalizeEncoding(manifest?.constPoolBlobEncoding ?? null, "const pool shared blob encoding");
  return {
    offset,
    length,
    storedLength,
    encoding,
  };
}

function readSourceModules(manifest, manifestDir, inputBinaryPath) {
  if (manifest?.format !== MODULE_BUNDLE_V2_FORMAT) {
    throw new Error(`Unsupported bundle format: expected ${MODULE_BUNDLE_V2_FORMAT}`);
  }
  const indexPath = resolveInputIndexPath(manifestDir, manifest, inputBinaryPath);
  if (!fs.existsSync(indexPath)) {
    throw new Error(`Missing module index: ${indexPath}`);
  }
  const indexBytes = fs.readFileSync(indexPath);
  const templatePrefix =
    typeof manifest?.exportNameTemplatePrefix === "string" && manifest.exportNameTemplatePrefix.length > 0
      ? manifest.exportNameTemplatePrefix
      : MODULE_BUNDLE_V2_DEFAULT_TEMPLATE_PREFIX;
  const decoded = decodeModuleBundleIndexV2(indexBytes, { templatePrefix });
  return decoded.modules;
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  const manifestPath = path.resolve(opts.manifest);
  const manifestDir = path.dirname(manifestPath);
  const manifest = JSON.parse(await fsp.readFile(manifestPath, "utf8"));
  const gcRootPolicyModes = normalizeGcRootPolicyModes(manifest?.gcRootPolicyModes);
  const gcRootBoundaryOps = normalizeGcRootBoundaryOps(manifest?.gcRootBoundaryOps);

  const inputBinaryPath = normalizeBinaryPath(manifestDir, manifest.binary);
  const modules = readSourceModules(manifest, manifestDir, inputBinaryPath);
  if (!Array.isArray(modules) || modules.length === 0) {
    throw new Error("Bundle contains no modules");
  }

  const inputSizeBefore = (await fsp.stat(inputBinaryPath)).size;
  const output = deriveOutputPaths(opts, manifestPath, manifest, inputBinaryPath);
  if (!opts.inPlace && output.finalBinaryPath === inputBinaryPath) {
    throw new Error("Refusing to overwrite input binary without --in-place");
  }

  await fsp.mkdir(path.dirname(output.tempBinaryPath), { recursive: true });
  await fsp.mkdir(path.dirname(output.tempManifestPath), { recursive: true });
  await fsp.mkdir(path.dirname(output.tempIndexPath), { recursive: true });

  const inFd = fs.openSync(inputBinaryPath, "r");
  const outFd = fs.openSync(output.tempBinaryPath, "w+");
  const inputConstPoolSharedBlob = resolveConstPoolSharedBlobInfo(manifest);
  let inputConstPoolSharedBlobRaw = null;

  const sourceConstPoolById = new Map();
  for (const entry of modules) {
    if (!Number.isFinite(entry?.constPoolId)) continue;
    const id = entry.constPoolId >>> 0;
    if (!Number.isFinite(entry?.constPoolOffset) || !Number.isFinite(entry?.constPoolLength)) continue;
    if (!sourceConstPoolById.has(id)) sourceConstPoolById.set(id, entry);
  }
  const sourceConstPoolRawCache = new Map();
  const sourceConstPoolDecodeInFlight = new Set();

  const outModules = [];
  const outConstPools = [];
  const constPoolIdBySig = new Map();
  const constPoolAnchorsByLength = new Map();
  const constPoolPayloadById = new Map();
  const useSharedConstPoolBlobOutput = opts.constPoolSharedBlob;
  const sharedConstPoolBlobEncoding = opts.constPoolSharedBlobEncoding ?? null;
  let sharedConstPoolBlobInfo = null;
  let sharedConstPoolRawLength = 0;

  let writeOffset = 0;
  let rawModuleBytes = 0;
  let storedModuleBytes = 0;
  let moduleCompressedCount = 0;
  let rawConstBytes = 0;
  let uniqueConstBytes = 0;
  let storedUniqueConstBytes = 0;
  let compressedUniqueConstPools = 0;
  let deltaConstPools = 0;
  let reusedConstPools = 0;

  if (inputConstPoolSharedBlob) {
    const stored = readSpan(inFd, inputConstPoolSharedBlob.offset, inputConstPoolSharedBlob.storedLength);
    inputConstPoolSharedBlobRaw = decodeBytes(
      stored,
      inputConstPoolSharedBlob.encoding,
      inputConstPoolSharedBlob.length,
    );
  }

  function decodeSourceConstPoolRaw(entry) {
    if (!entry) return null;
    if (!Number.isFinite(entry.constPoolOffset) || !Number.isFinite(entry.constPoolLength)) return null;

    const poolId = Number.isFinite(entry?.constPoolId) ? (entry.constPoolId >>> 0) : null;
    if (poolId != null && sourceConstPoolRawCache.has(poolId)) {
      return sourceConstPoolRawCache.get(poolId);
    }
    if (poolId != null) {
      if (sourceConstPoolDecodeInFlight.has(poolId)) {
        throw new Error(`const pool decode cycle at id ${poolId}`);
      }
      sourceConstPoolDecodeInFlight.add(poolId);
    }

    try {
      const rawLength = entry.constPoolLength >>> 0;
      let rawBytes;
      if (inputConstPoolSharedBlobRaw) {
        const start = entry.constPoolOffset >>> 0;
        const storedLength = Number.isFinite(entry.constPoolStoredLength)
          ? (entry.constPoolStoredLength >>> 0)
          : rawLength;
        const end = start + storedLength;
        if (end > inputConstPoolSharedBlobRaw.length) {
          throw new Error(`const pool span out of bounds in shared blob: ${start}+${storedLength}`);
        }
        const encoding = normalizeEncoding(entry.constPoolEncoding ?? null, "source const pool encoding");
        const slice = inputConstPoolSharedBlobRaw.subarray(start, end);
        rawBytes = decodeBytes(slice, encoding, rawLength);
      } else {
        const storedLength = Number.isFinite(entry.constPoolStoredLength)
          ? (entry.constPoolStoredLength >>> 0)
          : rawLength;
        const encoding = normalizeEncoding(entry.constPoolEncoding ?? null, "source const pool encoding");
        const storedBytes = readSpan(inFd, entry.constPoolOffset >>> 0, storedLength);
        rawBytes = decodeBytes(storedBytes, encoding, rawLength);
      }

      const baseId = Number.isFinite(entry?.constPoolDeltaBaseId)
        ? (entry.constPoolDeltaBaseId >>> 0)
        : null;
      if (baseId != null) {
        const deltaOp = entry?.constPoolDeltaOp ?? null;
        if (deltaOp !== "xor") {
          throw new Error(`unsupported const pool delta op: ${deltaOp ?? "<missing>"}`);
        }
        const baseEntry = sourceConstPoolById.get(baseId);
        if (!baseEntry) {
          throw new Error(`missing const pool delta base id: ${baseId}`);
        }
        const baseBytes = decodeSourceConstPoolRaw(baseEntry);
        if (!baseBytes || baseBytes.length !== rawBytes.length) {
          throw new Error(`const pool delta size mismatch for base ${baseId}`);
        }
        const out = Buffer.allocUnsafe(rawBytes.length);
        for (let i = 0; i < rawBytes.length; i++) {
          out[i] = rawBytes[i] ^ baseBytes[i];
        }
        rawBytes = out;
      }

      if (poolId != null) sourceConstPoolRawCache.set(poolId, rawBytes);
      return rawBytes;
    } finally {
      if (poolId != null) sourceConstPoolDecodeInFlight.delete(poolId);
    }
  }

  try {
    for (const entry of modules) {
      const outEntry = {
        exportName: entry.exportName,
        entryIndex: entry.entryIndex >>> 0,
        moduleVersion: Number.isFinite(entry.moduleVersion) ? (entry.moduleVersion >>> 0) : 1,
      };

      if (!Number.isFinite(entry.offset) || !Number.isFinite(entry.length)) {
        throw new Error(`module ${entry.exportName ?? "?"} missing offset/length`);
      }

      const moduleOffset = entry.offset >>> 0;
      const moduleLength = entry.length >>> 0;
      const moduleStoredLengthIn = Number.isFinite(entry.moduleStoredLength)
        ? (entry.moduleStoredLength >>> 0)
        : moduleLength;
      const moduleEncodingIn = normalizeEncoding(entry.moduleEncoding ?? null, "source module encoding");
      const moduleStoredIn = readSpan(inFd, moduleOffset, moduleStoredLengthIn);
      const moduleRawBytes = decodeBytes(moduleStoredIn, moduleEncodingIn, moduleLength);
      rawModuleBytes += moduleLength;

      let moduleOutBytes;
      let moduleOutEncoding;
      if (opts.moduleEncoding) {
        const encoded = encodeBytes(moduleRawBytes, opts.moduleEncoding, opts);
        moduleOutBytes = encoded.bytes;
        moduleOutEncoding = encoded.encoding;
      } else if (moduleEncodingIn) {
        moduleOutBytes = moduleStoredIn;
        moduleOutEncoding = moduleEncodingIn;
      } else {
        moduleOutBytes = moduleRawBytes;
        moduleOutEncoding = null;
      }

      const moduleOutStoredLength = moduleOutBytes.length >>> 0;
      storedModuleBytes += moduleOutStoredLength;
      if (moduleOutEncoding) moduleCompressedCount += 1;

      outEntry.offset = writeOffset;
      outEntry.length = moduleLength;
      if (moduleOutStoredLength !== moduleLength) {
        outEntry.moduleStoredLength = moduleOutStoredLength;
      }
      if (moduleOutEncoding) {
        outEntry.moduleEncoding = moduleOutEncoding;
      }

      writeSpan(outFd, moduleOutBytes, writeOffset);
      writeOffset += moduleOutStoredLength;

      const hasConstPool =
        Number.isFinite(entry.constPoolOffset) &&
        Number.isFinite(entry.constPoolLength) &&
        (entry.constPoolLength >>> 0) > 0;

      if (!hasConstPool) {
        outModules.push(outEntry);
        continue;
      }

      const constRawBytes = decodeSourceConstPoolRaw(entry);
      if (!constRawBytes) {
        throw new Error(`const pool decode failed for ${entry.exportName}`);
      }
      const constLength = constRawBytes.length >>> 0;
      rawConstBytes += constLength;

      const hash = crypto.createHash("sha256").update(constRawBytes).digest("hex");
      const sig = `${constLength}:${hash}`;
      let constPoolId = constPoolIdBySig.get(sig);
      if (constPoolId == null) {
        constPoolId = outConstPools.length;
        constPoolIdBySig.set(sig, constPoolId);

        const directEncoded = opts.constPoolEncoding
          ? encodeBytes(constRawBytes, opts.constPoolEncoding, opts)
          : { bytes: constRawBytes, encoding: null };

        let chosenBytes = directEncoded.bytes;
        let chosenEncoding = directEncoded.encoding;
        let chosenDeltaBaseId = null;
        let chosenDeltaOp = null;

        if (opts.constPoolDelta && constLength >= opts.constPoolDeltaMinBytes) {
          const anchor = constPoolAnchorsByLength.get(constLength);
          if (anchor?.raw) {
            const xorBytes = Buffer.allocUnsafe(constLength);
            for (let i = 0; i < constLength; i++) {
              xorBytes[i] = constRawBytes[i] ^ anchor.raw[i];
            }
            const xorEncoded = opts.constPoolEncoding
              ? encodeBytes(xorBytes, opts.constPoolEncoding, opts)
              : { bytes: xorBytes, encoding: null };
            if (xorEncoded.bytes.length < chosenBytes.length) {
              chosenBytes = xorEncoded.bytes;
              chosenEncoding = xorEncoded.encoding;
              chosenDeltaBaseId = anchor.id;
              chosenDeltaOp = "xor";
            }
          }

          const directStoredLength = directEncoded.bytes.length >>> 0;
          const currentAnchor = constPoolAnchorsByLength.get(constLength);
          if (!currentAnchor || directStoredLength < currentAnchor.directStoredLength) {
            constPoolAnchorsByLength.set(constLength, {
              id: constPoolId,
              raw: constRawBytes,
              directStoredLength,
            });
          }
        }

        const outStoredLength = chosenBytes.length >>> 0;
        const record = {
          id: constPoolId,
          offset: useSharedConstPoolBlobOutput ? sharedConstPoolRawLength : writeOffset,
          length: constLength,
        };
        if (outStoredLength !== constLength) {
          record.storedLength = outStoredLength;
        }
        if (chosenEncoding) {
          record.encoding = chosenEncoding;
          compressedUniqueConstPools += 1;
        }
        if (chosenDeltaBaseId != null) {
          record.deltaBaseId = chosenDeltaBaseId;
          record.deltaOp = chosenDeltaOp;
          deltaConstPools += 1;
        }

        if (useSharedConstPoolBlobOutput) {
          constPoolPayloadById.set(constPoolId, chosenBytes);
          sharedConstPoolRawLength += outStoredLength;
        } else {
          writeSpan(outFd, chosenBytes, writeOffset);
          writeOffset += outStoredLength;
        }

        outConstPools.push(record);
        uniqueConstBytes += constLength;
        storedUniqueConstBytes += outStoredLength;
      } else {
        reusedConstPools += 1;
      }

      outEntry.constPoolId = constPoolId;
      outModules.push(outEntry);
    }

    if (useSharedConstPoolBlobOutput && outConstPools.length > 0) {
      if (sharedConstPoolRawLength === 0) {
        throw new Error("shared const pool blob requested but no payload bytes were collected");
      }

      const sharedRaw = Buffer.allocUnsafe(sharedConstPoolRawLength);
      let cursor = 0;
      for (let i = 0; i < outConstPools.length; i++) {
        const payload = constPoolPayloadById.get(i);
        if (!payload) {
          throw new Error(`missing payload for shared const pool id ${i}`);
        }
        sharedRaw.set(payload, cursor);
        cursor += payload.length;
      }
      if (cursor !== sharedRaw.length) {
        throw new Error(`shared const pool blob size mismatch: expected ${sharedRaw.length}, built ${cursor}`);
      }

      const sharedEncoded = sharedConstPoolBlobEncoding
        ? encodeBytes(sharedRaw, sharedConstPoolBlobEncoding, opts)
        : { bytes: sharedRaw, encoding: null };
      const sharedOutBytes = sharedEncoded.bytes;
      const sharedOutEncoding = sharedEncoded.encoding;
      const sharedOutStoredLength = sharedOutBytes.length >>> 0;

      sharedConstPoolBlobInfo = {
        offset: writeOffset,
        length: sharedRaw.length >>> 0,
        storedLength: sharedOutStoredLength,
        encoding: sharedOutEncoding,
      };

      writeSpan(outFd, sharedOutBytes, writeOffset);
      writeOffset += sharedOutStoredLength;
    }
  } finally {
    fs.closeSync(inFd);
    fs.closeSync(outFd);
  }

  const indexBytes = encodeModuleBundleIndexV2({
    modules: outModules,
    constPools: outConstPools,
    templatePrefix: opts.templatePrefix,
  });

  await fsp.writeFile(output.tempIndexPath, indexBytes);

  const outManifest = {
    format: MODULE_BUNDLE_V2_FORMAT,
    version: MODULE_BUNDLE_V2_VERSION,
    binary: toPosixPath(path.relative(path.dirname(output.finalManifestPath), output.finalBinaryPath)),
    index: toPosixPath(path.relative(path.dirname(output.finalManifestPath), output.finalIndexPath)),
    exportNameTemplatePrefix: opts.templatePrefix,
    moduleCount: outModules.length,
    constPoolCount: outConstPools.length,
  };
  if (!opts.stripFunctions) {
    outManifest.functions = Array.isArray(manifest?.functions) ? manifest.functions : [];
  }
  if (sharedConstPoolBlobInfo) {
    outManifest.constPoolBlobOffset = sharedConstPoolBlobInfo.offset;
    outManifest.constPoolBlobLength = sharedConstPoolBlobInfo.length;
    if (sharedConstPoolBlobInfo.storedLength !== sharedConstPoolBlobInfo.length) {
      outManifest.constPoolBlobStoredLength = sharedConstPoolBlobInfo.storedLength;
    }
    if (sharedConstPoolBlobInfo.encoding) {
      outManifest.constPoolBlobEncoding = sharedConstPoolBlobInfo.encoding;
    }
  }
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

  await fsp.writeFile(output.tempManifestPath, `${JSON.stringify(outManifest)}\n`);

  if (opts.inPlace) {
    await fsp.rename(output.tempBinaryPath, output.finalBinaryPath);
    await fsp.rename(output.tempIndexPath, output.finalIndexPath);
    await fsp.rename(output.tempManifestPath, output.finalManifestPath);
  }

  const outputSize = (await fsp.stat(output.finalBinaryPath)).size;
  const indexSize = (await fsp.stat(output.finalIndexPath)).size;
  const savedBytes = inputSizeBefore - outputSize;

  console.log(`format: ${opts.format}`);
  console.log(`modules: ${outModules.length}`);
  console.log(`modules (raw bytes): ${rawModuleBytes}`);
  console.log(`modules (stored bytes): ${storedModuleBytes}`);
  console.log(`modules compressed: ${moduleCompressedCount}`);
  console.log(`const pools (raw): ${rawConstBytes}`);
  console.log(`const pools (unique): ${uniqueConstBytes}`);
  console.log(`const pools (unique stored): ${storedUniqueConstBytes}`);
  console.log(`const pools unique compressed: ${compressedUniqueConstPools}`);
  console.log(`const pools unique delta-encoded: ${deltaConstPools}`);
  console.log(`const pools reused: ${reusedConstPools}`);
  if (sharedConstPoolBlobInfo) {
    console.log(`const pool shared blob (raw): ${sharedConstPoolBlobInfo.length}`);
    console.log(`const pool shared blob (stored): ${sharedConstPoolBlobInfo.storedLength}`);
    console.log(`const pool shared blob encoding: ${sharedConstPoolBlobInfo.encoding ?? "raw"}`);
  }
  console.log(`const pool target encoding: ${opts.constPoolEncoding ?? "inherit"}`);
  console.log(`module target encoding: ${opts.moduleEncoding ?? "inherit"}`);
  console.log(`input binary: ${inputSizeBefore}`);
  console.log(`output binary: ${outputSize}`);
  console.log(`saved bytes: ${savedBytes}`);
  console.log(`index bytes: ${indexSize}`);
  console.log(`manifest: ${output.finalManifestPath}`);
  console.log(`binary: ${output.finalBinaryPath}`);
  console.log(`index: ${output.finalIndexPath}`);
}

main().catch((err) => {
  console.error(`FAIL: ${err.message}`);
  process.exit(1);
});
