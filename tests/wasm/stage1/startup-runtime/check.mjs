import fs from 'node:fs';
import assert from 'node:assert/strict';
import {Worker,isMainThread,parentPort,workerData} from 'node:worker_threads';
import {CollectorOwner} from './owner.mjs';
import {CollectionStatistics} from './statistics.mjs';
import {statisticsService} from './service.mjs';
import {sha256} from './sha256.mjs';
if(isMainThread){
 const dir=process.argv[2],rows=[];
 for(const base of [2097152,2147483648])rows.push(await new Promise((ok,no)=>{const w=new Worker(new URL(import.meta.url),{workerData:{base,dir}});w.once('message',ok);w.once('error',no);w.once('exit',c=>{if(c)no(Error('worker '+c));});}));
 fs.writeFileSync(process.argv[3],JSON.stringify({status:'PASS',comparisons:rows.reduce((a,b)=>a+b.comparisons,0),collections:rows.reduce((a,b)=>a+b.collections,0),rows},null,2)+'\n');
}else{
 const {base,dir}=workerData,read=n=>JSON.parse(fs.readFileSync(dir+'/'+n));
 const bytes=fs.readFileSync(dir+'/collector.wasm'),N=77825,T=77838,TCR=1024,ROOT=131064,EXTERNAL=262144,BINDINGS=266240,REG=263168,DESC=800006,DONE=800009,RESULT=1185000;
 const memory=new WebAssembly.Memory({initial:base>1e9?32769:48,maximum:32769,shared:true});
 let v=new DataView(memory.buffer),owner,clock=0n,step=0n,comparisons=0,collections=0;const rows=[];
 const get=p=>{v=new DataView(memory.buffer);return v.getUint32(p,true);},put=(p,n)=>{v=new DataView(memory.buffer);v.setUint32(p,n,true);},t=o=>get(TCR+o),set=(o,n)=>put(TCR+o,n);
 const table=new WebAssembly.Table({element:'anyfunc',initial:16}),tail_table=new WebAssembly.Table({element:'anyfunc',initial:16}),call_error=new WebAssembly.Tag({parameters:['i32']}),type_error=new WebAssembly.Tag({parameters:['i32','i32']}),nonlocal_exit=new WebAssembly.Tag({parameters:['i32']});
 const env={memory,tcr:TCR,code_registry:REG,table,tail_table,call_error,type_error,nonlocal_exit},adapter=new WebAssembly.Module(fs.readFileSync(dir+'/adapter.wasm'));
 const symbolNames=new Map();
 const compiled=read('compiled/modules.json').map((m,i)=>({...m,id:i+3,module:new WebAssembly.Module(fs.readFileSync(dir+'/compiled/'+m.name+'.wasm'))}));
 assert.equal(read('compiled/materialized.json').image,'');
 function object(id){return 786432+32*id+6;}
 function register(id,inst){[id,4,17,23].forEach((n,i)=>put(REG+8+16*id+4*i,n));table.set(id,inst.exports.entry);tail_table.set(id,inst.exports.tail_entry);}
 function setup(capacity=128,units=1000){
  const regions=[['tcr',TCR,TCR+256],['image',77824,77864],['image',786432,786432+32*16],['image',800000,800016],['image',801024,801024+32*16],['vstack',ROOT,ROOT+32776],['temp',196608,212992],['control',212992,229376],['external',EXTERNAL,EXTERNAL+4096],['bindings',BINDINGS,BINDINGS+4096],['c-stack',1048576,1114112],['root-list',1180000,1184096],['external-scratch',RESULT,RESULT+16],['scratch',1200000,1800000]].filter(r=>r[0]!=='external-scratch').map(([role,start,end],i)=>({name:role+'-'+i,role,start,end}));
  const layout={version:1,collector:'copying',workers:1,egc:false,tcr:TCR,maximumPages:32769,logCapacity:32768,regions,spaces:[base,base+32768].map((start,i)=>({name:'heap-'+i,start,end:start+capacity})),groups:['module-constants','callbacks','registry','host'].map((kind,i)=>({kind,slots:[EXTERNAL+4*i]}))};
  for(const r of [...regions,...layout.spaces])new Uint8Array(memory.buffer,r.start,r.end-r.start).fill(0);
  put(N-1,N);put(N+3,N);put(T-6,1850);for(let i=1;i<8;i++)put(T-6+4*i,N);
  for(let id=0;id<16;id++)[1578,4*id,N,4,N,N,N,0].forEach((n,i)=>put(object(id)-6+4*i,n));
  for(let i=0;i<16;i++)[1850,N,N,N,N,0,N,0].forEach((x,j)=>put(801024+32*i+4*j,x));symbolNames.clear();
  put(DESC-6,250);put(DESC-2,0);put(DONE-1,N);put(DONE+3,N);
  for(const g of layout.groups)for(const p of g.slots)put(p,N);
  for(const [o,n]of [[48,base],[52,base+capacity],[56,base],[68,ROOT+8],[72,ROOT+32776],[64,ROOT+8],[128,ROOT],[80,196608],[76,196608],[84,212992],[92,212992],[88,212992],[96,229376],[104,BINDINGS],[108,0],[120,ROOT+8200],[124,ROOT+8456],[188,N],[200,7]])set(o,n);
  put(ROOT,0);put(ROOT+4,0);put(REG,16);put(REG+4,1);
  clock=0n;step=0n;owner=CollectorOwner.create(memory,bytes,sha256(bytes),layout,{clock:()=>{const n=clock;clock+=step;return n;}});
  const run=statisticsService({memory,owner,descriptor:DESC,result:RESULT,units});
  for(const [id,op]of [[1,5],[2,4]])register(id,new WebAssembly.Instance(adapter,{env,hash:{run:(...args)=>{if(capacity===64){while(t(48)+8<=t(52)){const p=t(48);put(p,N);put(p+4,N);set(48,p+8);}}return run(...args);},collect:()=>{owner.atSafepoint(o=>o.collect());return 0;},config:0,operation:op,scratch:0,scratch_end:0,result:RESULT}}));
  for(const m of compiled){const imports=WebAssembly.Module.imports(m.module).filter(i=>i.module==='symbols');const symbols=Object.fromEntries(imports.map(i=>{if(!symbolNames.has(i.name))symbolNames.set(i.name,801024+32*symbolNames.size+6);return [i.name,symbolNames.get(i.name)];}));const instance=new WebAssembly.Instance(m.module,{env,symbols});register(m.id,instance);m.entry=instance.exports.entry;}
  assert(symbolNames.size<=16);
  for(const [name,p] of symbolNames){
   if(name==='gctime_snapshot')put(p+6,object(1));
   if(name==='gctime')put(p+6,object(compiled.find(m=>m.name==='gctime').id));
   if(name.includes('statistics')&&name.includes('descriptor'))put(p+2,DESC);
  }
  return run;
 }
 function integer(p){if((p&3)===0)return BigInt(p|0)/4n;assert.equal(p&7,6);const h=get(p-6);assert.equal(h&255,7);let n=0n;for(let i=(h>>>8)-1;i>=0;i--)n=(n<<32n)|BigInt(get(p-2+4*i));return n;}
 function call(name,args){
  args.forEach((n,i)=>put(ROOT+8+4*i,n));const before=Array.from({length:64},(_,i)=>get(TCR+4*i)),m=compiled.find(x=>x.name===name);let pair;
  try{pair=m.entry(object(m.id),args.length);}catch(e){throw Error(name+': '+(e.is?.(call_error)?'checked '+e.getArg(call_error,0):String(e)));}
  for(let i=0;i<64;i++)if(![12,13,14,29].includes(i))assert.equal(get(TCR+4*i),before[i],'TCR word '+i);
  assert.equal(t(116),pair[1]);return Array.from({length:pair[1]},(_,i)=>integer(get(t(120)+4*i)));
 }
 for(const native of read('compiled/native.json'))for(const units of [1000,1000000])for(const capacity of [base>1e9?64:16,128]){
  setup(capacity,units);step=BigInt(native.microseconds);owner.atSafepoint(o=>o.collect());step=0n;
  const expected=(units===1000?native.milliseconds:native.values).map(BigInt);assert.deepEqual(owner.gctime(units),expected,'native time conversion');
  // Native GCTIME uses microseconds; its timeval converter supplies the
  // millisecond policy used by the accepted browser configuration.
  assert.equal(native.units,1000000);
  const f=compiled.find(m=>m.name==='gctime_port').id,receiver=compiled.find(m=>m.name==='gctime_receiver').id;
  for(const [name,args]of [
   ['gctime_port',[object(1),DESC]],
   ['gctime',[]],
   ['gctime_named_caller',[]],
   ['gctime_cleanup',[object(f),object(1),DESC,DONE]],
   ['gctime_dynamic',[object(f),object(receiver),object(1),DESC]],
   ['gctime_retained',[object(f),object(1),DESC,object(2)]],
  ]){
   assert.deepEqual(call(name,args),expected,name+' exact five native values');comparisons++;
   if(name==='gctime_cleanup')assert.equal(get(DONE+3),611*4);
  }
  collections+=Number(owner.statistics.collections);rows.push({microseconds:native.microseconds,units,capacity,values:expected.map(String),collections:String(owner.statistics.collections)});
 }
 // A snapshot describes the instant before its own allocation triggers GC.
 setup(base>1e9?64:16);step=1000n;owner.atSafepoint(o=>o.collect());
 assert.deepEqual(call('gctime_port',[object(1),DESC]),[1n,1n,0n,0n,0n],'snapshot before collecting assurance');
 assert(owner.statistics.collections>1n);assert(owner.gctime()[0]>1n);comparisons++;
 // Sub-millisecond intervals accumulate before native ROUND, never per event.
 let sample=0n;const accumulated=new CollectionStatistics(()=>{const n=sample;sample+=500n;return n;});
 accumulated.committed(accumulated.sample(),8);accumulated.committed(accumulated.sample(),16);
 assert.deepEqual(accumulated.gctime(),[1n,1n,0n,0n,0n],'accumulate before rounding');assert.equal(accumulated.snapshot().bytesFreed,24n,'bytesFreed');
 // Named reader is a real live binding: omission prevents execution and no
 // replacement value can stand in for its required installed module.
 setup();const gc=compiled.find(m=>m.name==='gctime');tail_table.set(gc.id,null);
 assert.throws(()=>call('gctime_named_caller',[]));
 setup();put(symbolNames.get('gctime')+6,N);assert.throws(()=>call('gctime_named_caller',[]));
 // Actual dead/live accounting, refused collection, reset by a fresh owner.
 setup(32);put(base,N);put(base+4,28);put(base+8,N);put(base+12,44);set(48,base+16);put(EXTERNAL,base+1);step=1500n;
 const report=owner.atSafepoint(o=>o.collect());assert.equal(report.reclaimed,8);assert.equal(owner.statistics.bytesFreed,8n,'bytesFreed');assert.equal(owner.statistics.collections,1n);assert.deepEqual(owner.gctime(),[2n,2n,0n,0n,0n]);
 const stats=owner.statistics;put(EXTERNAL,t(56)+9);assert.throws(()=>owner.atSafepoint(o=>o.collect()),/collection refused/);assert.deepEqual(owner.statistics,stats,'refused copy is not accounted');
 setup();assert.deepEqual(owner.gctime(),[0n,0n,0n,0n,0n]);assert.equal(owner.statistics.collections,0n);
 // Complement-poison every publication word, check all on direct success.
 const run=setup();[DESC,N,1,0].forEach((n,i)=>put(RESULT+4*i,~n));assert.equal(run(DESC,DESC+2,5,N,N,0,0,RESULT),0);assert.deepEqual([get(RESULT+4),get(RESULT+8),get(RESULT+12)],[N,1,0],'publication');assert.equal(get(get(RESULT)-6),1530);
 const published=Array.from({length:4},(_,i)=>get(RESULT+4*i));assert.throws(()=>statisticsService({memory,owner,descriptor:DESC,result:DESC-6}),/admission/);
 assert.equal(run(DESC,DESC+2,5,T,N,0,0,RESULT),4);assert.deepEqual(Array.from({length:4},(_,i)=>get(RESULT+4*i)),published);
 // Bad clocks cannot turn a committed collection into an apparent refusal.
 const bad=new CollectionStatistics(()=>{throw Error('clock unavailable');});bad.committed(bad.sample(),8);assert.equal(bad.snapshot().collections,1n);assert.equal(bad.snapshot().timingValid,false);assert.throws(()=>bad.gctime(),/unavailable/);
 let calls=0;const reverse=new CollectionStatistics(()=>[10n,9n][calls++]);reverse.committed(reverse.sample(),0);assert.throws(()=>reverse.gctime(),/unavailable/);
 parentPort.postMessage({base,comparisons,collections,rows,checks:8});
}
