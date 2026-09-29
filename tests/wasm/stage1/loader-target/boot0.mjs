// Call the real bootstrap once. A failure ends this Worker; no initializer is
// skipped and no definition or binding is filled in by the harness.
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import assert from 'node:assert/strict';
import {Worker, isMainThread, parentPort, workerData} from 'node:worker_threads';
import {sha256} from '../../../../runtime/wasm32/sha256.mjs';
import {observeChecks} from './diagnose.mjs';
import {bundleNamespace} from '../../../../runtime/wasm32/target-load-session.mjs';
import {serviceRequest} from '../../../../runtime/wasm32/file-host.mjs';
import {inputInventory} from '../../../../runtime/wasm32/input-inventory.mjs';
import {archiveSource,readArchiveSource} from './archive-source.mjs';
import {startupTiming} from './startup-timing.mjs';
import {benchmarkObserver} from '../execution-bench/observe.mjs';
import {pathToFileURL} from 'node:url';

const timingPrefix = isMainThread ? process.argv.find(a => a.startsWith('--timing='))?.slice(9) : workerData.timingPrefix;
const timing = startupTiming(timingPrefix, isMainThread ? 'main' : 'worker');
const measure = timing?.measure ?? ((_phase, run) => run());
const inputs=inputInventory();

if (isMainThread) {
  const runtimeDirectory = new URL('../../../../runtime/wasm32/', import.meta.url);
  const scripts = Object.fromEntries([new URL(import.meta.url), new URL('./boot-worker.mjs', import.meta.url), new URL('./diagnose.mjs', import.meta.url), new URL('./startup-timing.mjs', import.meta.url),
    new URL('../execution-bench/observe.mjs', import.meta.url),
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
  const postReadyLoads = process.argv.filter(a => a.startsWith('--post-ready-load=')).map(a => a.slice(18));
  const benchmarkEvents = process.argv.includes('--benchmark-events');
  // Optional fixture capability, shared by later runtime units. It wraps the
  // declared process-service entry without rewriting generated code or this
  // driver. Its module and configuration are bound in the report.
  const hostExtension=process.argv.find(a=>a.startsWith('--host-extension='))?.slice(17);
  const extensionConfig=JSON.parse(process.argv.find(a=>a.startsWith('--extension-config='))?.slice(19)??'{}');
  if(hostExtension)scripts[hostExtension]=sha256(fs.readFileSync(hostExtension));
  const callbackSelection = JSON.parse(fs.readFileSync(new URL('../startup-resets/selection.json', import.meta.url)));
  const workerFiles=files.map(({path,sha256,sourceDir,bytes})=>{const container=namespace.containers.get(path);
    return {path,sha256,sourceDir,...(container?{container}:{bytes})};});
  timing?.event('worker-send',{inputOwnership:ownedInputs()});
  const worker = measure('worker.construct', () => new Worker(new URL(import.meta.url), {workerData: {out, runtime, trace, traceFrom, inspectCode,
    files:workerFiles,archives:archives.map(directory),bootArchive:bootArchive?directory(bootArchive):null,
    layoutConfig, dumpFailure, startupLoads, postReadyLoads, omittedBundles, callbackSelection, scripts, timingPrefix, benchmarkEvents, hostExtension, extensionConfig}}));
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
  const {runBoot}=await import('./boot-worker.mjs');
  await runBoot({workerData,parentPort,assert,timing,observeChecks,benchmarkObserver,
    readFile:name=>fs.readFileSync(name),writeFile:(name,data)=>fs.writeFileSync(name,data),
    output:(channel,text)=>fs.writeSync(channel,text),
    // macOS supplies timezone history/DST as an embedding capability.
    calendar:seconds=>JSON.parse(execFileSync('/usr/bin/python3',['-c',
      'import time,json,sys; t=time.localtime(int(sys.argv[1])); print(json.dumps(dict(minutesWest=(-t.tm_gmtoff)//60,daylight=t.tm_isdst>0)))',
      String(seconds)],{encoding:'utf8'})),
    cpuTime:()=>process.cpuUsage(),
    environment:{node:process.version,v8:process.versions.v8,execArgv:process.execArgv},
    createExtension:workerData.hostExtension?(await import(pathToFileURL(workerData.hostExtension))).create:null});
}
