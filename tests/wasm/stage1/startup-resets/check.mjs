import fs from 'node:fs';
import assert from 'node:assert/strict';
import {Worker,isMainThread,parentPort,workerData} from 'node:worker_threads';
import {BootstrapSchedule} from './bootstrap-schedule.mjs';
import {scheduleInstaller} from './install.mjs';
import {PROFILE,sha} from './loader.mjs';
import {inspect} from './binary.mjs';
const NIL=77825,T=77838,TCR=16384,REG=4096,STACK=32768;
const read=(d,n)=>JSON.parse(fs.readFileSync(d+'/'+n));
function execute(dir,base){
 const selected=read(dir,'selection.json').callbacks.filter(r=>r.disposition==='SELECTED_LITERAL_RESET');
 const all=read(dir,'compiled/modules.json').map((m,i)=>{
  const bytes=fs.readFileSync(dir+'/compiled/'+m.name+'.wasm'),x=inspect(bytes);
  return {name:m.name,bytes,record:{name:m.name,slot:i+1,code:i+1,version:4,signature:17,role:23,profile:PROFILE,sha256:sha(bytes),imports:x.imports,entries:Object.fromEntries(x.exports.map(e=>[e.name,{role:e.name,index:e.index}]))}};
 });
 const names=['preflight',...selected.map(r=>r.module),'workload'];
 assert.equal(all.length,15);assert.equal(selected.length,13);
 const mat=read(dir,'compiled/materialized.json');assert.equal(mat.image,'');
 const memory=new WebAssembly.Memory({initial:32769,maximum:32769,shared:true}),v=new DataView(memory.buffer);
 const get=p=>v.getUint32(p,true),put=(p,x)=>v.setUint32(p,x,true),S=base+8192,READY=S+256;
 const table=new WebAssembly.Table({element:'anyfunc',initial:32}),tail_table=new WebAssembly.Table({element:'anyfunc',initial:32});
 const call_error=new WebAssembly.Tag({parameters:['i32']}),type_error=new WebAssembly.Tag({parameters:['i32','i32']}),nonlocal_exit=new WebAssembly.Tag({parameters:['i32']});
 const imports={env:{memory,tcr:TCR,table,tail_table,code_registry:REG,call_error,type_error,nonlocal_exit},symbols:{}};
 const fields=Object.fromEntries(read(dir,'tcr.json').fields.map(r=>[r.name,r.offset]));
 const set=(n,x)=>{assert(n in fields);put(TCR+fields[n],x);};
 const keys=[...new Set(all.flatMap(m=>m.record.imports.filter(x=>x.module==='symbols').map(x=>x.name)))];
 keys.forEach((k,i)=>imports.symbols[k]=base+4096+32*i+6);
 const symbol=i=>base+1024+32*i+6,encode=x=>x==='nil'?NIL:x==='t'?T:x*4;
 const decode=x=>x===NIL?'nil':x===T?'t':((assert.equal(x&3,0),x|0)/4);
 const globals=()=>selected.map((_,i)=>decode(get(symbol(i)+2)));
 let invocations=0,answers=[],workload,preflight;
 function reset(sentinel){
  new Uint8Array(memory.buffer,TCR,256).fill(0);new Uint8Array(memory.buffer,STACK,32768).fill(0);
  new Uint8Array(memory.buffer,base,8600).fill(0);
  for(let i=0;i<32;i++){table.set(i,null);tail_table.set(i,null);}
  put(77824,NIL);put(77828,NIL);put(77832,1850);for(let i=3;i<16;i++)put(77824+4*i,NIL);
  put(REG,32);put(REG+4,1);
  all.forEach((m,i)=>{
   [i+1,4,17,23].forEach((x,j)=>put(REG+8+16*(i+1)+4*j,x));
   [1578,4*(i+1),NIL,4,NIL,NIL,mat.roots[i],0].forEach((x,j)=>put(base+32*i+4*j,x));
  });
  keys.forEach((k,i)=>[1850,NIL,NIL,NIL,NIL,0,NIL,0].forEach((x,j)=>put(base+4096+32*i+4*j,x)));
  selected.forEach((r,i)=>[1850,NIL,4*sentinel,NIL,NIL,0,NIL,0].forEach((x,j)=>put(symbol(i)-6+4*j,x)));
  for(const [n,x]of Object.entries({tcr_address:TCR,alloc_base:131072,alloc_pointer:131072,alloc_limit:135168,vsp_base:STACK+16,vsp:STACK+512,vsp_limit:STACK+32768,tsp_base:8192,tsp:8192,tsp_limit:12288,csp_base:12288,csp:12288,csp_limit:16384,tlb_pointer:139264,tlb_limit:64,mv_base:STACK+1024,mv_owner_top:STACK+1088,root_head:STACK+8,next_method_context:NIL,fp_control:7}))set(n,x);
  for(let i=0;i<64;i++)put(139264+4*i,243);
  for(let i=0;i<15;i++){put(S+8*i,NIL);put(S+8*i+4,0);}
  answers=[];workload=null;preflight=null;
 }
 function plan(sentinel){return {version:1,state:{start:base+1024,size:S+128-(base+1024)},ready:READY,initializers:names.map((name,i)=>({
  id:name,module:name,sha256:all.find(m=>m.name===name).record.sha256,phase:i===0?0:i===14?2:1,
  prerequisites:i?[names[i-1]]:[],completion:{address:S+8*i+4,value:4*(i===14?200:100+i)},
  before:i===14?selected.map((r,j)=>({address:symbol(j)+2,value:encode(r.value)})):[{address:symbol(i?i-1:0)+2,value:4*sentinel}],
  after:i>0&&i<14?[{address:symbol(i-1)+2,value:encode(selected[i-1].value)}]:[]
 }))};}
 function invoke(entry,row){
  const i=names.indexOf(row.id),index=all.findIndex(m=>m.name===row.module);
  const args=i===14?[...selected.map((_,j)=>symbol(j)),S+8*i+1]:[symbol(i?i-1:0),S+8*i+1];
  set('vsp',STACK+512);set('mv_base',STACK+1024);set('mv_owner_top',STACK+1088);set('mv_count',0);
  args.forEach((x,j)=>put(STACK+512+4*j,x));const saved=[64,128,140,92,112,48].map(o=>get(TCR+o));
  const image=Uint8Array.from(new Uint8Array(memory.buffer,base,8600));
  invocations++;let pair;
  try{pair=entry(base+32*index+6,args.length);}catch(e){if(e.is?.(call_error))throw Error('CHECKED_'+e.getArg(call_error,0));if(e.is?.(type_error))throw Error('TYPE_'+e.getArg(type_error,0));throw e;}
  finally{assert.deepEqual([64,128,140,92,112,48].map(o=>get(TCR+o)),saved,'caller and allocation restored');}
  assert.equal(pair[1],i===14?13:1);
  const values=Array.from({length:pair[1]},(_,j)=>decode(get(STACK+1024+4*j)));
  // Independently allow only this initializer's destination and completion.
  const old=new DataView(image.buffer);
  old.setUint32(row.completion.address-base,get(row.completion.address),true);
  if(i>0&&i<14)old.setUint32(symbol(i-1)+2-base,get(symbol(i-1)+2),true);
  assert.deepEqual(new Uint8Array(memory.buffer,base,8600),image,'no foreign image writes');
  if(i===0)preflight=values;else if(i===14)workload=values;else answers.push({values,globals:globals()});
 }
 function admission(){
  const seen=new Set();
  selected.forEach((r,i)=>{
   const p=symbol(i);assert.equal(get(p-6),1850,'RESET_SYMBOL_HEADER');assert.equal(get(p+22),0,'RESET_GLOBAL_INDEX');
   assert.equal(get(p+14)&8,0,'RESET_WRITABLE');assert(!seen.has(p),'RESET_SYMBOL_ALIAS');seen.add(p);
  });
 }
 function adapter(modules=all){
  admission();return scheduleInstaller({modules,imports,invoke,loaderOptions:{memory,table,tail_table,call_error,nonlocal_exit,stub:new WebAssembly.Module(fs.readFileSync(dir+'/stub.wasm'))}});
 }
 const rows=[];
 for(const [round,sentinel]of [37,91].entries()){
  reset(sentinel);const p=plan(sentinel),a=adapter(),owner=new BootstrapSchedule({memory,plan:p,digest:sha(JSON.stringify(p)),modules:all});
  const events=owner.run(a.install);
  assert.deepEqual(answers,read(dir,'expected.json')[round],'real native reset effects');assert.deepEqual(answers,read(dir,'compiled/native.json')[round]);
  assert.deepEqual(preflight,[sentinel]);assert.deepEqual(workload,selected.map(r=>r.value),'post-startup workload');
  assert.equal(get(READY),1);assert.equal(get(READY+4),15);assert.equal(get(READY+8),parseInt(sha(JSON.stringify(p)).slice(0,8),16));
  assert.equal(owner.state,'READY');assert.deepEqual(a.installed().map(r=>r.name),names);
  for(const r of a.installed())assert.equal(r.sha256,all.find(m=>m.name===r.name).record.sha256,'installed digest bound to selected module');
  rows.push({sentinel,answers:structuredClone(answers),preflight,workload,events,installed:a.installed()});
 }
 const refusals=[];
 function refuse(name,body,reason){reset(37);const before=sha(new Uint8Array(memory.buffer,base,8600));assert.throws(body,new RegExp(reason),name);assert.equal(get(READY),0);refusals.push({name,reason});return before;}
 for(let i=0;i<13;i++)refuse('missing '+selected[i].module,()=>{const p=plan(37);new BootstrapSchedule({memory,plan:p,digest:sha(JSON.stringify(p)),modules:all.filter(m=>m.name!==selected[i].module)});},'MODULE_SET');
 refuse('non-global destination',()=>{put(symbol(0)+22,4);adapter();},'RESET_GLOBAL_INDEX');
 refuse('readonly destination',()=>{put(symbol(0)+14,8);adapter();},'RESET_WRITABLE');
 refuse('bad symbol header',()=>{put(symbol(0)-6,0);adapter();},'RESET_SYMBOL_HEADER');
 const failure=(name,hook,reason)=>refuse(name,()=>{
  const p=plan(37),a=adapter(),owner=new BootstrapSchedule({memory,plan:p,digest:sha(JSON.stringify(p)),modules:all});
  assert.throws(()=>owner.run((m,r)=>hook(a,m,r)),new RegExp(reason),name);
  assert.equal(owner.state,'FAILED');assert(!owner.events.some(e=>e.id==='workload'&&e.event==='completed'));
  throw Error(reason);
 },reason);
 failure('no load',()=>()=>{},'COMPLETION_MISSING');
 failure('skip effect forge completion',(a,m,r)=>()=>put(r.completion.address,r.completion.value),'POSTCONDITION');
 failure('omit completion',(a,m,r)=>{const f=a.install(m,r);return()=>{f();put(r.completion.address,0);};},'COMPLETION_MISSING');
 failure('mutated installed bytes',(a,m,r)=>{m.bytes[0]^=1;return a.install(m,r);},'INSTALL_PLAN_IDENTITY');
 failure('different digest same behaviour',(a,m,r)=>{
  // Valid custom section, no behavioural change. Rebind the candidate record
  // and row together; the installer's private plan catalog must still refuse.
  m.bytes=Uint8Array.from([...m.bytes,0,2,1,120]);m.record.sha256=sha(m.bytes);r.sha256=m.record.sha256;
  assert(WebAssembly.validate(m.bytes));return a.install(m,r);
 },'INSTALL_PLAN_IDENTITY');
 reset(37);const p=plan(37),privateModules=all.map(m=>({name:m.name,record:structuredClone(m.record),bytes:Uint8Array.from(m.bytes)}));
 const a=adapter(privateModules);privateModules.forEach(m=>m.bytes.fill(0));
 try{new BootstrapSchedule({memory,plan:p,digest:sha(JSON.stringify(p)),modules:all}).run(a.install);}catch(e){throw Error('PRIVATE_CATALOG '+String(e));}
 assert.deepEqual(answers,read(dir,'expected.json')[0],'private loader bytes');
 return {base,rows,refusals,private_catalog:true,invocations};
}
if(!isMainThread){try{parentPort.postMessage(execute(workerData.dir,workerData.base));}catch(e){throw Error(String(e)+'\n'+e.stack);}}
else{
 const dir=process.argv[2],rows=[];
 for(const base of [4194304,2147483648]){
  const w=new Worker(new URL(import.meta.url),{workerData:{dir,base}});
  const exit=new Promise((resolve,reject)=>{w.once('error',reject);w.once('exit',c=>c?reject(Error('Worker exit '+c)):resolve());});
  const answer=new Promise((resolve,reject)=>{w.once('message',resolve);w.once('error',reject);});rows.push(await answer);await exit;
 }
 fs.writeFileSync(process.argv[3],JSON.stringify({status:'PASS',rows},null,2)+'\n');
}
