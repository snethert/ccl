import fs from 'node:fs';
import {Worker} from 'node:worker_threads';
import assert from 'node:assert/strict';

const [dir,planFile,output]=process.argv.slice(2);
const plan=JSON.parse(fs.readFileSync(planFile));
assert(Number.isInteger(plan.workers)&&plan.workers>=1&&plan.workers<=16);
const jobs=[];
for(const base of [8388608,2146500608]){
  const partitions=Array.from({length:plan.workers},()=>[]);
  plan.indices.forEach((index,i)=>partitions[i%plan.workers].push(index));
  for(const indices of partitions)if(indices.length)jobs.push({base,indices,controls:false});
  if(plan.controls)jobs.push({base,indices:plan.controlIndices,controls:true});
}
const results=Array(jobs.length);let next=0;
async function consume(){
  while(next<jobs.length){
    const index=next++,job=jobs[index];
    results[index]=await new Promise((resolve,reject)=>{
      let result,received=false;
      const worker=new Worker(new URL('./worker.mjs',import.meta.url),{workerData:{dir,...job}});
      worker.on('message',value=>{assert(!received,'multiple worker results');result=value;received=true;});
      worker.on('error',reject);
      worker.on('exit',code=>code||!received?reject(Error('worker failed '+code)):resolve({...result,controls:job.controls}));
    });
  }
}
await Promise.all(Array.from({length:Math.min(plan.workers,jobs.length)},consume));
const rows=results.filter(x=>!x.controls).flatMap(x=>x.rows.map(row=>({...row,base:x.base})));
rows.sort((a,b)=>a.caseId.localeCompare(b.caseId)||a.base-b.base||Number(a.moved)-Number(b.moved));
assert.equal(rows.length,plan.indices.length*4);
assert.equal(new Set(rows.map(r=>[r.caseId,r.base,r.moved].join(':'))).size,rows.length);
fs.writeFileSync(output,JSON.stringify({status:'PASS',rows,workers:plan.workers,
  comparisons:rows.length,collections:results.filter(x=>!x.controls).reduce((n,r)=>n+r.collections+r.internalCollections,0),
  controls:results.filter(x=>x.controls)},null,2)+'\n');
