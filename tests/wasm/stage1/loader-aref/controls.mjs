import assert from 'node:assert/strict';
import {controls as locks} from './lock-controls.mjs';

export function controls(context) {
  const rows=locks(context);
  const {get,put,N,T,EXTERNAL,t,symbolAddress,callObject}=context;
  const entry=name=>get(symbolAddress('CCL',name)-6+12);
  const fn=entry('LOADER-ARRAY-OPERATION');
  const invoke=(op,a=N,i=0,j=0,k=0,value=0)=>callObject(fn,[op*4,a,i,j,k,value],false);
  const words=(p,n)=>Array.from({length:n},(_,i)=>get(p+4*i));
  function refusal(name,make,op,indices,value=0) {
    const a=invoke(make)[0];put(EXTERNAL+12,a);
    const data=get(a+6),header=words(a-6,(get(a-6)>>>8)+1);
    // All test backings fit this allocated extent, including bit/string data.
    const count=get(data-6)>>>8,tag=get(data-6)&255;
    const bytes=tag===255?Math.ceil(count/32)*4:count*4;
    const before=words(data-6,1+Math.ceil(bytes/4));
    const tcr=[64,76,88,128,108].map(t);
    let reason;
    assert.throws(()=>invoke(op,a,...indices,value),error=>{
      reason=error.message;
      return /^checked \d+$/.test(reason)||/^type_error \d+ \d+$/.test(reason);
    },name);
    assert.deepEqual(words(a-6,header.length),header,name+' header preserved');
    assert.deepEqual(words(data-6,before.length),before,name+' backing preserved');
    assert.deepEqual([64,76,88,128,108].map(t),tcr,name+' TCR restored');
    rows.push({name,reason,statePreserved:true});
    put(EXTERNAL+12,N);
  }
  for(const op of [1,2]) {
    for(const [axis,limit] of [[0,2],[1,3]]) {
      for(const [kind,value] of [['negative',-4],['upper',limit*4],['type',T]]) {
        const indices=[0,0,0];indices[axis]=value;
        refusal(`array-rank2-op${op}-axis${axis}-${kind}`,0,op,indices,28);
      }
    }
    refusal('array-empty-'+op,6,op,[0,0,0]);
    refusal('array-rank3-as-rank2-'+op,3,op,[0,0,0]);
  }
  for(const op of [4,5]) {
    for(let axis=0;axis<3;axis++) {
      for(const [kind,value] of [['negative',-4],['upper',8],['type',T]]) {
        const indices=[0,0,0];indices[axis]=value;
        refusal(`array-rank3-op${op}-axis${axis}-${kind}`,3,op,indices,28);
      }
    }
    refusal('array-rank2-as-rank3-'+op,0,op,[0,0,0]);
  }
  refusal('array-bit-store-type',7,2,[0,0,0],8);
  refusal('array-character-store-type',8,5,[0,0,0],28);
  for(const op of [1,2,4,5]) {
    for(const [name,value] of [['nil',N],['integer',4],['symbol',T]]) {
      const before=[64,76,88,128,108].map(t);
      let reason;
      assert.throws(()=>invoke(op,value),error=>{
        reason=error.message;return /^checked \d+$/.test(reason)||/^type_error \d+ \d+$/.test(reason);
      },'array-nonarray-'+name+'-'+op);
      assert.deepEqual([64,76,88,128,108].map(t),before);
      rows.push({name:'array-nonarray-'+name+'-'+op,reason});
    }
  }
  const a=invoke(0)[0];put(EXTERNAL+12,a);
  const cube=invoke(3)[0];put(EXTERNAL+8,cube);
  const shapedVector=invoke(9)[0];put(EXTERNAL+4,shapedVector);
  for(const [name,good,args,expected] of [
    ['LOWER','%WASM-ARRAY-SUBSCRIPT',[a,0,-4],-4],
    ['UPPER','%WASM-ARRAY-SUBSCRIPT',[a,0,8],8],
    ['RANK','%WASM-ARRAY-INDEX',[cube,8,0,0,0],0],
    ['HEADER','%WASM-ARRAY-INDEX',[shapedVector,8,0,0,0],0]
  ]) {
    // Bind the early error context as the ordinary operation wrapper does.
    const handlers=symbolAddress('CCL','%HANDLERS%')-6+8,old=get(handlers);
    put(handlers,N);
    try {
      assert.throws(()=>callObject(entry(good),args,false),/^Error: (checked \d+|type_error \d+ \d+)$/);
      assert.deepEqual(callObject(entry('LOADER-ARRAY-MUTANT-'+name),args,false),[expected>>>0]);
    } finally {put(handlers,old);}
    rows.push({name:'array-'+name.toLowerCase()+'-clause-mutant',status:'KILLED'});
  }
  put(EXTERNAL+12,N);
  put(EXTERNAL+8,N);
  put(EXTERNAL+4,N);
  return rows;
}
