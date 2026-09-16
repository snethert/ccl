import fs from 'node:fs';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import {Worker,isMainThread,parentPort,workerData} from 'node:worker_threads';
if(isMainThread){
 const [directory,out]=process.argv.slice(2);
 const result=await new Promise((resolve,reject)=>{const w=new Worker(new URL(import.meta.url),{workerData:{directory}});w.once('message',resolve);w.once('error',reject);w.once('exit',code=>{if(code)reject(Error(`Worker exit ${code}`));});});
 fs.writeFileSync(out,JSON.stringify(result,null,2)+'\n');console.log('S1-REPRESENTATION-WASM-PASS');
}else{
 const {directory}=workerData;const cases=JSON.parse(fs.readFileSync(`${directory}/cases.json`));
 // This oracle deliberately does not read the generator's schema/offset descriptions.
 const NIL=77825,TRUE=77838,TCR=256,VSP=2048,MV=4096;
 const memory=new WebAssembly.Memory({initial:2,maximum:32769,shared:true});
 const typeError=new WebAssembly.Tag({parameters:['i32','i32']});
 const modules=new Map();for(const c of cases)if(!modules.has(c.function))modules.set(c.function,await WebAssembly.compile(fs.readFileSync(`${directory}/installed/${c.function}.wasm`)));
 const rows=[];const u32=x=>x<0?x+4294967296:x;
 // The high-bit runs are actual dereferences, not merely conversion calculations.
 for(const placement of ['low','cross-2gib','above-2gib','last-aligned']){
  if(placement!=='low' && memory.buffer.byteLength<2147549184)memory.grow(32767);
  const base=placement==='low'?8192:placement==='cross-2gib'?2147483640:placement==='above-2gib'?2147483648:memory.buffer.byteLength-24;
  const view=new DataView(memory.buffer);const prefix=new Uint8Array(memory.buffer,0,131072);
  const encode=v=>typeof v==='number'?u32(v*4):v==='nil'?NIL:v==='t'?TRUE:base+8*Number(v.slice(1))+1;
  for(const c of cases){
   prefix.fill(0x5a);const guardStart=base-16;const guard=new Uint8Array(memory.buffer,guardStart,Math.min(64,memory.buffer.byteLength-guardStart));guard.fill(0xa5);
   const set=(a,v)=>view.setUint32(a,u32(v),true),get=a=>view.getUint32(a,true);
   set(TCR+64,VSP);set(TCR+120,MV);set(TCR+124,MV+16);
   // Canonical NIL contains poison, making a missing NIL branch independently observable.
   set(NIL-1,0x11223344);set(NIL+3,0x55667788);
   for(let i=0;i<c.nodes.length;i++){set(base+8*i,encode(c.nodes[i][1]));set(base+8*i+4,encode(c.nodes[i][0]));}
   c.args.forEach((v,i)=>set(VSP+4*i,encode(v)));
   const before=prefix.slice(),guardBefore=guard.slice();
   const instance=await WebAssembly.instantiate(modules.get(c.function),{env:{memory,tcr:TCR,type_error:typeError}});
   assert.deepEqual(prefix,before,`${c.id}: instantiation wrote prefix`);assert.deepEqual(guard,guardBefore,`${c.id}: instantiation wrote graph`);
   let status,result;
   try{result=instance.exports.entry(0,3);status='RETURN';}
   catch(e){if(!(e instanceof WebAssembly.Exception)||!e.is(typeError))throw new Error(`${placement}/${c.id}: unexpected target failure`,{cause:e});status='TYPE_ERROR';result=[u32(e.getArg(typeError,0)),e.getArg(typeError,1)];}
   const label=`${placement}/${c.id}`;assert.equal(status,c.expected.status,label+': status');
   if(status==='RETURN'){
    assert.deepEqual(result.map(u32),[encode(c.expected.value),1],label+': result');
    assert.equal(get(MV),encode(c.expected.value),label+': result ownership');assert.equal(get(TCR+116),1,label+': count');
   }else{
    assert.equal(result[0],encode(c.expected.datum),label+': condition datum');assert.equal(result[1],c.expected.expected_kind,label+': condition type');
   }
   const expectedPrefix=before.slice(),expectedGuard=guardBefore.slice();
   const put=(addr,value)=>{if(addr<expectedPrefix.length)new DataView(expectedPrefix.buffer).setUint32(addr,value,true);if(addr>=guardStart&&addr+4<=guardStart+expectedGuard.length)new DataView(expectedGuard.buffer).setUint32(addr-guardStart,value,true);};
   for(let i=0;i<c.nodes.length;i++){put(base+8*i,encode(c.expected.nodes[i][1]));put(base+8*i+4,encode(c.expected.nodes[i][0]));}
   if(status==='RETURN'){put(MV,encode(c.expected.value));put(TCR+116,1);}
   assert.deepEqual(prefix,expectedPrefix,label+': memory outside intended fields');assert.deepEqual(guard,expectedGuard,label+': graph/guard bytes');
   rows.push({case:c.id,placement,status,result:status==='RETURN'?result.map(u32):result,graph_sha256:crypto.createHash('sha256').update(guard).digest('hex')});
  }
  // Probe every fulltag with deliberately forged values. These target-only
  // representation probes are distinct from the native Lisp comparisons.
  for(let tag=0;tag<8;tag++)for(const operation of ['car','cdr','rplaca','rplacd']){
   prefix.fill(0x5a);const guardStart=base-16,guard=new Uint8Array(memory.buffer,guardStart,Math.min(64,memory.buffer.byteLength-guardStart));guard.fill(0xa5);
   const set=(a,v)=>view.setUint32(a,u32(v),true);set(TCR+64,VSP);set(TCR+120,MV);set(TCR+124,MV+16);
   set(base,encode(-7));set(base+4,encode(13));set(VSP,base+tag);set(VSP+4,encode(29));set(VSP+8,encode(-33));
   const before=prefix.slice(),guardBefore=guard.slice(),valid=tag===1;
   const instance=await WebAssembly.instantiate(modules.get(operation),{env:{memory,tcr:TCR,type_error:typeError}});
   assert.deepEqual(prefix,before);assert.deepEqual(guard,guardBefore);
   const label=`${placement}/raw-tag-${tag}/${operation}`;let result;
   try{result=instance.exports.entry(0,3);assert.ok(valid,label+': invalid tag admitted');}
   catch(e){if(e instanceof WebAssembly.Exception && e.is(typeError)){
     assert.ok(!valid,label+': valid tag refused');assert.equal(u32(e.getArg(typeError,0)),base+tag,label+': datum');assert.equal(e.getArg(typeError,1),operation.startsWith('rplac')?2:1,label+': kind');
   }else throw e;}
   const expected=operation==='car'?encode(13):operation==='cdr'?encode(-7):base+1;
   const expectedPrefix=before.slice(),expectedGuard=guardBefore.slice();
   const put=(a,v)=>{if(a<expectedPrefix.length)new DataView(expectedPrefix.buffer).setUint32(a,v,true);if(a>=guardStart&&a+4<=guardStart+expectedGuard.length)new DataView(expectedGuard.buffer).setUint32(a-guardStart,v,true);};
   if(valid){assert.deepEqual(result.map(u32),[expected,1],label+': values');put(MV,expected);put(TCR+116,1);if(operation==='rplaca')put(base+4,encode(29));if(operation==='rplacd')put(base,encode(29));}
   assert.deepEqual(prefix,expectedPrefix,label+': prefix');assert.deepEqual(guard,expectedGuard,label+': guard');
   rows.push({case:`raw-tag-${tag}/${operation}`,placement,status:valid?'RETURN':'TYPE_ERROR',synthetic_tag_probe:true});
  }
 }
 parentPort.postMessage({status:'PASS',worker_count:1,memory_pages:memory.buffer.byteLength/65536,modules:modules.size,cases:rows,scope:'Independent raw CDR-first fixture; all low memory and graph guard bytes compared. High runs compare the low prefix and graph guard, not every untouched byte of 2 GiB. Typed Wasm exception boundary only, not the Lisp condition system.'});
}
