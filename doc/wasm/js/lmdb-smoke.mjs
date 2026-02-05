import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import * as lmdb from "lmdb";

function makeWorkDir() {
  const override = process.env.LMDB_SMOKE_PATH;
  if (override) return override;
  return fs.mkdtempSync(path.join(os.tmpdir(), "ccl-lmdb-smoke-"));
}

function cleanup(dir, keep) {
  if (keep) return;
  try {
    fs.rmSync(dir, { recursive: true, force: true });
  } catch (_e) {
    // best-effort
  }
}

const keepDir = process.env.LMDB_SMOKE_KEEP === "1";
const workDir = makeWorkDir();

try {
  const env = lmdb.open({ path: workDir, maxDbs: 8 });
  const meta = env.openDB("meta");
  // Use synchronous write to avoid async commit timing in smoke tests.
  meta.putSync("key", "value");
  const got = meta.get("key");
  if (got !== "value") {
    throw new Error(`unexpected value: ${String(got)}`);
  }
  meta.close?.();
  env.close?.();
  cleanup(workDir, keepDir);
  // eslint-disable-next-line no-console
  console.log("lmdb-smoke: ok", workDir);
} catch (err) {
  cleanup(workDir, keepDir);
  // eslint-disable-next-line no-console
  console.error("lmdb-smoke: failed", err?.message || err);
  process.exitCode = 1;
}
