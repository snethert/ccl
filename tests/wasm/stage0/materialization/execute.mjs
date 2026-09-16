#!/usr/bin/env node
// Node/V8 execution of one materialization bundle: node execute.mjs BUNDLE OUT
// The bundle holds the assembled template, runtimes, control modules, the
// interface, engine admission rows and per-binary classifications produced by
// the runner's disassembly. Everything observed is written to observed.json.
import fs from 'node:fs';
import path from 'node:path';
import { Worker } from 'node:worker_threads';
import { pathToFileURL } from 'node:url';
const [bundle, out] = process.argv.slice(2);
if (!bundle || !out) throw Error('usage: node execute.mjs BUNDLE_DIRECTORY OUTPUT_DIRECTORY');
const M = await import(pathToFileURL(path.join(bundle, 'materializer.mjs')).href);
const read = name => new Uint8Array(fs.readFileSync(path.join(bundle, name)));
const json = name => JSON.parse(fs.readFileSync(path.join(bundle, name), 'utf8'));
const abi = json('abi.json'), classes = json('classification.json'), admission = json('admission.json');
const cls = name => classes[name] || (() => { throw Error('no classification for ' + name); })();
const outcome = fn => { try { return { value: fn() }; } catch (e) { return { error: e.constructor.name, message: e.message }; } };
const refusal = fn => { try { fn(); return { escaped: true }; } catch (e) { return { refused: e.message }; } };
const record = { version: 1, engine: { node: process.version, v8: process.versions.v8 }, materializer_version: M.MATERIALIZER_VERSION };

const template = read('template.wasm');
const manifest = M.manifest(template, abi, cls('template.wasm'));
record.manifest = manifest;
const shared = M.materialize(template, manifest, abi, 'full', cls('template.wasm'), admission.node);
const unshared = M.materialize(template, manifest, abi, 'single_thread_jspi', cls('template.wasm'), admission.node);
const callback = M.materialize(template, manifest, abi, 'precompiled_callback', cls('template.wasm'), admission.node);
record.materialized = { shared: shared.record, unshared: unshared.record, callback: callback.record };
const diff = [];
for (let i = 0; i < template.length; i++) if (shared.bytes[i] !== template[i]) diff.push({ offset: i, template: template[i], shared: shared.bytes[i] });
record.byte_difference = { length_preserved: shared.bytes.length === template.length, differences: diff, unshared_identical: Buffer.compare(unshared.bytes, template) === 0, callback_identical: Buffer.compare(callback.bytes, template) === 0 };
fs.mkdirSync(out, { recursive: true });
fs.writeFileSync(path.join(out, 'shared.wasm'), shared.bytes); fs.writeFileSync(path.join(out, 'unshared.wasm'), unshared.bytes);

// Import limits: the engine's own acceptance of matching, narrower and wider memories.
const link = (bytes, memory) => outcome(() => { new WebAssembly.Instance(new WebAssembly.Module(bytes), { env: { memory }, runtime: { request: x => x } }); return 'linked'; });
const mem = (initial, maximum, sharedFlag) => new WebAssembly.Memory(maximum === undefined ? { initial, shared: sharedFlag } : { initial, maximum, shared: sharedFlag });
record.import_limits = {
  unshared_matching: link(unshared.bytes, mem(1, 4, false)), unshared_larger_minimum: link(unshared.bytes, mem(2, 4, false)), unshared_smaller_maximum: link(unshared.bytes, mem(1, 3, false)),
  unshared_larger_maximum: link(unshared.bytes, mem(1, 8, false)), unshared_unbounded: link(unshared.bytes, mem(1, undefined, false)), unshared_with_shared_memory: link(unshared.bytes, mem(1, 4, true)),
  shared_matching: link(shared.bytes, mem(1, 4, true)), shared_larger_maximum: link(shared.bytes, mem(1, 8, true)), shared_with_unshared_memory: link(shared.bytes, mem(1, 4, false)),
};
const growth = (bytes, memory) => { const t = new WebAssembly.Instance(new WebAssembly.Module(bytes), { env: { memory }, runtime: { request: x => x } }); return { to_maximum: t.exports.grow(3), beyond_maximum: t.exports.grow(1), size: t.exports.size(), buffer_bytes: memory.buffer.byteLength }; };
record.growth = { unshared: growth(unshared.bytes, mem(1, 4, false)), shared: growth(shared.bytes, mem(1, 4, true)) };

// Installation identity.
record.installation = {
  shared: outcome(() => (M.install(shared.bytes, shared.record), 'installed')), unshared: outcome(() => (M.install(unshared.bytes, unshared.record), 'installed')),
};

// Profile suspension paths: the same template bytes under three runtimes.
const runtimeFull = read('runtime-full.wasm'), runtimeJspi = read('runtime-jspi.wasm'), runtimeSync = read('runtime-sync.wasm');
record.runtime_checks = { full: outcome(() => M.checkRuntime(runtimeFull, 'full', abi, cls('runtime-full.wasm'))), jspi: outcome(() => M.checkRuntime(runtimeJspi, 'single_thread_jspi', abi, cls('runtime-jspi.wasm'))),
  sync: outcome(() => M.checkRuntime(runtimeSync, 'precompiled_callback', abi, cls('runtime-sync.wasm'))) };
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function fullProfile() {
  const memory = mem(1, 4, true), words = new Int32Array(memory.buffer), W = abi.words;
  const worker = new Worker(pathToFileURL(path.join(bundle, 'worker.mjs')), { workerData: { memory, runtime: runtimeFull, template: shared.bytes, argument: 21, calls: 2 } });
  let finished = false;
  const done = new Promise((resolve, reject) => {
    const timer = setTimeout(() => { worker.terminate(); reject(Error('WORKER_TIMEOUT')); }, 15000);
    worker.once('message', m => { clearTimeout(timer); finished = true; worker.terminate(); resolve(m); });
    worker.once('error', e => { clearTimeout(timer); reject(e); });
  });
  const served = [];
  const deadline = Date.now() + 10000;
  while (!finished && served.length < 2 && Date.now() < deadline) {
    if (Atomics.load(words, W.flag / 4) === 1) {
      const argument = Atomics.load(words, W.argument / 4);
      Atomics.store(words, W.answer / 4, argument * 2);
      Atomics.store(words, W.flag / 4, 0);
      Atomics.store(words, W.wait / 4, 1);
      let woken = 0;
      while (woken !== 1 && Date.now() < deadline) { woken = Atomics.notify(words, W.wait / 4, 1); if (woken !== 1) await sleep(1); }
      served.push({ argument, answer: argument * 2, woken });
    } else await sleep(1);
  }
  const result = await done;
  return { served, worker: result, counter: Atomics.load(words, W.counter / 4) };
}
record.profiles = { full: await fullProfile() };
async function jspiProfile() {
  if (typeof WebAssembly.Suspending !== 'function') return { available: false };
  const memory = mem(1, 4, false);
  let suspensions = 0;
  const io = new WebAssembly.Suspending(async x => { suspensions += 1; await sleep(2); return x * 2; });
  const rt = new WebAssembly.Instance(new WebAssembly.Module(runtimeJspi), { env: { memory }, host: { io } });
  const t = new WebAssembly.Instance(M.install(unshared.bytes, unshared.record), { env: { memory }, runtime: { request: rt.exports.request } });
  const entry = WebAssembly.promising(t.exports.entry);
  const results = [Array.from(await entry(21)), Array.from(await entry(21))];
  return { available: true, results, suspensions, counter: new Int32Array(memory.buffer)[abi.words.counter / 4] };
}
record.profiles.single_thread_jspi = await jspiProfile();
{
  const memory = mem(1, 4, false);
  const rt = new WebAssembly.Instance(new WebAssembly.Module(runtimeSync), { env: { memory } });
  const t = new WebAssembly.Instance(M.install(callback.bytes, callback.record), { env: { memory }, runtime: { request: rt.exports.request } });
  record.profiles.precompiled_callback = { results: [Array.from(t.exports.entry(21)), Array.from(t.exports.entry(21))], counter: new Int32Array(memory.buffer)[abi.words.counter / 4] };
}

// Rejection controls: each must be refused with its specific reason.
const bad = (name, mutate) => { const r = JSON.parse(JSON.stringify(manifest)); mutate(r); return r; };
// A valid module with different bytes: the template plus an appended custom section.
const tampered = new Uint8Array([...template, 0, 8, 6, ...Buffer.from('tamper'), 0, 0]);
const controls = {
  'wrong-offset': refusal(() => M.materialize(template, bad('o', r => { r.offset += 1; }), abi, 'full', cls('template.wasm'), admission.node)),
  'wrong-original-byte': refusal(() => M.materialize(template, bad('b', r => { r.original_byte = 3; }), abi, 'full', cls('template.wasm'), admission.node)),
  'wrong-template-hash': refusal(() => M.materialize(template, bad('h', r => { r.template_sha256 = '0'.repeat(64); }), abi, 'full', cls('template.wasm'), admission.node)),
  'tampered-template': refusal(() => M.materialize(tampered, manifest, abi, 'full', cls('template.wasm'), admission.node)),
  'wrong-maximum': refusal(() => M.materialize(template, bad('m', r => { r.maximum = 8; }), abi, 'full', cls('template.wasm'), admission.node)),
  'import-mismatch': refusal(() => M.materialize(template, bad('i', r => { delete r.imports['runtime.request']; }), abi, 'full', cls('template.wasm'), admission.node)),
  'export-mismatch': refusal(() => M.materialize(template, bad('e', r => { r.exports.entry.results = ['i32']; }), abi, 'full', cls('template.wasm'), admission.node)),
  'feature-mismatch': refusal(() => M.materialize(template, bad('f', r => { r.features = ['multivalue']; }), abi, 'full', cls('template.wasm'), admission.node)),
  'stale-materializer-version': refusal(() => M.materialize(template, bad('v', r => { r.materializer_version = 1; r.version = 1; }), abi, 'full', cls('template.wasm'), admission.node)),
  'unknown-profile': refusal(() => M.materialize(template, manifest, abi, 'legacy', cls('template.wasm'), admission.node)),
  'profile-not-admitted': refusal(() => M.materialize(template, manifest, abi, 'single_thread_jspi', cls('template.wasm'), admission.safari)),
  'already-shared-template': refusal(() => M.manifest(read('controls/already-shared.wasm'), abi, cls('controls/already-shared.wasm'))),
  'defined-memory-template': refusal(() => M.manifest(read('controls/defined-memory.wasm'), abi, cls('controls/defined-memory.wasm'))),
  'unbounded-template': refusal(() => M.manifest(read('controls/unbounded.wasm'), abi, cls('controls/unbounded.wasm'))),
  'wait-in-template': refusal(() => M.manifest(read('controls/wait-in-template.wasm'), abi, cls('controls/wait-in-template.wasm'))),
  'wrong-signature-template': refusal(() => M.manifest(read('controls/wrong-signature.wasm'), abi, cls('controls/wrong-signature.wasm'))),
  'stale-binary-hash': refusal(() => M.install(shared.bytes, { ...shared.record, binary_sha256: 'f'.repeat(64) })),
  'template-hash-as-identity': refusal(() => M.install(shared.bytes, { ...shared.record, binary_sha256: shared.record.template_sha256 })),
  'stale-install-version': refusal(() => M.install(shared.bytes, { ...shared.record, materializer_version: 1 })),
  'runtime-profile-mismatch': refusal(() => M.checkRuntime(runtimeFull, 'single_thread_jspi', abi, cls('runtime-full.wasm'))),
  'runtime-unshared-wait': refusal(() => M.checkRuntime(read('controls/runtime-unshared-wait.wasm'), 'precompiled_callback', abi, cls('controls/runtime-unshared-wait.wasm'))),
  'runtime-without-wait-for-full': refusal(() => M.checkRuntime(runtimeSync, 'full', abi, cls('runtime-sync.wasm'))),
  'runtime-shared-memory-for-unshared-profile': refusal(() => M.checkRuntime(read('controls/runtime-shared-nowait.wasm'), 'single_thread_jspi', abi, cls('controls/runtime-shared-nowait.wasm'))),
};
// Execution witness for the unshared-runtime-with-wait control: bypassing the
// profile check reaches a wait on unshared memory, which traps.
controls['runtime-unshared-wait-execution'] = outcome(() => {
  const memory = mem(1, 4, false);
  const rt = new WebAssembly.Instance(new WebAssembly.Module(read('controls/runtime-unshared-wait.wasm')), { env: { memory } });
  const t = new WebAssembly.Instance(new WebAssembly.Module(callback.bytes), { env: { memory }, runtime: { request: rt.exports.request } });
  return Array.from(t.exports.entry(21));
});
record.controls = controls;
fs.writeFileSync(path.join(out, 'observed.json'), JSON.stringify(record, null, 2) + '\n');
console.log('observed ' + path.join(out, 'observed.json'));
