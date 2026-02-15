/*
 * Runtime modules manifest smoke test.
 *
 * Validates that doc/wasm/wasm-runtime-modules.json is v2 and that its
 * binary+index sidecars can be resolved/decoded by the loader.
 */

import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { resolveBundleEntries } from "./ccl-loader.mjs";

function fail(msg) {
  console.error(`FAIL: ${msg}`);
  process.exit(1);
}

function assert(cond, msg) {
  if (!cond) fail(msg);
}

const manifestUrl = new URL("../../../build/wasm32/modules/wasm-smoke-modules.json", import.meta.url);
const manifestPath = fileURLToPath(manifestUrl);
const manifestDir = path.dirname(manifestPath);

const manifest = JSON.parse(await fs.readFile(manifestPath, "utf8"));
assert(manifest?.format === "ccl-wasm-modules-v2", "wasm-runtime-modules.json must be ccl-wasm-modules-v2");
assert(typeof manifest?.binary === "string" && manifest.binary.length > 0, "missing binary field");
assert(typeof manifest?.index === "string" && manifest.index.length > 0, "missing index field");

const binaryPath = path.resolve(manifestDir, manifest.binary);
const indexPath = path.resolve(manifestDir, manifest.index);

const binaryBytes = await fs.readFile(binaryPath);
const indexBytes = await fs.readFile(indexPath);
assert(binaryBytes.length > 0, "runtime modules binary is empty");
assert(indexBytes.length > 0, "runtime modules index is empty");

const resolved = await resolveBundleEntries({
  bundle: manifest,
  indexBytes,
});
const modules = Array.isArray(resolved?.modules) ? resolved.modules : [];
assert(modules.length > 0, "runtime modules manifest resolves to zero modules");

console.log("PASS: runtime modules manifest smoke test");
