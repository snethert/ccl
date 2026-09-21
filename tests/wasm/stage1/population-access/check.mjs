import fs from 'node:fs';import assert from 'node:assert/strict';
import {Worker,isMainThread,parentPort,workerData} from 'node:worker_threads';
import {createStrongPopulation,POPULATION_POLICY} from './builder.mjs';
if(isMainThread){
 const rows=[];for(const base of [262144,2147483648])for(const generated of [false,true])rows.push(await new Promise((ok,no)=>{const w=new Worker(new URL(import.meta.url),{workerData:{base,dir:process.argv[2],generated}});w.on('message',ok);w.on('error',no);w.on('exit',c=>{if(c)no(Error('Worker '+c));});}));
 fs.writeFileSync(process.argv[3],JSON.stringify({status:'PASS',rows},null,2)+'\n');
}else{
 const {base,dir}=workerData,N=77825,T=77838,tcr=1024,root=131064,config=1200000,result=2048000,size=32768,space2=3145728;
 const memory=new WebAssembly.Memory({initial:Math.max(64,Math.ceil((base+65536)/65536)),maximum:32769,shared:true});
 const view=new DataView(memory.buffer),get=p=>view.getUint32(p,true),put=(p,n)=>view.setUint32(p,n,true),bytes=(p,n)=>new Uint8Array(memory.buffer,p,n);
 const service=(await WebAssembly.instantiate(fs.readFileSync(dir+'/population.wasm'),{env:{memory}})).instance.exports;
 const collector=(await WebAssembly.instantiate(fs.readFileSync(dir+'/collector.wasm'),{env:{memory}})).instance.exports;
 const gen=workerData.generated?await(await import('./generated.mjs')).install({dir,memory,tcr,get,put,service,scratch:1900000,scratchEnd:2031072,result,collector,config}):null;
 assert.equal(JSON.parse(fs.readFileSync(dir+'/native.json')).length,2);
 let pop,member,other,comparisons=0,collections=0;const checks=[];
 function setup(type){
  bytes(tcr,256).fill(0);bytes(config,96).fill(0);bytes(base,size).fill(0);bytes(space2,size).fill(0);
  for(const[o,n]of[[48,base],[52,base+size],[56,base],[68,root+8],[72,196608],[128,root],[80,700000],[76,700000],[84,900000],[120,100000],[124,100064],[104,610000]])put(tcr+o,n);
  put(config,tcr);put(config+16,space2);put(config+20,space2+size);put(config+68,32768);put(config+72,1180000);put(config+80,1800000);
  member=base+1;put(base,92);put(base+4,68);other=base+9;put(base+8,148);put(base+12,124);
  const start=base+16,end=start+16+(type==='list'?16:16),p=createStrongPopulation({memory,base:start,end,type,members:type==='list'?[member,other]:[[member,other]],policy:POPULATION_POLICY});pop=p.object;
  put(tcr+48,end);put(root,0);put(root+4,3);[pop,member,other].forEach((v,i)=>put(root+8+4*i,v));
 }
 function raw(op,key=N){
  bytes(result,16).fill(0xa5);assert.equal(service.pop_run(pop,pop-6+16,op,key,N,0,0,result),0,'status');
  const r=Array.from({length:4},(_,i)=>get(result+4*i));assert.deepEqual(r.slice(1),[N,1,0],'publication');return r[0];
 }
 function call(op,key=N){const x=gen?gen.invoke(op,pop,key,N)[0]:raw(op,key);comparisons++;return x;}
 function move(){
  const old=get(tcr+56);put(config+16,old===base?space2:base);put(config+20,get(config+16)+size);put(tcr+116,0);
  assert.equal(collector.collect(config),0,'collect');[pop,member,other]=[0,1,2].map(i=>get(root+8+4*i));bytes(old,size).fill(0xda);collections++;
 }
 function cons(a,b){const p=get(tcr+48);put(p,b);put(p+4,a);put(tcr+48,p+8);return p+1;}
 for(const type of ['list','alist']){
  setup(type);
  for(let i=0;i<12;i++){
   assert.equal(call(2),type==='list'?0:4,'type code');
   const head=call(0);assert.equal(head&7,1,'contents cons');
   if(type==='list')assert.equal(get(head+3),member,'contents member');
   else{assert.equal(get(get(head+3)+3),member,'contents alist key');assert.equal(get(get(head+3)-1),other,'contents alist value');}
   move();
  }
  // SETF shares its supplied spine: no copy, even for dotted/cyclic lists.
  for(const shape of ['nil','proper','dotted','cycle'])for(let repeat=0;repeat<6;repeat++){
   let replacement=N;
   if(shape!=='nil'){replacement=cons(member,shape==='dotted'?other:N);if(shape==='cycle')put(replacement-1,replacement);}
   assert.equal(call(1,replacement),replacement,'setter result');assert.equal(call(0),replacement,'set readback');
   move();const head=call(0);
   if(shape==='nil')assert.equal(head,N,'nil');else{assert.equal(get(head+3),member,'retained member');assert.equal(get(head-1),shape==='cycle'?head:shape==='dotted'?other:N,'retained tail');}
  }
  // Only the population roots the member after publication.
  call(1,cons(member,cons(other,N)));put(root+4,1);move();const head=call(0),first=get(head+3),second=get(get(head-1)+3);assert.deepEqual([get(first+3),get(first-1),get(second+3),get(second-1)],[68,92,124,148],'population-only member roots');comparisons++;
  // Restore explicit fixture roots for subsequent refusal checks.
  member=first;other=second;put(root+4,3);put(root+12,member);put(root+16,other);
  for(const [name,damage,key,expected]of[
   ['type refusal',()=>{},28,3],['population pad',()=>put(pop+6,1),N,2],
   ['population type',()=>put(pop-2,8),N,2],['population header',()=>put(pop-6,1018),N,2],
  ]){
   const clean=bytes(pop-6,16).slice();damage();const before=bytes(pop-6,16).slice();bytes(result,16).fill(0x5a);
   assert.equal(service.pop_run(pop,pop+10,1,key,N,0,0,result),expected,name);assert.deepEqual(bytes(pop-6,16),before,name);assert(bytes(result,16).every(b=>b===0x5a),name);bytes(pop-6,16).set(clean);checks.push(name);
  }
  // Raw success publication is checked even when generated calls ignore padding.
  raw(0);raw(1,N);raw(2);
 }
 parentPort.postMessage({base,generated:!!gen,comparisons,collections,checks,...(gen?{dispatch:gen.counts()}: {})});
}
