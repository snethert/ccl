import {sha256} from './sha256.mjs';
// One trusted Worker grants a disjoint pinned slab, outside moving heaps/stacks.
// No collection or memory growth is performed here. Every reservation is fresh.
export function counterStorage({memory,base,end,bytes,digest}){
 const need=(ok,why)=>{if(!ok)throw Error(why);};
 need(memory instanceof WebAssembly.Memory,'COUNTER_MEMORY');
 need(Number.isSafeInteger(base)&&base>=0&&base%8===0&&Number.isSafeInteger(end)&&end>=base&&end<=memory.buffer.byteLength&&end<=0xffffffff,'COUNTER_REGION');
 const binary=Uint8Array.from(bytes);need(sha256(binary)===digest,'COUNTER_DIGEST');
 const module=new WebAssembly.Module(binary);
 need(JSON.stringify(WebAssembly.Module.imports(module))===JSON.stringify([{module:'env',name:'memory',kind:'memory'}]),'COUNTER_IMPORTS');
 need(JSON.stringify(WebAssembly.Module.exports(module))===JSON.stringify([{name:'counter_run',kind:'function'}]),'COUNTER_EXPORTS');
 const run=new WebAssembly.Instance(module,{env:{memory}}).exports.counter_run;
 let cursor=base;
 return Object.freeze({run,reserve(kind){
  need(kind===0||kind===1,'COUNTER_KIND');const size=kind===0?80:8,next=cursor+16+size;
  need(next<=end,'COUNTER_CAPACITY');const p=cursor,v=new DataView(memory.buffer);
  [799,p+16,0,0].forEach((word,j)=>v.setUint32(p+4*j,word,true));cursor=next;
  return Object.freeze({pointer:p+6,base:p,end:next,bytes:size});
 }});
}
