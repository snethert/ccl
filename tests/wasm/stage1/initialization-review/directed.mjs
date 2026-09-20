import fs from 'node:fs';
import assert from 'node:assert/strict';
import {Worker,isMainThread,parentPort,workerData} from 'node:worker_threads';
import {InitializationOwner} from './owner.mjs';
import {sha} from './loader.mjs';
import {modules,layout} from './check.mjs';
const tables=(n=8,t=8)=>({table:new WebAssembly.Table({element:'anyfunc',initial:n}),tail_table:new WebAssembly.Table({element:'anyfunc',initial:t})});
const memory=()=>new WebAssembly.Memory({initial:32769,maximum:32769,shared:true});
function make(mem,l,mods,ts=tables()){return new InitializationOwner({memory:mem,layout:l,layoutDigest:sha(JSON.stringify(l)),modules:mods,...ts});}
const state=(mem)=>new Int32Array(mem.buffer,2048,32);
const fingerprint=(mem,l)=>l.regions.map(r=>[r.name,sha(new Uint8Array(mem.buffer,r.start,r.size))]);
if(!isMainThread){
 const {dir,mem,l,mode,gate}=workerData,mods=modules(dir),o=make(mem,l,mods),g=new Int32Array(gate);
 parentPort.postMessage('ready');Atomics.wait(g,0,0,10000);
 try{
  const callback=()=>{Atomics.add(g,2,1);parentPort.postMessage('entered');assert.equal(Atomics.wait(g,1,0,10000),'ok','race released');};
  if(mode==='process')o.process(0,callback);else o.worker(1,callback);
  parentPort.postMessage({status:'ADMITTED'});
 }catch(e){parentPort.postMessage({status:'REFUSED',reason:e.message});}
}else{
 const dir=process.argv[2],mods=modules(dir),rows=[];
 async function race(mem,l,mode){
  const gate=new SharedArrayBuffer(16),g=new Int32Array(gate);let ready=0,entered=0;const answers=[];
  const ws=Array.from({length:3},()=>new Worker(new URL(import.meta.url),{workerData:{dir,mem,l,mode,gate}}));
  const exits=ws.map(w=>new Promise((resolve,reject)=>{w.once('exit',c=>c===0?resolve():reject(Error('race exit '+c)));}));
  await new Promise((resolve,reject)=>{
   const timer=setTimeout(()=>reject(Error('race timeout')),20000);
   for(const w of ws){w.on('error',reject);w.on('message',m=>{
    if(m==='ready'){if(++ready===3){Atomics.store(g,0,1);Atomics.notify(g,0);}}
    else if(m==='entered')entered++;
    else answers.push(m);
    if(answers.filter(x=>x.status==='REFUSED').length===2&&entered===1){Atomics.store(g,1,1);Atomics.notify(g,1);}
    if(answers.length===3){clearTimeout(timer);resolve();}
   });}
  });
  await Promise.all(exits);
  assert.equal(g[2],1,'single callback');assert.equal(answers.filter(x=>x.status==='ADMITTED').length,1);
  const rejected=answers.filter(x=>x.status==='REFUSED');assert.equal(rejected.length,2);
  for(const r of rejected)assert((mode==='process'?['PROCESS_STATE','CONTROL_NOT_FRESH']:['WORKER_STATE']).includes(r.reason),r.reason);
  return {mode,callbacks:1,admitted:1,refused:2}; // scheduling-dependent busy diagnostics are not evidence of a different outcome
 }
 for(const base of [4194304,2147483648]){
  const mem=memory(),l=layout(dir,base,mods),s=state(mem),o=make(mem,l,mods);let callbacks=0;
  const counts={table:0,fresh:0,reserved:0,phase:0};
  // Full declared capacity must be backed, even if all used slots would fit.
  for(const phase of ['fresh','ready']){
   if(phase==='ready')o.process(0,()=>{});
   for(const [a,b]of [[0,8],[5,8],[6,8],[7,8],[8,0],[8,5],[8,6],[8,7]]){
    const before=fingerprint(mem,l),ts=tables(a,b),tb=[ts.table.length,ts.tail_table.length];
    assert.throws(()=>make(mem,l,mods,ts),/ACTUAL_TABLE_CAPACITY/,'actual table '+a+'/'+b+' '+phase);
    assert.deepEqual(fingerprint(mem,l),before,'capacity refusal before claim or initialization');assert.deepEqual([ts.table.length,ts.tail_table.length],tb);counts.table++;
   }
   for(const missing of ['table','tail_table']){const ts=tables();delete ts[missing];const before=fingerprint(mem,l);assert.throws(()=>make(mem,l,mods,ts),/ACTUAL_TABLE_CAPACITY/,'missing actual table');assert.deepEqual(fingerprint(mem,l),before);counts.table++;}
  }
  // Restore only in the test: production has no reset from ready/failed states.
  s.fill(0);
  for(let byte=4;byte<128;byte++){
   const bytes=new Uint8Array(mem.buffer,2048,128);bytes[byte]=0x80;const before=fingerprint(mem,l);
   assert.throws(()=>o.process(0,()=>callbacks++),/CONTROL_(RESERVED|NOT_FRESH)/,'dirty fresh byte '+byte);
   assert.equal(s[0],0,'dirty bootstrap not claimed');assert.deepEqual(fingerprint(mem,l),before,'dirty fresh state preserved');bytes[byte]=0;counts.fresh++;
  }
  for(const value of [1,3,4,-1]){s[0]=value;const before=fingerprint(mem,l);assert.throws(()=>o.process(0,()=>callbacks++),/PROCESS_STATE/);assert.deepEqual(fingerprint(mem,l),before);counts.phase++;}s[0]=0;
  assert.equal(callbacks,0);assert.equal(o.process(0,()=>callbacks++),true);assert.equal(callbacks,1);
  // Every reserved byte stays zero after bootstrap and is checked on both APIs.
  const reserved=[];for(let byte=4;byte<128;byte++)if(!(byte>=8&&byte<40)&&!(byte>=64&&byte<76))reserved.push(byte);
  for(const byte of reserved){
   const bytes=new Uint8Array(mem.buffer,2048,128);bytes[byte]=0x80;const before=fingerprint(mem,l);
   assert.throws(()=>o.process(0,()=>callbacks++),/CONTROL_RESERVED/,'dirty ready process byte '+byte);
   assert.throws(()=>o.worker(1,()=>callbacks++),/CONTROL_RESERVED/,'dirty ready Worker byte '+byte);
   assert.equal(s[17],0);assert.deepEqual(fingerprint(mem,l),before,'reserved control refusal preserved');bytes[byte]=0;counts.reserved+=2;
  }
  assert.equal(callbacks,1);o.worker(1,()=>callbacks++);assert.equal(callbacks,2);assert.deepEqual(Array.from(s.slice(16,19)),[2,2,0]);
  // Already-live states are allowed; failed state cannot be reused.
  assert.equal(o.process(0,()=>callbacks++),false);assert.throws(()=>o.worker(1,()=>callbacks++),/WORKER_STATE/);
  assert.throws(()=>o.worker(2,()=>{throw Error('failed worker');}),/failed worker/);assert.throws(()=>o.worker(2,()=>callbacks++),/WORKER_STATE/);assert.equal(s[0],2);assert.equal(s[18],3);assert.equal(callbacks,2);
  const bigger=make(mem,l,mods,tables(9,16));assert.equal(bigger.process(0,()=>callbacks++),false);
  for(const byte of reserved)assert.equal(new Uint8Array(mem.buffer,2048,128)[byte],0);
  // Races use fresh memory and Worker-local actual table objects.
  const rm=memory(),races=[await race(rm,l,'process'),await race(rm,l,'worker')];
  rows.push({base,counts,callbacks,larger_tables:true,failed_worker_terminal:true,races});
 }
 fs.writeFileSync(process.argv[3],JSON.stringify({status:'PASS',rows},null,2)+'\n');
}
