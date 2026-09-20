import fs from 'node:fs';
import {Worker,isMainThread,parentPort,workerData} from 'node:worker_threads';
import {execute} from './check.mjs';
if(!isMainThread){parentPort.postMessage(execute(workerData.assets,workerData.base));}
else{
 const dir=process.argv[2],assets=Object.fromEntries(JSON.parse(fs.readFileSync(dir+'/assets.json')).map(n=>[n,Uint8Array.from(fs.readFileSync(dir+'/'+n))])),rows=[];
 for(const base of [4194304,2147483648]){
  const w=new Worker(new URL(import.meta.url),{workerData:{assets,base}});
  const exit=new Promise((resolve,reject)=>{w.once('error',reject);w.once('exit',c=>c?reject(Error('Worker exit '+c)):resolve());});
  const answer=new Promise((resolve,reject)=>{w.once('message',resolve);w.once('error',reject);});rows.push(await answer);await exit;
 }
 fs.writeFileSync(process.argv[3],JSON.stringify({status:'PASS',rows},null,2)+'\n');
}
