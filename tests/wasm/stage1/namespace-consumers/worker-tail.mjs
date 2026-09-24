bytes(tcr,256).fill(0);bytes(config,96).fill(0);
for(const [offset,value] of [[0,1],[8,1],[32,2],[48,base],[52,base+size],[56,base],[68,131072],[72,196608],
 [128,root],[80,700000],[76,700000],[84,780000],[88,900000],[92,900000],[96,1000000],[120,132352],[124,132512],[104,680000],[200,7]])put(tcr+offset,value);
put(config,tcr);put(config+16,other);put(config+20,other+size);
put(config+68,262144);put(config+72,4600000);put(config+80,20971520);
gen.reset(movingPools[base],true);
const packageState=await packages({dir,memory,gen,owners:ownerNames,get,put,addRoot});
services();
for(const [pkg,name,target] of JSON.parse(fs.readFileSync(dir+'/ready-bindings.json'))) {
 const symbol=(p,n)=>gen.ownerWords.get(ownerNames.find(x=>x.package===p&&x.name===n).id);
 put(symbol(pkg,name)+6,get(symbol('CCL',target)+6));
}
let requests=0,fileArgs;
const fileRun=fileClient({memory,tcr,collect:()=>{if(workerData.movement)collect();},
 allocate:n=>{serviceOwner.atSafepoint(o=>o.ensure(n));const p=get(tcr+48);put(tcr+48,p+n);return p;},
 pinned:[{start:2097152,end:gen.imageEnd}],
 post:request=>{requests++;parentPort.postMessage({type:'request',...request});}});
const file=args=>{const a=Array.from({length:4},(_,i)=>get(args+4*i));if(a[0]===4)fileArgs={args:a,header:get(a[2]-6)};return fileRun(args);};
const adapter=new WebAssembly.Instance(new WebAssembly.Module(fs.readFileSync(dir+'/file-adapter.wasm')),{env:gen.env,files:{run:file}});
const id=4;[id,4,17,23].forEach((v,i)=>put(4096+8+16*id+4*i,v));gen.env.table.set(id,adapter.exports.entry);gen.env.tail_table.set(id,adapter.exports.tail_entry);
const leaf=1170000;[1578,id*4,NIL,4,NIL,NIL,NIL,0].forEach((v,i)=>put(leaf+4*i,v));
const requestSymbol=ownerNames.find(r=>r.package==='CCL'&&r.name==='%WASM-FILE-REQUEST');put(gen.ownerWords.get(requestSymbol.id)+6,leaf+6);
const expected=native[0];const args=expected.args.map(encode);
const setfNames=JSON.parse(fs.readFileSync(dir+'/compiled/setf-bindings.json')).reduceRight((tail,[name,symbol])=>[[{symbol:name},{symbol}],tail],null);
put(root,0);put(root+4,args.length+2);args.forEach((v,i)=>put(root+8+4*i,v));put(root+8+4*args.length,encode({string:workerData.cclRoot}));put(root+12+4*args.length,encode(setfNames));
put(config+76,gen.extraRoots.length);gen.extraRoots.forEach((slot,i)=>put(4600000+4*i,slot));
parentPort.postMessage({type:'memory',memory});
const debug=[];
try {
 const row=name=>{const sym=ownerNames.find(x=>x.package==='WASM32-COMPILER'&&x.name===name);return gen.mods.find(m=>m.function===sym.id&&m.cplMode).name;};
 console.log('STATUS',gen.invoke(row('READY-IMAGE-STATUS'),args).map(decode));
 console.log('INITIALIZE',gen.invoke(row('READY-INITIALIZE'),args).map(decode));
 for(const [name,target] of JSON.parse(fs.readFileSync(dir+'/compiled/load-bindings.json'))){const fn=gen.functions.get(target);if(fn)put(gen.ownerWords.get(name)+6,fn);}
 const initializers=JSON.parse(fs.readFileSync(dir+'/compiled/initializers.json'));
 const lockOwner=ownerNames.find(x=>x.package==='CCL'&&x.name==='MAKE-LOCK').id;
 const streamInitializers=initializers.filter(name=>gen.mods.find(m=>m.name===name).symbols.some(([,owner])=>owner===lockOwner));
 assert.equal(streamInitializers.length,1);
 for(const name of initializers.filter(name=>!streamInitializers.includes(name)))console.log('TOPLEVEL',gen.invoke(name,[]).map(decode));
 const supportSymbol=ownerNames.find(x=>x.package==='CCL'&&x.name==='%WASM-NAMESPACE-SUPPORT-INITIALIZE');
 const support=gen.mods.find(m=>m.function===supportSymbol.id&&m.cplMode);
 assert.deepEqual(gen.invoke(support.name,[]),[T]);
 for(const name of streamInitializers)console.log('TOPLEVEL',gen.invoke(name,[]).map(decode));
 const find=gen.mods.find(m=>m.function===ownerNames.find(x=>x.name==='FIND-CLASS'&&x.package==='COMMON-LISP').id&&m.cplMode);
 const io=gen.ownerWords.get(ownerNames.find(x=>x.name==='IO-BUFFER'&&x.package==='CCL').id);
 debug.push(gen.invoke(find.name,[io,NIL]));
 console.log('TYPES',gen.invoke(row('NAMESPACE-TYPE-INITIALIZE'),[get(root+8),get(root+16)]).map(decode));
 const foreignValues=workerData.foreign?gen.invoke(row('NAMESPACE-FOREIGN-CHECK'),[]).map(decode):null;
 console.log('METHODS',gen.invoke(row('NAMESPACE-METHOD-INITIALIZE'),[]).map(decode));
 debug.push(gen.invoke(find.name,[io,NIL]));
 if(workerData.namespace){
  const symbol=ownerNames.find(x=>x.package==='CCL'&&x.name==='%WASM-NAMESPACE-INITIALIZE');
  const initializer=gen.mods.find(m=>m.function===symbol.id&&m.cplMode);
  debug.push(gen.invoke(initializer.name,[get(root+12)]).map(decode));
  assert.deepEqual(gen.invoke(row('NAMESPACE-ROOT-CHECK'),[]).map(decode),
    [{vector:[true,true,{string:'/other/'},{string:'/other/a.bin'},{string:'/ccl/'}]}],
    'namespace root publication and refusal atomicity');
 }
 const values=gen.invoke(expected.name,[get(root+8)]).map(decode);
 const tableRefusals=gen.invoke(row('NAMESPACE-TABLE-REFUSALS'),[]).map(decode);
 let refused=tableRefusals[0],tableRefusalCount=0;
 while(refused){assert.equal(refused[0],true,'table option refusal');tableRefusalCount++;refused=refused[1];}
 assert.equal(tableRefusalCount,12);
 const controls=checkBoundaries({memory,gen,row,get,put,tcr,collect});
 parentPort.postMessage({type:'done',values,foreignValues,controls,tableRefusalCount,requests,collections:internalCollections,packageState});
} catch(e) {let typeErrorValue;try{const match=String(e).match(/type_error (\d+)/);if(match)typeErrorValue=decode(Number(match[1]));}catch{}parentPort.postMessage({type:'failed',message:e.stack,heap:[get(tcr+56),get(tcr+48),get(tcr+52)],internalCollections,retryCollections,requests,debug,fileArgs,serviceFailure,failedModule:gen.mods[get(6009312)]?.name??get(6009312),recent:Array.from({length:Math.min(1024,get(6000000)/4)},(_,i)=>{const n=(get(6000000)/4-1-i)%1024,m=gen.mods[get(6000016+4*n)];return m?.function?ownerNames.find(x=>x.id===m.function)?.name:m?.name;}),snapshotArgs:Array.from({length:8},(_,i)=>get(6009400+4*i)),failedClass:{word:get(6005108),header:get(6005108)>=6?get(get(6005108)-6):null},unbound:ownerNames.find(x=>gen.ownerWords.get(x.id)===get(6005100)),classOf:{word:get(6005096),header:get(6005096)>=6?get(get(6005096)-6):null},typeErrorValue,lastClass:decode(get(6005080)),missing:ownerNames.find(x=>gen.ownerWords.get(x.id)===get(6000004)),implicitSite:[get(6009472),get(6009476),get(6009480),gen.mods[get(6009484)]?.name],destructureArgs:Array.from({length:4},(_,i)=>{try{return decode(get(6009456+i*4));}catch{return get(6009456+i*4);}}),errorArgs:Array.from({length:4},(_,i)=>{try{return decode(get(6005000+i*4));}catch{return get(6005000+i*4);}}),implicit:Array.from({length:3},(_,i)=>{try{return decode(get(6005048+i*4));}catch{return get(6005048+i*4);}}),trace:Array.from({length:Math.min(40,get(6009300)/4)},(_,i)=>{const n=(get(6009300)/4-1-i)%1024,m=gen.mods[get(6005200+4*n)];return m?.function?ownerNames.find(x=>x.id===m.function):m?.name;})});}
