// Exercise moving bundle imports and heap enumeration with the real collector.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {CollectorOwner} from '../../../../runtime/wasm32/collector-owner.mjs';
import {allocationService, collectionInhibitionService, heapSnapshotService, objectValidityService} from '../../../../runtime/wasm32/allocation-service.mjs';
import {sha256} from '../../../../runtime/wasm32/sha256.mjs';

const bytes = fs.readFileSync(process.argv[2]), digest = sha256(bytes);
const N = 77825, tcr = 1024, root = 131064, external = 262144;
const a = 2097152, b = a + 65536, rows = [];
let memory, owner;
const get = p => new DataView(memory.buffer).getUint32(p, true);
const put = (p, value) => new DataView(memory.buffer).setUint32(p, value, true);
function setup({rootListSize = 4096, scratchSize = 600000, maximumPages = 32769,
  engineMaximumPages = 32769, runtimeGlobals = true, enumerableImage = true} = {}) {
  memory = new WebAssembly.Memory({initial: 48, maximum: engineMaximumPages, shared: true});
  const regions = [['tcr', tcr, tcr + 256], ['image', 77824, 77864],
    ['image', 786432, 786448], ['vstack', root, root + 32776],
    ['temp', 196608, 212992], ['control', 212992, 229376],
    ['external', external, external + 4096], ['bindings', 266240, 270336],
    ...(runtimeGlobals ? [['runtime-globals', 270336, 270352]] : []),
    ['c-stack', 1048576, 1114112], ['root-list', 1180000, 1180000 + rootListSize],
    ['scratch', 1200000, 1200000 + scratchSize]]
    .map(([role, start, end], i) => ({name: role + '-' + i, role, start, end}));
  regions.find(r => r.start === 786432).enumerable = enumerableImage;
  const layout = {version: 1, collector: 'copying', workers: 1, egc: false,
    tcr, maximumPages, logCapacity: 32768, regions,
    spaces: [a, b].map((start, i) => ({name: 'heap-' + i, start, end: start + 65536})),
    groups: ['module-constants', 'callbacks', 'registry', 'host']
      .map((kind, i) => ({kind, slots: [external + i * 4]}))};
  put(N - 1, N); put(N + 3, N); put(77832, 1850);
  for (let i = 1; i < 8; i++) put(77832 + i * 4, N);
  put(786432, 762); put(786436, N); put(786440, N);
  put(270336, 1);
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
  const inhibition = [owner.collectionInhibition, owner.collectionPending];
  assert.throws(action, pattern);
  assert.deepEqual(new Uint8Array(memory.buffer), before);
  assert.deepEqual([owner.collectionInhibition, owner.collectionPending], inhibition);
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
setup();
refusal('inhibition outside boundary', () => owner.inhibitCollection(1), /legal owner boundary/);
owner.atSafepoint(o => {
  refusal('inhibition operation', () => o.inhibitCollection(0), /inhibition operation/);
  refusal('unmatched inhibition release', () => o.inhibitCollection(-1), /inhibition depth/);
  const value = cons(168), roots = o.rootCells([value]);
  assert.equal(o.inhibitCollection(1), 1);
  const locked = roots.values()[0], count = o.collectionCount;
  assert.equal(o.inhibitCollection(1), 2);
  assert.deepEqual(o.ensure(8), {collected: false, grown: false});
  assert.deepEqual(o.collect(), {deferred: true});
  assert(o.collectionPending);
  assert.equal(o.collectionCount, count);
  assert.deepEqual(o.ensure(65536), {collected: false, grown: true, deferred: true});
  assert.equal(roots.values()[0], locked);
  assert.equal(o.collectionCount, count);
  assert.equal(o.inhibitCollection(-1), -1);
  assert.equal(o.inhibitCollection(1), -2);
  assert.equal(o.inhibitCollection(-1), -1);
  assert.equal(o.inhibitCollection(-1), 0);
  assert.equal(o.collectionCount, count + 1);
  assert(!o.collectionPending);
  assert.notEqual(roots.values()[0], locked);
  assert.equal(get(roots.values()[0] + 3), 168);
  // The second semispace is now active at the end of memory. Exercise growth
  // from it as well as absorbing the adjacent inactive space in the first run.
  assert.equal(o.inhibitCollection(1), 1);
  const second = roots.values()[0], secondCount = o.collectionCount;
  assert.deepEqual(o.ensure(131072), {collected: false, grown: true, deferred: true});
  assert.equal(roots.values()[0], second);
  assert.equal(o.collectionCount, secondCount);
  assert.equal(o.inhibitCollection(-1), 0);
  assert.equal(o.collectionCount, secondCount + 1);
  assert.equal(get(roots.values()[0] + 3), 168);
  roots.release(); pass('inhibited allocation grows without movement; final release performs deferred collection');

});
setup();
owner.atSafepoint(o => {
  put(270340, 536870911);
  refusal('inhibition overflow', () => o.inhibitCollection(1), /inhibition depth/);
});
for (const [offset, value] of [[0, 0], [4, 536870912], [8, 2], [12, 1]]) {
  setup(); put(270336 + offset, value);
  const before = new Uint8Array(memory.buffer).slice();
  owner.atSafepoint(o => assert.throws(() => o.inhibitCollection(1), /inhibition state/));
  assert.deepEqual(new Uint8Array(memory.buffer), before);
  pass('inhibition metadata ' + offset);
}
setup(); put(270344, 1);
owner.atSafepoint(o => assert.throws(() => o.inhibitCollection(1), /inhibition state/));
pass('pending collection requires an active inhibitor');
setup({maximumPages: 48});
owner.atSafepoint(o => refusal('first lock cannot relocate beyond budget', () => o.inhibitCollection(1), /growth maximum/));
setup({maximumPages: 52});
owner.atSafepoint(o => {
  o.inhibitCollection(1);
  refusal('inhibited growth cannot exceed budget', () => o.ensure(262144), /heap growth maximum/);
  assert.equal(o.inhibitCollection(-1), 0);
});
setup();
const callError = new WebAssembly.Tag({parameters: ['i32']});
assert.throws(() => collectionInhibitionService({}, callError), TypeError);
assert.throws(() => collectionInhibitionService(owner, {}), TypeError);
pass('inhibition service capabilities');
const inhibit = collectionInhibitionService(owner, callError);
assert.throws(() => inhibit(-1), e => e.is?.(callError) && e.getArg(callError, 0) === 11);
pass('Lisp inhibition metadata refusal is checked 11');
setup({maximumPages: 48});
const exhausted = collectionInhibitionService(owner, callError);
assert.throws(() => exhausted(1), e => e.is?.(callError) && e.getArg(callError, 0) === 6);
pass('Lisp inhibition allocation refusal is checked 6');
setup({maximumPages: 52, engineMaximumPages: 48});
const engineExhausted = collectionInhibitionService(owner, callError);
const engineBefore = new Uint8Array(memory.buffer).slice();
assert.throws(() => engineExhausted(1), e => e.is?.(callError) && e.getArg(callError, 0) === 6);
assert.deepEqual(new Uint8Array(memory.buffer), engineBefore);
pass('engine growth refusal is checked 6 before inhibition publication');
setup({scratchSize: 16384, maximumPages: 55});
owner.atSafepoint(o => {
  const roots = o.rootCells([cons(44)]), before = new Uint8Array(memory.buffer).slice(), spaces = o.spaces;
  assert.throws(() => o.inhibitCollection(1), /heap growth maximum/);
  assert(memory.buffer.byteLength > before.length);
  assert.deepEqual(new Uint8Array(memory.buffer, 0, before.length), before);
  assert.deepEqual(o.spaces, spaces);
  assert.deepEqual([o.collectionInhibition, o.collectionPending], [0, false]);
  assert.equal(get(roots.values()[0] + 3), 44);
  roots.release(); pass('first-lock budget refusal may reserve scratch but preserves Lisp state');
});
setup({runtimeGlobals: false});
const absent = collectionInhibitionService(owner, callError);
assert.throws(() => absent(1), e => e.is?.(callError) && e.getArg(callError, 0) === 11);
owner.atSafepoint(o => {
  const roots = o.rootCells([cons(44)]);
  o.ensure(8); o.collect();
  assert.equal(get(roots.values()[0] + 3), 44);
  roots.release();
});
pass('layouts without runtime globals collect normally and refuse inhibition with checked 11');
setup();
owner.atSafepoint(o => {
  o.inhibitCollection(1); memory.grow(1);
  refusal('external growth loses inhibited heap ownership', () => o.ensure(65544), /inhibited heap ownership/);
});
setup();
const finalRelease = collectionInhibitionService(owner, callError);
finalRelease(1);
let deferredFailure;
owner.atSafepoint(o => {
  const value = cons(44), roots = o.rootCells([value]);
  put(value - 1, 31); // Invalid live header; deferred collection has not inspected it.
  o.collect();
  const heap = new Uint8Array(memory.buffer, get(tcr + 56), get(tcr + 48) - get(tcr + 56)).slice();
  const metadata = new Uint8Array(memory.buffer, tcr, 256).slice(), count = o.collectionCount;
  roots.release();
  // Leave a root in a registered slot for the deferred collector.
  put(external, value);
  deferredFailure = {heap, metadata, count, value};
});
assert.throws(() => finalRelease(-1), e => e.is?.(callError) && e.getArg(callError, 0) === 11);
assert.deepEqual([owner.collectionInhibition, owner.collectionPending], [0, false]);
assert.equal(owner.collectionCount, deferredFailure.count);
assert.deepEqual(new Uint8Array(memory.buffer, tcr, 256), deferredFailure.metadata);
assert.deepEqual(new Uint8Array(memory.buffer, get(tcr + 56), get(tcr + 48) - get(tcr + 56)), deferredFailure.heap);
assert.equal(get(external), deferredFailure.value);
pass('failed deferred collection releases inhibition and preserves the uncollected Lisp heap');
setup();
const snapshot = heapSnapshotService(owner, callError);
assert.throws(() => heapSnapshotService({}, callError), TypeError);
assert.throws(() => heapSnapshotService(owner, {}), TypeError);
assert.throws(() => snapshot(4), e => e.is?.(callError) && e.getArg(callError, 0) === 11);
owner.atSafepoint(o => {
  o.inhibitCollection(1);
  const values = Array.from({length: 8192}, (_, i) => cons(i * 4)), count = o.collectionCount;
  const result = o.heapSnapshot(1), held = o.rootCells([result]);
  assert.deepEqual(vector(result), values);
  assert.equal(o.collectionCount, count);
  assert(o.collectionPending);
  assert.equal(o.inhibitCollection(-1), 0);
  assert.equal(o.collectionCount, count + 1);
  assert.deepEqual(vector(held.values()[0]).map(p => get(p + 3)), values.map((_, i) => i * 4));
  held.release();
});
pass('heap snapshot grows without movement under inhibition and roots its objects after release');
setup({maximumPages: 51});
owner.atSafepoint(o => { o.inhibitCollection(1); for (let i = 0; i < 8192; i++) cons(i * 4); });
assert.throws(() => heapSnapshotService(owner, callError)(1), e => e.is?.(callError) && e.getArg(callError, 0) === 6);
pass('heap snapshot growth refusal is checked 6');
setup(); put(270336, 0);
assert.throws(() => allocationService(owner, callError)(65544), e => e.is?.(callError) && e.getArg(callError, 0) === 11);
pass('allocation inhibition corruption is checked 11');
for (const [name, mask, corrupt, pattern] of [
  ['dynamic unknown header', 1, () => { put(a, 31); put(tcr + 48, a + 8); }, /heap snapshot kind/],
  ['dynamic node extent', 1, () => { put(a, 4 * 256 + 250); put(tcr + 48, a + 8); }, /heap snapshot extent/],
  ['dynamic byte extent', 1, () => { put(a, 9 * 256 + 199); put(tcr + 48, a + 8); }, /heap snapshot extent/],
  ['image unknown header', 2, () => put(786432, 31), /heap snapshot kind/],
  ['image node extent', 2, () => put(786432, 4 * 256 + 250), /heap snapshot extent/],
  ['unowned allocation metadata', 1, () => put(tcr + 48, a - 8), /allocation ownership/]
]) {
  setup(); corrupt();
  owner.atSafepoint(o => refusal(name, () => o.heapSnapshot(mask), pattern));
}
// After ensure(), GC can only remove or move the enumerated objects. It cannot
// increase their count; capacity is a defensive invariant of this synchronous
// owner boundary, not an independently admitted caller-controlled clause.
setup();
refusal('validity outside boundary', () => owner.validObject(N), /legal owner boundary/);
owner.atSafepoint(o => {
  for (const value of [-1, 2 ** 32, 1.5, NaN])
    refusal('invalid object word ' + value, () => o.validObject(value), /object word/);
  const x = cons(168), roots = o.rootCells([x]);
  const before = new Uint8Array(memory.buffer).slice();
  for (const value of [0, 4, 0xfffffffc, 11, 83, N, 77838, 786438, x])
    assert(o.validObject(value), String(value));
  for (const value of [2, 5, 7, x + 5, 786433, 786446, a + 9, b + 1,
    external + 1, memory.buffer.byteLength + 6, 0xfffffffe])
    assert(!o.validObject(value), String(value));
  assert.deepEqual(new Uint8Array(memory.buffer), before);
  o.collect();
  assert(o.validObject(roots.values()[0])); assert(!o.validObject(x));
  roots.release(); pass('validity checks immediate tags, owner areas, object boundaries and movement without writes');
});
// Each admitted family has its actual allocation extent, including padding.
for (const [kind, n, raw] of [[10, 2, 8], [26, 2, 8], [42, 6, 24], [42, 7, 28],
  [50, 4, 16], [50, 7, 28], [58, 7, 28], [66, 6, 24], [74, 16, 64], [82, 1, 4],
  [90, 3, 12], [98, 8, 32], [106, 2, 8], [114, 2, 8], [122, 2, 8], [130, 1, 4],
  [234, 5, 20], [242, 5, 20], [250, 0, 0], [7, 1, 4], [15, 1, 4], [23, 3, 12],
  [71, 3, 12], [79, 5, 20], ...[159, 167, 175, 183, 191].map(k => [k, 3, 12]),
  [199, 9, 9], [207, 9, 9], [215, 3, 6], [223, 3, 6], [231, 2, 20], [239, 2, 20],
  [247, 1, 20], [255, 17, 3]]) {
  setup(); put(a, n * 256 + kind);
  const extent = Math.ceil((4 + raw) / 8) * 8; put(tcr + 48, a + extent);
  owner.atSafepoint(o => {
    const before = new Uint8Array(memory.buffer).slice();
    assert(o.validObject(a + 6)); assert(!o.validObject(a + 1));
    if (extent > 8) assert(!o.validObject(a + 14));
    assert.deepEqual(new Uint8Array(memory.buffer), before);
  });
}
pass('validity covers every admitted node and raw object family');
for (const [kind, n] of [[31, 1], [42, 5], [130, 0], [98, 7], [90, 2], [82, 0],
  [66, 5], [50, 6], [74, 15], [234, 4], [242, 6], [7, 0], [15, 2], [23, 2],
  [71, 2], [79, 4], [250, 3], [199, 9]]) {
  setup(); put(a, n * 256 + kind); put(tcr + 48, a + 8);
  owner.atSafepoint(o => { const before = new Uint8Array(memory.buffer).slice();
    assert(!o.validObject(a + 6)); assert.deepEqual(new Uint8Array(memory.buffer), before); });
}
pass('validity rejects unsupported shapes and truncated extents without writes');
setup();
owner.atSafepoint(o => {
  const p = root + 8; put(p, 1578); put(tcr + 64, p + 32);
  assert(o.validObject(p + 6)); assert(!o.validObject(p + 1));
  put(tcr + 64, p + 24); assert(!o.validObject(p + 6));
  put(tcr + 64, p + 32); put(p, 1834); assert(!o.validObject(p + 6));
  pass('validity recognizes only complete live stack callables');
});
for (const capabilities of [[{}, callError], [owner, {}]])
  assert.throws(() => objectValidityService(...capabilities), /object validity capabilities/);
setup(); put(tcr + 48, a - 8);
assert.throws(() => objectValidityService(owner, callError)(N), e => e.is?.(callError) && e.getArg(callError, 0) === 11);
pass('validity owner corruption is checked 11');
setup({enumerableImage: false});
owner.atSafepoint(o => {
  assert(!o.validObject(786438)); assert(o.validObject(N));
});
pass('validity excludes image root storage from object ownership');
for (const top of [root, root + 32784]) {
  setup(); put(tcr + 64, top);
  const before = new Uint8Array(memory.buffer).slice();
  assert.throws(() => objectValidityService(owner, callError)(external + 6),
    e => e.is?.(callError) && e.getArg(callError, 0) === 11);
  assert.deepEqual(new Uint8Array(memory.buffer), before);
}
pass('validity refuses both invalid stack frontiers without writes');
const report = {status: 'PASS', checks: rows.length, rows,
  inputs: {collector: digest, owner: sha256(fs.readFileSync(new URL('../../../../runtime/wasm32/collector-owner.mjs', import.meta.url))),
    services: sha256(fs.readFileSync(new URL('../../../../runtime/wasm32/allocation-service.mjs', import.meta.url))),
    runner: sha256(fs.readFileSync(new URL(import.meta.url)))}};
fs.writeFileSync(process.argv[3], JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report));
