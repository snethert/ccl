import {parentPort,workerData as data} from 'node:worker_threads';
import {validateCode,sha} from './loader.mjs';
const {runtime,schema,kernel:kernelBytes,emitted:emittedBytes,slots,candidate,options}=data;
const f={...runtime.tcr,...schema.tcr},q=runtime.request,s=schema.state;
let memory,words,plan,kernel,abi,table,wrong,control;
let installed=new Map(),events=[],requests=[],lookupLog=[];
const word=p=>Atomics.load(words,p/4)>>>0;
const state=n=>word(plan.state.start+s[n]);
function lookup(code,path) {
  const e=slots.entries.find(e=>e.code===code);if(!e)throw Error('UNKNOWN_CODE_ID');
  const role=path===2?'adapter':path===1?'direct':'G';
  let slot=e[role];
  if(options?.wrongRole&&path===0) {slot=slots.wrong;if(!options.bypassRole)throw Error('ROLE_MISMATCH');}
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
  const instance=new WebAssembly.Instance(new WebAssembly.Module(record.bytes),{env:{memory,table},kernel:kernel.exports,abi:abi.exports,loader:{lookup}});
  const descriptor=slots.entries.find(e=>e.code===code);
  for(const role of ['G','direct','adapter'])table.set(descriptor[role],instance.exports[role]);
  installed.set(code,instance);events.push({kind:'installed',code,sha256:sha(record.bytes)});
}
function configure(m) {
  memory=m.memory;words=new Int32Array(memory.buffer);plan=m.plan;control=new Int32Array(m.control);
  installed=new Map();events=[];requests=[];lookupLog=[];
  const emitted=new WebAssembly.Instance(new WebAssembly.Module(emittedBytes));
  table=new WebAssembly.Table({initial:slots.minimum,element:'anyfunc'});
  kernel=new WebAssembly.Instance(new WebAssembly.Module(kernelBytes),{env:{memory,__indirect_function_table:table},bridge:{park(){throw Error('legacy park');}},
    emitted:emitted.exports,schedule:{point(tcr,code,detail){
      events.push({kind:'schedule',code,detail:detail>>>0});
      if(code===runtime.events.WAITING)parentPort.postMessage({kind:'waiting',id:plan.id});
    }},host:{
      request(tcr,address){requests.push(address);parentPort.postMessage({kind:'request',id:plan.id,address:address>>>0,lazy_code:state('lazy_code')});},
      callback(){abi.exports.debugger();},
      install(address){const length=word(address+q.length);if(length>192)throw Error('INSTALL_PAYLOAD_BOUNDS');const payload=new Uint8Array(memory.buffer,address+q.payload,length);install(new DataView(payload.buffer,payload.byteOffset,payload.byteLength).getUint32(0,true),payload);}
    }});
  kernel.exports.__stack_pointer.value=plan.stack.end;kernel.exports.__wasm_init_tls(plan.tls.start);kernel.exports.set_tcr(plan.tcr.start);
  kernel.exports.abi_setup(plan.state.start,plan.abi.start,plan.abi.end,plan.replies.start,plan.replies.end);
  abi=new WebAssembly.Instance(new WebAssembly.Module(candidate.support),{env:{memory,table},kernel:kernel.exports,emitted:emitted.exports,loader:{lookup}});
  const stub=new WebAssembly.Instance(new WebAssembly.Module(candidate.stub),{env:{memory,table},kernel:kernel.exports,abi:abi.exports,loader:{lookup}});
  wrong=new WebAssembly.Instance(new WebAssembly.Module(candidate.wrong),{env:{memory,table}});
  table.set(slots.wrong,wrong.exports.entry);table.set(slots.wrong+1,wrong.exports.signature);
  for(const e of slots.entries) {
    table.set(e.G,options?.nullStub?null:stub.exports.G);table.set(e.direct,stub.exports.G);table.set(e.adapter,stub.exports.adapter);
    if(!(options?.lazyCodes||[]).includes(e.code))install(e.code);
  }
}
function snapshot() {
  return {tcr:Object.fromEntries(Object.entries(f).map(([n,off])=>[n,word(plan.tcr.start+off)])),
    state:Object.fromEntries(Object.entries(s).map(([n,off])=>[n,word(plan.state.start+off)])),
    c_sp:kernel.exports.__stack_pointer.value,entered:wrong.exports.entered?.value,events,requests,lookup:lookupLog};
}
parentPort.on('message',m=>{
  try {
    if(m.kind==='configure'){configure(m);parentPort.postMessage({kind:'configured',id:plan.id});return;}
    events=[];requests=[];lookupLog=[];
    let result;
    if(m.kind==='collect')result=kernel.exports.collect_and_park();
    else if(m.kind==='probe')result=wrong.exports.probe(3.5);
    else if(m.kind==='redefine')result=abi.exports.redefine();
    else if(m.kind==='start')result=abi.exports.start(...m.args);
    else if(m.kind==='wasm_layout')result=abi.exports.layout(...m.args);
    else if(m.kind==='layout') {
      kernel.exports.admit();const p=m.args[0];
      result=[kernel.exports.abi_car(p),kernel.exports.abi_cdr(p),kernel.exports.abi_car(65),kernel.exports.abi_cdr(65)];
      if(m.args[1]){kernel.exports.abi_rplaca(p,124);kernel.exports.abi_rplacd(p,(-36)>>>0);}kernel.exports.park();
    } else throw Error('unknown ABI actor command');
    parentPort.postMessage({kind:'done',id:plan.id,result,snapshot:snapshot()});
  } catch(error) {parentPort.postMessage({kind:'failure',id:plan?.id,error:error.stack,snapshot:plan&&kernel&&wrong?snapshot():null});}
});
