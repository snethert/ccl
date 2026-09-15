#!/usr/bin/env node
// Node/V8 reference-engine execution of one bundle: node execute.mjs BUNDLE OUT
import fs from 'node:fs';
import path from 'node:path';
import { Worker } from 'node:worker_threads';
import { pathToFileURL } from 'node:url';
const [bundle, out] = process.argv.slice(2);
if (!bundle || !out) throw Error('usage: node execute.mjs BUNDLE_DIRECTORY OUTPUT_DIRECTORY');
const { runMatrix } = await import(pathToFileURL(path.join(bundle, 'matrix.mjs')).href);
const read = name => new Uint8Array(fs.readFileSync(path.join(bundle, name)));
const probeNames = fs.readdirSync(path.join(bundle, 'probes')).filter(n => n.endsWith('.wasm')).sort();
const bytes = { features: read('features.wasm'), featuresShared: read('features-shared.wasm'), suspend: read('suspend.wasm'), invalid: read('invalid.wasm'),
  probes: Object.fromEntries(probeNames.map(n => [n.replace(/\.wasm$/, ''), read(path.join('probes', n))])) };
const sleep = ms => new Promise(r => setTimeout(r, ms));
function spawnWaiter(data) {
  return new Promise((resolve, reject) => {
    const w = new Worker(pathToFileURL(path.join(bundle, 'wait-worker.mjs')), { workerData: data });
    const timer = setTimeout(() => { w.terminate(); reject(Error('WAITER_TIMEOUT')); }, 15000);
    w.once('message', m => { clearTimeout(timer); w.terminate(); resolve(m); });
    w.once('error', e => { clearTimeout(timer); reject(e); });
    w.once('exit', code => { clearTimeout(timer); if (code !== 0) reject(Error('WAITER_EXIT ' + code)); });
  });
}
const engine = { kind: 'node', node: process.version, v8: process.versions.v8, platform: process.platform, arch: process.arch, execArgv: process.execArgv };
const record = await runMatrix({ engine, bytes, spawnWaiter, sleep });
fs.mkdirSync(out, { recursive: true });
fs.writeFileSync(path.join(out, 'observed.json'), JSON.stringify(record, null, 2) + '\n');
console.log('observed ' + path.join(out, 'observed.json'));
