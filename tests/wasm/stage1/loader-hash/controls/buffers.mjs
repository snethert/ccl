import assert from 'node:assert/strict';
export function controls({get,t,symbolAddress,callObject}) {
 const rows=[],sym=n=>symbolAddress('CCL',n),cleanup=sym('*LOADER-BUFFER-CLEANUP*')+2;
 for(let kind=0;kind<10;kind++) {
  const state=[64,76,88,108,128,140,148].map(t),before=get(cleanup);
  assert.throws(()=>callObject(get(sym('LOADER-BUFFER-REFUSAL')+6),[kind*4],false),/^Error: checked \d+$/);
  assert.deepEqual([64,76,88,108,128,140,148].map(t),state);
  assert.equal(get(cleanup),before+4);
  rows.push({name:'buffer-hash-refusal-'+kind,checked:true,cleanup:true,statePreserved:true});
 }
 return rows;
}
