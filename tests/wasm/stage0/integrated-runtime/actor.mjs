import { parentPort, workerData } from 'node:worker_threads';
import { createHash } from 'node:crypto';
import { inspect } from '../runtime-boundary/binary.mjs';

const schema=workerData.schema, f=schema.tcr, q=schema.request;
const clock=()=>Number(process.hrtime.bigint())/1e6;
let memory, plan, control, kernel, emitted, program, table, id;
let events=[], pauses=[], occurrences=new Map(), installed=null,automatic=false;
function point(tcr, code, detail) {
  const occurrence=(occurrences.get(code)||0)+1; occurrences.set(code,occurrence);
  const e={id, code, detail:detail>>>0, occurrence, at_ms:clock()}; events.push(e);
  if(code===schema.events.WAITING) parentPort.postMessage({kind:'observation',event:e});
  const match=pauses.find(p=>p.code===code && (p.occurrence??1)===occurrence);
  if(match||automatic) {
    Atomics.store(control,0,0);
    parentPort.postMessage({kind:match?'point':'automatic',event:e});
    const result=Atomics.wait(control,0,0,5000);
    if(result==='timed-out') throw Error('scheduler point deadline');
  }
}
function install(address) {
  const words=new Uint32Array(memory.buffer), length=words[(address+q.length)/4];
  if(length>schema.payload_capacity) throw Error('module payload exceeds owned request storage');
  const bytes=Buffer.from(new Uint8Array(memory.buffer,address+q.payload,length));
  const digest=createHash('sha256').update(bytes).digest('hex');
  if(digest!==workerData.manifest.sha256) throw Error('lazy binary digest mismatch');
  if(installed===digest) return;
  if(!WebAssembly.validate(bytes)) throw Error('invalid lazy module');
  const m=inspect(bytes), entry=m.exports.find(e=>e.name==='entry'&&e.kind===0);
  if(m.start!==undefined||m.data.length||m.elements.length||m.imports.length!==1||!entry)
    throw Error('lazy module has unauthorized initialization/imports');
  const imported=m.imports[0];
  if(imported.module!=='env'||imported.name!=='memory'||imported.flags!==3||imported.minimum!==8||imported.maximum!==16)
    throw Error('lazy memory profile mismatch');
  if(JSON.stringify(m.types[m.functionTypes[entry.index]])!==JSON.stringify({params:['i32'],results:['i32']}))
    throw Error('lazy entry structural signature mismatch');
  const slot=workerData.manifest.slot;
  if(workerData.metadata.reservedSlots.includes(slot)) throw Error('lazy entry overlaps reserved C slot');
  const module=new WebAssembly.Instance(new WebAssembly.Module(bytes),{env:{memory}});
  table.set(slot,module.exports.entry); installed=digest;
}
function configure(data) {
  memory=data.memory; plan=data.plan; id=plan.id; control=new Int32Array(data.control);
  installed=null;
  emitted=new WebAssembly.Instance(new WebAssembly.Module(workerData.emitted));
  table=new WebAssembly.Table({initial:workerData.manifest.slot+1,element:'anyfunc'});
  kernel=new WebAssembly.Instance(new WebAssembly.Module(workerData.kernel),{
    env:{memory,__indirect_function_table:table},
    bridge:{park(){throw Error('unexpected legacy park');}},
    emitted:{raise:emitted.exports.raise}, schedule:{point},
    host:{request(tcr,address){parentPort.postMessage({kind:'request',id,address:address>>>0,at_ms:clock()});},
          callback(){program.exports.debugger();},install}
  });
  kernel.exports.__stack_pointer.value=plan.stack.end;
  kernel.exports.__wasm_init_tls(plan.tls.start);
  kernel.exports.set_tcr(plan.tcr.start);
  if(kernel.exports.get_tcr()!==plan.tcr.start) throw Error('private TLS/current TCR mismatch');
  program=new WebAssembly.Instance(new WebAssembly.Module(workerData.program),{
    env:{memory,table},kernel:kernel.exports,emitted:emitted.exports});
}
parentPort.on('message',message=>{
  try {
    if(message.kind==='configure') { configure(message); parentPort.postMessage({kind:'configured',id}); return; }
    if(message.kind!=='run') throw Error('unknown actor command');
    events=[]; pauses=message.pauses||[]; occurrences=new Map(); automatic=!!message.automatic;
    const exports=message.module==='program'?program.exports:kernel.exports;
    const result=exports[message.method](...(message.args||[]));
    const words=new Uint32Array(memory.buffer), t=plan.tcr.start;
    const snapshot=Object.fromEntries(Object.entries(f).map(([key,offset])=>[key,words[(t+offset)/4]]));
    snapshot.c_sp=kernel.exports.__stack_pointer.value;
    snapshot.values=Array.from(words.slice(snapshot.mv_base/4,snapshot.mv_base/4+snapshot.nvalues));
    snapshot.root=words[snapshot.root_slot/4];
    parentPort.postMessage({kind:'done',id,result,snapshot,events,installed});
  } catch(error) {
    parentPort.postMessage({kind:'failure',id,error:error.stack,events});
  }
});
