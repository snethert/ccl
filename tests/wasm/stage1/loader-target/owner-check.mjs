// Exercise moving bundle imports and heap enumeration with the real collector.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {CollectorOwner} from '../../../../runtime/wasm32/collector-owner.mjs';
import {sha256} from '../../../../runtime/wasm32/sha256.mjs';

const bytes = fs.readFileSync(process.argv[2]), digest = sha256(bytes);
const N = 77825, tcr = 1024, root = 131064, external = 262144;
const a = 2097152, b = a + 65536, rows = [];
let memory, owner;
const get = p => new DataView(memory.buffer).getUint32(p, true);
const put = (p, value) => new DataView(memory.buffer).setUint32(p, value, true);
function setup({rootListSize = 4096, scratchSize = 600000} = {}) {
  memory = new WebAssembly.Memory({initial: 48, maximum: 32769, shared: true});
  const regions = [['tcr', tcr, tcr + 256], ['image', 77824, 77864],
    ['image', 786432, 786448], ['vstack', root, root + 32776],
    ['temp', 196608, 212992], ['control', 212992, 229376],
    ['external', external, external + 4096], ['bindings', 266240, 270336],
    ['c-stack', 1048576, 1114112], ['root-list', 1180000, 1180000 + rootListSize],
    ['scratch', 1200000, 1200000 + scratchSize]]
    .map(([role, start, end], i) => ({name: role + '-' + i, role, start, end}));
  const layout = {version: 1, collector: 'copying', workers: 1, egc: false,
    tcr, maximumPages: 32769, logCapacity: 32768, regions,
    spaces: [a, b].map((start, i) => ({name: 'heap-' + i, start, end: start + 65536})),
    groups: ['module-constants', 'callbacks', 'registry', 'host']
      .map((kind, i) => ({kind, slots: [external + i * 4]}))};
  put(N - 1, N); put(N + 3, N); put(77832, 1850);
  for (let i = 1; i < 8; i++) put(77832 + i * 4, N);
  put(786432, 762); put(786436, N); put(786440, N);
  for (const group of layout.groups) put(group.slots[0], N);
  for (const [offset, value] of [[48, a], [52, a + 65536], [56, a],
    [64, root + 8], [68, root + 8], [72, root + 32776], [76, 196608],
    [80, 196608], [84, 212992], [88, 212992], [92, 212992], [96, 229376],
    [104, 266240], [108, 0], [120, root + 8200], [124, root + 8264],
    [128, root], [188, N]]) put(tcr + offset, value);
  owner = CollectorOwner.create(memory, bytes, digest, layout);
}
function cons(car) {
  const p = get(tcr + 48); put(p, N); put(p + 4, car); put(tcr + 48, p + 8);
  return p + 1;
}
function vector(word) {
  const p = word - 6, n = get(p) >>> 8;
  assert.equal(get(p) & 255, 250);
  return Array.from({length: n}, (_, i) => get(p + 4 + i * 4));
}
function pass(name) { rows.push(name); }
function refusal(name, action, pattern) {
  const before = new Uint8Array(memory.buffer).slice();
  assert.throws(action, pattern);
  assert.deepEqual(new Uint8Array(memory.buffer), before);
  pass(name);
}

setup();
refusal('roots outside boundary', () => owner.rootCells([]), /legal owner boundary/);
owner.atSafepoint(o => {
  for (const value of [null, {}, [-1], [2 ** 32], [NaN], [1.5]])
    refusal('invalid root values ' + JSON.stringify(value), () => o.rootCells(value), /root values/);
  refusal('external root capacity', () => o.rootCells(Array(1021).fill(N)), /root capacity/);
  const first = cons(168), second = cons(172), roots = o.rootCells([first, first]);
  const other = o.rootCells([second]);
  assert.equal(new Set([...roots.slots, ...other.slots]).size, 3);
  o.collect();
  const moved = roots.values();
  assert.notEqual(moved[0], first); assert.equal(moved[0], moved[1]);
  assert.equal(get(moved[0] + 3), 168); assert.equal(get(other.values()[0] + 3), 172);
  roots.release();
  refusal('released root read', () => roots.values(), /released roots/);
  refusal('double release', () => roots.release(), /released roots/);
  const recycled = o.rootCells([other.values()[0]]);
  assert.equal(recycled.slots[0], roots.slots[0]);
  o.collect();
  assert.equal(recycled.values()[0], other.values()[0]);
  assert.equal(get(recycled.values()[0] + 3), 172);
  recycled.release(); other.release();
  pass('moving imports, alias identity, release and slot reuse');
});
setup({rootListSize: 64});
owner.atSafepoint(o => refusal('root list capacity', () => o.rootCells(Array(16).fill(N)), /root capacity/));

setup();
refusal('snapshot outside boundary', () => owner.heapSnapshot(1), /legal owner boundary/);
owner.atSafepoint(o => {
  for (const mask of [-1, 4, 1.5])
    refusal('snapshot mask ' + mask, () => o.heapSnapshot(mask), /heap areas/);
  const x = cons(4), y = cons(8), roots = o.rootCells([x]);
  const snapshot = o.heapSnapshot(1), held = o.rootCells([snapshot]);
  assert.deepEqual(vector(snapshot), [x, y]);
  o.collect();
  const moved = vector(held.values()[0]);
  assert.equal(moved[0], roots.values()[0]);
  assert.equal(get(moved[1] + 3), 8);
  assert.deepEqual(vector(o.heapSnapshot(2)), [N, 77838, 786438]);
  assert.deepEqual(vector(o.heapSnapshot(0)), []);
  held.release(); roots.release();
  pass('snapshot roots otherwise unreachable objects and selects areas');
});
setup({scratchSize: 16384});
owner.atSafepoint(o => {
  const roots = o.rootCells([cons(44)]), size = memory.buffer.byteLength;
  o.collect();
  assert(memory.buffer.byteLength > size);
  assert.equal(get(roots.values()[0] + 3), 44);
  roots.release(); pass('collector workspace grows before collection');
});
const report = {status: 'PASS', checks: rows.length, rows,
  inputs: {collector: digest, owner: sha256(fs.readFileSync(new URL('../../../../runtime/wasm32/collector-owner.mjs', import.meta.url))),
    runner: sha256(fs.readFileSync(new URL(import.meta.url)))}};
fs.writeFileSync(process.argv[3], JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report));
