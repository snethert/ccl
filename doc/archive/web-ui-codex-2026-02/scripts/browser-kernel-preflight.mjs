import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, "..");
const repoRoot = path.resolve(projectRoot, "..");

function firstExisting(paths) {
  for (const candidate of paths) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }
  return null;
}

function formatList(paths) {
  return paths
    .map((candidate) => `  - ${path.relative(repoRoot, candidate)}`)
    .join("\n");
}

const checks = [
  {
    id: "bundle",
    label: "UI bundle",
    candidates: [
      path.join(repoRoot, "doc/wasm/wasm-ui-modules.json"),
      path.join(repoRoot, "build/wasm32/modules/wasm-ui-modules.json"),
      path.join(repoRoot, "build/wasm32/wasm-ui-modules.json")
    ]
  },
  {
    id: "kernel",
    label: "Kernel wasm",
    candidates: [
      path.join(repoRoot, "build/wasm32/kernel/wasmcl.wasm"),
      path.join(repoRoot, "build/wasm32/wasmcl.wasm"),
      path.join(repoRoot, "doc/wasm/js/wasmcl.wasm")
    ]
  },
  {
    id: "subprims",
    label: "Subprims wasm",
    candidates: [
      path.join(repoRoot, "build/wasm32/subprims/subprims.wasm"),
      path.join(repoRoot, "build/wasm32/subprims.wasm"),
      path.join(repoRoot, "doc/wasm/js/subprims.wasm")
    ]
  },
  {
    id: "subprims-map",
    label: "Subprims map",
    candidates: [
      path.join(repoRoot, "build/wasm32/subprims-map.json")
    ]
  },
  {
    id: "boot-image",
    label: "Boot image (root or minimal)",
    candidates: [
      path.join(repoRoot, "build/wasm32/root.image"),
      path.join(repoRoot, "doc/wasm/root.image"),
      path.join(repoRoot, "build/wasm32/minimal.image"),
      path.join(repoRoot, "doc/wasm/minimal.image")
    ]
  }
];

let failures = 0;
console.log("Kernel browser harness preflight");
console.log("================================");
for (const check of checks) {
  const found = firstExisting(check.candidates);
  if (found) {
    console.log(`PASS ${check.label}: ${path.relative(repoRoot, found)}`);
  } else {
    failures += 1;
    console.log(`FAIL ${check.label}`);
    console.log(formatList(check.candidates));
  }
}

if (failures > 0) {
  console.log("");
  console.log(`Preflight failed with ${failures} missing requirement(s).`);
  console.log("Kernel-on browser harness is expected to fail until these assets exist.");
  process.exit(1);
}

console.log("");
console.log("Preflight passed. Kernel-on browser harness has required local assets.");
