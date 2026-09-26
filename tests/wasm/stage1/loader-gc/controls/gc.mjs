import assert from 'node:assert/strict';
export function controls({get,put,N,T,TCR,t,symbolAddress,callObject,collect,owner}) {
 const rows=[],fn=n=>get(symbolAddress('CCL',n)+6),call=n=>callObject(fn(n),[]);
 for(const tracking of [false,true]){
  callObject(fn('LOADER-GC-HOLD'),[tracking?T:N]);
  let state=call('LOADER-GC-STATE');
  assert.deepEqual(state,[owner.collectionCount,owner.collectionCount,null,null,41,43,97,101]);
  for(let turn=0;turn<2;turn++){
   const stamp=state[1],before=owner.collectionCount;
   collect();assert.equal(owner.collectionCount,before+1);
   state=call('LOADER-GC-STATE');
   assert.deepEqual(state,[before+1,stamp,true,tracking?true:null,41,43,97,101]);
   call('LOADER-GC-RESET');state=call('LOADER-GC-STATE');
   assert.deepEqual(state,[before+1,before+1,null,null,41,43,97,101]);
  }
  call('LOADER-GC-FORCE');state=call('LOADER-GC-STATE');
  assert.deepEqual(state,[owner.collectionCount,owner.collectionCount-1,true,tracking?true:null,41,43,97,101]);
  call('LOADER-GC-RESET');assert.equal(call('LOADER-GC-STATE')[2],null);
  rows.push({name:tracking?'gc-tracked-keys':'gc-component-address',collections:2,reset:true,forced:true});
 }
 const count=t(204);
 try{
  put(TCR+204,536870911);assert.deepEqual(call('%GET-GC-COUNT'),[536870911]);
  put(TCR+204,536870912);assert.throws(()=>call('%GET-GC-COUNT'),/^Error: checked 6$/);
 }finally{put(TCR+204,count);}
 rows.push({name:'gc-count-read-boundary',checked:true});
 return rows;
}
