import fs from 'node:fs';
import assert from 'node:assert/strict';
import {admitTerminationExclusion,POLICY} from './admission.mjs';
const rows=[];
for(const base of [4096,2147483648]){
 const memory=new WebAssembly.Memory({initial:base>1e9?32769:1,maximum:32769});
 const v=new DataView(memory.buffer),slots={populationData:base,pendingCallbacks:base+4,functionCount:base+8,automaticEnabled:base+12};
 const args=()=>({memory,policy:POLICY,region:{start:base,end:base+16},slots:{...slots}});
 const reset=()=>[77825,77825,0,77825].forEach((x,i)=>v.setUint32(base+4*i,x,true));
 const capture=()=>new Uint8Array(memory.buffer,base-16,48).slice();
 reset();const before=capture(),a=args(),record=admitTerminationExclusion(a);
 assert.deepEqual(capture(),before,'success does not clear state');
 assert(Object.isFrozen(record)&&Object.isFrozen(record.slots)&&Object.isFrozen(record.values));
 a.slots.populationData+=4;a.region.end+=4;assert.deepEqual(record.slots,slots,'private record');
 rows.push({base,kind:'empty-disabled',status:'ADMITTED'});
 for(const [name,change,why] of [
  ['registered',a=>v.setUint32(base,12345,true),'registered objects'],
  ['pending',a=>v.setUint32(base+4,12345,true),'pending callbacks'],
  ['functions',a=>v.setUint32(base+8,4,true),'function registrations'],
  ['automatic',a=>v.setUint32(base+12,77838,true),'automatic scheduling'],
  ['policy',a=>a.policy='strong-retention','policy'],
  ['memory',a=>a.memory={},'memory'],
  ['missing-slot',a=>delete a.slots.functionCount,'slot inventory'],
  ['extra-slot',a=>a.slots.extra=base,'slot inventory'],
  ['aliased-slot',a=>a.slots.pendingCallbacks=base,'slot extent/alias'],
  ['unaligned-slot',a=>a.slots.populationData++,'slot extent/alias'],
  ['negative-slot',a=>a.slots.populationData=-4,'slot extent/alias'],
  ['out-of-region',a=>a.slots.populationData=base+16,'slot extent/alias'],
  ['past-memory',a=>a.region.end=memory.buffer.byteLength+4,'region'],
  ['inverted-region',a=>a.region.end=base,'region'],
  ['fractional-region',a=>a.region.start+=.5,'region'],
 ]){
  reset();const a=args();change(a);const old=capture();
  assert.throws(()=>admitTerminationExclusion(a),new RegExp(why),name);
  assert.deepEqual(capture(),old,name+' no writes');rows.push({base,kind:name,status:'REFUSED'});
 }
 // Unknown nonzero encodings must not masquerade as empty/disabled.
 for(const [key,expected]of Object.entries({populationData:77825,pendingCallbacks:77825,functionCount:0,automaticEnabled:77825})){
  for(const value of [0,4,77825,77838,0xffffffff].filter(n=>n!==expected)){
   reset();v.setUint32(slots[key],value,true);const old=capture();
   assert.throws(()=>admitTerminationExclusion(args()),/termination exclusion:/,key+' exact encoding');
   assert.deepEqual(capture(),old);rows.push({base,kind:key+'='+value,status:'REFUSED'});
  }
 }
}
fs.writeFileSync(process.argv[2],JSON.stringify({status:'PASS',checks:rows.length,rows},null,2)+'\n');
