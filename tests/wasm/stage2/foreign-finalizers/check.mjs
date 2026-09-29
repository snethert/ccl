// Reused by the API matrix: real copying collector, private foreign memory.
export function finalizerChecks({test,setup,equal,assert,throws}) {
 const N=77825;
 const collect=f=>{const r=f.owner.atSafepoint(o=>o.collect());if(r.source!==undefined)new Uint8Array(f.memory.buffer,r.source,r.usedBytes).fill(0xa5);return r;};
 const buffer=f=>f.request(3,f.vec([f.library(),32]));
 const watch=(f,h,w)=>f.request(8,f.vec([h,w]));
 const releaseCount=f=>f.events.filter(n=>n===2).length;
 const forget=f=>f.put(f.args+8,N);
 for(const placement of [0,65536])test('finalizer-moving-'+placement,()=>{
  const f=setup({placement}),h=buffer(f),w=f.vec([168]);equal(watch(f,h,w),0);collect(f);
  equal(f.owner.pendingFinalizers,0);equal(releaseCount(f),0);
  const moved=f.get(f.get(f.args+8)+2);assert(moved!==w,'anchor moved');equal(f.get(moved-2),168);
  collect(f);equal(f.owner.pendingFinalizers,0,'second forwarding');
  forget(f);collect(f);equal(f.owner.pendingFinalizers,1);equal(releaseCount(f),0,'collection only queues');
  equal(f.request(9,N),4);equal(releaseCount(f),1);equal(f.request(9,N),0);equal(f.request(4,h),0);
 });
 test('finalizer-cons',()=>{const f=setup(),h=buffer(f),p=f.get(f.tcr+48);f.put(p,N);f.put(p+4,168);f.put(f.tcr+48,p+8);
  equal(watch(f,h,p+1),0);collect(f);equal(f.owner.pendingFinalizers,0);forget(f);collect(f);equal(f.request(9,N),4);});
 for(const queued of [false,true])test('finalizer-explicit-'+queued,()=>{const f=setup(),h=buffer(f);equal(watch(f,h,f.vec([N])),0);
  if(queued){forget(f);collect(f);equal(f.owner.pendingFinalizers,1);}equal(f.request(4,h),4);forget(f);collect(f);
  equal(f.owner.pendingFinalizers,0);equal(f.request(9,N),0);equal(releaseCount(f),1);});
 for(const queued of [false,true])test('finalizer-close-'+queued,()=>{const f=setup(),l=f.library(),h=f.request(3,f.vec([l,32]));equal(watch(f,h,f.vec([N])),0);
  if(queued){forget(f);collect(f);equal(f.owner.pendingFinalizers,1);}equal(f.request(1,l),0);forget(f);collect(f);
  equal(f.owner.pendingFinalizers,0);equal(f.request(9,N),0);equal(releaseCount(f),0);});
 test('finalizer-trap-cancels',()=>{const f=setup(),l=f.library(),h=f.request(3,f.vec([l,32])),r=f.request(5,f.vec([h,0]));
  equal(watch(f,h,f.vec([N])),0);forget(f);collect(f);equal(f.owner.pendingFinalizers,1);
  equal(f.call(l,'run',[r,0,8]),-8);equal(f.owner.pendingFinalizers,0);equal(f.request(9,N),0);equal(releaseCount(f),0);});
 test('finalizer-destructor-trap',()=>{const f=setup(),l=f.library(),a=f.request(3,f.vec([l,32])),b=f.request(3,f.vec([l,32]));
  equal(watch(f,a,f.vec([N])),0);equal(watch(f,b,f.vec([N])),0);forget(f);collect(f);equal(f.owner.pendingFinalizers,2);
  equal(f.call(l,'mode',[4]),0);equal(f.request(9,N),-8);equal(f.owner.pendingFinalizers,0);equal(releaseCount(f),1);equal(f.request(9,N),0);});
 test('finalizer-once',()=>{const f=setup(),h=buffer(f);equal(watch(f,h,f.vec([N])),0);equal(watch(f,h,f.vec([N])),-4);
  forget(f);collect(f);equal(f.owner.pendingFinalizers,1);equal(f.request(9,N),4);equal(releaseCount(f),1);});
 for(const [name,word] of [['nil',()=>N],['fixnum',f=>f.vec([N])-6],['truth',()=>77838],['interior',f=>f.vec([N,N,N])+8],
   ['wrong-lowtag',f=>f.vec([N])-5],['past-heap',f=>f.get(f.tcr+52)+6],['negative',()=>-2],['fraction',()=>1.5]])
  test('finalizer-object-'+name,()=>{const f=setup(),h=buffer(f),w=word(f);
   if(name==='negative'||name==='fraction')throws(()=>f.owner.atSafepoint(o=>o.registerFinalizer(w,()=>{})),/finalizer object/);
   else equal(watch(f,h,w),-4);
   equal(f.owner.pendingFinalizers,0);equal(releaseCount(f),0);equal(f.request(4,h),4);
  });
 test('finalizer-refuse-outside-boundary',()=>{const f=setup();throws(()=>f.owner.registerFinalizer(f.vec([N]),()=>{}),/legal owner boundary/);});
 test('finalizer-refuse-action',()=>{const f=setup();throws(()=>f.owner.atSafepoint(o=>o.registerFinalizer(f.vec([N]),0)),/finalizer action/);});
 test('finalizer-drain-payload',()=>{const f=setup(),h=buffer(f);equal(watch(f,h,f.vec([N])),0);forget(f);collect(f);
  equal(f.request(9,0),-4);equal(f.owner.pendingFinalizers,1);equal(f.request(9,N),4);});
 test('finalizer-drain-foreign',()=>{const f=setup(),h=buffer(f);equal(watch(f,h,f.vec([N])),0);forget(f);collect(f);
  const token=f.owner.foreignBoundary.enter('test');let error;try{f.owner.drainFinalizers();}catch(e){error=e;}
  equal(f.owner.pendingFinalizers,1,'refusal preserves queue');assert(/finalizer boundary/.test(String(error)),'drain refusal');
  equal(f.owner.pendingFinalizers,1);f.owner.foreignBoundary.leave(token);equal(f.request(9,N),4);});
 test('finalizer-drain-safepoint',()=>{const f=setup();throws(()=>f.owner.atSafepoint(o=>o.drainFinalizers()),/finalizer boundary/);});
 test('finalizer-drain-state',()=>{const f=setup();f.put(f.tcr+32,3);throws(()=>f.owner.drainFinalizers(),/finalizer thread/);equal(f.get(f.tcr+32),3);});
 test('finalizer-reentry',()=>{const f=setup();let calls=0;f.owner.atSafepoint(o=>o.registerFinalizer(f.vec([N]),()=>{calls++;throws(()=>o.drainFinalizers(),/finalizer boundary/);}));
  forget(f);collect(f);equal(f.owner.drainFinalizers(),1);equal(calls,1);});
 test('finalizer-batch',()=>{const f=setup();let calls=0;
  f.owner.atSafepoint(o=>o.registerFinalizer(f.vec([N]),()=>{calls++;o.atSafepoint(o=>o.registerFinalizer(f.vec([N]),()=>calls++));collect(f);}));
  collect(f);equal(f.owner.drainFinalizers(),1);equal(calls,1);equal(f.owner.pendingFinalizers,1);equal(f.owner.drainFinalizers(),1);equal(calls,2);});
 test('finalizer-failure-no-retry',()=>{const f=setup(),primary=Error('primary');let calls=0;
  f.owner.atSafepoint(o=>{o.registerFinalizer(f.vec([N]),()=>{calls++;throw primary;});o.registerFinalizer(f.vec([N]),()=>calls++);});
  collect(f);try{f.owner.drainFinalizers();throw Error('missing exception');}catch(e){equal(e,primary);}
  equal(calls,1);equal(f.owner.pendingFinalizers,1);equal(f.owner.drainFinalizers(),1);equal(calls,2);equal(f.owner.drainFinalizers(),0);});
 test('finalizer-async',()=>{const f=setup();f.owner.atSafepoint(o=>o.registerFinalizer(f.vec([N]),()=>({then(){}})));
  collect(f);throws(()=>f.owner.drainFinalizers(),/finalizer synchronous/);equal(f.owner.pendingFinalizers,0);equal(f.owner.drainFinalizers(),0);});
 test('finalizer-cancel',()=>{const f=setup();const ticket=f.owner.atSafepoint(o=>o.registerFinalizer(f.vec([N]),()=>{throw Error('cancelled');}));
  equal(ticket.cancel(),true);equal(ticket.cancel(),false);collect(f);equal(f.owner.drainFinalizers(),0);});
 test('finalizer-refused-collection',()=>{const f=setup();let calls=0;f.owner.atSafepoint(o=>o.registerFinalizer(f.vec([N]),()=>calls++));
  f.put(f.args+8,f.get(f.tcr+48)+6);throws(()=>collect(f),/collection refused/);equal(f.owner.pendingFinalizers,0);equal(calls,0);
  forget(f);collect(f);equal(f.owner.drainFinalizers(),1);equal(calls,1);});
 test('finalizer-inhibition',()=>{const f=setup();let calls=0;f.owner.atSafepoint(o=>o.registerFinalizer(f.vec([N]),()=>calls++));
  // Entering inhibition can relocate. Register a fresh anchor after that move.
  f.owner.atSafepoint(o=>o.inhibitCollection(1));const pending=f.owner.pendingFinalizers;
  f.owner.atSafepoint(o=>o.registerFinalizer(f.vec([N]),()=>calls++));equal(collect(f).deferred,true);
  equal(f.owner.pendingFinalizers,pending);f.owner.atSafepoint(o=>o.inhibitCollection(-1));equal(f.owner.pendingFinalizers,2);
  equal(f.owner.drainFinalizers(),2);equal(calls,2);});
 test('finalizer-cross-library-failure',()=>{const f=setup({maximumNames:2}),l=f.library(),other=f.request(0,f.str('second')),
  a=f.request(3,f.vec([l,32])),b=f.request(3,f.vec([other,32]));
  equal(watch(f,a,f.vec([N])),0);equal(watch(f,b,f.vec([N])),0);forget(f);collect(f);
  equal(f.call(l,'mode',[4]),0);equal(f.request(9,N),-8);equal(f.owner.pendingFinalizers,1);equal(releaseCount(f),1);
  equal(f.request(9,N),4);equal(releaseCount(f),2);equal(f.owner.pendingFinalizers,0);});
 test('finalizer-shared-anchor',()=>{const f=setup(),a=buffer(f),b=buffer(f),w=f.vec([N]);
  equal(watch(f,a,w),0);equal(watch(f,b,w),0);collect(f);equal(f.owner.pendingFinalizers,0);
  forget(f);collect(f);equal(f.owner.pendingFinalizers,2);equal(f.request(4,a),4);equal(f.owner.pendingFinalizers,1);
  equal(f.request(9,N),4);equal(releaseCount(f),2);});
 test('finalizer-cycle',()=>{const f=setup(),h=buffer(f),w=f.vec([N]);f.put(w-2,w);equal(watch(f,h,w),0);
  forget(f);collect(f);equal(f.owner.pendingFinalizers,1);equal(f.request(9,N),4);});
 test('finalizer-forward-query',()=>{const f=setup(),dead=f.vec([N]),live=f.vec([N,N,N]);f.put(f.args+8,live);
  collect(f);const raw=f.rawCollector(),scratch=f.layout.regions.find(r=>r.role==='scratch').start,
   before=new Uint8Array(f.memory.buffer).slice(),query=w=>raw.weak_forward(scratch,w)>>>0;
  equal(query(dead),0);equal(query(live),f.get(f.args+8));
  for(const w of [N,4,dead-6,live+8,live-5,f.get(f.tcr+48)+6])equal(query(w),0xffffffff);
  const after=new Uint8Array(f.memory.buffer);assert(before.every((v,i)=>v===after[i]),'query is read-only');
  f.put(scratch+36,1);equal(query(live),0xffffffff,'failed collection map');});

 test('finalizer-recoverable-destructor',()=>{const f=setup(),l=f.library(),a=buffer(f),b=buffer(f);
  equal(watch(f,a,f.vec([N])),0);equal(watch(f,b,f.vec([N])),0);forget(f);collect(f);
  equal(f.call(l,'mode',[8]),0);equal(f.request(9,N),-12);equal(f.owner.pendingFinalizers,1);equal(releaseCount(f),1);
  equal(f.call(l,'mode',[0]),0);equal(f.request(9,N),4);equal(releaseCount(f),2);equal(f.request(4,a),0);equal(f.request(4,b),0);});
 test('finalizer-cancel-collecting',()=>{let ticket,checked=false;const f=setup({measure(phase,run){
  if(phase==='collector.c'&&ticket){throws(()=>ticket.cancel(),/finalizer collecting/);checked=true;}return run();}});
  ticket=f.owner.atSafepoint(o=>o.registerFinalizer(f.vec([N]),()=>{}));collect(f);assert(checked,'critical section tested');
  equal(f.owner.pendingFinalizers,1);equal(f.owner.drainFinalizers(),1);});

}
