// Audit 182: each new native-vector clause has a directed input. The old
// owner-created EQ-vector representation is still exercised by the parent.
{
 function nativeHash(size=3,flags=1<<30){return node(74,[0,flags,0,N,N,51,N,0,0,N,51,N,size*4,0,...Array(size*2).fill(51)]);}
 function largeSetup(){setup(196608,[A,A+196608]);layout.logCapacity=1024;owner=CollectorOwner.create(memory,bytes,digest,layout);}
 setup();put(EXTERNAL,node(74,Array(20).fill(51)));collect();pass('uninitialized-native-hash');
 for(const tracking of [true,false]){
  setup();const h=nativeHash(3,tracking?1<<30:1<<27),k=cons(43*4);
  put(h-2+14*4,k);put(h-2+15*4,cons(97*4));put(h-2+8*4,4);put(EXTERNAL,h);
  collect();const mh=get(EXTERNAL);
  assert.notEqual(get(mh-2+14*4),k);assert.equal(get(get(mh-2+14*4)+3),43*4);
  assert.equal(get(get(mh-2+15*4)+3),97*4);
  assert.equal(get(mh+2)&(1<<29),tracking?1<<29:0,'native-hash-untracked-key-movement');
  pass(tracking?'native-hash-key-movement':'native-hash-untracked-key-movement');
 }
 for(const [name,offset,value] of [
  ['weak',8,1<<14],['size',52,16],['count',36,16],['free-list',16,0],
  ['unaligned-flags',8,(1<<30)+1],['finalization-list',20,0],
  ['cache-index-limit',40,20*4],['cache-index-type',40,1],['gc-count-type',12,1],
  ['deleted-count',32,16],['deleted-count-type',32,1],['count-type',36,1],
  ['mark',24,N]
 ]){
  setup();const p=nativeHash()-6;put(p+offset,value);put(EXTERNAL,p+6);
  refused('native-hash-'+name,collect,'collection refused 2');
 }
 setup();const sum=nativeHash();put(sum-6+32,8);put(sum-6+36,8);put(EXTERNAL,sum);
 refused('native-hash-deleted-plus-count',collect,'collection refused 2');
 setup();const odd=nativeHash();put(odd-6,(21<<8)|74);put(odd-6+84,51);set(48,odd-6+88);put(EXTERNAL,odd);
 refused('native-hash-odd-cell-count',collect,'collection refused 2');
 largeSetup();put(EXTERNAL,nativeHash(16385));refused('native-hash-capacity',collect,'collection refused 2');
 largeSetup();put(EXTERNAL,nativeHash(16384));collect();pass('native-hash-maximum-capacity');
 setup();const cached=nativeHash();put(cached-6+40,19*4);put(cached-6+12,0xfffffffc);put(EXTERNAL,cached);
 collect();assert.equal(get(get(EXTERNAL)-6+40),19*4);assert.equal(get(get(EXTERNAL)-6+12),0xfffffffc);pass('native-hash-cache-and-negative-stamp');
 setup();const short=node(74,[0,1<<30,0,N,N,51,N,0,0,N,51,N,0,0]);put(EXTERNAL,short);
 refused('native-hash-minimum-cells',collect,'collection refused 2');
 setup();const truncated=nativeHash();put(truncated-6,(22<<8)|74);put(EXTERNAL,truncated);
 refused('native-hash-truncated-extent',collect,'collection refused 2');
 setup();const raw=node(74,Array(20).fill(51));put(raw+2,0);put(EXTERNAL,raw);
 refused('mixed-uninitialized-hash',collect,'collection refused 2');
 for(const [name,n] of [['minimum',14],['odd',17]]){
  setup();put(EXTERNAL,node(74,Array(n).fill(51)));refused('uninitialized-native-hash-'+name,collect,'collection refused 2');
 }
 largeSetup();put(EXTERNAL,node(74,Array(32784).fill(51)));refused('uninitialized-native-hash-maximum',collect,'collection refused 2');
 setup();const u=node(74,Array(20).fill(51));put(u-6,(22<<8)|74);put(EXTERNAL,u);
 refused('uninitialized-native-hash-extent',collect,'collection refused 2');
 // Count publication is part of the copying transaction, including empty GC.
 setup();assert.equal(owner.collectionCount,0);collect();assert.equal(owner.collectionCount,1);
 owner.atSafepoint(o=>o.ensure(8));assert.equal(owner.collectionCount,1);
 owner.atSafepoint(o=>o.growMemory(memory.buffer.byteLength/PAGE));assert.equal(owner.collectionCount,1);
 collect();assert.equal(owner.collectionCount,2);pass('collection-count-success-only');
 setup();const scalar=cons(4);set(204,scalar);const reclaimed=collect();
 assert.equal(reclaimed.reclaimed,8);assert.equal(owner.collectionCount,scalar+1);pass('collection-count-is-not-a-root');
 setup();const broken=cons(4);put(EXTERNAL,broken+8);refused('collection-count-refusal',collect,'collection refused 3');
 assert.equal(owner.collectionCount,0);put(EXTERNAL,broken);collect();assert.equal(owner.collectionCount,1);pass('collection-count-refusal-recovery');
 setup(32);let chain=N;for(let i=0;i<4;i++)chain=cons(4,chain);put(EXTERNAL,chain);
 assert(owner.atSafepoint(o=>o.ensure(64)).grown);assert.equal(owner.collectionCount,2);pass('collection-count-two-copy-growth');
 setup();set(204,536870910);collect();assert.equal(owner.collectionCount,536870911);
 refused('collection-count-exhaustion',collect,'collection count exhausted');
 setup();set(204,536870912);refused('collection-count-invalid',collect,'collection count');
 setup();collect();set(204,536870911);
 const scratch=layout.regions.find(r=>r.role==='scratch').start,before=snapshot();put(scratch+16,A);put(scratch+20,A+256);
 const service=new WebAssembly.Instance(new WebAssembly.Module(bytes),{env:{memory}}).exports;
 assert.equal(service.collect(scratch),1,'raw-collection-count-exhaustion');
 snapshot().forEach((v,i)=>assert.deepEqual(v,before[i]));pass('raw-collection-count-exhaustion');
}
