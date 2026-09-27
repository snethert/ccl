// Separate forced-GC diagnostic, never part of timed startup or correctness.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {MessageChannel} from 'node:worker_threads';
import {writeHeapSnapshot} from 'node:v8';
import {sha256} from '../../../../runtime/wasm32/sha256.mjs';
import {bundleNamespace,targetLoadSession} from '../../../../runtime/wasm32/target-load-session.mjs';
import {encodeTargetContainer} from '../../../../runtime/wasm32/target-bundle.mjs';
import {serviceRequest} from '../../../../runtime/wasm32/file-host.mjs';
import {inputInventory} from '../../../../runtime/wasm32/input-inventory.mjs';
import {readArchiveSource} from './archive-source.mjs';

const [fixture,archiveDir,out]=process.argv.slice(2);
assert(global.gc,'run with --expose-gc');fs.mkdirSync(out,{recursive:true});
const read=n=>JSON.parse(fs.readFileSync(fixture+'/'+n)),refs=[],seen=new WeakSet(),inputs=inputInventory();
const mark=(value,label)=>{if(seen.has(value))return;seen.add(value);
 Object.defineProperty(value,'archiveRetentionMarker',{value:label});refs.push({label,ref:new WeakRef(value)});};
const markTree=(value,label)=>{if(!value||typeof value!=='object'||seen.has(value))return;
 mark(value,label);for(const child of Object.values(value))markTree(child,label);};
const markManifest=(value,label)=>{mark(value,label);
 for(const name of ['d2','functions','entries','helpers','helper_sets','helper_bodies','shared_symbols'])markTree(value[name],label+':'+name);
 // Individual unit rows become compact publication metadata; their enclosing
 // validation array must be released.
 mark(value.units,label+':units');};
const onBuffers=(label,values)=>{inputs.release(label);if(values.length){
 values.forEach(v=>mark(v.buffer??v,label));inputs.hold(label,'validation',values);}};
const onManifest=(label,value)=>{inputs.releaseManifest(label);if(value){markManifest(value,label);
 inputs.holdManifest(label,value);}};
const transfer=async bytes=>{const {port1,port2}=new MessageChannel();
 try{const received=new Promise(resolve=>port2.once('message',resolve));port1.postMessage(bytes,[bytes]);
 assert.equal(bytes.byteLength,0);return await received;}finally{port1.close();port2.close();}};

async function exercise(){
 const binaryPath=out+'/source.wasm',metadataPath=out+'/source.json';
 fs.copyFileSync(archiveDir+'/smoke.wasm',binaryPath);fs.copyFileSync(archiveDir+'/smoke.json',metadataPath);
 const source={binaryPath,metadataPath,digest:sha256(fs.readFileSync(binaryPath)),manifestDigest:sha256(fs.readFileSync(metadataPath))};
 let raw=readArchiveSource(source);mark(raw.bytes,'sender');mark(raw.metadata,'metadata');
 let bytes=await transfer(raw.bytes),manifest=JSON.parse(new TextDecoder().decode(raw.metadata));
 mark(bytes,'receiver');markManifest(manifest,'source-manifest');raw=null;
 // Authenticate every read, including after a previously successful delivery.
 const fd=fs.openSync(binaryPath,'r+');fs.writeSync(fd,new Uint8Array([1]),0,1,0);fs.closeSync(fd);
 assert.throws(()=>readArchiveSource(source),/BINARY_DIGEST/);fs.copyFileSync(archiveDir+'/smoke.wasm',binaryPath);
 fs.appendFileSync(metadataPath,' ');assert.throws(()=>readArchiveSource(source),/MANIFEST_DIGEST/);
 fs.copyFileSync(archiveDir+'/smoke.json',metadataPath);assert.equal(readArchiveSource(source).bytes.byteLength,bytes.byteLength);
 const units=manifest.units.map(u=>({name:u.name,wire:u.wire,symbol_count:u.symbol_count}));
 const functions=manifest.function_count,rootCells=manifest.root_cells;
 const payload=new Uint8Array([7,11,19,23]);let container=encodeTargetContainer({units:units.map(u=>u.name),archive_sha256:source.digest,fasl:payload});
 mark(container.buffer,'container');const path='/ccl/test.w32fsl',files=[{path,sha256:sha256(container),bytes:container}];
 const main=bundleNamespace({files,retainCode:false,discardInputs:true});assert(!files[0].bytes);container=null;
 const memory=new WebAssembly.Memory({initial:32,maximum:32769,shared:true}),tcr=1024,registry=4096,args=131072;
 const view=new DataView(memory.buffer),put=(p,v)=>view.setUint32(p,v,true);
 const env={memory,tcr,code_registry:registry,table:new WebAssembly.Table({element:'anyfunc',initial:256}),
  tail_table:new WebAssembly.Table({element:'anyfunc',initial:256}),call_error:new WebAssembly.Tag({parameters:['i32']}),
  type_error:new WebAssembly.Tag({parameters:['i32','i32']}),nonlocal_exit:new WebAssembly.Tag({parameters:['i32']})};
 put(registry,256);put(registry+4,1);
 for(const [o,v] of [[32,2],[8,1],[64,args],[68,args],[72,args+256]])put(tcr+o,v);
 let nextRoot=65536,nextObject=393216;const registered=new Set();
 const owner={atSafepoint:run=>run(owner),reserveRootBlock:n=>{const base=nextRoot;nextRoot+=4*n;
  return {base,count:n,commit(){},release(){nextRoot=base;},register:cells=>cells.forEach(p=>registered.add(p)),unregister:cells=>cells.forEach(p=>registered.delete(p))};}};
 const allocate=n=>{const p=nextObject;nextObject+=Math.ceil(n/8)*8;return p;};
 function encode(v,vector=false){if(v===null)return 77825;if(Number.isInteger(v))return v*4;
  if(typeof v==='string'){const cs=Array.from(v),p=allocate(4+4*cs.length);put(p,256*cs.length+191);cs.forEach((c,i)=>put(p+4+4*i,c.codePointAt(0)));return p+6;}
  assert(Array.isArray(v));if(vector||!v.length){const p=allocate(4+4*v.length);put(p,256*v.length+250);v.forEach((x,i)=>put(p+4+4*i,encode(x)));return p+6;}
  let tail=77825;for(let i=v.length-1;i>=0;i--){const p=allocate(8);put(p,tail);put(p+4,encode(v[i]));tail=p+1;}return tail;}
 const host=main.session();let hostFailure=false,hostRefusal=false;
 const unexpected=()=>{throw Error('unexpected capability');};
 const config={files:[{path,container:main.containers.get(path)}],archives:[{bytes,manifest,digest:source.digest}],
  memory,env,owner,versions:read('versions.json'),policy:read('policy.json'),nextCode:16,nextSlot:24,generations:3,
  capabilities:{owner:{ensure:unexpected},integer:{calculate:unexpected},floating:{calculate:unexpected}},
  pinned:[{start:393216,end:1048576}],onBuffers,onManifest,
  post:({lifetime,generation})=>{if(hostFailure)throw Error('HOST_FAILURE');
   assert(serviceRequest(memory,hostRefusal?{...host,open(){throw Object.assign(Error('missing'),{code:'NOT_FOUND'});}}:host,lifetime,generation));}};
 const rejected={bytes:bytes.slice(0),manifest:structuredClone(manifest),digest:source.digest};
 rejected.manifest.entries[0].body_sha256='0'.repeat(64);mark(rejected.bytes,'failed-input');markManifest(rejected.manifest,'failed-manifest');
 await assert.rejects(()=>targetLoadSession({...config,archives:[rejected]}),/BODY_DIGEST/);
 assert.equal(rejected.bytes,null);assert.equal(rejected.manifest,null);
 assert.equal(inputs.snapshot().bytes,0);assert.equal(inputs.snapshot().validationManifests,0);
 const loader=await targetLoadSession(config);
 assert.equal(bytes.byteLength,0);bytes=null;manifest=null;
 const request=(op,a,b=0,c=0)=>{[op*4,a,b,c].forEach((v,i)=>put(args+4*i,v));return loader.file(args)>>2;};
 const pathWord=encode(path),open=()=>request(0,pathWord),close=fd=>request(3,fd*4);
 hostFailure=true;assert.throws(open,/HOST_FAILURE/);hostFailure=false;assert.equal(loader.archives()[0].openSessions,0);
 hostRefusal=true;assert(open()<0);hostRefusal=false;assert.equal(loader.archives()[0].openSessions,0);
 const unit=units[0],row=read('records.json').units.find(r=>r.name===unit.wire),record=encode(row.install_record??row.record);
 const symbols=encode(Array(unit.symbol_count).fill(null),true);
 for(let i=0;i<unit.symbol_count;i++){const p=allocate(32);put(p,1850);put(p+28,4);put(symbols-2+4*i,p+6);}
 const install=fd=>{[record,symbols,fd*4].forEach((v,i)=>put(args+4*i,v));return loader.install(args);};
 const first=open(),overlap=open();assert.equal(loader.archives()[0].generations,2);
 const code1=install(first);close(overlap);assert.equal(loader.archives()[0].openSessions,1);
 const partial=open();assert.equal(loader.archives()[0].generations,2);const code2=install(partial);
 close(first);close(partial);assert.notEqual(code1,code2);assert.equal(loader.archives()[0].openSessions,0);
 const third=open();const code3=install(third);assert.notEqual(code3,code2);
 assert.deepEqual(loader.closeSessions(),[path]);host.close(third);assert.deepEqual(loader.openFiles(),[]);
 assert.equal(loader.archives()[0].openSessions,0);assert.equal(loader.archives()[0].generations,3);
 assert.throws(()=>install(third),/CLOSED_SESSION/);
 assert.equal(inputs.snapshot().bytes,0);assert.equal(inputs.snapshot().validationManifests,0);
 assert.deepEqual(loader.ownership(),{fasl:{bytes:0,count:0},v1Bundles:{bytes:0,count:0}});
 for(let i=0;i<3;i++){const fd=host.open(path,'read');assert.deepEqual(host.read(fd,4),payload);host.close(fd);}
 return {loader,main,env,report:{functions,rootCells,codeIds:[code1,code2,code3].map(n=>n/4),registeredRoots:registered.size,
  storage:loader.archives(),mainOwnership:main.ownership(),workerOwnership:inputs.snapshot()}};
}
const alive=await exercise();globalThis.retentionPositiveControl={archiveRetentionMarker:'positive-control'};
// Let promise reactions and the WeakRef keep-alive job finish before collecting.
for(let i=0;i<8;i++){await new Promise(resolve=>setImmediate(resolve));global.gc();}
await new Promise(resolve=>setImmediate(resolve));
const retained=refs.filter(({ref})=>ref.deref()).map(({label})=>label);
const snapshotPath=writeHeapSnapshot(out+'/retention.heapsnapshot');
const heap=JSON.parse(fs.readFileSync(snapshotPath)),meta=heap.snapshot.meta,nf=meta.node_fields,ef=meta.edge_fields;
const nodeWidth=nf.length,edgeWidth=ef.length,edgeCount=nf.indexOf('edge_count'),edgeName=ef.indexOf('name_or_index'),edgeType=ef.indexOf('type');
let edgeOffset=0;const markerOwners=[];
for(let n=0;n<heap.nodes.length;n+=nodeWidth){
 for(let i=0;i<heap.nodes[n+edgeCount];i++,edgeOffset+=edgeWidth)
  if(meta.edge_types[edgeType][heap.edges[edgeOffset+edgeType]]==='property'&&heap.strings[heap.edges[edgeOffset+edgeName]]==='archiveRetentionMarker')
   markerOwners.push({id:heap.nodes[n+nf.indexOf('id')],name:heap.strings[heap.nodes[n+nf.indexOf('name')]],
    marker:heap.strings[heap.nodes[heap.edges[edgeOffset+ef.indexOf('to_node')]+nf.indexOf('name')]]});
}
const report={status:retained.length===0&&markerOwners.length===1&&markerOwners[0].marker==='positive-control'?'PASS':'FAIL',...alive.report,
 trackedObjects:refs.length,retained,markerOwners,snapshotSha256:sha256(fs.readFileSync(snapshotPath)),
 checks:['sender detachment','archive reread digest','manifest reread digest','failed admission releases inputs','host throw releases reservation','host refusal releases reservation',
 'overlapping LOAD','partial close and generation reuse','three generations with distinct IDs','terminal session release','main FASL rereads after release',
 'WeakRef reachability','heap snapshot property edges with retained positive control'],
 scope:'Forced-GC diagnostic of application retention; engine-internal code storage is not partitioned.'};
fs.writeFileSync(out+'/result.json',JSON.stringify(report,null,2)+'\n');assert.equal(report.status,'PASS',JSON.stringify(retained));console.log(JSON.stringify(report));
