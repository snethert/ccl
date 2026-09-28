// Real collector + owner; the synthetic B argument frame isolates admission.
import {CollectorOwner} from './runtime/collector-owner.mjs';
import {deriveLayout} from './runtime/layout.mjs';
import {openForeignModule,foreignFailure} from './runtime/foreign-module.mjs';
import {sha256} from './runtime/sha256.mjs';

export function check(binaries,{only}={}) {
 const rows=[],assert=(ok,why)=>{if(!ok)throw Error(why);};
 const equal=(a,b,why)=>assert(Object.is(a,b),why+': '+a+' != '+b);
 const test=(name,run)=>{if(only&&name!==only)return;try{run();rows.push(name);}catch(e){throw Error(name+': '+e,{cause:e});}};
 const throws=(run,pattern)=>{try{run();}catch(e){assert(pattern.test(String(e)),'wrong refusal: '+e);return e;}throw Error('missing refusal '+pattern);};
 function setup(placement=0){
  const layout=deriveLayout({spaceBytes:65536,freeTarget:0,valueStack:1048576+placement},{bootFunctions:0,runtimeFunctions:0,runtimeRootCells:0,image:[{start:77824,end:77864}]}),tcr=layout.tcr;
  const memory=new WebAssembly.Memory({initial:layout.initialPages,maximum:32769,shared:true});
  const get=p=>new DataView(memory.buffer).getUint32(p,true),put=(p,v)=>new DataView(memory.buffer).setUint32(p,v,true);
  put(77824,77825);put(77828,77825);put(77832,1850);for(let p=77836;p<77864;p+=4)put(p,77825);
  for(const [o,v] of Object.entries({...layout.tcrWords,8:1,32:2,188:77825}))put(tcr+Number(o),v);
  put(layout.runtimeGlobals,1);for(const group of layout.groups)put(group.slots[0],77825);
  const head=layout.root+40,args=head+16,base=get(tcr+48),pair=base+1;
  put(base,77825);put(base+4,168);put(tcr+48,base+8);
  put(head,layout.root);put(head+4,5);put(head+8,77825);put(head+12,77825);
  put(args,0);put(args+4,0);put(args+8,pair);put(tcr+64,args);put(tcr+128,head);
  const owner=CollectorOwner.create(memory,binaries.collector,sha256(binaries.collector),layout),boundary=owner.foreignBoundary;
  return {memory,tcr,layout,owner,boundary,get,put,head,args,pair,
   snapshot:()=>new Uint8Array(memory.buffer).slice(),
   unchanged:before=>{const after=new Uint8Array(memory.buffer);assert(before.length===after.length&&before.every((v,i)=>v===after[i]),'refusal wrote memory');}};
 }
 for(const placement of [0,65536]) {
  test('owner-return-'+placement,()=>{
   const f=setup(placement),before=f.snapshot(),token=f.boundary.enter('call');
   equal(f.get(f.tcr+32),3,'FOREIGN');equal(f.get(f.tcr+144),f.head,'root descriptor');
   f.boundary.leave(token);f.unchanged(before);
  });
  test('owner-moving-collection-'+placement,()=>{
   const f=setup(placement),token=f.boundary.enter('call');
   const result=f.owner.collectForeign();equal(f.owner.collectionCount,1,'collector count');
   equal(f.get(f.tcr+32),3,'still FOREIGN');const moved=f.get(f.args+8);
   assert(moved!==f.pair,'argument moved');
   new Uint8Array(f.memory.buffer,result.source,result.usedBytes).fill(0xa5);
   f.boundary.leave(token);equal(f.get(moved+3),168,'root reload');equal(f.get(f.tcr+144),0,'descriptor restored');
   equal(f.get(f.tcr+32),2,'RUNNING');equal(f.get(f.tcr+56),result.destination,'new allocation base');
  });
  test('owner-growth-view-'+placement,()=>{
   const f=setup(placement),token=f.boundary.enter('call');
   f.memory.grow(1);f.boundary.leave(token);equal(f.get(f.tcr+32),2,'fresh view on return');
  });
 }
 const entryRefusals=[
  ['state',f=>f.put(f.tcr+32,1),/foreign thread/],
  ['lifetime',f=>f.put(f.tcr+8,0),/foreign thread/],
  ['next-worker',f=>f.put(f.tcr+12,1280),/foreign thread/],
  ['previous-worker',f=>f.put(f.tcr+16,1280),/foreign thread/],
  ['descriptor',f=>f.put(f.tcr+144,17),/foreign descriptor/],
  ['active-request',f=>f.put(f.tcr+152,17),/foreign descriptor/],
  ['root-alignment',f=>{f.put(f.tcr+128,f.head+4);f.put(f.tcr+64,f.args+4);},/foreign root head/],
  ['root-location',f=>{f.put(f.tcr+128,0);f.put(f.tcr+64,16);},/foreign root head/],
  ['argument-head',f=>f.put(f.tcr+64,f.args+8),/foreign root head/],
  ['root-count',f=>f.put(f.head+4,1),/foreign root extent/],
  ['root-capacity',f=>f.put(f.head+4,0xffffffff),/foreign root extent/],
 ];
 for(const [name,edit,pattern] of entryRefusals)test('owner-refusal-'+name,()=>{
  const f=setup();edit(f);const before=f.snapshot();throws(()=>f.boundary.enter('call'),pattern);f.unchanged(before);
 });
 test('owner-refusal-operation',()=>{const f=setup(),before=f.snapshot();throws(()=>f.boundary.enter(null),/foreign operation/);f.unchanged(before);});
 test('owner-refusal-collect-outside',()=>{const f=setup(),before=f.snapshot();throws(()=>f.owner.collectForeign(),/foreign collection/);f.unchanged(before);});
 test('owner-refusal-nested-safepoint',()=>{const f=setup(),before=f.snapshot();f.owner.atSafepoint(()=>throws(()=>f.boundary.enter('call'),/foreign reentry/));f.unchanged(before);});
 test('owner-refusal-nested-entry',()=>{const f=setup(),token=f.boundary.enter('call'),before=f.snapshot();
  throws(()=>f.owner.foreignBoundary.enter('other-library'),/foreign reentry/);f.unchanged(before);f.boundary.leave(token);});
 test('owner-refusal-token',()=>{const f=setup(),token=f.boundary.enter('call'),before=f.snapshot();
  throws(()=>f.boundary.leave({operation:'call'}),/foreign token/);f.unchanged(before);f.boundary.leave(token);
  const after=f.snapshot();throws(()=>f.boundary.leave(token),/foreign token/);f.unchanged(after);});
 test('owner-refusal-leave-safepoint',()=>{const f=setup(),token=f.boundary.enter('call'),before=f.snapshot();
  f.owner.atSafepoint(()=>throws(()=>f.boundary.leave(token),/foreign collecting/));f.unchanged(before);f.boundary.leave(token);});
 for(const [name,offset,value,pattern] of [['state',32,2,/foreign publication/],['descriptor',144,0,/foreign publication/],['checkpoint',168,8,/foreign checkpoint/]])
  test('owner-refusal-return-'+name,()=>{const f=setup();const token=f.boundary.enter('call');f.put(f.tcr+offset,value);const before=f.snapshot();
   throws(()=>f.boundary.leave(token),pattern);f.unchanged(before);});
 test('owner-refusal-collection-state',()=>{const f=setup();f.boundary.enter('call');f.put(f.tcr+32,2);const before=f.snapshot();
  throws(()=>f.owner.collectForeign(),/foreign collection/);f.unchanged(before);});
 for(const [mode,kind] of [[0,null],[1,null],[2,'exception'],[3,'trap'],[4,'trap'],[5,'host']])test('owner-library-'+mode,()=>{
  const f=setup(),tag=new WebAssembly.Tag({parameters:['i32']}),bytes=binaries.library;
  const declaration={version:1,name:'owner-unit',sha256:sha256(bytes),policy:'per-worker',
   memory:{export:'memory',minimum:1,maximum:2},tables:[],initialization:{kind:'export',name:'initialize'},
   imports:[{module:'host',name:'collect',params:[],results:[]},{module:'host',name:'fail',params:[],results:[]}],
   exports:[{name:'initialize',params:[],results:[]},{name:'run',params:['i32','i32'],results:['i32']}]};
  const library=openForeignModule({bytes,declaration,boundary:f.boundary,errorTag:tag,
   imports:{host:{collect:()=>{const r=f.owner.collectForeign();new Uint8Array(f.memory.buffer,r.source,r.usedBytes).fill(0xa5);},fail:()=>{throw Error('host cause');}}}});
  equal(f.owner.collectionCount,1,'initializer collects');
  if(kind){let error;try{library.call('run',[mode,35]);}catch(e){error=e;}
   equal(foreignFailure(error)?.kind,kind,'converted failure');equal(library.state,kind==='trap'?'retired':'ready','retirement');}
  else equal(library.call('run',[mode,35]),42,'foreign result');
  equal(f.owner.collectionCount,mode===0?1:2,'live foreign collection');
  equal(f.get(f.tcr+32),2,'readmitted');equal(f.get(f.tcr+144),0,'descriptor restored');
  equal(f.get(f.get(f.args+8)+3),168,'moved root survived');
 });
 assert(rows.length>0,'no selected checks');return {status:'PASS',checks:rows.length,rows};
}
