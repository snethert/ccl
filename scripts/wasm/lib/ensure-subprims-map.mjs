/**
 * Ensure build/wasm32/subprims-map.json exists, auto-generating if missing.
 *
 * Usage:
 *   import { ensureSubprimsMap } from "./lib/ensure-subprims-map.mjs";
 *   const subprimsMap = await ensureSubprimsMap(repoRoot);
 */

import fs from "node:fs/promises";
import { execFileSync } from "node:child_process";
import path from "node:path";

export async function ensureSubprimsMap(repoRoot) {
  const mapPath = path.join(repoRoot, "build/wasm32/subprims-map.json");
  try {
    await fs.access(mapPath);
  } catch {
    const genScript = path.join(repoRoot, "scripts/wasm/generate_subprims_artifacts.py");
    console.error(`subprims-map.json missing — generating automatically...`);
    execFileSync("python3", [genScript], { cwd: repoRoot, stdio: "inherit" });
  }
  return JSON.parse(await fs.readFile(mapPath, "utf-8"));
}

export function ensureSubprimsMapPath(repoRoot) {
  return path.join(repoRoot, "build/wasm32/subprims-map.json");
}
