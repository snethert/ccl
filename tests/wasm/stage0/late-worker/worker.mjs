import {parentPort,workerData as d} from 'node:worker_threads';
import fs from 'node:fs';
import {inspect} from '../runtime-boundary/binary.mjs';
const loader=await import(d.loader);
const table=new WebAssembly.Table({element:'anyfunc',initial:8,maximum:8});
let kernel,meta,ready=false,generation=0,installed=false;
const words=new Int32Array(d.memory.buffer),lazy=fs.readFileSync(d.lazy);
function state(){
  if(!kernel)return {ready:false,instantiated:false};
  const e=kernel.exports;
  return {ready,instantiated:true,owner:e.owner.value,tls:e.tls.value,tcr:e.tcr.value,csp:e.csp.value,vsp:e.vsp.value,generation,
    slots:Array.from({length:table.length},(_,i)=>table.get(i)===null?null:(table.get(i)(7)>>>0))};
}
function sync(){
  const g=Atomics.load(words,meta.globals.generation_word/4);
  if(!g||g===generation)return;
  if(g!==1)throw Error('CODE_GENERATION');
  const digest=Buffer.from(d.memory.buffer,meta.globals.code_record,32).toString('hex');
  if(digest!==d.lazyDigest)throw Error('PUBLICATION_DIGEST');
  if(!installed){loader.installLazy(lazy,digest,d.memory,table,d.slot,meta,d.abi,inspect);installed=true;}
  generation=g;
}
try {
  const bytes=fs.readFileSync(d.kernel);
  meta=loader.inspectKernel(bytes,d.kernelDigest,d.abi,inspect);
  kernel=loader.instantiateKernel(bytes,d.memory,table);
  parentPort.postMessage({status:'OK',value:null,state:state(),metadata:meta});
} catch(e){parentPort.postMessage({status:'ERROR',error:e.message,state:state()});}
parentPort.on('message',m=>{
  try {
    let value=null;
    if(m.op==='process')value=kernel.exports.process_once();
    else if(m.op==='setup'){
      value=kernel.exports.setup(d.id,m.base);
      if(value!==0)throw Error('PRIVATE_RANGE');
      sync();ready=true;
    } else if(m.op==='shared')kernel.exports.touch_shared(m.round);
    else if(m.op==='touch')kernel.exports.touch_private(m.token);
    else if(m.op==='install'){loader.installLazy(lazy,d.lazyDigest,d.memory,table,d.slot,meta,d.abi,inspect);installed=true;}
    else if(m.op==='sync')sync();
    else if(m.op!=='observe')throw Error('COMMAND');
    parentPort.postMessage({status:'OK',value,state:state()});
  } catch(e){parentPort.postMessage({status:'ERROR',error:e.message,state:state()});}
});
