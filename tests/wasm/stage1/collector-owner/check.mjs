import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {CollectorOwner} from './owner.mjs';
const bytes=fs.readFileSync(process.argv[2]),digest=createHash('sha256').update(bytes).digest('hex');
const N=77825,T=77838,PAGE=65536,TCR=1024,ROOT=131064,EXTERNAL=262144,BINDINGS=266240,A=2097152,B=2162688;
let memory=new WebAssembly.Memory({initial:48,maximum:32769,shared:true});
let d,owner,layout;const rows=[];
const get=p=>{d=new DataView(memory.buffer);return d.getUint32(p,true);},put=(p,v)=>{d=new DataView(memory.buffer);d.setUint32(p,v,true);};
const t=o=>get(TCR+o),set=(o,v)=>put(TCR+o,v);
function setup(capacity=256,spaces=[A,B]){
 const regions=[['tcr',TCR,TCR+256],['image',77824,77864],['image',786432,786464],['vstack',ROOT,ROOT+32776],['temp',196608,212992],['control',212992,229376],['external',EXTERNAL,EXTERNAL+4096],['bindings',BINDINGS,BINDINGS+4096],['c-stack',1048576,1114112],['root-list',1180000,1184096],['scratch',1200000,1800000]].map(([role,start,end],i)=>({name:role+'-'+i,role,start,end}));
 layout={version:1,collector:'copying',workers:1,egc:false,tcr:TCR,maximumPages:32769,logCapacity:32768,regions,spaces:spaces.map((start,i)=>({name:'heap-'+i,start,end:start+capacity})),groups:['module-constants','callbacks','registry','host'].map((kind,i)=>({kind,slots:[EXTERNAL+4*i]}))};
 for(const r of [...regions,...layout.spaces])new Uint8Array(memory.buffer,r.start,r.end-r.start).fill(0);
 put(N-1,N);put(N+3,N);put(T-6,1850);for(let i=1;i<8;i++)put(T-6+4*i,N);
 // Pinned function object; its environment and literal pool are image roots.
 put(786432,1578);[4,N,4,N,N,N,0].forEach((v,i)=>put(786436+4*i,v));
 for(const g of layout.groups)for(const p of g.slots)put(p,N);
 set(48,spaces[0]);set(52,spaces[0]+capacity);set(56,spaces[0]);set(68,ROOT+8);set(72,ROOT+32776);set(64,ROOT+8);set(128,ROOT);put(ROOT,0);put(ROOT+4,0);
 set(80,196608);set(76,196608);set(84,212992);set(92,212992);set(88,212992);set(96,229376);set(104,BINDINGS);set(108,0);set(120,ROOT+8200);set(124,ROOT+8264);set(188,N);
 owner=CollectorOwner.create(memory,bytes,digest,layout);return owner;
}
function cons(car,cdr=N){const p=t(48);assert(p+8<=t(52));put(p,cdr);put(p+4,car);set(48,p+8);return p+1;}
function collect(){return owner.atSafepoint(o=>o.collect());}
function poison(from,end){new Uint8Array(memory.buffer,from,end-from).fill(0xdd);}
function pass(name,detail={}){rows.push({name,status:'PASS',...detail});}
// Each root family is the sole live path to its own object. Every other tagged
// looking scalar (including a code-ID row) must neither retain nor be updated.
setup();const slots=[...layout.groups.flatMap(g=>g.slots),TCR+188,786440,786456,T+2,T+6];
const refs=slots.map((p,i)=>{const v=cons(4*(101+i));put(p,v);return v;});
const dead=cons(999*4);put(EXTERNAL+128,dead);const oldFrom=t(56),oldEnd=t(52),r=collect();poison(oldFrom,oldEnd);
slots.forEach((slot,i)=>{assert.notEqual(get(slot),refs[i],'root family moved '+i);assert.equal(get(get(slot)+3),4*(101+i),'root family value '+i);});assert.equal(r.objects,slots.length,'precise live count');assert.equal(r.reclaimed,8,'raw metadata does not retain allocation');assert.equal(get(EXTERNAL+128),dead,'raw registry word untouched');pass('all-root-families',r);
const next=collect();slots.forEach((p,i)=>assert.equal(get(get(p)+3),4*(101+i)));pass('second-collection',next);
// Immutable admission data: later mutation of the caller's manifest cannot
// erase the roots or change the admitted region ownership.
setup();const kept=cons(431*4);put(EXTERNAL,kept);layout.groups[0].slots=[];layout.regions[0].end=0;collect();assert.equal(get(get(EXTERNAL)+3),431*4);pass('manifest-is-copied');
setup(32);cons(1*4);cons(2*4);cons(3*4);cons(4*4);const reclaim=owner.atSafepoint(o=>o.ensure(24));assert.equal(reclaim.collected,true);assert.equal(reclaim.grown,false,'retry reclaims before growth');assert.equal(t(48),t(56));pass('allocation-retry-after-reclaim',reclaim);
setup(32);let chain=N;for(let i=0;i<4;i++)chain=cons(4*(i+1),chain);put(EXTERNAL,chain);
const oldView=owner.view,oldEpoch=owner.viewEpoch,oldLength=oldView.byteLength;
const growth=owner.atSafepoint(o=>o.ensure(64));assert(growth.grown);assert.equal(t(52)-t(56),PAGE);assert.equal(owner.viewEpoch,oldEpoch+1);assert.equal(oldView.byteLength,oldLength);assert(owner.view.byteLength>oldLength);assert.notEqual(owner.view,oldView);assert.throws(()=>oldView.getUint32(oldLength,true),RangeError);let p=get(EXTERNAL);for(let i=4;i;i--){assert.equal(get(p+3),4*i);p=get(p-1);}assert.equal(p,N);assert(t(52)-t(48)>=64);collect();pass('live-growth-and-view-refresh',growth);
// Actual engine growth to the admitted maximum, then pointers above 2 GiB.
const before=owner.view,grew=owner.atSafepoint(o=>o.growMemory(32769));assert.equal(memory.buffer.byteLength,32769*PAGE);assert.equal(owner.view.byteLength,32769*PAGE);assert(before.byteLength<owner.view.byteLength);owner.view.setUint32(2147483648,0x87654321,true);assert.equal(get(2147483648),0x87654321);pass('actual-memory-maximum',grew);
setup(256,[2147483648,2147516416]);const hi=cons(443*4);put(EXTERNAL,hi);collect();assert(get(EXTERNAL)>2147483648);assert.equal(get(get(EXTERNAL)+3),443*4);pass('unsigned-high-heap');
function snapshot(){return [new Uint8Array(memory.buffer,TCR,256).slice(),new Uint8Array(memory.buffer,t(56),t(52)-t(56)).slice(),new Uint8Array(memory.buffer,EXTERNAL,4096).slice(),new Uint8Array(memory.buffer,ROOT,32768).slice()];}
function refused(name,fn,why){const before=snapshot();assert.throws(fn,new RegExp('collector-owner: '+why),name);const after=snapshot();after.forEach((v,i)=>assert.deepEqual(v,before[i],name+': preserved region '+i));pass(name,{refusal:why});}
setup();refused('outside-boundary',()=>owner.collect(),'legal owner boundary');refused('nested-boundary',()=>owner.atSafepoint(o=>o.atSafepoint(()=>0)),'nested boundary');refused('async-boundary',()=>owner.atSafepoint(()=>Promise.resolve(0)),'synchronous boundary');refused('zero-allocation',()=>owner.atSafepoint(o=>o.ensure(0)),'allocation request');refused('unaligned-allocation',()=>owner.atSafepoint(o=>o.ensure(9)),'allocation request');refused('past-memory-maximum',()=>owner.atSafepoint(o=>o.growMemory(32770)),'growth maximum');
// Re-entering after a refusal is legal; boundary state is always released.
collect();pass('recover-after-refusal');
for(const [name,damage,why] of [
 ['EGC-request',l=>l.egc=true,'collector profile'],['multiple-workers',l=>l.workers=2,'collector profile'],
 ['missing-group',l=>l.groups.pop(),'root groups'],['duplicate-group',l=>l.groups[1].kind=l.groups[0].kind,'root groups'],['unknown-group',l=>l.groups[0].kind='other','root groups'],
 ['duplicate-slot',l=>l.groups[1].slots=l.groups[0].slots,'external root slot'],['scratch-slot',l=>l.groups[0].slots=[1200000],'external root slot'],['unaligned-slot',l=>l.groups[0].slots=[EXTERNAL+1],'external root slot'],
 ['canonical-stack-overlap',l=>l.regions.find(r=>r.role==='vstack').start=77824,'regions overlap'],['missing-canonical-image',l=>l.regions=l.regions.filter(r=>r.start!==77824),'canonical object ownership'],
 ['scratch-stack-overlap',l=>l.regions.find(r=>r.role==='scratch').start=ROOT,'regions overlap'],['heaps-overlap',l=>l.spaces[1]= {...l.spaces[1],start:A},'regions overlap'],
 ['C-stack-mismatch',l=>l.regions.find(r=>r.role==='c-stack').end-=8,'compiled C stack'],['truncated-image',l=>l.regions.find(r=>r.start===786432).end-=8,'image object extent'],
 ['oversized-TCR',l=>l.tcr+=240,'TCR extent'],['small-root-list',l=>l.regions.find(r=>r.role==='root-list').end=1180008,'root-list capacity'],
 ]){setup();damage(layout);refused(name,()=>CollectorOwner.create(memory,bytes,digest,layout),why);}
setup();refused('wrong-digest',()=>CollectorOwner.create(memory,bytes,'0'.repeat(64),layout),'collector digest');
for(const [name,damage,why] of [
 ['allocation-limit',()=>set(52,t(52)+8),'allocation ownership'],['stack-base',()=>set(68,77824),'value-stack ownership'],['result-into-C-stack',()=>{set(120,1048576);set(124,1048592);},'result ownership'],['binding-into-C-stack',()=>{set(104,1048576);set(108,4);},'binding-vector ownership'],['T-header',()=>put(T-6,1578),'canonical objects'],['unknown-image-kind',()=>put(786432,258),'image kind'],
 ]){setup();damage();refused(name,collect,why);}
setup();const bad=cons(4);put(EXTERNAL,bad+8);refused('interior-heap-root',collect,'collection refused 3');
// Growth exhaustion is explicit. Collection may have committed before the
// resource refusal; all live values still have their correct current roots.
setup(16);put(EXTERNAL,cons(457*4));put(EXTERNAL+4,cons(461*4));assert.throws(()=>owner.atSafepoint(o=>o.ensure(32769*PAGE)),/heap growth maximum/);assert.equal(get(get(EXTERNAL)+3),457*4);assert.equal(get(get(EXTERNAL+4)+3),461*4);pass('heap-growth-exhaustion-preserves-live');
// Execute the real accepted compiler's B entries over owner-managed storage.
// No slow path is inserted inside generated allocation: the owner ensures space
// at the public boundary, with arguments published, then construction is atomic.
if(process.argv[4]){
 const dir=process.argv[4],native=JSON.parse(fs.readFileSync(dir+'/native.json'));
 assert.deepEqual(native.find(x=>x.id==='make').nodes,[[7,11]]);assert.deepEqual(native.find(x=>x.id==='read_pair').values,[7,11]);
 memory=new WebAssembly.Memory({initial:48,maximum:32769,shared:true});setup(16);const env={memory,tcr:TCR,table:new WebAssembly.Table({element:'anyfunc',initial:1}),tail_table:new WebAssembly.Table({element:'anyfunc',initial:1}),code_registry:0,call_error:new WebAssembly.Tag({parameters:['i32']}),type_error:new WebAssembly.Tag({parameters:['i32','i32']}),nonlocal_exit:new WebAssembly.Tag({parameters:['i32']})};
 const entries={};for(const name of ['make','read_pair']){
  const m=new WebAssembly.Module(fs.readFileSync(dir+'/installed/'+name+'.wasm')),symbols=Object.fromEntries(WebAssembly.Module.imports(m).filter(x=>x.module==='symbols').map(x=>[x.name,N]));
  entries[name]=new WebAssembly.Instance(m,{env,symbols}).exports.entry;
 }
 function call(name,args,allocation=0){
  put(ROOT,0);put(ROOT+4,args.length);args.forEach((v,i)=>put(ROOT+8+4*i,v));set(64,ROOT+8);set(128,ROOT);set(116,0);set(120,ROOT+8200);set(124,ROOT+8264);
  if(allocation)owner.atSafepoint(o=>o.ensure(allocation));
  let pair;try{pair=entries[name](786438,args.length);}catch(e){if(e instanceof WebAssembly.Exception&&e.is(env.call_error))throw new Error(name+': checked code '+e.getArg(env.call_error,0));throw e;}const [primary,count]=pair;return {primary:primary>>>0,values:Array.from({length:count},(_,i)=>get(ROOT+8200+4*i))};
 }
 for(let i=0;i<12;i++){
  const made=call('make',[28,44],8);assert.equal(made.values.length,1);put(EXTERNAL,made.primary);
  collect();const read=call('read_pair',[get(EXTERNAL)]);assert.deepEqual(read.values,native.find(x=>x.id==='read_pair').values.map(x=>x*4),'generated native values after movement');
 }
 // Keep only the published registry root; clear stale top-level argument/result
 // roots before asking for a larger allocation at this host boundary.
 put(ROOT+4,0);set(116,0);const enlarged=owner.atSafepoint(o=>o.ensure(64));assert(enlarged.grown);const after=call('read_pair',[get(EXTERNAL)]);assert.deepEqual(after.values,[28,44]);
 pass('generated-B-boundary-allocation',{allocations:12,reads:13,nativeComparisons:25});
}
// Actual engine limit can be tighter than the declared policy; refuse visibly.
memory=new WebAssembly.Memory({initial:48,maximum:48,shared:true});setup();refused('engine-growth-refusal',()=>owner.atSafepoint(o=>o.growMemory(49)),'engine growth refusal');

fs.writeFileSync(process.argv[3],JSON.stringify({status:'PASS',checks:rows.length,rows},null,2)+'\n');console.log('PASS',rows.length,'owner checks');
