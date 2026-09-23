import assert from 'node:assert/strict';

export function checkKeywordMetadata({gen,memory,tcr,root,get,put,encode}) {
  const NIL=77825,T=77838,records=[];
  const fn=gen.functions.get('core_key_one'),raw=fn-6;
  const arity=get(raw+16)-6,pool=get(raw+24)-6,keys=get(arity+28)-6;
  const bytes=(p,n)=>Buffer.from(new Uint8Array(memory.buffer,p,n));
  const frame=()=>[64,68,72,76,80,84,88,92,96,104,112,128,140].map(n=>get(tcr+n));
  function refusal(label,args) {
    const before=frame(),from=get(tcr+56),used=get(tcr+48),heap=bytes(from,used-from);
    assert.throws(()=>gen.invoke('core_key_read',args),/checked 4$/,label);
    // invoke supplies the incoming value-stack pointer; compare the restored
    // caller state after one harmless call established the same entry setup.
    assert.deepEqual(frame(),before,label+' caller state');
    assert.equal(get(tcr+48),used,label+' allocation');
    assert.deepEqual(bytes(from,used-from),heap,label+' heap');
    records.push(label);
  }
  assert.equal(gen.invoke('core_key_read',[fn])[0],keys+6);
  for(const [label,p,value] of [
    ['missing metadata',raw+16,NIL],
    ['pool identity',raw+16,get(gen.functions.get('core_key_none')+10)],
    ['pool tag',raw+24,NIL],['pool span',raw+24,memory.buffer.byteLength+6],
    ['pool header',pool,23],['pool length',pool,506],
    ['arity width',arity,1786],['schema version',arity+4,8],
    ['required count tag',arity+8,75],['required count negative',arity+8,0xfffffffc],
    ['optional count tag',arity+12,75],['optional count negative',arity+12,0xfffffffc],
    ['rest flag',arity+16,0],['keys flag',arity+20,0],['allow-other-keys flag',arity+24,0],
    ['key vector tag',arity+28,NIL],['key vector header',keys,23],
    ['key vector span',arity+28,memory.buffer.byteLength+6],
    ['no-key nonempty vector',arity+20,NIL]]) {
    const old=get(p);put(p,value);
    try { refusal(label,[fn]); } finally { put(p,old); }
  }
  const end=memory.buffer.byteLength-8,oldEnd=get(end),oldKeys=get(arity+28);
  put(end,762);put(arity+28,end+6);
  try { refusal('key vector full extent',[fn]); } finally { put(end,oldEnd);put(arity+28,oldKeys); }
  refusal('non-function',[NIL]);
  refusal('function span',[memory.buffer.byteLength-2]);
  for(const [label,value] of [['arity tag',NIL],['arity span',memory.buffer.byteLength+6]]) {
    const old=get(raw+16),oldPool=get(pool+4);put(raw+16,value);put(pool+4,value);
    try { refusal(label,[fn]); } finally { put(raw+16,old);put(pool+4,oldPool); }
  }
  const side=encode({vector:[null,null,null,null,null,null,null]});
  put(root+4,2);put(root+8,fn);put(root+12,side);
  const gf=gen.invoke('core_gf_make',[fn,side])[0];put(root+12,gf);
  gen.invoke('core_key_read',[fn]);
  assert.deepEqual(gen.invoke('core_key_read',[gf]),[NIL]);
  records.push('funcallable key vector is NIL, as native LFUN-KEYVECT');
  const ordinary=gen.functions.get('core_generic_function_bits');
  const base=ordinary-6, literal=get(base+24)-6, prefix=get(base+16)===NIL?0:8;
  assert.equal(get(literal+4+prefix),4*0x574153);
  const bits=gen.invoke('core_generic_function_bits',[ordinary]);
  assert.equal(bits.length,1);assert.equal(bits[0]&3,0);
  function bitsRefusal(label,p,value){
    const old=get(p);put(p,value);
    try{assert.throws(()=>gen.invoke('core_generic_function_bits',[ordinary]),/checked 4$/,label);}
    finally{put(p,old);}
    records.push('bootstrap '+label);
  }
  for(const [label,p,value] of [
    ['pool tag',base+24,NIL],['pool header span',base+24,memory.buffer.byteLength+6],
    ['pool header',literal,23],['prefix length',literal,250],
    ['prefix magic',literal+4+prefix,0]]) bitsRefusal(label,p,value);
  const endPool=memory.buffer.byteLength-8,oldHeader=get(endPool);
  put(endPool,(3+prefix/4)*256+250);
  try{bitsRefusal('prefix full extent',base+24,endPool+6);}
  finally{put(endPool,oldHeader);}
  for(const [label,args] of [
    ['bits writer ordinary function',[ordinary,0]],
    ['bits writer type',[gf,NIL]],['bits writer negative',[gf,0xfffffffc]]]) {
    const side=get(gf+22),oldBits=get(side+22);
    assert.throws(()=>gen.invoke('core_generic_set_function_bits',args),/checked 4$/,label);
    assert.equal(get(side+22),oldBits);records.push(label);
  }
  return records;
}
