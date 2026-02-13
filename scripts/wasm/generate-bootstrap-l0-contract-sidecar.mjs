#!/usr/bin/env node

import fsp from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT_DIR = path.resolve(__dirname, "../..");
const SOURCE_PATH = path.join(ROOT_DIR, "doc/wasm/js/bootstrap-l0-contract.mjs");
const DEFAULT_OUT_PATH = path.join(ROOT_DIR, "doc/wasm/bootstrap-l0-contract.v1.json");

function usage() {
  console.log("Usage:");
  console.log("  node scripts/wasm/generate-bootstrap-l0-contract-sidecar.mjs [--out PATH]");
}

function parseArgs(argv) {
  let outPath = DEFAULT_OUT_PATH;
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--out") {
      const value = argv[++i];
      if (!value) throw new Error("Missing required value for --out");
      outPath = path.resolve(value);
      continue;
    }
    if (arg === "-h" || arg === "--help") {
      usage();
      process.exit(0);
    }
    throw new Error(`Unknown argument: ${arg}`);
  }
  return { outPath };
}

function canonicalizeJson(value) {
  if (Array.isArray(value)) {
    return value.map(canonicalizeJson);
  }
  if (value && typeof value === "object") {
    const out = {};
    for (const key of Object.keys(value).sort()) {
      out[key] = canonicalizeJson(value[key]);
    }
    return out;
  }
  return value;
}

function requireArrayField(contract, key) {
  if (!Array.isArray(contract?.[key])) {
    throw new Error(`bootstrap contract is missing required array field: ${key}`);
  }
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  const moduleNs = await import(pathToFileURL(SOURCE_PATH).href);
  const contract = moduleNs?.BOOTSTRAP_L0_CONTRACT_V1;
  if (!contract || typeof contract !== "object" || Array.isArray(contract)) {
    throw new Error("bootstrap contract export BOOTSTRAP_L0_CONTRACT_V1 is missing or invalid");
  }

  requireArrayField(contract, "requiredConstPools");
  requireArrayField(contract, "requiredCallables");
  requireArrayField(contract, "requiredSpecialVariables");

  const canonicalContract = canonicalizeJson(contract);
  const json = `${JSON.stringify(canonicalContract, null, 2)}\n`;
  await fsp.mkdir(path.dirname(opts.outPath), { recursive: true });
  await fsp.writeFile(opts.outPath, json, "utf8");
}

main().catch((err) => {
  console.error(`error: ${err instanceof Error ? err.message : String(err)}`);
  process.exit(1);
});
