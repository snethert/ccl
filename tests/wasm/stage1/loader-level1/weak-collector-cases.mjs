// Native-shape weak vectors. Each row isolates a retention/reaping clause.
{
 const WEAK=0x4000,VALUE=0x2000,FROZEN=0x800,TRACK=1<<30,MOVED=1<<29;
 const slot=(h,i)=>h-2+4*i;
 function hash(size=3,flags=WEAK){return node(74,[0,flags,0,N,N,51,N,0,0,N,51,N,size*4,0,...Array(size*2).fill(51)]);}
 function pair(h,i,k,v){put(slot(h,14+2*i),k);put(slot(h,15+2*i),v);put(slot(h,8),get(slot(h,8))+4);}
 function row(name,fn){try{fn();pass(name);}catch(e){console.error(name);throw e;}}
 for(const valueWeak of [false,true])for(const frozen of [false,true])for(const retained of [false,true]){
  const name=`weak-${valueWeak?'value':'key'}-${frozen?'frozen':'unfrozen'}-${retained?'retained':'reaped'}`;
  row(name,()=>{
   setup();const h=hash(3,WEAK|(valueWeak?VALUE:0)|(frozen?FROZEN:0)),k=cons(41*4),v=cons(97*4);
   pair(h,0,k,v);put(EXTERNAL,h);if(retained)put(EXTERNAL+4,valueWeak?v:k);
   const source=new Uint8Array(memory.buffer,A,t(48)-A).slice(),r=collect(),mh=get(EXTERNAL);
   assert.deepEqual(new Uint8Array(memory.buffer,A,source.length),source,'source untouched');
   assert.equal(r.objects,retained?3:1,'nonweak member must not be copied before weak member lives');
   assert.equal(get(slot(mh,8)),retained?4:0,'count');
   assert.equal(get(slot(mh,7)),!retained&&!frozen?4:0,'deleted');
   assert.equal(get(slot(mh,5)),51,'weak-deletions-count remains fill marker');
   assert.equal(get(slot(mh,1))&MOVED,0,'reaping does not request rehash');
   if(retained){
    assert.notEqual(get(slot(mh,14)),k);assert.notEqual(get(slot(mh,15)),v);
    assert.equal(get(get(slot(mh,14))+3),41*4);assert.equal(get(get(slot(mh,15))+3),97*4);
   }else{assert.equal(get(slot(mh,14)),83,'deleted key');assert.equal(get(slot(mh,15)),frozen?83:N,'deleted value');}
   // Repeat after semispace reversal: no dangling old pointer, no double reap.
   collect();assert.equal(get(slot(get(EXTERNAL),8)),retained?4:0);
   assert.equal(get(slot(get(EXTERNAL),7)),!retained&&!frozen?4:0);
  });
 }
 for(const reverse of [false,true])row('weak-chain-'+(reverse?'reverse':'forward'),()=>{
  setup();const h=hash(),ka=cons(41*4),kb=cons(43*4),va=cons(97*4,kb),vb=cons(101*4);
  pair(h,reverse?1:0,ka,va);pair(h,reverse?0:1,kb,vb);put(EXTERNAL,h);put(EXTERNAL+4,ka);
  assert.equal(collect().objects,5);const mh=get(EXTERNAL);
  assert.equal(get(slot(mh,8)),8);assert.equal(get(get(slot(mh,15+(reverse?0:2)))+3),101*4);
  assert.equal(get(get(slot(mh,15+(reverse?2:0)))-1),get(slot(mh,14+(reverse?0:2))));
 });
 row('weak-self-support-cycle',()=>{
  setup();const h=hash(),k=cons(41*4),v=cons(97*4,k);pair(h,0,k,v);put(EXTERNAL,h);
  assert.equal(collect().objects,1);assert.equal(get(slot(get(EXTERNAL),14)),83);assert.equal(get(slot(get(EXTERNAL),8)),0);
 });
 row('weak-mutual-support-cycle',()=>{
  setup();const h=hash(),a=cons(41*4),b=cons(43*4);pair(h,0,a,b);pair(h,1,b,a);put(EXTERNAL,h);
  assert.equal(collect().objects,1);assert.equal(get(slot(get(EXTERNAL),8)),0);assert.equal(get(slot(get(EXTERNAL),7)),8);
 });
 row('weak-newly-discovered-vector',()=>{
  setup(512);const a=hash(),b=hash(),k=cons(41*4),dead=cons(43*4);
  pair(a,0,k,b);pair(b,0,k,cons(97*4));pair(b,1,dead,cons(101*4));put(EXTERNAL,a);put(EXTERNAL+4,k);
  assert.equal(collect().objects,4);const mb=get(slot(get(EXTERNAL),15));
  assert.equal(get(slot(mb,8)),4);assert.equal(get(slot(mb,7)),4);
  assert.equal(get(get(slot(mb,15))+3),97*4);assert.equal(get(slot(mb,16)),83);
 });
 for(const tracking of [false,true])row('weak-'+(tracking?'tracked':'untracked')+'-key-movement',()=>{
  setup();const h=hash(3,WEAK|(tracking?TRACK:0)),k=cons(41*4);pair(h,0,k,cons(97*4));put(EXTERNAL,h);put(EXTERNAL+4,k);
  collect();const mh=get(EXTERNAL);assert.notEqual(get(slot(mh,14)),k);assert.equal(get(slot(mh,1))&MOVED,tracking?MOVED:0);
 });
 row('weak-native-signed-track-mask',()=>{
  setup();const h=hash(3,WEAK|TRACK|0x80000000),k=cons(41*4);pair(h,0,k,cons(97*4));put(EXTERNAL,h);put(EXTERNAL+4,k);
  collect();const mh=get(EXTERNAL);assert.notEqual(get(slot(mh,14)),k);
  assert.equal(get(slot(mh,1)),(WEAK|TRACK|MOVED|0x80000000)>>>0);
 });
 {
  setup();const h=hash(3,WEAK|0x80000000);put(EXTERNAL,h);
  refused('weak-sign-bit-without-tracking',collect,'collection refused 2');
 }
 for(const cache of [10,11])row('weak-strong-cache-'+cache,()=>{
  setup();const h=hash(),k=cons(41*4);pair(h,0,k,cons(97*4));put(slot(h,cache),k);put(EXTERNAL,h);
  assert.equal(collect().objects,3);const mh=get(EXTERNAL);assert.equal(get(slot(mh,cache)),get(slot(mh,14)));assert.equal(get(slot(mh,8)),4);
 });
 row('weak-unreachable-vector',()=>{
  setup();const h=hash(),k=cons(41*4);pair(h,0,k,cons(97*4));const before=new Uint8Array(memory.buffer,A,t(48)-A).slice();
  assert.equal(collect().objects,0);assert.deepEqual(new Uint8Array(memory.buffer,A,before.length),before);
 });
 for(const size of [1,16384])row('weak-capacity-'+size,()=>{
  setup(size===1?256:196608,[A,size===1?B:A+196608]);layout.logCapacity=1024;owner=CollectorOwner.create(memory,bytes,digest,layout);
  const h=hash(size);pair(h,size-1,cons(41*4),cons(97*4));put(EXTERNAL,h);
  assert.equal(collect().objects,1);assert.equal(get(slot(get(EXTERNAL),14+2*(size-1))),83);assert.equal(get(slot(get(EXTERNAL),8)),0);
 });
 for(const valueWeak of [false,true])row('weak-immediates-markers-'+valueWeak,()=>{
  setup(512);const h=hash(6,WEAK|(valueWeak?VALUE:0));
  const cells=[44,48,51,51,83,N,N,T,T,N,83,83];cells.forEach((x,i)=>put(slot(h,14+i),x));put(slot(h,8),12);put(EXTERNAL,h);
  collect();const mh=get(EXTERNAL);assert.deepEqual(cells.map((_,i)=>get(slot(mh,14+i))),cells);assert.equal(get(slot(mh,8)),12);
 });
 // An immediate weak member retains its otherwise unrooted heap partner.
 for(const valueWeak of [false,true])row('weak-immediate-keeps-partner-'+valueWeak,()=>{
  setup();const h=hash(3,WEAK|(valueWeak?VALUE:0)),v=cons(97*4);pair(h,0,valueWeak?v:44,valueWeak?44:v);put(EXTERNAL,h);
  assert.equal(collect().objects,2);assert.equal(get(get(slot(get(EXTERNAL),valueWeak?14:15))+3),97*4);
 });
 for(const [name,n] of [['minimum',14],['odd',17]]){
  setup();const h=hash();put(h-6,(n<<8)|74);put(EXTERNAL,h);refused('weak-'+name+'-cells',collect,'collection refused 2');
 }
 row('weak-late-no-space-atomic',()=>{
  setup();const h=hash(),k=cons(41*4);pair(h,0,k,cons(97*4));put(EXTERNAL,h);put(EXTERNAL+4,k);
  const config=layout.regions.find(r=>r.role==='scratch').start;
  const roots=layout.regions.find(r=>r.role==='root-list').start;
  // Space for the table and rooted key, but not its deferred value.
  new Uint8Array(memory.buffer,config,96).fill(0);
  for(const [offset,value] of [[0,TCR],[16,B],[20,B+96],[68,1024],[72,roots],[76,2],[80,config+600000]])put(config+offset,value);
  put(roots,EXTERNAL);put(roots+4,EXTERNAL+4);
  const before=snapshot(),service=new WebAssembly.Instance(new WebAssembly.Module(bytes),{env:{memory}}).exports;
  assert.equal(service.collect(config),4);
  snapshot().forEach((v,i)=>assert.deepEqual(v,before[i]));
  collect();assert.equal(get(slot(get(EXTERNAL),8)),4);
 });
 // Weak flags are still illegal for hash.c's owner-created shape.
 for(const flags of [WEAK,WEAK|VALUE,0x1000]){
  setup();const h=node(74,[N,TRACK|flags,0,N,N,0,N,0,0,0xfffffffc,51,N,16,0,...Array(8).fill(51)]);put(EXTERNAL,h);
  refused('owner-hash-flags-'+flags,collect,'collection refused 2');
 }
 for(const field of [14,15])for(const kind of ['interior','unused','wrong-tag','destination']){
  setup();const h=hash(),k=cons(41*4),v=cons(97*4);pair(h,0,k,v);put(EXTERNAL,h);
  put(slot(h,field),kind==='interior'?h+8:kind==='unused'?t(48)+1:kind==='wrong-tag'?k+5:B+1);
  refused('weak-reference-'+field+'-'+kind,collect,'collection refused 3');
 }
}
