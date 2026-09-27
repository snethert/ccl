import fs from 'node:fs';
import assert from 'node:assert/strict';
import {deriveLayout} from '../../../../runtime/wasm32/layout.mjs';
import {CollectorOwner} from '../../../../runtime/wasm32/collector-owner.mjs';
import {sha256} from '../../../../runtime/wasm32/sha256.mjs';
const binary=fs.readFileSync(process.argv[2]),N=77825,T=77838,PAGE=65536,checks=[];
const input={bootFunctions:3,bootRootCells:5,runtimeFunctions:10,runtimeRootCells:20,image:[{start:77824,end:77864}]};
for(const space of [16,32,64]){
 const l=deriveLayout({spaceBytes:space*1048576},input);
 assert.equal(l.stackDefaults[0],1048576);assert.equal(l.stackDefaults[1],1048576);assert.equal(l.stackDefaults[2],524288);
 assert.equal(l.tcrWords[64]%16,0);assert.equal(l.rows,16+3+2*10+8192);
 assert.equal(l.spaces[0].end-l.spaces[0].start,space*1048576);
 assert(l.regions.every(r=>r.end<=l.initialPages*PAGE));
 for(const [i,a] of [...l.regions,...l.spaces].entries())for(const b of [...l.regions,...l.spaces].slice(0,i))assert(a.start>=b.end||b.start>=a.end);
 checks.push('disjoint-'+space);
}
for(const [name,config] of [['unaligned-space',{spaceBytes:65537}],['small-value-stack',{valueStack:8192}],
 ['unaligned-temp-stack',{tempStack:17}],['unaligned-control-stack',{controlStack:17}],['zero-generations',{generations:0}],
 ['too-small-memory',{maximumPages:1}],['negative-headroom',{freeTarget:-1}],['fractional-budget',{postImageCodes:1.5}]]){
 assert.throws(()=>deriveLayout(config,input),/layout:/);checks.push(name);
}
assert.throws(()=>deriveLayout({}, {...input,image:[{start:1024,end:1280}]}),/overlap/);checks.push('fixed-region-overlap');
function fixture({headroom=2*PAGE,maximumPages=32769,engineMaximum=32769,fill=true}={}){
 const l=deriveLayout({spaceBytes:PAGE,freeTarget:headroom,postImageRoots:0,maximumPages},input);
 const memory=new WebAssembly.Memory({initial:l.initialPages,maximum:engineMaximum,shared:true});
 const get=p=>new DataView(memory.buffer).getUint32(p,true),put=(p,v)=>new DataView(memory.buffer).setUint32(p,v,true);
 put(N-1,N);put(N+3,N);put(T-6,1850);for(let i=1;i<8;i++)put(T-6+4*i,N);
 for(const [o,v] of Object.entries({...l.tcrWords,188:N}))put(l.tcr+Number(o),v);
 for(const g of l.groups)for(const p of g.slots)put(p,N);put(l.runtimeGlobals,1);
 if(fill){let tail=N;for(let p=l.spaces[0].start;p<l.spaces[0].end;p+=8){put(p,tail);put(p+4,28);tail=p+1;}
  put(l.external,tail);put(l.tcr+48,l.spaces[0].end);}
 const phases=[];
 const owner=CollectorOwner.create(memory,binary,sha256(binary),l,{measure:(phase,run)=>{const value=run();phases.push({phase,value});return value;}});
 return {l,memory,get,put,owner,phases,at:f=>owner.atSafepoint(f)};
}
{
 const f=fixture(),r=f.at(o=>o.ensure(8));assert(r.grown);assert(f.get(f.l.tcr+52)-f.get(f.l.tcr+48)>=2*PAGE+8);
 assert.equal(f.get(f.get(f.l.external)+3),28);checks.push('allocation-growth-with-headroom');
 assert(f.phases.some(x=>x.phase==='collector.prepare')&&f.phases.some(x=>x.phase==='collector.c'));
 const copies=f.phases.filter(x=>x.phase==='collector.copy');assert.equal(copies.length,2);
 assert(copies.every(x=>x.value.usedBytes===PAGE&&x.value.liveBytes===PAGE&&x.value.rootSlots>0));checks.push('collector-timer-counts');
}
{
 const f=fixture(),r=f.at(o=>o.collect());assert(r.grown);assert(f.get(f.l.tcr+52)-f.get(f.l.tcr+48)>=2*PAGE);checks.push('explicit-collection-headroom');
}
{
 const f=fixture({fill:false});const before=f.memory.buffer.byteLength;
 assert.deepEqual(f.at(o=>o.ensure(8)),{collected:false,grown:false});assert.equal(f.memory.buffer.byteLength,before);checks.push('fast-fit-no-headroom-refusal');
 const initial=f.l.initialPages;
 const limited=fixture({fill:false,engineMaximum:initial});const r=limited.at(o=>o.collect());
 assert(r.headroomRefused);assert.equal(limited.owner.collectionCount,1);assert.equal(limited.get(limited.l.tcr+48),limited.get(limited.l.tcr+56));checks.push('optional-headroom-engine-refusal');
}
{
 const initial=fixture().l.initialPages;
 const f=fixture({engineMaximum:initial});assert.throws(()=>f.at(o=>o.ensure(8)),/engine growth refusal/);
 assert.equal(f.get(f.get(f.l.external)+3),28);assert.equal(f.owner.collectionCount,1);checks.push('allocation-refusal-preserves-live');
}
{
 const initial=fixture().l.initialPages;
 const f=fixture({engineMaximum:initial+4}),r=f.at(o=>o.ensure(8));
 assert(r.grown&&r.collection.headroomRefused);assert(f.get(f.l.tcr+52)-f.get(f.l.tcr+48)>=8);
 assert(f.get(f.l.tcr+52)-f.get(f.l.tcr+48)<2*PAGE);assert.equal(f.get(f.get(f.l.external)+3),28);checks.push('required-growth-without-optional-headroom');
}
for(const [name,offset,limit] of [['temp',76,84],['control',88,96]]){
 const f=fixture({fill:false});f.put(f.l.tcr+offset,f.get(f.l.tcr+limit)+8);
 assert.throws(()=>f.at(o=>o.ensure(8)),new RegExp(name+'-stack ownership'));checks.push(name+'-upper-bound');
}
{
 const f=fixture();f.at(o=>o.inhibitCollection(1));const before=f.owner.collectionCount;
 const r=f.at(o=>o.ensure(8));assert(r.deferred&&r.grown);assert.equal(f.owner.collectionCount,before);
 assert(f.owner.collectionPending);assert.equal(f.get(f.get(f.l.external)+3),28);
 f.at(o=>o.inhibitCollection(-1));assert(!f.owner.collectionPending);assert(f.owner.collectionCount>before);checks.push('inhibited-growth-and-unlock');
}
console.log(JSON.stringify({status:'PASS',checks:checks.length,cases:checks}));
