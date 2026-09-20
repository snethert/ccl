import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
// Real compiler output calls owner-installed B runtime leaves. No post-compile
// rewriting. The adapter binds the same hash.wasm used by the independent core.
export async function install({dir,memory,tcr,get,put,service,scratch,scratchEnd,result,collector,config}){
 const NIL=77825,registry=4096,table=new WebAssembly.Table({element:'anyfunc',initial:32}),tail_table=new WebAssembly.Table({element:'anyfunc',initial:32});
 const call_error=new WebAssembly.Tag({parameters:['i32']}),type_error=new WebAssembly.Tag({parameters:['i32','i32']}),nonlocal_exit=new WebAssembly.Tag({parameters:['i32']});
 const read=n=>JSON.parse(fs.readFileSync(dir+'/compiled/'+n));const material=read('materialized.json'),modules=read('modules.json');
 new Uint8Array(memory.buffer,2097152,material.image.length/2).set(Buffer.from(material.image,'hex'));
 let cursor=2097152+material.image.length/2;
 const functionObject=(id,pool)=>{const p=cursor;cursor+=32;[1578,id*4,NIL,4,NIL,NIL,pool,0].forEach((x,i)=>put(p+i*4,x));return p+6;};
 const env={memory,tcr,table,tail_table,code_registry:registry,call_error,type_error,nonlocal_exit};
 put(registry,32);put(registry+4,1);
 function register(id,instance){put(registry+8+16*id,id);put(registry+12+16*id,4);put(registry+16+16*id,17);put(registry+20+16*id,23);table.set(id,instance.exports.entry);tail_table.set(id,instance.exports.tail_entry);}
 const adapter=await WebAssembly.compile(fs.readFileSync(dir+'/adapter.wasm')),operations=[],adapters=[];
 for(let op=0;op<5;op++){
  const id=1+op,instance=new WebAssembly.Instance(adapter,{env,hash:{run:service.ht_run,collect:collector.collect,config,operation:op,scratch,scratch_end:scratchEnd,result}});
  register(id,instance);adapters.push(instance);operations.push(functionObject(id,NIL));
 }
 const entries=[],installed=[];fs.mkdirSync(dir+'/installed',{recursive:true});let symNext=600000;const symbols={};
 for(let i=0;i<modules.length;i++){
  const bytes=fs.readFileSync(dir+'/compiled/'+modules[i].name+'.wasm'),wasm=await WebAssembly.compile(bytes);
  fs.writeFileSync(dir+'/installed/'+modules[i].name+'.wasm',bytes);installed.push({name:modules[i].name,sha256:createHash('sha256').update(bytes).digest('hex')});
  for(const item of WebAssembly.Module.imports(wasm))if(item.module==='symbols'&&!(item.name in symbols)){
   const p=symNext;symNext+=32;put(p,1850);for(let w=1;w<8;w++)put(p+4*w,NIL);put(p+28,0);symbols[item.name]=p+6;
  }
  const id=i+8,instance=new WebAssembly.Instance(wasm,{env,symbols});register(id,instance);entries.push({name:modules[i].name,fn:instance.exports.entry,self:functionObject(id,material.roots[i])});
 }
 let calls=0,moving=[],variants=Object.fromEntries(entries.map(e=>[e.name,0]));
 return {
  invoke(op,tableObject,key,value){
   const ordinary=entries.filter(e=>!e.name.startsWith('hash_gc')&&e.name!=='hash_receiver');
   const entry=ordinary[calls++%ordinary.length],args=entry.name.startsWith('hash_dynamic')?[operations[op],entries.find(e=>e.name==='hash_receiver').self,tableObject,key,value]:[operations[op],tableObject,key,value],incoming=132096,output=132352,owner=132384;
   put(tcr+64,incoming);put(tcr+116,0);put(tcr+120,output);put(tcr+124,owner);
   args.forEach((v,i)=>put(incoming+4*i,v));const root=get(tcr+128),handlers=get(tcr+140),beforeFlag=get(tableObject+2);
   let pair;try{pair=entry.fn(entry.self,args.length);}catch(e){throw Error(entry.name+': '+(e.is?.(call_error)?'checked '+e.getArg(call_error,0):String(e)));}
   assert.equal(get(tcr+64),incoming,'caller VSP restored');assert.equal(get(tcr+128),root,'caller root chain restored');assert.equal(get(tcr+140),handlers,'caller handlers restored');
   // MVB intentionally supplies NIL for absent second values.
   const n=['hash_values','hash_dynamic','hash_dynamic_indirect'].includes(entry.name)?2:op===0?2:1;
   assert.equal(pair[1]>>>0,n,'generated result count');assert.equal(get(tcr+116),n);assert.equal(pair[0]>>>0,get(output));variants[entry.name]++;
   const first=get(output),second=n===2?get(output+4):NIL;
   put(tcr+116,0); // owner drops returned values after consuming them
   return [first,second,op===0?2:1,(beforeFlag&2**29)?1:0];
  },moving(name,tableObject,key){
   const entry=entries.find(e=>e.name===name),args=name==='hash_gc'?[operations[0],operations[1],operations[4],tableObject,key]:[operations[0],operations[4],tableObject,key];
   const incoming=132096,output=132352,owner=132384;
   put(tcr+64,incoming);put(tcr+116,0);put(tcr+120,output);put(tcr+124,owner);args.forEach((v,i)=>put(incoming+4*i,v));
   const root=get(tcr+128),before=get(tcr+56);let pair;
   try{pair=entry.fn(entry.self,args.length);}catch(e){throw Error(name+': '+(e.is?.(call_error)?'checked '+e.getArg(call_error,0):String(e)));}
   assert.equal(get(tcr+128),root);assert.equal(get(tcr+64),incoming);
   const values=Array.from({length:pair[1]>>>0},(_,i)=>get(output+4*i));put(tcr+116,0);variants[name]++;moving.push({name,values,before,after:get(tcr+56)});return values;
  },counts(){const delivery=adapters.map(a=>Object.fromEntries(['fixed_calls','dynamic_calls','direct_calls'].map(n=>[n,a.exports[n].value])));assert(delivery.some(d=>d.dynamic_calls>0),'dynamic delivery reached');assert(delivery.some(d=>d.direct_calls>0),'direct producer reached');assert(delivery.some(d=>d.dynamic_calls>d.direct_calls),'indirect descriptor reached');assert(delivery.some(d=>d.fixed_calls>0),'fixed delivery reached');return {calls,variants,moving,delivery,modules:modules.length,compilerUnmodified:true,installed};}
 };
}
