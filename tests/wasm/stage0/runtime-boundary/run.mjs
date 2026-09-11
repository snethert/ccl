#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { Worker } from 'node:worker_threads';
import { inspect, preflight } from './binary.mjs';
import { adapterWat } from './adapter.mjs';
import { planMemory, validateMap, instantiate, setup, assertIsolation } from './runtime.mjs';
import { clang, ld, wat, checkLLVM } from './toolchain.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, '../../../..'), docs = path.join(repo, 'doc/WASM');
const pos = process.argv.indexOf('--output');
if (pos < 0 || !process.argv[pos + 1]) throw Error('usage: node tests/wasm/stage0/runtime-boundary/run.mjs --output EMPTY_DIRECTORY');
const out = path.resolve(process.argv[pos + 1]);
if (out === repo || out.startsWith(repo + path.sep)) throw Error('run into a separate evidence directory before retention');
fs.mkdirSync(out, { recursive: true });
assert.equal(fs.readdirSync(out).length, 0, 'do not mix evidence runs');
fs.mkdirSync(path.join(out, 'quarantine'));
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const fileSha = p => sha(fs.readFileSync(p));
const json = (name, value) => fs.writeFileSync(path.join(out, name), JSON.stringify(value, null, 2) + '\n');
const commandLog = [];
let commandNumber = 0;
function command(executable, args, { expectedFailure = false, reason } = {}) {
  const result = spawnSync(executable, args, { encoding: 'utf8', timeout: 30000, cwd: repo });
  const rec = { executable, args, exit_code: result.status, signal: result.signal, error: result.error?.message,
    stdout: result.stdout ?? '', stderr: result.stderr ?? '', expected_failure: expectedFailure, reason };
  const log = `command-${String(++commandNumber).padStart(2, '0')}.json`;
  json(log, rec); commandLog.push(log);
  if (result.error || result.signal) throw Error(`command did not complete: ${executable}; ${log}`);
  if (expectedFailure) assert.notEqual(result.status, 0, `negative link control unexpectedly passed: ${log}`);
  else if (result.status !== 0) throw Error(`command failed: ${executable}; ${log}\n${result.stderr}`);
  return rec;
}

const checkoutRevision = command('git', ['rev-parse', 'HEAD']).stdout.trim();
const inventoryPath = path.join(docs, 'stage0/inventory.json');
const inventory = JSON.parse(fs.readFileSync(inventoryPath));
const revision = inventory.source_revision;
command('git', ['merge-base', '--is-ancestor', revision, checkoutRevision]);
const sourceNames = fs.readdirSync(here).filter(n => fs.statSync(path.join(here, n)).isFile()).sort();
fs.mkdirSync(path.join(out, 'source'));
const sourceFiles = sourceNames.map(name => {
  fs.copyFileSync(path.join(here, name), path.join(out, 'source', name));
  return { path: 'source/' + name, sha256: fileSha(path.join(here, name)) };
});
fs.copyFileSync(inventoryPath, path.join(out, 'inventory.json'));
const contract = JSON.parse(fs.readFileSync(path.join(here, 'contract.json')));
const sourceState = command('git', ['status', '--porcelain']).stdout;
const changed = command('git', ['ls-files', '--modified', '--others', '--exclude-standard', '-z']).stdout.split('\0').filter(Boolean);
json('source-state.json', { revision, checkout_revision: checkoutRevision, status: sourceState, inputs: [...new Set(changed)].sort().map(p => ({ path: p,
  sha256: fs.existsSync(path.join(repo, p)) ? fileSha(path.join(repo, p)) : 'DELETED' })) });
const tools = { clang: command(clang, ['--version']).stdout.trim(), linker: command(ld, ['--version']).stdout.trim(),
  wabt: command(wat, ['--version']).stdout.trim(), node: process.version, v8: process.versions.v8,
  os: os.platform(), release: os.release(), architecture: os.arch() };
checkLLVM(tools.clang, tools.linker);
tools.paths = { clang, linker: ld, wabt: wat };
tools.executable_sha256 = { clang: fileSha(clang), linker: fileSha(ld), wabt: fileSha(wat) };
const report = { version: 1, source_revision: revision, inventory_sha256: fileSha(inventoryPath),
  scope: 'Hand-built C/emitted boundary slices S0-LL13-c and S0-LL19-b; not full Stage 0 acceptance.',
  results: [], setup_failure: null };
const checks = { 'S0-LL13-c': [], 'S0-LL19-b': [] };
const negativeControls = [];
const record = (id, message, details = {}) => checks[id].push({ assertion: message, status: 'PASS', ...details });
function reject(id, name, fn, pattern) {
  assert.throws(fn, pattern);
  negativeControls.push({ name, obligation: id, status: 'REJECTED', quarantine: true });
}

function buildKernel(name, defines = [], expectedFailure = false) {
  const stem = path.join(out, name);
  const compileArgs = ['--target=wasm32-unknown-unknown', '-O1', '-ffreestanding', '-fno-builtin', '-fno-stack-protector',
    '-matomics', '-mbulk-memory', ...defines.map(d => '-D' + d), '-c', path.join(out, 'source/kernel.c'), '-o', stem + '.o'];
  command(clang, compileArgs);
  const link = command(ld, ['--no-entry', '--import-memory', '--import-table', '--shared-memory', '--initial-memory=131072',
    '--max-memory=1048576', '-z', 'stack-size=16384', '--fatal-warnings', '--export-all', '--export=__stack_pointer',
    '--export=__tls_base', '--Map=' + stem + '.map', stem + '.o', '-o', stem + '.wasm'], { expectedFailure });
  if (expectedFailure) { assert.match(link.stderr, /unapproved_helper/); return; }
  fs.writeFileSync(stem + '.disassembly.txt', command('wasm-objdump', ['-dx', stem + '.wasm']).stdout);
  return fs.readFileSync(stem + '.wasm');
}
function buildWat(name, source) {
  const stem = path.join(out, name);
  fs.writeFileSync(stem + '.wat', source);
  command(wat, ['--enable-threads', '--enable-exceptions', stem + '.wat', '-o', stem + '.wasm']);
  return fs.readFileSync(stem + '.wasm');
}
function uleb(n) { const b = []; do { let x = n % 128; n = Math.floor(n / 128); if (n) x |= 128; b.push(x); } while (n); return b; }
function sleb(n) { const b = []; let more; do { let x = n & 127; n >>= 7; more = !((n === 0 && !(x & 64)) || (n === -1 && (x & 64))); if (more) x |= 128; b.push(x); } while (more); return b; }
function activeDataMutant(bytes, address) {
  const m = inspect(bytes), section = m.sections.find(s => s.id === 11), segment = m.data[0];
  const payload = Buffer.concat([bytes.subarray(section.payload, segment.flagPosition), Buffer.from([0, 0x41, ...sleb(address), 0x0b]), bytes.subarray(segment.flagPosition + 1, section.end)]);
  return Buffer.concat([bytes.subarray(0, section.start), Buffer.from([11, ...uleb(payload.length)]), payload, bytes.subarray(section.end)]);
}
function startWorker(data) {
  const w = new Worker(new URL('./worker.mjs', import.meta.url), { workerData: data });
  let readyResolve, readyReject, doneResolve, doneReject, finished = false;
  const ready = new Promise((resolve, reject) => { readyResolve = resolve; readyReject = reject; });
  const done = new Promise((resolve, reject) => { doneResolve = resolve; doneReject = reject; });
  done.catch(() => {});
  const fail = e => { clearTimeout(timer); readyReject(e); doneReject(e); };
  const timer = setTimeout(() => { fail(Error('supervisor Worker deadline expired')); w.terminate(); }, 5000);
  w.on('message', m => {
    if (m.kind === 'parked') readyResolve(m);
    else if (m.kind === 'done') { finished = true; clearTimeout(timer); doneResolve(m); }
    else if (m.kind === 'error') fail(Error(m.error));
  });
  w.on('error', fail);
  w.on('exit', code => { if (!finished) fail(Error(`Worker exited before completion: ${code}`)); });
  return { ready, done, terminate: () => { clearTimeout(timer); return w.terminate(); } };
}
async function isolation(kernel, emitted, metadata, map, mutantStack = false) {
  const memory = new WebAssembly.Memory({ initial: 2, maximum: 16, shared: true });
  const main = instantiate(kernel, emitted, memory, metadata);
  const words = new Uint32Array(memory.buffer);
  const dataIndex = main.kernel.exports.data_sentinel.value / 4, bssIndex = main.kernel.exports.bss_sentinel.value / 4;
  assert.equal(words[dataIndex], 0x11223344); assert.equal(words[bssIndex], 0);
  words[dataIndex] = 0x55667788; words[bssIndex] = 0x99aabbcc;
  const workers = [];
  try {
    for (let i = 0; i < 2; i++) {
      const worker = startWorker({ kernel, emitted, memory, metadata, plan: map.workers[i], token: 1001 + i,
        ...(mutantStack && i === 1 ? { mutantStackTop: map.workers[0].stack.end } : {}) });
      workers.push(worker);
      await worker.ready; // First C activation is live before the next Worker is installed.
      assert.equal(words[dataIndex], 0x55667788, 'late Worker replayed shared .data');
      assert.equal(words[bssIndex], 0x99aabbcc, 'late Worker replayed BSS writes');
    }
    for (let i = 0; i < workers.length; i++) {
      const at = (map.workers[i].tcr.start + 76) / 4;
      Atomics.store(words, at, 1); Atomics.notify(new Int32Array(memory.buffer), at);
    }
    const results = await Promise.all(workers.map(w => w.done));
    return { observations: results.map(r => r.observation), stackPointers: results.map(r => r.stackPointer),
      sentinels: [words[dataIndex], words[bssIndex]] };
  } finally { await Promise.all(workers.map(w => w.terminate())); }
}

let kernel, emitted, metadata, map, adapter;
try {
  kernel = buildKernel('kernel');
  metadata = preflight(kernel, contract); map = planMemory(metadata, contract);
  json('linked-metadata.json', metadata); json('memory-ownership.json', map);
  emitted = buildWat('emitted', fs.readFileSync(path.join(here, 'emitted.wat'), 'utf8'));
  adapter = buildWat('adapter', adapterWat());
  const slotCheck = instantiate(kernel, emitted, new WebAssembly.Memory({ initial: 2, maximum: 16, shared: true }), metadata);
  const slot = slotCheck.kernel.exports.pointer_slot();
  assert.ok(metadata.reservedSlots.includes(slot));
  assert.equal(slotCheck.table.get(slot)(25), 42); assert.equal(slotCheck.kernel.exports.call_pointer(25), 42);
  record('S0-LL13-c', 'Final imports, passive initialization, linker stack/TLS ranges and actual C pointer reservation validated', { slot });
  const normal = await isolation(kernel, emitted, metadata, map);
  assertIsolation(normal.observations, map.workers.slice(0, 2));
  assert.deepEqual(normal.stackPointers, map.workers.slice(0, 2).map(w => w.stack.end));
  json('concurrent-C-calls.json', normal);
  record('S0-LL13-c', 'Concurrent live C frames use distinct owned stacks/TCRs; late instances preserve mutated .data/BSS');
  const badMap = structuredClone(map); badMap.regions[2].start = badMap.regions[1].start;
  reject('S0-LL13-c', 'overlapping ownership metadata', () => validateMap(badMap, 131072), /overlap|ownership/);
  const badInit = activeDataMutant(kernel, metadata.exportedGlobals.data_sentinel.value);
  fs.writeFileSync(path.join(out, 'quarantine/active-initialization.wasm'), badInit);
  reject('S0-LL13-c', 'active initialization in late-Worker module', () => preflight(badInit, contract), /active shared initialization/);
  const sharedStack = await isolation(kernel, emitted, metadata, map, true);
  json('quarantine/shared-stack-observations.json', sharedStack);
  reject('S0-LL13-c', 'shared C stack backing region', () => assertIsolation(sharedStack.observations, map.workers.slice(0, 2)), /owned stack|locals overwritten|alias/);
  const sharedTcrKernel = buildKernel('quarantine/shared-tcr', ['MUTANT_SHARED_TCR']);
  const sharedTcrMetadata = preflight(sharedTcrKernel, contract), sharedTcrMap = planMemory(sharedTcrMetadata, contract);
  const sharedTcr = await isolation(sharedTcrKernel, emitted, sharedTcrMetadata, sharedTcrMap);
  json('quarantine/shared-tcr-observations.json', sharedTcr);
  reject('S0-LL13-c', 'shared current-TCR global', () => assertIsolation(sharedTcr.observations, sharedTcrMap.workers.slice(0, 2)), /current TCR changed/);
  buildKernel('quarantine/unresolved', ['MUTANT_UNRESOLVED'], true);
  negativeControls.push({ name: 'unapproved compiler/helper import', obligation: 'S0-LL13-c', status: 'REJECTED', quarantine: true });
  // Real object-file type conflict: --fatal-warnings must reject LLD's
  // signature-mismatch path rather than quietly supplying a trapping stub.
  const caller = path.join(out, 'quarantine/signature-caller');
  const callee = path.join(out, 'quarantine/signature-callee');
  fs.writeFileSync(caller + '.c', 'extern int target(int, int); int use_target(void) { return target(1, 2); }\n');
  fs.writeFileSync(callee + '.c', 'int target(int x) { return x; }\n');
  for (const stem of [caller, callee]) command(clang, ['--target=wasm32-unknown-unknown', '-ffreestanding', '-c', stem + '.c', '-o', stem + '.o']);
  const mismatch = command(ld, ['--no-entry', '--export-all', '--fatal-warnings', caller + '.o', callee + '.o',
    '-o', path.join(out, 'quarantine/signature-mismatch.wasm')], { expectedFailure: true, reason: 'function signature mismatch must fail linking' });
  assert.match(mismatch.stderr, /signature mismatch/i);
  negativeControls.push({ name: 'C link signature mismatch', obligation: 'S0-LL13-c', status: 'REJECTED', quarantine: true });
  record('S0-LL13-c', 'Ownership/initialization/stack/TCR/import mutants rejected');
} catch (error) {
  report.setup_failure = error.stack;
  json('setup-failure.json', { error: error.stack });
}

function boundaryCase(adapterBytes, mode, restart, count, emittedBytes = emitted) {
  const memory = new WebAssembly.Memory({ initial: 2, maximum: 16, shared: true });
  const state = instantiate(kernel, emittedBytes, memory, metadata), plan = map.workers[0];
  setup(state, memory, plan, metadata);
  const a = new WebAssembly.Instance(new WebAssembly.Module(adapterBytes), { env: { memory }, kernel: state.kernel.exports, emitted: state.emitted.exports });
  const words = new Uint32Array(memory.buffer), signed = new Int32Array(memory.buffer), t = plan.tcr.start / 4;
  const checkpoints = [plan.lisp.start + 512, 7, plan.lisp.start + 32, plan.lisp.start + 528, plan.lisp.start + 1024];
  const values = [4, -28, 44, 129, 0, 2147483644];
  words[16] = 65; words[17] = 65; signed[32] = -28; signed[33] = 44;
  signed.set(values.slice(0, count), plan.lisp.start / 4);
  words.set([0, 2, 129, 8], checkpoints[0] / 4);
  checkpoints.forEach((v, i) => { words[t + 6 + i] = v; });
  words[t + 11] = count; words[t + 12] = plan.lisp.start; words[t + 13] = plan.lisp.start + 32;
  const beforeSp = state.kernel.exports.__stack_pointer.value;
  const returned = a.exports.outer(mode, restart);
  const after = checkpoints.map((_, i) => words[t + 6 + i]);
  const result = { mode, restart, count, returned, beforeSp, afterSp: state.kernel.exports.__stack_pointer.value,
    checkpointsBefore: checkpoints, checkpointsAfter: after, postExitEffects: words[t + 5], cleanupEffects: words[t + 20],
    catchReason: words[t + 21], observedCFrame: words[t + 22], allValues: Array.from(signed.slice(plan.lisp.start / 4, plan.lisp.start / 4 + count)),
    descriptor: [words[t + 11], words[t + 12], words[t + 13]] };
  // This is the same complete oracle for valid and deliberately broken adapters.
  const check = () => {
    assert.equal(result.afterSp, result.beforeSp, 'C stack pointer not restored after exit');
    assert.deepEqual(result.checkpointsAfter, checkpoints, 'root/binding/explicit-stack checkpoint not restored');
    assert.ok(result.observedCFrame >= plan.stack.start && result.observedCFrame < beforeSp - 128, 'nested C frames did not execute');
    assert.equal(result.postExitEffects, mode ? 0 : 2, 'post-exit C effects or missing normal effects');
    assert.equal(result.cleanupEffects, mode ? 1 : 0, 'cleanup did not execute exactly once');
    assert.deepEqual(result.allValues, values.slice(0, count), 'complete ordered multiple values lost');
    assert.deepEqual(result.descriptor, [count, plan.lisp.start, plan.lisp.start + 32], 'result-region ownership changed');
    const propagated = mode && restart;
    assert.deepEqual(returned, propagated ? [restart === 1 ? -101 : -102, 0] : [count ? values[0] : 65, count]);
    assert.equal(result.catchReason, propagated ? restart : 0, 'wrong exit/cleanup tag path');
    // Re-enter C only after the original activation has been restored.
    assert.equal(state.kernel.exports.call_pointer(25), 42);
    assert.equal(state.kernel.exports.__stack_pointer.value, beforeSp);
  };
  return { result, check };
}

if (!report.setup_failure) {
  try {
    const observations = [];
    for (const count of [0, 1, 6]) for (const [mode, restart] of [[0, 0], [1, 0], [1, 1], [1, 2]]) {
      const { result, check } = boundaryCase(adapter, mode, restart, count); check(); observations.push(result);
    }
    json('C-boundary-cases.json', observations);
    record('S0-LL19-b', '12 normal/handled/rethrown/cleanup-transfer cases preserve zero/one/six values, C SP and all checkpoints', { cases: observations.length });
    const noSp = buildWat('quarantine/no-stack-restore', adapterWat({ omitStackRestore: true }));
    const badSp = boundaryCase(noSp, 1, 0, 6); json('quarantine/no-stack-restore.json', badSp.result);
    reject('S0-LL19-b', 'omitted exceptional C-stack restoration', badSp.check, /C stack pointer not restored/);
    const noRoot = buildWat('quarantine/no-root-restore', adapterWat({ omitRootRestore: true }));
    const badRoot = boundaryCase(noRoot, 1, 0, 6); json('quarantine/no-root-restore.json', badRoot.result);
    reject('S0-LL19-b', 'omitted root-head restoration', badRoot.check, /checkpoint not restored/);
    const noThrowSource = fs.readFileSync(path.join(here, 'emitted.wat'), 'utf8').replace('(throw $exit (local.get $tcr))', '(nop)');
    const noThrow = buildWat('quarantine/omitted-throw', noThrowSource);
    const badTransfer = boundaryCase(adapter, 1, 0, 6, noThrow);
    json('quarantine/omitted-throw.json', badTransfer.result);
    reject('S0-LL19-b', 'omitted nonlocal transfer', badTransfer.check, /post-exit C effects/);
    record('S0-LL19-b', 'Omitted C-SP and root restoration mutants rejected by the same complete boundary oracle');
  } catch (error) { json('boundary-failure.json', { error: error.stack }); checks['S0-LL19-b'].push({ status: 'FAIL', error: error.stack }); }
}

json('negative-controls.json', negativeControls);
function files(dir = out, prefix = '') { return fs.readdirSync(dir, { withFileTypes: true }).flatMap(e => e.isDirectory() ? files(path.join(dir, e.name), prefix + e.name + '/') : [prefix + e.name]); }
const role = name => name.startsWith('quarantine/') ? 'negative_control' : name.startsWith('source/') ? 'test' : name.endsWith('.wasm') || name.endsWith('.o') ? 'implementation' : name.endsWith('.map') || name.endsWith('.disassembly.txt') ? 'link_metadata' : 'log';
const allFiles = files();
const artifacts = allFiles.map(name => ({ path: name, role: role(name), sha256: fileSha(path.join(out, name)) }));
artifacts.push({ path: 'source/contract.json', role: 'schema', sha256: fileSha(path.join(out, 'source/contract.json')) });
for (const id of Object.keys(checks)) {
  const status = report.setup_failure || checks[id].some(c => c.status === 'FAIL') || !checks[id].length ? 'FAIL' : 'PASS';
  report.results.push({ id, variant: 'full', status, evidence_kind: 'HAND-BUILT WASM EXECUTION', source_revision: revision,
    test_revision: sha(Buffer.from(JSON.stringify(sourceFiles))), toolchain: tools, engine: `Node ${process.version} / V8 ${process.versions.v8}`,
    timestamp: new Date().toISOString(), command: `node tests/wasm/stage0/runtime-boundary/run.mjs --output ${out}`,
    configuration: { optimization: 'O1', profile: 'shared wasm32', exception_encoding: 'final try_table/throw', contract_version: 1 }, seed: 0,
    substitutions: [], skips: [], review_disposition: 'NOT_REVIEWED',
    assertions: [{ id: id + ':contract', status }], checks: checks[id], artifacts });
  console.log(`${status} ${id}`);
}
json('execution-results.json', report);
const binding = spawnSync('python3', [path.join(repo, 'doc/WASM/tools/bind-evidence.py'),
  '--results', path.join(out, 'execution-results.json'), '--inventory', path.join(out, 'inventory.json'),
  '--output', path.join(out, 'results.json'), '--fresh'], {cwd:repo,encoding:'utf8',timeout:30000});
if(binding.error || binding.status !== 0) throw Error('evidence binding failed: ' + (binding.stderr || binding.error));
console.log(`Evidence: ${out}; full Stage 0 remains incomplete.`);
process.exitCode = report.results.some(r => r.status !== 'PASS') ? 1 : 0;
