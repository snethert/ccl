import {openForeignModule,foreignFailure} from './runtime/foreign-module.mjs';
import {sha256} from './runtime/sha256.mjs';
import {declaration} from './declaration.mjs';
import {setup} from './setup.mjs';
export function check(binaries,{only}={}) {
 const rows=[],assert=(ok,why)=>{if(!ok)throw Error(why);};
 const equal=(a,b,why)=>assert(Object.is(a,b),why+': '+String(a)+' != '+String(b));
 const test=(name,run)=>{if(only&&name!==only)return;try{run();rows.push(name);}catch(e){throw Error(name+': '+e+(foreignFailure(e)?' CAUSE '+String(foreignFailure(e).cause)+' '+foreignFailure(e).cause?.stack:''),{cause:e});}};
 const throws=(run,pattern)=>{try{run();}catch(e){assert(pattern.test(String(e)),'wrong refusal: '+e);return e;}throw Error('missing refusal '+pattern);};
 const fixture=(placement=0,edit=()=>{})=>{
  const f=setup(binaries,placement),d=declaration(sha256(binaries.library)),errorTag=new WebAssembly.Tag({parameters:['i32']});edit(d);
  const library=openForeignModule({bytes:binaries.library,declaration:d,boundary:f.boundary,errorTag});
  return {...f,library,d,errorTag};
 };
 for(const placement of [0,65536]){
  test('moving-'+placement,()=>{
   const f=fixture(placement),count=f.owner.storage.registeredRootCells;
   const h=f.library.registerCallback('integer',f.owner,f.pair,(root,args)=>{
    equal(f.get(f.tcr+32),2,'callback RUNNING');equal(f.get(f.tcr+144),0,'descriptor cleared');
    const before=root(),m=f.owner.atSafepoint(o=>o.collect());
    new Uint8Array(f.memory.buffer,m.source,m.usedBytes).fill(0xa5);
    assert(root()!==before,'root moved');equal(f.get(root()+3),168,'root value');
    throws(()=>f.owner.collectForeign(),/foreign collection/);
    return args[0]+f.get(root()+3)/4;
   });
   equal(f.owner.storage.registeredRootCells,count+1,'registered root');
   // Only the registration holds this object alive.
   f.put(f.args+8,77825);f.owner.atSafepoint(o=>o.collect());
   equal(f.library.call('call',[h,5]),47,'callback answer');
   equal(f.library.call('alias',[h,6]),48,'alias answer');
   equal(f.get(f.tcr+32),2,'caller RUNNING');equal(f.get(f.tcr+144),0,'caller descriptor');
   equal(f.library.deregisterCallback(h),true,'deregister');equal(f.library.deregisterCallback(h),false,'idempotent');
   equal(f.owner.storage.registeredRootCells,count,'root released');
   const m=f.owner.atSafepoint(o=>o.collect());equal(m.liveBytes,0,'dead callback root reclaimed');
  });
 }
 test('scalars',()=>{
  const f=fixture();const h=f.library.registerCallback('scalars',f.owner,77825,(_,args)=>args);
  const values=[-2147483648,-9223372036854775808n,-0,1.25];
  const result=f.library.call('scalars',[h,...values]);values.forEach((v,i)=>equal(result[i],v,'scalar '+i));
  let calls=0;const v=f.library.registerCallback('void',f.owner,77825,()=>{calls++;});
  equal(f.library.call('void',[v]),undefined,'void result');equal(calls,1,'void entered');f.library.close();
 });
 test('tombstone',()=>{
  const f=fixture();let first=0,second=0;
  const a=f.library.registerCallback('integer',f.owner,77825,()=>{first++;return 11;});
  equal(f.library.call('call',[a,0]),11,'first');f.library.deregisterCallback(a);
  const b=f.library.registerCallback('integer',f.owner,77825,()=>{second++;return 22;});
  equal(f.library.call('saved',[0]),-1,'stale saved index');equal(first,1,'old not called');equal(second,0,'new not aliased');
  const before=f.snapshot();throws(()=>f.library.call('call',[a,0]),/CALLBACK_HANDLE/);f.unchanged(before);
  equal(f.library.call('call',[b,0]),22,'new handle');f.library.close();
 });
 for(const kind of ['error','exception','primitive','bad-result','async'])test('failure-'+kind,()=>{
  const f=fixture(),count=f.owner.storage.registeredRootCells;let calls=0;
  const cause=kind==='exception'?new WebAssembly.Exception(f.errorTag,[17]):kind==='primitive'?null:Error('callback cause');
  const h=f.library.registerCallback('integer',f.owner,f.pair,()=>{
   calls++;if(kind==='bad-result')return 2147483648;if(kind==='async')return Promise.resolve(3);throw cause;
  });
  const error=throws(()=>f.library.call('twice',[h,2]),kind==='async'?/.*/:/WebAssembly.Exception|wasm exception/i);
  equal(calls,1,'later callback suppressed');
  if(kind==='async'){
   assert(error instanceof AggregateError,'fatal asynchronous callback');equal(f.library.state,'retired','async retires');
   equal(f.owner.storage.registeredRootCells,count,'async releases roots');
   equal(f.get(f.tcr+32),3,'fatal leaves foreign publication');throws(()=>f.boundary.enter('after-fatal'),/foreign reentry/);
  }else{
   equal(f.library.call('after'),1,'foreign continuation ran');equal(f.get(f.tcr+32),2,'admitted before error');
   equal(foreignFailure(error)?.kind,kind==='exception'?'exception':'host','failure kind');
   if(kind!=='bad-result')equal(foreignFailure(error).cause,cause,'original cause');
   equal(f.library.state,'ready','recoverable');f.library.close();
  }
 });
 test('callback-trap',()=>{
  const f=fixture(),count=f.owner.storage.registeredRootCells;
  const h=f.library.registerCallback('integer',f.owner,f.pair,()=>{throw new WebAssembly.RuntimeError('callback trap');});
  const error=throws(()=>f.library.call('twice',[h,0]),/.*/);
  assert(error instanceof AggregateError,'callback trap must be fatal');assert(error.cause instanceof WebAssembly.RuntimeError,'original trap');
  equal(f.get(f.tcr+32),3,'fatal trap state');throws(()=>f.boundary.enter('after-fatal'),/foreign reentry/);
  equal(f.library.state,'retired','callback trap retires');equal(f.owner.storage.registeredRootCells,count,'roots released');
 });
 test('trap-primary',()=>{
  const f=fixture(),count=f.owner.storage.registeredRootCells;
  const h=f.library.registerCallback('integer',f.owner,f.pair,()=>{throw Error('secondary');});
  const error=throws(()=>f.library.call('trap',[h,0]),/WebAssembly.Exception|wasm exception/i);
  equal(foreignFailure(error)?.kind,'trap','trap stays primary');equal(f.library.state,'retired','retired');
  equal(f.owner.storage.registeredRootCells,count,'retirement releases roots');
  equal(f.library.deregisterCallback(h),false,'already retired');
 });
 test('close',()=>{
  const f=fixture(),count=f.owner.storage.registeredRootCells,h=f.library.registerCallback('integer',f.owner,f.pair,()=>1);
  f.library.close();equal(f.owner.storage.registeredRootCells,count,'close root release');
  equal(f.library.deregisterCallback(h),false,'closed deregistration');throws(()=>f.library.registerCallback('integer',f.owner,f.pair,()=>1),/RETIRED/);
 });
 test('capacity',()=>{
  const f=fixture(),handles=[];for(let i=0;i<7;i++)handles.push(f.library.registerCallback('integer',f.owner,f.pair,()=>i));
  const before=f.snapshot(),count=f.owner.storage.registeredRootCells;
  const error=throws(()=>f.library.registerCallback('integer',f.owner,f.pair,()=>9),/.*/);f.unchanged(before);
  assert(/CALLBACK_CAPACITY/.test(String(error)),'capacity refusal');
  equal(f.owner.storage.registeredRootCells,count,'no leaked root');
  f.library.deregisterCallback(handles[0]);throws(()=>f.library.registerCallback('integer',f.owner,f.pair,()=>9),/CALLBACK_CAPACITY/);f.library.close();
 });
 test('owner-hooks-snapshot',()=>{
  const f=fixture(),h=f.library.registerCallback('integer',f.owner,f.pair,()=>42),count=f.owner.storage.registeredRootCells;
  f.owner.callForeignCallback=()=>{throw Error('changed admission hook');};
  f.owner.atSafepoint=()=>{throw Error('changed safepoint hook');};
  equal(f.library.call('call',[h,0]),42,'captured admission');f.library.close();
  equal(f.owner.storage.registeredRootCells,count-1,'captured release');
 });
 test('async-owner',()=>{
  const f=fixture(),count=f.owner.storage.registeredRootCells,owner={atSafepoint:f.owner.atSafepoint.bind(f.owner),callForeignCallback:()=>Promise.resolve(7)};
  const h=f.library.registerCallback('integer',owner,f.pair,()=>{throw Error('must not run');});
  const error=throws(()=>f.library.call('call',[h,0]),/.*/);assert(error instanceof AggregateError,'asynchronous owner fatal');
  equal(f.library.state,'retired','async owner retires');equal(f.owner.storage.registeredRootCells,count,'root release');
 });
 test('growth-rollback',()=>{
  const f=fixture(),count=f.owner.storage.registeredRootCells,grow=WebAssembly.Table.prototype.grow;let calls=0;
  try{
   WebAssembly.Table.prototype.grow=function(){calls++;throw new RangeError('injected growth failure');};
   throws(()=>f.library.registerCallback('integer',f.owner,f.pair,()=>0),/injected growth failure/);
  }finally{WebAssembly.Table.prototype.grow=grow;}
  equal(calls,1,'growth attempted');equal(f.owner.storage.registeredRootCells,count,'growth rollback released root');
  const h=f.library.registerCallback('integer',f.owner,f.pair,()=>12);equal(f.library.call('call',[h,0]),12,'later registration');f.library.close();
 });
 test('affinity-type-raw',()=>{
  const a=fixture(),b=fixture(),h=a.library.registerCallback('integer',a.owner,a.pair,()=>1),other=b.library.registerCallback('integer',b.owner,b.pair,()=>2);
  const wrong=a.library.registerCallback('void',a.owner,a.pair,()=>{}),before=a.snapshot();
  for(const value of [other,wrong,1,{},null]){
   const error=throws(()=>a.library.call('call',[value,0]),/.*/);
   equal(a.library.state,'ready','refusal must not retire');a.unchanged(before);assert(/CALLBACK_HANDLE/.test(String(error)),'handle refusal');
  }
  throws(()=>b.library.deregisterCallback(h),/CALLBACK_HANDLE/);a.library.close();b.library.close();
 });
 test('root-scope',()=>{
  const f=fixture();let read;const h=f.library.registerCallback('integer',f.owner,f.pair,r=>{read=r;return 0;});
  f.library.call('call',[h,0]);throws(()=>read(),/CALLBACK_ROOT_SCOPE/);f.library.close();
 });
 test('reentry',()=>{
  const f=fixture();let h;
  h=f.library.registerCallback('integer',f.owner,f.pair,()=>{
   const before=f.snapshot();for(const run of [()=>f.library.call('after'),()=>f.library.close(),()=>f.library.deregisterCallback(h),
    ()=>f.library.registerCallback('integer',f.owner,f.pair,()=>0)]){throws(run,/REENTRY/);f.unchanged(before);}
   throws(()=>f.boundary.enter('nested'),/foreign reentry/);f.unchanged(before);return 7;
  });equal(f.library.call('call',[h,0]),7,'returned');f.library.close();
 });
 test('finalizer-drain-refusal',()=>{
  const f=fixture();let released=0;
  f.owner.atSafepoint(o=>o.registerFinalizer(f.pair,()=>{released++;}));
  f.put(f.args+8,77825);f.owner.atSafepoint(o=>o.collect());equal(f.owner.pendingFinalizers,1,'queued');
  const h=f.library.registerCallback('integer',f.owner,77825,()=>{
   const before=f.snapshot();throws(()=>f.owner.drainFinalizers(),/finalizer boundary/);f.unchanged(before);
   equal(f.owner.pendingFinalizers,1,'queue preserved');equal(released,0,'no release');return 1;
  });
  equal(f.library.call('call',[h,0]),1,'callback');equal(f.owner.drainFinalizers(),1,'later drain');equal(released,1,'released later');f.library.close();
 });
 test('pending-inhibition',()=>{
  const f=fixture();f.owner.atSafepoint(o=>o.inhibitCollection(1));
  const h=f.library.registerCallback('integer',f.owner,f.pair,root=>{
   equal(f.owner.collectionPending,true,'pending before callback');
   f.owner.atSafepoint(o=>o.inhibitCollection(-1));equal(f.owner.collectionPending,false,'pending serviced');
   equal(f.get(root()+3),168,'root after pending collection');return 42;
  });
  // Set the same synchronous pending flag that an inhibited foreign collection uses.
  const token=f.boundary.enter('pending');f.owner.collectForeign();f.boundary.leave(token);
  equal(f.library.call('call',[h,0]),42,'pending callback');f.library.close();
 });
 test('registration-refusals',()=>{
  const f=fixture(),before=f.snapshot(),count=f.owner.storage.registeredRootCells;
  throws(()=>f.library.registerCallback('absent',f.owner,f.pair,()=>0),/CALLBACK_TYPE/);
  for(const [owner,run] of [[null,()=>0],[{},()=>0],[{atSafepoint(){}},()=>0],[f.owner,null]])
   throws(()=>f.library.registerCallback('integer',owner,f.pair,run),/CALLBACK_OWNER/);
  throws(()=>f.library.registerCallback('integer',f.owner,-1,()=>0),/root values/);
  f.unchanged(before);equal(f.owner.storage.registeredRootCells,count,'no published registration');
 });
 test('wrong-owner',()=>{
  const f=fixture(),other=setup(binaries,65536),h=f.library.registerCallback('integer',other.owner,other.pair,()=>{throw Error('must not enter');});
  const before=other.snapshot().slice(other.tcr,other.tcr+256),count=other.owner.storage.registeredRootCells;
  throws(()=>f.library.call('call',[h,0]),/callback admission/);
  assert(before.every((v,i)=>v===new Uint8Array(other.memory.buffer)[other.tcr+i]),'wrong owner TCR unchanged');
  equal(other.owner.storage.registeredRootCells,count-1,'retirement drops wrong-owner root');
  equal(f.library.state,'retired','wrong owner fatal');
 });
 test('owner-action',()=>{
  const f=setup(binaries),token=f.boundary.enter('call'),before=f.snapshot();
  throws(()=>f.owner.callForeignCallback(null),/callback admission/);f.unchanged(before);f.boundary.leave(token);
 });
 test('owner-async',()=>{
  const f=setup(binaries),token=f.boundary.enter('call');
  const error=throws(()=>f.owner.callForeignCallback(()=>Promise.resolve(1)),/asynchronous callback/);
  assert(error instanceof AggregateError,'fatal async');f.boundary.leave(token);
 });
 test('failure-reset',()=>{
  const f=fixture();let calls=0;const h=f.library.registerCallback('integer',f.owner,f.pair,()=>{if(calls++===0)throw Error('first');return 7;});
  throws(()=>f.library.call('call',[h,0]),/WebAssembly.Exception|wasm exception/i);
  equal(f.library.call('call',[h,0]),7,'next entry recovered');f.library.close();
 });
 for(const type of ['void','scalars'])test('fallback-'+type,()=>{
  const f=fixture(),h=f.library.registerCallback(type,f.owner,f.pair,()=>{throw Error('cause');});
  const error=throws(()=>f.library.call(type,type==='void'?[h]:[h,1,2n,3,4]),/WebAssembly.Exception|wasm exception/i);
  equal(foreignFailure(error)?.kind,'host','valid typed fallback');equal(f.library.state,'ready','no conversion trap');f.library.close();
 });
 for(const [name,edit,pattern] of [
  ['export',()=>{},/TABLE_EXPORT/],
  ['table-type',d=>{delete d.tables[0].export;for(const c of d.callbacks)c.table=undefined;},/CALLBACK_TABLE/]
 ])test('hidden-table-'+name,()=>{
  const f=setup(binaries),bytes=binaries.hidden,d=declaration(sha256(bytes)),before=f.snapshot();edit(d);
  throws(()=>openForeignModule({bytes,declaration:d,boundary:f.boundary,errorTag:new WebAssembly.Tag({parameters:['i32']})}),pattern);f.unchanged(before);
 });
 const buffers=d=>{d.buffers={allocate:'allocate',release:'release',maximumBytes:16};};
 const refusals=[
  ['callbacks-shape',d=>d.callbacks={},/CALLBACKS/],
  ['callback-null',d=>d.callbacks.push(null),/CALLBACK_NAME/],
  ['callback-name-type',d=>d.callbacks[0].name=1,/CALLBACK_NAME/],
  ['callback-name-empty',d=>d.callbacks[0].name='',/CALLBACK_NAME/],
  ['callback-name-duplicate',d=>d.callbacks.push(d.callbacks[0]),/CALLBACK_NAME/],
  ['callback-table',d=>d.callbacks[0].table='absent',/CALLBACK_TABLE/],
  ['callback-table-type',d=>{delete d.tables[0].export;for(const c of d.callbacks)c.table=undefined;},/EXPORT_KIND/],
  ['callback-params-shape',d=>d.callbacks[0].params={},/CALLBACK_SIGNATURE/],
  ['callback-results-shape',d=>d.callbacks[0].results={},/CALLBACK_SIGNATURE/],
  ['callback-param-type',d=>d.callbacks[0].params=['externref'],/CALLBACK_SIGNATURE/],
  ['callback-result-type',d=>d.callbacks[0].results=['externref'],/CALLBACK_SIGNATURE/],
  ['callback-error-arity',d=>d.callbacks[0].error=[],/ARITY/],
  ['callback-error-type',d=>d.callbacks[0].error=['bad'],/I32/],
  ['table-export',d=>d.tables[0].export='absent',/EXPORT_KIND/],
  ['slots-shape',d=>d.exports[2].callbacks={},/CALLBACK_SLOTS/],
  ['slot-null',d=>d.exports[2].callbacks=[null],/CALLBACK_SLOT/],
  ['slot-negative',d=>d.exports[2].callbacks[0].parameter=-1,/CALLBACK_SLOT/],
  ['slot-type',d=>d.exports[2].callbacks[0].type='absent',/CALLBACK_SLOT/],
  ['slot-duplicate',d=>d.exports[2].callbacks.push(d.exports[2].callbacks[0]),/CALLBACK_SLOT/],
  ['slot-extent',d=>d.exports[2].callbacks[0].parameter=2,/CALLBACK_SLOT/],
  ['slot-scalar',d=>d.exports.find(e=>e.name==='scalars').callbacks[0].parameter=2,/CALLBACK_SLOT/],
  ['slot-managed',d=>{buffers(d);d.exports[0].callbacks=[{parameter:0,type:'integer'}];},/CALLBACK_SLOT/],
  ['slot-range-pointer',d=>{buffers(d);for(const e of d.exports.filter(e=>['call','alias'].includes(e.name)))e.ranges=[{pointer:0,length:1,access:'read',encoding:'bytes'}];},/CALLBACK_SLOT/],
  ['slot-range-length',d=>{buffers(d);for(const e of d.exports.filter(e=>['call','alias'].includes(e.name)))e.ranges=[{pointer:1,length:0,access:'read',encoding:'bytes'}];},/CALLBACK_SLOT/],
  ['slot-alias',d=>delete d.exports[3].callbacks,/CALLBACK_ALIAS/]
 ];
 for(const [name,edit,pattern] of refusals)test('admission-'+name,()=>{
  const f=setup(binaries),before=f.snapshot(),d=declaration(sha256(binaries.library));edit(d);
  if(name!=='slot-alias')d.exports[3].callbacks=structuredClone(d.exports[2].callbacks);
  throws(()=>openForeignModule({bytes:binaries.library,declaration:d,boundary:f.boundary,errorTag:new WebAssembly.Tag({parameters:['i32']})}),pattern);f.unchanged(before);
 });
 for(const [name,offset,value,pattern] of [['state',32,3,/callback publication/],['descriptor',144,17,/callback publication/],
  ['checkpoint',168,8,/callback checkpoint/],['heap',48,0,/allocation ownership/]])test('fatal-return-'+name,()=>{
  const f=fixture(),h=f.library.registerCallback('integer',f.owner,f.pair,()=>{f.put(f.tcr+offset,value);return 2;});
  const error=throws(()=>f.library.call('twice',[h,0]),/.*/);assert(error instanceof AggregateError,'fatal owner failure');
  equal(f.get(f.tcr+32),name==='state'?3:2,'refusal must not publish FOREIGN');
  throws(()=>f.boundary.enter('after-fatal'),/foreign reentry/);
  assert(pattern.test(String(error.cause)),'owner cause');equal(f.library.state,'retired','fatal retirement');
 });
 for(const offset of [8,12,16,64,76,88,116,120,124,128,132,140,148,152,156,160,164,168])test('owner-callback-checkpoint-'+offset,()=>{
  const f=setup(binaries);f.boundary.enter('call');let before;
  const error=throws(()=>f.owner.callForeignCallback(()=>{f.put(f.tcr+offset,f.get(f.tcr+offset)+8);before=f.snapshot();}),/.*/);
  f.unchanged(before);assert(error instanceof AggregateError&&/callback checkpoint/.test(String(error.cause)),'checkpoint refusal');
 });
 test('owner-outside',()=>{const f=setup(binaries),before=f.snapshot();throws(()=>f.owner.callForeignCallback(()=>0),/callback admission/);f.unchanged(before);});
 test('owner-nested',()=>{
  const f=setup(binaries),token=f.boundary.enter('call');f.owner.callForeignCallback(()=>{
   const before=f.snapshot();throws(()=>f.owner.callForeignCallback(()=>0),/callback admission/);f.unchanged(before);
  });f.boundary.leave(token);
 });
 test('owner-throw',()=>{
  const f=setup(binaries),token=f.boundary.enter('call'),cause=Error('body');
  equal(throws(()=>f.owner.callForeignCallback(()=>{throw cause;}),/body/),cause,'original');
  equal(f.get(f.tcr+32),3,'FOREIGN after throw');equal(f.get(f.tcr+144),f.head,'descriptor after throw');f.boundary.leave(token);
 });
 assert(rows.length>0,'no selected checks');return {status:'PASS',checks:rows.length,rows};
}
