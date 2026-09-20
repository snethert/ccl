import fs from 'node:fs';
import assert from 'node:assert/strict';
import {Worker,isMainThread,parentPort,workerData} from 'node:worker_threads';
import {BootstrapSchedule} from './schedule.mjs';
import {LazyLoader,PROFILE,sha} from './loader.mjs';
import {inspect} from './binary.mjs';
const NIL=77825,TCR=16384,REG=4096,STACK=32768;
const names=['seed_map','seed_fatal','seed_install','define_one','define_two','define_three','define_four','activate','workload'];
const read=(d,n)=>JSON.parse(fs.readFileSync(d+'/'+n));
function execute(dir,base){
 const modules=read(dir,'compiled/modules.json').map((m,i)=>{
  const bytes=fs.readFileSync(dir+'/compiled/'+m.name+'.wasm'),x=inspect(bytes);
  return {name:m.name,bytes,record:{name:m.name,slot:i+1,code:i+1,version:4,signature:17,role:23,profile:PROFILE,sha256:sha(bytes),imports:x.imports,entries:Object.fromEntries(x.exports.map(e=>[e.name,{role:e.name,index:e.index}]))}};
 });
 const mat=read(dir,'compiled/materialized.json');assert.equal(mat.image,'','no hidden initializer pool state');
 const memory=new WebAssembly.Memory({initial:32769,maximum:32769,shared:true}),v=new DataView(memory.buffer);
 const get=p=>v.getUint32(p,true),put=(p,x)=>v.setUint32(p,x,true),S=base+8192,READY=S+256;
 const table=new WebAssembly.Table({element:'anyfunc',initial:32}),tail_table=new WebAssembly.Table({element:'anyfunc',initial:32});
 const call_error=new WebAssembly.Tag({parameters:['i32']}),type_error=new WebAssembly.Tag({parameters:['i32','i32']}),nonlocal_exit=new WebAssembly.Tag({parameters:['i32']});
 const imports={env:{memory,tcr:TCR,table,tail_table,code_registry:REG,call_error,type_error,nonlocal_exit},symbols:{}};
 const schema=read(dir,'tcr.json'),fields=Object.fromEntries(schema.fields.map(r=>[r.name,r.offset]));
 assert.equal(schema.size_bytes,256);const set=(n,x)=>{assert(n in fields);put(TCR+fields[n],x);};
 const keys=[...new Set(modules.flatMap(m=>m.record.imports.filter(x=>x.module==='symbols').map(x=>x.name)))];
 keys.forEach((k,i)=>imports.symbols[k]=base+4096+32*i+6);
 const selected=()=>names.map(n=>modules.find(m=>m.name===n));
 function plan(){return {version:1,state:{start:S,size:128},ready:READY,initializers:names.map((name,i)=>({
  id:name,module:name,sha256:modules.find(m=>m.name===name).record.sha256,phase:i<3?0:i<7?1:2,
  prerequisites:i?[names[i-1]]:[],completion:{address:S+8*i+4,value:4*(101+i)},
  before:[{address:S+100,value:4*i},{address:S+108,value:i<2?0:i<8?4:8}],
  after:[{address:S+100,value:4*(i+1)},...(i===1||i===7?[{address:S+108,value:i===1?4:8}]:[]),...(i===8?[{address:S+116,value:36},{address:S+112,value:8}]:[])]
 }))};}
 let loader,invocations=0,installs=[],answers=[];
 function reset(){
  new Uint8Array(memory.buffer,TCR,256).fill(0);new Uint8Array(memory.buffer,STACK,32768).fill(0);
  new Uint8Array(memory.buffer,S,272).fill(0);
  for(let i=0;i<32;i++){table.set(i,null);tail_table.set(i,null);}
  put(77824,NIL);put(77828,NIL);put(77832,1850);for(let i=3;i<16;i++)put(77824+4*i,NIL);
  put(REG,32);put(REG+4,1);
  modules.forEach((m,i)=>{
   [i+1,4,17,23].forEach((x,j)=>put(REG+8+16*(i+1)+4*j,x));
   [1578,4*(i+1),NIL,4,NIL,NIL,mat.roots[i],0].forEach((x,j)=>put(base+32*i+4*j,x));
  });
  keys.forEach((k,i)=>[1850,NIL,NIL,NIL,NIL,NIL,NIL,0].forEach((x,j)=>put(base+4096+32*i+4*j,x)));
  for(const [n,x]of Object.entries({tcr_address:TCR,alloc_base:131072,alloc_pointer:131072,alloc_limit:135168,vsp_base:STACK+16,vsp:STACK+512,vsp_limit:STACK+32768,tsp_base:8192,tsp:8192,tsp_limit:12288,csp_base:12288,csp:12288,csp_limit:16384,tlb_pointer:139264,tlb_limit:64,mv_base:STACK+1024,mv_owner_top:STACK+1040,root_head:STACK+8,next_method_context:NIL,fp_control:7}))set(n,x);
  for(let i=0;i<64;i++)put(139264+4*i,243);
  for(let i=0;i<12;i++){put(S+8*i,NIL);put(S+8*i+4,0);}
  put(S+96,NIL);put(S+100,0);put(S+104,NIL);put(S+108,0);put(S+112,0);put(S+116,0);
  loader=new LazyLoader({memory,table,tail_table,call_error,nonlocal_exit,catalog:modules.map(m=>m.record),stub:new WebAssembly.Module(fs.readFileSync(dir+'/stub.wasm')),readBytes:n=>modules.find(m=>m.name===n).bytes});
  installs=[];answers=[];
 }
 function install(m,r){
  const i=names.indexOf(r.id);assert(i>=0);
  if(r.phase>0)for(let j=0;j<3;j++)assert.equal(get(S+8*j+4),4*(101+j),'phase zero before bundle installation');
  const e=loader.defer(m.name,imports).host_entry,index=modules.findIndex(x=>x.name===m.name);
  // Physical installation occurs here, not merely declaration of a stub.
  try{loader.install(m.record.slot);}catch(error){throw Error('INSTALL_FAILED '+JSON.stringify(loader.events));}installs.push(r.id);
  return ()=>{
   const args=[S+8*i+1,S+97,S+105,i?S+8*(i-1)+1:S+81,S+113];
   set('vsp',STACK+512);set('mv_base',STACK+1024);set('mv_owner_top',STACK+1040);set('mv_count',0);
   args.forEach((x,j)=>put(STACK+512+4*j,x));const saved=[64,128,140,92].map(o=>get(TCR+o));
   let pair;invocations++;
   try{pair=e(base+32*index+6,args.length);}catch(error){if(error.is?.(call_error))throw Error('CHECKED_'+error.getArg(call_error,0));if(error.is?.(type_error))throw Error('TYPE_ERROR_'+error.getArg(type_error,0));throw error;}
   finally{assert.deepEqual([64,128,140,92].map(o=>get(TCR+o)),saved,'caller restored');}
   assert.equal(pair[1],2);const values=[get(STACK+1024)/4,get(STACK+1028)/4];
   answers.push({values,state:get(S+100)/4,mode:get(S+108)/4,output:[get(S+116)/4,get(S+112)/4]});
  };
 }
 const make=(p=plan(),ms=selected(),digest=sha(JSON.stringify(p)))=>new BootstrapSchedule({memory,plan:p,digest,modules:ms});
 const snapshot=()=>({memory:sha(new Uint8Array(memory.buffer,S,272)),tcr:sha(new Uint8Array(memory.buffer,TCR,256)),tables:[table,tail_table].map(t=>Array.from({length:32},(_,i)=>t.get(i)))});
 reset();const p=plan(),owner=make(p);p.initializers.length=0; // admitted snapshot independent of caller data
 const events=owner.run(install);assert.equal(owner.state,'READY');
 assert.deepEqual(answers,read(dir,'expected.json'),'generated phase effects');assert.deepEqual(answers,read(dir,'compiled/native.json'),'native phase effects');
 assert.deepEqual(events,names.flatMap((id,i)=>['installed','entered','completed'].map(event=>({id,phase:i<3?0:i<7?1:2,event}))),'full execution trace');
 assert.equal(get(READY),1);assert.equal(get(READY+4),9);assert.equal(get(READY+8),parseInt(sha(JSON.stringify(plan())).slice(0,8),16));
 assert.throws(()=>owner.run(install),/SCHEDULE_STATE/,'ready cannot rerun');
 const positive={answers:structuredClone(answers),events,installed:installs.slice(),loader:loader.snapshot(),load_events:structuredClone(loader.events),state:get(S+100),mode:get(S+108)};
 const refusals=[];
 function bad(name,change,reason){
  reset();const p=plan(),ms=selected().map(m=>({...m,bytes:Uint8Array.from(m.bytes),record:structuredClone(m.record)}));change(p,ms);
  const before=snapshot();assert.throws(()=>make(p,ms),new RegExp(reason),name);assert.deepEqual(snapshot(),before,name+' admission writes nothing');refusals.push({name,reason});
 }
 bad('omitted required module',(_,ms)=>ms.pop(),'MODULE_SET');
 bad('duplicate module',(_,ms)=>ms[1]=ms[0],'MODULE_SET');
 bad('missing initializer',p=>p.initializers.pop(),'MODULE_SET');
 bad('unknown prerequisite',p=>p.initializers[4].prerequisites=['absent'],'PREREQUISITE');
 bad('forward phase',p=>p.initializers[0].prerequisites=['activate'],'PREREQUISITE');
 bad('cyclic initializers',p=>p.initializers[0].prerequisites=['seed_install'],'INITIALIZER_CYCLE');
 bad('duplicate initializer',p=>p.initializers[1].id=p.initializers[0].id,'INITIALIZER_ID');
 bad('completion alias',p=>p.initializers[1].completion.address=p.initializers[0].completion.address,'COMPLETION');
 bad('effect completion alias',p=>p.initializers[0].after[0].address=p.initializers[1].completion.address,'STATE_COMPLETION_ALIAS');
 bad('unbacked state',p=>p.state.start=memory.buffer.byteLength,'STATE_EXTENT');
 bad('unaligned state',p=>p.state.start++,'STATE_EXTENT');
 bad('unbacked assertion',p=>p.initializers[0].before[0].address=memory.buffer.byteLength,'STATE_ASSERTION');
 bad('ready aliases effects',p=>p.ready=S,'READY_EXTENT');
 bad('invalid phase',p=>p.initializers[0].phase=3,'PHASE');
 bad('no loader phase',p=>p.initializers.forEach(r=>r.phase=2),'PHASE_SET');
 bad('changed module digest',(_,ms)=>ms[0].bytes[0]^=1,'BINARY_DIGEST');
 bad('wrong planned digest',p=>p.initializers[0].sha256='0'.repeat(64),'MODULE_IDENTITY');
 bad('wrong export role',(_,ms)=>ms[0].record.entries.entry.role='tail_entry','EXPORT_ROLE');
 bad('duplicate prerequisite',p=>p.initializers[1].prerequisites.push('seed_map'),'PREREQUISITE_SET');
 reset();assert.throws(()=>make(plan(),selected(),'0'.repeat(64)),/PLAN_DIGEST/);refusals.push({name:'wrong plan identity',reason:'PLAN_DIGEST'});
 function fails(name,{change=()=>{},pre=()=>{},hook=install,reason}){
  reset();const p=plan(),ms=selected();change(p,ms);const owner=make(p,ms);pre();
  assert.throws(()=>owner.run(hook),new RegExp(reason),name);assert.equal(owner.state,'FAILED',name+' terminal');
  assert.throws(()=>owner.run(install),/SCHEDULE_STATE/,name+' retry refused');
  assert(!owner.events.some(e=>e.id==='workload'&&e.event==='completed'),name+' no later completion');
  assert.equal(get(READY),0,name+' never ready');refusals.push({name,reason,events:owner.events,installed:installs.slice()});
 }
 fails('dirty completion',{pre:()=>put(S+4,404),reason:'NOT_FRESH'});
 fails('dirty ready count',{pre:()=>put(READY+4,9),reason:'NOT_FRESH'});
 fails('wrong prerequisite state',{pre:()=>put(S+100,12),reason:'PRECONDITION'});
 fails('no-load path',{hook:()=>()=>{},reason:'COMPLETION_MISSING'});
 fails('invalid installation result',{hook:()=>undefined,reason:'INSTALL_RESULT'});
 fails('asynchronous initializer',{hook:()=>()=>Promise.resolve(),reason:'SYNCHRONOUS_INITIALIZER'});
 fails('prewritten completion',{hook:(m,r)=>{put(r.completion.address,r.completion.value);return ()=>{};},reason:'PREWRITTEN_COMPLETION'});
 fails('state changed during installation',{hook:(m,r)=>{put(S+100,999);return ()=>{};},reason:'PRECONDITION'});
 for(const [name,reason]of [['wrong_completion','COMPLETION_MISSING'],['no_completion','COMPLETION_MISSING'],['no_effect','POSTCONDITION'],['clobber_previous','COMPLETION_CLOBBER'],['raises','TYPE_ERROR_']]){
  fails(name,{change:(p,ms)=>{const m=modules.find(m=>m.name===name);ms[4]=m;p.initializers[4].module=m.name;p.initializers[4].sha256=m.record.sha256;},reason});
 }
 fails('reentrant initialization',{hook:()=>{throw Error('REENTRANT_TEST');},reason:'REENTRANT_TEST'});
 reset();const reentrant=make();assert.throws(()=>reentrant.run(()=>{reentrant.run(install);}),/SCHEDULE_STATE/,'reentrant same owner');assert.equal(reentrant.state,'FAILED');refusals.push({name:'reentrant same owner',reason:'SCHEDULE_STATE'});
 reset();const reversed=plan();reversed.initializers.reverse();make(reversed).run(install);assert.deepEqual(answers,positive.answers,'topological ordering independent of manifest order');
 return {base,positive,refusals,invocations,topological_reordering:true};
}
if(!isMainThread){try{parentPort.postMessage(execute(workerData.dir,workerData.base));}catch(e){throw Error(String(e)+'\n'+e.stack);}}
else{
 const dir=process.argv[2],rows=[];
 for(const base of (process.env.SCHEDULE_CONTROL?[4194304]:[4194304,2147483648,4194304,2147483648])){
  const w=new Worker(new URL(import.meta.url),{workerData:{dir,base}});
  const exit=new Promise((resolve,reject)=>{w.once('error',reject);w.once('exit',c=>c?reject(Error('Worker exit '+c)):resolve());});
  const answer=new Promise((resolve,reject)=>{w.once('message',resolve);w.once('error',reject);});
  rows.push(await answer);await exit;
 }
 fs.writeFileSync(process.argv[3],JSON.stringify({status:'PASS',rows},null,2)+'\n');
}
