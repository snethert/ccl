import assert from 'node:assert/strict';

export function controls({get,put,N,T,EXTERNAL,t,symbolAddress,callObject}) {
  const entry=name=>get(symbolAddress('CCL',name)-6+12);
  const fn=entry('LOADER-RWLOCK-OPERATION'),mutant=entry('LOADER-RWLOCK-MUTANT-STATE');
  const invoke=(op,lock=N,flag=N)=>callObject(fn,[op*4,lock,flag],false);
  const lockRoot=EXTERNAL+12;
  const fresh=()=>{const lock=invoke(0)[0];put(lockRoot,lock);return lock;};
  const pointer=lock=>get(lock-2), words=(p,n)=>Array.from({length:n},(_,i)=>get(p+4*i));
  const rows=[];
  const float=invoke(12)[0], alternate=pointer(fresh());
  put(EXTERNAL+8,alternate);
  function refusal(name,op,change=()=>{},flag=N) {
    const lock=fresh(),ptr=pointer(lock);
    const original={lock:words(lock-6,7),state:words(ptr-6,3)};
    change(lock,ptr);
    const before={lock:words(lock-6,7),state:words(ptr-6,3),tcr:[64,76,88,128,108].map(t)};
    let reason;
    assert.throws(()=>invoke(op,lock,typeof flag==='function'?flag(lock,ptr):flag),error=>{
      reason=error.message;
      return /^checked \d+$/.test(reason)||/^type_error \d+ \d+$/.test(reason);
    },name);
    assert.deepEqual(words(lock-6,7),before.lock,name+' lock preserved');
    assert.deepEqual(words(ptr-6,3),before.state,name+' state preserved');
    assert.deepEqual([64,76,88,128,108].map(t),before.tcr,name+' TCR restored');
    rows.push({name,reason,statePreserved:true});
    original.lock.forEach((v,i)=>put(lock-6+4*i,v));
    original.state.forEach((v,i)=>put(ptr-6+4*i,v));
  }
  // The helper's kind/identity guards are tested directly; the public accessor
  // separately validates kind before reaching it.
  refusal('lock-tag',5,l=>put(l-6,(6<<8)|250),(_,p)=>p);
  refusal('lock-kind',5,l=>put(l+2,T),(_,p)=>p);
  refusal('state-identity',5,()=>{},()=>get(EXTERNAL+8));
  refusal('state-vector-kind',5,(_,p)=>put(p-6,(2<<8)|191),(_,p)=>p);
  refusal('state-vector-length',5,(_,p)=>put(p-6,(3<<8)|250),(_,p)=>p);
  refusal('owner-type',5,(_,p)=>{put(p-2,float);put(p+2,4);},(_,p)=>p);
  refusal('depth-type',5,(_,p)=>{put(p-2,1024);put(p+2,float);},(_,p)=>p);
  refusal('negative-owner',5,(_,p)=>{put(p-2,-4);put(p+2,4);},(_,p)=>p);
  refusal('owner-without-depth',5,(_,p)=>put(p-2,1024),(_,p)=>p);
  refusal('depth-without-owner',5,(_,p)=>put(p+2,4),(_,p)=>p);
  for(const op of [1,2,3,4]) {
    refusal('other-owner-'+op,op,(_,p)=>{put(p-2,2048);put(p+2,op===1?-4:4);});
  }
  refusal('read-under-write',1,l=>invoke(2,l));
  refusal('write-under-read',2,l=>invoke(1,l));
  refusal('read-depth-exhausted',1,(_,p)=>{put(p-2,1024);put(p+2,0x80000000);});
  refusal('write-depth-exhausted',2,(_,p)=>{put(p-2,1024);put(p+2,0x7ffffffc);});
  refusal('unlock-empty',3);
  refusal('promote-empty',4);
  refusal('promote-multiple-readers',4,l=>{invoke(1,l);invoke(1,l);});
  for(const op of [1,2,4]) refusal('invalid-flag-'+op,op,()=>{},T);
  for(const [op,name] of [[6,'native-revival'],[7,'semaphore'],[8,'c-string'],[9,'c-string-segment'],[10,'disposable-pointer']])
    refusal(name,op);
  const lock=fresh(),ptr=pointer(lock);
  assert.throws(()=>invoke(11,lock),/^Error: checked \d+$/);
  assert.deepEqual(words(ptr-2,2),[0,0],'error cleanup releases lock');
  assert.deepEqual(invoke(1,lock),[T]);assert.deepEqual(invoke(3,lock),[T]);
  rows.push({name:'error-cleanup',released:true});
  // Exact deletion of the owner/depth coherence clause admits its directed row.
  put(ptr-2,1024);
  assert.throws(()=>invoke(5,lock,ptr),/^Error: checked \d+$/);
  assert.deepEqual(callObject(mutant,[ptr,lock],false),[ptr]);
  rows.push({name:'owner-depth-clause-mutant',status:'KILLED'});
  for(const [name,owner,depth] of [['OWNER',float,4],['DEPTH',1024,float]]) {
    put(ptr-2,owner);put(ptr+2,depth);
    assert.throws(()=>invoke(5,lock,ptr),/^Error: checked \d+$/);
    assert.deepEqual(callObject(entry('LOADER-RWLOCK-MUTANT-'+name),[ptr,lock],false),[ptr]);
    rows.push({name:name.toLowerCase()+'-type-clause-mutant',status:'KILLED'});
  }
  put(ptr-2,0);put(ptr+2,0);
  put(EXTERNAL+8,N);
  put(lockRoot,N);
  return rows;
}
