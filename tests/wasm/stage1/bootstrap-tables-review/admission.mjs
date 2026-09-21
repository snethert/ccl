import fs from 'node:fs';import assert from 'node:assert/strict';
import {createStrongEQ,strongPlan,plannedCapacity,STRONG_POLICY} from './policy.mjs';
const dir=process.argv[2],site=JSON.parse(fs.readFileSync(dir+'/selection.json'))[0];
const memory=new WebAssembly.Memory({initial:64,maximum:32769,shared:true}),base=262144;
const service=(await WebAssembly.instantiate(fs.readFileSync(dir+'/hash.wasm'),{env:{memory}})).instance.exports;
const liveCount=1281,capacity=plannedCapacity(site,liveCount),bytes=64+8*capacity;
assert.equal(capacity,2048);assert.equal(plannedCapacity(site,1049),2048);
for(const n of [undefined,-1,1.5,NaN,Infinity,Number.MAX_SAFE_INTEGER])assert.throws(()=>plannedCapacity(site,n));
for(const n of [13108,16384,16385])assert.throws(()=>plannedCapacity(site,n),/exceeds 16384/);
assert.equal(plannedCapacity(site,13107),16384);
let checks=[];
const args={site,policy:STRONG_POLICY,memory,service,base,end:base+bytes,capacity,liveCount};
// A spy records entry to the primitive, independently of its own validation.
for(const [name,changes] of [
 ['capacity-population',{capacity:64}],['capacity-min',{capacity:2}],['capacity-max',{capacity:32768}],['capacity-power',{capacity:2049}],
 ['capacity-extra',{capacity:4096}],
 ['alignment',{base:base+4,end:base+4+bytes}],['negative-base',{base:-8,end:bytes-8}],
 ['end-bound',{base:memory.buffer.byteLength-8,end:memory.buffer.byteLength-8+bytes}],
 ['extent',{end:base+bytes+8}],['memory',{memory:{}}],['missing-count',{liveCount:undefined}],
 ]){
 let entered=0;const spy={ht_size:c=>{entered++;return service.ht_size(c);},ht_init:(...x)=>{entered++;return service.ht_init(...x);}};
 const modified={...args,...changes,service:spy};if('capacity' in changes)modified.end=base+64+8*changes.capacity;
 const before=new Uint8Array(memory.buffer).slice();assert.throws(()=>createStrongEQ(modified),undefined,name);
 assert.equal(entered,0,name+' preflight');assert.deepEqual(new Uint8Array(memory.buffer),before,name+' untouched');checks.push(name);
}
let entered=0;assert.throws(()=>createStrongEQ({...args,service:{ht_size:()=>bytes+8,ht_init:()=>{entered++;return 0;}}}),/service size/);assert.equal(entered,0);checks.push('service-size');
// A real service bound to a smaller memory rejects the otherwise admitted base.
const small=new WebAssembly.Memory({initial:32,maximum:32769,shared:true});
const other=(await WebAssembly.instantiate(fs.readFileSync(dir+'/hash.wasm'),{env:{memory:small}})).instance.exports;
const far=3145728;let status;
const before=new Uint8Array(memory.buffer).slice(),smallBefore=new Uint8Array(small.buffer).slice();
assert.throws(()=>createStrongEQ({...args,base:far,end:far+bytes,service:{ht_size:other.ht_size,ht_init:(...x)=>{status=other.ht_init(...x);return status;}}}),/table construction/,'failed primitive');
assert.notEqual(status,0);assert.deepEqual(new Uint8Array(memory.buffer),before);assert.deepEqual(new Uint8Array(small.buffer),smallBefore);checks.push('init-status');
assert.throws(()=>strongPlan({...site,weak:'bogus'},STRONG_POLICY),/constructor policy/);
assert.equal(strongPlan({...site,weak:'value'},STRONG_POLICY).retention,'keys-and-values');checks.push('metadata');
// Full capacity is a visible checked refusal, never eviction or silent growth.
const cap=16384,end=base+64+8*cap,result=1900000,scratch=1600000;
const table=createStrongEQ({...args,capacity:cap,liveCount:13107,end}).table;
const v=new DataView(memory.buffer),get=p=>v.getUint32(p,true);
for(let i=0;i<cap;i++)assert.equal(service.ht_run(table,end,1,i*4,28,scratch,scratch+131072,result),0);
const saved=new Uint8Array(memory.buffer,base,end-base).slice();new Uint8Array(memory.buffer,result,16).fill(0xa5);
assert.equal(service.ht_run(table,end,1,cap*4,32,scratch,scratch+131072,result),4,'FULL at ceiling');
assert.deepEqual(new Uint8Array(memory.buffer,base,end-base),saved);assert(new Uint8Array(memory.buffer,result,16).every(x=>x===0xa5));assert.equal(get(table+30),cap*4);checks.push('ceiling-full-preserves');
fs.writeFileSync(process.argv[3],JSON.stringify({status:'PASS',checks,fullEntries:cap},null,2)+'\n');
