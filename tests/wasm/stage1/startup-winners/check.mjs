import fs from 'node:fs';
import assert from 'node:assert/strict';
import {Worker,isMainThread,parentPort,workerData} from 'node:worker_threads';
if(isMainThread){
 const rows=[];
 for(const base of [4194304,2147483648])rows.push(await new Promise((resolve,reject)=>{const w=new Worker(new URL(import.meta.url),{workerData:{dir:process.argv[2],base}});w.once('message',resolve);w.once('error',reject);w.once('exit',c=>{if(c)reject(Error('Worker '+c));});}));
 const summary={status:'PASS',placements:2,generatedComparisons:rows.reduce((n,r)=>n+r.rows.length,0),collections:rows.reduce((n,r)=>n+r.collections,0),refusals:rows.reduce((n,r)=>n+r.refusals.length,0),slot_credit:false};
 fs.writeFileSync(process.argv[3],JSON.stringify({summary,rows},null,2)+'\n');
}else{
 const {dir,base}=workerData,read=n=>JSON.parse(fs.readFileSync(dir+'/'+n));
 const memory=new WebAssembly.Memory({initial:32769,maximum:32769,shared:true}),v=new DataView(memory.buffer),get=p=>v.getUint32(p,true),put=(p,x)=>v.setUint32(p,x,true);
 const NIL=77825,T=77838,EMPTY=243,DELETED=251,MOVED=2**29,TCR=16384,REG=4096,STACK=131064,OTHER=8388608,SIZE=32768,SCRATCH=1900000,RESULT=2048000,CONFIG=1200000,DONE=2300000;
 const service=(await WebAssembly.instantiate(fs.readFileSync(dir+'/hash.wasm'),{env:{memory}})).instance.exports;
 const collector=(await WebAssembly.instantiate(fs.readFileSync(dir+'/collector.wasm'),{env:{memory}})).instance.exports;
 const table=new WebAssembly.Table({element:'anyfunc',initial:32}),tail_table=new WebAssembly.Table({element:'anyfunc',initial:32});
 const call_error=new WebAssembly.Tag({parameters:['i32']}),type_error=new WebAssembly.Tag({parameters:['i32','i32']}),nonlocal_exit=new WebAssembly.Tag({parameters:['i32']});
 const env={memory,tcr:TCR,table,tail_table,code_registry:REG,call_error,type_error,nonlocal_exit};
 const adapter=new WebAssembly.Instance(new WebAssembly.Module(fs.readFileSync(dir+'/adapter.wasm')),{env,hash:{run:service.ht_run,collect:collector.collect,config:CONFIG,operation:5,scratch:SCRATCH,scratch_end:SCRATCH+131072,result:RESULT}});
 const symbols={},entries=[],mods=read('compiled/modules.json'),mat=read('compiled/materialized.json');assert.equal(mat.image,'');
 function register(id,instance){[id,4,17,23].forEach((x,j)=>put(REG+8+16*id+4*j,x));table.set(id,instance.exports.entry);tail_table.set(id,instance.exports.tail_entry);}
 function object(id,pool=NIL){const p=2100000+32*id;[1578,id*4,NIL,4,NIL,NIL,pool,0].forEach((x,j)=>put(p+4*j,x));return p+6;}
 put(REG,32);put(REG+4,1);register(1,adapter);const operation=object(1);
 for(const [i,m]of mods.entries()){
  const module=new WebAssembly.Module(fs.readFileSync(dir+'/compiled/'+m.name+'.wasm'));
  for(const imp of WebAssembly.Module.imports(module))if(imp.module==='symbols'&&!(imp.name in symbols)){
   const p=2200000+32*Object.keys(symbols).length;[1850,NIL,NIL,NIL,NIL,0,NIL,0].forEach((x,j)=>put(p+4*j,x));symbols[imp.name]=p+6;
  }
  const instance=new WebAssembly.Instance(module,{env,symbols});register(i+2,instance);entries.push({name:m.name,self:object(i+2,mat.roots[i]),fn:instance.exports.entry});
 }
 put(77824,NIL);put(77828,NIL);put(77832,1850);for(let j=3;j<16;j++)put(77824+4*j,NIL);
 let ht,cap,collections=0;
 const rows=[],refusals=[],tcrWords=Array.from({length:64},(_,j)=>4*j).filter(o=>o!==116);
 function setup(n){
  new Uint8Array(memory.buffer,TCR,256).fill(0);new Uint8Array(memory.buffer,CONFIG,96).fill(0);
  new Uint8Array(memory.buffer,base,SIZE).fill(0xcd);new Uint8Array(memory.buffer,OTHER,SIZE).fill(0xa5);new Uint8Array(memory.buffer,STACK,65544).fill(0);
  cap=4;while(cap<n)cap*=2;
  put(TCR,TCR);put(TCR+48,base);put(TCR+52,base+SIZE);put(TCR+56,base);put(TCR+68,STACK+8);put(TCR+72,STACK+65544);put(TCR+64,STACK+520);put(TCR+128,STACK);
  put(STACK,0);put(STACK+4,1);put(TCR+80,700000);put(TCR+76,700000);put(TCR+84,900000);
  put(TCR+88,900000);put(TCR+92,900000);put(TCR+96,950000);
  put(TCR+120,STACK+1032);put(TCR+124,STACK+1096);put(TCR+104,610000);put(TCR+108,0);put(TCR+136,NIL);put(TCR+200,7);
  put(CONFIG,TCR);put(CONFIG+16,OTHER);put(CONFIG+20,OTHER+SIZE);put(CONFIG+68,32768);put(CONFIG+72,1180000);put(CONFIG+76,0);put(CONFIG+80,1800000);
  assert.equal(service.ht_init(base,base+service.ht_size(cap),cap),0);put(TCR+48,base+service.ht_size(cap));ht=base+6;put(STACK+8,ht);put(DONE,NIL);put(DONE+4,0);
 }
 function cons(a=28,b=NIL){const p=get(TCR+48);put(p,b);put(p+4,a);put(TCR+48,p+8);return p+1;}
 function primitive(op,key=NIL,value=NIL){const status=service.ht_run(ht,ht-6+service.ht_size(cap),op,key,value,SCRATCH,SCRATCH+131072,RESULT);assert.equal(status,0,'primitive operation');return [get(RESULT),get(RESULT+4),get(RESULT+8)];}
 function move(label){
  const old=get(TCR+56),next=old===base?OTHER:base;put(CONFIG+16,next);put(CONFIG+20,next+SIZE);
  const code=collector.collect(CONFIG);assert.equal(code,0,label+' collection');ht=get(STACK+8);assert.equal(ht,next+6);new Uint8Array(memory.buffer,old,SIZE).fill(0xda);collections++;
 }
 function checkEmpty(){
  assert.equal(get(ht+26),0,'tombstones cleared');assert.equal(get(ht+30),0,'live count cleared');
  assert.equal(get(ht+2),2**30,'moved flag cleared');
  const b=ht-6;assert.equal(get(b+40),0xfffffffc,'cache index cleared');assert.equal(get(b+44),EMPTY,'cache key cleared');assert.equal(get(b+48),NIL,'cache value cleared');
  for(let j=0;j<cap;j++){assert.equal(get(b+60+8*j),EMPTY,'bucket key cleared');assert.equal(get(b+64+8*j),NIL,'bucket value cleared');}
  assert.equal(get(b+52),cap*4,'capacity preserved');assert.equal(get(b+service.ht_size(cap)-4),0,'padding zero');
 }
 function generated(form){
  const entry=entries.find(e=>e.name===form.name),receiver=entries.find(e=>e.name==='clear_receiver');
  const args=['clear_direct','clear_indirect'].includes(form.name)?[operation,receiver.self,ht,DONE+1]:[operation,ht,DONE+1];
  put(TCR+64,STACK+520);put(TCR+120,STACK+1032);put(TCR+124,STACK+1096);put(TCR+116,0);put(DONE+4,0);
  args.forEach((x,j)=>put(STACK+520+4*j,x));const saved=tcrWords.map(o=>get(TCR+o)),alloc=get(TCR+48);let pair;
  try{pair=entry.fn(entry.self,args.length);}catch(e){throw Error(form.name+' '+(e.is?.(call_error)?'CHECKED_'+e.getArg(call_error,0):String(e)));}
  assert.deepEqual(tcrWords.map(o=>get(TCR+o)),saved,'restored TCR');assert.equal(get(TCR+48)-alloc,0,'known allocation');
  assert.equal(pair[1],form.count,'native value count');assert.equal(get(TCR+116),pair[1]);assert.equal(pair[0]>>>0,ht,'native return identity');assert.equal(get(STACK+1032),ht);
  if(form.count===2)assert.equal(get(STACK+1036),NIL,'native secondary NIL');assert.equal(get(DONE+4),form.done*4,'generated completion');
 }
 for(const native of read('compiled/native.json'))for(const form of native.forms)for(const mode of ['full','tombstones','moved']){
  setup(native.initial);let keys=[];
  for(let j=0;j<native.initial;j++){const key=cons(j*4),value=cons(j*4,key);keys.push(key);primitive(1,key,value);}
  if(mode==='tombstones')for(let j=1;j<keys.length;j+=2)primitive(2,keys[j]);
  if(keys.length)primitive(0,keys[0]);
  if(mode==='moved'){move('before clear');keys=[];for(let j=0;j<cap;j++){const k=get(ht-6+60+8*j);if(k!==EMPTY&&k!==DELETED)keys.push(k);}}
  const identity=ht,tail=ht-6+service.ht_size(cap),untouched=Uint8Array.from(new Uint8Array(memory.buffer,tail,get(TCR+48)-tail));generated(form);assert.deepEqual(new Uint8Array(memory.buffer,tail,untouched.length),untouched,'entry objects unchanged');assert.equal(ht,identity,'same table object');checkEmpty();
  for(const key of keys)assert.deepEqual(primitive(0,key,NIL),[NIL,NIL,2],'old key absent');
  const allocated=get(TCR+48)-get(TCR+56);put(TCR+116,0);move('after clear');
  assert.equal(get(CONFIG+84),1,'only empty table survives');assert.equal(get(TCR+48)-get(TCR+56),service.ht_size(cap),'empty table extent');assert.equal(get(CONFIG+92),allocated-service.ht_size(cap),'all old entries reclaimed');checkEmpty();
  primitive(1,T,364);assert.deepEqual(primitive(0,T,NIL),[364,T,2],'reuse after clear');generated(form);checkEmpty();
  rows.push({initial:native.initial,mode,form:form.name,values:form.count,done:form.done,reclaimed:allocated-service.ht_size(cap)});
 }
 // Refuse before publication for invalid object or owner ranges; clear's
 // result and table preserve bytes even when its arguments are malformed.
 for(const [name,edit]of [
  ['bad tag',a=>a[0]++],['short extent',a=>a[1]-=8],['scratch alias',a=>{a[5]=ht-6;a[6]=a[5]+cap*8;}],['result alias',a=>a[7]=ht-6],['scratch short',a=>a[6]=a[5]],['bad operation',a=>a[2]=6],
 ]){
  setup(4);primitive(1,T,28);const a=[ht,ht-6+service.ht_size(cap),5,NIL,NIL,SCRATCH,SCRATCH+131072,RESULT];edit(a);
  const before=Uint8Array.from(new Uint8Array(memory.buffer,ht-6,service.ht_size(cap))),pub=Uint8Array.from(new Uint8Array(memory.buffer,RESULT,16));
  const status=service.ht_run(...a);assert(status,'refusal '+name);assert.deepEqual(new Uint8Array(memory.buffer,ht-6,before.length),before,'refusal preserves table');assert.deepEqual(new Uint8Array(memory.buffer,RESULT,16),pub,'refusal preserves result');refusals.push({name,status});
 }
 const delivery=Object.fromEntries(['fixed_calls','dynamic_calls','direct_calls'].map(n=>[n,adapter.exports[n].value]));assert(delivery.fixed_calls>0);assert(delivery.direct_calls>0);assert(delivery.dynamic_calls>delivery.direct_calls);
 parentPort.postMessage({base,rows,collections,refusals,delivery});
}
