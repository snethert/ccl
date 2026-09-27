// Focused loader test: real compiler bytes, B entry invocation, and transaction
// failures. This is not a boot0 or whole-file target-LOAD claim.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {admitTargetBundle, decodeTargetBundle, encodeTargetBundle} from '../../../../runtime/wasm32/target-bundle.mjs';
import {targetCodeService} from '../../../../runtime/wasm32/target-code-service.mjs';
import {sha256} from '../../../../runtime/wasm32/sha256.mjs';

const out = process.argv[2], read = name => JSON.parse(fs.readFileSync(out + '/' + name));
const bytes = fs.readFileSync(out + '/modules.w32bundle'), digest = sha256(bytes);
const versions = read('versions.json'), policy = read('policy.json');
const decoded = decodeTargetBundle(bytes, digest), rows = decoded.manifest.codeSet.modules;
const records = read('records.json');
const units = decoded.manifest.units.map(u => {
  const compiled = records.units.find(r => r.name === u.name);
  return {...u, record: compiled.install_record ?? compiled.record};
});
const functions = read('fixture-functions.json');
const namedUnit = name => units.find(u => functions[u.name].name?.symbol === name);
assert.deepEqual(Buffer.from(decoded.fasl), fs.readFileSync(out + '/smoke.w32fsl'));
const N = 77825, T = 77838, tcr = 1024, registry = 4096, root = 131064;
const memory = new WebAssembly.Memory({initial: 64, maximum: 32769, shared: true});
const view = new DataView(memory.buffer), get = p => view.getUint32(p, true), put = (p, n) => view.setUint32(p, n, true);
const env = {memory, tcr, code_registry: registry,
  table: new WebAssembly.Table({element: 'anyfunc', initial: 128}),
  tail_table: new WebAssembly.Table({element: 'anyfunc', initial: 128}),
  call_error: new WebAssembly.Tag({parameters: ['i32']}), type_error: new WebAssembly.Tag({parameters: ['i32', 'i32']}),
  nonlocal_exit: new WebAssembly.Tag({parameters: ['i32']})};
put(registry, 128); put(registry + 4, 1);
const slots = Object.fromEntries(rows.map((r, i) => [r.code_id, i + 32]));
const codeIds = Object.fromEntries(rows.map((r, i) => [r.code_id, i + 16]));
// Smoke arithmetic stays within fixnums. Invoking any other provider is an
// unexpected test failure, not a substitute arithmetic implementation.
const unexpected = () => { throw Error('Unexpected numeric/allocation service'); };
const capabilities = {owner: {ensure: unexpected}, integer: {calculate: unexpected}, floating: {calculate: unexpected}};
const options = {bytes, digest, env, capabilities, versions, policy, slots, codeIds,
  stableReference: word => word === N || word === T || word % 4 === 0 ||
    (word >= 393222 && word < 458752 && word % 8 === 6 && get(word - 6) === 1850)};
let nextRoot = 524288;
options.rootCells = values => {
  const start = nextRoot, cells = values.map((v, i) => { const p = start + i * 4; put(p, v); return p; });
  nextRoot += values.length * 4;
  return {slots: cells, values: () => cells.map(get), release: () => { cells.forEach(p => put(p, N)); nextRoot = start; }};
};
const state = () => ({registry: Array.from(new Uint32Array(memory.buffer, registry, 2 + 128 * 4)),
  public: Array.from({length: 128}, (_, i) => env.table.get(i)),
  tail: Array.from({length: 128}, (_, i) => env.tail_table.get(i))});
const controls = [];
function refuses(name, action, pattern) {
  const before = state(); assert.throws(action, pattern); assert.deepEqual(state(), before); controls.push(name);
}
refuses('digest', () => admitTargetBundle({...options, digest: '0'.repeat(64)}), /DIGEST/);
const truncated = bytes.subarray(0, bytes.length - 1);
refuses('truncated', () => admitTargetBundle({...options, bytes: truncated, digest: sha256(truncated)}), /TRUNCATED/);
const changed = structuredClone(decoded.manifest.codeSet);
changed.modules[0].entries[0].table = 'tail';
const wrongRole = encodeTargetBundle({codeSet: changed, units: decoded.manifest.units, fasl: decoded.fasl,
  readBytes: n => decoded.modules.get(n).bytes, readTemplate: n => decoded.modules.get(n).template});
refuses('role', () => admitTargetBundle({...options, bytes: wrongRole, digest: sha256(wrongRole)}), /ROLE/);
const session = admitTargetBundle(options);
refuses('unknown-code', () => session.install('missing', [], []), /CODE_RECORD/);
const unit = namedUnit('TARGET-LOADER-ADD-SEVEN');
assert(unit, 'compiled ADD-SEVEN unit');
const symbols = Array.from({length: unit.symbol_count}, (_, i) => {
  const p = 393216 + i * 32;
  [1850, N, N, N, N, 0, N, (i + 1) * 4].forEach((v, j) => put(p + j * 4, v));
  return p + 6;
});
refuses('record-substitution', () => session.install(unit.name, [4, unit.name], symbols), /CODE_RECORD/);
const noRoots = admitTargetBundle({...options, rootCells: undefined});
refuses('missing-root-authority', () => noRoots.install(unit.name, unit.record, symbols), /ROOT_AUTHORITY/);

// Materialize the two input arguments as ordinary D1 data and invoke the real
// service through both B adapter roles. The service must read the supplied
// record and symbol vector; passing a name alone cannot install a module.
let next = 1048576;
const allocate = n => { const p = next; next += Math.ceil(n / 8) * 8; return p; };
const literalSymbols = new Map();
function encode(value, vector = false) {
  if (value === null) return N;
  if (value === true) return T;
  if (Number.isInteger(value)) return (value * 4) >>> 0;
  if (Number.isInteger(value.character)) return value.character * 256 + 75;
  if (value.vector) return encode(value.vector, true);
  if (value.symbol) {
    const key = JSON.stringify([value.package, value.symbol]);
    if (!literalSymbols.has(key)) {
      const p = allocate(32), name = encode(value.symbol);
      [1850, name, N, N, N, 0, N, 0].forEach((v, i) => put(p + 4 * i, v));
      literalSymbols.set(key, p + 6);
    }
    return literalSymbols.get(key);
  }
  if (typeof value === 'string') {
    const chars = Array.from(value), p = allocate(4 + chars.length * 4); put(p, chars.length * 256 + 191);
    chars.forEach((c, i) => put(p + 4 + i * 4, c.codePointAt(0))); return p + 6;
  }
  assert(Array.isArray(value), 'unsupported fixture literal');
  if (vector || value.length === 0) {
    const p = allocate(4 + value.length * 4); put(p, value.length * 256 + 250);
    value.forEach((v, i) => put(p + 4 + i * 4, encode(v))); return p + 6;
  }
  let tail = N;
  for (let i = value.length - 1; i >= 0; i--) { const p = allocate(8); put(p, tail); put(p + 4, encode(value[i])); tail = p + 1; }
  return tail;
}
const input = encode(unit.record), symbolVector = encode(symbols.map(() => null), true);
symbols.forEach((v, i) => put(symbolVector - 2 + 4 * i, v));
const context = root + 8, args = context + 48;
put(tcr + 64, args); put(tcr + 128, context + 32); put(tcr + 120, root + 8200); put(tcr + 124, root + 8264);
put(args, input); put(args + 4, symbolVector);
const service = targetCodeService({memory, session});
const adapter = new WebAssembly.Instance(new WebAssembly.Module(fs.readFileSync(out + '/target-code-adapter.wasm')),
  {env, loader: {run: args => service(get(args), get(args + 4))}});
const code = codeIds[unit.root];
assert.deepEqual(adapter.exports.tail_entry(0, 2, context), [code * 4, 1]);
assert.deepEqual(adapter.exports.tail_entry(0, 2, context), [code * 4, 1]);
assert.equal(get(root + 8200), code * 4);
assert.deepEqual(session.installed(), [unit.name]);
assert.notEqual(code, slots[unit.root]);
assert.equal(get(registry + 8 + code * 16), slots[unit.root]);

// Invoke the generated ADD-SEVEN entry from the installed table. The fixture's
// D1 pool has six metadata cells followed by the actual compiler literals.
const arity = encode([1, 1, 0, null, null, null, []], true);
const pools = read('fixture-pools.json');
const debug = encode([1, null, []], true), pool = encode([null, null, 0x574153, 0, [], null, ...pools[unit.name]], true);
put(pool - 2, arity); put(pool + 2, debug);
const fn = allocate(32);
[1578, code * 4, N, 4, arity, debug, pool, 0].forEach((v, i) => put(fn + i * 4, v));
for (const [offset, value] of [[48, 3145728], [52, 3211264], [56, 3145728], [64, root + 8],
  [68, root + 8], [72, root + 32776], [76, 196608], [80, 196608], [84, 212992],
  [88, 212992], [92, 212992], [96, 229376], [104, 262144], [108, 0], [116, 0],
  [120, root + 8200], [124, root + 8264], [128, root], [188, N]]) put(tcr + offset, value);
put(root, 0); put(root + 4, 1); put(root + 8, 35 * 4);
let result;
try { result = env.table.get(slots[unit.root])(fn + 6, 1); }
catch (error) {
  if (error.is?.(env.call_error)) throw Error('generated entry: checked ' + error.getArg(env.call_error, 0));
  if (error.is?.(env.type_error)) throw Error('generated entry: type ' + error.getArg(env.type_error, 0));
  throw error;
}
assert.deepEqual(result, [42 * 4, 1]); assert.equal(get(root + 8200), 42 * 4);
// Two-argument MIN/MAX must work before their level-1 function cells exist.
// These symbol objects deliberately have no callable definitions.
const extrema = namedUnit('TARGET-LOADER-EXTREMA');
assert(extrema, 'compiled EXTREMA unit');
const extremaSymbols = Array.from({length: extrema.symbol_count}, (_, i) => symbols[i % symbols.length]);
const extremaCode = session.install(extrema.name, extrema.record, extremaSymbols);
const extremaArity = encode([1, 2, 0, null, null, null, []], true);
const extremaPool = encode([null, null, 0x574153, 0, [], null, ...pools[extrema.name]], true);
put(extremaPool - 2, extremaArity); put(extremaPool + 2, debug);
const extremaFn = allocate(32);
[1578, extremaCode * 4, N, 4, extremaArity, debug, extremaPool, 0].forEach((v, i) => put(extremaFn + 4 * i, v));
const extremaCases = read('extrema-native.json');
for (const [args, expected] of extremaCases) {
  args.forEach((v, i) => put(root + 8 + 4 * i, v * 4));
  const [first, count] = env.table.get(slots[extrema.root])(extremaFn + 6, 2);
  assert.equal(count, expected.length); assert.equal(first >> 2, expected[0]);
  assert.deepEqual(expected.map((_, i) => get(root + 8200 + 4 * i) >> 2), expected);
}
// Method entry accepts the keyword union checked by generic dispatch. Its
// source keyword vector still describes only that method's declared keys.
function keywordFunction(name) {
  const unit = namedUnit(name), metadata = functions[unit.name];
  const imports = metadata.symbols.map(s => encode(s));
  for (const i of unit.record[9] ?? []) put(imports[i] + 22, 4 * (i + 1));
  const code = session.install(unit.name, unit.record, imports);
  const arity = encode(metadata.arity, true);
  put(arity - 2 + 6 * 4, encode(metadata.arity[6], true));
  const pool = encode([null, null, 0x574153, 0, [], null, ...pools[unit.name]], true);
  put(pool - 2, arity); put(pool + 2, debug);
  const fn = allocate(32);
  [1578, code * 4, N, 4, arity, debug, pool, 0].forEach((v, i) => put(fn + i * 4, v));
  const call = args => {
    call.words = args.map(v => encode(v));
    return call.raw(call.words);
  };
  call.raw = words => {
    words.forEach((v, i) => put(root + 8 + 4 * i, v));
    return env.table.get(slots[unit.root])(fn + 6, words.length);
  };
  return call;
}
const ordinaryKeys = keywordFunction('TARGET-LOADER-ORDINARY-KEYS');
const returnValues = keywordFunction('TARGET-LOADER-VALUES');
const returnList = keywordFunction('TARGET-LOADER-VALUES-LIST');
const valuesCases = read('values-native.json');
put(tcr + 124, root + 8328); // A 32-value caller result area.
for (const [input, result] of valuesCases) {
  const args = input ?? [], expected = result ?? [];
  let returned;
  try { returned = returnValues(args); }
  catch (e) { throw Error('VALUES with ' + args.length + ' arguments: ' +
    (e.is?.(env.call_error) ? 'checked ' + e.getArg(env.call_error, 0) : String(e))); }
  const [first, count] = returned;
  assert.equal(count, expected.length);
  const words = expected.map(x => x === null ? N : x * 4);
  assert.equal(first, words[0] ?? N);
  assert.deepEqual(words.map((_, i) => get(root + 8200 + i * 4)), words);
}
const valuesRefusals = [];
for (const [name, list] of [['non-list', 68], ['unbacked cons', memory.buffer.byteLength + 1], ['improper tail', encode([1])],
  ['one-cell cycle', encode([1])], ['three-cell cycle', encode([1, 2, 3])]]) {
  if (name === 'improper tail') put(list - 1, 68);
  if (name === 'one-cell cycle') put(list - 1, list);
  if (name === 'three-cell cycle') put(get(get(list - 1) - 1) - 1, list);
  const before = new Uint8Array(memory.buffer, root + 8200, 128).slice();
  assert.throws(() => returnList.raw([list]), e => e.is?.(env.call_error) && e.getArg(env.call_error, 0) === 5);
  assert.deepEqual(new Uint8Array(memory.buffer, root + 8200, 128), before);
  valuesRefusals.push(name);
}
put(tcr + 124, root + 8264);
const tooMany = encode(Array.from({length: 32}, (_, i) => i));
const priorValues = new Uint8Array(memory.buffer, root + 8200, 64).slice();
assert.throws(() => returnList.raw([tooMany]), e => e.is?.(env.call_error) && e.getArg(env.call_error, 0) === 3);
assert.deepEqual(new Uint8Array(memory.buffer, root + 8200, 64), priorValues);
valuesRefusals.push('caller result capacity');
const assq = keywordFunction('TARGET-LOADER-ASSQ');
const assqCases = read('assq-native.json');
for (const [args, expected] of assqCases) {
  const before = [get(tcr + 48), get(tcr + 52)];
  if (expected === 'TYPE-ERROR') {
    assert.throws(() => assq(args), e => e.is?.(env.type_error),
      'native ASSQ compiler macro uses the type-error channel');
  } else {
    const [value, count] = assq(args);
    assert.equal(count, 1);
    let cursor = assq.words[1], found = N;
    while (cursor !== N) {
      const pair = get(cursor + 3);
      if (pair !== N && get(pair + 3) === assq.words[0]) { found = pair; break; }
      cursor = get(cursor - 1);
    }
    assert.equal(value, found, 'ASSQ returns the original pair');
    assert.deepEqual(found === N ? null : [get(found + 3) === N ? null : get(found + 3) >> 2,
      get(get(found - 1) + 3) >> 2], expected);
  }
  assert.deepEqual([get(tcr + 48), get(tcr + 52)], before, 'ASSQ does not allocate');
}
const badCons = memory.buffer.byteLength + 1;
const badPairList = encode([null]);
put(badPairList + 3, badCons);
for (const list of [badCons, badPairList]) {
  const before = [get(tcr + 48), get(tcr + 52), get(badPairList + 3)];
  assert.throws(() => assq.raw([4, list]),
    error => error.is?.(env.call_error) && error.getArg(env.call_error, 0) === 4,
    'ASSQ checks the extent of both the list spine and its pair');
  assert.deepEqual([get(tcr + 48), get(tcr + 52), get(badPairList + 3)], before);
}
const methodKeys = keywordFunction('TARGET-LOADER-METHOD-KEYS');
const amount = {package: 'KEYWORD', symbol: 'AMOUNT'}, other = {package: 'KEYWORD', symbol: 'OTHER'};
const keywordResults = [ordinaryKeys([40, amount, 2])[0] >> 2,
  methodKeys([null, 40, amount, 2, other, 9])[0] >> 2,
  methodKeys([null, 40, other, 9])[0] >> 2];
assert.throws(() => ordinaryKeys([40, other, 9]), e => e.is?.(env.call_error));
keywordResults.push(true);
assert.deepEqual(keywordResults, read('keyword-native.json'));
assert.throws(() => methodKeys([null, 40, other]), e => e.is?.(env.call_error));
const typeMember = keywordFunction('TARGET-LOADER-TYPE-MEMBER');
const typeMemberResults = [{package: 'COMMON-LISP', symbol: '*'}, other,
  {package: 'CCL', symbol: 'OTHER'}, null, 17].map(x => {
    try { return typeMember([x])[0] === T ? true : null; }
    catch (error) {
      if (error.is?.(env.call_error)) throw Error('TYPE-MEMBER ' + JSON.stringify(x) + ': checked ' + error.getArg(env.call_error, 0));
      throw error;
    }
  });
assert.deepEqual(typeMemberResults, read('type-member-native.json'));
const requireValue = keywordFunction('TARGET-LOADER-REQUIRE');
const requireCases = read('require-native.json');
for (const [args, expected] of requireCases) {
  if (expected === 'TYPE-ERROR')
    assert.throws(() => requireValue(args), e => e.is?.(env.call_error) && e.getArg(env.call_error, 0) === 5,
      'REQUIRE refusal ' + JSON.stringify(args));
  else {
    assert.equal(expected, true);
    let result;
    try { result = requireValue(args); }
    catch (error) {
      if (error.is?.(env.call_error)) throw Error('REQUIRE ' + JSON.stringify(args) + ': checked ' + error.getArg(env.call_error, 0));
      throw error;
    }
    assert.equal(result[0] >>> 0, requireValue.words[1], 'REQUIRE identity ' + JSON.stringify(args));
  }
}
const vectorInit = keywordFunction('TARGET-LOADER-VECTOR-INIT');
const vectorCases = read('vector-init-native.json');
for (const [args, expected] of vectorCases) {
  const [value, count] = vectorInit(args);
  assert.equal(count, 2);
  assert.equal(value, encode(expected[0]));
  assert.equal(get(root + 8204), encode(expected[1]));
}
const resetBinding = keywordFunction('TARGET-LOADER-RESET-BINDING');
const earlyError = keywordFunction('TARGET-LOADER-EARLY-ERROR');
assert.equal(get(tcr + 192), 0);
const earlyErrorModes = [0, 2];
for (const mode of earlyErrorModes) {
  put(tcr + 192, mode);
  const before = [64, 112, 128].map(offset => get(tcr + offset));
  let failure;
  try { earlyError([17]); }
  catch (error) { assert(error.is?.(env.call_error), 'checked exception, not host trap'); failure = error.getArg(env.call_error, 0); }
  assert.equal(failure, 5,
    'early fault preserved with a handler bound and unavailable error service, mode ' + mode);
  assert.deepEqual([64, 112, 128].map(offset => get(tcr + offset)), before,
    'early refusal restores argument, binding and root heads');
  assert.deepEqual(earlyError([null]), [N, 1], 'valid call still succeeds after the refusal');
}
put(tcr + 192, 0);
const structureInit = keywordFunction('TARGET-LOADER-STRUCTURE-INIT');
const structureCases = read('structure-init-native.json');
for (const [args, expected] of structureCases) {
  const [value, count] = structureInit(args);
  assert.equal(count, expected.length);
  assert.equal(value, encode(expected[0]));
  assert.deepEqual(expected.map((_, i) => get(root + 8200 + i * 4)), expected.map(x => encode(x)));
}
const allocationBefore = [get(tcr + 48), get(tcr + 52)];
assert.throws(() => structureInit([0, null, 1]),
  error => error.is?.(env.call_error) && error.getArg(env.call_error, 0) === 6,
  'an istruct requires its type-name slot');
assert.deepEqual([get(tcr + 48), get(tcr + 52)], allocationBefore,
  'empty istruct refusal preserves allocation state');
assert.equal(resetBinding([99])[1], 3);
const resetValues = [0, 1, 2].map(i => get(root + 8200 + i * 4) >> 2);
assert.deepEqual(resetValues, read('reset-binding-native.json'));
assert.equal(get(tcr + 112), 0);
const resetSymbol = keywordFunction('TARGET-LOADER-RESET-SYMBOL');
const resetTarget = encode({package: 'CCL', symbol: '*RESET-REFUSAL-TARGET*'});
put(resetTarget + 22, 4);
const bindingHead = root + 20008, bindingOlder = bindingHead - 64;
const bindingRefusals = [];
for (const [name, corrupt] of [
  ['unaligned link', () => put(tcr + 112, bindingHead + 4)],
  ['below stack', () => put(tcr + 112, root - 8)],
  ['beyond stack', () => put(tcr + 112, root + 32760)],
  ['unbacked record', () => { put(tcr + 72, memory.buffer.byteLength + 32); put(tcr + 112, memory.buffer.byteLength); }],
  ['record magic', () => put(bindingHead + 24, 0)],
  ['self link', () => put(bindingHead, bindingHead)],
  ['ascending link', () => put(bindingHead, bindingHead + 32)],
  ['older record invalid before any store', () => put(bindingOlder + 24, 0)]
]) {
  for (const [p, next] of [[bindingHead, bindingOlder], [bindingOlder, 0]])
    [next, 4, 0, 0, 0, 40, 1112425521, 0].forEach((v, i) => put(p + i * 4, v));
  put(resetTarget + 2, 40); put(tcr + 112, bindingHead);
  corrupt();
  const before = {value: get(resetTarget + 2), link: get(tcr + 112), allocation: get(tcr + 48),
    records: new Uint8Array(memory.buffer, bindingOlder, 96).slice()};
  assert.throws(() => resetSymbol.raw([resetTarget, 396]),
    e => e.is?.(env.call_error) && [11, 2].includes(e.getArg(env.call_error, 0)), name);
  assert.deepEqual({value: get(resetTarget + 2), link: get(tcr + 112), allocation: get(tcr + 48),
    records: new Uint8Array(memory.buffer, bindingOlder, 96).slice()}, before, name + ' preserves bindings');
  put(tcr + 112, 0); put(tcr + 72, root + 32776);
  bindingRefusals.push(name);
}
const nested = units.find(u => u.modules.length > 1);
assert(nested, 'nested code graph');
const nestedSymbols = Array.from({length: nested.symbol_count}, (_, i) => symbols[i % symbols.length]);
const nestedCode = session.install(nested.name, nested.record, nestedSymbols);
assert.equal(nestedCode, codeIds[nested.root]);
for (const id of nested.modules) {
  assert.equal(get(registry + 8 + codeIds[id] * 16), slots[id]);
  assert.equal(typeof env.table.get(slots[id]), 'function');
  assert.equal(typeof env.tail_table.get(slots[id]), 'function');
}
// A second session cannot overwrite an installed logical ID or either role.
refuses('occupied', () => admitTargetBundle(options), /CODE_OCCUPIED/);
const report = {status: 'PASS', compiledModules: rows.length, installedUnits: session.installed(),
  result: 42, extremaNativeMatches: extremaCases.length, keywordNativeMatches: keywordResults.length,
  assqNativeMatches: assqCases.length,
  valuesNativeMatches: valuesCases.length,
  valuesRefusals,
  assqExtentRefusals: 2,
  typeMemberNativeMatches: typeMemberResults.length,
  requireNativeMatches: requireCases.length,
  vectorInitializationNativeMatches: vectorCases.length,
  structureInitializationNativeMatches: structureCases.length,
  emptyIstructRefused: true,
  earlyErrorPreserved: true,
  earlyErrorModes,
  bindingRefusals,
  nestedBindingNativeMatch: resetValues,
  codeId: code, slot: slots[unit.root], controls, targetLoadedFiles: 0, boot0: false,
  inputs: {bundle: digest, runner: sha256(fs.readFileSync(new URL(import.meta.url))),
    adapter: sha256(fs.readFileSync(out + '/target-code-adapter.wasm')),
    native: sha256(fs.readFileSync(out + '/extrema-native.json')),
    valuesNative: sha256(fs.readFileSync(out + '/values-native.json')),
    pools: sha256(fs.readFileSync(out + '/fixture-pools.json'))}};
fs.writeFileSync(out + '/check.json', JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report));
