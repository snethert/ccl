// Audit 168 O-41: address-hashed keys must be rehashed after image relocation.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {sha256} from '../../../../runtime/wasm32/sha256.mjs';
import {writeHeapImage,admitHeapImage} from '../../../../runtime/wasm32/heap-image.mjs';

const [binary,output]=process.argv.slice(2);
const bytes=fs.readFileSync(binary);
const binaryDigest='c008b010d2baad452ba974321f40b77180cc604ceac8e3df584c953bc15698de';
assert.equal(sha256(bytes),binaryDigest,'reviewed hash leaf');
const module=await WebAssembly.compile(bytes);
const NIL=77825,T=77838,MOVED=0x20000000,source=1048576,cap=64;
const rootSlots=[8192,8196,8200,8204],regions=[{name:'roots',kind:'roots',start:8192,size:16}];
const scratch=196608,result=197632,records=[];

for(const destination of [8388608,2146500608]){
 const memory=new WebAssembly.Memory({initial:Math.ceil((destination+65536)/65536),maximum:32769,shared:true});
 const {exports:h}=await WebAssembly.instantiate(module,{env:{memory}});
 const v=new DataView(memory.buffer),put=(p,w)=>v.setUint32(p,w,true),get=p=>v.getUint32(p,true);
 const size=h.ht_size(cap),end=source+size+24;
 assert.equal(h.ht_init(source,source+size,cap),0);
 const keys=[source+size+1,source+size+9,source+size+17];
 for(let i=0;i<3;i++){put(keys[i]-1,(i+1)*4);put(keys[i]+3,NIL);}
 function call(base,op,key=NIL,value=NIL){
  [0xaaaaaaaa,0xbbbbbbbb,0xcccccccc,0xdddddddd].forEach((w,i)=>put(result+4*i,w));
  assert.equal(h.ht_run(base+6,base+size,op,key,value,scratch,scratch+cap*8,result),0);
  return [0,1,2,3].map(i=>get(result+4*i));
 }
 // A moved value aliases a key, a value points to the table itself, and a
 // deleted bucket survives in the serialized table until rehash compacts it.
 assert.deepEqual(call(source,1,keys[0],keys[1]),[keys[1],NIL,1,0]);
 assert.deepEqual(call(source,1,keys[1],source+6),[source+6,NIL,1,0]);
 call(source,1,keys[2],28);assert.deepEqual(call(source,2,keys[2]),[T,NIL,1,0]);
 assert.equal(get(source+32),4);
 // Serialize a live cache entry too: it must move and then be invalidated.
 assert.deepEqual(call(source,0,keys[0]),[keys[1],T,2,0]);
 [source+6,...keys].forEach((word,i)=>put(rootSlots[i],word));
 const image=writeHeapImage({memory,start:source,end,regions,rootSlots,codeDigest:binaryDigest});
 new Uint8Array(memory.buffer,source,end-source).fill(0xa5);
 const admission=()=>admitHeapImage({...image,memory,start:destination,limit:destination+size+24,regions,rootSlots,codeDigest:binaryDigest});
 admission().install();
 const relocated=keys.map(k=>k-source+destination);
 assert.deepEqual(rootSlots.map(get),[destination+6,...relocated]);
 assert.equal(get(destination+8)&MOVED,MOVED);
 assert.equal(get(destination+44),relocated[0]);assert.equal(get(destination+48),relocated[1]);
 for(let i=0;i<3;i++){assert.equal(get(relocated[i]-1),(i+1)*4);assert.equal(get(relocated[i]+3),NIL);}

 // The control removes only rehash notification and invalidates the cache.
 // At least one relocated live key must be absent with stale buckets.
 put(destination+8,get(destination+8)&~MOVED);
 put(destination+40,0xfffffffc);put(destination+44,243);put(destination+48,NIL);
 const misses=relocated.slice(0,2).filter(key=>call(destination,0,key)[1]===NIL).length;
 assert.ok(misses>0,'omitted MOVED must fail a retained lookup');

 admission().install();
 assert.deepEqual(call(destination,0,relocated[0]),[relocated[1],T,2,1]);
 assert.equal(get(destination+8)&MOVED,0);assert.equal(get(destination+32),0);
 assert.deepEqual(call(destination,0,relocated[1]),[destination+6,T,2,0]);
 assert.deepEqual(call(destination,0,relocated[2]),[NIL,NIL,2,0]);
 assert.deepEqual(call(destination,3),[8,NIL,1,0]);
 // Exercise mutation after restoration, not just the old cached answer.
 assert.deepEqual(call(destination,1,relocated[2],relocated[0]),[relocated[0],NIL,1,0]);
 assert.deepEqual(call(destination,2,relocated[1]),[T,NIL,1,0]);
 assert.deepEqual(call(destination,0,relocated[2]),[relocated[0],T,2,0]);
 records.push({destination,image_digest:image.digest,
  live_keys:2,old_heap_poisoned:true,rehash:1,omitted_moved_lookup_misses:misses});
}
const report={status:'PASS',observation:'O-41',hash_binary_sha256:binaryDigest,
 loader_sha256:sha256(fs.readFileSync(new URL('../../../../runtime/wasm32/heap-image.mjs',import.meta.url))),
 records,original_definition_credit:0,slot_credit:false};
fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report));
