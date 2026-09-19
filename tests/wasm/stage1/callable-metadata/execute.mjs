import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';
import {Worker,isMainThread,workerData,parentPort} from 'node:worker_threads';
import {LazyLoader,PROFILE,sha} from './loader.mjs';import {inspect} from './binary.mjs';
import {captureOwned,restoreOwned} from './transport.mjs';
if(isMainThread){
 const dir=process.argv[2];async function run(data){return new Promise((resolve,reject)=>{const w=new Worker(new URL(import.meta.url),{workerData:{dir,...data}});let result;w.on('message',v=>result=v);w.on('error',reject);w.on('exit',n=>n?reject(Error('worker '+n)):resolve(result));});}
 const origin=await run({base:1048576});const restored=[];for(const base of [2097152,2147483648])restored.push(await run({base,snapshot:origin.snapshot}));
 fs.writeFileSync(path.join(dir,'snapshot.json'),JSON.stringify(origin.snapshot));delete origin.snapshot;
 fs.writeFileSync(process.argv[3],JSON.stringify({status:'PASS',origin,restored},null,2)+'\n');
}else{
 const {dir,base,snapshot}=workerData,read=n=>JSON.parse(fs.readFileSync(path.join(dir,n))),mods=read('modules.json'),NIL=77825,T=77838;
 const memory=new WebAssembly.Memory({initial:Math.ceil((base+65536)/65536),maximum:32769,shared:true}),dv=new DataView(memory.buffer),tcr=256;
 const get=p=>dv.getUint32(p,true),put=(p,v)=>dv.setUint32(p,v,true),set=(o,v)=>put(tcr+o,v);
 const material=read('materialized.json'),symbolNames=Object.keys(material.symbols);
 const symbols=Object.fromEntries(symbolNames.map((k,i)=>[k,620006+32*i+(snapshot?2048:0)]));
 for(const p of Object.values(symbols)){put(p-6,1850);for(let i=1;i<8;i++)put(p-6+4*i,NIL);}
 const keywords=Object.fromEntries(Object.entries(symbols).map(([k,v])=>[k.split('::')[1].toLowerCase(),v]));
 keywords['allow-other-keys']??=623006;put(keywords['allow-other-keys']-6,1850);
 const importsSymbols={condition_handlers:600006,condition_registry:600038,debugger_hook:600070,error_message:600102,expected_function:600134};
 for(const p of Object.values(importsSymbols)){put(p-6,1850);for(let i=1;i<8;i++)put(p-6+4*i,NIL);put(p+22,0);}set(104,610000);set(108,2);put(610000,243);put(610004,243);
 let roots,objects,length;
 if(!snapshot){new Uint8Array(memory.buffer,base,material.image.length/2).set(Buffer.from(material.image,'hex'));roots=material.roots;objects=material.objects;length=material.image.length/2;}
 else {const r=restoreOwned(Buffer.from(snapshot.hex,'hex'),snapshot.sha256,memory,base,65536,symbols);roots=r.roots;objects=snapshot.objects;length=r.byteLength;}
 const table=new WebAssembly.Table({element:'anyfunc',initial:mods.length+1}),tail_table=new WebAssembly.Table({element:'anyfunc',initial:mods.length+1});
 const call_error=new WebAssembly.Tag({parameters:['i32']}),type_error=new WebAssembly.Tag({parameters:['i32','i32']}),nonlocal_exit=new WebAssembly.Tag({parameters:['i32']});
 const binaries=new Map(mods.map(m=>[m.name,fs.readFileSync(path.join(dir,m.name+'.wasm'))]));
 const catalog=mods.map((m,i)=>{const b=binaries.get(m.name),x=inspect(b);return{name:m.name,slot:i+1,code:i+1,version:4,signature:17,role:23,sha256:sha(b),profile:PROFILE,imports:x.imports,entries:Object.fromEntries(x.exports.map(e=>[e.name,{index:e.index,role:e.name}]))};});
 const loader=new LazyLoader({memory,table,tail_table,call_error,nonlocal_exit,stub:new WebAssembly.Module(fs.readFileSync(new URL('stub.wasm',import.meta.url))),catalog,readBytes:n=>binaries.get(n)});
 const codes=Object.fromEntries(mods.map((m,i)=>[m.name,4*(i+1)])),functions=new Map(),handles={};
 put(4096,mods.length+1);put(4100,1);
 let top=base+length;
 function vector(p,n){assert.equal(p%8,6);assert.equal(get(p-6),n*256+250);return Array.from({length:n},(_,i)=>get(p-2+4*i));}
 function string(p){assert.equal(p%8,6);const h=get(p-6);assert.equal(h%256,191);return String.fromCodePoint(...Array.from({length:Math.floor(h/256)},(_,i)=>get(p-2+4*i)));}
 function decode(p){if(p===NIL)return null;if(p===T)return true;if(p%4===0)return (p|0)/4;for(const [k,v]of Object.entries(symbols))if(v===p)return {symbol:k};const h=get(p-6);if(h%256===191)return string(p);assert.equal(h%256,250);return vector(p,Math.floor(h/256)).map(decode);}
 // Native compiled function-args and lfun-keyvect are independent of pass 1 metadata.
 const native=read('native-metadata.json'),nativeNodes=Object.fromEntries(native.objects.map(r=>[r.id,r.value]));
 function nativeValue(v){if(v.symbol)return v;if(v.ref){const x=nativeNodes[v.ref];if(x.kind==='string')return String.fromCodePoint(...x.value);assert.equal(x.kind,'general-vector');return x.elements.map(nativeValue);}if(v.kind==='integer')return Number(v.value);if(v.kind==='singleton')return v.value==='nil'?null:true;throw Error('native descriptor');}
 const nativeRows=native.roots.map(nativeValue);let metadataChecks=0;const metadataRecords=[];
 for(let i=0;i<mods.length;i++){
  const m=mods[i],row=4104+16*(i+1);[i+1,4,17,23].forEach((v,j)=>put(row+4*j,v));
  if(m.top){if(!snapshot){const p=top;top+=32;[1578,4*(i+1),NIL,4,get(roots[i]-2),get(roots[i]+2),roots[i],0].forEach((v,j)=>put(p+4*j,v));objects.push({id:'function-'+m.name,offset:p-base,tag:6});handles[m.name]=p+6;roots.push(p+6);}else handles[m.name]=roots[mods.length+Object.keys(handles).length];}
  functions.set(m.name,loader.defer(m.name,{env:{memory,tcr,table,tail_table,code_registry:4096,call_error,type_error,nonlocal_exit},codes,symbols:importsSymbols,keywords}).host_entry);
  const pool=roots[i],arity=decode(get(pool-2)),debug=decode(get(pool+2));
  assert.equal(arity[0],1);assert.equal(debug[0],1);assert.equal(debug[1],m.name);assert.equal(debug[2].length,m.captures);
  debug[2].forEach((r,j)=>{assert.equal(r[0],j,'capture slot ordinal');assert.equal(r[1][0],'WASM32-COMPILER','capture package');});
  const expectedNames=m.name==='multi_inner_1'?['LEFT','RIGHT']:m.top?[]:['X'];assert.deepEqual(debug[2].map(r=>r[1][1]).sort(),expectedNames,'source capture names');metadataRecords.push({name:m.name,arity,debug});metadataChecks++;
 }
 for(const [name,args,keys]of nativeRows){const selected=['factory','twins','separate','multi'].includes(name)?mods.findIndex(m=>m.name.startsWith(name+'_inner_')):mods.findIndex(m=>m.name===name);const a=decode(get(roots[selected]-2));assert.deepEqual(a.slice(1,6),[args[0],args[1],args[2],args[3]!==null?true:null,args[4]],name+' native arity');assert.deepEqual(a[6],keys,name+' native keys');metadataChecks++;}
 set(48,top);set(56,base);set(52,base+65536);set(80,700000);set(76,700000);set(84,900000);
 const observations=[];function invoke(name,args=[],self=handles[name]){
  new Uint8Array(memory.buffer,65536,32768).fill(0x55);set(64,65536);set(68,65536);set(72,98304);set(116,0);set(120,66000);set(124,66032);set(128,0);set(140,0);set(148,0);
  args.forEach((v,i)=>put(65536+4*i,v));let pair;try{pair=functions.get(name)(self,args.length).map(x=>x>>>0);}catch(e){console.error(JSON.stringify({base,name,self,args,code:e.is?.(call_error)?e.getArg(call_error,0):null}));throw e;}assert.equal(pair[1],get(tcr+116));assert.deepEqual([get(tcr+64),get(tcr+120),get(tcr+124),get(tcr+128)],[65536,66000,66032,0]);const values=Array.from({length:pair[1]},(_,i)=>get(66000+4*i));observations.push({name,self,args,values});return values;
 }
 function checkFunction(f){assert.equal(get(f-6),1578);const i=get(f-2)/4-1,pool=roots[i];assert.equal(get(f+18),pool,'restored pool identity');assert.equal(get(f+10),get(pool-2),'arity identity');assert.equal(get(f+14),get(pool+2),'debug identity');return i;}
 // All metadata is readable before any code is installed.
 for(const f of Object.values(handles))checkFunction(f);assert(loader.snapshot().every(r=>r.state==='COLD'));
 const before=new Uint8Array(memory.buffer,base,top-base).slice();for(const m of mods)loader.install(codes[m.name]/4);assert.deepEqual(new Uint8Array(memory.buffer,base,top-base),before,'installation preserves metadata and environment bytes');
 assert.deepEqual(invoke('plain',[12]),[12,28]);assert.deepEqual(invoke('keyword',[12,36,keywords.alias,44]),[12,36,44]);assert.deepEqual(invoke('aliases',[keywords.x,36]),[36,8]);assert.deepEqual(invoke('empty_keys'),[68]);
 let closures;
 if(!snapshot){const a=invoke('factory',[76])[0],b=invoke('factory',[164])[0],[setter,reader]=invoke('twins',[76]);const multi=invoke('multi',[68,116])[0];closures=[a,b,setter,reader,multi];closures.forEach(checkFunction);
  const observed=[invoke('driver',[a,92])[0]/4,invoke(mods[checkFunction(b)].name,[],b)[0]/4,invoke('set_y',[setter,124])[0]/4,invoke('get',[reader])[0]/4,a===b?true:null,setter===reader?true:null];
  const nb=read('native-behavior.json'),nodes=Object.fromEntries(nb.objects.map(r=>[r.id,r.value]));const ex=nodes[nb.roots[0].ref].elements.map(v=>v.kind==='integer'?Number(v.value):v.value==='nil'?null:true);assert.deepEqual(observed,ex,'native escaping mutable closures');
  assert.notEqual(get(a+2),get(b+2));assert.equal(get(setter+2)%8,6);assert.equal(get(get(setter+2)-2),get(get(reader+2)-2),'shared capture cell');roots.push(...closures);
 }else {closures=roots.slice(mods.length+Object.keys(handles).length);closures.forEach(checkFunction);assert.equal(invoke('get',[closures[3]])[0],124,'restored shared mutable cell');assert.equal(invoke('driver',[closures[0],148])[0],148);assert.equal(invoke('get',[closures[3]])[0],124,'separate restored activation');}
 const multi=closures[4],multiIndex=checkFunction(multi),multiDebug=decode(get(multi+14)),multiCells=vector(get(multi+2),2);
 multiDebug[2].forEach(([i,[pkg,name]])=>assert.equal(get(multiCells[i]+3),name==='LEFT'?68:116,'debug slot resolves captured value'));
 assert.deepEqual(invoke(mods[multiIndex].name,[],multi),[68,116,68,116],'multi captured defaults');
 const faultSelf=handles.plain,refusals=[];for(const [label,offset,value]of [['truncated-header',-6,1322],['missing-arity',10,NIL],['missing-debug',14,NIL],['wrong-pool',18,NIL]]){const old=get(faultSelf+offset);put(faultSelf+offset,value);let caught;try{invoke('plain',[12]);}catch(e){caught=e;}assert(caught?.is?.(call_error),label);assert.equal(caught.getArg(call_error,0),4,label);put(faultSelf+offset,old);refusals.push(label);}
 let saved;if(!snapshot){let cursor=top;while(cursor<get(tcr+48)){const h=get(cursor),header=h%8===2;const bytes=header?Math.ceil((4+4*Math.floor(h/256))/8)*8:8;assert(!header||[42,250].includes(h%256),'heap object kind');objects.push({id:'heap-'+(cursor-base),offset:cursor-base,tag:header?6:1});cursor+=bytes;}assert.equal(cursor,get(tcr+48));saved=captureOwned(memory,{base,length:cursor-base,objects,roots,symbols});}
 parentPort.postMessage({status:'PASS',base,modules:mods.length,observations,metadataRecords,metadataChecks,nativeSignatures:nativeRows.length,refusals,installed:loader.snapshot().filter(r=>r.state==='READY').length,restoredClosures:!!snapshot,installations:loader.events.filter(r=>r.event==='INSTALLED'),...(saved?{snapshot:{hex:saved.bytes.toString('hex'),sha256:saved.sha256,objects}}:{})});
}
