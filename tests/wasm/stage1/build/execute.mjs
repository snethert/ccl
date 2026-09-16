import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {Worker,isMainThread,parentPort,workerData} from 'node:worker_threads';
import {pathToFileURL} from 'node:url';
import {preflight,install,sha,roles} from './loader.mjs';
if(isMainThread){
  const [root,reporterFile,output]=process.argv.slice(2);
  const result=await new Promise((resolve,reject)=>{const w=new Worker(new URL(import.meta.url),{workerData:{root,reporterFile}});w.once('message',resolve);w.once('error',reject);w.once('exit',c=>{if(c)reject(Error('WORKER_EXIT '+c));});});
  fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n');console.log('S1-BUILD-DIAGNOSTICS-PASS');
}else{
  const {root,reporterFile}=workerData,manifestBytes=fs.readFileSync(path.join(root,'build.json')),buildID=sha(manifestBytes);
  const build=preflight(root,manifestBytes,buildID),manifest=build.manifest,controls=[];
  const reject=(name,fn,reason)=>{assert.throws(fn,e=>String(e.message).startsWith(reason),name);controls.push({name,status:'REJECTED',reason});};
  reject('wrong-build',()=>preflight(root,manifestBytes,'0'.repeat(64)),'BUILD_IDENTITY');
  for(const role of roles){const m=structuredClone(manifest);m.files=m.files.filter(x=>x.role!==role);const b=Buffer.from(JSON.stringify(m));reject('omit-'+role,()=>preflight(root,b,sha(b)),'BUILD_ROLE');}
  for(const role of roles){const m=structuredClone(manifest);m.files.find(f=>f.role===role).sha256='0'.repeat(64);const b=Buffer.from(JSON.stringify(m));reject('stale-'+role,()=>preflight(root,b,sha(b)),'BUILD_FILE_IDENTITY');}
  for(const [name,mutate,reason] of [
    ['duplicate-slot',m=>m.entries[1].slot=m.entries[0].slot,'BUILD_ENTRY'],
    ['duplicate-code',m=>m.entries[1].logical_code_id=m.entries[0].logical_code_id,'BUILD_ENTRY'],
    ['wrong-signature',m=>m.entries[0].signature='(i32)->(i32)','BUILD_ENTRY'],
    ['wrong-entry-kind',m=>m.entries[0].entry_kind='C','BUILD_ENTRY'],
    ['missing-module',m=>m.entries[0].module='absent.wasm','BUILD_INSTALL_IDENTITY'],
    ['mixed-binary',m=>m.entries[0].binary=m.entries[1].binary,'BUILD_INSTALL_IDENTITY'],
    ['source-role-substitution',m=>m.entries[0].source=m.entries[0].template,'BUILD_ENTRY_ARTIFACT'],
    ['escaped-path',m=>m.files[0].path='../outside','BUILD_PATH'],
    ['duplicate-artifact',m=>m.files.push(m.files[0]),'BUILD_PATH']]){
    const m=structuredClone(manifest);mutate(m);const b=Buffer.from(JSON.stringify(m));reject(name,()=>preflight(root,b,sha(b)),reason);
  }
  const memory=new WebAssembly.Memory({initial:1,maximum:32769,shared:true}),view=new DataView(memory.buffer),tcr=256;
  const installed=await install(build,memory,tcr);
  const offsets=Object.fromEntries(JSON.parse(fs.readFileSync(path.join(root,'schemas/tcr.json'))).fields.map(f=>[f.name,f.offset]));
  function reset(){new Uint8Array(memory.buffer).fill(0);view.setUint32(tcr+offsets.vsp,2048,true);view.setUint32(tcr+offsets.mv_base,4096,true);view.setUint32(tcr+offsets.mv_limit,4112,true);}
  const positive=[];
  for(const c of JSON.parse(fs.readFileSync(path.join(root,'native/generated-cases.json')))){
    reset();for(let i=0;i<c.args.length;i++)view.setInt32(2048+i*4,c.args[i],true);
    const e=installed.entries.find(e=>e.name===c.name),actual=installed.invoke(e,0,c.arity);
    assert.deepEqual(actual,[c.expected,1]);assert.equal(view.getInt32(4096,true),c.expected);
    positive.push({name:c.name,args:c.args,values:actual,code:e.logical_code_id,slot:e.slot});
  }
  const e=installed.entries.find(e=>e.name==='identity'),other=installed.entries.find(e=>e.name==='constant');
  installed.table.set(e.slot,other.entry);reject('corrupt-installed-slot',()=>installed.invoke(e,0,1),'INSTALLED_SLOT_IDENTITY');installed.table.set(e.slot,e.entry);
  const {reporter}=await import(pathToFileURL(reporterFile));
  const identity={manifest_sha256:buildID,binary_sha256:sha(e.bytes),module:e.name};
  const context={logical_code_id:other.logical_code_id,event_id:'previous-function'};
  function fault(mode){reset();if(mode==='load')view.setUint32(tcr+offsets.vsp,65536,true);if(mode==='store')view.setUint32(tcr+offsets.mv_base,65536,true);
    try{installed.invoke(e,0,mode==='arity'?2:1);throw Error('EXPECTED_WASM_TRAP');}catch(err){assert(err instanceof WebAssembly.RuntimeError);return err;}}
  const diag=reporter(identity,e.map),observations=[];
  for(const mode of ['load','store','arity'])observations.push({mode,diagnostic:diag.capture(fault(mode),context)});
  for(let i=0;i<22;i++)diag.capture(fault('store'),context);
  assert.equal(diag.report.failures,25);assert.equal(diag.report.dropped,22);assert.equal(diag.report.errors.length,3);
  assert.deepEqual(diag.report.first_failure,observations[0].diagnostic);assert(Buffer.byteLength(JSON.stringify(diag.report))<=8192);
  for(const row of observations){const d=row.diagnostic;assert.equal(d.classification,'WASM_FAULT');assert.equal(d.fault.logical_code_id,e.logical_code_id);assert.equal(d.fault.entry_kind,'B');assert.equal(d.fault.signature,e.signature);assert.equal(d.fault.slot,e.slot);assert.equal(d.last_observed.attribution,'CONTEXT_ONLY');}
  const unavailable=[];
  for(const mode of ['hidden','unreadable-top']){const err=fault('load');err.stack=mode==='hidden'?'no engine stack':'RuntimeError: bad\n    at wasm://unreadable\n    at wasm://wasm/abc:wasm-function[0]:0x55';const d=reporter(identity,e.map).capture(err,context);assert.equal(d.classification,'UNAVAILABLE');assert.equal(d.fault,null);unavailable.push({mode,diagnostic:d});}
  parentPort.postMessage({status:'PASS',engine:{node:process.version,v8:process.versions.v8},build:identity,controls,positive,observations,unavailable,report:diag.report,diagnostic_bytes:Buffer.byteLength(JSON.stringify(diag.report)),map:e.map,scope:'Compiler-generated leaf entries, installed in actual B-signature slots; no Lisp condition, bootstrap heap, GC or general ABI qualification.'});
}
