import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {Worker,isMainThread,workerData,parentPort} from 'node:worker_threads';
const U32=4294967296, bytes=32769*65536;
const unsigned=n=>n<0?n+U32:n;
if(isMainThread){
 const worker=new Worker(new URL(import.meta.url),{workerData:{directory:process.argv[2]}});
 worker.on('message',r=>fs.writeFileSync(process.argv[3],JSON.stringify(r,null,2)+'\n'));
 worker.on('error',e=>{console.error(e);process.exitCode=1;});
 worker.on('exit',code=>{if(code)process.exitCode=code;});
}else{
 const dir=workerData.directory,read=n=>JSON.parse(fs.readFileSync(path.join(dir,n)));
 const memory=new WebAssembly.Memory({initial:1,maximum:32769,shared:true});
 assert.equal(memory.grow(32768),1,'real memory growth');
 const dv=new DataView(memory.buffer),slots=new WebAssembly.Table({element:'anyfunc',initial:8,maximum:8});
 const conversion_error=new WebAssembly.Tag({parameters:['i32']}),functions=new Map();
 const regions=[[0,16384],[2147483632,48],[bytes-16,16]];
 const zero=()=>{for(const [p,n]of regions)new Uint8Array(memory.buffer,p,n).fill(0);};
 const checkMemory=(words,label)=>{
  for(const [p,n]of regions){const expected=new Uint8Array(n),view=new DataView(expected.buffer);
   for(const [addr,value]of words)if(addr>=p&&addr+4<=p+n)view.setUint32(addr-p,value,true);
   assert.deepEqual(new Uint8Array(memory.buffer,p,n),expected,label+' region '+p);}
 };
 zero();
 for(const m of read('modules.json')){
  const compiled=new WebAssembly.Module(fs.readFileSync(path.join(dir,'installed',m.name+'.wasm')));
  const instance=new WebAssembly.Instance(compiled,{env:{memory,slots,conversion_error}});
  checkMemory([],'instantiation');functions.set(m.name,instance.exports.entry);
 }
 slots.set(4,functions.get('slot_target'));slots.set(5,functions.get('slot_target'));
 const observations=[];
 for(const c of read('cases.json')){
  zero();for(const [addr,value]of c.memory)dv.setUint32(addr,value,true);
  let value=null,error=0;
  assert(c.args.every(a=>Number.isInteger(a)&&a>=0&&a<U32),'host argument widths');
  try{value=unsigned(functions.get(c.function)(...c.args));}
  catch(e){assert(e instanceof WebAssembly.Exception && e.is(conversion_error),c.id+': expected checked refusal, got '+e);error=e.getArg(conversion_error,0);}
  assert.deepEqual({value,error},c.expected,c.id+': result');checkMemory(c.after,c.id+': memory');
  if(!error&&(c.function==='validate_slot'||c.function==='slot_index'))assert.equal(slots.get(value)(71),71,c.id+': checked slot dispatch');
  observations.push({id:c.id,value,error});
 }
 // A real issuance history shared by different generated module instances.
 zero();dv.setUint32(512,536870910,true);dv.setUint32(516,536870910,true);dv.setUint32(520,536870912,true);
 const history=[];
 for(let i=0;i<2;i++){const id=unsigned(functions.get('issue')(512));assert.equal(id,(536870910+i)*4,'issuance sequence');assert.equal(functions.get('id_index')(id,512),536870910+i,'issued identity');history.push(id);}
 const before=new Uint8Array(memory.buffer,512,12).slice();let exhausted=false;
 try{functions.get('issue')(512);}catch(e){assert(e instanceof WebAssembly.Exception&&e.is(conversion_error));assert.equal(e.getArg(conversion_error,0),6);exhausted=true;}
 assert(exhausted,'ID exhaustion');assert.deepEqual(new Uint8Array(memory.buffer,512,12),before,'exhaustion preserves state');
 parentPort.postMessage({status:'PASS',modules:functions.size,cases:observations,issuance:history,memory_pages:32769});
}
