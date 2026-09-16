import {Worker, isMainThread, parentPort, workerData} from 'node:worker_threads';
import fs from 'node:fs';
import assert from 'node:assert/strict';
if (isMainThread) {
  const [directory,schemaFile]=process.argv.slice(2);
  const result=await new Promise((resolve,reject)=>{
    const worker=new Worker(new URL(import.meta.url),{workerData:{directory,schemaFile}});
    worker.once('message',resolve);worker.once('error',reject);
    worker.once('exit',code=>{if(code)reject(new Error(`Worker exit ${code}`));});
  });
  fs.writeFileSync(`${directory}/execution.json`,JSON.stringify(result,null,2)+'\n');
  console.log('S1-WASM-PASS');
} else {
  const {directory,schemaFile}=workerData;
  const schema=JSON.parse(fs.readFileSync(schemaFile));
  const offset=Object.fromEntries(schema.fields.map(f=>[f.name,f.offset]));
  const memory=new WebAssembly.Memory({initial:1,maximum:32769,shared:true});
  const bytes=new Uint8Array(memory.buffer);const view=new DataView(memory.buffer);
  const cases=JSON.parse(fs.readFileSync(`${directory}/generated-cases.json`));
  const tcr=256,vsp=2048,mv=4096,rows=[];
  for(const c of cases){
    bytes.fill(0x5a);
    view.setUint32(tcr+offset.vsp,vsp,true);view.setUint32(tcr+offset.mv_base,mv,true);
    view.setUint32(tcr+offset.mv_limit,mv+16,true);
    for(let i=0;i<c.args.length;i++)view.setInt32(vsp+4*i,c.args[i],true);
    const before=bytes.slice();
    const {instance}=await WebAssembly.instantiate(fs.readFileSync(`${directory}/${c.name}.wasm`),{env:{memory,tcr}});
    assert.deepEqual(bytes,before,'instantiation writes memory');
    const values=instance.exports.entry(0,c.arity);
    assert.deepEqual(values,[c.expected,c.count]);
    assert.equal(view.getInt32(mv,true),c.expected);
    assert.equal(view.getUint32(tcr+offset.mv_count,true),1);
    for(let i=0;i<bytes.length;i++)if(!(i>=mv&&i<mv+4)&&!(i>=tcr+offset.mv_count&&i<tcr+offset.mv_count+4))assert.equal(bytes[i],before[i],`unexpected write ${i}`);
    rows.push({name:c.name,args:c.args,values});
  }
  parentPort.postMessage({status:'PASS',worker_count:1,cases:rows,scope:'Generated nonallocating leaf registration smoke; no full ABI, GC, or condition qualification.'});
}
