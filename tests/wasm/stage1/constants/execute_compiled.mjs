import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';
import {Worker,isMainThread,workerData,parentPort} from 'node:worker_threads';
import {LazyLoader,PROFILE,sha,validate} from './loader.mjs';import {inspect} from './binary.mjs';
import {captureOwned,restoreOwned} from './transport.mjs';
if(isMainThread){
 const dir=process.argv[2];
 async function run(data){return new Promise((resolve,reject)=>{let result;const w=new Worker(new URL(import.meta.url),{workerData:{dir,...data}});w.on('message',r=>result=r);w.on('error',reject);w.on('exit',code=>code?reject(Error('worker exit '+code)):resolve(result));});}
 const origin=await run({mode:'origin',base:1048576});
 fs.writeFileSync(path.join(dir,'snapshot.json'),JSON.stringify(origin.snapshot));
 const restored=[];for(const base of [2097152,2147483648])restored.push(await run({mode:'restore',base,snapshot:origin.snapshot}));
 delete origin.snapshot;console.log(JSON.stringify({status:'PASS',modules:origin.modules,native_comparisons:origin.native_comparisons+restored.reduce((n,r)=>n+r.native_comparisons,0),origin,restored},null,2));
}else{
 const {dir,mode,base,snapshot}=workerData,read=n=>JSON.parse(fs.readFileSync(path.join(dir,n))),mods=read('modules.json');
 const memory=new WebAssembly.Memory({initial:Math.ceil((Math.max(base+65536,5242880))/65536),maximum:32769,shared:true}),dv=new DataView(memory.buffer),tcr=256;
 const load=p=>dv.getUint32(p,true),store=(p,v)=>dv.setUint32(p,v,true),set=(o,v)=>store(tcr+o,v),get=o=>load(tcr+o);
 // Restoring Worker receives serialized target bytes, never the build graph.
 let pool,transportRefusals=0;
 if(mode==='origin'){
  pool=read('materialized.json');new Uint8Array(memory.buffer,pool.base,pool.image.length/2).set(Buffer.from(pool.image,'hex'));
 }else{
  const symbols={'WASM32-COMPILER::POOL-OWNER':620070,'WASM32-COMPILER::pool-owner':620102};
  const bytes=Buffer.from(snapshot.hex,'hex');new Uint8Array(memory.buffer,base-16,65552).fill(0xa5);
  const before=new Uint8Array(memory.buffer,base-16,65552).slice();
  const badRecord=JSON.parse(bytes.toString());badRecord.layout='wrong';const bad=Buffer.from(JSON.stringify(badRecord));
  for(const [data,digest,limit] of [[bytes,'0'.repeat(64),65536],[bytes,snapshot.sha256,1],[bad,sha(bad),65536]]){
   assert.throws(()=>restoreOwned(data,digest,memory,base,limit,symbols));assert.deepEqual(new Uint8Array(memory.buffer,base-16,65552),before,'refused restoration writes nothing');transportRefusals++;
  }
  const result=restoreOwned(bytes,snapshot.sha256,memory,base,65536,symbols);
  assert(new Uint8Array(memory.buffer,base+result.byteLength,65536-result.byteLength).every(x=>x===0xa5),'owned tail remains untouched');
  assert(new Uint8Array(memory.buffer,base-16,16).every(x=>x===0xa5),'owned prefix remains untouched');
  pool={base,roots:result.roots,objects:result.objects,symbols};
 }
 for(const addr of Object.values(pool.symbols)){store(addr-6,1850);for(let i=1;i<8;i++)store(addr-6+4*i,77825);}
 const table=new WebAssembly.Table({element:'anyfunc',initial:mods.length+1}),tail_table=new WebAssembly.Table({element:'anyfunc',initial:mods.length+1});
 const call_error=new WebAssembly.Tag({parameters:['i32']}),type_error=new WebAssembly.Tag({parameters:['i32','i32']}),nonlocal_exit=new WebAssembly.Tag({parameters:['i32']});
 const conversion_error=new WebAssembly.Tag({parameters:['i32']});
 const headerProbe=new WebAssembly.Instance(new WebAssembly.Module(fs.readFileSync(path.join(dir,'header_probe.wasm'))),{env:{memory,slots:table,conversion_error}}).exports.entry;
 let headerChecks=0;
 const codes=Object.fromEntries(mods.map((m,i)=>[m.name,4*(i+1)])),symbols={condition_handlers:600006},functions=new Map();
 store(600000,1850);for(let i=1;i<8;i++)store(600000+i*4,77825);store(600028,4);store(610000,243);store(610004,243);set(104,610000);set(108,2);
 store(4096,mods.length+1);store(4100,1);
 const binaries=new Map(mods.map(m=>[m.name,fs.readFileSync(path.join(dir,m.name+'.wasm'))]));
 const catalog=mods.map((m,i)=>{const bytes=binaries.get(m.name),info=inspect(bytes);return {name:m.name,slot:i+1,code:i+1,version:4,signature:17,role:23,sha256:sha(bytes),profile:PROFILE,imports:info.imports,entries:Object.fromEntries(info.exports.map(e=>[e.name,{index:e.index,role:e.name}]))};});
 const stub=new WebAssembly.Module(fs.readFileSync(path.join(dir,'lazy-stub.wasm')));
 const loader=new LazyLoader({memory,table,tail_table,call_error,nonlocal_exit,stub,catalog,readBytes:name=>binaries.get(name)});
 // The new layout cannot be declared under the former installation profile.
 assert.throws(()=>validate(binaries.get(mods[0].name),{...catalog[0],profile:'wasm32-shared-B-exnref-tail-mv-storage-v2'}),/PROFILE/);
 for(let i=0;i<mods.length;i++){
  const m=mods[i],row=4104+16*(i+1);store(row,i+1);store(row+4,4);store(row+8,17);store(row+12,23);
  if(m.top){const base=131072+32*i;store(base,1578);store(base+4,4*(i+1));store(base+8,77825);store(base+12,4);store(base+16,77825);store(base+20,77825);store(base+24,pool.roots[i]);store(base+28,0);}
  const entry=loader.defer(m.name,{env:{memory,tcr,table,tail_table,code_registry:4096,call_error,type_error,nonlocal_exit},codes,symbols,keywords:{}});
  functions.set(m.name,entry.host_entry);
 }
 const handles=Object.fromEntries(mods.map((m,i)=>[m.name,131078+32*i]));
 // Allocation offsets come from the production schema.
 const schema=JSON.parse(fs.readFileSync(new URL('../../../../doc/WASM/contracts/tcr.v1.json',import.meta.url)));
 function rows(x){if(x&&typeof x==='object'){if(!Array.isArray(x)&&'name'in x&&'offset'in x)fields[x.name]=x.offset;for(const v of Object.values(x))rows(v);}}
 const fields={};rows(schema);set(fields.alloc_pointer,262144);set(fields.alloc_base,262144);set(fields.alloc_limit,524288);
 set(80,700000);set(76,700000);set(84,900000);
 function invoke(name,args=[],self=handles[name],stackBytes=32768){
  set(64,65536);set(68,65536);set(72,65536+stackBytes);set(116,0);set(120,66000);set(124,66016);set(128,0);set(140,0);set(148,0);
  args.forEach((v,i)=>store(65536+4*i,v));
  let pair;try{pair=functions.get(name)(self,args.length).map(v=>v>>>0);}catch(e){if(e.is?.(call_error))throw new Error(name+': call_error '+e.getArg(call_error,0));throw e;}
  assert.equal(pair[1],get(116));assert.deepEqual([get(64),get(120),get(124),get(128)],[65536,66000,66016,0]);
  return Array.from({length:pair[1]},(_,i)=>load(66000+4*i));
 }
 function describe(values,name){const seen=new Map(),objects=[];
  function value(x){for(const [key,address] of Object.entries(pool.symbols))if(x===address)return {symbol:key};if(x===77825)return {kind:'singleton',value:'nil'};if(x===77838)return {kind:'singleton',value:'t'};if(x%4===0)return {kind:'integer',value:String((x|0)/4)};if(x%256===75)return {kind:'character',value:Math.floor(x/256)};if(!seen.has(x)){seen.set(x,objects.length);objects.push(x);}return {ref:seen.get(x)};}
  const roots=values.map(value),result=[];
  for(let i=0;i<objects.length;i++){let x=objects[i],p=x-x%8;
   if(x%8===1){result.push({kind:'cons',car:value(load(p+4)),cdr:value(load(p))});continue;}
   assert.equal(x%8,6,'value-tag '+name);const header=headerProbe(x)>>>0,tag=header%256,n=Math.floor(header/256);assert.equal(header,load(p),'generated header read');headerChecks++;
   if(tag===250)result.push({kind:'general-vector',elements:Array.from({length:n},(_,j)=>value(load(p+4+4*j)))});
   else if(tag===191)result.push({kind:'string',value:Array.from({length:n},(_,j)=>load(p+4+4*j))});
   else if(tag===7){let v=0n;for(let j=n-1;j>=0;j--)v=v*4294967296n+BigInt(load(p+4+4*j));if(load(p+4*n)>=0x80000000)v-=1n<<BigInt(n*32);result.push({kind:'integer',value:String(v)});}
   else if(tag===15)result.push({kind:'single-float',value:load(p+4).toString(16).padStart(8,'0')});
   else if(tag===23)result.push({kind:'double-float',value:dv.getBigUint64(p+8,true).toString(16).padStart(16,'0')});
   else {
    const ints={199:['u8',1,false],207:['s8',1,true],215:['u16',2,false],223:['s16',2,true],167:['u32',4,false],175:['s32',4,true],183:['fixnum',4,true]};
    if(tag in ints){const [type,width,signed]=ints[tag];result.push({kind:'vector',type,elements:Array.from({length:n},(_,j)=>String(dv['get'+(signed?'Int':'Uint')+(width*8)](p+4+width*j,true)))});}
    else if(tag===255)result.push({kind:'vector',type:'bit',elements:Array.from({length:n},(_,j)=>(dv.getUint8(p+4+Math.floor(j/8))>>>(j%8))&1)});
    else if([159,231,239,247].includes(tag)){
     const width=[231,247].includes(tag)?8:4,parts=[239,247].includes(tag)?2:1,offset=tag===159?4:8,type={159:'single-float',231:'double-float',239:'complex-single-float',247:'complex-double-float'}[tag];
     const bits=where=>(width===8?dv.getBigUint64(where,true):dv.getUint32(where,true)).toString(16).padStart(width*2,'0');
     result.push({kind:'vector',type,elements:Array.from({length:n},(_,j)=>parts===1?bits(p+offset+j*width):[bits(p+offset+j*width*2),bits(p+offset+j*width*2+width)])});
    }else throw new Error('oracle unsupported tag '+tag);
   }
  }return {roots,objects:result};
 }
 const expected=read('expected.json'),results=[];
 if(mode==='restore')for(const row of Object.values(expected))for(const obj of row.objects)if(obj.kind==='cons'&&obj.car?.kind==='integer'&&obj.car.value==='7')obj.car.value='11';
 const coldIndex=mods.findIndex(m=>m.name==='cold');assert(coldIndex>=0);
 assert.equal(loader.snapshot()[coldIndex].state,'COLD');
 // Inspect the restored cold pool before installing or calling its function.
 const coldPool=pool.roots[coldIndex];assert.notEqual(coldPool,77825,'cold pool retained');assert.equal(headerProbe(coldPool)>>>0,506);headerChecks++;
 assert.equal(loader.snapshot()[coldIndex].state,'COLD');
 for(const m of mods.filter(m=>m.top)){
  if(mode==='origin'&&m.name==='cold')continue;
  if(m.name==='tail_pool'){
   const head=4194305;for(let i=0;i<100000;i++){store(head-1+8*i,i===99999?77825:head+8*(i+1));store(head+3+8*i,0);}
   const before=get(fields.alloc_pointer),got=invoke(m.name,[head],handles[m.name],2048);assert.deepEqual(describe(got,m.name),expected[m.name],m.name);
   assert.equal(get(fields.alloc_pointer)-before,48,'tail pool heap bounded');results.push(m.name);continue;
  }
  if(m.name==='mutate_pool'){store(300000,77825);store(300004,28);}
  let values=invoke(m.name,m.name==='mutate_pool'?[300001]:['captured','captured_apply','flet_constant'].includes(m.name)?[68]:[]);
  while(values.length===1 && values[0]%8===6 && load(values[0]-6)===1578){
   const closure=values[0],id=load(closure-2)/4,child=mods[id-1].name;
   assert.equal(load(closure-6),1578);assert.equal(load(closure+18),pool.roots[id-1],'closure-pool '+m.name);
   new Uint8Array(memory.buffer,65536,32768).fill(0x55);
   values=invoke(child,[],closure);
  }
  const got=describe(values,m.name);assert.deepEqual(got,expected[m.name],m.name);results.push(m.name);
 }
 // Two factory activations share the pool but keep distinct environments.
 const beforeFactories=get(fields.alloc_pointer),first=invoke('captured',[68])[0],second=invoke('captured',[92])[0];
 assert.equal(get(fields.alloc_pointer)-beforeFactories,96,'two independent 48-byte factories');
 assert.notEqual(first,second);assert.notEqual(load(first+2),load(second+2));assert.equal(load(first+18),load(second+18));
 new Uint8Array(memory.buffer,65536,32768).fill(0x55);
 const child=mods[load(first-2)/4-1].name,left=invoke(child,[],first),right=invoke(child,[],second);
 assert.equal(left[0],68);assert.equal(right[0],92);assert.equal(left[1],right[1]);
 const self=handles.string,old=load(self+18),alt=900000;
 new Uint8Array(memory.buffer,alt,8).set(new Uint8Array(memory.buffer,old-6,8));store(alt+4,77838);store(self+18,alt+6);
 assert.deepEqual(invoke('string'),[77838]);store(self+18,old);
 const guard=[];for(const [label,ptr]of [['wrong-tag',old+1],['outside',0xfffffff6]]){store(self+18,ptr);assert.throws(()=>invoke('string'),/call_error 4/);guard.push(label);}store(self+18,old);
 let saved;
 if(mode==='origin'){
  // A generated Lisp mutation must survive, not just the original builder data.
  const ptr=invoke('cycle')[0];
  invoke('mutate_pool',[ptr]);assert.equal(load(ptr+3),44);
  assert.equal(loader.snapshot()[coldIndex].state,'COLD');
  saved=captureOwned(memory,{base:pool.base,length:pool.image.length/2,objects:pool.objects,roots:pool.roots,symbols:pool.symbols});
 }
 parentPort.postMessage({status:'PASS',base,modules:mods.length,native_comparisons:results.length,cases:results,generated_header_checks:headerChecks,pool_self_rebinding:true,invalid_pool_refusals:guard,escaped_closure_stack_overwrite:true,transport_refusals:transportRefusals,cold_pool_before_install:true,shared_pools_distinct_environments:true,tail_pool_steps:100000,tail_stack_bytes:2048,cold_installations:loader.events.filter(e=>e.event==='INSTALLED').length,...(saved?{snapshot:{hex:saved.bytes.toString('hex'),sha256:saved.sha256}}:{})});
}
