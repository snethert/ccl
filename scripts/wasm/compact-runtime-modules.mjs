#!/usr/bin/env node

import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";
import * as zlib from "node:zlib";

function usage() {
  console.log("Usage:");
  console.log("  node scripts/wasm/compact-runtime-modules.mjs --manifest PATH [--out-manifest PATH] [--out-binary PATH] [--compress-const-pools]");
  console.log("  node scripts/wasm/compact-runtime-modules.mjs --manifest PATH --in-place [--compress-const-pools]");
  console.log("  node scripts/wasm/compact-runtime-modules.mjs --manifest PATH --in-place --const-pool-encoding br --brotli-quality 7");
}

function parseArgs(argv) {
  const opts = {
    manifest: null,
    outManifest: null,
    outBinary: null,
    inPlace: false,
    constPoolEncoding: null,
    brotliQuality: 5,
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
    if (arg === "--in-place") {
      opts.inPlace = true;
      continue;
    }
    if (arg === "--compress-const-pools") {
      if (!opts.constPoolEncoding) opts.constPoolEncoding = "gzip";
      continue;
    }
    if (arg === "--const-pool-encoding") {
      opts.constPoolEncoding = normalizeEncoding(argv[++i] ?? null, "--const-pool-encoding");
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
    if (arg === "-h" || arg === "--help") {
      usage();
      process.exit(0);
    }
    throw new Error(`Unknown argument: ${arg}`);
  }

  if (!opts.manifest) {
    throw new Error("Missing required --manifest PATH");
  }
  if (opts.inPlace && (opts.outManifest || opts.outBinary)) {
    throw new Error("--in-place cannot be combined with --out-manifest or --out-binary");
  }
  if (opts.constPoolEncoding !== "br" && opts.brotliQuality !== 5) {
    throw new Error("--brotli-quality is only valid with --const-pool-encoding br");
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
    throw new Error("Bundle manifest missing non-empty \"binary\" field");
  }
  return path.resolve(manifestDir, binaryField);
}

function deriveOutputPaths(opts, manifestPath, manifest, inputBinaryPath) {
  if (opts.inPlace) {
    return {
      finalManifestPath: manifestPath,
      finalBinaryPath: inputBinaryPath,
      tempManifestPath: `${manifestPath}.tmp`,
      tempBinaryPath: `${inputBinaryPath}.tmp`,
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

  return {
    finalManifestPath: outManifestPath,
    finalBinaryPath: outBinaryPath,
    tempManifestPath: outManifestPath,
    tempBinaryPath: outBinaryPath,
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

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  const manifestPath = path.resolve(opts.manifest);
  const manifestDir = path.dirname(manifestPath);
  const manifest = JSON.parse(await fsp.readFile(manifestPath, "utf8"));
  const modules = Array.isArray(manifest.modules) ? manifest.modules : [];
  if (modules.length === 0) {
    throw new Error("Bundle contains no modules");
  }

  const inputBinaryPath = normalizeBinaryPath(manifestDir, manifest.binary);
  const inputSizeBefore = (await fsp.stat(inputBinaryPath)).size;
  const output = deriveOutputPaths(opts, manifestPath, manifest, inputBinaryPath);
  if (!opts.inPlace && output.finalBinaryPath === inputBinaryPath) {
    throw new Error("Refusing to overwrite input binary without --in-place");
  }
  await fsp.mkdir(path.dirname(output.tempBinaryPath), { recursive: true });
  await fsp.mkdir(path.dirname(output.tempManifestPath), { recursive: true });

  const inFd = fs.openSync(inputBinaryPath, "r");
  const outFd = fs.openSync(output.tempBinaryPath, "w+");

  const constPoolIndex = new Map();
  const outModules = [];
  let writeOffset = 0;
  let rawConstBytes = 0;
  let uniqueConstBytes = 0;
  let storedUniqueConstBytes = 0;
  let compressedUniqueConstPools = 0;
  let reusedConstPools = 0;

  try {
    for (const entry of modules) {
      const outEntry = { ...entry };
      if (!Number.isFinite(entry.offset) || !Number.isFinite(entry.length)) {
        throw new Error(`module ${entry.exportName ?? "?"} missing offset/length`);
      }

      const moduleOffset = entry.offset >>> 0;
      const moduleLength = entry.length >>> 0;
      const moduleStoredLength = Number.isFinite(entry.moduleStoredLength)
        ? (entry.moduleStoredLength >>> 0)
        : moduleLength;
      const moduleEncoding = normalizeEncoding(entry.moduleEncoding ?? null, "module encoding");
      const moduleBytes = readSpan(inFd, moduleOffset, moduleStoredLength);
      outEntry.offset = writeOffset;
      outEntry.length = moduleLength;
      writeSpan(outFd, moduleBytes, writeOffset);
      writeOffset += moduleStoredLength;
      if (moduleStoredLength !== moduleLength) {
        outEntry.moduleStoredLength = moduleStoredLength;
      } else {
        delete outEntry.moduleStoredLength;
      }
      if (moduleEncoding) {
        outEntry.moduleEncoding = moduleEncoding;
      } else {
        delete outEntry.moduleEncoding;
      }

      const hasConstPool =
        Number.isFinite(entry.constPoolOffset) &&
        Number.isFinite(entry.constPoolLength) &&
        (entry.constPoolLength >>> 0) > 0;

      if (!hasConstPool) {
        delete outEntry.constPoolOffset;
        delete outEntry.constPoolLength;
        delete outEntry.constPoolStoredLength;
        delete outEntry.constPoolEncoding;
        outModules.push(outEntry);
        continue;
      }

      const constOffset = entry.constPoolOffset >>> 0;
      const constLength = entry.constPoolLength >>> 0;
      const constStoredLength = Number.isFinite(entry.constPoolStoredLength)
        ? (entry.constPoolStoredLength >>> 0)
        : constLength;
      const constInputEncoding = normalizeEncoding(entry.constPoolEncoding ?? null, "const pool encoding");
      const constStoredBytes = readSpan(inFd, constOffset, constStoredLength);
      const constBytes = decodeBytes(constStoredBytes, constInputEncoding, constLength);
      rawConstBytes += constLength;

      const hash = crypto.createHash("sha256").update(constBytes).digest("hex");
      const sig = `${constLength}:${hash}`;
      const reused = constPoolIndex.get(sig) ?? null;

      if (reused) {
        outEntry.constPoolOffset = reused.offset;
        outEntry.constPoolLength = constLength;
        if (reused.storedLength !== constLength) {
          outEntry.constPoolStoredLength = reused.storedLength;
        } else {
          delete outEntry.constPoolStoredLength;
        }
        if (reused.encoding) {
          outEntry.constPoolEncoding = reused.encoding;
        } else {
          delete outEntry.constPoolEncoding;
        }
        reusedConstPools += 1;
      } else {
        const desiredEncoding = opts.constPoolEncoding;
        const encoded = desiredEncoding
          ? encodeBytes(constBytes, desiredEncoding, opts)
          : { bytes: constStoredBytes, encoding: constInputEncoding };
        const outputBytes = encoded.bytes;
        const outputStoredLength = outputBytes.length >>> 0;

        outEntry.constPoolOffset = writeOffset;
        outEntry.constPoolLength = constLength;
        writeSpan(outFd, outputBytes, writeOffset);
        writeOffset += outputStoredLength;
        uniqueConstBytes += constLength;
        storedUniqueConstBytes += outputStoredLength;
        if (outputStoredLength !== constLength) {
          outEntry.constPoolStoredLength = outputStoredLength;
        } else {
          delete outEntry.constPoolStoredLength;
        }
        if (encoded.encoding) {
          outEntry.constPoolEncoding = encoded.encoding;
          compressedUniqueConstPools += 1;
        } else {
          delete outEntry.constPoolEncoding;
        }
        constPoolIndex.set(sig, {
          offset: outEntry.constPoolOffset,
          storedLength: outputStoredLength,
          encoding: encoded.encoding,
        });
      }

      outModules.push(outEntry);
    }
  } finally {
    fs.closeSync(inFd);
    fs.closeSync(outFd);
  }

  const outManifest = {
    ...manifest,
    binary: toPosixPath(path.relative(path.dirname(output.finalManifestPath), output.finalBinaryPath)),
    modules: outModules,
  };

  await fsp.writeFile(output.tempManifestPath, `${JSON.stringify(outManifest)}\n`);

  if (opts.inPlace) {
    await fsp.rename(output.tempBinaryPath, output.finalBinaryPath);
    await fsp.rename(output.tempManifestPath, output.finalManifestPath);
  }

  const outputSize = (await fsp.stat(output.finalBinaryPath)).size;
  const savedBytes = inputSizeBefore - outputSize;

  console.log(`modules: ${outModules.length}`);
  console.log(`const pools (raw): ${rawConstBytes}`);
  console.log(`const pools (unique): ${uniqueConstBytes}`);
  console.log(`const pools (unique stored): ${storedUniqueConstBytes}`);
  console.log(`const pools unique compressed: ${compressedUniqueConstPools}`);
  console.log(`const pool target encoding: ${opts.constPoolEncoding ?? "inherit"}`);
  console.log(`const pools reused: ${reusedConstPools}`);
  console.log(`input binary: ${inputSizeBefore}`);
  console.log(`output binary: ${outputSize}`);
  console.log(`saved bytes: ${savedBytes}`);
  console.log(`manifest: ${output.finalManifestPath}`);
  console.log(`binary: ${output.finalBinaryPath}`);
}

main().catch((err) => {
  console.error(`FAIL: ${err.message}`);
  process.exit(1);
});
