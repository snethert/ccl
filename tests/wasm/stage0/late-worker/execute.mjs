import fs from 'node:fs';
import path from 'node:path';
import {Worker} from 'node:worker_threads';
import {pathToFileURL} from 'node:url';
import {gzipSync} from 'node:zlib';
const [bundle,configPath,out]=process.argv.slice(2);
const config=JSON.parse(fs.readFileSync(configPath)),abi=JSON.parse(fs.readFileSync(path.join(bundle,'abi.json')));
const manifest=JSON.parse(fs.readFileSync(path.join(bundle,'manifest.json')));
const memory=new WebAssembly.Memory({initial:1,maximum:1,shared:true}),bytes=new Uint8Array(memory.buffer),words=new Int32Array(memory.buffer);
for(let i=0;i<bytes.length;i++)bytes[i]=(i*17+31)%256;
Atomics.store(words,8,0);Atomics.store(words,12,0);
const actors=[],leases=new Set(),rows=[],snapshots=[];
function wait(w){return new Promise((resolve,reject)=>{
  const finish=(fn,value)=>{clearTimeout(timer);w.off('message',ok);w.off('error',bad);w.off('exit',exit);fn(value);};
  const ok=v=>finish(resolve,v),bad=e=>finish(reject,e),exit=n=>bad(Error('WORKER_EXIT '+n));
  const timer=setTimeout(()=>bad(Error('WORKER_TIMEOUT')),10000);
  w.once('message',ok);w.once('error',bad);w.once('exit',exit);
});}
function record(name,result){
  snapshots.push(Buffer.from(bytes));
  rows.push({name,result,snapshot:rows.length});
  if(result.status==='ERROR')throw Object.assign(Error(result.error),{expectedCapture:true});
}
async function spawn(index){
  const id=config.case==='duplicate-owner'&&index===2?1:index;
  if(leases.has(id)){record('instance-'+index,{status:'ERROR',error:'OWNER_ALREADY_ASSIGNED',state:{ready:false,instantiated:false}});return;}
  leases.add(id);
  const variant=index===2&&manifest.attackKernel?'attack-kernel.wasm':'kernel.wasm';
  const loader=index===2&&manifest.attackLoader?'attack-loader.mjs':'loader.mjs';
  const w=new Worker(new URL('./worker.mjs',import.meta.url),{workerData:{
    id,memory,abi,slot:manifest.slot,kernel:path.join(bundle,variant),kernelDigest:config.case==='wrong-digest'&&index===2?'0'.repeat(64):manifest.files[variant],
    loader:pathToFileURL(path.join(bundle,loader)).href,lazy:path.join(bundle,'lazy.wasm'),lazyDigest:manifest.files['lazy.wasm']}});
  actors[index]=w;record('instance-'+index,await wait(w));
}
async function call(id,name,m){const w=actors[id],answer=wait(w);w.postMessage(m);record(name,await answer);}
let failure=null;
try{
  await spawn(0);await call(0,'process-0',{op:'process'});await call(0,'setup-0',{op:'setup',base:4096});
  await spawn(1);await call(1,'setup-1',{op:'setup',base:4608});
  await call(0,'shared-1',{op:'shared',round:1});
  await call(0,'touch-0',{op:'touch',token:0x11220000});await call(1,'touch-1',{op:'touch',token:0x11220001});
  // Installation completes before the process publishes the digest/generation.
  await call(0,'install-0',{op:'install'});
  bytes.set(Buffer.from(manifest.files['lazy.wasm'],'hex'),224);Atomics.store(words,12,1);
  record('publish',{status:'OK',value:1,state:null});
  await call(0,'sync-0',{op:'sync'});
  await call(1,'sync-1',{op:'sync'});
  await call(0,'shared-2',{op:'shared',round:2});
  await spawn(2);await call(2,'setup-2',{op:'setup',base:config.case==='wrong-private-base'?4608:5120});
  await call(2,'retry-process-2',{op:'process'});await call(2,'touch-2',{op:'touch',token:0x11220002});
  await call(0,'shared-3',{op:'shared',round:3});
  await spawn(3);await call(3,'setup-3',{op:'setup',base:5632});
  for(let id=0;id<4;id++)await call(id,'observe-'+id,{op:'observe'});
}catch(e){failure=e.message;if(!e.expectedCapture)throw e;}
finally{
  await Promise.all(actors.map(w=>w?.terminate()));
  fs.writeFileSync(path.join(out,'memory.bin.gz'),gzipSync(Buffer.concat(snapshots)));
  fs.writeFileSync(path.join(out,'observed.json'),JSON.stringify({version:1,case:config.case,node:process.version,rows,failure},null,2)+'\n');
}
