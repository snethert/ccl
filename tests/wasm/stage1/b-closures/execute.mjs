import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import {Worker,isMainThread,workerData,parentPort} from 'node:worker_threads';
const u32=n=>n<0?n+4294967296:n,NIL=77825,T=77838;
if(isMainThread){const w=new Worker(new URL(import.meta.url),{workerData:process.argv[2]});w.on('message',x=>fs.writeFileSync(process.argv[3],JSON.stringify(x,null,2)+'\n'));w.on('error',e=>{console.error(e);process.exitCode=1;});w.on('exit',c=>{if(c)process.exitCode=c;});}
else{
const dir=workerData,read=n=>JSON.parse(fs.readFileSync(path.join(dir,n))),mods=read('modules.json'),cases=read('cases.json');
const memory=new WebAssembly.Memory({initial:2,maximum:32769,shared:true});memory.grow(32767);const dv=new DataView(memory.buffer);
const tcr=256,table=new WebAssembly.Table({element:'anyfunc',initial:mods.length+1,maximum:mods.length+1});
const call_error=new WebAssembly.Tag({parameters:['i32']}),type_error=new WebAssembly.Tag({parameters:['i32','i32']}),conversion_error=new WebAssembly.Tag({parameters:['i32']});
const handles=new Map(mods.map((m,i)=>[m.name,131078+32*i])),byHandle=new Map([...handles].map(([n,h])=>[h,n]));
const load=p=>dv.getUint32(p,true),store=(p,x)=>dv.setUint32(p,x,true),get=o=>load(tcr+o),set=(o,x)=>store(tcr+o,x);
const keywords=Object.fromEntries(['a','b','x','external','bad','allow-other-keys'].map((k,i)=>[k,262150+i*16]));
const compiled=new Map(mods.map(m=>[m.name,new WebAssembly.Module(fs.readFileSync(path.join(dir,'installed',m.name+'.wasm')))]));
let checks=0,peakRoots=0,activeFrame=0,activeRoots=0;
function inspect(label){let head=get(128),slots=new Set(),seen=new Set(),frames=0;while(head){assert(!seen.has(head),label+': acyclic roots');seen.add(head);let n=load(head+4);if(head===activeFrame)assert.equal(n,activeRoots,label+': bound variables are roots');assert(n<=(get(72)-head-8)/4,label+': root capacity');for(let i=0;i<n;i++){let p=head+8+4*i;assert(!slots.has(p),label+': unique root scanner');assert(!(p>=get(120)&&p<get(124)),label+': output reservation is not a root record');slots.add(p);}head=load(head);frames++;}for(let i=0;i<get(116);i++)assert(!slots.has(get(120)+4*i),label+': result single scanner');peakRoots=Math.max(peakRoots,frames);checks++;}
const observations=[];let resultChecks=0,callableChecks=0,closureChecks=0;
for(const observed of [false,true]){
 const functions=new Map();
 const symbols=Object.fromEntries(mods.map((m,i)=>[m.name,196614+32*i]));
 const observer=new WebAssembly.Module(fs.readFileSync(path.join(dir,'installed','observe_entry.wasm')));
 for(const m of mods){
  const codes=Object.fromEntries(mods.map((m,i)=>[m.name,4*(i+1)]));
  const instance=new WebAssembly.Instance(compiled.get(m.name),{env:{memory,tcr,table,code_registry:4096,call_error,type_error},symbols,keywords,codes});
  const entry=instance.exports.entry;functions.set(m.name,entry);
  const wrapper=observed?new WebAssembly.Instance(observer,{env:{entry,observe:self=>{inspect('dispatch '+m.name);assert.equal(load(u32(self)-2),4*(mods.findIndex(x=>x.name===m.name)+1),'resolved self code');if(m.captures){let found=false;for(let h=get(128);h;h=load(h))for(let i=0;i<load(h+4);i++)if(load(h+8+4*i)===u32(self))found=true;assert(found,'closure SELF has a physical root');}}}}).exports.entry:entry;
  table.set(functions.size,wrapper);
 }
 function installObjects(){
  store(4096,mods.length+1);store(4100,1);
  for(let i=0;i<mods.length;i++){
   const base=handles.get(mods[i].name)-6,symbol=symbols[mods[i].name]-6,row=4104+16*(i+1);
   store(base,1322);store(base+4,4*(i+1));store(base+8,NIL);store(base+12,4);store(base+16,NIL);store(base+20,NIL);
   store(symbol,1850);for(let j=1;j<8;j++)store(symbol+4*j,NIL);store(symbol+12,base+6);
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
  for(const c of cases){closureNames=new Map();const capacity=c.capacity,owner=out+4*capacity;activeFrame=owner;activeRoots=Math.max(4,capacity)+mods.find(m=>m.name===c.function).bound_words;new Uint8Array(memory.buffer,0,32768).fill(0);new Uint8Array(memory.buffer,root,32776).fill(0);new Uint8Array(memory.buffer,heap,32768).fill(0xcd);set(48,heap);set(52,heapLimit);set(56,heap);objects=c.nodes.map((_,i)=>16385+8*i);objectNames=new Map(objects.map((p,i)=>[p,i]));
   installObjects();for(const [name,target]of Object.entries(c.bindings))store(symbols[name]+6,handles.get(target));store(512,mods.length+1);store(516,1);for(let i=1;i<=mods.length;i++){store(520+8*i,17);store(524+8*i,23);}
   for(let i=0;i<c.nodes.length;i++){store(16384+8*i,encode(c.nodes[i][1]));store(16388+8*i,encode(c.nodes[i][0]));}
   store(root,0);store(root+4,c.args.length);c.args.forEach((v,i)=>store(start+4*i,encode(v)));
   new Uint8Array(memory.buffer,out,4*capacity).fill(0xa5);set(64,start);set(68,start);set(72,limit);set(116,0);set(120,out);set(124,owner);set(128,root);
   const savedArgs=new Uint8Array(memory.buffer,start,4*c.args.length).slice();let result=[],status='RETURN',count=0,primary=NIL;
   try{const pair=functions.get(c.function)(handles.get(c.function),c.args.length);[primary,count]=pair.map(u32);assert(count<=capacity,c.id+': count bound');assert.equal(get(116),count,c.id+': count ownership');result=Array.from({length:count},(_,i)=>decode(load(out+4*i)));assert.equal(decode(primary),count?result[0]:'nil',c.id+': primary');}
   catch(e){assert(e instanceof WebAssembly.Exception,c.id+': checked failure, not engine trap: '+e);if(e.is(type_error))status='TYPE';else{assert(e.is(call_error));const code=e.getArg(call_error,0);assert([1,4,5].includes(code),c.id+': unexpected call refusal '+code);status=code===1?'ARITY':code===5?'TYPE':'DESIGNATOR';}assert.equal(get(116),0,c.id+': exceptional count');}
   const nodes=[];for(let i=0;i<objects.length;i++)nodes.push([decode(load(objects[i]+3)),decode(load(objects[i]-1))]);assert.equal(get(48),heap+8*c.allocated_cells+c.closure_bytes,c.id+': allocation count');assert(new Uint8Array(memory.buffer,get(48),heapLimit-get(48)).every(x=>x===0xcd),c.id+': heap tail untouched');assert.deepEqual({status,values:result,nodes},c.expected,c.id+': native/logical result');
   assert.deepEqual([get(64),get(120),get(124),get(128)],[start,out,owner,root],c.id+': restored ownership');assert.deepEqual(new Uint8Array(memory.buffer,start,4*c.args.length),savedArgs,c.id+': caller arguments unchanged');assert(new Uint8Array(memory.buffer,out+4*count,4*capacity-4*count).every(x=>x===0xa5),c.id+': unpublished result tail');inspect('returned '+c.id);observations.push({id:c.id,observed,start,status,values:result,nodes});
  }
  // Host-turn escape: save the generated closure, overwrite the entire Lisp
  // stack, then call it on fresh invocations. No host closure resolver exists.
  function invoke(name,args,self=handles.get(name)){
   activeFrame=0;new Uint8Array(memory.buffer,root,32776).fill(0x9b);
   store(root,0);store(root+4,args.length);args.forEach((v,i)=>store(start+4*i,v));
   set(64,start);set(68,start);set(72,limit);set(116,0);set(120,out);set(124,owner);set(128,root);new Uint8Array(memory.buffer,out,256).fill(0xa5);
   try {const pair=functions.get(name)(self,args.length).map(u32);assert.equal(pair[1],get(116));return Array.from({length:pair[1]},(_,i)=>load(out+4*i));}
   finally {assert.deepEqual([get(64),get(120),get(124),get(128)],[start,out,owner,root],'closure host-turn ownership');inspect('closure host turn');}
  }
  installObjects();new Uint8Array(memory.buffer,heap,32768).fill(0xcd);set(48,heap);set(52,heapLimit);set(56,heap);
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
  // Recursion exhausts the explicit stack through a checked condition.
  {activeFrame=0;installObjects();for(let i=0;i<80;i++){store(16384+8*i,i===79?NIL:16393+8*i);store(16388+8*i,4*i);}store(root,0);store(root+4,1);store(start,16385);set(64,start);set(68,start);set(72,limit);set(116,0);set(120,out);set(124,owner);set(128,root);new Uint8Array(memory.buffer,out,256).fill(0xa5);
   let reason=0;try{functions.get('walk_list')(handles.get('walk_list'),1);}catch(e){assert(e instanceof WebAssembly.Exception&&e.is(call_error),'recursive stack checked');reason=e.getArg(call_error,0);}assert.equal(reason,2,'recursive stack capacity');assert.deepEqual([get(64),get(120),get(124),get(128),get(116)],[start,out,owner,root,0]);assert(new Uint8Array(memory.buffer,out,256).every(x=>x===0xa5));callableChecks++;
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
   activeFrame=0;new Uint8Array(memory.buffer,root,32776).fill(0xa5);
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
  // Exactly sufficient scratch plus staging space: 544 + 528 bytes.
  {activeFrame=0;store(root,0);store(root+4,1);store(start,28);set(64,start);set(68,start);set(72,out+528+1072);set(116,0);set(120,out);set(124,out+528);set(128,root);
   const [value,count]=functions.get('many')(handles.get('many'),1).map(u32);assert.equal(value,28);assert.equal(count,130);assert.equal(load(out+4*129),2147483644);assert.deepEqual([get(64),get(120),get(124),get(128)],[start,out,out+528,root]);resultChecks++;
  }
  // Empty rest lists require no allocation; exact capacity is sufficient.
  for(const n of [0,2]){set(48,heap);set(52,heap+8*n);set(56,heap);set(64,start);set(68,start);set(72,limit);set(116,0);set(120,out);set(124,owner);set(128,root);store(root+4,n);store(start,28);store(start+4,36);
   const [value,count]=functions.get('rest_all')(handles.get('rest_all'),n).map(u32);assert.equal(count,1,'rest exact capacity count');assert.equal(get(48),heap+8*n,'rest exact capacity pointer');if(!n)assert.equal(value,NIL,'empty rest');else{assert.equal(load(value+3),28);const tail=load(value-1);assert.equal(load(tail+3),36);assert.equal(load(tail-1),NIL);}
  }
 }
}
parentPort.postMessage({status:'PASS',modules:mods.length,comparisons:observations.length,ownership_inspections:checks,peak_root_frames:peakRoots,cases:observations,resource_refusals:60,callable_checks:callableChecks,closure_checks:closureChecks,result_capacity_checks:resultChecks,allocation_boundary_checks:8});
}
