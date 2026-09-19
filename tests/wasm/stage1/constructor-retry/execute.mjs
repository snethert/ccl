import fs from 'node:fs';import assert from 'node:assert/strict';import {createHash} from 'node:crypto';
import {inspect as legacyInspect} from './binary.mjs';
import {LazyLoader,OWNER_PROFILE,sha} from './loader.mjs';
import {allocationService} from './allocation-service.mjs';
import {CollectorOwner} from './collector-owner.mjs';
const [dir,collectorPath,output]=process.argv.slice(2),read=n=>JSON.parse(fs.readFileSync(dir+'/'+n));
const mods=read('modules.json'),cases=read('cases.json'),native=read('native.json'),bytes=fs.readFileSync(collectorPath),digest=createHash('sha256').update(bytes).digest('hex');
const NIL=77825,T=77838,tcr=1024,ROOT=131064,OUT=139264,A=2097152,B=2162688;
const modules=new Map(mods.map(m=>[m.name,new WebAssembly.Module(fs.readFileSync(dir+'/installed/'+m.name+'.wasm'))]));
for(const m of mods){const b=fs.readFileSync(dir+'/installed/'+m.name+'.wasm');assert.throws(()=>legacyInspect(b),/FUNCTION_IMPORT/,'legacy loader refuses new capability');const imports=WebAssembly.Module.imports(modules.get(m.name));assert.deepEqual(imports.filter(i=>i.kind==='function'),[{module:'owner',name:'ensure',kind:'function'},...(process.env.CONSTRUCTOR_PRESSURE?[{module:'pressure',name:'fill',kind:'function'}]:[])]);}
const rows=[];let collections=0,growths=0;
for(const scenario of [{cap:8},{cap:16},{cap:32},{cap:128},{cap:512},{cap:512,empty:true},{cap:32768,high:true},{cap:32,fail:true}])for(const c of cases){
 if(process.env.RETRY_CASE&&c.id!==process.env.RETRY_CASE)continue;
 if(process.env.OWNER_NESTED&&(scenario.empty||scenario.fail))continue;
 if(scenario.fail&&c.id!=='failure_live')continue;const cap=scenario.cap;const A=scenario.high?2147483648:2097152,B=scenario.high?2147516416:2162688;
 const memory=new WebAssembly.Memory({initial:scenario.high?32769:48,maximum:scenario.fail?48:32769,shared:true});
 const load=p=>new DataView(memory.buffer).getUint32(p,true),store=(p,v)=>new DataView(memory.buffer).setUint32(p,v,true),get=o=>load(tcr+o),set=(o,v)=>store(tcr+o,v);
 const table=new WebAssembly.Table({element:'anyfunc',initial:mods.length+1}),tail_table=new WebAssembly.Table({element:'anyfunc',initial:mods.length+1});
 const call_error=new WebAssembly.Tag({parameters:['i32']}),type_error=new WebAssembly.Tag({parameters:['i32','i32']}),nonlocal_exit=new WebAssembly.Tag({parameters:['i32']});
 let imageTop=786432;const images=[];
 const allocImage=bytes=>{const p=imageTop;imageTop+=bytes;images.push({name:'image-'+p,role:'image',start:p,end:p+bytes});return p;};
 const symbol=()=>{const p=allocImage(32);store(p,1850);for(let j=1;j<8;j++)store(p+4*j,NIL);store(p+20,0);store(p+28,0);return p+6;};
 const symbols={},keywords={},codes={},handles={};
 mods.forEach((m,i)=>{codes[m.name]=4*(i+1);if(m.source){const p=allocImage(32);store(p,1578);[codes[m.name],NIL,4,NIL,NIL,NIL,0].forEach((v,j)=>store(p+4+4*j,v));handles[m.name]=p+6;symbols[m.name]=symbol();store(symbols[m.name]+6,p+6);}});
 for(const mod of modules.values())for(const imp of WebAssembly.Module.imports(mod)){
  if(imp.module==='symbols'&&symbols[imp.name]===undefined)symbols[imp.name]=symbol();
  if(imp.module==='keywords'&&keywords[imp.name]===undefined){keywords[imp.name]=symbol();store(keywords[imp.name]+2,keywords[imp.name]);store(keywords[imp.name]+14,8);}
 }
 for(const [i,n] of ['dyn_a','dyn_b','dyn_u'].entries())if(symbols[n]){store(symbols[n]+2,i===2?51:4*(101+2*i));store(symbols[n]+22,4*[31,127,255][i]);}
 for(const [i,n] of ['condition_handlers','condition_restarts','debugger_hook'].entries())if(symbols[n])store(symbols[n]+22,4*(i+3));

 const vector=(values,tag=250)=>{const p=allocImage(8*Math.ceil((4+4*values.length)/8));store(p,256*values.length+tag);values.forEach((x,i)=>store(p+4+4*i,x));return p+6;};
 const string=text=>{const p=allocImage(8*Math.ceil((4+4*text.length)/8));store(p,256*text.length+191);Array.from(text).forEach((c,i)=>store(p+4+4*i,c.codePointAt(0)));return p+6;};
 const names=['CONDITION','SIMPLE-CONDITION','SIMPLE-ERROR','TYPE-ERROR','CONTROL-ERROR','SIMPLE-WARNING','PROGRAM-ERROR','SIMPLE-PROGRAM-ERROR','UNDEFINED-FUNCTION','UNBOUND-VARIABLE','STORAGE-CONDITION','ERROR'];
 const masks=[1,9,31,39,71,393,519,527,1031,2055,4099,7];
 const slotNames=[[],['FORMAT-CONTROL','FORMAT-ARGUMENTS'],['FORMAT-CONTROL','FORMAT-ARGUMENTS'],['DATUM','EXPECTED-TYPE','FORMAT-CONTROL'],[],['FORMAT-CONTROL','FORMAT-ARGUMENTS'],[],['FORMAT-CONTROL','FORMAT-ARGUMENTS','CONTEXT'],['NAME','ERROR-TYPE'],['NAME','ERROR-TYPE'],[],[]];
 const shapes=read('native-condition-classes.json');assert.equal(shapes.length,12);
 symbols.condition_registry=vector(shapes.map((shape,i)=>{
  assert.equal(shape.name,names[i]);assert.deepEqual(shape.slots.map(s=>s.name),slotNames[i]);
  const name=symbol(),wrapperName=symbol(),slots=vector(shape.slots.map(()=>symbol())),defaults=vector(shape.slots.map(s=>s.default===null?NIL:typeof s.default==='string'?string(s.default):83));
  const instance=allocImage(16);store(instance,882);store(instance+4,0);store(instance+8,NIL);store(instance+12,vector([instance+6,name,NIL],106));
  const wrapper=vector([wrapperName,4*i,instance+6,slots,NIL,NIL,NIL,NIL,NIL,NIL,NIL,4*i,masks[i]*4]);
  return vector([wrapper,masks[i]*4,defaults]);
 }));
 symbols.error_message=string('Checked Lisp runtime operation failed.');
 // Pin the native input graph independently of dynamic allocations.
 const objects=c.nodes.map(()=>allocImage(8)+1);
 const decode=x=>typeof x==='number'?4*x:x==='nil'?NIL:x==='t'?T:x.startsWith('n')?objects[Number(x.slice(1))]:x.startsWith('f:')?handles[x.slice(2)]:x.startsWith('s:')?symbols[x.slice(2)]:keywords[x.slice(1)];
 c.nodes.forEach(([a,b],i)=>{store(objects[i]-1,decode(b));store(objects[i]+3,decode(a));});
 store(NIL-1,NIL);store(NIL+3,NIL);store(T-6,1850);for(let i=1;i<8;i++)store(T-6+4*i,NIL);
 store(4096,mods.length+1);store(4100,1);mods.forEach((m,i)=>[i+1,4,17,23].forEach((v,j)=>store(4104+16*(i+1)+4*j,v)));
 set(48,scenario.empty?A:A+cap);set(52,A+cap);set(56,A);for(let p=A;p<A+cap;p+=8){store(p,NIL);store(p+4,0);} // force first internal shortage
 set(68,ROOT+8);set(72,163840);set(64,ROOT+8);set(128,ROOT);store(ROOT,0);store(ROOT+4,c.args.length);c.args.map(decode).forEach((v,i)=>store(ROOT+8+4*i,v));
 set(80,196608);set(76,196608);set(84,229376);set(92,229376);set(88,229376);set(96,245760);set(104,266240);set(108,2);for(let i=0;i<2;i++)store(266240+4*i,243);set(188,NIL);set(120,OUT);set(124,OUT+4*c.capacity);
 const regions=[['tcr',1024,1280],['external',4096,16384],['image',77824,77864],['vstack',ROOT,163840],['temp',196608,229376],['control',229376,245760],['bindings',266240,270336],['c-stack',1048576,1114112],['root-list',1180000,1200000],['scratch',1200000,1800000]].map(([role,start,end],i)=>({name:role+i,role,start,end}));
 const layout={version:1,collector:'copying',workers:1,egc:false,tcr,maximumPages:32769,logCapacity:32768,regions:[...regions,...images],spaces:[{name:'a',start:A,end:A+cap},{name:'b',start:B,end:B+cap}],groups:['module-constants','callbacks','registry','host'].map(kind=>({kind,slots:[]}))};
 const owner=CollectorOwner.create(memory,bytes,digest,layout);let retries=0,moves=0,grown=0;const constructors=[0,0,0];
 const fill=kind=>{assert(kind>=1&&kind<=3);constructors[kind-1]++;for(let p=get(48);p<get(52);p+=8){store(p,NIL);store(p+4,0);}set(48,get(52));};
 const service=allocationService(owner,call_error);const ensure=n=>{assert(n>0&&n%8===0,'request aligned');assert(get(48)+n>get(52),'slow path only on shortage');const from=get(56),limit=get(52),spaces=owner.spaces;retries++;let error;
  try{service(n);}catch(e){error=e;}
  if(get(56)!==from){const grew=!spaces.some(s=>s.start===get(56));moves+=grew?2:1;if(grew)grown++;}
  for(const space of spaces)if(space.start!==get(56))new Uint8Array(memory.buffer,space.start,space.end-space.start).fill(0xdd);
  if(error)throw error;
 };
 const entries={};const env={memory,tcr,table,tail_table,code_registry:4096,call_error,type_error,nonlocal_exit};let loader;
 if(process.env.LAZY_OWNER){
  const catalog=mods.map((m,i)=>{const b=fs.readFileSync(dir+'/installed/'+m.name+'.wasm'),info=legacyInspect(b,{ownerRetry:true});return {name:m.name,slot:i+1,code:i+1,version:4,signature:17,role:23,profile:OWNER_PROFILE,sha256:sha(b),imports:info.imports,entries:Object.fromEntries(info.exports.map(e=>[e.name,{index:e.index,role:e.name}]))};});
  loader=new LazyLoader({...env,allocationEnsure:ensure,catalog,readBytes:name=>fs.readFileSync(dir+'/installed/'+name+'.wasm'),stub:new WebAssembly.Module(fs.readFileSync(new URL('./stub.wasm',import.meta.url)))});
  for(const m of mods)entries[m.name]=loader.defer(m.name,{env,symbols,keywords,codes,owner:{ensure}}).host_entry;
 }else mods.forEach((m,i)=>{const instance=new WebAssembly.Instance(modules.get(m.name),{env,symbols,keywords,codes,owner:{ensure},pressure:{fill}});entries[m.name]=instance.exports.entry;table.set(i+1,instance.exports.entry);tail_table.set(i+1,instance.exports.tail_entry);});
 assert.equal(retries,0,'instantiation has no allocation authority');
 let result,refusal=null;try{result=process.env.OWNER_NESTED?owner.atSafepoint(()=>entries[c.function](handles[c.function],c.args.length)):entries[c.function](handles[c.function],c.args.length);}catch(e){if(e instanceof WebAssembly.Exception&&e.is(call_error)){refusal=e.getArg(call_error,0);if(!scenario.fail&&!process.env.OWNER_NESTED)throw new Error(c.id+': checked '+refusal);}else if(e instanceof WebAssembly.Exception&&e.is(type_error))throw new Error(c.id+': type refusal '+e.getArg(type_error,0)+' '+e.getArg(type_error,1));else throw e;}
 if(process.env.OWNER_NESTED){assert.equal(refusal,6,'nested owner boundary refuses');assert.equal(get(128),ROOT);assert.equal(get(56),A);assert.equal(get(48),A+cap);rows.push({id:c.id,refusal,contract:'invoke Lisp outside the owner boundary'});continue;}
 if(scenario.fail){assert.equal(refusal,6,'owner refusal propagates');assert(moves>=2,'failure includes movement');const moved=load(objects[0]-1);assert.equal(load(moved+3),191*4,'cleanup reloads after refused assurance');assert.equal(load(moved-1),181*4,'live datum after refused assurance');assert.equal(get(128),ROOT);assert.equal(get(140),0);assert.equal(get(112),0);rows.push({id:c.id,refusal,moves});collections+=moves;continue;}
 const graph=[...objects];const token=v=>{v=v>>>0;if(v===NIL)return 'nil';if(v===T)return 't';if(v%4===0)return (v|0)/4;if(v%8===6){const name=Object.keys(symbols).find(n=>symbols[n]===v);if(name)return 's:'+name;}if(v%8===1){let i=graph.indexOf(v);if(i<0){i=graph.length;graph.push(v);}return 'n'+i;}throw new Error('unhandled result '+v);};
 const values=Array.from({length:result[1]},(_,i)=>token(load(OUT+4*i))),nodes=[];for(let i=0;i<graph.length;i++)nodes.push([token(load(graph[i]+3)),token(load(graph[i]-1))]);
 assert.deepEqual({values,nodes},{values:c.expected.values,nodes:c.expected.nodes},c.id+': native graph');
 assert.deepEqual(native.find(r=>r.id===c.id),{id:c.id,...c.expected},c.id+': native expectation');
 assert.equal(get(128),ROOT,c.id+': caller roots restored');assert.equal(get(112),0,c.id+': binding chain restored');assert.equal(get(140),0,c.id+': control chain restored');
 if(loader){assert(loader.snapshot().some(r=>r.state==='READY'),'cold installation executed');assert.equal(loader.events.filter(e=>e.event==='REFUSED').length,0);}
 collections+=moves;growths+=grown;rows.push({id:c.id,capacity:cap,empty:!!scenario.empty,high:!!scenario.high,retries,moves,grown,constructors});
}
fs.writeFileSync(output,JSON.stringify({status:'PASS',modules:mods.length,comparisons:rows.length,native_comparisons:rows.filter(r=>r.refusal===undefined).length,resource_refusals:rows.filter(r=>r.refusal!==undefined).length,collections,growths,rows},null,2)+'\n');console.log('PASS',rows.length,'allocation retry comparisons');
