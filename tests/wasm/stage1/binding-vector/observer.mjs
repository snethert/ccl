// Called only at entry into an explicitly requested GC service or v_read.
if(currentControlCase&&m.name==='irq_gc'){
 const old=get(104),cap=get(108),target=980004+2048*relocations;
 assert(target+4*cap<1000000,'bounded evacuation destination');
 const values=Array.from({length:cap},(_,i)=>load(old+4*i));
 const before={binding:get(112),root:get(128),index:get(0)};
 store(target-4,256*cap+250);values.forEach((x,i)=>store(target+4*i,x));
 set(104,target); // raw interior TCR root; capacity is unchanged
 for(let i=0;i<cap;i++)store(old+4*i,0xdeadbeef);
 assert.deepEqual(Array.from({length:cap},(_,i)=>load(get(104)+4*i)),values,'evacuated complete binding vector');
 assert.deepEqual({binding:get(112),root:get(128),index:get(0)},before,'collector preserves other namespaces');
 movedVectors.push({capacity:cap,liveBindings:values.filter(x=>x!==243).length});relocations++;
}
if(currentControlCase&&currentControlCase.function==='v_host'&&m.name==='v_read'){
 const state=[get(104),get(108),get(112),get(128),get(0),load(get(104)+31*4)];
 assert.equal(state[5],73*4,'host suspension sees current dynamic value');
 const sync=new Int32Array(new SharedArrayBuffer(4));
 parentPort.postMessage({suspend:true,sync:sync.buffer,memory:memory.buffer,tcr,state});
 assert.equal(Atomics.wait(sync,0,0,10000),'ok','host resumes suspended Worker');
 assert.equal(Atomics.load(sync,0),1,'host acknowledged state');
 assert.deepEqual([get(104),get(108),get(112),get(128),get(0),load(get(104)+31*4)],state,'host suspension preserved bindings and roots');
 suspensions++;
}
