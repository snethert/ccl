// Call the real bootstrap once. A failure ends this Worker; no initializer is
// skipped and no definition or binding is filled in by the harness.
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import assert from 'node:assert/strict';
import {Worker, isMainThread, parentPort, workerData} from 'node:worker_threads';
import {admitCrossImageAsync} from '../../../../runtime/wasm32/cross-image.mjs';
import {CollectorOwner} from '../../../../runtime/wasm32/collector-owner.mjs';
import {allocationService, collectionInhibitionService, heapSnapshotService, objectValidityService} from '../../../../runtime/wasm32/allocation-service.mjs';
import {integerService} from '../../../../runtime/wasm32/integer-service.mjs';
import {floatService} from '../../../../runtime/wasm32/float-service.mjs';
import {sha256} from '../../../../runtime/wasm32/sha256.mjs';
import {observeChecks} from './diagnose.mjs';
import {bundleNamespace, targetLoadSession} from '../../../../runtime/wasm32/target-load-session.mjs';
import {serviceRequest} from '../../../../runtime/wasm32/file-host.mjs';
import {processService, ProcessReady} from '../../../../runtime/wasm32/process-service.mjs';
import {deriveLayout} from '../../../../runtime/wasm32/layout.mjs';
import {inputInventory} from '../../../../runtime/wasm32/input-inventory.mjs';
import {archiveSource,readArchiveSource} from './archive-source.mjs';
import {startupTiming} from './startup-timing.mjs';

const timingPrefix = isMainThread ? process.argv.find(a => a.startsWith('--timing='))?.slice(9) : workerData.timingPrefix;
const timing = startupTiming(timingPrefix, isMainThread ? 'main' : 'worker');
const measure = timing?.measure ?? ((_phase, run) => run());
const inputs=inputInventory();
const onBuffers=(label,values)=>{inputs.release(label);if(values.length)inputs.hold(label,'admissionWork',values);};
const onManifest=(label,value)=>value?inputs.holdManifest(label,value):inputs.releaseManifest(label);

if (isMainThread) {
  const runtimeDirectory = new URL('../../../../runtime/wasm32/', import.meta.url);
  const scripts = Object.fromEntries([new URL(import.meta.url), new URL('./diagnose.mjs', import.meta.url), new URL('./startup-timing.mjs', import.meta.url),
    ...fs.readdirSync(runtimeDirectory).filter(name => name.endsWith('.mjs')).map(name => new URL(name, runtimeDirectory))]
    .map(url => [url.pathname, sha256(fs.readFileSync(url))]));
  const [out, runtime] = process.argv.slice(2);
  const traceFrom = process.argv.find(a => a.startsWith('--trace-from='))?.slice(13);
  const trace = process.argv.includes('--trace') || !!traceFrom;
  const inspectCode = Number(process.argv.find(a => a.startsWith('--inspect-code='))?.split('=')[1]);
  const bundleDirs = process.argv.filter(a => a.startsWith('--bundles=')).map(a => a.slice(10));
  const limit = Number(process.argv.find(a => a.startsWith('--bundle-limit='))?.split('=')[1] ?? Infinity);
  const layoutConfig=JSON.parse(process.argv.find(a=>a.startsWith('--layout='))?.slice(9)??'{}');
  const archives=bundleDirs.flatMap(dir=>{
    const a=JSON.parse(fs.readFileSync(dir+'/bundle-manifest.json')).archive;
    return a?[archiveSource(dir,a)]:[];
  });
  const artifacts=out+'/boot/artifacts',bootManifest=JSON.parse(fs.readFileSync(artifacts+'/manifest.json'));
  let bootArchive=bootManifest.archive?archiveSource(artifacts,bootManifest.archive,'boot'):null;
  if(!bootArchive){
    const raw=fs.readFileSync(artifacts+'/code-set.json'),set=JSON.parse(raw);
    if(set.archive)bootArchive=archiveSource(artifacts,{file:'boot.archive.wasm',manifest:'code-set.json',
      sha256:set.archive.binary_sha256,manifest_sha256:sha256(raw),function_count:set.archive.function_count,root_cells:set.archive.root_cells},'boot');
  }
  const catalog=new Map([...archives,...(bootArchive?[bootArchive]:[])].map(a=>[a.digest,a]));
  const directory=a=>({kind:a.kind,digest:a.digest,manifestDigest:a.manifestDigest,function_count:a.function_count,root_cells:a.root_cells});
  const selected = new Map();
  for (const dir of bundleDirs) for (const row of JSON.parse(fs.readFileSync(dir + '/bundle-manifest.json')).files)
    selected.set(row.path, {path: row.path, sha256: row.sha256, sourceDir: dir + '/' + row.stem,
      bytes: measure('bundle.read', () => new Uint8Array(fs.readFileSync(dir + '/' + row.bundle)), {path: row.path})});
  const omittedBundles = process.argv.filter(a => a.startsWith('--omit-bundle=')).map(a => a.slice(14));
  for (const path of omittedBundles) assert(selected.delete(path), 'omitted bundle must exist: ' + path);
  const files = [...selected.values()].slice(0, limit);
  inputs.hold('containers','containers',files.map(f=>f.bytes));
  timing?.memory('bundles-read', {inputOwnership:inputs.snapshot()});
  const namespace = measure('namespace.create', () => bundleNamespace({files, measure,retainCode:false})), session = namespace.session();
  const ownedInputs=()=>inputs.snapshot({fasl:namespace.namespace.storage()});
  timing?.memory('namespace-created',{inputOwnership:ownedInputs()});
  assert(!inspectCode || trace, '--inspect-code requires --trace');
  const dumpFailure = process.argv.includes('--dump-failure');
  const startupLoads = process.argv.filter(a => a.startsWith('--startup-load=')).map(a => a.slice(15));
  const callbackSelection = JSON.parse(fs.readFileSync(new URL('../startup-resets/selection.json', import.meta.url)));
  const workerFiles=files.map(({path,sha256,sourceDir,bytes})=>{const container=namespace.containers.get(path);
    return {path,sha256,sourceDir,...(container?{container}:{bytes})};});
  timing?.event('worker-send',{inputOwnership:ownedInputs()});
  const worker = measure('worker.construct', () => new Worker(new URL(import.meta.url), {workerData: {out, runtime, trace, traceFrom, inspectCode,
    files:workerFiles,archives:archives.map(directory),bootArchive:bootArchive?directory(bootArchive):null,
    layoutConfig, dumpFailure, startupLoads, omittedBundles, callbackSelection, scripts, timingPrefix}}));
  selected.clear();files.length=0;workerFiles.length=0;inputs.release('containers');
  timing?.memory('directory-delivered',{inputOwnership:ownedInputs()});
  const sampling = timing && setInterval(() => timing.memory('periodic',{inputOwnership:ownedInputs()}), 1000);
  sampling?.unref();
  let memory;
  const result = await new Promise((resolve, reject) => {
    worker.on('message', message => {
      try {
        if(message.type==='archive-request'){
          const source=catalog.get(message.digest);assert(source,'unknown archive request');
          const data=measure('archive.read',()=>readArchiveSource(source));
          inputs.hold('archive-code','archiveBytes',[data.bytes]);inputs.hold('archive-manifest','manifestBytes',[data.metadata]);
          timing?.memory('archive-read',{tier:source.kind,inputOwnership:ownedInputs()});
          try{
            worker.postMessage({type:'archive-input',digest:source.digest,...data},[data.bytes,data.metadata]);
            assert.equal(data.bytes.byteLength,0);assert.equal(data.metadata.byteLength,0);
          }finally{inputs.release('archive-code');inputs.release('archive-manifest');}
          timing?.memory('archive-transferred',{tier:source.kind,senderDetached:true,inputOwnership:ownedInputs()});return;
        }
        if (message.type === 'memory') { memory = message.memory; return; }
        if (message.type === 'request') {
          measure('host.request', () => assert(serviceRequest(memory, session, message.lifetime, message.generation))); return;
        }
        if (message.type === 'stderr') { process.stderr.write(message.text); return; }
        if (message.type === 'progress') { console.error(JSON.stringify(message)); return; }
        resolve(message);
      } catch (error) { worker.terminate(); reject(error); }
    }); worker.once('error', reject);
    worker.once('exit', code => { if (code) reject(Error('boot Worker exit ' + code)); });
  });
  if (sampling) clearInterval(sampling);
  timing?.memory('result-received', {status: result.status,inputOwnership:ownedInputs()});
  const report = process.argv.find(a => a.startsWith('--report='))?.slice(9) ??
    out + (inspectCode ? '/boot0-checks.json' : trace ? '/boot0-trace.json' : '/boot0.json');
  fs.writeFileSync(report, JSON.stringify(result, null, 2) + '\n');
  console.log(JSON.stringify(result));
  if (process.argv.includes('--expect-ready') && !result.ready) process.exitCode = 1;
  timing?.finish();
} else {
  const {out, runtime} = workerData, artifacts = out + '/boot/artifacts';
  const json = name => JSON.parse(fs.readFileSync(name));
  const manifest=json(artifacts+'/manifest.json');let record=json(artifacts+'/heap-image.json');
  async function receiveArchive(descriptor){
    let message=await new Promise((resolve,reject)=>{
      const listener=m=>{if(m.type==='archive-input'&&m.digest===descriptor.digest){parentPort.off('message',listener);resolve(m);}};
      parentPort.on('message',listener);parentPort.postMessage({type:'archive-request',digest:descriptor.digest});
    });
    inputs.hold('archive-code','archiveBytes',[message.bytes]);inputs.hold('archive-manifest','manifestBytes',[message.metadata]);
    timing?.memory('archive-received',{tier:descriptor.kind,inputOwnership:inputs.snapshot()});
    try{
      assert.equal(sha256(message.metadata),descriptor.manifestDigest,'archive metadata digest');
      const parsed=JSON.parse(new TextDecoder('utf8',{fatal:true}).decode(message.metadata));inputs.holdManifest('source-manifest',parsed);
      const archive=descriptor.kind==='boot'?parsed.archive:parsed;
      assert.equal(archive.function_count,descriptor.function_count);assert.equal(archive.root_cells,descriptor.root_cells);
      const result={digest:descriptor.digest,bytes:message.bytes,manifest:archive,...(descriptor.kind==='boot'?{codeSet:parsed}:{})};
      message.metadata=null;inputs.release('archive-manifest');return result;
    }catch(e){inputs.release('archive-code');inputs.release('archive-manifest');inputs.releaseManifest('source-manifest');throw e;}
    finally{message=null;}
  }
  let bootInput=workerData.bootArchive?await receiveArchive(workerData.bootArchive):null;
  const codeSet=bootInput?.codeSet??json(artifacts+'/code-set.json'),bootIsArchive=!!codeSet.archive,
    policy=json(out+'/policy.json'),versions=json(out+'/versions.json');
  const N=77825,tcr=1024;
  const imageRegions=[{start:manifest.static.start,end:manifest.static.start+manifest.static.bytes},
    {start:manifest.heap.start,end:manifest.heap.start+manifest.heap.bytes},
    {start:manifest.roots.start,end:manifest.roots.start+64,enumerable:false},
    {start:280000,end:280256}];
  const layout=deriveLayout(workerData.layoutConfig,{bootFunctions:codeSet.modules.length,
    bootRootCells:codeSet.archive?.root_cells??0,
    runtimeFunctions:workerData.archives.reduce((n,a)=>n+a.function_count,0),
    runtimeRootCells:workerData.archives.reduce((n,a)=>n+a.root_cells,0),image:imageRegions});
  const {registry,root,external,bindings}=layout,capacity=layout.tableCapacity;
  const memory=new WebAssembly.Memory({initial:layout.initialPages,maximum:32769,shared:true});
  const get = p => new DataView(memory.buffer).getUint32(p, true), put = (p, v) => new DataView(memory.buffer).setUint32(p, v, true);
  parentPort.postMessage({type: 'memory', memory});
  const start = manifest.heap.start, end = start + manifest.heap.bytes;
  const fixed = fs.readFileSync(artifacts + '/static.bin');
  assert.equal(sha256(fixed), manifest.static.sha256);
  new Uint8Array(memory.buffer, manifest.static.start, fixed.length).set(fixed);
  const regions = [{name: 'static', start: manifest.static.start, size: fixed.length, kind: 'objects'},
    {name: 'roots', start: manifest.roots.start, size: 64, kind: 'roots'}];
  const layoutRegions=layout.regions;
  for(let i=0;i<4;i++)put(external+i*4,N);
  for(const [offset,value] of Object.entries({...layout.tcrWords,0:1,8:1,32:2,108:0,116:0,188:N}))put(tcr+Number(offset),value);
  put(root,0);put(root+4,0);put(layout.runtimeGlobals,1);
  const binary = name => fs.readFileSync(runtime + '/' + name + '.wasm');
  const runtimeIdentity = json(runtime + '/array-runtime.json');
  assert.equal(sha256(fs.readFileSync(new URL('../../../../runtime/wasm32/collector.c', import.meta.url))), runtimeIdentity.source);
  assert.equal(sha256(binary('collector')), runtimeIdentity.binary);
  let lastCollection,loader;const inputState=()=>inputs.snapshot(loader?.ownership());
  const stackHighWater={value:0,temp:0,control:0};
  const heapState = () => {
    for(const [name,offset,start] of [['value',64,root+8],['temp',76,get(tcr+80)],['control',88,get(tcr+92)]])
      stackHighWater[name]=Math.max(stackHighWater[name],get(tcr+offset)-start);
    return ({inputOwnership:inputState(),configuration:layout.configuration,stackHighWaterLowerBounds:{...stackHighWater},linearMemoryBytes: memory.buffer.byteLength,
    allocatedHeapBytes: get(tcr + 48) - get(tcr + 56), activeHeapCapacityBytes: get(tcr + 52) - get(tcr + 56),
    collections: owner.collectionCount, storage: owner.storage, lastCollection});};
  const owner = CollectorOwner.create(memory, binary('collector'), runtimeIdentity.binary, layout,
    timing ? {measure: (phase, run) => {
      const result = measure(phase, run);
      if(phase!=='collector.copy')return result;
      lastCollection = {...result,epochMs: performance.timeOrigin + performance.now(),
        liveHeapBytes: get(tcr + 48) - get(tcr + 56), collection: owner.collectionCount};
      timing.event('collection', {...lastCollection, linearMemoryBytes: memory.buffer.byteLength});
      return result;
    }} : {});
  timing?.memory('linear-memory-created', heapState());
  const env = {memory, tcr, code_registry: registry,
    table: new WebAssembly.Table({element: 'anyfunc', initial: capacity}),
    tail_table: new WebAssembly.Table({element: 'anyfunc', initial: capacity}),
    call_error: new WebAssembly.Tag({parameters: ['i32']}), type_error: new WebAssembly.Tag({parameters: ['i32', 'i32']}),
    nonlocal_exit: new WebAssembly.Tag({parameters: ['i32']})};
  put(registry, layout.rows); put(registry + 4, 1);
  const pinned = layoutRegions.filter(r => r.role === 'image');
  const numeric = {memory, tcr, owner, callError: env.call_error, pinned};
  const integer = integerService({...numeric, bytes: binary('integer'), digest: sha256(binary('integer'))});
  const floating = floatService({...numeric, bytes: binary('float'), digest: sha256(binary('float')),
    detectorBytes: binary('detector'), detectorDigest: sha256(binary('detector'))});
  const expected = {...versions, modules: codeSet.modules.map(m => [m.name, m.code_id, m.generation]),
    table_capacity: capacity, reserved_slots: [0, 1, 2, 3, 4, 5, 6, 7, 8], slots: Object.fromEntries(codeSet.modules.map(m => [m.code_id, m.code_id + 8]))};
  let admitted,installed;
  try{
  admitted = await measure('boot.admit', () => admitCrossImageAsync({memory, owner, onBuffers, onManifest, manifest, record, codeSet, regions, env, policy, expected,
    payload: fs.readFileSync(artifacts + '/heap.payload.bin'),
    readBytes: name => name==='boot.archive'&&bootInput?bootInput.bytes:fs.readFileSync(artifacts + '/' + name + '.wasm'),
    readTemplate: name => fs.readFileSync(artifacts + '/' + name + '.template.wasm'),
    capabilities: {owner: {ensure: allocationService(owner, env.call_error)}, integer: {calculate: integer}, floating: {calculate: floating}}}));
  installed = measure('boot.install', () => admitted.install());
  }finally{
  admitted=null;record=null;
  if(bootInput){bootInput.bytes=null;bootInput.manifest=null;bootInput.codeSet=null;bootInput=null;codeSet.archive=null;inputs.release('archive-code');inputs.releaseManifest('source-manifest');}
  timing?.memory('boot-admission-end',{validationManifests:0,inputOwnership:inputState()});
  }
  timing?.memory('boot-installed', heapState());
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
  loader = await targetLoadSession({files: workerData.files, archives:workerData.archives, generations:layout.configuration.generations, memory, env, owner, versions, policy, capabilities, pinned,
    readArchive:receiveArchive,onBuffers,onManifest,onInput:(label,a)=>{
      if(label==='admission-end'){inputs.release('archive-code');inputs.releaseManifest('source-manifest');}
      timing?.memory(label,{validationManifests:label==='admission-start'?1:0,inputOwnership:inputState()});
    },
    measure, onAdmission: path => timing?.memory('file-admitted', {path, ...heapState()}),
    nextCode: Math.max(...codeSet.modules.map(m => m.code_id)) + 1,
    nextSlot: Math.max(...Object.values(expected.slots)) + 1,
    post: request => parentPort.postMessage({type: 'request', ...request}),
    onOpen: (path, fd) => { loadEvents.push({event: 'open', path, fd}); timing?.open(path, fd); enableObservation(path); },
    onClose: (path, fd) => { loadEvents.push({event: 'close', path, fd}); timing?.close(path, fd);
      timing?.memory('file-closed', {path, ...heapState()}); },
    onInstall: (path, entries) => observeInstalled(path, entries)});
  workerData.archives=null;workerData.bootArchive=null;
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
      defaults: layout.stackDefaults},
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
    const id = i + 1, base = 280000 + i * 32, instance = new WebAssembly.Instance(adapter, {env, host: {arity,
      run: timing ? args => measure('host.' + name, () => run(args)) : run}});
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
  const instrumentation={modules:1,instances:0};
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
          instrumentation.modules++;instrumentation.instances++;
        }
        const wrapper = new WebAssembly.Instance(observer, {env, trace: {
          code: codeId, failed: (...args) => { failed(...args); if (firstFailure?.code === codeId) firstFailure.file = path; },
          entered, returned, ...exports}});
        instrumentation.instances++;
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
        instrumentation.modules++;instrumentation.instances++;
      }
      const wrapper = new WebAssembly.Instance(observer, {env, trace: {code: row.code_id, failed, entered, returned, ...instance.exports}});
      instrumentation.instances++;
      env.table.set(row.slot, wrapper.exports.entry); env.tail_table.set(row.slot, wrapper.exports.tail_entry);
    }
    assert(!workerData.inspectCode || observation || workerData.inspectCode > Math.max(...codeSet.modules.map(r => r.code_id)),
      'requested diagnostic code ID is absent');
  }
  installed.instances=null;
  const index = manifest.roots.names.indexOf('toplevel-function');
  const fn = get(manifest.roots.start + index * 4), id = get(fn - 2) >>> 2;
  assert.equal(get(fn - 6), 1578);
  let result;
  timing?.memory('lisp-start', heapState());
  try {
    const values = measure('lisp.run', () => env.table.get(expected.slots[id])(fn, 0));
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
  const abandonedSessions=loader.closeSessions();
  timing?.memory(result.ready ? 'READY' : 'STOPPED', heapState());
  timing?.finish();
  parentPort.postMessage({...result, boot0: handoff, firstFailure, terminalFailureChain, recentFailures, firstCheck, firstCondition, observation, traceFrom: workerData.traceFrom ?? null, loadEvents, entry: '%TOPLEVEL-FUNCTION%', modules: codeSet.modules.length,
    productModules:5+(bootIsArchive?1:codeSet.modules.length)+loader.productCounts().modules,
    productInstances:9+(bootIsArchive?1:codeSet.modules.length)+loader.productCounts().instances,
    instrumentation,
    abandonedSessions,inputOwnership:inputState(),archiveStorage:loader.archives(),openFiles:loader.openFiles(),
    heapDigest: manifest.heap.digest, codeDigest: manifest.codeDigest, collections: owner.collectionCount,
    environment: {node: process.version, runner: workerData.scripts[new URL(import.meta.url).pathname], scripts: workerData.scripts,
      observer: sha256(fs.readFileSync(out + '/observe.wasm')),
      runtime: Object.fromEntries(['collector', 'integer', 'float', 'detector'].map(name => [name, sha256(binary(name))]))},
    level1CrossLoaded: false, targetLoadedFiles: completedLoads.length, completedLoads,
    execution: execution(), classErrorTransition, conditionCalls, outputEvents, callbackEvents,
    errorServiceMode: get(tcr + 192), collectionInhibition: owner.collectionInhibition,
    collectionPending: owner.collectionPending,
    startupLoads: workerData.startupLoads, omittedBundles: workerData.omittedBundles,
    bundleInputs: workerData.files.map(({path, sha256}) => ({path, sha256}))});
}
