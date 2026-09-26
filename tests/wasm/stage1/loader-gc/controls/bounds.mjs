import assert from 'node:assert/strict';
export function controls({get,t,symbolAddress,callObject}) {
 const sym=n=>symbolAddress('CCL',n),fn=n=>get(sym(n)+6),rows=[];
 const state=()=>[64,76,88,108,128,140,148].map(t);
 const allocation=()=>[48,52,56,204].map(t),beforeAllocation=allocation();
 let saved=state();
 assert.throws(()=>callObject(fn('LOADER-GC-ALLOCATE-HASH'),[32784*4],false),/^Error: checked 6$/);
 assert.deepEqual(state(),saved);assert.deepEqual(allocation(),beforeAllocation);
 rows.push({name:'native-hash-allocator-upper-limit',checked:true,statePreserved:true});
 const parser=get(sym('*LOADER-FASL-STATE*')+2),destination=get(sym('*LOADER-FASL-DESTINATION*')+2);
 const fields=Array.from({length:15},(_,i)=>get(parser-6+4*i));saved=state();
 // With N=0 no copying or refill occurs. Only the parser's offset clause
 // can reject this input; downstream copy bounds cannot hide its removal.
 assert.throws(()=>callObject(fn('%SIMPLE-FASL-READ-N-BYTES'),[parser,destination,-4,0],false),/^Error: checked 10$/);
 assert.deepEqual(Array.from({length:15},(_,i)=>get(parser-6+4*i)),fields);
 assert.deepEqual(state(),saved);
 rows.push({name:'fasl-negative-offset-zero-count',checked:true,statePreserved:true});
 return rows;
}
