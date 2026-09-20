import fs from 'node:fs';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {Worker,isMainThread,parentPort,workerData} from 'node:worker_threads';
import {image,NIL,T,CONFIG,RESULT,hashName} from './image.mjs';
if(isMainThread){
 const rows=[];for(const base of [4194304,8388608,2147483648])for(const generated of [false,true])rows.push(await new Promise((resolve,reject)=>{const w=new Worker(new URL(import.meta.url),{workerData:{base,generated,dir:process.argv[2]}});w.on('message',resolve);w.on('error',reject);w.on('exit',c=>{if(c)reject(Error('Worker '+c));});}));
 fs.writeFileSync(process.argv[3],JSON.stringify({status:'PASS',rows},null,2)+'\n');
}else{
 const {base,dir,generated}=workerData,read=n=>JSON.parse(fs.readFileSync(dir+'/'+n));
 const memory=new WebAssembly.Memory({initial:32769,maximum:32769,shared:true});
 const service=(await WebAssembly.instantiate(fs.readFileSync(dir+'/symbols.wasm'),{env:{memory}})).instance.exports;
 let owner=image(memory,base,{version:73,initialKeywords:read('initial-keywords.json')}),{get,put,query,decode}=owner,packages=owner.packages,statuses=owner.statuses;
 const tcr=1024,root=131064;
 put(tcr+48,3145728);put(tcr+52,3211264);put(tcr+56,3145728);put(tcr+68,root+8);put(tcr+72,196608);put(tcr+128,root);put(root,0);put(root+4,0);put(tcr+80,700000);put(tcr+76,700000);put(tcr+84,900000);put(tcr+104,610000);put(tcr+108,8);for(let i=0;i<8;i++)put(610000+4*i,243);
 const code=generated?await(await import('./generated.mjs')).install({dir,memory,tcr,get,put,service,config:CONFIG,result:RESULT}):null;
 const raw=(op,a,b=NIL,c=NIL)=>{assert.equal(service.symbols_run(CONFIG,op,a,b,c,RESULT),0,'runtime operation');return [get(RESULT),get(RESULT+4)];};
 const invoke=(...a)=>code?code.invoke(...a):raw(...a);
 assert.equal(service.symbols_run(CONFIG,0,query('NIL'),packages.CL,NIL,RESULT),6,'pre-admission lookup refused');
 assert.equal(service.symbols_admit(CONFIG,RESULT),0,'legacy hash rebuild');assert.equal(get(RESULT),1);
 assert.equal(service.symbols_admit(CONFIG,RESULT),0,'target hash admission');assert.equal(get(RESULT),0);
 let bindingComparisons=0;
 function bindings(){
 // Native binding values; package collisions must never alias a value cell.
 const a=invoke(1,query('BOUND'),packages.A)[0],b=invoke(1,query('BOUND'),packages.B)[0],u=invoke(2,query('BOUND'))[0];assert.notEqual(a,b,'distinct package symbol identities');assert.notEqual(a,u);

 if(code){
  for(const [s,v,index] of [[a,7,1],[b,17,2],[u,27,3]]){put(s+22,index*4);assert.deepEqual(code.call('symbol_write',[s,v*4]),[v*4]);assert.deepEqual(code.call('symbol_read',[s]),[v*4]);assert.deepEqual(code.call('symbol_bind',[s,36]),[36]);assert.deepEqual(code.call('symbol_repeat_bind',[s,44,52]),[52]);assert.deepEqual(code.call('symbol_read',[s]),[v*4]);bindingComparisons+=5;}
  assert.deepEqual(read('bindings.json'),[7,9,13,7]);
  assert.deepEqual(code.call('symbol_bind_pair',[a,b,84,88]),[84,88],'same name distinct dynamic slots');
  assert.deepEqual(code.call('symbol_read',[a]),[28]);assert.deepEqual(code.call('symbol_read',[b]),[68]);bindingComparisons+=3;
  assert.deepEqual(code.call('symbol_eq',[a,b]),[NIL]);assert.deepEqual(code.call('symbol_eq',[a,a]),[T]);assert.deepEqual(code.call('symbol_read',[NIL]),[NIL]);assert.deepEqual(code.call('symbol_read',[T]),[T]);
  const kw=invoke(1,query('SELF'),packages.KEYWORD)[0];assert.deepEqual(code.call('symbol_read',[kw]),[kw]);bindingComparisons+=5;
 }
 }
 bindings();
 const trace=read('trace.json'),native=read('native.json');let ids=new Map([[NIL,0],[T,1]]),count=2,observations=[],restored=false,loads=[];
 for(let i=0;i<trace.length;i++){
  if(i===Math.floor(trace.length/2)){
   const sentinel=raw(1,query('RELOCATION-FIXNUM'),packages.A)[0],sentinelValue=base+4096;put(sentinel+2,sentinelValue);
   const snap=owner.snapshot(),nextBase=base===4194304?8388608:4194304,r=owner.restore(snap,nextBase);packages=r.packages;statuses=r.statuses;ids=new Map([...ids].map(([p,id])=>[r.move(p),id]));
   new Uint8Array(memory.buffer,base,snap.bytes.length).fill(0xda);
   assert.equal(service.symbols_run(CONFIG,0,query('NIL'),packages.CL,NIL,RESULT),6,'restored lookup needs admission');
   assert.equal(service.symbols_admit(CONFIG,RESULT),0,'restored image admission');assert.equal(get(r.move(sentinel)+2),sentinelValue,'tag-looking fixnum value preserved');
   loads.push({from:base,to:nextBase,bytes:snap.bytes.length,sha256:createHash('sha256').update(snap.bytes).digest('hex'),symbolBefore:sentinel,symbolAfter:r.move(sentinel),rawFixnum:sentinelValue});restored=true;
  }
  const [op,name,pkg]=trace[i],s=query(name);assert.equal(service.symbol_hash(s)>>>0,hashName(name),'host target hash');
  const [v,status]=invoke(op,s,packages[pkg]);if(!ids.has(v))ids.set(v,count++);
  const row=[ids.get(v),status===NIL?0:statuses.indexOf(status)+1];assert.deepEqual(row,native[i],'native trace '+i+' '+op+' '+JSON.stringify(name)+' '+pkg);observations.push(row);
  if(op===2||status!==NIL||op===1){assert.equal(decode(invoke(3,v)[0]),name,'symbol name');assert.equal(invoke(4,v)[0],op===2?NIL:pkg==='USER'?packages.CL:packages[pkg],'symbol package');}
 }
 bindings();
 let refusals=[];
 const preserve=(label,f,expected)=>{const imageBase=get(CONFIG+4),bytes=Uint8Array.from(new Uint8Array(memory.buffer,imageBase,get(CONFIG+12)-imageBase)),config=Uint8Array.from(new Uint8Array(memory.buffer,CONFIG,80));new Uint8Array(memory.buffer,RESULT,16).fill(0x59);assert.equal(f(),expected,label);assert.deepEqual(new Uint8Array(memory.buffer,imageBase,bytes.length),bytes,label+' image unchanged');assert.deepEqual(new Uint8Array(memory.buffer,CONFIG,80),config,label+' config unchanged');assert(new Uint8Array(memory.buffer,RESULT,16).every(x=>x===0x59),label+' result unchanged');refusals.push(label);};
 preserve('unknown package',()=>service.symbols_run(CONFIG,1,query('X'),NIL,NIL,RESULT),3);
 preserve('invalid string',()=>service.symbols_run(CONFIG,1,28,packages.A,NIL,RESULT),4);
 preserve('invalid symbol',()=>service.symbols_run(CONFIG,3,28,NIL,NIL,RESULT),2);
 preserve('invalid operation',()=>service.symbols_run(CONFIG,99,NIL,NIL,NIL,RESULT),7);
 let end=get(CONFIG+8);put(CONFIG+8,get(CONFIG+12));preserve('allocation exhaustion',()=>service.symbols_run(CONFIG,2,query('NEVER'),NIL,NIL,RESULT),5);put(CONFIG+8,end);
 for(const bad of [0,262144,4194305,2147483656])assert.throws(()=>owner.restore(owner.snapshot(),bad),/unsupported image base/);
 // Mislabelled legacy hash tables must refuse before lookup, preserving data.
 owner=image(memory,base,{version:77});({get,put}=owner);put(CONFIG+20,1);preserve('mislabelled hash',()=>service.symbols_admit(CONFIG,RESULT),6);
 put(CONFIG+20,77);assert.equal(service.symbols_admit(CONFIG,RESULT),0);
 // Structural owner refusals are transactional; scratch is explicitly expendable.
 for(const [label,offset,value,status] of [['bad canonical NIL',28,0,1],['unaligned allocation',12,get(CONFIG+12)+1,1],['scratch aliases image',52,base,1],['unknown keyword package',36,NIL,3],['unregistered status',40,NIL,2]]){
  const old=get(CONFIG+offset);put(CONFIG+offset,value);preserve(label,()=>service.symbols_admit(CONFIG,RESULT),status);put(CONFIG+offset,old);
 }
 owner=image(memory,base,{capacity:4});({get,put}=owner);packages=owner.packages;assert.equal(service.symbols_admit(CONFIG,RESULT),0);
 for(let i=0;i<4;i++)raw(1,owner.query('F'+i),packages.A);
 preserve('full table',()=>service.symbols_run(CONFIG,1,owner.query('FIFTH'),packages.A,NIL,RESULT),5);
 assert.equal(raw(0,owner.query('F2'),packages.A)[1],owner.statuses[0]);
 parentPort.postMessage({base,generated,nativeComparisons:observations.length,observations,restored,loads,bindingComparisons,refusals,delivery:code?code.counts():null});
}
