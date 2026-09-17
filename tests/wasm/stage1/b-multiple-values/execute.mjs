import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import {Worker,isMainThread,workerData,parentPort} from 'node:worker_threads';
const u32=n=>n<0?n+4294967296:n,NIL=77825,T=77838;
if(isMainThread){const w=new Worker(new URL(import.meta.url),{workerData:process.argv[2]});w.on('message',x=>fs.writeFileSync(process.argv[3],JSON.stringify(x,null,2)+'\n'));w.on('error',e=>{console.error(e);process.exitCode=1;});w.on('exit',c=>{if(c)process.exitCode=c;});}
else{
const dir=workerData,read=n=>JSON.parse(fs.readFileSync(path.join(dir,n))),mods=read('modules.json'),cases=read('cases.json');
const rootContracts=read('root-contracts.json');for(const m of mods){assert.equal(m.bound_words,rootContracts[m.name].bound_words,m.name+': independent bound slots');assert.equal(m.captures,rootContracts[m.name].captures,m.name+': independent capture count');}
const memory=new WebAssembly.Memory({initial:2,maximum:32769,shared:true});memory.grow(32767);const dv=new DataView(memory.buffer);
const tcr=256,table=new WebAssembly.Table({element:'anyfunc',initial:mods.length+1,maximum:mods.length+1});
const tail_table=new WebAssembly.Table({element:'anyfunc',initial:mods.length+1,maximum:mods.length+1});
const nonlocal_exit=new WebAssembly.Tag({parameters:['i32']});
const call_error=new WebAssembly.Tag({parameters:['i32']}),type_error=new WebAssembly.Tag({parameters:['i32','i32']}),conversion_error=new WebAssembly.Tag({parameters:['i32']});
const handles=new Map(mods.flatMap((m,i)=>m.source?[[m.name,131078+32*i]]:[])),byHandle=new Map([...handles].map(([n,h])=>[h,n]));
const load=p=>dv.getUint32(p,true),store=(p,x)=>dv.setUint32(p,x,true),get=o=>load(tcr+o),set=(o,x)=>store(tcr+o,x);
const keywords=Object.fromEntries(['a','b','x','y','external','bad','allow-other-keys'].map((k,i)=>[k,524294+i*16]));
assert(mods.length>447,'regression corpus crosses the removed registry ceiling');
assert(4104+16*(mods.length+1)<=16384,'code registry exceeds fixture-owned range');
assert(196608+32*mods.length<=262144,'function symbols exceed fixture-owned range');
const compiled=new Map(mods.map(m=>[m.name,new WebAssembly.Module(fs.readFileSync(path.join(dir,'installed',m.name+'.wasm')))]));
let multipleValueResources=0;let lexicalExitChecks=0;let progvChecks=0;let bindingInspections=0,bindingChecks=0,peakBindings=0;let controlInspections=0,stateChecks=0,chainChecks=0,chainFault=null;let cleanupEntries=0,cleanupResources=0;let publicDispatches=0,internalEntries=0;let checks=0,peakRoots=0,activeFrame=0,activeRoots=0,topContext=0;
function inspect(label){let head=get(128),slots=new Set(),seen=new Set(),frames=0;while(head){assert(!seen.has(head),label+': acyclic roots');seen.add(head);let n=load(head+4);if(head===activeFrame)assert.equal(n,activeRoots,label+': bound variables are roots');assert(n<=(get(72)-head-8)/4,label+': root capacity');for(let i=0;i<n;i++){let p=head+8+4*i;assert(!slots.has(p),label+': unique root scanner');assert(!(p>=get(120)&&p<get(124)),label+': output reservation is not a root record');slots.add(p);}head=load(head);frames++;}for(let i=0;i<get(116);i++)assert(!slots.has(get(120)+4*i),label+': result single scanner');let prior=get(72);for(let c=get(140);c;c=load(c)){
 assert(c%16===0&&c>=get(68)&&c+48<=prior,label+': bounded control chain');
 const capacity=load(c+8);assert(c+48+4*capacity<=get(72),label+': control extent');
 assert.equal(load(c+24),1128483889,label+': control version');assert([1,2,3].includes(load(c+4)),label+': control kind');
 assert.equal(load(c+16),c+32,label+': control root location');assert(seen.has(c+32),label+': control record rooted');
 assert.equal(load(c+36),capacity+2,label+': control root count');assert(load(c+12)<=capacity,label+': transfer count bound');
 assert([0,1,2].includes(load(c+20)),label+': saved unwind state');prior=c;controlInspections++;
 }let previous=get(72),depth=0;for(let b=get(112);b;b=load(b)){
 assert(b%16===0&&b>=get(68)&&b+32<=previous,label+': bounded binding chain');
 assert.equal(load(b+24),1112425521,label+': binding version');assert(seen.has(b+8),label+': saved binding rooted');assert.equal(load(b+12),2,label+': two saved binding roots');
 const symbol=load(b+16),index=load(b+4);assert.equal(load(symbol-6),1850,label+': binding symbol');assert.equal(load(symbol+22),index,label+': symbol binding index');assert(index>0&&index%4===0&&index/4<get(108),label+': binding index capacity');assert(get(104)+4*get(108)<=memory.buffer.byteLength,label+': binding vector extent');assert(!slots.has(get(104)+index),label+': TLB has its own scanner');
 previous=b;depth++;bindingInspections++;
 }peakBindings=Math.max(peakBindings,depth);assert([0,1,2].includes(get(148)),label+': unwind state');peakRoots=Math.max(peakRoots,frames);checks++;}
let stressState=null;const tailRuns=[];let nonTailChecks=0,tailChecks=0;
const observations=[];let resultChecks=0,callableChecks=0,closureChecks=0,localChecks=0;
for(const observed of [false,true]){
 const functions=new Map();
 const symbols=Object.fromEntries(mods.flatMap((m,i)=>m.source?[[m.name,196614+32*i]]:[]));
 const specialNames=['dyn_a','dyn_b','dyn_u'];specialNames.forEach((name,i)=>symbols[name]=600006+32*i);
 const tailObserver=new WebAssembly.Module(fs.readFileSync(path.join(dir,'installed','observe_tail.wasm')));
 const observer=new WebAssembly.Module(fs.readFileSync(path.join(dir,'installed','observe_entry.wasm')));
 for(const m of mods){
  const codes=Object.fromEntries(mods.map((m,i)=>[m.name,4*(i+1)]));
  const instance=new WebAssembly.Instance(compiled.get(m.name),{env:{memory,tcr,table,tail_table,code_registry:4096,call_error,type_error,nonlocal_exit},symbols,keywords,codes});
  const entry=instance.exports.entry;functions.set(m.name,entry);
  const wrapper=new WebAssembly.Instance(observer,{env:{entry,observe:()=>{publicDispatches++;assert.fail('compiled call entered public B wrapper');}}}).exports.entry;
  table.set(functions.size,wrapper);
  const tail=instance.exports.tail_entry;
  tail_table.set(functions.size,observed?new WebAssembly.Instance(tailObserver,{env:{entry:tail,observe:(self,n,context)=>{internalEntries++;inspect('internal '+m.name);assert.equal(load(u32(self)-2),4*(mods.findIndex(x=>x.name===m.name)+1),'tail self');assert.equal(get(64),u32(context)+48,'tail argument area');assert.equal(get(128),u32(context)+32,'retired root frames');assert.equal(load(u32(context)+40),u32(self),'continuation SELF root');assert.equal(load(u32(context)+12),load(u32(context)+32),'saved and linked parent root');assert.equal(load(u32(context)+36),2+4*Math.ceil(n/4),'tail root count');if(m.name==='ct_state'){assert.equal(get(148),load(get(64)+4)/4,'dynamic unwind state at Lisp observation');stateChecks++;}
 if(m.name==='ct_raw_throw'&&chainFault){const c=get(140),fault=chainFault;chainFault=null;
  if(fault==='absent')set(140,0);if(fault==='alignment')set(140,c+1);if(fault==='outside')set(140,get(72)+16);if(fault==='short-header')set(140,get(72)-16);
  const edits={'marker':[24,0],'capacity':[8,0xffffffff],'root':[16,c+48],'root-count':[36,0],'kind':[4,4],'cycle':[0,c],'higher':[0,c+16]};if(edits[fault])store(c+edits[fault][0],edits[fault][1]);
 }
 if(m.name==='uw_cleanup'){
 const c=u32(context),budget=c-get(120),retention=load(c+12);
 assert.equal(retention,c-budget-16*Math.ceil((48+budget)/16)+32,'cleanup resumes at original stack cursor');
 assert.equal(load(retention+4),2+budget/4,'cleanup retention root extent');
 // Find the nearest surviving continuation through the actual root chain.
 // A continuation owns itself at raw+8, and roots SELF at raw+40.
 let h=load(retention),parent=0;
 while(h){const q=h-32;if(q>=get(68)&&load(q+8)===q&&load(q+40)!==NIL){parent=q;break;}h=load(h);}
 assert(parent,'cleanup has a surviving continuation');
 assert.equal(load(c),parent+48,'cleanup resumes with original VSP');
 cleanupEntries++;
} if(stressState){stressState.transfers++;assert.equal(u32(context),stressState.context,'one continuation per tail chain');let depth=0;for(let h=get(128);h;h=load(h))depth++;assert.equal(depth,2,'constant tail root depth');stressState.maxRootDepth=Math.max(stressState.maxRootDepth,depth);stressState.maxArguments=Math.max(stressState.maxArguments,n);}if(u32(context)===topContext){activeFrame=u32(context)+48+16*Math.ceil(n/4)+load(u32(context)+24);activeRoots=Math.max(4,(get(124)-get(120))/4)+rootContracts[m.name].bound_words;}}}}).exports.entry:tail);
 }
 function installObjects(){
  set(104,610000);set(108,4);set(112,0);set(0,37);
  for(let i=0;i<4;i++)store(610000+4*i,243);
  specialNames.forEach((name,i)=>{const base=symbols[name]-6;store(base,1850);for(let j=1;j<8;j++)store(base+4*j,NIL);store(base+8,i===2?51:4*(101+2*i));store(base+20,0);store(base+28,4*(i+1));});
  store(4096,mods.length+1);store(4100,1);
  for(let i=0;i<mods.length;i++){
   const row=4104+16*(i+1);
   if(mods[i].source){
    const base=handles.get(mods[i].name)-6,symbol=symbols[mods[i].name]-6;
    store(base,1322);store(base+4,4*(i+1));store(base+8,NIL);store(base+12,4);store(base+16,NIL);store(base+20,NIL);
    store(symbol,1850);for(let j=1;j<8;j++)store(symbol+4*j,NIL);store(symbol+12,base+6);
   }else{assert.equal(load(131072+32*i),0,'no static inner function object');assert.equal(load(196608+32*i),0,'no static inner symbol');}
   store(row,i+1);store(row+4,4);store(row+8,17);store(row+12,23);
  }
 }
 for(const start of [65536,2147483648]){
  const root=start-8,out=start+8192,owner=out+256,limit=start+32768,heap=start===65536?262144:limit,heapLimit=heap+32768;
  const encode=x=>typeof x==='number'?(x*4+4294967296)%4294967296:x==='nil'?NIL:x==='t'?T:x.startsWith(':')?keywords[x.slice(1)]:x.startsWith('n')?16385+8*Number(x.slice(1)):x.startsWith('s:')?symbols[x.slice(2)]:handles.get(x.slice(2));
  let objects=[],objectNames=new Map(),closureNames=new Map();
  const decode=x=>{x=u32(x);if(x===NIL)return'nil';if(x===T)return't';for(const [k,v]of Object.entries(keywords))if(x===v)return ':'+k;
   if(byHandle.has(x))return 'f:'+byHandle.get(x);
   for(const [name,p]of Object.entries(symbols))if(p===x)return 's:'+name;
   if(x%8===6&&x>=heap+6&&x+18<=get(48)&&load(x-6)===1322){if(!closureNames.has(x))closureNames.set(x,'c'+closureNames.size);return closureNames.get(x);}
   if(objectNames.has(x))return 'n'+objectNames.get(x);
   if(x>=heap+1&&x+7<=get(48)&&(x-heap-1)%8===0){objectNames.set(x,objects.length);objects.push(x);return 'n'+(objects.length-1);}
   if(x%4===0)return (x>=2147483648?x-4294967296:x)/4;throw Error('Unrepresented result '+x);};
  for(const c of cases){closureNames=new Map();const capacity=c.capacity,owner=out+4*capacity;topContext=owner;activeFrame=owner+48+16*Math.ceil(c.args.length/4);activeRoots=Math.max(4,capacity)+rootContracts[c.function].bound_words;new Uint8Array(memory.buffer,0,32768).fill(0);new Uint8Array(memory.buffer,root,32776).fill(0);new Uint8Array(memory.buffer,heap,32768).fill(0xcd);set(48,heap);set(52,heapLimit);set(56,heap);objects=c.nodes.map((_,i)=>16385+8*i);objectNames=new Map(objects.map((p,i)=>[p,i]));
   installObjects();for(const [name,target]of Object.entries(c.bindings))store(symbols[name]+6,handles.get(target));
   for(let i=0;i<c.nodes.length;i++){store(16384+8*i,encode(c.nodes[i][1]));store(16388+8*i,encode(c.nodes[i][0]));}
   store(root,0);store(root+4,c.args.length);c.args.forEach((v,i)=>store(start+4*i,encode(v)));
   new Uint8Array(memory.buffer,out,4*capacity).fill(0xa5);set(64,start);set(68,start);set(72,limit);set(116,0);set(120,out);set(124,owner);set(128,root);
   const savedArgs=new Uint8Array(memory.buffer,start,4*c.args.length).slice();let result=[],status='RETURN',count=0,primary=NIL;
   try{const pair=functions.get(c.function)(handles.get(c.function),c.args.length);[primary,count]=pair.map(u32);assert(count<=capacity,c.id+': count bound');assert.equal(get(116),count,c.id+': count ownership');result=Array.from({length:count},(_,i)=>decode(load(out+4*i)));assert.equal(decode(primary),count?result[0]:'nil',c.id+': primary');}
   catch(e){assert(e instanceof WebAssembly.Exception,c.id+': checked failure, not engine trap: '+e);if(e.is(type_error))status='TYPE';else{assert(e.is(call_error));const code=e.getArg(call_error,0);assert([1,4,5,8,10,12].includes(code),c.id+': unexpected call refusal '+code);status=code===1?'ARITY':code===5?'TYPE':code===8?'CONTROL':code===10?'UNBOUND':code===12?'BINDING':'DESIGNATOR';}assert.equal(get(116),0,c.id+': exceptional count');}
   const nodes=[];for(let i=0;i<objects.length;i++)nodes.push([decode(load(objects[i]+3)),decode(load(objects[i]-1))]);assert.equal(get(48),heap+8*c.allocated_cells+c.closure_bytes,c.id+': allocation count');assert(new Uint8Array(memory.buffer,get(48),heapLimit-get(48)).every(x=>x===0xcd),c.id+': heap tail untouched');const specials=specialNames.map(name=>load(symbols[name]+2)===51?'unbound':decode(load(symbols[name]+2)));assert.deepEqual({status,values:result,nodes,specials},c.expected,c.id+': native/logical result');assert.equal(get(112),0,c.id+': binding chain restored');assert.deepEqual(Array.from({length:4},(_,i)=>load(610000+4*i)),[243,243,243,243],c.id+': binding vector restored');
   assert.deepEqual([get(64),get(120),get(124),get(128)],[start,out,owner,root],c.id+': restored ownership');assert.deepEqual(new Uint8Array(memory.buffer,start,4*c.args.length),savedArgs,c.id+': caller arguments unchanged');assert(new Uint8Array(memory.buffer,out+4*count,4*capacity-4*count).every(x=>x===0xa5),c.id+': unpublished result tail');assert.deepEqual([get(140),get(148)],[0,0],c.id+': control chain retired');inspect('returned '+c.id);observations.push({id:c.id,observed,start,status,values:result,nodes,specials});
  }
  // Host-turn escape: save the generated closure, overwrite the entire Lisp
  // stack, then call it on fresh invocations. No host closure resolver exists.
  function invoke(name,args,self=handles.get(name)){
   activeFrame=0;topContext=0;new Uint8Array(memory.buffer,root,32776).fill(0x9b);
   store(root,0);store(root+4,args.length);args.forEach((v,i)=>store(start+4*i,v));
   set(64,start);set(68,start);set(72,limit);set(116,0);set(120,out);set(124,owner);set(128,root);new Uint8Array(memory.buffer,out,256).fill(0xa5);
   try {const pair=functions.get(name)(self,args.length).map(u32);assert.equal(pair[1],get(116));return Array.from({length:pair[1]},(_,i)=>load(out+4*i));}
   finally {assert.deepEqual([get(64),get(120),get(124),get(128)],[start,out,owner,root],'closure host-turn ownership');assert.deepEqual([get(140),get(148)],[0,0],'host control state');inspect('closure host turn');}
  }
  installObjects();new Uint8Array(memory.buffer,heap,32768).fill(0xcd);set(48,heap);set(52,heapLimit);set(56,heap);
  // Resource exceptions must run cleanup too, with no heap rollback.
  for(const [name,code,marker] of [['uw_capacity',3,211],['uw_heap',6,223]]){
   store(16384,NIL);store(16388,44);if(name==='uw_heap')set(52,heap);
   assert.throws(()=>invoke(name,[16385]),e=>e instanceof WebAssembly.Exception&&e.is(call_error)&&e.getArg(call_error,0)===code,name+': checked resource condition');
   assert.equal(load(16388),marker*4,name+': cleanup ran on resource failure');assert.equal(get(116),0,name+': no returned values');set(52,heapLimit);cleanupResources++;
  }
  store(16384,NIL);store(16388,44);
  assert.throws(()=>invoke('uw_datum',[16385,2664]),e=>e instanceof WebAssembly.Exception&&e.is(type_error)&&e.getArg(type_error,0)===2664&&e.getArg(type_error,1)===1,'cleanup preserves original exception tag and datum');
  assert.equal(load(16388),908);cleanupResources++;
  for(const fault of ['header','nonfixnum','negative','reserved','index-limit','zero-pointer','alignment','empty','extent','near-end','partial-capacity']){
   installObjects();const symbol=symbols.dyn_a;
   if(fault==='header')store(symbol-6,1849);if(fault==='nonfixnum')store(symbol+22,5);if(fault==='negative')store(symbol+22,0xfffffffc);if(fault==='reserved')store(symbol+22,0);if(fault==='index-limit')store(symbol+22,16);
   if(fault==='zero-pointer')set(104,0);if(fault==='alignment')set(104,610001);if(fault==='empty')set(108,0);if(fault==='extent')set(108,0xffffffff);if(fault==='near-end')set(104,0xfffffff0);if(fault==='partial-capacity')set(108,2);
   const before=new Uint8Array(memory.buffer,600000,96).slice();
   assert.throws(()=>invoke(fault==='partial-capacity'?'sd_sequential':'sd_bind',[44]),e=>e instanceof WebAssembly.Exception&&e.is(call_error)&&e.getArg(call_error,0)===11,'binding metadata refusal '+fault);
   assert.equal(get(112),0,'partial binding unwound');assert.deepEqual(Array.from({length:4},(_,i)=>load(610000+4*i)),[243,243,243,243],'refused binding preserves TLB');assert.deepEqual(new Uint8Array(memory.buffer,600000,96),before,'refused binding preserves symbols');bindingChecks++;
  }installObjects();
  // Target-only malformed metadata, post-values list mutation, and resource
  // refusals. These are not counted as native CL semantics comparisons.
  for(const fault of ['constant','global','flags-tag','cycle-after-values','record-capacity','short-values']){
   installObjects();store(16384,52);store(16388,44);store(20000,NIL);store(20004,symbols.dyn_a);store(24000,NIL);store(24004,148);
   const flags={constant:8,global:16,'flags-tag':1};if(fault in flags)store(symbols.dyn_a+14,flags[fault]);
   let name='pv_order',args=[16385,20001,24001],code=12;
   if(fault==='cycle-after-values'){name='pv_cycle_after';args=[20001,24001];}
   if(fault==='record-capacity'){for(let i=0;i<1100;i++){store(20000+8*i,i===1099?NIL:20009+8*i);store(20004+8*i,symbols.dyn_a);}args=[16385,20001,NIL];code=2;}
   if(fault==='short-values'){store(20000,20009);store(20008,NIL);store(20012,symbols.dyn_b);store(24000,28);name='pv_read';args=[20001,24001];code=5;}
   assert.throws(()=>invoke(name,args),e=>e instanceof WebAssembly.Exception&&e.is(call_error)&&e.getArg(call_error,0)===code,'PROGV refusal '+fault);
   assert.equal(get(112),0,'PROGV refusal unbinds '+fault);assert.deepEqual(Array.from({length:4},(_,i)=>load(610000+4*i)),[243,243,243,243],'PROGV refusal restores vector '+fault);
   if(fault in flags||fault==='record-capacity')assert.deepEqual([load(16388),load(16384)],[44,13*4],'PROGV validates before values '+fault);
   progvChecks++;
  }installObjects();
  if(observed)for(const fault of ['absent','alignment','outside','short-header','marker','capacity','root','root-count','kind','cycle','higher']){
   chainFault=fault;assert.throws(()=>invoke('ct_raw_catch',[28,44]),e=>e instanceof WebAssembly.Exception&&e.is(call_error)&&e.getArg(call_error,0)===(fault==='absent'?8:9),'checked control-chain refusal '+fault);assert.equal(chainFault,null);chainChecks++;
  }
  for(const remaining of [0,7,8]){
   set(48,heap);set(52,heap+remaining);const before=new Uint8Array(memory.buffer,heap,16).slice();
   if(remaining<8){assert.throws(()=>invoke('bl_cons',[28,44]),e=>e instanceof WebAssembly.Exception&&e.is(call_error)&&e.getArg(call_error,0)===6,'CONS complete allocation before writes');assert.equal(get(48),heap);assert.deepEqual(new Uint8Array(memory.buffer,heap,16),before);}
   else {assert.deepEqual(invoke('bl_cons',[28,44]),[heap+1]);assert.equal(get(48),heap+8);assert.deepEqual([load(heap),load(heap+4)],[44,28]);}
   lexicalExitChecks++;
  }
  set(48,heap);set(52,heap+32768);
  const expired=invoke('bl_factory',[])[0];
  for(const name of ['dynamic_one','bl_use_stale']){
   assert.throws(()=>invoke(name,name==='dynamic_one'?[expired,28]:[expired]),e=>e instanceof WebAssembly.Exception&&e.is(call_error)&&e.getArg(call_error,0)===8,'expired lexical block '+name);
   assert.equal(get(112),0,'expired block restores bindings');lexicalExitChecks++;
  }
  // Restore the heap baseline for inherited byte-exact closure checks.
  new Uint8Array(memory.buffer,heap,32768).fill(0xcd);set(48,heap);
  const escaped=invoke('cell_factory',[28])[0],env=load(escaped+2),cell=load(env-2);
  assert.equal(escaped,heap+14,'factory cell precedes closure');assert.equal(load(escaped-6),1322);assert.equal(load(env-6),506);assert.equal(load(cell-1),NIL);assert.equal(load(cell+3),28);closureChecks++;
  assert.deepEqual(invoke('dynamic0',[escaped]),[28]);closureChecks++;
  assert.deepEqual(invoke('dynamic_one',[escaped,68]),[68]);closureChecks++;
  assert.deepEqual(invoke('dynamic0',[escaped]),[68]);assert.equal(load(cell+3),68);closureChecks++;
  const second=invoke('cell_factory',[92])[0];assert.notEqual(second,escaped);assert.notEqual(load(load(second+2)-2),cell);assert.deepEqual(invoke('dynamic0',[second]),[92]);assert.deepEqual(invoke('dynamic0',[escaped]),[68]);closureChecks++;
  // Bad SELF environments are checked before any captured load or write.
  for(const fault of ['nil-environment','environment-tag','environment-header','environment-length','environment-outside','nil-cell','cell-tag','cell-outside']){
   const oldEnv=load(escaped+2),oldHeader=load(env-6),oldCell=load(env-2);
   if(fault==='nil-environment')store(escaped+2,NIL);
   if(fault==='environment-tag')store(escaped+2,env+1);
   if(fault==='environment-header')store(env-6,1322);
   if(fault==='environment-length')store(env-6,762);
   if(fault==='environment-outside')store(escaped+2,memory.buffer.byteLength+6);
   if(fault==='nil-cell')store(env-2,NIL);
   if(fault==='cell-tag')store(env-2,cell+1);
   if(fault==='cell-outside')store(env-2,memory.buffer.byteLength+1);
   let reason=0;
   try{invoke('dynamic0',[escaped]);}catch(e){assert(e instanceof WebAssembly.Exception&&e.is(call_error),fault+': checked environment failure');reason=e.getArg(call_error,0);}
   finally{store(escaped+2,oldEnv);store(env-6,oldHeader);store(env-2,oldCell);}
   assert.equal(reason,4,fault+': environment refusal');assert.equal(load(cell+3),68,fault+': no captured mutation');assert(new Uint8Array(memory.buffer,out,256).every(x=>x===0xa5));closureChecks++;
  }
  // Allocation refuses before touching an unavailable region. Cell allocation
  // may succeed before closure allocation fails; it is retained, not rolled back.
  for(const bytes of [0,7,8,39,40]){
   new Uint8Array(memory.buffer,heap,32768).fill(0xcd);set(48,heap);set(52,heap+bytes);set(56,heap);let reason=0,values=[];
   try{values=invoke('factory',[44]);}catch(e){assert(e instanceof WebAssembly.Exception&&e.is(call_error),'closure heap checked');reason=e.getArg(call_error,0);}
   assert.equal(reason,bytes<40?6:0,'closure allocation limit '+bytes);assert.equal(get(48),heap+(bytes<8?0:bytes<40?8:40),'closure allocation publication '+bytes);
   assert(new Uint8Array(memory.buffer,get(48),heapLimit-get(48)).every(x=>x===0xcd),'closure allocation tail '+bytes);
   if(reason)assert(new Uint8Array(memory.buffer,out,256).every(x=>x===0xa5),'closure failure unpublished');else assert.deepEqual(invoke('dynamic0',values),[44]);closureChecks++;
  }
  set(52,heapLimit);
  // The local function group escapes across host turns; its recursive lexical
  // cells must survive wholesale stack replacement and preserve shared state.
  set(48,heap);set(56,heap);store(16384,NIL);store(16388,NIL);
  assert.deepEqual(invoke('local_labels_pair_factory',[28,16385]),[16385]);
  const localGet=load(16388),localRelay=load(16384);
  assert.equal(get(48),heap+120);localChecks++;
  assert.deepEqual(invoke('dynamic0',[localGet]),[28]);localChecks++;
  assert.deepEqual(invoke('dynamic_one',[localRelay,92]),[92]);localChecks++;
  assert.deepEqual(invoke('dynamic0',[localGet]),[92]);localChecks++;
  for(const bytes of [0,8,15,16]){
   new Uint8Array(memory.buffer,heap,32768).fill(0xcd);set(48,heap);set(52,heap+bytes);let reason=0,values=[];
   try{values=invoke('local_inline_rest',[44]);}catch(e){assert(e instanceof WebAssembly.Exception&&e.is(call_error));reason=e.getArg(call_error,0);}
   assert.equal(reason,bytes<16?6:0,'inline rest extent');assert.equal(get(48),heap+(bytes<16?0:16));
   assert(new Uint8Array(memory.buffer,get(48),heapLimit-get(48)).every(x=>x===0xcd),'inline rest no partial write');
   if(!reason){assert.deepEqual(values,[44,heap+1]);assert.equal(load(heap+4),28);assert.equal(load(heap),heap+9);assert.equal(load(heap+12),44);assert.equal(load(heap+8),NIL);}localChecks++;
  }
  set(52,heapLimit);
  // Literal APPLY's callable is temporary stack storage; a nested closure
  // may escape, but its cells and environment must be independently owned.
  installObjects();set(48,heap);set(52,heap);set(56,heap);store(16384,NIL);store(16388,68);
  assert.deepEqual(invoke('tail_apply_nocapture',[16385]),[68,116]);assert.equal(get(48),heap,'literal APPLY requires no heap for its callable');tailChecks++;
  set(52,heapLimit);const appliedEscape=invoke('tail_apply_escape',[28,16385])[0];assert.equal(get(48),heap+56);tailChecks++;
  assert.deepEqual(invoke('dynamic0',[appliedEscape]),[28,68]);tailChecks++;
  // Paired tail tables are owner-supplied, but absence and extent are checked.
  for(const entryName of ['dynamic_one','nested'])for(const missing of ['null','range']){
   const slot=mods.findIndex(m=>m.name==='v1')+1,old=tail_table.get(slot);
   const entry=missing==='range'?new WebAssembly.Instance(compiled.get(entryName),{env:{memory,tcr,table,tail_table:new WebAssembly.Table({element:'anyfunc',initial:1,maximum:1}),code_registry:4096,call_error,type_error,nonlocal_exit},symbols,keywords,codes:Object.fromEntries(mods.map((m,i)=>[m.name,4*(i+1)]))}).exports.entry:functions.get(entryName);
   if(missing==='null')tail_table.set(slot,null);
   activeFrame=0;topContext=0;store(root,0);store(root+4,2);store(start,handles.get('v1'));store(start+4,28);set(64,start);set(68,start);set(72,limit);set(116,0);set(120,out);set(124,owner);set(128,root);let reason=0;
   try{entry(handles.get(entryName),2);}catch(e){assert(e instanceof WebAssembly.Exception&&e.is(call_error),'tail table checked refusal');reason=e.getArg(call_error,0);}finally{tail_table.set(slot,old);}
   assert.equal(reason,4);assert.deepEqual([get(64),get(120),get(124),get(128),get(116)],[start,out,owner,root,0]);tailChecks++;
  }
  // Malformed objects and registry metadata must fail before indirect entry.
  for(const fault of ['tag','header','short-header','end-pointer','symbol-header','symbol-cycle','unbound','id-tag','id-zero','id-range','version-tag','version-zero','version-mismatch','signature','role','slot-zero','slot-range','slot-null','registry-prefix']){
   installObjects();activeFrame=0;
   const object=handles.get('v1'),symbol=symbols.v1,slot=mods.findIndex(m=>m.name==='v1')+1,row=4104+16*slot;
   let designator=object;const oldEntry=table.get(slot);
   if(fault==='tag'){const bytes=new Uint8Array(memory.buffer,object-6,24).slice();new Uint8Array(memory.buffer,154001,24).set(bytes);designator=154007;}
   if(fault==='header')store(object-6,1850);
   if(fault==='short-header')store(object-6,1066);
   if(fault==='end-pointer'){designator=memory.buffer.byteLength-2;store(designator-6,1322);store(designator-2,4*slot);}
   if(fault==='symbol-header'){designator=symbol;store(symbol-6,1594);}
   if(fault==='symbol-cycle'){designator=symbol;store(symbol+6,symbol);}
   if(fault==='unbound'){designator=symbol;store(symbol+6,NIL);}
   if(fault==='id-tag')store(object-2,5);
   if(fault==='id-zero')store(object-2,0);
   if(fault==='id-range'){const extra=4104+16*(mods.length+1);store(object-2,4*(mods.length+1));store(extra,slot);store(extra+4,4);store(extra+8,17);store(extra+12,23);}
   if(fault==='version-tag'){store(object+6,5);store(row+4,5);}
   if(fault==='version-zero'){store(object+6,0);store(row+4,0);}
   if(fault==='version-mismatch')store(object+6,8);
   if(fault==='signature')store(row+8,91);
   if(fault==='role')store(row+12,91);
   if(fault==='slot-zero')store(row,0);
   if(fault==='slot-range')store(row,table.length);
   if(fault==='slot-null')table.set(slot,null);
   if(fault==='registry-prefix')store(4100,0);
   store(root,0);store(root+4,2);store(start,designator);store(start+4,28);set(64,start);set(68,start);set(72,limit);set(116,0);set(120,out);set(124,owner);set(128,root);new Uint8Array(memory.buffer,out,256).fill(0xa5);
   let reason=0;try{functions.get('dynamic_one')(handles.get('dynamic_one'),2);}catch(e){assert(e instanceof WebAssembly.Exception&&e.is(call_error),fault+': checked object refusal');reason=e.getArg(call_error,0);}finally{table.set(slot,oldEntry);}
   assert.equal(reason,4,fault+': object reason');assert.deepEqual([get(64),get(120),get(124),get(128),get(116)],[start,out,owner,root,0],fault+': restored ownership');assert(new Uint8Array(memory.buffer,out,256).every(x=>x===0xa5),fault+': unpublished result');callableChecks++;
  }
  // Two objects can share code without sharing identity or environment.
  installObjects();for(const environment of [NIL,16385]){
   const alias=150006;for(let i=0;i<24;i++)new Uint8Array(memory.buffer,alias-6,24)[i]=new Uint8Array(memory.buffer,handles.get('v1')-6,24)[i];store(alias+2,environment);
   store(root,0);store(root+4,2);store(start,alias);store(start+4,52);set(64,start);set(68,start);set(72,limit);set(116,0);set(120,out);set(124,owner);set(128,root);
   const pair=functions.get('dynamic_one')(handles.get('dynamic_one'),2).map(u32);assert.deepEqual(pair,[52,1]);assert.equal(load(alias+2),environment,'distinct environment preserved');callableChecks++;
  }
  installObjects();
  // The formerly stack-exhausting tail recursion now completes.
  {activeFrame=0;installObjects();for(let i=0;i<80;i++){store(16384+8*i,i===79?NIL:16393+8*i);store(16388+8*i,4*i);}store(root,0);store(root+4,1);store(start,16385);set(64,start);set(68,start);set(72,limit);set(116,0);set(120,out);set(124,owner);set(128,root);new Uint8Array(memory.buffer,out,256).fill(0xa5);
   let reason=0;try{functions.get('walk_list')(handles.get('walk_list'),1);}catch(e){assert(e instanceof WebAssembly.Exception&&e.is(call_error),'recursive stack checked');reason=e.getArg(call_error,0);}assert.equal(reason,0,'tail recursion is bounded');assert.deepEqual([get(64),get(120),get(124),get(128)],[start,out,owner,root]);assert.equal(get(116),2);assert.deepEqual([load(out),load(out+4)],[284,292]);callableChecks++;
  }
  // Resource refusals are target-specific, separate from native Lisp cases.
  activeFrame=0;for(const capacity of ['stack','results','alignment','bound-frame','argument-region']){
   store(root,0);store(root+4,6);for(let i=0;i<6;i++)store(start+4*i,(i+1)*4);set(64,start);set(68,start);set(72,capacity==='stack'?owner+16:capacity==='bound-frame'?owner+272:limit);set(116,0);set(120,out);set(124,capacity==='results'?out+16:owner);set(128,root);if(capacity==='alignment')set(64,start+1);if(capacity==='argument-region')set(120,start+16);if(capacity==='bound-frame')set(64,start);
   const snapshot=[get(64),get(120),get(124),get(128),get(116)];let code=0;try{functions.get(capacity==='bound-frame'?'opt':'v6')(handles.get(capacity==='bound-frame'?'opt':'v6'),capacity==='bound-frame'?1:6);}catch(e){assert(e instanceof WebAssembly.Exception&&e.is(call_error));code=e.getArg(call_error,0);}assert.equal(code,capacity==='results'?3:2,'checked '+capacity);assert.deepEqual([get(64),get(120),get(124),get(128),get(116)],snapshot,'resource failure restores '+capacity);
  }
  // These are target-specific malformed input/resource checks. Circular APPLY
  // is deliberately never sent to native CCL, where termination is unspecified.
  for(const kind of ['heap-exhausted','heap-unaligned','heap-below-base','heap-outside-memory','incoming-count-overflow','incoming-count-max','apply-space','cycle-one','cycle-tail','list-outside-memory']){
   activeFrame=0;new Uint8Array(memory.buffer,heap,32768).fill(0xcd);set(48,heap);set(52,heapLimit);set(56,heap);
   store(root,0);store(root+4,2);set(64,start);set(68,start);set(72,limit);set(116,0);set(120,out);set(124,owner);set(128,root);
   let name='rest_all',nargs=2,expected=6;store(start,4);store(start+4,8);
   if(kind==='heap-exhausted')set(52,heap+8);
   if(kind==='heap-unaligned')set(48,heap+1);
   if(kind==='heap-below-base')set(56,heap+8);
   if(kind==='heap-outside-memory')set(52,memory.buffer.byteLength+8);
   if(kind==='incoming-count-overflow'||kind==='incoming-count-max'){nargs=kind==='incoming-count-max'?4294967295:1073741824;expected=2;}
   if(kind.startsWith('cycle')||kind==='list-outside-memory'||kind==='apply-space'){
    name='apply0';store(start,handles.get('rest_all'));store(start+4,16385);store(16388,44);store(16384,kind==='cycle-one'?16385:16393);store(16396,52);store(16392,16393);expected=5;
    if(kind==='list-outside-memory')store(start+4,4294967289);
    if(kind==='apply-space'){store(16392,16401);store(16404,68);store(16400,NIL);set(72,owner+304);expected=2;}
   }
   if(kind==='apply-space')new Uint8Array(memory.buffer,get(72),64).fill(0xa7);
   const snapshot=[get(64),get(120),get(124),get(128),get(116),get(48)];let code=0;
   try{functions.get(name)(handles.get(name),nargs);}catch(e){assert(e instanceof WebAssembly.Exception&&e.is(call_error),kind+': checked refusal, not trap');code=e.getArg(call_error,0);}
   assert.equal(code,expected,kind+': reason');assert.deepEqual([get(64),get(120),get(124),get(128),get(116),get(48)],snapshot,kind+': no publication');assert(new Uint8Array(memory.buffer,heap,32768).every(x=>x===0xcd),kind+': no heap writes');if(kind==='apply-space')assert(new Uint8Array(memory.buffer,get(72),64).every(x=>x===0xa7),kind+': stack fence');
  }
  // Result budgets and scratch frames are resources, not fixed value counts.
  // All observations below come from literal region geometry and pre-call bytes.
  for(const kind of ['values-short','direct-short','apply-short','discard-short','empty-output','entry-space','values-space','extent-overflow']){
   activeFrame=0;topContext=0;new Uint8Array(memory.buffer,root,32776).fill(0xa5);
   let name='v65',nargs=65,cap=64,expected=3,actualOwner=out+256,actualLimit=limit;
   for(let i=0;i<65;i++)store(start+4*i,(i+1)*4);
   if(kind==='direct-short')name='call65';
   if(kind==='apply-short'){name='apply0';nargs=2;store(start,handles.get('v65'));store(start+4,16385);for(let i=0;i<65;i++){store(16384+8*i,i===64?NIL:16393+8*i);store(16388+8*i,(i+1)*4);}}
   if(kind==='discard-short'){name='discard_values';nargs=0;}
   if(kind==='empty-output'){name='v1';nargs=1;cap=0;actualOwner=out;}
   if(kind==='entry-space'||kind==='values-space'){name='many';nargs=1;store(start,28);cap=132;actualOwner=out+528;actualLimit=actualOwner+(kind==='entry-space'?528:1056);expected=2;}
   if(kind==='extent-overflow'){name='v0';nargs=0;actualOwner=memory.buffer.byteLength-64;actualLimit=memory.buffer.byteLength;expected=2;}
   store(root,0);store(root+4,nargs);set(64,start);set(68,start);set(72,actualLimit);set(116,0);set(120,out);set(124,actualOwner);set(128,root);
   const before=[get(64),get(120),get(124),get(128),get(116)];
   if(kind==='extent-overflow')new Uint8Array(memory.buffer,actualOwner,64).fill(0xa7);
   else new Uint8Array(memory.buffer,actualLimit,64).fill(0xa7);
   let code=0;try{functions.get(name)(handles.get(name),nargs);}catch(e){assert(e instanceof WebAssembly.Exception&&e.is(call_error),kind+': checked result refusal');code=e.getArg(call_error,0);}
   assert.equal(code,expected,kind+': result reason');assert.deepEqual([get(64),get(120),get(124),get(128),get(116)],before,kind+': restored result ownership');
   assert(new Uint8Array(memory.buffer,out,kind==='extent-overflow'?256:4*cap).every(x=>x===0xa5),kind+': no result publication');
   assert(new Uint8Array(memory.buffer,kind==='extent-overflow'?actualOwner:actualLimit,64).every(x=>x===0xa7),kind+': result stack fence');resultChecks++;
  }
  // Exactly sufficient context, scratch and staging: 64 + 544 + 528 bytes.
  {activeFrame=0;store(root,0);store(root+4,1);store(start,28);set(64,start);set(68,start);set(72,out+528+1136);set(116,0);set(120,out);set(124,out+528);set(128,root);
   const [value,count]=functions.get('many')(handles.get('many'),1).map(u32);assert.equal(value,28);assert.equal(count,130);assert.equal(load(out+4*129),2147483644);assert.deepEqual([get(64),get(120),get(124),get(128)],[start,out,out+528,root]);resultChecks++;
  }
  // Empty rest lists require no allocation; exact capacity is sufficient.
  for(const n of [0,2]){set(48,heap);set(52,heap+8*n);set(56,heap);set(64,start);set(68,start);set(72,limit);set(116,0);set(120,out);set(124,owner);set(128,root);store(root+4,n);store(start,28);store(start+4,36);
   const [value,count]=functions.get('rest_all')(handles.get('rest_all'),n).map(u32);assert.equal(count,1,'rest exact capacity count');assert.equal(get(48),heap+8*n,'rest exact capacity pointer');if(!n)assert.equal(value,NIL,'empty rest');else{assert.equal(load(value+3),28);const tail=load(value-1);assert.equal(load(tail+3),36);assert.equal(load(tail-1),NIL);}
  }
  // Each chain exceeds the engine's ordinary recursion depth by a wide margin.
  // Input lists live outside the owned allocation region. No per-step heap
  // allocation is permitted for these forms; output and argument fences remain.
  const longBase=1048576,steps=100000;
  for(let i=0;i<steps;i++){store(longBase+8*i,i===steps-1?NIL:longBase+8*i+9);store(longBase+8*i+4,4*(i%97));}
  const head=longBase+1;
  for(const scenario of [
   {name:'mvc_tail',args:[head],values:[284,292],heap:0},
   {name:'mvb_tail',args:[head],values:[284,292],heap:0},
   {name:'mvc_tail_indirect',args:[handles.get('mvc_tail_indirect'),head],values:[284,292],heap:0},
   {name:'walk_list',args:[head],values:[284,292],heap:0},
   {name:'tail_apply_loop',args:[head],values:[284,292],heap:0},
   {name:'tail_indirect',args:[handles.get('tail_indirect'),head],values:[284,292],heap:0},
   {name:'tail_wide_a',args:[head],values:[284,292],heap:0},
   {name:'local_mutual',args:[68,head],values:[68,44],heap:104},
   {name:'tail_local_apply_loop',args:[68,head],values:[68,292],heap:40},
   {name:'tail_zero',args:[head],values:[],heap:0},
   {name:'tail_many',args:[head],values:Array.from({length:26},()=>[28,NIL,T,2147483648,2147483644]).flat(),heap:0,capacity:132},
   {name:'tail_failure',args:[head,28],error:true,heap:0,oldCount:3},
  ]){
   activeFrame=0;topContext=0;installObjects();new Uint8Array(memory.buffer,heap,32768).fill(0xcd);set(48,heap);set(52,heapLimit);set(56,heap);
   const cap=scenario.capacity??4,reserve=out+4*cap,stackEnd=reserve+2048;
   store(root,0);store(root+4,scenario.args.length);scenario.args.forEach((v,i)=>store(start+4*i,v));
   const argsBefore=new Uint8Array(memory.buffer,start,4*scenario.args.length).slice();
   set(64,start);set(68,start);set(72,stackEnd);set(116,scenario.oldCount??0);set(120,out);set(124,reserve);set(128,root);
   new Uint8Array(memory.buffer,out,4*cap).fill(0xa5);if(scenario.oldCount)for(let i=0;i<scenario.oldCount;i++)store(out+4*i,4*(i+1));const outputBefore=new Uint8Array(memory.buffer,out,4*cap).slice();new Uint8Array(memory.buffer,stackEnd,64).fill(0xa7);
   stressState={context:reserve,transfers:0,maxRootDepth:0,maxArguments:0};let result=[],status='RETURN';
   try{const pair=functions.get(scenario.name)(handles.get(scenario.name),scenario.args.length).map(u32);assert.equal(pair[1],get(116));result=Array.from({length:pair[1]},(_,i)=>load(out+4*i));assert.equal(pair[0],result.length?result[0]:NIL);}
   catch(e){assert(e instanceof WebAssembly.Exception&&e.is(type_error),scenario.name+': no engine-stack trap');status='TYPE';}
   assert.equal(status,scenario.error?'TYPE':'RETURN');assert.deepEqual(result,scenario.values??[]);assert.equal(get(48),heap+scenario.heap,scenario.name+': bounded heap');
   assert.deepEqual(new Uint8Array(memory.buffer,start,4*scenario.args.length),argsBefore,scenario.name+': caller arguments preserved');
   assert(new Uint8Array(memory.buffer,stackEnd,64).every(x=>x===0xa7),scenario.name+': stack fence');if(scenario.error)assert.deepEqual(new Uint8Array(memory.buffer,out,4*cap),outputBefore,'exception preserves old values');else assert(new Uint8Array(memory.buffer,out+result.length*4,(cap-result.length)*4).every(x=>x===0xa5),scenario.name+': result tail');
   assert.deepEqual([get(64),get(120),get(124),get(128),get(116)],[start,out,reserve,root,scenario.error?(scenario.oldCount??0):result.length],scenario.name+': continuation restored');
   if(observed)assert(stressState.transfers>=steps,scenario.name+': actual tail entries');
   tailRuns.push({name:scenario.name,observed,start,steps,status,values:result,heap_bytes:scenario.heap,stack_bytes:2048,restored_count:get(116),...stressState});stressState=null;
  }
  // Finite argument growth must fail as a checked resource condition before
  // touching the stack fence. Producer effects already performed are retained.
  for(const bytes of [1024,2048,8192]){
   activeFrame=0;topContext=0;installObjects();set(48,heap);set(52,heapLimit);set(56,heap);store(16384,NIL);store(16388,0);
   store(root,0);store(root+4,1);store(start,16385);const reserve=out+528,stackEnd=reserve+bytes;
   set(64,start);set(68,start);set(72,stackEnd);set(116,0);set(120,out);set(124,reserve);set(128,root);
   new Uint8Array(memory.buffer,out,528).fill(0xa5);new Uint8Array(memory.buffer,stackEnd,64).fill(0xa7);
   let code=0,pair;try{pair=functions.get('mvc_resource')(handles.get('mvc_resource'),1).map(u32);}catch(e){assert(e instanceof WebAssembly.Exception&&e.is(call_error),'MVC checked capacity');code=e.getArg(call_error,0);}
   assert.equal(code,bytes===8192?0:2,'MVC finite stack capacity '+bytes);
   assert(new Uint8Array(memory.buffer,stackEnd,64).every(x=>x===0xa7),'MVC capacity fence '+bytes);
   assert.deepEqual([get(64),get(120),get(124),get(128)],[start,out,reserve,root],'MVC restores partial arguments');
   if(code){assert.equal(get(116),0);assert.equal(get(48),heap,'MVC capacity before rest allocation');assert(new Uint8Array(memory.buffer,out,528).every(x=>x===0xa5),'MVC failure unpublished');}
   else {assert.equal(pair[1],1);assert.equal(get(48),heap+520*8);assert.equal(load(16388),16);}
   multipleValueResources++;
  }
  // A multiple-value retention with a pending effect is not in tail position.
  {activeFrame=0;topContext=0;store(16384,NIL);store(16388,4);store(root,0);store(root+4,2);store(start,head);store(start+4,16385);set(64,start);set(68,start);set(72,out+16+2048);set(116,0);set(120,out);set(124,out+16);set(128,root);
   let code=0;try{functions.get('non_tail_effect')(handles.get('non_tail_effect'),2);}catch(e){assert(e instanceof WebAssembly.Exception&&e.is(call_error),'non-tail checked stack limit');code=e.getArg(call_error,0);}assert.equal(code,2,'pending effect retains frame');assert.equal(load(16388),4,'unreturned pending effects do not run');assert.deepEqual([get(64),get(120),get(124),get(128),get(116)],[start,out,out+16,root,0]);nonTailChecks++;
  }

 }
}
assert.equal(publicDispatches,0,'no compiled call uses a public wrapper');
parentPort.postMessage({status:'PASS',multiple_value_resources:multipleValueResources,lexical_exit_checks:lexicalExitChecks,progv_checks:progvChecks,binding_inspections:bindingInspections,binding_checks:bindingChecks,peak_bindings:peakBindings,control_inspections:controlInspections,state_checks:stateChecks,chain_checks:chainChecks,cleanup_entries:cleanupEntries,cleanup_resources:cleanupResources,public_dispatches:publicDispatches,internal_entries:internalEntries,tail_runs:tailRuns,non_tail_checks:nonTailChecks,tail_checks:tailChecks,modules:mods.length,comparisons:observations.length,ownership_inspections:checks,peak_root_frames:peakRoots,cases:observations,resource_refusals:60,callable_checks:callableChecks,closure_checks:closureChecks,local_checks:localChecks,result_capacity_checks:resultChecks,allocation_boundary_checks:8});
}
