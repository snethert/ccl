/*
 * Root image manifest smoke test.
 *
 * Verifies that every artifact listed in the root-image manifest exists and
 * matches the recorded SHA-256 hash.
 */

import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";

function fail(msg) {
  console.error(`FAIL: ${msg}`);
  process.exit(1);
}

function assert(cond, msg) {
  if (!cond) fail(msg);
}

function sha256Hex(bytes) {
  return crypto.createHash("sha256").update(bytes).digest("hex");
}

const args = process.argv.slice(2);
const manifestArgIndex = args.indexOf("--manifest");

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDir, "../../..");
const manifestPath = manifestArgIndex >= 0 && args[manifestArgIndex + 1]
  ? path.resolve(args[manifestArgIndex + 1])
  : path.resolve(repoRoot, "doc/wasm/root.image.manifest.json");

const manifest = JSON.parse(await fs.readFile(manifestPath, "utf8"));
assert(Number.isFinite(manifest?.schemaVersion) && (manifest.schemaVersion >>> 0) >= 1, "invalid schemaVersion");
assert(typeof manifest?.generatedAt === "string" && manifest.generatedAt.length > 0, "missing generatedAt");

const artifactKeys = [
  "rootImage",
  "runtimeModulesManifest",
  "runtimeModulesBinary",
  "runtimeModulesIndex",
  "kernelWasm",
  "subprimsWasm",
];
for (const key of artifactKeys) {
  const artifact = manifest?.artifacts?.[key];
  assert(artifact && typeof artifact === "object", `missing artifact: ${key}`);
  assert(typeof artifact.path === "string" && artifact.path.length > 0, `missing artifact path: ${key}`);
  assert(typeof artifact.sha256 === "string" && artifact.sha256.length === 64, `invalid artifact sha256: ${key}`);

  const absolutePath = path.isAbsolute(artifact.path)
    ? artifact.path
    : path.resolve(repoRoot, artifact.path);
  const bytes = await fs.readFile(absolutePath);
  const digest = sha256Hex(bytes);
  assert(digest === artifact.sha256, `${key} hash mismatch: expected ${artifact.sha256}, got ${digest}`);
}

console.log("PASS: root image manifest smoke test");
