import fs from 'node:fs';
import assert from 'node:assert/strict';
export async function install({dir,memory,tcr,get,put,service,config,result}){
 const NIL=77825,registry=4096,table=new WebAssembly.Table({element:'anyfunc',initial:64}),tail_table=new WebAssembly.Table({element:'anyfunc',initial:64});
 const call_error=new WebAssembly.Tag({parameters:['i32']}),type_error=new WebAssembly.Tag({parameters:['i32','i32']}),nonlocal_exit=new WebAssembly.Tag({parameters:['i32']});
 const read=n=>JSON.parse(fs.readFileSync(dir+'/compiled/'+n)),material=read('materialized.json'),modules=read('modules.json');
 new Uint8Array(memory.buffer,2097152,material.image.length/2).set(Buffer.from(material.image,'hex'));
 let cursor=2097152+material.image.length/2;
 const object=(id,pool)=>{const p=cursor;cursor+=32;[1578,id*4,NIL,4,NIL,NIL,pool,0].forEach((x,i)=>put(p+4*i,x));return p+6;};
 const env={memory,tcr,table,tail_table,code_registry:registry,call_error,type_error,nonlocal_exit};put(registry,64);put(registry+4,1);
 function register(id,x){[id,4,17,23].forEach((v,i)=>put(registry+8+16*id+4*i,v));table.set(id,x.exports.entry);tail_table.set(id,x.exports.tail_entry);}
 const adapter=await WebAssembly.compile(fs.readFileSync(dir+'/adapter.wasm')),operations=[],adapters=[];
 for(let op=0;op<5;op++){const id=op+1,x=new WebAssembly.Instance(adapter,{env,symbols_runtime:{run:service.symbols_run,config,operation:op,result}});register(id,x);operations.push(object(id,NIL));adapters.push(x);}
 const entries={},symbols={};let symNext=600000;
 for(let i=0;i<modules.length;i++){
  const m=modules[i],wasm=await WebAssembly.compile(fs.readFileSync(dir+'/compiled/'+m.name+'.wasm'));
  for(const item of WebAssembly.Module.imports(wasm))if(item.module==='symbols'&&!(item.name in symbols)){const p=symNext;symNext+=32;put(p,1850);for(let w=1;w<8;w++)put(p+4*w,NIL);put(p+28,0);symbols[item.name]=p+6;}
  const id=i+8,x=new WebAssembly.Instance(wasm,{env,symbols});register(id,x);entries[m.name]={fn:x.exports.entry,self:object(id,material.roots[i])};
 }
 fs.mkdirSync(dir+'/installed',{recursive:true});for(const m of modules)fs.copyFileSync(dir+'/compiled/'+m.name+'.wasm',dir+'/installed/'+m.name+'.wasm');
 let calls=0;const variants={};
 function call(name,args){
  const e=entries[name],incoming=132096,output=132352;put(tcr+64,incoming);put(tcr+116,0);put(tcr+120,output);put(tcr+124,132384);args.forEach((v,i)=>put(incoming+4*i,v));
  const before=[64,128,140,92].map(o=>get(tcr+o));let pair;
  try{pair=e.fn(e.self,args.length);}catch(error){if(error.is?.(call_error))throw Error('checked '+error.getArg(call_error,0)+' '+name);throw error;}
  assert.deepEqual([64,128,140,92].map(o=>get(tcr+o)),before,'caller state restored');assert.equal(pair[0]>>>0,get(output));assert.equal(pair[1],get(tcr+116));
  const values=Array.from({length:pair[1]},(_,i)=>get(output+4*i));put(tcr+116,0);variants[name]=(variants[name]||0)+1;return values;
 }
 return {call,invoke(op,a,b=NIL,c=NIL){const forms=['symbol_call','symbol_values','symbol_preserve','symbol_apply','symbol_dynamic','symbol_indirect'],name=forms[calls++%6],args=name==='symbol_dynamic'||name==='symbol_indirect'?[operations[op],entries.symbol_receiver.self,a,b,c]:[operations[op],a,b,c],v=call(name,args);const n=['symbol_values','symbol_dynamic','symbol_indirect'].includes(name)?2:op<2?2:1;assert.equal(v.length,n,'generated result count');return [v[0],v[1]??NIL];},counts(){const delivery=adapters.map(a=>Object.fromEntries(['fixed_calls','dynamic_calls','direct_calls'].map(n=>[n,a.exports[n].value])));for(const key of ['fixed_calls','dynamic_calls','direct_calls'])assert(delivery.some(d=>d[key]>0),key);assert(delivery.some(d=>d.dynamic_calls>d.direct_calls));return {calls,variants,delivery,modules:modules.length};}};
}
