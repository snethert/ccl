import {Worker} from 'node:worker_threads';
import fs from 'node:fs';
import assert from 'node:assert/strict';
const [dir,imageDir,output]=process.argv.slice(2);
const native=JSON.parse(fs.readFileSync(dir+'/compiled/native.json'));
const indices=native.flatMap((r,i)=>r.definition==='READY-START'?[i]:[]);
assert.equal(indices.length,1);
const result=await new Promise((resolve,reject)=>{
 const worker=new Worker(new URL('file://'+dir+'/ready-worker.mjs'),{workerData:{
  dir,base:8388608,indices,controls:false,imageMode:'read',imageDir,
  codeDigest:fs.readFileSync(dir+'/class-image-code.sha256','utf8').trim(),
  move:false,fault:'image-obsolete-wrapper'}});
 worker.once('message',message=>reject(Error('guard omission escaped: '+JSON.stringify(message))));
 worker.once('error',error=>resolve({reason:error.message}));
 worker.once('exit',code=>{if(!code)reject(Error('guard omission silently exited'));});
});
assert.match(result.reason,/failed generated admission published a root/);
fs.writeFileSync(output,JSON.stringify({status:'PASS',mutation:'omit READY-INITIALIZE admission',
 rejectedBy:'startup root preservation',...result},null,2)+'\n');
