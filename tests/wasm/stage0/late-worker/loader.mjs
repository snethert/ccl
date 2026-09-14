import {createHash} from 'node:crypto';
export const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
function need(ok,reason){if(!ok)throw Error(reason);}
export function inspectKernel(bytes, digest, abi, inspect) {
  need(hash(bytes)===digest,'BINARY_DIGEST');
  need(WebAssembly.validate(bytes),'INVALID_WASM');
  const m=inspect(bytes);
  if(m.data.some(d=>!d.passive))throw Error('ACTIVE_DATA');
  if(m.start!==undefined)throw Error('START_FUNCTION');
  need(m.imports.length===2&&m.imports[0].kind==='memory'&&m.imports[0].module==='env'&&m.imports[0].name==='memory'&&
    m.imports[0].flags===3&&m.imports[0].minimum===abi.memory_pages&&m.imports[0].maximum===abi.memory_pages&&
    m.imports[1].kind==='table'&&m.imports[1].module==='env'&&m.imports[1].name==='table'&&
    m.imports[1].element==='funcref'&&m.imports[1].minimum===abi.table_slots&&m.imports[1].maximum===abi.table_slots,'IMPORTS');
  need(m.sections.every(s=>[0,1,2,3,6,7,8,9,10,11,12].includes(s.id)),'KERNEL_SECTIONS');
  const functions=Object.fromEntries(m.exports.filter(e=>e.kind===0).map(e=>[e.name,m.types[m.functionTypes[e.index]]]));
  need(JSON.stringify(functions)===JSON.stringify(abi.kernel_exports),'KERNEL_SIGNATURES');
  const g={};for(const e of m.exports.filter(e=>e.kind===3)){
    const v=m.globals[e.index];need(v?.type==='i32','GLOBAL_TYPE');
    if(['owner','tls','tcr','csp','vsp'].includes(e.name))need(v.mutable===1,'INSTANCE_GLOBAL');
    else {need(v.mutable===0,'METADATA_GLOBAL');g[e.name]=v.value;}
  }
  const shared=['data','bss','heap','staging'],privateNames=Object.keys(abi.private_minimums);
  const names=['process_word','generation_word','code_record','worker_base','worker_stride','worker_count',
    ...shared.flatMap(n=>[n+'_base',n+'_size']),...privateNames.flatMap(n=>[n+'_offset',n+'_size'])];
  need(JSON.stringify(Object.keys(g).sort())===JSON.stringify(names.sort()),'METADATA_NAMES');
  need(g.worker_count===4&&g.worker_stride>0,'WORKER_COUNT');
  const regions=[];
  function region(name,start,size,alignment=abi.alignment){
    need(Number.isSafeInteger(start)&&Number.isSafeInteger(size)&&size>0,'REGION_SIZE');
    need(start%alignment===0&&size%alignment===0,'REGION_ALIGNMENT');
    need(start+size<=abi.memory_pages*65536,'REGION_BOUND');regions.push({name,start,end:start+size});
  }
  region('process',g.process_word,4,4);region('generation',g.generation_word,4,4);
  region('code',g.code_record,abi.publication.digest_bytes);
  for(const n of shared)region(n,g[n+'_base'],g[n+'_size']);
  for(let id=0;id<g.worker_count;id++)region('worker-'+id,g.worker_base+id*g.worker_stride,g.worker_stride);
  regions.sort((a,b)=>a.start-b.start);
  need(regions.every((r,i)=>!i||regions[i-1].end<=r.start),'REGION_OVERLAP');
  const owned=privateNames.map(n=>({name:n,start:g[n+'_offset'],end:g[n+'_offset']+g[n+'_size']})).sort((a,b)=>a.start-b.start);
  need(owned.every(r=>g[r.name+'_size']>=abi.private_minimums[r.name]),'PRIVATE_SIZE');
  need(owned.every((r,i)=>r.start%abi.alignment===0&&r.end%abi.alignment===0&&r.end<=g.worker_stride&&(!i||owned[i-1].end<=r.start)),'PRIVATE_LAYOUT');
  need(m.data.filter(d=>d.passive).length===1&&m.data.find(d=>d.passive).size===g.data_size&&m.dataCount===m.data.length,'PASSIVE_IMAGE');
  const reserved=[0];
  for(const e of m.elements)for(let i=0;i<e.functions.length;i++){
    const slot=e.offset+i;need(slot<abi.table_slots&&!reserved.includes(slot),'TABLE_RESERVATION');reserved.push(slot);
  }
  need(JSON.stringify(reserved)==='[0,1]','RESERVED_PREFIX');
  return {globals:g,regions,owned,reserved};
}
export function instantiateKernel(bytes,memory,table){
  return new WebAssembly.Instance(new WebAssembly.Module(bytes),{env:{memory,table}});
}
export function installLazy(bytes,digest,memory,table,slot,meta,abi,inspect) {
  need(hash(bytes)===digest,'LAZY_DIGEST');need(WebAssembly.validate(bytes),'INVALID_LAZY');
  const m=inspect(bytes);
  if(m.data.length)throw Error('LAZY_DATA');
  if(m.start!==undefined)throw Error('LAZY_START');
  need(m.elements.length===0&&m.imports.length===1&&m.imports[0].kind==='memory'&&
    m.imports[0].module==='env'&&m.imports[0].name==='memory'&&m.imports[0].flags===3&&
    m.imports[0].minimum===abi.memory_pages&&m.imports[0].maximum===abi.memory_pages,'LAZY_IMPORTS');
  need(m.sections.every(s=>[0,1,2,3,7,8,10,11,12].includes(s.id)),'LAZY_SECTIONS');
  const e=m.exports.find(e=>e.name==='entry'&&e.kind===0);
  need(m.exports.length===1&&e&&JSON.stringify(m.types[m.functionTypes[e.index]])===JSON.stringify(abi.entry_signature),'LAZY_SIGNATURE');
  if(meta.reserved.includes(slot))throw Error('RESERVED_SLOT');
  need(Number.isInteger(slot)&&slot>=0&&slot<table.length&&table.get(slot)===null,'SLOT_CAPACITY');
  const instance=new WebAssembly.Instance(new WebAssembly.Module(bytes),{env:{memory}});
  table.set(slot,instance.exports.entry);
}
