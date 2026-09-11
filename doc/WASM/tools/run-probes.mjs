#!/usr/bin/env node
// Initial hand-built execution only. No PROBE result discharges an S0 acceptance ID.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import { Worker } from 'node:worker_threads';
import { inspectTemplate, materialize, sha256 } from './materialize.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.dirname(here), repo = path.resolve(root, '../..');
const arg = process.argv.indexOf('--output');
if (arg < 0 || !process.argv[arg + 1]) throw Error('usage: node run-probes.mjs --output DIRECTORY');
const out = path.resolve(process.argv[arg + 1]);
if (out === root || out.startsWith(root + path.sep)) throw Error('retain results outside the source package');
fs.mkdirSync(out, { recursive: true });
// Refuse overwriting an evidence record or mixing output from different runs.
if (fs.readdirSync(out).length) throw Error('output directory must be empty');
const inventory = fs.readFileSync(path.join(root, 'stage0/inventory.json'));
const checkoutRevision = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: repo, encoding: 'utf8' }).trim();
const revision = JSON.parse(inventory).source_revision;
execFileSync('git', ['merge-base', '--is-ancestor', revision, checkoutRevision], { cwd: repo });
const status = execFileSync('git', ['status', '--porcelain'], { cwd: repo, encoding: 'utf8' });
const inputPaths = [...new Set(execFileSync('git', ['ls-files', '--modified', '--others', '--exclude-standard', '-z'], { cwd: repo, encoding: 'utf8' }).split('\0').filter(Boolean))].sort();
const inputs = inputPaths.map(p => ({ path: p, sha256: fs.existsSync(path.join(repo, p)) ? sha256(fs.readFileSync(path.join(repo, p))) : 'DELETED' }));
fs.writeFileSync(path.join(out, 'source-inputs.json'), JSON.stringify({ revision, checkout_revision: checkoutRevision, status, inputs }, null, 2));
const toolchain = { node: process.version, v8: process.versions.v8, wabt: execFileSync('wat2wasm', ['--version'], { encoding: 'utf8' }).trim(), os: os.platform(), release: os.release(), arch: os.arch() };
const testFiles = ['run-probes.mjs', 'materialize.mjs', 'probe-worker.mjs'];
for (const name of testFiles) fs.copyFileSync(path.join(here, name), path.join(out, name));
fs.copyFileSync(path.join(root, 'contracts/layout.json'), path.join(out, 'layout.json'));
const testRevision = sha256(Buffer.from(testFiles.map(name => `${name}:${sha256(fs.readFileSync(path.join(out, name)))}`).join('\n')));
const report = { version: 1, source_revision: revision, inventory_sha256: sha256(inventory),
  source_inputs_sha256: sha256(fs.readFileSync(path.join(out, 'source-inputs.json'))),
  scope: 'Initial hand-built probes only; Stage 0 remains incomplete.', results: [] };

function compile(name, wat) {
  if (name.includes('mutant')) {
    fs.mkdirSync(path.join(out, 'quarantine'), { recursive: true });
    name = 'quarantine/' + name;
  }
  const src = path.join(out, name + '.wat'), dest = path.join(out, name + '.wasm');
  fs.writeFileSync(src, wat);
  execFileSync('wat2wasm', [src, '--enable-threads', '--enable-tail-call', '-o', dest], { encoding: 'utf8', timeout: 10000 });
  return fs.readFileSync(dest);
}
function artifact(name, role) { return { path: name, role, sha256: sha256(fs.readFileSync(path.join(out, name))) }; }
function retainedFiles(dir = out, prefix = '') {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap(e => e.isDirectory()
    ? retainedFiles(path.join(dir, e.name), prefix + e.name + '/') : [prefix + e.name]);
}
async function probe(id, assertionNames, fn) {
  const before = new Set(retainedFiles());
  let error;
  try { await fn(); } catch (e) { error = e.stack ?? String(e); }
  const logName = id + '.log';
  fs.writeFileSync(path.join(out, logName), error ?? assertionNames.join('\n') + '\nPASS\n');
  const binaries = retainedFiles().filter(p => p.endsWith('.wasm') && !before.has(p));
  report.results.push({ id, variant: 'initial-hand-built', status: error ? 'FAIL' : 'PASS',
    evidence_kind: 'HAND-BUILT WASM EXECUTION', source_revision: revision, test_revision: testRevision,
    toolchain, engine: `Node ${process.version} / V8 ${process.versions.v8}`, timestamp: new Date().toISOString(),
    command: 'node doc/WASM/tools/run-probes.mjs --output ' + out,
    configuration: { scope: 'initial probe only', wat_flags: ['--enable-threads', '--enable-tail-call'] }, seed: 0,
    substitutions: [], skips: [], review_disposition: 'NOT_REVIEWED',
    assertions: assertionNames.map(id => ({ id, status: error ? 'FAIL' : 'PASS' })),
    artifacts: [...binaries.map(p => artifact(p, p.startsWith('quarantine/') ? 'negative_control' : 'implementation')), ...testFiles.map(p => artifact(p, 'test')),
      artifact('layout.json', 'schema'), artifact('source-inputs.json', 'provenance'), artifact(logName, 'log')] });
  console.log(`${error ? 'FAIL' : 'PASS'} ${id}`);
  fs.writeFileSync(path.join(out, 'results.json'), JSON.stringify(report, null, 2) + '\n');
}

await probe('PROBE-cons-layout', ['independent-byte-fixture', 'car-cdr-mutation', 'one-sided-swap-rejected', 'signed-fixnum-bounds'], () => {
  const bytes = compile('cons', `(module (import "env" "memory" (memory 1 4))
    (func (export "car") (param $p i32) (result i32) (i32.load offset=3 (local.get $p)))
    (func (export "cdr") (param $p i32) (result i32) (i32.load (i32.sub (local.get $p) (i32.const 1))))
    (func (export "setcar") (param $p i32) (param $v i32) (i32.store offset=3 (local.get $p) (local.get $v)))
    (func (export "setcdr") (param $p i32) (param $v i32) (i32.store (i32.sub (local.get $p) (i32.const 1)) (local.get $v)))
    (func (export "unbox") (param $x i32) (result i32) (i32.shr_s (local.get $x) (i32.const 2))))`);
  const memory = new WebAssembly.Memory({ initial: 1, maximum: 4 });
  const f = new WebAssembly.Instance(new WebAssembly.Module(bytes), { env: { memory } }).exports;
  // Hard-coded independent fixture: CDR=-7 tagged, CAR=11 tagged; no schema-generated writer.
  new Uint8Array(memory.buffer, 64, 8).set([0xe4, 0xff, 0xff, 0xff, 0x2c, 0, 0, 0]);
  assert.equal(f.cdr(65), -28); assert.equal(f.car(65), 44);
  f.setcar(65, 68); assert.equal(f.cdr(65), -28); assert.equal(f.car(65), 68);
  f.setcdr(65, 92); assert.equal(f.cdr(65), 92); assert.equal(f.car(65), 68);
  new Uint8Array(memory.buffer, 64, 8).set([0x2c, 0, 0, 0, 0xe4, 0xff, 0xff, 0xff]);
  assert.throws(() => assert.equal(f.cdr(65), -28), assert.AssertionError);
  assert.equal(f.unbox(-2147483648), -536870912);
  assert.equal(f.unbox(2147483644), 536870911);
  const schema = JSON.parse(fs.readFileSync(path.join(out, 'layout.json')));
  assert.deepEqual([schema.word_bytes, schema.cons.cdr_raw_offset, schema.cons.car_raw_offset, schema.cons.tag], [4, 0, 4, 1]);
});

await probe('PROBE-memory-materialization', ['structural-flag-materialization', 'shared-unshared-loads', 'unshared-wait-traps', 'import-mismatch-rejected', 'growth-refresh', 'bad-hash-offset-limits-rejected'], () => {
  const template = compile('memory-template', `(module (import "env" "memory" (memory 1 4))
    (func (export "load") (result i32) (i32.atomic.load (i32.const 0)))
    (func (export "wait") (result i32) (memory.atomic.wait32 (i32.const 0) (i32.const 0) (i64.const 0))))`);
  const manifest = { version: 1, template_sha256: sha256(template), original_byte: 1, ...inspectTemplate(template) };
  const variants = [];
  for (const shared of [false, true]) {
    const bytes = materialize(template, manifest, shared);
    const name = shared ? 'memory-shared.wasm' : 'memory-unshared.wasm';
    fs.writeFileSync(path.join(out, name), bytes);
    variants.push({ profile: shared ? 'shared' : 'unshared', binary_sha256: sha256(bytes) });
    const memory = new WebAssembly.Memory({ initial: 1, maximum: 4, shared });
    const f = new WebAssembly.Instance(new WebAssembly.Module(bytes), { env: { memory } }).exports;
    assert.equal(f.load(), 0);
    if (shared) assert.equal(f.wait(), 2); else assert.throws(() => f.wait(), WebAssembly.RuntimeError);
    const wrong = new WebAssembly.Memory({ initial: 1, maximum: 4, shared: !shared });
    assert.throws(() => new WebAssembly.Instance(new WebAssembly.Module(bytes), { env: { memory: wrong } }), WebAssembly.LinkError);
    const tooLarge = new WebAssembly.Memory({ initial: 1, maximum: 5, shared });
    assert.throws(() => new WebAssembly.Instance(new WebAssembly.Module(bytes), { env: { memory: tooLarge } }), WebAssembly.LinkError);
    const old = new Uint8Array(memory.buffer); memory.grow(1);
    const refreshed = new Uint8Array(memory.buffer); assert.equal(refreshed.length, 131072);
    assert.equal(old.length, shared ? 65536 : 0);
    refreshed[70000] = 73; assert.equal(new Uint8Array(memory.buffer)[70000], 73);
  }
  assert.throws(() => materialize(template, { ...manifest, offset: manifest.offset + 1 }, true));
  assert.throws(() => materialize(template, { ...manifest, template_sha256: '0'.repeat(64) }, true));
  assert.throws(() => materialize(template, { ...manifest, maximum: 5 }, true));
  assert.throws(() => materialize(template, { ...manifest, original_byte: 3 }, true));
  const truncated = template.subarray(0, -1);
  assert.throws(() => inspectTemplate(truncated));
  fs.writeFileSync(path.join(out, 'materialization.json'), JSON.stringify({ ...manifest, materializer_sha256: sha256(fs.readFileSync(path.join(here, 'materialize.mjs'))), variants }, null, 2));
});

function worker(bytes, memory, privateOffset, token) {
  return new Promise((resolve, reject) => {
    const w = new Worker(new URL('./probe-worker.mjs', import.meta.url), { workerData: { bytes, memory, privateOffset, token } });
    let settled = false;
    const finish = (error, value) => {
      if (settled) return; settled = true; clearTimeout(timer);
      w.terminate().then(() => error ? reject(error) : resolve(value), reject);
    };
    const timer = setTimeout(() => finish(Error('Worker probe timeout')), 5000);
    w.once('error', e => finish(e));
    w.once('message', m => finish(m.error ? Error(m.error) : null, m));
    w.once('exit', code => { if (!settled) finish(Error(`Worker exited before result: ${code}`)); });
  });
}

await probe('PROBE-late-worker', ['process-once-sentinel-survives', 'worker-private-regions-distinct', 'repeated-active-data-mutant-detected'], async () => {
  const wat = `(module (import "env" "memory" (memory 1 4 shared))
    (func (export "init") (local $old i32)
      (local.set $old (i32.atomic.rmw.cmpxchg (i32.const 0) (i32.const 0) (i32.const 1)))
      (if (i32.eqz (local.get $old))
        (then (i32.store (i32.const 16) (i32.const 123))
          (i32.atomic.store (i32.const 0) (i32.const 2))
          (drop (memory.atomic.notify (i32.const 0) (i32.const 2147483647)))))
      (block $done (loop $wait
        (br_if $done (i32.eq (i32.atomic.load (i32.const 0)) (i32.const 2)))
        (drop (memory.atomic.wait32 (i32.const 0) (i32.const 1) (i64.const 1000000000)))
        (br $wait))))
    (func (export "privateSetup") (param $p i32) (param $v i32)
      (i32.store (local.get $p) (local.get $v)))
    ACTIVE_SEGMENT)`;
  const bytes = compile('late-worker', wat.replace('ACTIVE_SEGMENT', ''));
  const memory = new WebAssembly.Memory({ initial: 1, maximum: 4, shared: true });
  const f = new WebAssembly.Instance(new WebAssembly.Module(bytes), { env: { memory } }).exports;
  f.init();
  const words = new Int32Array(memory.buffer); assert.equal(words[4], 123); words[4] = 777;
  const results = await Promise.all([worker(bytes, memory, 2048, 101), worker(bytes, memory, 2112, 202)]);
  assert.deepEqual(results.map(r => r.sentinel), [777, 777]);
  assert.deepEqual(results.map(r => r.initialized), [2, 2]);
  assert.deepEqual([words[512], words[528]], [101, 202]);
  const mutant = compile('late-worker-mutant', wat.replace('ACTIVE_SEGMENT', '(data (i32.const 16) "\\01\\00\\00\\00")'));
  const bad = await worker(mutant, memory, 2176, 303);
  assert.throws(() => assert.equal(bad.sentinel, 777), assert.AssertionError);
});

console.log(`Retained ${report.results.length} initial probe records in ${out}. Stage 0 is NOT accepted.`);
process.exitCode = report.results.some(r => r.status !== 'PASS') ? 1 : 0;
