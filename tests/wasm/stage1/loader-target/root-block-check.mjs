import fs from 'node:fs';
import assert from 'node:assert/strict';
import {deriveLayout} from '../../../../runtime/wasm32/layout.mjs';
import {CollectorOwner} from '../../../../runtime/wasm32/collector-owner.mjs';
import {sha256} from '../../../../runtime/wasm32/sha256.mjs';
const binary=fs.readFileSync(process.argv[2]),N=77825,T=77838;
const layout=deriveLayout({postImageRoots:0},{bootFunctions:0,runtimeFunctions:0,runtimeRootCells:8,image:[{start:77824,end:77864}]}),
 memory=new WebAssembly.Memory({initial:layout.initialPages,maximum:32769,shared:true});
const get=p=>new DataView(memory.buffer).getUint32(p,true),put=(p,v)=>new DataView(memory.buffer).setUint32(p,v,true);
put(N-1,N);put(N+3,N);put(T-6,1850);for(let i=1;i<8;i++)put(T-6+4*i,N);
for(const [o,v] of Object.entries({...layout.tcrWords,188:N}))put(layout.tcr+Number(o),v);
for(const g of layout.groups)for(const p of g.slots)put(p,N);put(layout.runtimeGlobals,1);
const owner=CollectorOwner.create(memory,binary,sha256(binary),layout),at=f=>owner.atSafepoint(f),checks=[];
const snapshot=()=>({storage:owner.storage,external:new Uint8Array(memory.buffer,layout.external,256).slice(),
 tcr:new Uint8Array(memory.buffer,layout.tcr,256).slice()});
function refuse(name,f,pattern){const before=snapshot();assert.throws(f,pattern);assert.deepEqual(snapshot(),before);checks.push(name);}
refuse('outside-boundary',()=>owner.reserveRootBlock(2),/legal owner boundary/);
refuse('zero-count',()=>at(o=>o.reserveRootBlock(0)),/root block count/);
refuse('fractional-count',()=>at(o=>o.reserveRootBlock(1.5)),/root block count/);
const before=snapshot(),a=at(o=>o.reserveRootBlock(8));at(()=>a.release());assert.deepEqual(snapshot(),before);checks.push('reservation-rollback');
const first=at(o=>o.reserveRootBlock(8)),second=at(o=>o.reserveRootBlock(8));first.commit();second.commit();
refuse('cumulative-charge',()=>at(o=>o.reserveRootBlock(2)),/root capacity/);
refuse('v1-respects-charge',()=>at(o=>o.rootCells([N,N])),/root capacity/);
refuse('duplicate-slice',()=>at(()=>first.register([first.base,first.base])),/root slice/);
refuse('outside-slice',()=>at(()=>first.register([second.base])),/root slice/);
const address=get(layout.tcr+48);put(address,N);put(address+4,314*4);put(layout.tcr+48,address+8);
put(first.base,address+1);at(()=>first.register([first.base]));
refuse('already-registered',()=>at(()=>first.register([first.base])),/root slice/);
refuse('published-block-release',()=>at(()=>first.release()),/released roots/);
// An invalid pointer in an unpublished cell must not enter the collector list.
put(second.base,1234567);
at(o=>o.collect());assert.notEqual(get(first.base),address+1);assert.equal(get(get(first.base)+3),314*4);
assert.equal(get(second.base),1234567);checks.push('published-only-moving-roots');
const v1=at(o=>o.rootCells([N]));assert(v1.slots[0]>=second.base+32);checks.push('v1-v2-disjoint');
at(()=>v1.release());at(()=>first.unregister([first.base]));at(()=>first.release());at(()=>second.release());
assert.equal(owner.storage.reservedRootCells,0);checks.push('release-capacity');
refuse('double-release',()=>at(()=>first.release()),/released roots/);
console.log(JSON.stringify({status:'PASS',checks:checks.length,cases:checks}));
