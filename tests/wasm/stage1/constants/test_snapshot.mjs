import assert from 'node:assert/strict';
import {Worker} from 'node:worker_threads';
import {readFileSync} from 'node:fs';
import {capture, restore, digest} from './snapshot.mjs';
const fixture = JSON.parse(readFileSync(process.argv[2]));
const probe = process.argv[3];
async function worker(data) {
  const w = new Worker(new URL('./snapshot-worker.mjs',import.meta.url),{workerData:{...data,probe}});
  return new Promise((resolve,reject)=>{let result; w.once('message',m=>result=m);w.once('error',reject);w.once('exit',code=>code===0&&result ? resolve(result):reject(new Error('worker exit '+code)));});
}
const saved = await worker({mode:'capture',fixture});
const restored = await worker({mode:'restore',snapshot:saved.bytes,sha256:saved.sha256});
const base=0x80000000;
// Literal independent expectations for the first vector, both conses and strings.
assert.deepEqual(restored.roots,[base+6,base+41,0x5006,77825]);
assert.deepEqual(restored.words.slice(0,14),[0x8fa,base+41,base+41,base+49,base+62,base+78,base+94,0x5006,77825,0,base+41,36,base+41,28]);
assert.deepEqual(restored.words.slice(14,22),[0x2bf,65,0x1f642,0,0x2bf,65,0x1f642,0]);
// Every remaining pointer-free word, including NaN bits and pointer-shaped float
// bits, remains byte-identical. The cold pool has its own relocation expectation.
const source=Buffer.from(JSON.parse(Buffer.from(saved.bytes,'hex')).image,'hex');
for(let i=88;i<source.length;i+=4) {
  const expected = i===96 ? base+41 : source.readUInt32LE(i);
  assert.equal(restored.words[i/4],expected, 'payload '+i);
}
assert.equal(restored.words[22],0x2fa); // Unexecuted pool retained.
assert.equal(restored.words[23],492);
const raw=Buffer.from(saved.bytes,'hex'), original=JSON.parse(raw);
const memory=new WebAssembly.Memory({initial:2});
new Uint8Array(memory.buffer).fill(0xa5);
const before=Buffer.from(new Uint8Array(memory.buffer));
const controls=[];
function reject(label,change,pattern,{region=65536,base=0x8000,symbols={'P::X':0x5006},badDigest=false}={}) {
  const r=structuredClone(original);change(r);
  const bytes=Buffer.from(JSON.stringify(r));
  assert.throws(()=>restore(bytes,badDigest?'0'.repeat(64):digest(bytes),memory,base,region,symbols),pattern,label);
  assert.ok(Buffer.from(memory.buffer).equals(before),'refusal changed memory: '+label);
  controls.push(label);
}
reject('digest',r=>{},/digest/,{badDigest:true});
reject('layout',r=>r.layout='0'.repeat(64),/layout/);
reject('interior-pointer',r=>{let b=Buffer.from(r.image,'hex');b.writeUInt32LE(0x100e,4);r.image=b.toString('hex');},/pointer/);
reject('unknown-root',r=>r.roots[0]=0x4001,/pointer/);
reject('wrong-tag',r=>r.objects[1].tag=3,/tag/);
reject('duplicate-id',r=>r.objects[1].id=r.objects[0].id,/identity/);
reject('omit-cold',r=>r.objects.splice(5,1),/coverage/);
reject('extra-bytes',r=>r.image+='0000000000000000',/unaccounted/);
reject('header-count',r=>{let b=Buffer.from(r.image,'hex');b.writeUInt32LE(0xfffffffa,0);r.image=b.toString('hex');},/extent/);
reject('unaligned',r=>{},/destination/,{base:0x8001});
reject('capacity',r=>{},/capacity/,{region:8});
reject('unknown-symbol',r=>{},/symbol binding/,{symbols:{}});
reject('symbol-overlap',r=>{},/overlaps/,{symbols:{'P::X':0x8006}});
reject('canonical-overlap',r=>{},/canonical object overlap/,{base:77824,region:1024});
reject('source-overflow',r=>r.base=0xfffffff8,/address extent/);
reject('missing-field',r=>delete r.roots,/record shape/);
reject('bad-hex',r=>r.image='zz',/encoding/);
reject('root-not-word',r=>r.roots[0]=true,/root word/);
reject('alias-split',r=>r.symbols.alias=r.symbols['P::X'],/alias split/,{symbols:{'P::X':0x5006,alias:0x6006}});
reject('alias-merge',r=>r.symbols.second=0x6006,/distinct symbols merged/,{symbols:{'P::X':0x5006,second:0x5006}});
const empty=new WebAssembly.Memory({initial:1});
assert.throws(()=>capture(empty,{...fixture.manifest,base:65528}),/capture extent/);
assert.throws(()=>restore(raw,saved.sha256,new WebAssembly.Memory({initial:1,maximum:1,shared:true}),8,1024,{'P::X':0x5006}),/unshared/);
console.log(JSON.stringify({status:'PASS',worker_round_trip:true,source_mutation_observed:36,restored_base:base,bytes:source.length,objects:restored.objects.length,controls,refusal_preserves_memory:true},null,2));
