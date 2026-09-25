// The same qualified internal B leaves used by the compiler/runtime corpus.
// Their objects occupy a declared pinned region; no Lisp consumer is replaced.
import assert from 'node:assert/strict';

export async function installHashLeaves({memory,env,get,put,binary,hash,pins,symbolAddress,layout,registry,N}) {
  for(const [start,end] of [[1800000,1940000],[1169504,1169512]]) {
    assert(end<=memory.buffer.byteLength);
    assert([...layout.regions,...layout.spaces].every(r=>end<=r.start||start>=r.end));
  }
  for(const [name,digest] of Object.entries(pins.binaries))
    assert.equal(hash(binary(name.slice(0,-5))),digest,name);
  const service=(await WebAssembly.instantiate(binary('hash'),{env:{memory}})).instance.exports;
  const adapter=await WebAssembly.compile(binary('hash-adapter'));
  const names=['%WASM-EQ-TABLE-GET','%WASM-EQ-TABLE-SET','%WASM-EQ-TABLE-REMOVE'];
  for(const [operation,name] of names.entries()) {
    const id=operation+1,base=280000+32*operation;
    assert.equal(env.table.get(id),null);assert.equal(env.tail_table.get(id),null);
    assert.deepEqual([0,4,8,12].map(i=>get(registry+8+16*id+i)),[0,0,0,0]);
    const instance=new WebAssembly.Instance(adapter,{env,hash:{run:service.ht_run,
      collect:()=>{throw Error('EQ-table leaf must not collect');},config:0,operation,
      scratch:1800000,scratch_end:1940000,result:1169504}});
    [1578,id*4,N,4,N,N,N,0].forEach((v,i)=>put(base+4*i,v));
    [id,4,17,23].forEach((v,i)=>put(registry+8+16*id+4*i,v));
    env.table.set(id,instance.exports.entry);env.tail_table.set(id,instance.exports.tail_entry);
    put(symbolAddress('CCL',name)+6,base+6);
  }
  return {names,...pins};
}
