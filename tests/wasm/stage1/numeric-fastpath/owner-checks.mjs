// Appended to the accepted owner's independent state/preservation checks.
// Fast assurance still checks mutable state. Image scanning occurs on admission
// and copying, never on a sufficient-space assurance.
memory=new WebAssembly.Memory({initial:48,maximum:32769,shared:true});
for(const [name,damage,why] of [
 ['fast-allocation-limit',()=>set(52,t(52)+8),'allocation ownership'],
 ['fast-allocation-cursor',()=>set(48,t(48)+1),'allocation ownership'],
 ['fast-stack-base',()=>set(68,77824),'value-stack ownership'],
 ['fast-temp-cursor',()=>set(76,0),'temp-stack ownership'],
 ['fast-control-cursor',()=>set(88,0),'control-stack ownership'],
 ['fast-result-extent',()=>{set(120,1048576);set(124,1048592);},'result ownership'],
 ['fast-binding-extent',()=>{set(104,1048576);set(108,4);},'binding-vector ownership'],
 ['fast-binding-capacity',()=>set(108,0xffffffff),'binding-vector shape'],
 ['fast-T-header',()=>put(T-6,1578),'canonical objects'],
 ['fast-NIL-car',()=>put(N+3,0),'canonical objects'],
 ]){setup();damage();refused(name,()=>owner.atSafepoint(o=>o.ensure(8)),why);}
setup();const scans=owner.testImageScans;
for(let i=0;i<1000;i++)assert.deepEqual(owner.atSafepoint(o=>o.ensure(8)),{collected:false,grown:false});
assert.equal(owner.testImageScans,scans,'fast assurance must not enumerate the image');pass('no-image-scan-on-fast-assurance',{assurances:1000});
// Mutable pinned fields are read anew at collection; there is no cached list of
// root values or object shapes. Corruption is refused before the first write.
const kept2=cons(123*4);put(786440,kept2);collect();assert.equal(get(get(786440)+3),123*4);
assert.equal(owner.testImageScans,scans+1,'one inventory per collection');pass('collection-reinventories-image');
setup();put(786432,258);assert.deepEqual(owner.atSafepoint(o=>o.ensure(8)),{collected:false,grown:false});
refused('damaged-image-at-copy',collect,'image kind');
setup();put(786432,258);set(48,t(52));refused('damaged-image-at-shortage',()=>owner.atSafepoint(o=>o.ensure(8)),'image kind');
setup();let big=cons(47*4);put(EXTERNAL,big);const epoch=owner.viewEpoch;
owner.atSafepoint(o=>o.ensure(65536));assert(owner.viewEpoch>epoch);assert.equal(get(get(EXTERNAL)+3),47*4);
assert.deepEqual(owner.atSafepoint(o=>o.ensure(8)),{collected:false,grown:false});pass('fast-assurance-after-growth');
