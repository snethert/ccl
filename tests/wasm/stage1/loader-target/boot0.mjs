// Call the real bootstrap once. A failure ends this Worker; no initializer is
// skipped and no definition or binding is filled in by the harness.
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import assert from 'node:assert/strict';
import {Worker, isMainThread, parentPort, workerData} from 'node:worker_threads';
import {admitCrossImage} from '../../../../runtime/wasm32/cross-image.mjs';
import {CollectorOwner} from '../../../../runtime/wasm32/collector-owner.mjs';
import {allocationService, collectionInhibitionService, heapSnapshotService, objectValidityService} from '../../../../runtime/wasm32/allocation-service.mjs';
import {integerService} from '../../../../runtime/wasm32/integer-service.mjs';
import {floatService} from '../../../../runtime/wasm32/float-service.mjs';
import {sha256} from '../../../../runtime/wasm32/sha256.mjs';
import {observeChecks} from './diagnose.mjs';
import {bundleNamespace, targetLoadSession} from '../../../../runtime/wasm32/target-load-session.mjs';
import {serviceRequest} from '../../../../runtime/wasm32/file-host.mjs';
import {processService, ProcessReady} from '../../../../runtime/wasm32/process-service.mjs';

if (isMainThread) {
  const runtimeDirectory = new URL('../../../../runtime/wasm32/', import.meta.url);
  const scripts = Object.fromEntries([new URL(import.meta.url), new URL('./diagnose.mjs', import.meta.url),
    ...fs.readdirSync(runtimeDirectory).filter(name => name.endsWith('.mjs')).map(name => new URL(name, runtimeDirectory))]
    .map(url => [url.pathname, sha256(fs.readFileSync(url))]));
  const [out, runtime] = process.argv.slice(2);
  const traceFrom = process.argv.find(a => a.startsWith('--trace-from='))?.slice(13);
  const trace = process.argv.includes('--trace') || !!traceFrom;
  const inspectCode = Number(process.argv.find(a => a.startsWith('--inspect-code='))?.split('=')[1]);
  const bundleDirs = process.argv.filter(a => a.startsWith('--bundles=')).map(a => a.slice(10));
  const limit = Number(process.argv.find(a => a.startsWith('--bundle-limit='))?.split('=')[1] ?? Infinity);
  const selected = new Map();
  for (const dir of bundleDirs) for (const row of JSON.parse(fs.readFileSync(dir + '/bundle-manifest.json')).files)
    selected.set(row.path, {path: row.path, sha256: row.sha256, sourceDir: dir + '/' + row.stem,
      bytes: new Uint8Array(fs.readFileSync(dir + '/' + row.bundle))});
  const omittedBundles = process.argv.filter(a => a.startsWith('--omit-bundle=')).map(a => a.slice(14));
  for (const path of omittedBundles) assert(selected.delete(path), 'omitted bundle must exist: ' + path);
  const files = [...selected.values()].slice(0, limit);
  const namespace = bundleNamespace({files}), session = namespace.session();
  assert(!inspectCode || trace, '--inspect-code requires --trace');
  const dumpFailure = process.argv.includes('--dump-failure');
  const startupLoads = process.argv.filter(a => a.startsWith('--startup-load=')).map(a => a.slice(15));
  const callbackSelection = JSON.parse(fs.readFileSync(new URL('../startup-resets/selection.json', import.meta.url)));
  const worker = new Worker(new URL(import.meta.url), {workerData: {out, runtime, trace, traceFrom, inspectCode, files, dumpFailure, startupLoads, omittedBundles, callbackSelection, scripts}});
  let memory;
  const result = await new Promise((resolve, reject) => {
    worker.on('message', message => {
      try {
        if (message.type === 'memory') { memory = message.memory; return; }
        if (message.type === 'request') {
          assert(serviceRequest(memory, session, message.lifetime, message.generation)); return;
        }
        if (message.type === 'stderr') { process.stderr.write(message.text); return; }
        if (message.type === 'progress') { console.error(JSON.stringify(message)); return; }
        resolve(message);
      } catch (error) { worker.terminate(); reject(error); }
    }); worker.once('error', reject);
    worker.once('exit', code => { if (code) reject(Error('boot Worker exit ' + code)); });
  });
  const report = process.argv.find(a => a.startsWith('--report='))?.slice(9) ??
    out + (inspectCode ? '/boot0-checks.json' : trace ? '/boot0-trace.json' : '/boot0.json');
  fs.writeFileSync(report, JSON.stringify(result, null, 2) + '\n');
  console.log(JSON.stringify(result));
  if (process.argv.includes('--expect-ready') && !result.ready) process.exitCode = 1;
} else {
  const {out, runtime} = workerData, artifacts = out + '/boot/artifacts';
  const json = name => JSON.parse(fs.readFileSync(name));
  const manifest = json(artifacts + '/manifest.json'), record = json(artifacts + '/heap-image.json');
  const codeSet = json(artifacts + '/code-set.json'), policy = json(out + '/policy.json'), versions = json(out + '/versions.json');
  const N = 77825, tcr = 1024, registry = 22020096, root = 26214392, external = 24117248, bindings = 266240, base = 8388608;
  // Match the advertised 1 MiB initial value stack. The old 32 KiB fixture
  // area booted, but ordinary nested generic printer calls exhausted it.
  const valueStackEnd = root + 8 + 1048576;
  const capacity = 32768;
  const memory = new WebAssembly.Memory({initial: 448, maximum: 32769, shared: true});
  const get = p => new DataView(memory.buffer).getUint32(p, true), put = (p, v) => new DataView(memory.buffer).setUint32(p, v, true);
  parentPort.postMessage({type: 'memory', memory});
  const start = manifest.heap.start, end = start + manifest.heap.bytes;
  const fixed = fs.readFileSync(artifacts + '/static.bin');
  assert.equal(sha256(fixed), manifest.static.sha256);
  new Uint8Array(memory.buffer, manifest.static.start, fixed.length).set(fixed);
  const regions = [{name: 'static', start: manifest.static.start, size: fixed.length, kind: 'objects'},
    {name: 'roots', start: manifest.roots.start, size: 64, kind: 'roots'}];
  const layoutRegions = [['tcr', tcr, tcr + 256], ['image', manifest.static.start, manifest.static.start + fixed.length],
    ['image', start, end], ['image', manifest.roots.start, manifest.roots.start + 64],
    ['vstack', root, valueStackEnd], ['temp', 196608, 212992], ['control', 212992, 229376],
    ['external', external, external + 1048576], ['bindings', bindings, bindings + 4096],
    ['image', 280000, 280256],
    ['runtime-globals', 280256, 280272],
    ['c-stack', 1048576, 1114112], ['root-list', 4600000, 5648576], ['scratch', 12582912, 20971520]]
    .map(([role, start, end], i) => ({name: role + '-' + i, role, start, end}));
  layoutRegions.find(r => r.start === manifest.roots.start).enumerable = false;
  const layout = {version: 1, collector: 'copying', workers: 1, egc: false, tcr, maximumPages: 32769,
    logCapacity: 262144, regions: layoutRegions,
    spaces: [base, base + 65536].map((start, i) => ({name: 'heap-' + i, start, end: start + 65536})),
    groups: ['module-constants', 'callbacks', 'registry', 'host'].map((kind, i) => ({kind, slots: [external + i * 4]}))};
  for (let i = 0; i < 4; i++) put(external + i * 4, N);
  for (const [offset, value] of [[0, 1], [8, 1], [32, 2], [48, base], [52, base + 65536], [56, base],
    [64, root + 8], [68, root + 8], [72, valueStackEnd], [76, 196608], [80, 196608], [84, 212992],
    [88, 212992], [92, 212992], [96, 229376], [104, bindings], [108, 0], [116, 0],
    [120, root + 8200], [124, root + 8264], [128, root], [188, N]]) put(tcr + offset, value);
  put(root, 0); put(root + 4, 0);
  put(280256, 1); // runtime-globals.v1: fresh inhibition and pending state.
  const binary = name => fs.readFileSync(runtime + '/' + name + '.wasm');
  const runtimeIdentity = json(runtime + '/array-runtime.json');
  assert.equal(sha256(fs.readFileSync(new URL('../../../../runtime/wasm32/collector.c', import.meta.url))), runtimeIdentity.source);
  assert.equal(sha256(binary('collector')), runtimeIdentity.binary);
  const owner = CollectorOwner.create(memory, binary('collector'), runtimeIdentity.binary, layout);
  const env = {memory, tcr, code_registry: registry,
    table: new WebAssembly.Table({element: 'anyfunc', initial: capacity}),
    tail_table: new WebAssembly.Table({element: 'anyfunc', initial: capacity}),
    call_error: new WebAssembly.Tag({parameters: ['i32']}), type_error: new WebAssembly.Tag({parameters: ['i32', 'i32']}),
    nonlocal_exit: new WebAssembly.Tag({parameters: ['i32']})};
  put(registry, capacity); put(registry + 4, 1);
  const pinned = layoutRegions.filter(r => r.role === 'image');
  const numeric = {memory, tcr, owner, callError: env.call_error, pinned};
  const integer = integerService({...numeric, bytes: binary('integer'), digest: sha256(binary('integer'))});
  const floating = floatService({...numeric, bytes: binary('float'), digest: sha256(binary('float')),
    detectorBytes: binary('detector'), detectorDigest: sha256(binary('detector'))});
  const expected = {...versions, modules: codeSet.modules.map(m => [m.name, m.code_id, m.generation]),
    table_capacity: capacity, reserved_slots: [0, 1, 2, 3, 4, 5, 6, 7, 8], slots: Object.fromEntries(codeSet.modules.map(m => [m.code_id, m.code_id + 8]))};
  const admitted = admitCrossImage({memory, manifest, record, codeSet, regions, env, policy, expected,
    payload: fs.readFileSync(artifacts + '/heap.payload.bin'),
    readBytes: name => fs.readFileSync(artifacts + '/' + name + '.wasm'),
    readTemplate: name => fs.readFileSync(artifacts + '/' + name + '.template.wasm'),
    capabilities: {owner: {ensure: allocationService(owner, env.call_error)}, integer: {calculate: integer}, floating: {calculate: floating}}});
  const installed = admitted.install();
  const resolve = r => Object.hasOwn(r, 'heap') ? start + r.heap + r.tag :
    regions.find(x => x.name === r.region).start + r.offset + r.tag;
  const symbol = name => {
    const row = manifest.symbols.find(s => s.package === 'CCL' && s.name === name);
    assert(row, 'missing runtime import ' + name); return resolve(row.reference);
  };
  const capabilities = {owner: {ensure: allocationService(owner, env.call_error)},
    integer: {calculate: integer}, floating: {calculate: floating}};
  const loadEvents = [], outputEvents = [];
  let observeInstalled = () => {}, enableObservation = () => {};
  let traceActive = workerData.trace && !workerData.traceFrom;
  const pendingObservations = [];
  const loader = targetLoadSession({files: workerData.files, memory, env, owner, versions, policy, capabilities, pinned,
    nextCode: Math.max(...codeSet.modules.map(m => m.code_id)) + 1,
    nextSlot: Math.max(...Object.values(expected.slots)) + 1,
    post: request => parentPort.postMessage({type: 'request', ...request}),
    onOpen: (path, fd) => { loadEvents.push({event: 'open', path, fd}); enableObservation(path); },
    onClose: (path, fd) => loadEvents.push({event: 'close', path, fd}),
    onInstall: (path, entries) => observeInstalled(path, entries)});
  const adapter = new WebAssembly.Module(fs.readFileSync(out + '/host-call-adapter.wasm'));
  const waitCell = new Int32Array(new SharedArrayBuffer(4));
  const processRequest = processService({memory,
    objectValidity: objectValidityService(owner, env.call_error),
    collectionInhibition: collectionInhibitionService(owner, env.call_error),
    // macOS supplies timezone history/DST; it is an embedding capability,
    // never reconstructed by Lisp or guessed from January/July offsets.
    calendar: seconds => JSON.parse(execFileSync('/usr/bin/python3', ['-c',
      'import time,json,sys; t=time.localtime(int(sys.argv[1])); print(json.dumps(dict(minutesWest=(-t.tm_gmtoff)//60,daylight=t.tm_isdst>0)))',
      String(seconds)], {encoding: 'utf8'})),
    cpuTime: () => process.cpuUsage(),
    startup: {imageName: '/ccl/boot/' + manifest.heap.digest + '.image',
      cclRoot: '/ccl/', arguments: ['--no-init', ...workerData.startupLoads.flatMap(path => ['--load', path])]},
    output: (channel, text) => { outputEvents.push({channel, text}); fs.writeSync(channel, text); },
    configuration: {pageSize: 65536, clockTicks: 1000, cpuCount: 1, stackSize: -1,
      defaults: [1048576, 1048576, 524288]},
    wait: milliseconds => Atomics.wait(waitCell, 0, 0, milliseconds)});
  const heapSnapshot = heapSnapshotService(owner, env.call_error);
  const services = [
    ['%WASM-HOST-FILE-REQUEST', 4, loader.file],
    ['%WASM-HOST-INSTALL-CODE', 3, loader.install],
    ['%WASM-HOST-HEAP-SNAPSHOT', 1, args => heapSnapshot(get(args) >>> 2)],
    ['%WASM-HOST-WRITE-STRING', 1, args => {
      const word = get(args); assert.equal(get(word - 6) & 255, 191);
      const text = Array.from({length: get(word - 6) >>> 8}, (_, i) => String.fromCodePoint(get(word - 2 + 4 * i))).join('');
      parentPort.postMessage({type: 'stderr', text}); return new TextEncoder().encode(text).length * 4;
    }],
    ['%WASM-HOST-PROCESS-REQUEST', 3, processRequest]
  ];
  services.forEach(([name, arity, run], i) => {
    const id = i + 1, base = 280000 + i * 32, instance = new WebAssembly.Instance(adapter, {env, host: {arity, run}});
    [1578, id * 4, N, 4, N, N, N, 0].forEach((v, n) => put(base + 4 * n, v));
    [id, 4, 17, 23].forEach((v, n) => put(registry + 8 + 16 * id + 4 * n, v));
    env.table.set(id, instance.exports.entry); env.tail_table.set(id, instance.exports.tail_entry);
    put(symbol(name) + 6, base + 6);
  });
  let firstFailure, firstCheck, firstCondition, observation, observedContext, handoff = false;
  let execution = () => [], classErrorTransition;
  const conditionCalls = [];
  let terminalFailureChain = [];
  const recentFailures = [];
  const callbackEvents = [], callbackTokens = new Map();
  const callbackByName = new Map(workerData.callbackSelection.callbacks.map(row => [row.name.split('::').at(-1), row]));
  const observedLookups = [];
  const completedLoads = [];
  {
    const observer = new WebAssembly.Module(fs.readFileSync(out + '/observe.wasm'));
    const text = word => {
      if (word % 8 !== 6 || word < 6 || word + 2 > memory.buffer.byteLength || (get(word - 6) & 255) !== 191) return word;
      const n = get(word - 6) >>> 8;
      return Array.from({length: Math.min(n, 160)}, (_, i) => String.fromCodePoint(get(word - 2 + i * 4))).join('');
    };
    const describe = (word, depth = 0) => {
      if (word === N) return null;
      if (word % 4 === 0) return (word | 0) >> 2;
      if (depth > 2 || word < 6 || word + 26 > memory.buffer.byteLength) return {word};
      if (word % 8 === 1) return {cons: [describe(get(word + 3), depth + 1), describe(get(word - 1), depth + 1)]};
      if (word % 8 === 6) {
        const tag = get(word - 6) & 255;
        if (tag === 58) return {symbol: text(get(word - 2))};
        if (tag === 191) return text(word);
        if (tag === 42) return {function: describe(get(get(word + 18) + 18), depth + 1)};
        if (tag === 7) return {bignum: Array.from({length: Math.min(get(word - 6) >>> 8, 4)}, (_, i) => get(word - 2 + 4 * i))};
        return {tag, word};
      }
      return {word};
    };
    const failed = (code, fn, count, args) => {
      terminalFailureChain.push({code, callable: describe(fn),
        args: Array.from({length: Math.min(count, 8)}, (_, i) => describe(get(args + i * 4)))});
      recentFailures.push(terminalFailureChain.at(-1));
      if (recentFailures.length > 1024) recentFailures.shift();
      if (firstFailure) return;
      firstFailure = {code, callable: describe(fn), args: Array.from({length: Math.min(count, 8)}, (_, i) => describe(get(args + i * 4))), recent: [...recentCalls]};
    };
    const observeCheck = (kind, datum, expected) => {
      if (kind === -999997) {
        observedLookups.push({symbol: describe(datum), value: describe(expected)});
        if (observedLookups.length > 8) observedLookups.shift();
        return;
      }
      if (kind === -999998) {
        observedContext = {self: describe(datum), address: expected,
          words: Array.from({length: 12}, (_, i) => get(expected + i * 4)),
          function: describe(get(expected + 40))};
        return;
      }
      firstCheck ??= {kind, datum: describe(datum), expected: describe(expected), context: observedContext, lookups: [...observedLookups]};
    };
    let calls = 0, serial = 0; const recent = [], recentCalls = [], callNames = new Map(), counts = new Map(), loads = new Map(), loadCodes = new Map(), conditionCodes = new Map(), conditionNames = new Map();
    const sources = new Map(installed.instances.map(({record: row}) =>
      [row.code_id, {file: 'boot0', module: row.name}]));
    execution = () => [...counts].map(([code, count]) =>
      ({...callNames.get(code), ...sources.get(code), count}));
    const entered = (code, fn, count, args) => {
      terminalFailureChain.length = 0;
      let token = 0;
      if (!loadCodes.has(code)) loadCodes.set(code, describe(fn)?.function?.symbol === '%FASLOAD');
      if (!conditionNames.has(code)) conditionNames.set(code, describe(fn)?.function?.symbol);
      const conditionName = conditionNames.get(code);
      if (conditionCalls.length < 8 && ['%WASM-KERNEL-RESTART', '%WASM-ERROR', 'INVOKE-DEBUGGER'].includes(conditionName))
        conditionCalls.push({code, name: conditionName,
          args: Array.from({length: Math.min(count, 8)}, (_, i) => describe(get(args + i * 4)))});
      if (loadCodes.get(code)) {
        token = ++serial; loads.set(token, text(get(args)));
        if (loads.get(token) === 'ccl:level-1.w32fsl') handoff = true;
      }
      if (!traceActive) return token;
      const selected = callbackByName.get(conditionName);
      if (selected) {
        token = ++serial;
        // Keep this observer's symbol reference under the same collector
        // authority as installed code; the callback may collect before return.
        const nameWord = get(get(fn + 18) + 18);
        const held = owner.atSafepoint(o => o.rootCells([nameWord]));
        callbackTokens.set(token, {held, selected, code});
        callbackEvents.push({event: 'enter', sequence: callbackEvents.length,
          name: selected.name, group: selected.group, ordinal: selected.ordinal,
          code, ...sources.get(code), globalValue: describe(get(nameWord + 2))});
      }
      if (get(tcr + 192) === 1) classErrorTransition ??= {code, callable: describe(fn), calls};
      if (!conditionCodes.has(code)) conditionCodes.set(code, describe(fn)?.function?.symbol === '%WASM-IMPLICIT-CONDITION');
      if (conditionCodes.get(code)) firstCondition ??= {
        args: Array.from({length: count}, (_, i) => describe(get(args + i * 4))), recent: [...recent], calls: [...recentCalls]};
      counts.set(code, (counts.get(code) ?? 0) + 1);
      recent.push(code); if (recent.length > 16) recent.shift();
      if (!callNames.has(code)) callNames.set(code, {code, callable: describe(fn)});
      recentCalls.push(callNames.get(code)); if (recentCalls.length > 16) recentCalls.shift();
      if (++calls === 10000 || calls % 1000000 === 0) parentPort.postMessage({type: 'progress', calls, code, callable: describe(fn),
        args: [describe(get(get(tcr + 64)))], recent,
        roots: (() => { const rows = []; let p = get(tcr + 128);
          for (let i = 0; p && i < 30; i++, p = get(p)) rows.push([p, get(p + 4), describe(get(p + 8))]); return rows; })(),
        packages: (() => { const rows = []; let p = get(symbol('%ALL-PACKAGES%') + 2);
          for (let i = 0; p !== N && i < 12; i++, p = get(p - 1)) { const pkg = get(p + 3); rows.push([pkg, describe(pkg), get(pkg + 14)]); } return rows; })(),
        counts: [...counts].sort((a, b) => b[1] - a[1]).slice(0, 12)});
      return token;
    };
    const returned = (token, value, count) => {
      if (!token) return;
      if (callbackTokens.has(token)) {
        const {held, selected, code} = callbackTokens.get(token);
        callbackEvents.push({event: 'return', sequence: callbackEvents.length,
          name: selected.name, group: selected.group, ordinal: selected.ordinal,
          code, ...sources.get(code), value: describe(value), count,
          globalValue: describe(get(held.values()[0] + 2))});
        owner.atSafepoint(() => held.release()); callbackTokens.delete(token);
        return;
      }
      const path = loads.get(token); loads.delete(token);
      loadEvents.push({event: 'return', path, value: describe(value), count});
      if (count > 0 && value === 77838) completedLoads.push(path);
    };
    const observedSlots = new Set();
    if (workerData.trace) observeInstalled = (path, entries) => {
      if (!traceActive) { pendingObservations.push({path, entries}); return; }
      for (const {record, instance, codeId, imports} of entries) {
        if (observedSlots.has(record.slot)) continue;
        sources.set(codeId, {file: path, module: record.name});
        let exports = instance.exports;
        if (codeId === workerData.inspectCode) {
          const sourceDir = workerData.files.find(file => file.path === path).sourceDir;
          const observed = observeChecks({out, row: {...record, code_id: codeId}, imports,
            sourceFile: sourceDir + '/' + record.name + '.wat',
            report: observeCheck});
          exports = observed.instance.exports; observation = observed.evidence;
        }
        const wrapper = new WebAssembly.Instance(observer, {env, trace: {
          code: codeId, failed: (...args) => { failed(...args); if (firstFailure?.code === codeId) firstFailure.file = path; },
          entered, returned, ...exports}});
        env.table.set(record.slot, wrapper.exports.entry); env.tail_table.set(record.slot, wrapper.exports.tail_entry);
        observedSlots.add(record.slot);
      }
    };
    enableObservation = path => {
      if (traceActive || path !== workerData.traceFrom) return;
      traceActive = true;
      for (const {path, entries} of pendingObservations) observeInstalled(path, entries);
      pendingObservations.length = 0;
    };
    for (const entry of installed.instances) {
      const {record: row} = entry;
      let {instance} = entry;
      if (row.code_id === workerData.inspectCode) {
        const observed = observeChecks({out, row, env, start, regions,
          capabilities: {owner: {ensure: allocationService(owner, env.call_error)},
            integer: {calculate: integer}, floating: {calculate: floating}},
          report: observeCheck});
        instance = observed.instance; observation = observed.evidence;
      }
      const wrapper = new WebAssembly.Instance(observer, {env, trace: {code: row.code_id, failed, entered, returned, ...instance.exports}});
      env.table.set(row.slot, wrapper.exports.entry); env.tail_table.set(row.slot, wrapper.exports.tail_entry);
    }
    assert(!workerData.inspectCode || observation || workerData.inspectCode > Math.max(...codeSet.modules.map(r => r.code_id)),
      'requested diagnostic code ID is absent');
  }
  const index = manifest.roots.names.indexOf('toplevel-function');
  const fn = get(manifest.roots.start + index * 4), id = get(fn - 2) >>> 2;
  assert.equal(get(fn - 6), 1578);
  let result;
  try {
    const values = env.table.get(expected.slots[id])(fn, 0);
    result = {status: 'RETURNED', values, boot0: false, reason: 'Bootstrap returned without a qualified handoff marker'};
  } catch (error) {
    const reason = error.is?.(env.call_error) ? 'checked ' + error.getArg(env.call_error, 0) :
      error.is?.(env.type_error) ? 'type_error ' + error.getArg(env.type_error, 0) + ' ' + error.getArg(env.type_error, 1) :
        String(error);
    result = {status: error instanceof ProcessReady ? 'READY' : 'STOPPED',
      ready: error instanceof ProcessReady, boot0: false, reason, stack: error.stack ?? null};
    if (workerData.dumpFailure && !(error instanceof ProcessReady)) {
      fs.writeFileSync(out + '/failure-memory.bin', new Uint8Array(memory.buffer));
      fs.writeFileSync(out + '/failure-spaces.json', JSON.stringify(owner.spaces));
    }
  }
  parentPort.postMessage({...result, boot0: handoff, firstFailure, terminalFailureChain, recentFailures, firstCheck, firstCondition, observation, traceFrom: workerData.traceFrom ?? null, loadEvents, entry: '%TOPLEVEL-FUNCTION%', modules: codeSet.modules.length,
    heapDigest: manifest.heap.digest, codeDigest: manifest.codeDigest, collections: owner.collectionCount,
    environment: {node: process.version, runner: workerData.scripts[new URL(import.meta.url).pathname], scripts: workerData.scripts,
      observer: workerData.trace ? sha256(fs.readFileSync(out + '/observe.wasm')) : null,
      runtime: Object.fromEntries(['collector', 'integer', 'float', 'detector'].map(name => [name, sha256(binary(name))]))},
    level1CrossLoaded: false, targetLoadedFiles: completedLoads.length, completedLoads,
    execution: execution(), classErrorTransition, conditionCalls, outputEvents, callbackEvents,
    errorServiceMode: get(tcr + 192), collectionInhibition: owner.collectionInhibition,
    collectionPending: owner.collectionPending,
    startupLoads: workerData.startupLoads, omittedBundles: workerData.omittedBundles,
    bundleInputs: workerData.files.map(({path, sha256}) => ({path, sha256}))});
}
