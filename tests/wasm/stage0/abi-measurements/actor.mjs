import {parentPort,workerData as data} from 'node:worker_threads';
import assert from 'node:assert/strict';
import {validateCode,validateDriver,sha,Roles} from './loader.mjs';
const {runtime,schema,kernel:kernelBytes,emitted:emittedBytes,slots,candidate,options}=data;
const f={...runtime.tcr,...schema.tcr},q=runtime.request,s=schema.state;
let memory,words,plan,kernel,abi,table,wrong,control,roles,registry,driver,schedule,measuring=false;
let cold=[],publicationSeen=null;
let installed=new Map(),events=[],requests=[],lookupLog=[];
const word=p=>Atomics.load(words,p/4)>>>0;
const state=n=>word(plan.state.start+s[n]);
function lookup(code,path) {
  const e=slots.entries.find(e=>e.code===code);if(!e)throw Error('UNKNOWN_CODE_ID');
  const role=path===2?'adapter':path===1?'direct':'G';
  let slot=e[role];
  if(options?.wrongRole&&path===0) {slot=slots.wrong;if(!options.bypassRole)roles.resolve(slot,code,role);}
  if(options?.wrongSignature&&path===0)slot=slots.wrong+1;
  if(options?.oldVersionAlias&&code===10)slot=slots.entries.find(e=>e.code===11)[role];
  lookupLog.push({code,role,slot});return slot;
}
function install(code,payload) {
  const record=candidate.modules.find(m=>m.code===code);if(!record||(options?.missingModule&&code===10))throw Error('MISSING_CODE_MODULE');
  if(payload) {
    if(payload.length!==36||new DataView(payload.buffer,payload.byteOffset,payload.byteLength).getUint32(0,true)!==code)throw Error('INSTALL_REQUEST_IDENTITY');
    if(Buffer.from(payload.subarray(4)).toString('hex')!==record.sha256)throw Error('INSTALL_REQUEST_DIGEST');
  }
  if(installed.has(code))return;
  const expected=options?.badHash&&code===10?{...record,sha256:'0'.repeat(64)}:record;
  validateCode(record.bytes,expected,candidate.k,slots.minimum);
  const began=performance.now(),module=candidate.packaging==='cross-instance'?new WebAssembly.Module(record.bytes):null,compiled=performance.now();
  const instance=candidate.packaging==='cross-instance'
    ? new WebAssembly.Instance(module,{env:{memory,table},kernel:kernel.exports,abi:abi.exports,loader:{lookup:resolvedLookup}}) : driver;
  cold.push({code,compile_ms:compiled-began,instantiate_ms:performance.now()-compiled,
    instantiated:candidate.packaging==='cross-instance',sha256:sha(record.bytes)});
  const descriptor=slots.entries.find(e=>e.code===code);
  roles.publish(code,['G','direct','adapter'].map(role=>[descriptor[role],role,instance.exports[role+(candidate.packaging==='cross-instance'?'':code)]]));
  installed.set(code,instance);events.push({kind:'installed',code,sha256:sha(record.bytes)});
}
let resolvedLookup;
function compile(bytes,label,imports={}) {
  const began=performance.now(),module=new WebAssembly.Module(bytes),compiled=performance.now();
  const instance=new WebAssembly.Instance(module,imports);
  cold.push({label,sha256:sha(bytes),compile_ms:compiled-began,instantiate_ms:performance.now()-compiled});
  return instance;
}
function configure(m) {
  memory=m.memory;words=new Int32Array(memory.buffer);plan=m.plan;control=new Int32Array(m.control);
  installed=new Map();events=[];requests=[];lookupLog=[];cold=[];
  const emitted=compile(emittedBytes,'emitted');
  table=new WebAssembly.Table({initial:slots.minimum,element:'anyfunc'});
  roles=new Roles(table,slots);
  registry=compile(candidate.registry,'registry',{guard:{fail(){throw Error('UNKNOWN_CODE_OR_ROLE');}}});
  // Normal calls enter a Wasm lookup function. Deliberate controls retain their injected path.
  resolvedLookup=(options.wrongRole||options.wrongSignature||options.oldVersionAlias)?lookup:registry.exports.lookup;
  schedule=compile(candidate.schedule,'schedule',{host:{point(tcr,code,detail){
    events.push({kind:'schedule',code,detail:detail>>>0});
    if(code===runtime.events.WAITING)parentPort.postMessage({kind:'waiting',id:plan.id});
  }}});
  kernel=compile(kernelBytes,"kernel",{env:{memory,__indirect_function_table:table},bridge:{park(){throw Error('legacy park');}},
    emitted:emitted.exports,schedule:schedule.exports,host:{
      request(tcr,address){if(measuring)throw Error('HOST_REQUEST_INSIDE_BATCH');requests.push(address);parentPort.postMessage({kind:'request',id:plan.id,address:address>>>0,lazy_code:state('lazy_code')});},
      callback(){if(measuring)throw Error('HOST_CALLBACK_INSIDE_BATCH');abi.exports.debugger();},
      install(address){const length=word(address+q.length);if(length>192)throw Error('INSTALL_PAYLOAD_BOUNDS');const payload=new Uint8Array(memory.buffer,address+q.payload,length);install(new DataView(payload.buffer,payload.byteOffset,payload.byteLength).getUint32(0,true),payload);}
    }});
  kernel.exports.__stack_pointer.value=plan.stack.end;kernel.exports.__wasm_init_tls(plan.tls.start);kernel.exports.set_tcr(plan.tcr.start);
  kernel.exports.abi_setup(plan.state.start,plan.abi.start,plan.abi.end,plan.replies.start,plan.replies.end);
  abi=compile(candidate.support,"support",{env:{memory,table},kernel:kernel.exports,emitted:emitted.exports,loader:{lookup:resolvedLookup}});
  validateDriver(candidate.driver,options.badDriverHash?'0'.repeat(64):candidate.driverSha256,candidate.k,slots,candidate.packaging);
  driver=compile(candidate.driver,'driver',{env:{memory,table},kernel:kernel.exports,abi:abi.exports,loader:{lookup:resolvedLookup}});
  table.set(slots.wrong+2,driver.exports.dispatch);
  const stub=compile(candidate.stub,"stub",{env:{memory,table},kernel:kernel.exports,abi:abi.exports,loader:{lookup:resolvedLookup}});
  wrong=compile(candidate.wrong,"wrong-role-control",{env:{memory,table}});
  table.set(slots.wrong,wrong.exports.entry);table.set(slots.wrong+1,wrong.exports.signature);
  for(const e of slots.entries) {
    roles.publish(e.code,[[e.G,'G',stub.exports.G],[e.direct,'direct',stub.exports.G],[e.adapter,'adapter',stub.exports.adapter]]);
    if(options?.nullStub)table.set(e.G,null);
    if(!(options?.lazyCodes||[]).includes(e.code))install(e.code);
  }
}
function snapshot() {
  return {tcr:Object.fromEntries(Object.entries(f).map(([n,off])=>[n,word(plan.tcr.start+off)])),
    state:Object.fromEntries(Object.entries(s).map(([n,off])=>[n,word(plan.state.start+off)])),
    c_sp:kernel.exports.__stack_pointer.value,entered:wrong.exports.entered?.value,events,requests,lookup:lookupLog,cold,publication:publicationSeen};
}
parentPort.on('message',m=>{
  try {
    if(m.kind==='configure'){configure(m);parentPort.postMessage({kind:'configured',id:plan.id,cold,memory:process.memoryUsage()});return;}
    events=[];requests=[];lookupLog=[];
    let result;
    if(m.kind==='collect')result=kernel.exports.collect_and_park();
    else if(m.kind==='probe')result=wrong.exports.probe(3.5);
    else if(m.kind==='redefine')result=abi.exports.redefine();
    else if(m.kind==='start')result=abi.exports.start(...m.args);
    else if(m.kind==='publish') {
      const record=candidate.modules.find(e=>e.code===m.args[0]);assert.ok(record,'MISSING_PREBUILT_CODE');
      validateCode(record.bytes,record,candidate.k,slots.minimum);
      const p=plan.publication.start;assert.equal(Atomics.load(words,p/4),0,'PUBLICATION_ALREADY_SET');
      words[p/4+1]=record.code;
      new Uint8Array(memory.buffer,p+8,32).set(Buffer.from(record.sha256,'hex'));
      Atomics.store(words,p/4,1);result={generation:1,code:record.code,sha256:record.sha256};
    }
    else if(m.kind==='published-start') {
      const p=plan.publication.start,generation=Atomics.load(words,p/4);
      assert.equal(generation,1,'UNPUBLISHED_CODE');
      const code=words[p/4+1],record=candidate.modules.find(e=>e.code===code);
      assert.ok(record,'UNKNOWN_PUBLICATION_CODE');
      const digest=Buffer.from(new Uint8Array(memory.buffer,p+8,32)).toString('hex');
      assert.equal(digest,record.sha256,'PUBLICATION_DIGEST');
      publicationSeen={generation,code,sha256:digest,previously_installed:installed.has(code)};
      result=abi.exports.start(schema.entries.findIndex(e=>e.code===code),m.args[1],m.args[2]);
    }
    else if(m.kind==='batch') {
      roles.checkAll();
      assert.equal(installed.size,schema.entries.length,'TIMING_REQUIRES_EAGER_INSTALLATION');
      schedule.exports.quiet(1);measuring=true;
      const began=performance.now();result=driver.exports.batch(...m.args);const elapsed_ms=performance.now()-began;
      measuring=false;schedule.exports.quiet(0);
      assert.equal(requests.length,0,'HOST_REQUEST_INSIDE_BATCH');
      parentPort.postMessage({kind:'done',id:plan.id,result,elapsed_ms,snapshot:snapshot()});return;
    }
    else if(m.kind==='corrupt-role') {
      const e=slots.entries[0];table.set(e.G,table.get(e.direct));roles.checkAll();
    }
    else if(m.kind==='wasm_layout')result=abi.exports.layout(...m.args);
    else if(m.kind==='layout') {
      kernel.exports.admit();const p=m.args[0];
      result=[kernel.exports.abi_car(p),kernel.exports.abi_cdr(p),kernel.exports.abi_car(65),kernel.exports.abi_cdr(65)];
      if(m.args[1]){kernel.exports.abi_rplaca(p,124);kernel.exports.abi_rplacd(p,(-36)>>>0);}kernel.exports.park();
    } else throw Error('unknown ABI actor command');
    parentPort.postMessage({kind:'done',id:plan.id,result,snapshot:snapshot()});
  } catch(error) {parentPort.postMessage({kind:'failure',id:plan?.id,error:error.stack,snapshot:plan&&kernel&&wrong?snapshot():null});}
});
