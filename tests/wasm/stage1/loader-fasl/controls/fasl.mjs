import assert from 'node:assert/strict';
export function controls({get,t,N,symbolAddress,callObject}) {
 const rows=[],sym=n=>symbolAddress('CCL',n),fn=n=>get(sym(n)+6),state=()=>[64,76,88,108,128,140,148].map(t);
 const cleanup=sym('*LOADER-FASL-CLEANUP*')+2;
 for(const kind of [0,1,2]) {
  const saved=state();
  assert.throws(()=>callObject(fn('LOADER-FASL-REFUSALS'),[kind*4],false),/^Error: checked 10$/);
  assert.deepEqual(state(),saved);
  rows.push({name:'fasl-malformed-'+kind,checked:true,statePreserved:true,nativeHandlerMatched:false});
 }
 for(const opcode of [2,20,72]) {
  const before=get(cleanup),saved=state();
  assert.throws(()=>callObject(fn('LOADER-FASL-NATIVE-CODE'),[opcode*4],false),/^Error: checked 10$/);
  assert.equal(get(cleanup),before+4);assert.deepEqual(state(),saved);
  rows.push({name:(opcode===72?'target-code-installation-':'native-code-opcode-')+opcode,checked:true,cleanup:true,statePreserved:true});
 }
 assert.throws(()=>callObject(fn('LOADER-FASL-WORD'),[N],false),/^Error: checked 5$/);
 rows.push({name:'word-to-int-non-fixnum',checked:true});
 callObject(fn('LOADER-FASL-HOLD'),[]);
 const parser=get(sym('*LOADER-FASL-STATE*')+2),destination=get(sym('*LOADER-FASL-DESTINATION*')+2);
 const snapshot=()=>[...Array.from({length:15},(_,i)=>get(parser-6+4*i)),get(destination-2),get(destination+2)];
 for(const [name,offset,count] of [['negative-offset',-1,1],['negative-count',0,-1],['destination-overrun',7,2]]) {
  const before=snapshot(),saved=state();
  assert.throws(()=>callObject(fn('%SIMPLE-FASL-READ-N-BYTES'),[parser,destination,offset*4,count*4],false),/^Error: checked \d+$/);
  assert.deepEqual(snapshot(),before);assert.deepEqual(state(),saved);
  rows.push({name:'fasl-copy-'+name,checked:true,statePreserved:true});
 }
 return rows;
}
