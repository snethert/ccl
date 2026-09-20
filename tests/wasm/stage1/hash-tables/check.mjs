import fs from 'node:fs';
import assert from 'node:assert/strict';
import {Worker,isMainThread,parentPort,workerData} from 'node:worker_threads';
if(isMainThread){
 const rows=[];for(const base of [262144,2147483648])rows.push(await new Promise((resolve,reject)=>{const w=new Worker(new URL(import.meta.url),{workerData:{base,dir:process.argv[2],generated:process.argv[4]==='generated'}});w.on('message',resolve);w.on('error',reject);w.on('exit',c=>{if(c)reject(Error('Worker '+c));});}));
 fs.writeFileSync(process.argv[3],JSON.stringify({status:'PASS',rows},null,2)+'\n');
}else{
 const {base,dir}=workerData,read=n=>JSON.parse(fs.readFileSync(dir+'/'+n));
 const memory=new WebAssembly.Memory({initial:Math.max(64,Math.ceil((base+65536)/65536)),maximum:32769,shared:true});
 const d=new DataView(memory.buffer),get=p=>d.getUint32(p,true),put=(p,v)=>d.setUint32(p,v,true),NIL=77825,T=77838,EMPTY=243,MOVED=2**29;
 const service=(await WebAssembly.instantiate(fs.readFileSync(dir+'/hash.wasm'),{env:{memory}})).instance.exports;
 const collector=(await WebAssembly.instantiate(fs.readFileSync(dir+'/collector.wasm'),{env:{memory}})).instance.exports;
 const tcr=1024,root=131064,config=1200000,hashScratch=1900000,result=2048000,space2=3145728,size=32768;
 let table,checks=[],moves=[],observations=[];
 const generated=workerData.generated?await (await import('./generated.mjs')).install({dir,memory,tcr,get,put,service,scratch:hashScratch,scratchEnd:hashScratch+131072,result,collector,config}):null;
 function setup(capacity=64){
  new Uint8Array(memory.buffer,tcr,256).fill(0);new Uint8Array(memory.buffer,config,96).fill(0);
  new Uint8Array(memory.buffer,base,size).fill(0xcd);new Uint8Array(memory.buffer,space2,size).fill(0xa5);
  put(tcr+48,base);put(tcr+52,base+size);put(tcr+56,base);put(tcr+68,root+8);put(tcr+72,196608);put(tcr+128,root);
  put(root,0);put(root+4,0);put(tcr+80,700000);put(tcr+76,700000);put(tcr+84,900000);
  put(tcr+120,100000);put(tcr+124,100064);put(tcr+104,610000);put(tcr+108,0);
  put(config,tcr);put(config+16,space2);put(config+20,space2+size);put(config+68,32768);put(config+72,1180000);put(config+76,0);put(config+80,1800000);
  const p=get(tcr+48),n=service.ht_size(capacity);assert(n);assert.equal(service.ht_init(p,p+n,capacity),0,'create');put(tcr+48,p+n);table=p+6;
 }
 function cons(car=28,cdr=NIL){const p=get(tcr+48);put(p,cdr);put(p+4,car);put(tcr+48,p+8);return p+1;}
 function roots(values){put(root+4,values.length);values.forEach((v,i)=>put(root+8+4*i,v));}
 function invoke(op,key=NIL,value=NIL){
  if(generated)return generated.invoke(op,table,key,value);
  const n=(get(table-6)>>>8)-14,end=table-6+64+n*4;
  const code=service.ht_run(table,end,op,key,value,hashScratch,hashScratch+131072,result);
  assert.equal(code,0,'operation status');const out=Array.from({length:4},(_,i)=>get(result+4*i));assert.equal(out[2],op===0?2:1);return out;
 }
 function collect(label,{moved=true}={}){
  const before=get(tcr+56),old=Array.from({length:get(root+4)},(_,i)=>get(root+8+4*i));
  const cached=[get(table+38),get(table+42)];
  put(config+16,before===base?space2:base);put(config+20,get(config+16)+size);
  assert.equal(collector.collect(config),0,label+': collection');table=get(root+8);
  const after=Array.from({length:get(root+4)},(_,i)=>get(root+8+4*i));
  assert.notEqual(table,old[0],label+': table moved');
  for(let j=0;j<2;j++)if(cached[j]>=before&&cached[j]<before+size&&[1,6].includes(cached[j]%8)){const v=get(table+38+j*4);assert(v>=get(tcr+56)&&v<get(tcr+48),j?'cached value relocated':'cached key relocated');}
  if(moved)assert.equal(get(table+2)&MOVED,MOVED,label+': moved-key notification');
  else assert.equal(get(table+2)&MOVED,0,label+': values alone must not request rehash');
  moves.push({label,from:before,to:get(tcr+56),before:old,after,live:get(config+84),reclaimed:get(config+92)});
  // Old payload is poisoned before any lookup: stale references cannot pass.
  new Uint8Array(memory.buffer,before,size).fill(0xda);
 }
 setup();let keys=Array.from({length:40},()=>cons()).concat([NIL,T,0,0xfffffffc]);roots([table,...keys]);
 const trace=read('trace.json'),native=read('native.json');assert.equal(trace.length,native.length);
 let round=0;
 for(let i=0;i<trace.length;i++){
  const [op,k,v]=trace[i];let actual;
  const identity=x=>{const at=keys.indexOf(x);assert(at>=0,'result identity '+i+' '+x);return at;};
  if(op==='gc'){
   const liveKeys=get(table+30)/4; // object word 9
   collect('trace-'+round++,{moved:liveKeys!==0});keys=keys.map((_,j)=>get(root+12+4*j));actual=[-1];
  }else if(op==='set'){actual=[identity(invoke(1,keys[k],keys[v])[0])];}
  else if(op==='get'){const row=invoke(0,keys[k],keys[v]);actual=[identity(row[0]),row[1]===T?1:0];}
  else if(op==='del'){actual=[invoke(2,keys[k])[0]===T?1:0];}
  else actual=[invoke(3)[0]/4];
  assert.deepEqual(actual,native[i],'native trace '+i+' '+op);observations.push(actual);
 }
 checks.push('native-trace');
 // Cached replacement and deletion after rehash must address the new bucket.
 setup();keys=Array.from({length:25},()=>cons());roots([table,...keys]);
 keys.forEach((k,i)=>invoke(1,k,4*i));invoke(0,keys[7]);let oldIndex=get(table+34);
 collect('cached-replacement');keys=keys.map((_,j)=>get(root+12+4*j));
 invoke(1,keys[7],3996);assert.equal(invoke(3)[0],100,'replacement count');
 for(let i=0;i<keys.length;i++)assert.equal(invoke(0,keys[i])[0],i===7?3996:4*i,'replacement after rehash '+i);
 invoke(0,keys[7]);assert.notEqual(get(table+34),oldIndex,'cache witness changes physical bucket');assert.equal(invoke(2,keys[7])[0],T);assert.deepEqual(invoke(0,keys[7],NIL).slice(0,2),[NIL,NIL],'deleted cache misses');checks.push('cached-replacement-delete');
 // Value-only movement cannot set the key flag; both entry and cache hold it.
 setup();let value=cons(44);invoke(1,NIL,value);invoke(0,NIL);roots([table]);collect('value-only',{moved:false});value=invoke(0,NIL)[0];assert.equal(get(value+3),44,'cached value relocated');assert.equal(invoke(3)[0],4);checks.push('value-only-cache');
 // A table may be its own key/value; two equal cons keys remain distinct.
 setup();const a=cons(),b=cons();invoke(1,a,b);invoke(1,b,a);invoke(1,table,table);roots([table]);collect('cycles');assert.equal(invoke(0,table)[0],table,'table self key');assert.equal(invoke(3)[0],12);let pairs=[];for(let i=0;i<64;i++){const p=table-6+60+i*8,k=get(p);if(k!==EMPTY&&k!==251&&k!==table)pairs.push([k,get(p+4)]);}assert.equal(pairs.length,2);assert.equal(pairs[0][0],pairs[1][1]);assert.equal(pairs[1][0],pairs[0][1]);assert.notEqual(pairs[0][0],pairs[1][0]);checks.push('table-only-root-cycle');
 // Full table, tombstone reuse, NIL-valued presence, and exact object extent.
 setup(4);roots([table]);for(let i=0;i<4;i++)invoke(1,i*4,NIL);
 const preserved=()=>Buffer.from(new Uint8Array(memory.buffer,table-6,service.ht_size(4))).toString('hex');
 let before=preserved();new Uint8Array(memory.buffer,result,16).fill(0x51);
 assert.equal(service.ht_run(table,table-6+96,1,16,28,hashScratch,hashScratch+32,result),4,'full refusal');assert.equal(preserved(),before);assert(new Uint8Array(memory.buffer,result,16).every(x=>x===0x51));
 assert.deepEqual(invoke(0,0).slice(0,2),[NIL,T]);invoke(2,4);invoke(1,16,28);assert.equal(invoke(3)[0],16);assert.equal(invoke(0,16)[0],28);checks.push('full-and-tombstones');
 if(generated){
  setup();let k=cons();roots([table,k]);
  assert.deepEqual(generated.moving('hash_gc',table,k),read('compiled/native-moving.json')[0],'generated locals and table survive collection');
  table=get(root+8);k=get(root+12);
  put(config+16,base);put(config+20,base+size);
  assert.deepEqual(generated.moving('hash_gc_values',table,k),read('compiled/native-moving.json')[1],'cached pending values survive collecting cleanup');
  table=get(root+8);assert.equal(invoke(3)[0],4);checks.push('collection-inside-generated-code');
  // Return to the four-bucket layout used by interface refusal controls.
  setup(4);roots([table]);for(let i=0;i<4;i++)invoke(1,i*4,NIL);
 }
 // Checked interface refusals preserve table and publication.
 const refusals=[];
 for(const [name,args,code] of [
  ['tag',[table+1,table-6+96,0,0,0,hashScratch,hashScratch+32,result],2],
  ['extent',[table,table-6+104,0,0,0,hashScratch,hashScratch+32,result],2],
  ['short-scratch',[table,table-6+96,0,0,0,hashScratch,hashScratch+24,result],1],
  ['overlap',[table,table-6+96,0,0,0,table-6,table-6+32,result],1],
  ['result-overlap',[table,table-6+96,0,0,0,hashScratch,hashScratch+32,table-6],1],
  ['bad-operation',[table,table-6+96,4,0,0,hashScratch,hashScratch+32,result],5],
  ['sentinel',[table,table-6+96,0,EMPTY,0,hashScratch,hashScratch+32,result],3],
 ]){const b=preserved(),r=Buffer.from(new Uint8Array(memory.buffer,result,16));assert.equal(service.ht_run(...args),code,name);assert.equal(preserved(),b,name);assert.deepEqual(Buffer.from(new Uint8Array(memory.buffer,result,16)),r,name);refusals.push({name,code});}
 // Collector shape refusal and post-copy reference refusal remain atomic.
 for(const [name,damage,code]of [
  ['weak-flags',()=>put(table+2,get(table+2)|16384),2],
  ['no-tracking',()=>put(table+2,0),2],
  ['bad-capacity',()=>put(table+46,12),2],
  ['wrong-count',()=>put(table+30,5),2],
  ['bad-cache-index',()=>put(table+34,256),2],
  ['late-interior-root',()=>{put(root+4,3);put(root+16,base+9);},3]
 ]){
  setup();const k=cons();invoke(1,k,28);roots([table,k]);damage();
  const old=Buffer.from(new Uint8Array(memory.buffer,base,size)),r=Buffer.from(new Uint8Array(memory.buffer,root,128)),t=Buffer.from(new Uint8Array(memory.buffer,tcr,256));
  assert.equal(collector.collect(config),code,name);assert.deepEqual(Buffer.from(new Uint8Array(memory.buffer,base,size)),old,name+': source');assert.deepEqual(Buffer.from(new Uint8Array(memory.buffer,root,128)),r,name+': roots');assert.deepEqual(Buffer.from(new Uint8Array(memory.buffer,tcr,256)),t,name+': TCR');refusals.push({name,code});
 }
 parentPort.postMessage({status:'PASS',base,nativeComparisons:observations.length,checks,refusals,moves,observations,...(generated?{generated:generated.counts()}:{} )});
}
