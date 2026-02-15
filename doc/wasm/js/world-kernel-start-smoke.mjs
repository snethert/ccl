/*
 * world-kernel runner.start smoke test.
 *
 * Creates a world with a preloaded image and ensures runner.start enters
 * start_lisp via the post-load entrypoint.
 */

import fs from "node:fs/promises";
import { fileURLToPath } from "node:url";

import { createKernel } from "./world-kernel.mjs";

function fail(msg) {
  console.error(`FAIL: ${msg}`);
  process.exit(1);
}

function assert(cond, msg) {
  if (!cond) fail(msg);
}

function readFileUrl(url) {
  return fs.readFile(fileURLToPath(url));
}

const kernelUrl = new URL("./wasmcl.wasm", import.meta.url);
const kernelBytes = await readFileUrl(kernelUrl);

const subprimsUrl = new URL("./subprims.wasm", import.meta.url);
const subprimsBytes = await readFileUrl(subprimsUrl);
const subprimsMapUrl = new URL("../../../build/wasm32/subprims-map.json", import.meta.url);
const subprimsMap = JSON.parse(await fs.readFile(fileURLToPath(subprimsMapUrl), "utf-8"));

const imageUrl = new URL("../minimal.image", import.meta.url);
const imageBytes = await readFileUrl(imageUrl);

const worldKernel = createKernel({
  kernelBytes,
  subprimsBytes,
  subprimsMap,
  writeStdout: () => {},
  writeStderr: () => {},
});

const worldId = worldKernel.createWorld({ imageBytes });
const runnerId = await worldKernel.createRunner(worldId);
const runner = worldKernel.getRunner(runnerId);

assert(runner, "runner not found");
assert(runner.imageLoaded === true, "expected image to be loaded via autoload");

const rc = runner.start() | 0;
assert(rc === 0, `expected runner.start rc=0, got ${rc}`);

console.log("PASS: world-kernel start smoke test");
