import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import {Worker,isMainThread,workerData,parentPort} from 'node:worker_threads';
const u32=n=>n<0?n+4294967296:n,NIL=77825,T=77838;
if(isMainThread){const w=new Worker(new URL(import.meta.url),{workerData:process.argv[2]});w.on('message',x=>fs.writeFileSync(process.argv[3],JSON.stringify(x,null,2)+'\n'));w.on('error',e=>{console.error(e);process.exitCode=1;});w.on('exit',c=>{if(c)process.exitCode=c;});}
else{
const dir=workerData,read=n=>JSON.parse(fs.readFileSync(path.join(dir,n))),mods=read('modules.json'),cases=read('cases.json');
const memory=new WebAssembly.Memory({initial:2,maximum:32769,shared:true});memory.grow(32767);const dv=new DataView(memory.buffer);
const tcr=256,table=new WebAssembly.Table({element:'anyfunc',initial:mods.length+1,maximum:mods.length+1});
const call_error=new WebAssembly.Tag({parameters:['i32']}),type_error=new WebAssembly.Tag({parameters:['i32','i32']}),conversion_error=new WebAssembly.Tag({parameters:['i32']});
const handles=new Map(mods.map((m,i)=>[m.name,131078+16*i])),byHandle=new Map([...handles].map(([n,h])=>[h,n]));
const load=p=>dv.getUint32(p,true),store=(p,x)=>dv.setUint32(p,x,true),get=o=>load(tcr+o),set=(o,x)=>store(tcr+o,x);
const compiled=new Map(mods.map(m=>[m.name,new WebAssembly.Module(fs.readFileSync(path.join(dir,'installed',m.name+'.wasm')))]));
const slotModule=new WebAssembly.Module(fs.readFileSync(path.join(dir,'installed','resolve_slot.wasm')));
const slotCheck=new WebAssembly.Instance(slotModule,{env:{memory,slots:table,conversion_error}}).exports.entry;
let checks=0,peakRoots=0;
function inspect(label){let head=get(128),slots=new Set(),seen=new Set(),frames=0;while(head){assert(!seen.has(head),label+': acyclic roots');seen.add(head);let n=load(head+4);assert(n<=256,label+': root capacity');for(let i=0;i<n;i++){let p=head+8+4*i;assert(!slots.has(p),label+': unique root scanner');slots.add(p);}head=load(head);frames++;}for(let i=0;i<get(116);i++)assert(!slots.has(get(120)+4*i),label+': result single scanner');peakRoots=Math.max(peakRoots,frames);checks++;}
const observations=[];
for(const observed of [false,true]){
 const functions=new Map();
 const resolve=node=>{inspect('resolve');const name=byHandle.get(u32(node));if(!name)throw new WebAssembly.Exception(call_error,[4]);const slot=mods.findIndex(m=>m.name===name)+1;try{return slotCheck(slot,3,17,23,512);}catch(e){if(e instanceof WebAssembly.Exception&&e.is(conversion_error))throw new WebAssembly.Exception(call_error,[4]);throw e;}};
 for(const m of mods){const fnImports={},selfImports={};for(const [name,fn]of functions){selfImports[name]=handles.get(name);fnImports[name]=observed?((self,n)=>{assert.equal(u32(self),handles.get(name),'direct self identity');inspect('direct '+name);const before=[get(64),get(120),get(124),get(128)];const result=fn(self,n);assert.deepEqual([get(64),get(120),get(124),get(128)],before,'callee ownership '+name);inspect('after '+name);return result;}):fn;}
  const instance=new WebAssembly.Instance(compiled.get(m.name),{env:{memory,tcr,table,resolve,call_error,type_error},functions:fnImports,handles:selfImports});functions.set(m.name,instance.exports.entry);table.set(functions.size,instance.exports.entry);}
 for(const start of [2048,2147483648]){
  const root=start-8,out=start+2048,owner=out+256,limit=start+32768;
  const encode=x=>typeof x==='number'?(x*4+4294967296)%4294967296:x==='nil'?NIL:x==='t'?T:x.startsWith('n')?16385+8*Number(x.slice(1)):handles.get(x.slice(2));
  const decode=x=>{x=u32(x);if(x===NIL)return'nil';if(x===T)return't';if(x>=16385&&x<16449&&(x-16385)%8===0)return'n'+(x-16385)/8;if(x%4===0)return (x>=2147483648?x-4294967296:x)/4;throw Error('Unrepresented result '+x);};
  for(const c of cases){new Uint8Array(memory.buffer,0,18000).fill(0);if(start>18000)new Uint8Array(memory.buffer,root,32776).fill(0);
   store(512,mods.length+1);store(516,1);for(let i=1;i<=mods.length;i++){store(520+8*i,17);store(524+8*i,23);}
   for(let i=0;i<c.nodes.length;i++){store(16384+8*i,encode(c.nodes[i][1]));store(16388+8*i,encode(c.nodes[i][0]));}
   store(root,0);store(root+4,c.args.length);c.args.forEach((v,i)=>store(start+4*i,encode(v)));
   new Uint8Array(memory.buffer,out,256).fill(0xa5);set(64,start);set(68,start);set(72,limit);set(116,0);set(120,out);set(124,owner);set(128,root);
   const savedArgs=new Uint8Array(memory.buffer,start,4*c.args.length).slice();let result=[],status='RETURN',count=0,primary=NIL;
   try{const pair=functions.get(c.function)(handles.get(c.function),c.args.length);[primary,count]=pair.map(u32);assert(count<=64,c.id+': count bound');assert.equal(get(116),count,c.id+': count ownership');result=Array.from({length:count},(_,i)=>decode(load(out+4*i)));assert.equal(decode(primary),count?result[0]:'nil',c.id+': primary');}
   catch(e){assert(e instanceof WebAssembly.Exception,c.id+': checked failure, not engine trap: '+e);if(e.is(type_error))status='TYPE';else{assert(e.is(call_error));const code=e.getArg(call_error,0);assert([1,4].includes(code),c.id+': unexpected call refusal '+code);status=code===1?'ARITY':'DESIGNATOR';}assert.equal(get(116),0,c.id+': exceptional count');}
   const nodes=Array.from({length:c.nodes.length},(_,i)=>[decode(load(16388+8*i)),decode(load(16384+8*i))]);assert.deepEqual({status,values:result,nodes},c.expected,c.id+': native/logical result');
   assert.deepEqual([get(64),get(120),get(124),get(128)],[start,out,owner,root],c.id+': restored ownership');assert.deepEqual(new Uint8Array(memory.buffer,start,4*c.args.length),savedArgs,c.id+': caller arguments unchanged');assert(new Uint8Array(memory.buffer,out+4*count,256-4*count).every(x=>x===0xa5),c.id+': unpublished result tail');inspect('returned '+c.id);observations.push({id:c.id,observed,start,status,values:result,nodes});
  }
  // Resource refusals are target-specific, separate from native Lisp cases.
  for(const capacity of ['stack','results','alignment']){
   store(root,0);store(root+4,6);for(let i=0;i<6;i++)store(start+4*i,(i+1)*4);set(64,start);set(68,start);set(72,capacity==='stack'?owner+16:limit);set(116,0);set(120,out);set(124,capacity==='results'?out+16:owner);set(128,root);if(capacity==='alignment')set(64,start+1);
   const snapshot=[get(64),get(120),get(124),get(128),get(116)];let code=0;try{functions.get('v6')(handles.get('v6'),6);}catch(e){assert(e instanceof WebAssembly.Exception&&e.is(call_error));code=e.getArg(call_error,0);}assert.equal(code,capacity==='results'?3:2,'checked '+capacity);assert.deepEqual([get(64),get(120),get(124),get(128),get(116)],snapshot,'resource failure restores '+capacity);
  }
 }
}
parentPort.postMessage({status:'PASS',modules:mods.length,comparisons:observations.length,ownership_inspections:checks,peak_root_frames:peakRoots,cases:observations,resource_refusals:12});
}
