import fs from 'node:fs';
import {Worker} from 'node:worker_threads';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
const [dir,mode,imageDir,output]=process.argv.slice(2);
assert(['write','read'].includes(mode));fs.mkdirSync(imageDir,{recursive:true});
const native=JSON.parse(fs.readFileSync(dir+'/compiled/native.json'));
const indices=native.flatMap((r,i)=>r.definition==='READY-START'?[i]:[]);assert.equal(indices.length,1);
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const codeDigest=fs.readFileSync(dir+'/class-image-code.sha256','utf8').trim();
const manifest=fs.readFileSync(dir+'/class-image-code.json');assert.equal(hash(manifest),codeDigest);
for(const [name,digest]of Object.entries(JSON.parse(manifest)))assert.equal(hash(fs.readFileSync(dir+'/'+name)),digest,name);
function run(base,move,fault){return new Promise((resolve,reject)=>{
 const worker=new Worker(new URL('file://'+dir+'/ready-worker.mjs'),{workerData:{dir,base,indices,
  controls:false,imageMode:mode,imageDir:fault==='no-image'?imageDir+'/absent':imageDir,codeDigest,move,fault}});
 worker.once('message',resolve);worker.once('error',reject);
 worker.once('exit',code=>{if(code)reject(Error('READY Worker exit '+code));});
});}
const results=[];
// Each boot gets one fresh Worker, one memory, one process-owner claim.
for(const base of mode==='write'?[8388608]:[8388608,2146500608])
 for(const move of mode==='write'?[false]:[false,true])results.push(await run(base,move));
const refusals=[];
if(mode==='read')for(const fault of ['no-image','no-entry','early-ready','native-table-gethash','native-table-puthash','native-table-remhash','native-table-clrhash']){
 const result=await run(8388608,false,fault);
 assert.equal(result.rejected,fault);assert.equal(result.state,3);
 assert.match(result.reason,fault==='no-image'?/ENOENT/:fault==='no-entry'?/READY_ENTRY_REQUIRED/:fault==='early-ready'?/published last/:/checked [0-9]+$/);
 refusals.push(result);
}
fs.writeFileSync(output,JSON.stringify({status:'PASS',mode,codeDigest,results,refusals,
 comparisons:results.reduce((n,r)=>n+r.comparisons,0)},null,2)+'\n');
console.log(JSON.stringify({status:'PASS',mode,boots:results.length,refusals}));
