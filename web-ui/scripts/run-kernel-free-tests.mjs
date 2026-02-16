import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, "..");
const testsRoot = path.join(projectRoot, "tests");

function listFilesRecursive(root) {
  const out = [];
  const queue = [root];
  while (queue.length > 0) {
    const current = queue.pop();
    const entries = fs.readdirSync(current, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(current, entry.name);
      if (entry.isDirectory()) {
        queue.push(fullPath);
        continue;
      }
      if (entry.isFile()) {
        out.push(fullPath);
      }
    }
  }
  return out;
}

function isKernelDependentTestFile(fullPath) {
  const relPath = path.relative(projectRoot, fullPath).split(path.sep).join("/");
  if (!relPath.startsWith("tests/")) return true;
  if (!relPath.endsWith(".test.mjs")) return true;
  if (relPath.startsWith("tests/browser/")) return true;

  const source = fs.readFileSync(fullPath, "utf8");
  return source.includes("doc/wasm/js/");
}

const testFiles = listFilesRecursive(testsRoot)
  .filter((fullPath) => !isKernelDependentTestFile(fullPath))
  .map((fullPath) => path.relative(projectRoot, fullPath).split(path.sep).join("/"))
  .sort((a, b) => a.localeCompare(b));

if (testFiles.length === 0) {
  console.error("No kernel-free tests were discovered.");
  process.exit(1);
}

const result = spawnSync(process.execPath, ["--test", ...testFiles], {
  cwd: projectRoot,
  stdio: "inherit"
});

if (result.error) {
  throw result.error;
}
process.exit(result.status ?? 1);
