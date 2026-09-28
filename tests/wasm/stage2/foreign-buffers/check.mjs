import {CollectorOwner} from './runtime/collector-owner.mjs';
import {deriveLayout} from './runtime/layout.mjs';
import {openForeignModule,foreignFailure} from './runtime/foreign-module.mjs';
import {sha256} from './runtime/sha256.mjs';
import {declaration} from './declaration.mjs';

export function check(binaries,{only}={}) {
 const rows=[],assert=(ok,why)=>{if(!ok)throw Error(why);};
 const equal=(a,b,why='equality')=>assert(Object.is(a,b),why+': '+a+' != '+b);
 const test=(name,run)=>{if(only&&name!==only)return;try{run();rows.push(name);}catch(e){throw Error(name+': '+e,{cause:e});}};
 const throws=(run,pattern)=>{try{run();}catch(e){assert(pattern.test(String(e)),'wrong refusal: '+e);return e;}throw Error('missing refusal '+pattern);};
 const data=new TextEncoder().encode('Aé🌍\0'),sum=data.reduce((a,b)=>a+b,0);
 function setup({placement=0,encoding='bytes',access='readwrite',edit=()=>{},onCollect=()=>{},beforeEnter=()=>{}}={}){
  const layout=deriveLayout({spaceBytes:65536,freeTarget:0,valueStack:1048576+placement},{bootFunctions:0,runtimeFunctions:0,runtimeRootCells:0,image:[{start:77824,end:77864}]}),tcr=layout.tcr;
  const memory=new WebAssembly.Memory({initial:layout.initialPages,maximum:32769,shared:true});
  const get=p=>new DataView(memory.buffer).getUint32(p,true),put=(p,v)=>new DataView(memory.buffer).setUint32(p,v,true);
  put(77824,77825);put(77828,77825);put(77832,1850);for(let p=77836;p<77864;p+=4)put(p,77825);
  for(const [o,v] of Object.entries({...layout.tcrWords,8:1,32:2,188:77825}))put(tcr+Number(o),v);
  put(layout.runtimeGlobals,1);for(const group of layout.groups)put(group.slots[0],77825);
  const head=layout.root+40,args=head+16,base=get(tcr+48);
  put(base,data.length*256+199);new Uint8Array(memory.buffer,base+4,data.length).set(data);put(tcr+48,base+16);
  put(head,layout.root);put(head+4,5);put(head+8,77825);put(head+12,77825);
  put(args,0);put(args+4,0);put(args+8,base+6);put(tcr+64,args);put(tcr+128,head);
  const owner=CollectorOwner.create(memory,binaries.collector,sha256(binaries.collector),layout),raw=owner.foreignBoundary;
  const entries=[],events=[],moves=[];let active=false;
  const boundary={enter(op){const refusal=beforeEnter(op);if(refusal)return refusal;equal(active,false);equal(get(tcr+32),2);const token=raw.enter(op);active=true;entries.push(op);return token;},
   leave(token){equal(active,true);raw.leave(token);equal(get(tcr+32),2);active=false;}};
  const imports={host:{collect(){equal(active,true);const before=get(args+8),r=owner.collectForeign();
   assert(get(args+8)!==before,'source moved');new Uint8Array(memory.buffer,r.source,r.usedBytes).fill(0xa5);
   moves.push(r);onCollect();},observe(kind,pointer){equal(active,true);events.push({kind,pointer});}}};
  const d=declaration(sha256(binaries.library),encoding,access);edit(d);
  let library;
  const open=()=>library=openForeignModule({bytes:binaries.library,declaration:d,imports,boundary,errorTag:new WebAssembly.Tag({parameters:['i32']})});
  const source=()=>{equal(active,false,'copy while admitted');return new Uint8Array(memory.buffer,get(args+8)-2,data.length);};
  return {open,get library(){return library;},entries,events,moves,source,owner,sourceWord:()=>get(args+8)};
 }
 const failure=(run,kind)=>{let caught;try{run();}catch(e){caught=e;}equal(foreignFailure(caught)?.kind,kind,'converted failure');return caught;};
 for(const placement of [0,65536])test('copy-moving-growth-'+placement,()=>{
  const f=setup({placement,encoding:'utf-8'}),l=f.open(),before=f.sourceWord(),h=l.allocate(16);
  assert(f.sourceWord()!==before,'allocation moved Lisp source');
  l.write(h,4,f.source());const r=l.range(h,4);equal(l.call('run',[r,data.length,3]),sum);
  equal(new TextDecoder().decode(l.read(h,4,data.length)),'Aé🌍\0','fresh foreign view after growth');
  const copy=l.read(h,4,data.length);copy.fill(0);equal(l.call('run',[r,data.length,0]),sum,'read is a copy');
  const source=f.source();l.write(h,4,source);source.fill(0);equal(l.call('run',[r,data.length,0]),sum,'write is a copy');
  equal(l.release(h),true);equal(l.release(h),false);equal(l.call('releases'),1,'free once');equal(f.moves.length,5,'allocator/calls/free collect');
  equal(f.entries[1],'allocate:allocate');equal(f.entries.at(-2),'release:release');
 });
 test('offset-reuse',()=>{
  const f=setup(),l=f.open(),h=l.allocate(16),old=l.range(h);l.release(h);const newer=l.allocate(16);
  equal(f.events[0].pointer,f.events[2].pointer,'allocator reuses offset');
  throws(()=>l.read(h,0,1),/HANDLE/);throws(()=>l.write(h,0,data),/HANDLE/);throws(()=>l.range(h),/HANDLE/);
  throws(()=>l.call('run',[old,1,0]),/HANDLE/);equal(l.release(h),false);l.write(newer,0,data);equal(l.call('run',[l.range(newer),data.length,0]),sum);
 });
 test('cross-library-handles',()=>{const a=setup().open(),b=setup().open(),h=a.allocate(16);
  throws(()=>b.range(h),/HANDLE/);throws(()=>b.release(h),/HANDLE/);throws(()=>b.call('run',[a.range(h),1,0]),/RANGE_HANDLE/);});
 test('close-retires',()=>{const f=setup(),l=f.open(),h=l.allocate(16);l.close();const count=f.entries.length;
  equal(l.release(h),false);equal(f.entries.length,count);throws(()=>l.read(h,0,1),/RETIRED/);throws(()=>l.call('run',[l.range(h),1,0]),/RETIRED/);});
 for(const [mode,kind] of [[1,'exception'],[2,'trap']])test('call-failure-'+kind,()=>{
  const f=setup(),l=f.open(),h=l.allocate(16),other=l.allocate(16);l.write(h,0,data);
  const error=failure(()=>l.call('run',[l.range(h),data.length,mode]),kind),count=f.entries.length;
  equal(l.release(h),kind==='exception');equal(l.release(other),kind==='exception');
  equal(f.entries.length,count+(kind==='exception'?2:0),'release policy');
  equal(foreignFailure(error).kind,kind,'primary failure unchanged');equal(l.state,kind==='trap'?'retired':'ready');
 });
 for(const [mode,kind] of [[6,'trap'],[7,'exception']])test('release-failure-'+kind,()=>{
  const f=setup(),l=f.open(),a=l.allocate(16),b=l.allocate(16);l.call('mode',[mode]);
  failure(()=>l.release(a),kind);const count=f.entries.length;equal(l.release(a),false,'uncertain release never retried');
  if(kind==='trap'){equal(l.release(b),false);equal(f.entries.length,count,'no second destructor');}
  else {l.call('mode',[0]);equal(l.release(b),true);equal(l.call('releases'),2);}
 });
 for(const [mode,kind] of [[4,'exception'],[5,'trap']])test('allocate-failure-'+kind,()=>{
  const f=setup(),l=f.open();l.call('mode',[mode]);failure(()=>l.allocate(16),kind);equal(l.state,kind==='trap'?'retired':'ready');
  equal(f.events.length,0,'no published allocation');
 });
 for(const mode of [1,2,3])test('allocator-result-'+mode,()=>{
  const f=setup(),l=f.open(),old=l.allocate(16);l.call('mode',[mode]);throws(()=>l.allocate(16),/ALLOCATION_RESULT/);
  equal(l.state,'retired');equal(l.release(old),false);equal(f.events.filter(e=>e.kind===1).length,0,'no unsafe free');
 });
 for(const name of ['allocate','allocate-alias','release','release-alias'])test('managed-'+name,()=>{
  const f=setup(),l=f.open(),n=f.entries.length;throws(()=>l.call(name,[16]),/MANAGED_EXPORT/);equal(f.entries.length,n);
 });
 const declarationRefusals=[
  ['buffer-type',d=>d.buffers.maximumBytes='16',/BUFFER_LIMIT/],
  ['buffer-negative',d=>d.buffers.maximumBytes=-1,/BUFFER_LIMIT/],
  ['buffer-fraction',d=>d.buffers.maximumBytes=0.5,/BUFFER_LIMIT/],
  ['buffer-overflow',d=>d.buffers.maximumBytes=2147483648,/BUFFER_LIMIT/],
  ['allocate-absent',d=>d.buffers.allocate='absent',/BUFFER_ABI/],
  ['release-absent',d=>d.buffers.release='absent',/BUFFER_ABI/],
  ['range-null',d=>d.exports.at(-1).ranges=[null],/RANGE_SIGNATURE/],
  ['range-string-index',d=>d.exports.at(-1).ranges[0].pointer='0',/RANGE_SIGNATURE/],
  ['range-length-index',d=>d.exports.at(-1).ranges[0].length=3,/RANGE_SIGNATURE/],
  ['buffer-limit',d=>d.buffers.maximumBytes=0,/BUFFER_LIMIT/],
  ['allocate-abi',d=>d.buffers.allocate='release',/BUFFER_ABI/],
  ['release-abi',d=>d.buffers.release='allocate',/BUFFER_ABI/],
  ['ranges-array',d=>d.exports.at(-1).ranges={},/RANGES/],
  ['range-no-buffers',d=>delete d.buffers,/RANGE_EXPORT/],
  ['range-managed',d=>d.exports.find(e=>e.name==='allocate').ranges=[{pointer:0,length:1,access:'read',encoding:'bytes'}],/RANGE_EXPORT/],
  ['range-same',d=>d.exports.at(-1).ranges[0].length=0,/RANGE_SIGNATURE/],
  ['range-index',d=>d.exports.at(-1).ranges[0].pointer=3,/RANGE_SIGNATURE/],
  ['range-negative',d=>d.exports.at(-1).ranges[0].pointer=-1,/RANGE_SIGNATURE/],
  ['range-duplicate',d=>d.exports.at(-1).ranges.push({...d.exports.at(-1).ranges[0]}),/RANGE_SIGNATURE/],
  ['range-access',d=>d.exports.at(-1).ranges[0].access='guess',/RANGE_FORMAT/],
  ['range-encoding',d=>d.exports.at(-1).ranges[0].encoding='utf-16',/RANGE_FORMAT/],
  ['range-alias',d=>d.exports.at(-1).ranges=[],/RANGE_ALIAS/],
 ];
 for(const [name,edit,pattern] of declarationRefusals)test('declare-'+name,()=>{const f=setup({edit});throws(()=>f.open(),pattern);equal(f.entries.length,0,'refuse before publication');});
 for(const [name,run,pattern] of [
  ['zero',l=>l.allocate(0),/ALLOCATION_SIZE/],['negative',l=>l.allocate(-1),/ALLOCATION_SIZE/],
  ['fraction',l=>l.allocate(1.5),/ALLOCATION_SIZE/],['limit',l=>l.allocate(65537),/ALLOCATION_SIZE/],
  ['unknown',(l,h)=>l.range({}),/HANDLE/],['offset',(l,h)=>l.range(h,17),/BUFFER_RANGE/],
  ['write-overflow',(l,h)=>l.write(h,15,data),/BUFFER_RANGE/],['read-overflow',(l,h)=>l.read(h,15,2),/BUFFER_RANGE/],
  ['read-negative',(l,h)=>l.read(h,-1,1),/BUFFER_RANGE/],['read-large',(l,h)=>l.read(h,0,2147483648),/BUFFER_RANGE/],
  ['read-fraction',(l,h)=>l.read(h,0,0.5),/BUFFER_RANGE/],['raw-pointer',(l,h)=>l.call('run',[65528,1,0]),/RANGE_HANDLE/],
  ['call-overflow',(l,h)=>l.call('run',[l.range(h,15),2,0]),/BUFFER_RANGE/],
  ['call-negative',(l,h)=>l.call('run',[l.range(h),-1,0]),/BUFFER_RANGE/],
  ['arity',(l,h)=>l.call('run',[l.range(h),1]),/ARITY/],
  ['scalar',(l,h)=>l.call('run',[l.range(h),1,'0']),/I32/],
 ])test('refuse-'+name,()=>{const f=setup(),l=f.open(),h=l.allocate(16),before=f.entries.length;
  const bytes=l.read(h,0,16);throws(()=>run(l,h),pattern);equal(f.entries.length,before,'no entry');
  equal(String(l.read(h,0,16)),String(bytes),'refusal preserves bytes');
 });
 test('no-buffer-profile',()=>{const f=setup({edit:d=>{delete d.buffers;for(const e of d.exports)delete e.ranges;}}),l=f.open();
  const n=f.entries.length;throws(()=>l.allocate(1),/BUFFERS/);equal(f.entries.length,n);});
 test('write-output-only',()=>{const l=setup({encoding:'utf-8',access:'write'}).open(),h=l.allocate(16);
  // Invalid prior content is allowed for a declared output; the call replaces it.
  l.write(h,0,new Uint8Array([0xff]));equal(l.call('run',[l.range(h),1,5]),0);equal(l.read(h,0,1)[0],0);
 });
 test('readwrite-utf8-output',()=>{const l=setup({encoding:'utf-8'}).open(),h=l.allocate(16);l.write(h,0,data);
  throws(()=>l.call('run',[l.range(h),data.length,4]),/UTF8/);equal(l.release(h),true);});
 test('zero-range',()=>{const l=setup().open(),h=l.allocate(16);l.write(h,16,new Uint8Array());equal(l.read(h,16,0).length,0);equal(l.call('run',[l.range(h,16),0,0]),0);});
 test('utf8-input',()=>{const f=setup({encoding:'utf-8'}),l=f.open(),h=l.allocate(16);l.write(h,0,new Uint8Array([0xff]));const n=f.entries.length;
  throws(()=>l.call('run',[l.range(h),1,0]),/UTF8/);equal(f.entries.length,n,'validate before foreign entry');});
 test('utf8-output',()=>{const f=setup({encoding:'utf-8',access:'write'}),l=f.open(),h=l.allocate(16);l.write(h,0,data);
  throws(()=>l.call('run',[l.range(h),data.length,4]),/UTF8/);equal(l.state,'ready');equal(l.release(h),true);});
 test('utf8-read-access',()=>{const l=setup({encoding:'utf-8',access:'read'}).open(),h=l.allocate(16);l.write(h,0,data);
  equal(l.call('run',[l.range(h),data.length,0]),sum);});
 test('reentry-copies-release',()=>{
  let l,h,range,calls=0;const f=setup({onCollect(){if(!h)return;
   for(const action of [()=>l.allocate(1),()=>l.range(h),()=>l.write(h,0,data),()=>l.read(h,0,1),()=>l.release(h),()=>l.close(),()=>l.call('run',[range,1,0])]){
    throws(action,/REENTRY/);calls++;
   }}});l=f.open();h=l.allocate(16);range=l.range(h);l.call('run',[range,0,0]);equal(calls,7);
  equal(l.read(h,0,1).length,1,'handle survives refused release');equal(l.release(h),true);equal(l.call('releases'),1);
 });
 test('async-entry-live-handles',()=>{
  let refuse=false;const f=setup({beforeEnter(){if(refuse)return Promise.resolve();}}),l=f.open(),a=l.allocate(16),b=l.allocate(16),range=l.range(a);
  const count=f.entries.length;refuse=true;throws(()=>l.call('run',[range,0,0]),/ASYNC_BOUNDARY/);
  equal(l.state,'retired');equal(l.release(a),false);equal(l.release(b),false);equal(f.entries.length,count,'no destructor after async owner');
 });
 test('release-entry-refusal',()=>{
  let refuse=false;const f=setup({beforeEnter(op){if(refuse&&op==='release:release')throw Error('entry denied');}}),l=f.open(),h=l.allocate(16);
  refuse=true;throws(()=>l.release(h),/entry denied/);equal(l.state,'ready');equal(l.release(h),false);equal(l.call('releases'),0);throws(()=>l.range(h),/HANDLE/);
 });
 assert(rows.length>0,'no selected checks');return {status:'PASS',checks:rows.length,rows};
}
