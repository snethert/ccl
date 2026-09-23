import fs from 'node:fs';
import {Worker} from 'node:worker_threads';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
const [dir,mode,imageDir,output]=process.argv.slice(2);
assert(['write','read','boot'].includes(mode));fs.mkdirSync(imageDir,{recursive:true});
const native=JSON.parse(fs.readFileSync(dir+'/compiled/native.json'));
let indices=native.flatMap((r,i)=>(mode==='boot'?r.definition==='CORE-CONDITION-OWN-TABLE':r.definition.startsWith('CORE-CONDITION-')&&r.args[0]?.graph)?[i]:[]);
assert(mode==='boot'?indices.length===1:indices.length>=45);
if(process.env.CLASS_IMAGE_CASE)indices=indices.filter(i=>native[i].definition===process.env.CLASS_IMAGE_CASE);
const codeDigest=fs.readFileSync(dir+'/class-image-code.sha256','utf8').trim();
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const manifest=fs.readFileSync(dir+'/class-image-code.json');
assert.equal(hash(manifest),codeDigest);
for(const [name,digest] of Object.entries(JSON.parse(manifest)))assert.equal(hash(fs.readFileSync(dir+'/'+name)),digest,'installed code '+name);
function run(base){return new Promise((resolve,reject)=>{
 const worker=new Worker(new URL('file://'+dir+'/image-worker.mjs'),{workerData:{
  dir,base,indices,controls:false,imageMode:mode==='write'?'write':'read',bootstrap:mode==='boot',imageDir,codeDigest}});
 worker.once('message',resolve);worker.once('error',reject);
 worker.once('exit',code=>{if(code)reject(Error('image worker exit '+code));});
});}
// Only the low placement produces bytes. Consumers run in independent Workers
// at both placements and do not receive the producer's memory or object graph.
const results=await Promise.all((mode==='write'?[8388608]:[8388608,2146500608]).map(run));
fs.writeFileSync(output,JSON.stringify({status:'PASS',mode,codeDigest,indices,
 comparisons:results.reduce((n,r)=>n+r.comparisons,0),results},null,2)+'\n');
console.log(JSON.stringify({status:'PASS',mode,cases:indices.length,comparisons:results.reduce((n,r)=>n+r.comparisons,0)}));
