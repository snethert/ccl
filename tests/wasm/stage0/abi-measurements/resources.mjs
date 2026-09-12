import fs from 'node:fs';
import path from 'node:path';
import {sha} from './build.mjs';
import {inspect} from '../runtime-boundary/binary.mjs';

function sections(bytes) {
  let p=8;const read=()=>{let n=0,s=0,b;do{b=bytes[p++];n+=(b&127)*2**s;s+=7;}while(b&128);return n;};
  const result=[];
  while(p<bytes.length){const id=bytes[p++],size=read(),start=p;result.push({id,bytes:size});p=start+size;}
  return result;
}
function callableBytes(bytes) {
  const m=inspect(bytes),section=m.sections.find(s=>s.id===10);let p=section.payload;
  const read=()=>{let n=0,s=0,b;do{b=bytes[p++];n+=(b&127)*2**s;s+=7;}while(b&128);return n;};
  const count=read(),bodies=[];for(let i=0;i<count;i++){const n=read();bodies.push(n);p+=n;}
  const imports=m.imports.filter(i=>i.kind==='function').length;
  return m.exports.filter(e=>e.kind===0).map(e=>({name:e.name,body_bytes:bodies[e.index-imports]}));
}
export function resources(build,name,dir) {
  const c=build.candidates[name];
  const active=[['kernel',build.kernel],['emitted',build.emitted],['support',c.support],['registry',c.registry],
    ['schedule',c.schedule],['driver',c.driver],['stub',c.stub],['wrong-role-control',c.wrong],
    ...(c.packaging==='cross-instance'?c.modules.map(m=>[m.name,m.bytes]):[])];
  return {candidate:name,packaging:c.packaging,
    modules:active.map(([name,bytes])=>({name,bytes:bytes.length,sha256:sha(bytes),sections:sections(bytes)})),
    instantiated_module_count:active.length,
    delivered_reference_bytes:c.modules.reduce((n,m)=>n+m.bytes.length,0),
    reference_scope:c.packaging==='cross-instance'?'callable modules instantiated':'individual callable bytes retained/delivered for identity validation; bundle is instantiated',
    metadata_bytes:fs.statSync(path.join(dir,name,'debug-metadata.json')).size,
    entry_bodies:(c.packaging==='cross-instance'?c.modules.map(m=>[m.name,m.bytes]):[['driver',c.driver]])
      .map(([module,bytes])=>({module,entries:callableBytes(bytes)})),
    stub_bodies:callableBytes(c.stub),table_slots:build.slots.minimum,callable_slots:build.slots.entries.length*3,
    layout:{debug_policy:1,logical_frame_bytes:512,maximum_arguments:32,maximum_results:6},
    memory:{shared_linear_bytes:1048576,semispace_bytes:4096,ownership_slots:4,live_workers:2,
      per_slot_explicit_stack_reserved_bytes:16384,per_slot_C_stack_reserved_bytes:16384,
      per_slot_inspection_reserved_bytes:131072,per_slot_schedule_reserved_bytes:8192,
      allocation_scope:'reservations within one shared linear memory; do not sum them again as independent allocations'},
    unavailable:['dynamic root stores and reloads','engine machine code bytes','peak C-stack use','per-Worker resident memory',
      'request-to-last-park, collector pause, release-to-progress latency','browser persistent code-cache state']};
}
