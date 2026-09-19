import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';
import {Worker,isMainThread,workerData,parentPort} from 'node:worker_threads';
import {BindingInstaller} from './installer.mjs';import {entryRanges} from './ranges.mjs';
import {PROFILE,sha} from './loader.mjs';import {inspect} from './binary.mjs';
if(isMainThread){const rows=[];for(const base of [1048576,2147483648])rows.push(await new Promise((resolve,reject)=>{const w=new Worker(new URL(import.meta.url),{workerData:{base,dir:process.argv[2]}});let r;w.on('message',x=>r=x);w.on('error',reject);w.on('exit',n=>n?reject(Error('Worker '+n)):resolve(r));}));fs.writeFileSync(process.argv[3],JSON.stringify({status:'PASS',rows},null,2)+'\n');}
else {
 process.on('uncaughtException',e=>{console.error(e.stack??String(e));process.exit(1);});
 const {dir,base}=workerData,read=n=>JSON.parse(fs.readFileSync(path.join(dir,n))),mods=read('modules.json'),material=read('materialized-'+base+'.json'),NIL=77825,T=77838;
 const memory=new WebAssembly.Memory({initial:Math.ceil((base+65536)/65536),maximum:32769,shared:true}),view=new DataView(memory.buffer),tcr=256,registry=4096,reserved=4;
 const get=p=>view.getUint32(p,true),put=(p,x)=>view.setUint32(p,x,true),set=(n,v)=>put(tcr+n,v);
 new Uint8Array(memory.buffer,base,material.image.length/2).set(Buffer.from(material.image,'hex'));const roots=material.roots;
 const table=new WebAssembly.Table({element:'anyfunc',initial:64}),tail_table=new WebAssembly.Table({element:'anyfunc',initial:64});
 const call_error=new WebAssembly.Tag({parameters:['i32']}),type_error=new WebAssembly.Tag({parameters:['i32','i32']}),nonlocal_exit=new WebAssembly.Tag({parameters:['i32']});
 const stub=new WebAssembly.Module(fs.readFileSync(new URL('stub.wasm',import.meta.url))),reservedStub=new WebAssembly.Instance(stub,{loader:{slot:0,table,tail_table,install:()=>{throw Error('RESERVED_EXECUTED');}}});
 for(let i=0;i<reserved;i++){table.set(i,reservedStub.exports.entry);tail_table.set(i,reservedStub.exports.tail_entry);}put(registry,64);put(registry+4,1);
 const names=[['BINDING-A','F'],['BINDING-B','F'],['BINDING-A','ALIAS'],['BINDING-A','f']],symbols=names.map((name,i)=>({name,address:600006+i*32}));
 const keywordSymbols=[{name:'KEYWORD::ALIAS',address:620006}],globals={condition_handlers:610006,condition_registry:610038,debugger_hook:610070,error_message:610102,expected_function:610134};
 for(const address of [...symbols.map(s=>s.address),...keywordSymbols.map(k=>k.address),...Object.values(globals),620038]){put(address-6,1850);for(let i=1;i<8;i++)put(address-6+4*i,NIL);put(address+22,0);}
 set(104,630000);set(108,2);put(630000,243);put(630004,243);
 const bytes=new Map(mods.map(m=>[m.name,fs.readFileSync(path.join(dir,m.name+'.wasm'))]));
 assert.equal(sha(bytes.get('one')),sha(bytes.get('two')),'separately named identical code');
 const codes=Object.fromEntries(mods.map((m,i)=>[m.name,4*(reserved+i)])),handles={};let end=base+material.image.length/2;
 function vector(p){assert.equal(p%8,6);const h=get(p-6);assert.equal(h%256,250);return Array.from({length:Math.floor(h/256)},(_,i)=>get(p-2+4*i));}
 function arity(pool){const a=vector(get(pool-2));return [a[1]/4,a[2]/4,...a.slice(3,6).map(x=>x===T),vector(a[6]).map(x=>keywordSymbols.find(k=>k.address===x).name)];}
 const catalog=mods.map((m,i)=>{const b=bytes.get(m.name),x=inspect(b);return {name:m.name,slot:reserved+i,code:reserved+i,version:4,signature:17,role:23,sha256:sha(b),profile:PROFILE,imports:x.imports,entries:Object.fromEntries(x.exports.map(e=>[e.name,{index:e.index,role:e.name}])),ranges:entryRanges(b),arity:arity(roots[i]),captures:m.captures};});
 const native=read('native-metadata.json');function unpack(g){const nodes=Object.fromEntries(g.objects.map(o=>[o.id,o.value]));function d(v){if(v.ref){const n=nodes[v.ref];return n.kind==='string'?String.fromCodePoint(...n.value):n.elements.map(d);}if(v.symbol)return v.symbol;if(v.kind==='integer')return Number(v.value);return v.value==='nil'?null:true;}return g.roots.map(d);}
 for(const [name,args,keys]of unpack(native)){const c=catalog.find(r=>r.name===(name==='make'?'make_inner_1':name));assert.deepEqual(c.arity,[args[0],args[1],!!args[2],args[3]!==null,!!args[4],keys],'native arity '+name);}
 for(let i=0;i<mods.length;i++)if(mods[i].top){const p=end;end+=32;[1578,codes[mods[i].name],NIL,4,get(roots[i]-2),get(roots[i]+2),roots[i],0].forEach((x,j)=>put(p+4*j,x));handles[mods[i].name]=p+6;}
 set(48,end);set(56,base);set(52,base+65536);set(80,700000);set(76,700000);set(84,900000);
 const imports={env:{memory,tcr,table,tail_table,code_registry:registry,call_error,type_error,nonlocal_exit},symbols:globals,keywords:{alias:620006,'allow-other-keys':620038},codes};
 const owner=new BindingInstaller({memory,table,tail_table,call_error,nonlocal_exit,stub,registry,reserved,symbols,keywords:keywordSymbols});
 const observations=[],publications=[],refusals=[],manifests=[];
 function publish(m,required,catalog){const result=owner.install(m,required,catalog,n=>bytes.get(n),imports);for(const b of m.bindings){const sym=symbols.find(s=>JSON.stringify(s.name)===JSON.stringify(b.name));assert.equal(get(sym.address+6),b.object,'published package binding '+JSON.stringify(b.name));}manifests.push(m);publications.push(result);}
 function invoke(name,args=[],self=handles[name]){new Uint8Array(memory.buffer,65536,32768).fill(0x55);set(64,65536);set(68,65536);set(72,98304);set(116,0);set(120,66000);set(124,66032);set(128,0);set(140,0);set(148,0);args.forEach((v,i)=>put(65536+4*i,v));let pair;try{pair=table.get(codes[name]/4)(self,args.length);}catch(e){console.error({name,args,code:e.is?.(call_error)?e.getArg(call_error,0):null});throw e;}assert.equal(pair[1]>>>0,get(tcr+116));assert.deepEqual([get(tcr+64),get(tcr+128),get(tcr+140)],[65536,0,0]);const values=Array.from({length:pair[1]>>>0},(_,i)=>get(66000+4*i));observations.push({name,args,values});return values[0];}
 const cell=i=>symbols[i].address+6,call=i=>invoke('call0',[symbols[i].address]);
 const bind=(i,object)=>({name:names[i],object,previous:get(cell(i))});
 const manifest=(rows,functions,bindings)=>({version:1,phase:owner.state().generation?'runtime':'boot',generation:owner.state().generation+1,previous:owner.state().head,modules:structuredClone(rows),functions,bindings});
 const capture=()=>({memory:[[registry,1032],[tcr,224],[base,65536],...symbols.map(s=>[s.address-6,32])].map(([p,n])=>Buffer.from(new Uint8Array(memory.buffer,p,n)).toString('hex')),table:Array.from({length:64},(_,i)=>table.get(i)),tail:Array.from({length:64},(_,i)=>tail_table.get(i)),state:owner.state()});
 function reject(label,m,c,expected,edit,diagnostic,importMap=imports){const b=structuredClone(m),r=structuredClone(c);edit(b,r);const before=capture();let error;try{owner.install(b,expected,r,n=>bytes.get(n),importMap);}catch(e){error=e;}assert(error,label+' must refuse');const reason=error.is?.(call_error)?'CALL_ERROR_'+error.getArg(call_error,0):error.message;assert.equal(reason,diagnostic,label);assert.deepEqual(capture(),before,label+' atomic refusal');refusals.push({label,reason});}
 const bootRows=catalog.filter(r=>r.name!=='replacement'),functions=Object.entries(handles).filter(([n])=>n!=='replacement').map(([module,object])=>({module,object}));
 const boot=manifest(bootRows,functions,[bind(0,handles.one),bind(1,handles.two),bind(2,handles.one),bind(3,handles.two)]);
 for(const [label,edit,reason]of [
 ['missing-alias',m=>m.bindings.pop(),'COMPLETE_BINDINGS'],['duplicate-alias',m=>m.bindings[1]=m.bindings[0],'COMPLETE_BINDINGS'],['case-lost',m=>m.bindings[3].name[1]='F','COMPLETE_BINDINGS'],['package-lost',m=>m.bindings[1].name[0]='BINDING-A','COMPLETE_BINDINGS'],
 ['wrong-generation',m=>m.generation++,'MANIFEST_CHAIN'],['wrong-phase',m=>m.phase='runtime','MANIFEST_CHAIN'],['missing-module',m=>m.modules.pop(),'COMPLETE_MODULES'],['conflicting-module',m=>m.modules[1]=m.modules[0],'MODULE_IDENTITY'],['unknown-function',m=>m.bindings[0].object=0,'BINDING_FUNCTION'],['duplicate-function',m=>m.functions.push(m.functions[0]),'FUNCTION_DUPLICATE'],['wrong-previous',m=>m.bindings[0].previous=0,'BINDING_PREVIOUS']])reject(label,boot,bootRows,names,edit,reason);
 for(const [label,edit,reason]of [
 ['reserved-slot',r=>{r.slot=0;r.code=0;},'SLOT_OWNER'],['past-table',r=>{r.slot=64;r.code=64;},'SLOT_OWNER'],['wrong-range-start',r=>r.ranges[0].start++,'ENTRY_RANGES'],['wrong-range-end',r=>r.ranges[1].end--,'ENTRY_RANGES'],['missing-entry-range',r=>r.ranges.pop(),'ENTRY_RANGES'],['wrong-entry-index',r=>r.entries.entry.index++,'EXPORT_ROLE'],['wrong-arity',r=>r.arity[0]++,'ARITY_IDENTITY'],['wrong-digest',r=>r.sha256='0'.repeat(64),'BINARY_DIGEST'],['wrong-profile',r=>r.profile='unknown','PROFILE']])reject(label,boot,bootRows,names,(m,c)=>{const n=label==='wrong-arity'?'one':'make';edit(c.find(r=>r.name===n));m.modules=structuredClone(c);},reason);
 reject('missing-global-import',boot,bootRows,names,()=>{},'CALL_ERROR_7',{...imports,codes:{}});
 reject('late-global-import',boot,bootRows,names,m=>m.modules.push(m.modules.shift()),'CALL_ERROR_7',{...imports,codes:{}});
 reject('conflicting-slot',boot,bootRows,names,(m,c)=>{c[1].slot=c[0].slot;c[1].code=c[0].code;m.modules=structuredClone(c);},'SLOT_OWNER');
 for(const [label,offset,value,reason]of [
 ['short-function',-6,1322,'OBJECT_HEADER'],['wrong-function-code',-2,0,'FUNCTION_IDENTITY'],['missing-owner-arity',10,NIL,'METADATA_IDENTITY'],['missing-owner-debug',14,NIL,'METADATA_IDENTITY'],['unexpected-environment',2,T,'EMPTY_ENVIRONMENT'],['invalid-pool',18,NIL,'POOL_SHAPE']]){
  const p=handles.one+offset,old=get(p);put(p,value);reject(label,boot,bootRows,names,()=>{},reason);put(p,old);
 }

 publish(boot,names,bootRows);
 const initial=names.map((_,i)=>call(i)/4);assert.deepEqual(initial,[7,7,7,7]);
 const x=invoke('make',[76]),y=invoke('make',[164]);assert.equal(get(x-2),get(y-2),'one entry, two closures');assert.notEqual(get(x+2),get(y+2),'distinct environment');
 const closures=manifest([], [{module:'make_inner_1',object:x},{module:'make_inner_1',object:y}],[bind(0,x),bind(1,y),bind(2,x)]);
 reject('missing-shared-alias',closures,[],names.slice(0,3),m=>m.bindings.pop(),'COMPLETE_BINDINGS');
 publish(closures,names.slice(0,3),[]);
 const before=names.map((_,i)=>call(i)/4),old=get(cell(0)),mutate=[invoke('call1',[symbols[0].address,124])/4,call(2)/4,call(1)/4];
 const rebind=manifest([],[{module:'one',object:handles.one}],[bind(0,handles.one)]);publish(rebind,[names[0]],[]);
 const replaced=[call(0)/4,invoke('call0',[old])/4,call(2)/4,call(1)/4];
 const nextRows=catalog.filter(r=>r.name==='replacement'),replace=manifest(nextRows,[{module:'replacement',object:handles.replacement}],[bind(0,handles.replacement)]);
 reject('stale-runtime-manifest',replace,nextRows,[names[0]],m=>m.previous=null,'MANIFEST_CHAIN');
 reject('reuse-live-slot',replace,nextRows,[names[0]],(m,c)=>{c[0].slot=bootRows[0].slot;c[0].code=c[0].slot;m.modules=structuredClone(c);},'SLOT_OWNER');
 publish(replace,[names[0]],nextRows);
 const after=[call(0)/4,invoke('call1',[old,148])/4,call(2)/4,call(1)/4,call(3)/4];
 assert.deepEqual([before,mutate,replaced,after],unpack(read('native-behavior.json'))[0],'native package bindings and redefinition');assert.equal(invoke('call0',[handles.one]),28,'old code survives');
 assert.equal(invoke('call2',[handles.keyword,620006,172]),172,'keyword callable');
 for(let i=0;i<reserved;i++){assert.equal(table.get(i),reservedStub.exports.entry);assert.equal(tail_table.get(i),reservedStub.exports.tail_entry);}
 parentPort.postMessage({status:'PASS',base,modules:mods.length,signatureRecords:catalog.map(c=>({name:c.name,arity:c.arity,captures:c.captures,ranges:c.ranges})),nativeSignatures:unpack(native).length,identicalCode:[sha(bytes.get('one')),sha(bytes.get('two'))],initial,before,mutate,replaced,after,observations,manifests,publications,refusals});
}
