import fs from 'node:fs';
import {pathToFileURL} from 'node:url';
import assert from 'node:assert/strict';
import {Worker,isMainThread,parentPort,workerData} from 'node:worker_threads';
if(isMainThread){
 const rows=[];for(const base of [4194304,2147483648])rows.push(await new Promise((resolve,reject)=>{const w=new Worker(new URL(import.meta.url),{workerData:{dir:process.argv[2],base}});w.once('message',resolve);w.once('error',reject);w.once('exit',c=>{if(c)reject(Error('Worker '+c));});}));
 const summary={status:'PASS',scenarios:rows.reduce((n,r)=>n+r.rows.length,0),refusals:rows.reduce((n,r)=>n+r.refusals.length,0),modules:4,placements:2,slot_credit:false};fs.writeFileSync(process.argv[3],JSON.stringify({summary,rows},null,2)+'\n');
}else{
 const {counterStorage}=await import(pathToFileURL(workerData.dir+'/owner.mjs'));
 const {base,dir}=workerData,read=n=>JSON.parse(fs.readFileSync(dir+'/'+n)),NIL=77825,T=77838,TCR=16384,REG=4096,STACK=32768,RESULT=2048000,DONE=2300000,HT=2300033,DT=2300041;
 const memory=new WebAssembly.Memory({initial:32769,maximum:32769,shared:true}),v=new DataView(memory.buffer),get=p=>v.getUint32(p,true),put=(p,x)=>v.setUint32(p,x,true);
 const binary=fs.readFileSync(dir+'/counters.wasm'),digest=read('service.json').sha256;
 const table=new WebAssembly.Table({element:'anyfunc',initial:32}),tail_table=new WebAssembly.Table({element:'anyfunc',initial:32}),call_error=new WebAssembly.Tag({parameters:['i32']}),type_error=new WebAssembly.Tag({parameters:['i32','i32']}),nonlocal_exit=new WebAssembly.Tag({parameters:['i32']});
 const env={memory,tcr:TCR,table,tail_table,code_registry:REG,call_error,type_error,nonlocal_exit},adapter=new WebAssembly.Module(fs.readFileSync(dir+'/adapter.wasm'));
 function register(id,x){[id,4,17,23].forEach((n,j)=>put(REG+8+16*id+4*j,n));table.set(id,x.exports.entry);tail_table.set(id,x.exports.tail_entry);}
 function object(id){const p=2100000+32*id;[1578,4*id,NIL,4,NIL,NIL,NIL,0].forEach((n,j)=>put(p+4*j,n));return p+6;}
 put(REG,32);put(REG+4,1);const operation=object(1),entries=[],symbols={};
 const mat=read('compiled/materialized.json');assert.equal(mat.image,'');assert(mat.roots.every(x=>x===NIL));
 for(const [i,m] of read('compiled/modules.json').entries()){
  const mod=new WebAssembly.Module(fs.readFileSync(dir+'/compiled/'+m.name+'.wasm'));
  for(const imp of WebAssembly.Module.imports(mod))if(imp.module==='symbols'&&!(imp.name in symbols)){
   const p=2200000+32*Object.keys(symbols).length;[1850,NIL,NIL,NIL,NIL,0,NIL,0].forEach((n,j)=>put(p+4*j,n));symbols[imp.name]=p+6;
  }
  const inst=new WebAssembly.Instance(mod,{env,symbols});register(i+2,inst);entries.push({name:m.name,self:object(i+2),fn:inst.exports.entry});
 }
 put(77824,NIL);put(77828,NIL);put(77832,1850);for(let j=3;j<16;j++)put(77824+4*j,NIL);
 put(HT-1,NIL);put(HT+3,NIL);put(DT-1,NIL);put(DT+3,T);

 const ST=2400006,SB=2400038,secondOp=object(6),rows=[],refusals=[];
 const words=Array.from({length:64},(_,j)=>4*j).filter(x=>x!==116);
 const bytes=()=>Uint8Array.from(new Uint8Array(memory.buffer,base,528));
 function reset(){
  new Uint8Array(memory.buffer,base,528).fill(0x96);
  new Uint8Array(memory.buffer,TCR,256).fill(0);new Uint8Array(memory.buffer,STACK,32768).fill(0);
  for(const [o,x]of [[0,TCR],[48,131072],[52,135168],[56,131072],[64,STACK+512],[68,STACK+16],[72,STACK+32768],[76,8192],[80,8192],[84,12288],[88,12288],[92,12288],[96,16384],[104,139264],[108,0],[120,STACK+1024],[124,STACK+1088],[128,STACK+8],[136,NIL],[200,7]])put(TCR+o,x);
  for(const p of [ST-6,SB-6])[1850,NIL,148,NIL,NIL,0,NIL,0].forEach((n,j)=>put(p+4*j,n));
  put(DONE,NIL);put(DONE+4,0);
  return counterStorage({memory,base,end:base+512,bytes:binary,digest});
 }
 function install(id,storage,r){register(id,new WebAssembly.Instance(adapter,{env,hash:{run:storage.run,collect:()=>{throw Error('unexpected collection');},config:0,operation:5,scratch:r.base,scratch_end:r.end,result:RESULT}}));}
 function call(name,args){
  const f=entries.find(e=>e.name===name);args.forEach((x,j)=>put(STACK+512+4*j,x));const before=words.map(o=>get(TCR+o));let pair;
  try{pair=f.fn(f.self,args.length);}catch(e){throw Error(name+' '+(e.is?.(call_error)?'CHECKED_'+e.getArg(call_error,0):String(e)));}
  assert.deepEqual(words.map(o=>get(TCR+o)),before,'counter TCR restoration');assert.equal(get(TCR+116),pair[1]);return pair.map(x=>x>>>0);
 }
 const poison=p=>[p,NIL,1,0].map(x=>(~x)>>>0).forEach((x,j)=>put(RESULT+4*j,x));
 const publication=p=>assert.deepEqual(Array.from({length:4},(_,j)=>get(RESULT+4*j)),[p,NIL,1,0],'counter publication');
 const native=read('compiled/native.json');assert.deepEqual(native.map(x=>x.bytes),[80,8]);assert(native.every(x=>x.zero&&x.published_identity&&x.fresh_twice));
 for(const mode of ['raw','generated','cleanup','joined']){
  const storage=reset();let previous=[];
  for(let round=0;round<2;round++){
   const rs=[storage.reserve(0),storage.reserve(1)];assert(rs[0].end<=rs[1].base,'fresh reservations');const before=bytes(),expected=Uint8Array.from(before);
   rs.forEach(r=>expected.fill(0,r.base+16-base,r.end-base));
   install(1,storage,rs[0]);install(6,storage,rs[1]);
   if(mode==='joined'){
    poison(rs[1].pointer);
    const pair=call('gc_joined',[entries[0].self,entries[1].self,operation,secondOp,rs[0].pointer,rs[1].pointer,ST,SB,DONE+1]);
    assert.deepEqual(pair,[rs[0].pointer,2]);assert.equal(get(STACK+1028),rs[1].pointer);publication(rs[1].pointer);
   }else for(let kind=0;kind<2;kind++){
    const r=rs[kind];poison(r.pointer);
    if(mode==='raw')assert.equal(storage.run(r.pointer,r.base+16,5,4*kind,NIL,r.base,r.end,RESULT),0,'counter raw status');
    else{
     const args=[kind?secondOp:operation,r.pointer,kind?SB:ST,DONE+1];
     const pair=mode==='cleanup'?call('gc_cleanup',[entries[kind].self,...args]):call(kind?'gc_bytes':'gc_time',args);
     assert.deepEqual(pair,[r.pointer,1]);assert.equal(get(DONE+4),4*(mode==='cleanup'?503:501+kind),'counter completion');
    }
    publication(r.pointer);
   }
   assert.deepEqual(bytes(),expected,'counter exact zeroing and preservation');
   for(let kind=0;kind<2;kind++){
    const r=rs[kind];assert.equal(get(r.base),799);assert.equal(get(r.base+4),r.base+16);
    if(mode!=='raw')assert.equal(get((kind?SB:ST)+2),r.pointer,'counter symbol identity');
    if(round)assert.notEqual(r.pointer,previous[kind],'fresh counter storage');
    rows.push({mode,round,kind,bytes:native[kind].bytes,zero:true,fresh:true});
    new Uint8Array(memory.buffer,r.base+16,r.bytes).fill(165);
   }
   previous=rs.map(r=>r.pointer);
  }
 }
 for(const [name,edit]of [
  ['operation',a=>a[2]=4],['kind',a=>a[3]=8],['unused',a=>a[4]=T],['owner alignment',a=>{new Uint8Array(memory.buffer,base,97).copyWithin(1,0,96);a[0]++;a[1]++;a[5]++;a[6]++;put(base+5,base+17);}],['owner extent',a=>a[6]+=8],['result alias',a=>a[7]=base],['result alignment',a=>a[7]++],['result outside',a=>a[7]=memory.buffer.byteLength-8],
  ['pointer identity',a=>a[0]+=8],['pointer extent',a=>a[1]+=8],['header',()=>put(base,31)],['address',()=>put(base+4,base+24)],['domain',()=>put(base+8,1)],['type',()=>put(base+12,1)],
 ]){
  const storage=reset(),r=storage.reserve(name==='kind'?1:0);const a=[r.pointer,r.base+16,5,0,NIL,r.base,r.end,RESULT];edit(a);poison(r.pointer);
  const before=bytes(),pub=Uint8Array.from(new Uint8Array(memory.buffer,RESULT,16)),tcr=Uint8Array.from(new Uint8Array(memory.buffer,TCR,256));
  const status=storage.run(...a);assert(status,'counter refusal '+name);assert.deepEqual(bytes(),before,'counter refusal storage');assert.deepEqual(new Uint8Array(memory.buffer,RESULT,16),pub,'counter refusal publication');assert.deepEqual(new Uint8Array(memory.buffer,TCR,256),tcr);refusals.push({name,status});
 }
 for(const [name,change]of [['digest',x=>x.digest='0'.repeat(64)],['base',x=>x.base++],['end',x=>x.end=memory.buffer.byteLength+8]]){
  reset();const x={memory,base,end:base+512,bytes:binary,digest};change(x);const before=bytes();assert.throws(()=>counterStorage(x),/COUNTER_/);assert.deepEqual(bytes(),before);refusals.push({name});
 }
 {reset();const storage=counterStorage({memory,base,end:base+120,bytes:binary,digest});storage.reserve(0);storage.reserve(1);const before=bytes();assert.throws(()=>storage.reserve(1),/COUNTER_CAPACITY/);assert.throws(()=>storage.reserve(2),/COUNTER_KIND/);assert.deepEqual(bytes(),before);refusals.push({name:'exact-fit then capacity'},{name:'reserve kind'});}
 parentPort.postMessage({base,rows,refusals});
}
