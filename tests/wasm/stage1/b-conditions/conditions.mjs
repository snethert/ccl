import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import {Worker,isMainThread,workerData,parentPort} from 'node:worker_threads';
const u32=n=>n<0?n+4294967296:n,NIL=77825,T=77838;
if(isMainThread){const w=new Worker(new URL(import.meta.url),{workerData:process.argv[2]});w.on('message',x=>fs.writeFileSync(process.argv[3]+(x.progress?'.progress.json':''),JSON.stringify(x,null,2)+'\n'));w.on('error',e=>{console.error(e);process.exitCode=1;});w.on('exit',c=>{if(c)process.exitCode=c;});}
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

assert(4104+16*(mods.length+1)<=16384,'code registry exceeds fixture-owned range');
assert(196608+32*mods.length<=262144,'function symbols exceed fixture-owned range');
const compiled=new Map(mods.map(m=>[m.name,new WebAssembly.Module(fs.readFileSync(path.join(dir,'installed',m.name+'.wasm')))]));
let multipleValueResources=0;let lexicalExitChecks=0;let progvChecks=0;let bindingInspections=0,bindingChecks=0,peakBindings=0;let controlInspections=0,stateChecks=0,chainChecks=0,chainFault=null;let cleanupEntries=0,cleanupResources=0;let publicDispatches=0,internalEntries=0;let checks=0,peakRoots=0,activeFrame=0,activeRoots=0,topContext=0;
function inspect(label){let head=get(128),slots=new Set(),seen=new Set(),frames=0;while(head){assert(!seen.has(head),label+': acyclic roots');seen.add(head);let n=load(head+4),pointer=head+8;if(n===0xffffffff){pointer=load(head+8);n=load(head+12);const inline=pointer===head+32&&n<=4&&head>=get(68)&&head+48<=get(72);assert(inline||pointer===0&&n===0||pointer>=get(80)+16&&pointer+4*n<=get(76),label+': dynamic result extent');if(n&&!inline){assert(load(pointer-12)!==0,label+': live result owner');assert.equal(load(pointer-4),1381384241,label+': result buffer marker');assert(n<=load(pointer-8),label+': owned result extent');}}if(head===activeFrame)assert.equal(n,activeRoots,label+': bound variables are roots');assert(n<=(memory.buffer.byteLength-pointer)/4,label+': root capacity');for(let i=0;i<n;i++){let p=pointer+4*i;assert(!slots.has(p),label+': unique root scanner');assert(!(p>=get(120)&&p<get(124)),label+': output reservation is not a root record');slots.add(p);}head=load(head);frames++;}for(let i=0;i<get(116);i++)assert(!slots.has(get(120)+4*i),label+': result single scanner');let prior=get(72);for(let c=get(140);c;c=load(c)){
 assert(c%16===0&&c>=get(68)&&c+48<=prior,label+': bounded control chain');
 const capacity=load(c+8);assert(c+48+4*capacity<=get(72),label+': control extent');
 assert.equal(load(c+24),1128483889,label+': control version');assert([1,2,3].includes(load(c+4)),label+': control kind');
 assert.equal(load(c+16),c+32,label+': control root location');assert(seen.has(c+32),label+': control record rooted');
 assert.equal(load(c+36),capacity+2,label+': control root count');assert(load(c+12)<=(load(c+28)?load(load(c+28)+12):capacity),label+': transfer count bound');
 assert([0,1,2].includes(load(c+20)),label+': saved unwind state');prior=c;controlInspections++;
 }let previous=get(72),depth=0;for(let b=get(112);b;b=load(b)){
 assert(b%16===0&&b>=get(68)&&b+32<=previous,label+': bounded binding chain');
 assert.equal(load(b+24),1112425521,label+': binding version');assert(seen.has(b+8),label+': saved binding rooted');assert.equal(load(b+12),2,label+': two saved binding roots');
 const symbol=load(b+16),index=load(b+4);assert.equal(load(symbol-6),1850,label+': binding symbol');assert.equal(load(symbol+22),index,label+': symbol binding index');assert(index>0&&index%4===0&&index/4<get(108),label+': binding index capacity');assert(get(104)+4*get(108)<=memory.buffer.byteLength,label+': binding vector extent');assert(!slots.has(get(104)+index),label+': TLB has its own scanner');
 previous=b;depth++;bindingInspections++;
 }peakBindings=Math.max(peakBindings,depth);assert([0,1,2].includes(get(148)),label+': unwind state');peakRoots=Math.max(peakRoots,frames);checks++;}
let stressState=null;const tailRuns=[];let nonTailChecks=0,tailChecks=0;
const conditionRefusals=[];let storageChecks=0;const observations=[];let resultChecks=0,callableChecks=0,closureChecks=0,localChecks=0;
for(const observed of [false,true]){
 const functions=new Map();
 const symbols=Object.fromEntries(mods.flatMap((m,i)=>m.source?[[m.name,196614+32*i]]:[]));
 const specialNames=['dyn_a','dyn_b','dyn_u','condition_handlers'];specialNames.forEach((name,i)=>symbols[name]=600006+32*i);
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
  set(80,700000);set(76,700000);set(84,900000);
  set(104,610000);set(108,5);set(112,0);set(0,37);
  for(let i=0;i<5;i++)store(610000+4*i,243);
  specialNames.forEach((name,i)=>{const base=symbols[name]-6;store(base,1850);for(let j=1;j<8;j++)store(base+4*j,NIL);store(base+8,i===3?NIL:i===2?51:4*(101+2*i));store(base+20,0);store(base+28,4*(i+1));});
  [1,9,31,39,71,393].forEach((mask,i)=>{const p=620000+16*i;store(p,762);store(p+4,mask*4);store(p+8,i*4);store(p+12,NIL);});
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
  const encode=x=>typeof x==='number'?(x*4+4294967296)%4294967296:x==='nil'?NIL:x==='t'?T:x.startsWith(':')?keywords[x.slice(1)]:x.startsWith('q')?620006+16*Number(x.slice(1)):x.startsWith('n')?16385+8*Number(x.slice(1)):x.startsWith('s:')?symbols[x.slice(2)]:handles.get(x.slice(2));
  let objects=[],objectNames=new Map(),closureNames=new Map();
  const decode=x=>{x=u32(x);if(x===NIL)return'nil';if(x===T)return't';for(const [k,v]of Object.entries(keywords))if(x===v)return ':'+k;
   if(x>=620006&&x<620102&&(x-620006)%16===0)return 'q'+((x-620006)/16);
   if(byHandle.has(x))return 'f:'+byHandle.get(x);
   for(const [name,p]of Object.entries(symbols))if(p===x)return 's:'+name;
   if(x%8===6&&x>=heap+6&&x+18<=get(48)&&load(x-6)===1322){if(!closureNames.has(x))closureNames.set(x,'c'+closureNames.size);return closureNames.get(x);}
   if(objectNames.has(x))return 'n'+objectNames.get(x);
   if(x>=heap+1&&x+7<=get(48)&&(x-heap-1)%8===0){objectNames.set(x,objects.length);objects.push(x);return 'n'+(objects.length-1);}
   if(x%4===0)return (x>=2147483648?x-4294967296:x)/4;throw Error('Unrepresented result '+x);};
  for(const c of cases){parentPort.postMessage({progress:c.id,observed,start});closureNames=new Map();const capacity=c.capacity,owner=out+4*capacity;topContext=owner;activeFrame=owner+48+16*Math.ceil(c.args.length/4);activeRoots=Math.max(4,capacity)+rootContracts[c.function].bound_words;new Uint8Array(memory.buffer,0,32768).fill(0);new Uint8Array(memory.buffer,root,32776).fill(0);new Uint8Array(memory.buffer,heap,32768).fill(0xcd);set(48,heap);set(52,heapLimit);set(56,heap);objects=c.nodes.map((_,i)=>16385+8*i);objectNames=new Map(objects.map((p,i)=>[p,i]));
   installObjects();for(const [name,target]of Object.entries(c.bindings))store(symbols[name]+6,handles.get(target));
   for(let i=0;i<c.nodes.length;i++){store(16384+8*i,encode(c.nodes[i][1]));store(16388+8*i,encode(c.nodes[i][0]));}
   store(root,0);store(root+4,c.args.length);c.args.forEach((v,i)=>store(start+4*i,encode(v)));
   new Uint8Array(memory.buffer,out,4*capacity).fill(0xa5);set(64,start);set(68,start);set(72,limit);set(116,0);set(120,out);set(124,owner);set(128,root);
   const savedArgs=new Uint8Array(memory.buffer,start,4*c.args.length).slice();let result=[],status='RETURN',count=0,primary=NIL;
   try{const pair=functions.get(c.function)(handles.get(c.function),c.args.length);[primary,count]=pair.map(u32);assert(count<=capacity,c.id+': count bound');assert.equal(get(116),count,c.id+': count ownership');result=Array.from({length:count},(_,i)=>decode(load(out+4*i)));assert.equal(decode(primary),count?result[0]:'nil',c.id+': primary');}
   catch(e){assert(e instanceof WebAssembly.Exception,c.id+': checked failure, not engine trap: '+e);if(e.is(type_error))status='TYPE';else{assert(e.is(call_error));const code=e.getArg(call_error,0);assert([1,4,5,8,10,12,15].includes(code),c.id+': unexpected call refusal '+code);status=code===15?'UNHANDLED':code===1?'ARITY':code===5?'TYPE':code===8?'CONTROL':code===10?'UNBOUND':code===12?'BINDING':'DESIGNATOR';}assert.equal(get(116),0,c.id+': exceptional count');}
   const nodes=[];for(let i=0;i<objects.length;i++)nodes.push([decode(load(objects[i]+3)),decode(load(objects[i]-1))]);assert(get(48)>=heap&&get(48)<=heapLimit,c.id+': allocation within owner extent');assert(new Uint8Array(memory.buffer,get(48),heapLimit-get(48)).every(x=>x===0xcd),c.id+': heap tail untouched');const specials=specialNames.slice(0,3).map(name=>load(symbols[name]+2)===51?'unbound':decode(load(symbols[name]+2)));assert.deepEqual({status,values:result,nodes,specials},c.expected,c.id+': native/logical result');assert.equal(get(112),0,c.id+': binding chain restored');assert.deepEqual(Array.from({length:5},(_,i)=>load(610000+4*i)),[243,243,243,243,243],c.id+': binding vector restored');
   assert.deepEqual([get(64),get(120),get(124),get(128)],[start,out,owner,root],c.id+': restored ownership');assert.deepEqual(new Uint8Array(memory.buffer,start,4*c.args.length),savedArgs,c.id+': caller arguments unchanged');assert(new Uint8Array(memory.buffer,out+4*count,4*capacity-4*count).every(x=>x===0xa5),c.id+': unpublished result tail');assert.deepEqual([get(140),get(148)],[0,0],c.id+': control chain retired');assert.equal(get(76),get(80),c.id+': temporary results released');inspect('returned '+c.id);observations.push({id:c.id,observed,start,status,values:result,nodes,specials});
  }
  for(const fault of ['fixnum','nil','header','mask-tag','mask-zero','mask-unknown','outside']){
   installObjects();set(48,heap);set(52,heapLimit);set(56,heap);
   set(64,start);set(68,start);set(72,limit);set(116,0);set(120,out);set(124,out+64);set(128,root);store(root,0);store(root+4,1);
   let value=620006;
   if(fault==='fixnum')value=28;if(fault==='nil')value=NIL;if(fault==='outside')value=4294967286;
   if(fault==='header')store(620000,1018);if(fault==='mask-tag')store(620004,5);if(fault==='mask-zero')store(620004,0);if(fault==='mask-unknown')store(620004,2044);
   store(start,value);const before=new Uint8Array(memory.buffer,620000,96).slice();
   assert.throws(()=>functions.get('h_signal')(handles.get('h_signal'),1),e=>e instanceof WebAssembly.Exception&&e.is(call_error)&&[4,5].includes(e.getArg(call_error,0)),fault+': checked condition refusal');
   assert.equal(get(48),heap,fault+': no heap write');assert.equal(get(76),get(80),fault+': no arena write');assert.deepEqual([get(112),get(140),get(148)],[0,0,0],fault+': chains restored');
   assert.deepEqual([get(64),get(120),get(124),get(128)],[start,out,out+64,root],fault+': ownership restored');assert.deepEqual(new Uint8Array(memory.buffer,620000,96),before,fault+': condition untouched');
   conditionRefusals.push({fault,observed,start});
  }
 }
}
parentPort.postMessage({status:'PASS',condition_refusals:conditionRefusals,modules:mods.length,comparisons:observations.length,conditions:observations,ownership_inspections:checks,control_inspections:controlInspections,binding_inspections:bindingInspections,public_dispatches:publicDispatches});
}
