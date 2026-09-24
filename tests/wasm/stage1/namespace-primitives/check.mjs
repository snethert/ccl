import fs from 'node:fs';
import assert from 'node:assert/strict';
import {Worker} from 'node:worker_threads';
import {pathToFileURL} from 'node:url';
import {manifest} from './fixtures.mjs';
const {serviceRequest}=await import(process.argv[4]?pathToFileURL(process.argv[4]):new URL('./host.mjs',import.meta.url));
import {REQUEST,SIZE,views} from './protocol.mjs';
const out=process.argv[2];
const {createNamespace}=await import(pathToFileURL(out+'/runtime/namespace.mjs'));
const expected=JSON.parse(fs.readFileSync(out+'/native.json'));
const namespace=createNamespace(manifest()),records=[];
for(const base of [8388608,2147483648])for(const movement of [false,true]) {
 const result=await new Promise((resolve,reject)=>{
  const worker=new Worker(new URL('./worker.mjs',import.meta.url),{workerData:{out,base,movement,client:process.argv[3]}});
  let memory,served=0,stale=0;
  const session=namespace.session();
  worker.on('error',reject);worker.on('exit',code=>{if(code)reject(Error('Worker exited '+code));});
  worker.on('message',message=>{
   try {
    if(message.type==='memory'){memory=message.memory;return;}
    if(message.type==='request'){
     assert.equal(new DataView(memory.buffer).getUint32(1024+32,true),3,'request in FOREIGN');
     const {generation,lifetime}=message;
     const before=new Uint8Array(memory.buffer,REQUEST,SIZE).slice();
     assert.equal(serviceRequest(memory,session,lifetime+1,generation),false);
     assert.equal(serviceRequest(memory,session,lifetime,generation-1),false);
     assert.deepEqual(new Uint8Array(memory.buffer,REQUEST,SIZE),before,'stale completion wrote');stale+=2;
     assert(serviceRequest(memory,session,lifetime,generation));served++;
     return;
    }
    if(message.type==='done'){
     assert.equal(message.requests,served);assert(stale);
     // Read-only policy intentionally differs from a writable native fd.
     assert.deepEqual(message.rows.find(r=>r.op==='write').value,[-30]);
     assert.equal(message.rows.find(r=>r.op==='open'&&r.args[2]===1).value,-30);
     const compared=message.rows.filter(r=>!['write','read-cap'].includes(r.op)&&!(r.op==='open'&&r.args[2]===1));
     assert.deepEqual(compared,expected.filter(r=>r.op!=='read-cap'),'native values and buffer post-state');
     // The native syscall can fill 8,129 bytes. The target's documented
     // descriptor bound produces a short read, preserving the unwritten tail.
     const raw=expected.find(r=>r.op==='read-cap'),capped=message.rows.find(r=>r.op==='read-cap');
     assert.deepEqual(raw.args,['large',8129]);assert.equal(raw.value[0],8129);assert.equal(raw.value[2],8129);
     assert.deepEqual(capped.value,[8128,[...raw.value[1].slice(0,8128),219],8128],'bounded read and position');
     records.push({...message,served,stale});worker.terminate();resolve();
    }
   }catch(e){worker.terminate();reject(e);}
  });
 });
}
fs.writeFileSync(out+'/execution.json',JSON.stringify({status:'PASS',records,comparisons:records.reduce((n,r)=>n+r.rows.length-3,0),bounded_reads:records.length},null,2)+'\n');
console.log('NAMESPACE-PRIMITIVES-PASS',records.length,'Workers');
