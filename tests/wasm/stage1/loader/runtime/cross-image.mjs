// Initial cross-loaded image admission. The Worker owner supplies the trusted
// manifest and capabilities. No Lisp initializer runs during installation.
import {sha256} from './sha256.mjs';
import {compile,publish,PACKAGING} from './bundle.mjs';
import {admitHeapImage} from './heap-image.mjs';
const need=(v,s)=>{if(!v)throw Error('cross image: '+s);};
export function admitCrossImage({memory,manifest,record,payload,codeSet,regions,env,readBytes,readTemplate,policy,expected,capabilities,start=manifest.heap.start}) {
 const m=structuredClone(manifest),set=structuredClone(codeSet);
 env={...env};expected=structuredClone(expected);
 need(m.version===1&&m.layout==='D1','MANIFEST');
 need(Number.isInteger(m.heap.bytes)&&m.heap.bytes===payload.length,'HEAP_LENGTH');
 need(sha256(JSON.stringify(set))===m.codeDigest,'CODE_DIGEST');
 need(set.version===1&&set.packaging===PACKAGING&&set.first_code_id===16,'PACKAGING');
 need(set.modules.length===m.modules,'MODULE_COUNT');
 need(env.memory===memory&&env.table!==env.tail_table,'CAPABILITIES');
 const view=new DataView(memory.buffer),get=p=>view.getUint32(p,true),put=(p,v)=>view.setUint32(p,v,true);
 const registry=env.code_registry;
 need(Number.isInteger(registry)&&registry%8===0&&registry>=0&&registry+8<=view.byteLength,'REGISTRY');
 const capacity=get(registry);
 need(get(registry+4)===1&&capacity<=env.table.length&&capacity<=env.tail_table.length&&registry+8+capacity*16<=view.byteLength,'REGISTRY');
 const registryEnd=registry+8+capacity*16;
 need([{start,size:m.heap.bytes},...regions].every(r=>registryEnd<=r.start||r.start+r.size<=registry),'REGISTRY_OVERLAP');
 const names=new Set(),ids=new Set();
 for(const row of set.modules){
  need(typeof row.name==='string'&&/^[a-zA-Z0-9_]+$/.test(row.name)&&!names.has(row.name),'NAME');names.add(row.name);
  need(Number.isInteger(row.code_id)&&row.code_id>=set.first_code_id&&row.code_id<capacity&&!ids.has(row.code_id),'CODE_ID');ids.add(row.code_id);
  need(row.version===4&&row.signature===17&&row.role===23,'CODE_ROLE');
  need(Array.isArray(row.arity)&&row.arity.length===6&&row.arity.slice(0,2).every(n=>Number.isInteger(n)&&n>=0)&&row.arity.slice(2,5).every(v=>typeof v==='boolean')&&Array.isArray(row.arity[5])&&row.arity[5].length===0&&Number.isInteger(row.captures)&&row.captures>=0,'CALLABLE_SHAPE');
  need(typeof row.profile==='string','PROFILE');
  need([0,4,8,12].every(o=>get(registry+8+16*row.code_id+o)===0),'OCCUPIED');
 }
 need(expected.slots!==undefined&&expected.table_capacity<=Math.min(env.table.length,env.tail_table.length),'TABLE_AUTHORITY');
 const compiled=compile(set,expected,readBytes,readTemplate,policy);
 const heap=admitHeapImage({memory,record,payload,digest:m.heap.digest,regions,start,limit:start+m.heap.bytes,codeDigest:m.codeDigest,rootSlots:m.roots.slots});
 const imports=new Map();
 for(const {record:row} of compiled){
  const symbols=Object.create(null),codes=Object.create(null);
  for(const s of row.symbols){need(!Object.hasOwn(symbols,s.wire),'SYMBOL_DUPLICATE');symbols[s.wire]=heap.reference(s.reference);}
  for(const c of row.codes){need(!Object.hasOwn(codes,c.name)&&ids.has(c.code_id),'CODE_IMPORT');codes[c.name]=c.code_id*4;}
  for(const i of row.d2.outputs.full.imports){
   if(i.module==='symbols')need(Object.hasOwn(symbols,i.name),'SYMBOL_IMPORT');
   if(i.module==='codes')need(Object.hasOwn(codes,i.name),'CODE_IMPORT');
   need(i.module!=='keywords','KEYWORD_IMPORT');
  }
  imports.set(row.name,{env,symbols,codes,...Object.fromEntries(['owner','integer','floating'].filter(n=>capabilities[n]).map(n=>[n,{...capabilities[n]}]))});
 }
 let state='ADMITTED';
 return Object.freeze({get state(){return state;},objects:heap.objects,
  install(){
   need(state==='ADMITTED','STATE');
   // Instantiation of every validated module precedes any image publication.
   // bundle.publish rolls back paired tables if publication fails.
   const installed=publish(compiled,n=>imports.get(n),env.table,env.tail_table);
   try{
    for(const {record:r} of compiled){
     need([0,4,8,12].every(o=>get(registry+8+16*r.code_id+o)===0),'REGISTRY_CHANGED');
    }
    heap.install(); // Rechecks static owners before its first write.
   }catch(error){for(const {record:r} of compiled){env.table.set(r.slot,null);env.tail_table.set(r.slot,null);}throw error;}
   // In-bounds scalar stores only; no callbacks, allocation, or suspension.
   for(const {record:r} of compiled)[r.slot,r.version,r.signature,r.role].forEach((v,i)=>put(registry+8+16*r.code_id+4*i,v));
   state='INSTALLED';return {start,end:start+m.heap.bytes,instances:installed};
  }
 });
}
