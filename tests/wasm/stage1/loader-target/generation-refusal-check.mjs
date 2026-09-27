// Exercise the file-service boundary with real archive reservations/publication.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {bundleNamespace, targetLoadSession} from '../../../../runtime/wasm32/target-load-session.mjs';
import {encodeTargetContainer} from '../../../../runtime/wasm32/target-bundle.mjs';
import {serviceRequest} from '../../../../runtime/wasm32/file-host.mjs';
import {sha256} from '../../../../runtime/wasm32/sha256.mjs';

const [fixture, archiveDir] = process.argv.slice(2);
const read = name => JSON.parse(fs.readFileSync(fixture + '/' + name));
const bytes = fs.readFileSync(archiveDir + '/smoke.wasm');
const manifest = JSON.parse(fs.readFileSync(archiveDir + '/smoke.json'));
const path = '/ccl/test.w32fsl', payload = new Uint8Array([7, 11, 19, 23]);
const container = encodeTargetContainer({units: manifest.units.map(u => u.name),
  archive_sha256: sha256(bytes), fasl: payload});
const invalidPath = '/ccl/invalid.w32fsl';
const invalidContainer = encodeTargetContainer({units: ['absent-unit'], archive_sha256: sha256(bytes), fasl: payload});
const files = [{path, bytes: container, sha256: sha256(container)},
  {path: invalidPath, bytes: invalidContainer, sha256: sha256(invalidContainer)}];
const host = bundleNamespace({files}).session(), handles = new Set();
let posts = 0, opens = 0;
const memory = new WebAssembly.Memory({initial: 32, maximum: 32769, shared: true});
const tcr = 1024, registry = 4096, args = 131072, view = new DataView(memory.buffer);
const get = p => view.getUint32(p, true), put = (p, v) => view.setUint32(p, v, true);
const env = {memory, tcr, code_registry: registry,
  table: new WebAssembly.Table({element: 'anyfunc', initial: 256}),
  tail_table: new WebAssembly.Table({element: 'anyfunc', initial: 256}),
  call_error: new WebAssembly.Tag({parameters: ['i32']}),
  type_error: new WebAssembly.Tag({parameters: ['i32', 'i32']}),
  nonlocal_exit: new WebAssembly.Tag({parameters: ['i32']})};
put(registry, 256); put(registry + 4, 1);
for (const [offset, value] of [[32, 2], [8, 1], [64, args], [68, args], [72, args + 256]]) put(tcr + offset, value);
let nextRoot = 65536, nextObject = 393216;
const roots = new Set(), owner = {atSafepoint: run => run(owner), reserveRootBlock: n => {
  const base = nextRoot; nextRoot += 4 * n;
  return {base, count: n, commit() {}, release() { nextRoot = base; },
    register: cells => cells.forEach(p => roots.add(p)), unregister: cells => cells.forEach(p => roots.delete(p))};
}};
const allocate = n => { const p = nextObject; nextObject += Math.ceil(n / 8) * 8; return p; };
function encode(value, vector = false) {
  if (value === null) return 77825;
  if (Number.isInteger(value)) return value * 4;
  if (typeof value === 'string') {
    const chars = Array.from(value), p = allocate(4 + 4 * chars.length); put(p, chars.length * 256 + 191);
    chars.forEach((ch, i) => put(p + 4 + 4 * i, ch.codePointAt(0))); return p + 6;
  }
  assert(Array.isArray(value));
  if (vector || !value.length) {
    const p = allocate(4 + 4 * value.length); put(p, value.length * 256 + 250);
    value.forEach((v, i) => put(p + 4 + 4 * i, encode(v))); return p + 6;
  }
  let tail = 77825;
  for (let i = value.length - 1; i >= 0; i--) { const p = allocate(8); put(p, tail); put(p + 4, encode(value[i])); tail = p + 1; }
  return tail;
}
const unexpected = () => { throw Error('unexpected capability'); };
const loader = await targetLoadSession({files, archives: [{bytes, manifest, digest: sha256(bytes)}],
  memory, env, owner, versions: read('versions.json'), policy: read('policy.json'), nextCode: 16, nextSlot: 24,
  // Omit generations: exercise the production default of two.
  capabilities: {owner: {ensure: unexpected}, integer: {calculate: unexpected}, floating: {calculate: unexpected}},
  pinned: [{start: 393216, end: 1048576}],
  post: ({lifetime, generation}) => {
    posts++;
    assert(serviceRequest(memory, {...host,
      open(name, mode) { opens++; const fd = host.open(name, mode); handles.add(fd); return fd; },
      close(fd) { host.close(fd); handles.delete(fd); }
    }, lifetime, generation));
  }});
const pathWord = encode(path), missing = encode('/ccl/missing.w32fsl'), invalid = encode(invalidPath);
const prepare = (op, a, b = 0, c = 0) => [op * 4, a, b, c].forEach((v, i) => put(args + 4 * i, v));
const request = (...values) => { prepare(...values); return loader.file(args) >> 2; };
const open = () => request(0, pathWord), close = fd => request(3, fd * 4);
const unit = manifest.units[0], row = read('records.json').units.find(r => r.name === unit.wire);
const record = encode(row.install_record ?? row.record), symbols = encode(Array(unit.symbol_count).fill(null), true);
for (let i = 0; i < unit.symbol_count; i++) { const p = allocate(32); put(p, 1850); put(p + 28, 4); put(symbols - 2 + 4 * i, p + 6); }
const install = fd => { [record, symbols, fd * 4].forEach((v, i) => put(args + 4 * i, v)); return loader.install(args); };
const state = () => ({memory: Buffer.from(new Uint8Array(memory.buffer)), roots: [...roots], nextRoot, posts, opens,
  handles: [...handles], openFiles: loader.openFiles(), archives: loader.archives(),
  table: Array.from({length: 256}, (_, i) => env.table.get(i)),
  tail: Array.from({length: 256}, (_, i) => env.tail_table.get(i))});
const first = open(), second = open();
assert.equal(loader.archives()[0].generations, 2);
prepare(0, pathWord);
let before = state();
assert.equal(loader.file(args), -12 * 4, 'overlapping third open returns tagged ENOMEM');
assert.deepEqual(state(), before, 'refusal preserves all memory, tables, roots and handles');
close(second);
const reused = open(); assert.equal(loader.archives()[0].generations, 2);
const code1 = install(first), code2 = install(reused); assert.notEqual(code1, code2);
close(first); close(reused);
for (let i = 0; i < 2; i++) {
  prepare(0, pathWord); before = state();
  assert.equal(loader.file(args), -12 * 4, 'published generations still exhaust the budget after close');
  assert.deepEqual(state(), before);
}
// A resource refusal must not bypass the file client's frame/owner checks.
prepare(0, pathWord); put(tcr + 64, args + 8); before = state();
assert.throws(() => loader.file(args), /thread state/); assert.deepEqual(state(), before); put(tcr + 64, args);
assert.equal(request(0, missing), -2, 'missing-file errno remains available');
assert.equal(request(0, pathWord, 4), -30, 'write refusal remains READ_ONLY');
prepare(0, invalid); before = state();
assert.throws(() => loader.file(args), /code archive: UNIT/, 'unrelated admission errors are not translated');
assert.deepEqual(state(), before);
assert.deepEqual(loader.openFiles(), []); assert.deepEqual([...handles], []);
assert.deepEqual(loader.closeSessions(), []);
console.log(JSON.stringify({status: 'PASS', generations: 2, publishedCodeIds: [code1 / 4, code2 / 4],
  checks: ['default budget', 'overlap ENOMEM', 'refusal preserves state', 'partial close reuses generation',
    'published generations persist', 'repeat ENOMEM', 'thread validation precedes capacity refusal',
    'missing file', 'read-only file', 'unrelated admission error preserved', 'no leaked handles or sessions']}));
