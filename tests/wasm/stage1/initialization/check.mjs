import fs from 'node:fs';
import assert from 'node:assert/strict';
import {Worker,isMainThread,parentPort,workerData} from 'node:worker_threads';
import {InitializationOwner} from './owner.mjs';
import {LazyLoader,PROFILE,sha} from './loader.mjs';
import {inspect} from './binary.mjs';
const NIL=77825,T=77838,REG=4096,POOL=2097152;
const read=(dir,n)=>JSON.parse(fs.readFileSync(dir+'/'+n));
function modules(dir){return read(dir,'compiled/modules.json').map((m,i)=>{
 const bytes=fs.readFileSync(dir+'/compiled/'+m.name+'.wasm'),x=inspect(bytes),record={name:m.name,slot:i+1,code:i+1,version:4,signature:17,role:23,profile:PROFILE,sha256:sha(bytes),imports:x.imports,entries:Object.fromEntries(x.exports.map(e=>[e.name,{role:e.name,index:e.index}]))};
 return {name:m.name,bytes,record};
});}
function layout(dir,base,mods){
 const mat=read(dir,'compiled/materialized.json'),schema=read(dir,'tcr.json');assert.equal(schema.size_bytes,256);
 const fields=Object.fromEntries(schema.fields.map(f=>[f.name,f.offset]));
 const regions=[],writes=[],workerInfo=[];
 function region(name,start,size,owner,alignment=8,minimum=size){regions.push({name,start,size,owner,alignment,minimum});}
 function write(region,owner,offset,words){writes.push({region,owner,offset,words});}
 region('control',2048,128,'process');region('registry',REG,8+16*8,'process');
 region('canonical',77824,64,'process');write('canonical','process',0,[NIL,NIL,1850,...Array(7).fill(NIL)]);
 const image=Buffer.from(mat.image,'hex');if(image.length){region('pools',POOL,image.length,'process');write('pools','process',0,Array.from({length:image.length/4},(_,i)=>image.readUInt32LE(4*i)));}
 region('functions',base,32*mods.length,'process');region('shared-cell',base+256,8,'process');write('shared-cell','process',0,[NIL,NIL]);
 region('runtime-bss',base+512,64,'process');region('shared-staging',base+1024,64,'process');
 const symbols={};const keys=[...new Set(mods.flatMap(m=>m.record.imports.filter(x=>x.module==='symbols').map(x=>x.name)))];
 region('symbols',base+2048,32*keys.length,'process');keys.forEach((k,i)=>{symbols[k]=base+2048+32*i+6;write('symbols','process',32*i,[1850,NIL,NIL,NIL,NIL,NIL,NIL,0]);});
 write('registry','process',0,[8,1]);
 mods.forEach((m,i)=>{write('registry','process',8+16*(i+1),[i+1,4,17,23]);write('functions','process',32*i,[1578,4*(i+1),NIL,4,NIL,NIL,mat.roots[i],0]);});
 for(let id=0;id<3;id++){
  const b=16777216+262144*id,info={id,tcr:b,vsp:b+4096,tsp:b+40960,csp:b+49152,heap:b+53248,tlb:b+57344,cell:b+57600,staging:b+57616};workerInfo.push(info);
  region('tcr-'+id,b,schema.size_bytes,id,schema.alignment);
  for(const [n,size,min]of [['vsp',32768,8192],['tsp',8192,4096],['csp',4096,256],['heap',4096,4096],['tlb',256,256],['cell',8,8],['staging',64,64]])region(n+'-'+id,info[n],size,id,8,min);
  const words=Array(64).fill(0),set=(n,v)=>{assert(n in fields,n);words[fields[n]/4]=v;};
  for(const [n,v]of Object.entries({tcr_index:id,worker_id:id,lifetime_generation:1,tcr_address:b,alloc_pointer:info.heap,alloc_limit:info.heap+4096,alloc_base:info.heap,vsp:info.vsp+512,vsp_base:info.vsp+16,vsp_limit:info.vsp+32768,tsp:info.tsp,tsp_base:info.tsp,tsp_limit:info.tsp+8192,csp:info.csp,csp_base:info.csp,csp_limit:info.csp+4096,tlb_pointer:info.tlb,tlb_limit:64,mv_base:info.vsp+1024,mv_owner_top:info.vsp+1040,root_head:info.vsp+8,next_method_context:NIL,fp_control:7}))set(n,v);
  write('tcr-'+id,id,0,words);write('tlb-'+id,id,0,Array(64).fill(243));write('cell-'+id,id,0,[NIL,NIL]);
 }
 return {version:1,tableCapacity:8,reservedSlots:[0,7],workers:[0,1,2],regions,writes,modules:mods.map(m=>({name:m.name,sha256:m.record.sha256})),workerInfo,base,symbols};
}
const regionBytes=(memory,r)=>new Uint8Array(memory.buffer,r.start,r.size);
const fingerprint=(memory,regions)=>regions.map(r=>[r.name,sha(regionBytes(memory,r))]);
function makeOwner(memory,l,mods){return new InitializationOwner({memory,layout:l,layoutDigest:sha(JSON.stringify(l)),modules:mods});}
if(!isMainThread){
 const {dir,memory,l,id}=workerData,mods=modules(dir),owner=makeOwner(memory,l,mods),w=l.workerInfo[id],v=new DataView(memory.buffer),get=p=>v.getUint32(p,true),put=(p,x)=>v.setUint32(p,x,true);
 const table=new WebAssembly.Table({element:'anyfunc',initial:8}),tail_table=new WebAssembly.Table({element:'anyfunc',initial:8}),call_error=new WebAssembly.Tag({parameters:['i32']}),type_error=new WebAssembly.Tag({parameters:['i32','i32']}),nonlocal_exit=new WebAssembly.Tag({parameters:['i32']});
 const reserve=new WebAssembly.Instance(new WebAssembly.Module(mods[0].bytes),{env:{memory,tcr:w.tcr,table,tail_table,code_registry:REG,call_error,type_error,nonlocal_exit},symbols:l.symbols}).exports.entry;table.set(0,reserve);tail_table.set(0,reserve);
 let loader,entries={},observations=[];
 function install(){
  const validated=owner.modules();fs.mkdirSync(dir+'/installed/'+id,{recursive:true});for(const m of validated)fs.writeFileSync(dir+'/installed/'+id+'/'+m.name+'.wasm',m.bytes);const bytes=new Map(validated.map(m=>[m.name,m.bytes]));
  loader=new LazyLoader({memory,table,tail_table,call_error,nonlocal_exit,catalog:validated.map(m=>m.record),stub:new WebAssembly.Module(fs.readFileSync(dir+'/stub.wasm')),readBytes:n=>bytes.get(n)});
  for(let i=0;i<mods.length;i++)entries[mods[i].name]={self:l.base+32*i+6,fn:loader.defer(mods[i].name,{env:{memory,tcr:w.tcr,table,tail_table,code_registry:REG,call_error,type_error,nonlocal_exit},symbols:l.symbols}).host_entry};
 }
 function invoke(name,args){const e=entries[name],incoming=w.vsp+512,out=w.vsp+1024;put(w.tcr+64,incoming);put(w.tcr+116,0);put(w.tcr+120,out);put(w.tcr+124,out+16);args.forEach((x,i)=>put(incoming+4*i,x));const before=[64,128,140,92].map(o=>get(w.tcr+o));let pair;
  try{pair=e.fn(e.self,args.length);}catch(e){if(e.is?.(call_error))throw Error('checked '+e.getArg(call_error,0)+' '+name);throw e;}
  assert.deepEqual([64,128,140,92].map(o=>get(w.tcr+o)),before,'caller restored');assert.equal(get(w.tcr+116),pair[1]);return Array.from({length:pair[1]},(_,i)=>get(out+4*i));}
 const native=read(dir,'compiled/native.json').map(a=>a.map(x=>4*x));
 function setup(){install();const answer=invoke('worker_init',[entries.read_cell.self,w.cell+1,8]);assert.deepEqual(answer,native[3],'generated private initialization');assert.equal(get(w.tcr+4),id);observations.push(answer);}
 if(id===0){assert.equal(owner.process(0,()=>{install();const answer=invoke('process_init',[l.base+257]);assert.deepEqual(answer,native[0]);observations.push(answer);const b=invoke('worker_init',[entries.read_cell.self,w.cell+1,8]);assert.deepEqual(b,native[3]);observations.push(b);}),true);assert.deepEqual(invoke('mutate',[l.base+257]),native[1]);put(l.base+512,0xdeadbeef);put(l.base+1024,0x13579bdf);}
 else{
  const protectedRegions=l.regions.filter(r=>r.owner!==id&&r.name!=='control'),before=fingerprint(memory,protectedRegions);
  owner.worker(id,setup);assert.deepEqual(fingerprint(memory,protectedRegions),before,'late Worker preserves all foreign regions');
 }
 const reader=invoke('call_reader',[entries.read_cell.self,l.base+257]);assert.deepEqual(reader,native[2],'late generated heap read');observations.push(reader);
 assert.equal(owner.process(0,()=>{throw Error('process initializer repeated');}),false,'process once');
 assert.throws(()=>owner.worker(id,()=>{throw Error('duplicate callback');}),/WORKER_STATE/,'duplicate Worker claim');
 assert.equal(table.get(0),reserve);assert.equal(tail_table.get(0),reserve);
 parentPort.postMessage({id,observations,published:loader.snapshot(),events:loader.events.map(e=>({slot:e.slot,event:e.event})),reserved:true});
 parentPort.on('message',message=>{if(message==='verify'){
  assert.deepEqual(invoke('read_cell',[l.base+257]),native[2]);assert.equal(get(l.base+512),0xdeadbeef);assert.equal(get(l.base+1024),0x13579bdf);assert.equal(table.get(0),reserve);parentPort.postMessage({verified:true,id});
 }else if(message==='stop')parentPort.close();});
}else{
 const dir=process.argv[2],mods=modules(dir),rows=[],refusals=[];
 const spawn=(memory,l,id)=>{const w=new Worker(new URL(import.meta.url),{workerData:{dir,memory,l,id}});const next=()=>new Promise((resolve,reject)=>{w.once('message',resolve);w.once('error',reject);});return {w,next};};
 for(const base of [4194304,2147483648]){
  const memory=new WebAssembly.Memory({initial:32769,maximum:32769,shared:true}),l=layout(dir,base,mods);
  for(const r of l.regions)if(r.owner!=='process')regionBytes(memory,r).fill(0xa5);
  const guards=[];for(const r of l.regions)for(const start of [r.start-8,r.start+r.size])if(start>=0&&!l.regions.some(q=>start<q.start+q.size&&start+8>q.start)){const g={name:'guard-'+start,start,size:8};regionBytes(memory,g).fill(0x5a);guards.push(g);}
  const guardBefore=fingerprint(memory,guards);
  const before=fingerprint(memory,l.regions);makeOwner(memory,l,mods);assert.deepEqual(fingerprint(memory,l.regions),before,'preflight writes nothing');
  const a=spawn(memory,l,0),first=await a.next(),b=spawn(memory,l,1),second=await b.next(),c=spawn(memory,l,2),third=await c.next();
  const ready=a.next();a.w.postMessage('verify');assert.deepEqual(await ready,{verified:true,id:0});
  for(const x of [a,b,c])x.w.postMessage('stop');
  const state=new Int32Array(memory.buffer,2048,32);assert.equal(state[0],2);assert.deepEqual(Array.from(state.slice(16,19)),[2,2,2]);
  assert.equal(new DataView(memory.buffer).getUint32(base+512,true),0xdeadbeef);
  assert.deepEqual(fingerprint(memory,guards),guardBefore,'ownership boundary canaries');
  rows.push({base,canaries:guards.length,workers:[first,second,third],original_worker_rechecked:true,shared:fingerprint(memory,l.regions.filter(r=>r.owner==='process'))});
  const bad=(name,change,reason)=>{
   const copy=structuredClone(l),ms=mods.map(m=>({...m,record:structuredClone(m.record)}));change(copy,ms);
   const before=fingerprint(memory,l.regions);assert.throws(()=>makeOwner(memory,copy,ms),new RegExp(reason),name);assert.deepEqual(fingerprint(memory,l.regions),before,name+' preserved');refusals.push({base,name,reason});
  };
  bad('overlap',x=>x.regions.find(r=>r.name==='vsp-1').start=x.workerInfo[0].vsp,'REGION_OVERLAP');
  bad('undersized-stack',x=>{const r=x.regions.find(r=>r.name==='vsp-1');r.minimum=65536;},'REGION_MINIMUM');
  bad('undersized-tcr',x=>{const t=x.regions.find(r=>r.name==='tcr-1');t.minimum=128;t.size=128;},'TCR_REGION');
  bad('misalignment',x=>x.regions.find(r=>r.name==='tcr-1').start+=4,'REGION_ALIGNMENT');
  bad('unbacked-range',x=>x.regions.find(r=>r.name==='staging-1').start=memory.buffer.byteLength,'REGION_EXTENT');
  bad('shared-write',x=>x.writes.push({region:'runtime-bss',owner:1,offset:0,words:[0]}),'WRITE_AUTHORITY');
  bad('other-worker-write',x=>x.writes.push({region:'cell-0',owner:1,offset:0,words:[0]}),'WRITE_AUTHORITY');
  bad('out-of-range-write',x=>x.writes.push({region:'cell-1',owner:1,offset:8,words:[0]}),'WRITE_EXTENT');
  bad('foreign-stack-pointer',x=>x.writes.find(w=>w.region==='tcr-1').words[68/4]=x.workerInfo[0].vsp+16,'TCR_INITIAL_STATE');
  bad('missing-owned-region',x=>x.regions=x.regions.filter(r=>r.name!=='csp-1'),'WORKER_REGIONS');
  bad('reserved-slot',(x,ms)=>ms[0].record.slot=7,'TABLE_SLOT');
  bad('undersized-table',x=>x.tableCapacity=2,'TABLE_SLOT');
  bad('duplicate-slot',(x,ms)=>ms[1].record.slot=ms[0].record.slot,'TABLE_SLOT');
  bad('code-role',(x,ms)=>ms[0].record.role=0,'CODE_ROLE');
  bad('omitted-module',(x,ms)=>ms.pop(),'MODULE_SET');
  for(const name of ['data','bss-start','element'])bad(name,(x,ms)=>{const m=ms.find(m=>m.name==='read_cell');m.bytes=fs.readFileSync(dir+'/malformed/'+name+'.wasm');m.record.sha256=sha(m.bytes);x.modules.find(m=>m.name==='read_cell').sha256=m.record.sha256;},'INITIALIZATION_OR_SECTION');
  const foreign=structuredClone(l);foreign.regions.find(r=>r.name==='runtime-bss').minimum=32;const foreignOwner=makeOwner(memory,foreign,mods);const beforeForeign=fingerprint(memory,l.regions);assert.throws(()=>foreignOwner.process(0,()=>{}),/PROCESS_IDENTITY/);assert.deepEqual(fingerprint(memory,l.regions),beforeForeign);refusals.push({base,name:'foreign-layout-ready',reason:'PROCESS_IDENTITY'});
  const fresh=new WebAssembly.Memory({initial:32769,maximum:32769,shared:true}),o=makeOwner(fresh,l,mods);assert.throws(()=>o.worker(1,()=>{}),/PROCESS_NOT_READY/);assert.equal(new Int32Array(fresh.buffer,2048,32)[17],0);assert.throws(()=>o.process(0,()=>{throw Error('initializer failed');}),/initializer failed/);assert.equal(new Int32Array(fresh.buffer,2048,32)[0],3);assert.throws(()=>o.process(0,()=>{}),/PROCESS_STATE/);assert.throws(()=>o.worker(1,()=>{}),/PROCESS_NOT_READY/);
  refusals.push({base,name:'failed-process-is-terminal',reason:'PROCESS_STATE'});
  fs.writeFileSync(dir+'/layout-'+base+'.json',JSON.stringify(l,null,2)+'\n');
 }
 fs.writeFileSync(process.argv[3],JSON.stringify({status:'PASS',modules:mods.length,workers:6,rows,refusals},null,2)+'\n');
}
