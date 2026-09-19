import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';
import {Worker,isMainThread,workerData,parentPort} from 'node:worker_threads';
import {BindingInstaller} from './installer.mjs';import {entryRanges} from './ranges.mjs';
import {PROFILE,sha} from './loader.mjs';import {inspect} from './binary.mjs';
if(isMainThread){const rows=[];for(const base of [1048576,2147483648])rows.push(await new Promise((resolve,reject)=>{const w=new Worker(new URL(import.meta.url),{workerData:{base,dir:process.argv[2]}});let r;w.on('message',x=>r=x);w.on('error',reject);w.on('exit',n=>n?reject(Error('Worker '+n)):resolve(r));}));fs.writeFileSync(process.argv[3],JSON.stringify({status:'PASS',rows},null,2)+'\n');}
else{
 process.on('uncaughtException',e=>{console.error(e.stack??String(e));process.exit(1);});
 const {base,dir}=workerData,read=n=>JSON.parse(fs.readFileSync(path.join(dir,n))),mods=read('modules.json'),material=read('materialized-'+base+'.json'),NIL=77825,T=77838,tcr=256,registry=4096,reserved=4;
 const memory=new WebAssembly.Memory({initial:Math.ceil((base+65536)/65536),maximum:32769,shared:true}),view=new DataView(memory.buffer),get=p=>view.getUint32(p,true),store=(p,v)=>view.setUint32(p,v,true),set=(n,v)=>store(tcr+n,v);
 new Uint8Array(memory.buffer,base,material.image.length/2).set(Buffer.from(material.image,'hex'));const roots=material.roots;
 const vector=p=>{assert.equal(p%8,6);assert.equal(get(p-6)%256,250);return Array.from({length:get(p-6)>>>8},(_,i)=>get(p-2+4*i));};
 const table=new WebAssembly.Table({element:'anyfunc',initial:128}),tail_table=new WebAssembly.Table({element:'anyfunc',initial:128}),call_error=new WebAssembly.Tag({parameters:['i32']}),type_error=new WebAssembly.Tag({parameters:['i32','i32']}),nonlocal_exit=new WebAssembly.Tag({parameters:['i32']});
 const stub=new WebAssembly.Module(fs.readFileSync(new URL('stub.wasm',import.meta.url)));store(registry,128);store(registry+4,1);
 const bytes=new Map(mods.map(m=>[m.name,fs.readFileSync(path.join(dir,m.name+'.wasm'))])),binaries=mods.map(m=>({name:m.name,sha256:sha(bytes.get(m.name))})),codes=Object.fromEntries(mods.map((m,i)=>[m.name,4*(reserved+i)])),handles={};
 const symbol=p=>{store(p,1850);for(let i=1;i<8;i++)store(p+4*i,NIL);store(p+28,0);return p+6;};
 const symbols={},bindingSymbols=mods.filter(m=>m.top).map((m,i)=>{const address=symbol(600000+32*i);symbols[m.name]=address;return {name:['WASM32-COMPILER',m.name.toUpperCase()],address};});
 const extras=[...new Set(mods.flatMap(m=>inspect(bytes.get(m.name)).imports.filter(i=>i.module==='symbols').map(i=>i.name)))].filter(n=>!(n in symbols));
 for(let i=0;i<extras.length;i++)symbols[extras[i]]=symbol(610000+32*i);
 symbols.condition_registry=650006;symbols.error_message=680006;symbols.expected_function=symbols.expected_function??symbol(614000);
 store(symbols.condition_handlers+22,4);store(symbols.condition_restarts+22,8);store(symbols.debugger_hook+22,12);
 store(630000,4*256+250);[243,NIL,NIL,NIL].forEach((v,i)=>store(630004+4*i,v));set(104,630004);set(108,4);
 // Class rows are the accepted native-derived twelve plus the real U1
 // NO-APPLICABLE-METHOD-EXISTS layout. No proxy condition is introduced.
 const conditionClasses=[['CONDITION',1,[]],['SIMPLE-CONDITION',9,['FORMAT-CONTROL','FORMAT-ARGUMENTS']],['SIMPLE-ERROR',31,['FORMAT-CONTROL','FORMAT-ARGUMENTS']],['TYPE-ERROR',39,['DATUM','EXPECTED-TYPE','FORMAT-CONTROL']],['CONTROL-ERROR',71,[]],['SIMPLE-WARNING',393,['FORMAT-CONTROL','FORMAT-ARGUMENTS']],['PROGRAM-ERROR',519,[]],['SIMPLE-PROGRAM-ERROR',527,['FORMAT-CONTROL','FORMAT-ARGUMENTS','CONTEXT']],['UNDEFINED-FUNCTION',1031,['NAME','ERROR-TYPE']],['UNBOUND-VARIABLE',2055,['NAME','ERROR-TYPE']],['STORAGE-CONDITION',4099,[]],['ERROR',7,[]],['NO-APPLICABLE-METHOD-EXISTS',8199,['GF','ARGS']]];
 const vec=(p,values,tag=250)=>{store(p,256*values.length+tag);values.forEach((v,i)=>store(p+4+4*i,v));return p+6;},shapes=read('native-condition-classes.json');assert.equal(shapes.length,13);let stringTop=660000;
 const string=text=>{const p=stringTop;stringTop+=8*Math.ceil((4+4*text.length)/8);assert(stringTop<680000);store(p,256*text.length+191);Array.from(text).forEach((c,i)=>store(p+4+4*i,c.codePointAt(0)));return p+6;};
 const rows=[];for(let i=0;i<13;i++){const [name,mask,slots]=conditionClasses[i],p=651000+512*i;assert.equal(shapes[i].name,name);assert.deepEqual(shapes[i].slots.map(s=>s.name),slots);const names=slots.map((_,j)=>symbol(p+320+32*j)),className=symbol(p+256),wrapperName=symbol(p+288);const slotNames=vec(p+64,names),defaults=vec(p+88,shapes[i].slots.map(s=>s.default===null?NIL:typeof s.default==='string'?string(s.default):83));store(p+112,882);store(p+116,0);store(p+120,NIL);store(p+124,p+134);vec(p+128,[p+118,className,NIL],106);const wrapper=vec(p,[wrapperName,4*i,p+118,slotNames,NIL,NIL,NIL,NIL,NIL,NIL,NIL,4*i,mask*4]);rows.push(vec(p+160,[wrapper,mask*4,defaults]));}vec(650000,rows);
 store(680000,250);let end=base+material.image.length/2;
 const catalog=mods.map((m,i)=>{const b=bytes.get(m.name),x=inspect(b),a=vector(get(roots[i]-2));return {name:m.name,slot:reserved+i,code:reserved+i,version:4,signature:17,role:23,sha256:sha(b),profile:PROFILE,imports:x.imports,entries:Object.fromEntries(x.exports.map(e=>[e.name,{index:e.index,role:e.name}])),ranges:entryRanges(b),arity:[a[1]/4,a[2]/4,...a.slice(3,6).map(v=>v===T),[]],captures:m.captures};});
 for(let i=0;i<mods.length;i++)if(mods[i].top){const p=end;end+=32;[1578,codes[mods[i].name],NIL,4,get(roots[i]-2),get(roots[i]+2),roots[i],0].forEach((v,j)=>store(p+4*j,v));handles[mods[i].name]=p+6;}
 set(48,end);set(52,base+65536);set(56,base);set(76,700000);set(80,700000);set(84,900000);set(88,920000);set(92,920000);set(96,940000);
 const imports={env:{memory,tcr,table,tail_table,code_registry:registry,call_error,type_error,nonlocal_exit},symbols,codes,keywords:{}},owner=new BindingInstaller({memory,table,tail_table,call_error,nonlocal_exit,stub,registry,reserved,symbols:bindingSymbols,keywords:[]});
 const manifest={version:1,phase:'boot',generation:1,previous:null,modules:catalog,functions:Object.entries(handles).map(([module,object])=>({module,object})),bindings:bindingSymbols.map(s=>({name:s.name,object:handles[s.name[1].toLowerCase()],previous:NIL}))};
 const installed=owner.install(manifest,bindingSymbols.map(s=>s.name),catalog,n=>bytes.get(n),imports),observations=[],checks=[];
 function invoke(name,args){new Uint8Array(memory.buffer,65536,32768).fill(0x55);set(64,65536);set(68,65536);set(72,98304);set(116,0);set(120,66032);set(124,66544);set(128,0);set(140,0);set(148,0);set(192,0);args.forEach((v,i)=>store(65536+4*i,v));let pair,error;try{pair=table.get(codes[name]/4)(handles[name],args.length);}catch(e){if(!e.is?.(call_error))throw e;error=e.getArg(call_error,0);}assert.deepEqual([get(tcr+64),get(tcr+128),get(tcr+140),get(tcr+148)],[65536,0,0,0]);assert.deepEqual([get(630008),get(630012),get(630016)],[NIL,NIL,NIL],'dynamic chains restored');const values=error===undefined?Array.from({length:pair[1]>>>0},(_,i)=>get(66032+4*i)):[];observations.push({name,args,values,...error===undefined?{}:{error}});return {values,error};}
 function cons(a,d){const p=get(tcr+48);assert(p+8<=get(tcr+52));store(p,d);store(p+4,a);set(48,p+8);return p+1;}
 const head=p=>get(p+3),tail=p=>get(p-1),nth=(p,i)=>{while(i--)p=tail(p);return head(p);},record=(key,fn)=>cons(key,handles[fn]),list=(...xs)=>xs.reduceRight((d,a)=>cons(a,d),NIL);
 const nativeGraph=read('native-behavior.json');function decode(g){const nodes=Object.fromEntries(g.objects.map(o=>[o.id,o.value]));function d(v){if(v.ref){const n=nodes[v.ref];return n.kind==='string'?String.fromCodePoint(...n.value):n.elements.map(d);}if(v.kind==='integer')return Number(v.value);return v.value==='nil'?null:true;}return g.roots.map(d);}
 const native=decode(nativeGraph),flow=decode(read('native-flow.json'))[0],scenarios=[];
 const want=(label,r,expected)=>{assert.equal(r.error,undefined,label+' error');assert.deepEqual(r.values,expected.map(v=>v===true?T:v===null?NIL:v*4),label);checks.push({label,values:r.values});};
 for(const encapsulated of [false,true]){
  const nr=native[encapsulated?1:0],trace=cons(NIL,NIL),mA=record(T,'gd_method_a'),mB=record(12,'gd_method_b'),mC=record(T,'gd_method_c');
  const factory=invoke('gd_factory',[list(mA),handles.gd_method_a,encapsulated?T:NIL,trace]);assert.equal(factory.values.length,2);const [gf,state]=factory.values;
  const call=()=>invoke('gd_probe',[gf,12]);want('universal',call(),nr[1]);
  invoke('gd_add',[state,mB]);want('specific',call(),nr[2]);want('table miss',invoke('gd_probe',[gf,36]),nr[3]);
  invoke('gd_remove',[state,mB]);want('remaining',call(),nr[4]);
  invoke('gd_remove',[state,mA]);assert.equal(head(state),NIL,'last method removed');assert.equal(nth(state,encapsulated?3:1),handles.gd_missing,'empty dcode publication');want('empty registry',call(),nr[6]);
  // A later raw store cannot resurrect a removed method, regardless of mode.
  invoke('gd_raw_store',[state,handles.gd_method_a]);want('stale raw store',call(),nr[6]);
  const cleanup=cons(0,NIL);want('cleanup condition transfer',invoke('gd_cleanup',[gf,12,cleanup]),flow[0]);assert.equal(head(cleanup),284);
  want('resignalled condition',invoke('gd_resignal',[gf,12]),flow[1]);
  assert.equal(invoke('gd_decline',[gf,12]).error,15,'declined no-applicable fatal boundary');
  want('continue reinstalls method',invoke('gd_continue',[gf,state,handles.gd_method_c,12]),nr[7]);want('replacement remains live',call(),nr[7]);
  // Emptying a table-selected registry must also replace that code, and old
  // callable references must read the same live registry after every update.
  invoke('gd_add',[state,mB]);want('table replacement',call(),[20,21]);
  invoke('gd_remove',[state,head(tail(head(state)))]);invoke('gd_remove',[state,mB]);assert.equal(head(state),NIL,'last table method removed');assert.equal(nth(state,encapsulated?3:1),handles.gd_missing,'empty table dcode publication');want('empty after table',call(),nr[6]);
  invoke('gd_add',[state,mC]);want('readd after table',call(),nr[7]);want('arity before dispatch',invoke('gd_arity',[gf]),flow[2]);
  let count=0;for(let p=head(trace);p!==NIL;p=tail(p)){assert.equal(head(p),4);count++;}assert.equal(count,encapsulated?15:0,'encapsulation preserved');scenarios.push({encapsulated,traceCalls:count,nativeDefect:nr[5],required:nr[6],resumed:nr[7]});
 }
 const order=decode(read('native-order.json'))[0],orderScenarios=[];
 for(const encapsulated of [false,true]){
  const trace=cons(NIL,NIL),[gf,state]=invoke('gd_factory',[NIL,handles.gd_method_a,encapsulated?T:NIL,trace]).values;
  want('initial empty registry',invoke('gd_probe',[gf,12]),[901,true,3]);
  invoke('gd_add',[state,record(12,'gd_method_b')]);want('eql only',invoke('gd_probe',[gf,12]),order[0]);want('nonempty no-match',invoke('gd_probe',[gf,36]),order[1]);
  invoke('gd_add',[state,record(T,'gd_method_a')]);want('specificity after universal',invoke('gd_probe',[gf,12]),order[2]);
  invoke('gd_add',[state,record(12,'gd_method_c')]);want('method replacement',invoke('gd_probe',[gf,12]),order[3]);
  orderScenarios.push({encapsulated,expected:order});
 }
 const registryRefusals=[];
 const [empty]=invoke('gd_factory',[NIL,handles.gd_missing,NIL,cons(NIL,NIL)]).values;
 for(const [name,header]of [['short-registry',11*256+250],['oversize-registry',14*256+250],['wrong-registry-kind',13*256+191],['missing-new-class',12*256+250]]){
  store(650000,header);const r=invoke('gd_probe',[empty,12]);assert.equal(r.error,5,name);registryRefusals.push({name,code:r.error});store(650000,13*256+250);
 }
 want('registry restored',invoke('gd_probe',[empty,12]),[901,true,3]);
 parentPort.postMessage({status:'PASS',base,modules:mods.length,classes:shapes,manifest,installed,binaries,scenarios,orderScenarios,registryRefusals,checks,observations});
}
