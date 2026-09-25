// Whole-file prefix plus original-definition package bootstrap witness.
// The standalone keyword image intentionally has no package bootstrap.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {admitCrossImage} from './runtime/cross-image.mjs';
import {CollectorOwner} from './runtime/collector-owner.mjs';
import {integerService} from './runtime/integer-service.mjs';
import {floatService} from './runtime/float-service.mjs';
const [artifacts,runtime,casesPath]=process.argv.slice(2);
const N=77825,T=77838,TCR=1024,ROOT=131064,EXTERNAL=262144,BINDINGS=266240,REGISTRY=4096,base=8388608;
const read=n=>JSON.parse(fs.readFileSync(artifacts+'/'+n));
const manifest=read('manifest.json'),record=read('heap-image.json'),codeSet=read('code-set.json');
const policy=JSON.parse(fs.readFileSync(new URL('./policy.json',import.meta.url)));
const versions=JSON.parse(fs.readFileSync(new URL('./versions.json',import.meta.url)));
const expected={...versions,modules:codeSet.modules.map(m=>[m.name,m.code_id,m.generation]),table_capacity:512,reserved_slots:[0,1,2,3],
 slots:Object.fromEntries(codeSet.modules.map(m=>[m.code_id,m.code_id+(process.argv.includes('--relocate')?20:8)]))};
const payload=fs.readFileSync(artifacts+'/heap.payload.bin'),fixed=fs.readFileSync(artifacts+'/static.bin');
const memory=new WebAssembly.Memory({initial:Math.ceil((20971520+65536)/65536),maximum:32769,shared:true});
const d=new DataView(memory.buffer),get=p=>d.getUint32(p,true),put=(p,v)=>d.setUint32(p,v,true),set=(o,v)=>put(TCR+o,v),t=o=>get(TCR+o);
const start=process.argv.includes('--relocate')?3145728:manifest.heap.start,end=start+manifest.heap.bytes;
new Uint8Array(memory.buffer,manifest.static.start,fixed.length).set(fixed);
const regions=[{name:'static',start:manifest.static.start,size:fixed.length,kind:'objects'},{name:'roots',start:manifest.roots.start,size:64,kind:'roots'}];
const resolve=r=>Object.hasOwn(r,'heap')?start+r.heap+r.tag:regions.find(x=>x.name===r.region).start+r.offset+r.tag;
// TCR, stacks and collector as the accepted single-Worker fixtures lay them out.
const image=[['image',manifest.static.start,manifest.static.start+fixed.length],['image',start,end],['image',manifest.roots.start,manifest.roots.start+64]];
const layoutRegions=[['tcr',TCR,TCR+256],...image,['vstack',ROOT,ROOT+32776],['temp',196608,212992],['control',212992,229376],['external',EXTERNAL,EXTERNAL+4096],['bindings',BINDINGS,BINDINGS+4096],['c-stack',1048576,1114112],['root-list',4600000,5648576],['scratch',12582912,20971520]].map(([role,s,e],i)=>({name:role+'-'+i,role,start:s,end:e}));
const layout={version:1,collector:'copying',workers:1,egc:false,tcr:TCR,maximumPages:32769,logCapacity:131072,regions:layoutRegions,
 spaces:[base,base+65536].map((s,i)=>({name:'heap-'+i,start:s,end:s+65536})),
 groups:['module-constants','callbacks','registry','host'].map((kind,i)=>({kind,slots:[EXTERNAL+4*i]}))};
for(let i=0;i<4;i++)put(EXTERNAL+4*i,N);
set(0,1);set(8,1);set(32,2);set(48,base);set(52,base+65536);set(56,base);set(68,ROOT+8);set(72,ROOT+32776);set(64,ROOT+8);set(128,ROOT);put(ROOT,0);put(ROOT+4,0);
set(80,196608);set(76,196608);set(84,212992);set(92,212992);set(88,212992);set(96,229376);set(104,BINDINGS);set(108,0);set(120,ROOT+8200);set(124,ROOT+8264);set(188,N);
const binary=n=>fs.readFileSync(runtime+'/'+n+'.wasm'),hash=b=>createHash('sha256').update(b).digest('hex');
const owner=CollectorOwner.create(memory,binary('collector'),hash(binary('collector')),layout);
let collections=0;
function collect(){const old=t(56),limit=t(52);owner.atSafepoint(o=>o.collect());new Uint8Array(memory.buffer,old,limit-old).fill(0xdd);collections++;}
function ensure(n){const r=owner.atSafepoint(o=>o.ensure(n));if(r.collected)collections++;}
const env={memory,tcr:TCR,table:new WebAssembly.Table({element:'anyfunc',initial:512}),tail_table:new WebAssembly.Table({element:'anyfunc',initial:512}),code_registry:REGISTRY,
 call_error:new WebAssembly.Tag({parameters:['i32']}),type_error:new WebAssembly.Tag({parameters:['i32','i32']}),nonlocal_exit:new WebAssembly.Tag({parameters:['i32']})};
put(REGISTRY,512);put(REGISTRY+4,1);
const pinned=layoutRegions.filter(r=>r.role==='image');
const integer=integerService({memory,tcr:TCR,owner,callError:env.call_error,bytes:binary('integer'),digest:hash(binary('integer')),pinned});
const floating=floatService({memory,tcr:TCR,owner,callError:env.call_error,bytes:binary('float'),digest:hash(binary('float')),detectorBytes:binary('detector'),detectorDigest:hash(binary('detector')),pinned});
// Complete artifact and module validation precedes heap/table publication.
assert.equal(hash(fixed),manifest.static.sha256,'static artifact digest');
const admitted=admitCrossImage({memory,manifest,record,payload,codeSet,regions,env,start,expected,policy,
 readTemplate:name=>fs.readFileSync(artifacts+'/'+name+'.template.wasm'),
 readBytes:name=>fs.readFileSync(artifacts+'/'+name+'.wasm'),
 capabilities:{owner:{ensure},integer:{calculate:integer},floating:{calculate:floating}}});
const installed=admitted.install();assert.equal(installed.end,end);
for(const {record:r} of installed.instances){assert.equal(r.slot,expected.slots[r.code_id]);assert.notEqual(r.slot,r.code_id);}
const entries=new Map(installed.instances.map(x=>[x.record.code_id,x.instance.exports.entry]));
const roots=Object.fromEntries(manifest.roots.names.map((name,i)=>[name,get(manifest.roots.start+4*i)]));
// The static symbols must refer to the relocated image, including their names.
for(const raw of [77832,77864])for(const offset of [4,12,16]){
 const word=get(raw+offset);assert(word===N||word===T||(word-6>=start&&word-6<end),'static outgoing reference');
}
function string(w){return Array.from({length:get(w-6)>>>8},(_,i)=>String.fromCodePoint(get(w-2+4*i))).join('');}
function packageName(pkg){if(pkg===N)return null;const names=get(pkg-6+20);return string(get(names+3));}
function decode(v,depth=0){
 assert(depth<64,'decode depth');
 if(v===N)return null;if(v===T)return true;if(!(v&3))return (v|0)>>2;
 if((v&7)===1)return [decode(get(v+3),depth+1),decode(get(v-1),depth+1)];
 if((v&7)===6){const tag=get(v-6)&255;
  if(tag===191)return {string:string(v)};
  if(tag===58)return {symbol:(packageName(get(v-6+16))??'#')+'::'+string(get(v-6+4))};
  if(tag===42)return {function:get(v-6+4)>>>2};
  if(tag===98)return {package:packageName(v)};
 }
 throw Error('decode '+v);
}
function callObject(fn,args){
 assert.equal(get(fn-6),1578,'function header');const id=get(fn-6+4)>>>2,entry=entries.get(id);assert(entry,'code id '+id);
 put(ROOT+4,args.length);args.forEach((v,i)=>put(ROOT+8+i*4,v));set(64,ROOT+8);set(128,ROOT);set(116,0);set(120,ROOT+8200);set(124,ROOT+8264);
 const before=Array.from({length:64},(_,i)=>t(i*4));let result;
 try{result=entry(fn,args.length);}catch(error){if(error.is?.(env.call_error))throw Error('checked '+error.getArg(env.call_error,0));if(error.is?.(env.type_error))throw Error('type_error '+error.getArg(env.type_error,0)+' '+error.getArg(env.type_error,1));throw error;}
 for(let i=0;i<64;i++)if(![48,52,56,104,108,116].includes(i*4))assert.equal(t(i*4),before[i],'TCR '+i*4);
 assert.equal(result[1],t(116));assert.equal(result[0]>>>0,result[1]?get(ROOT+8200):N);
 const values=Array.from({length:result[1]},(_,i)=>decode(get(ROOT+8200+i*4)));put(ROOT+4,0);set(116,0);return values;
}
const symbolAddress=(pkg,name)=>{const s=manifest.symbols.find(s=>s.package===pkg&&s.name===name);assert(s,pkg+'::'+name);return resolve(s.reference);};
// Drain the package witness's initializer queue in its serialized order.
const coldLoad=[];for(let list=roots['cold-load-functions'];list!==N;list=get(list-1)){
 const fn=get(list+3);assert.equal(get(fn-6),1578);coldLoad.push(get(fn-6+4)>>>2);
}
assert(coldLoad.length>0);
const packageFunction=get(symbolAddress('CCL','SET-PACKAGE')-6+12);
const initialized=packageFunction!==roots['unbound-function'];
const coldResults=[];
if(initialized){
 // Establish a different starting package by calling Lisp on the target.
 callObject(get(symbolAddress('CCL','LOADER-PACKAGE-KEYWORD')-6+12),[]);
 assert.equal(packageName(get(symbolAddress('COMMON-LISP','*PACKAGE*')-6+8)),'KEYWORD');
 for(let list=roots['cold-load-functions'];list!==N;list=get(list-1)){
  try{coldResults.push(callObject(get(list+3),[]));}
  catch(error){throw new Error('initializer '+(get(get(list+3)-2)>>>2)+': '+error.message,{cause:error});}
  if(process.argv.includes('--collect'))collect();
 }
 assert.equal(packageName(get(symbolAddress('COMMON-LISP','*PACKAGE*')-6+8)),'CCL','initializers set *PACKAGE*');
}
const blockedCalls=[];
if(manifest.symbols.some(s=>s.package==='CCL'&&s.name==='%FIXNUM-TRUNCATE')){
 assert.equal(get(symbolAddress('COMMON-LISP','EQL')-6+12),roots['unbound-function']);
 assert.throws(()=>callObject(get(symbolAddress('CCL','LOADER-BOXED-EQL')-6+12),[]),/^Error: checked 4$/);
 blockedCalls.push({name:'CCL::LOADER-BOXED-EQL',dependency:'COMMON-LISP::EQL',reason:4});
}
const properList=[{symbol:'COMMON-LISP::SATISFIES'},[{symbol:'CCL::PROPER-LIST-P'},null]];
for(const row of codeSet.modules){
 const type=row.symbols.find(s=>s.wire==='expected_proper_list');assert(type);
 assert.deepEqual(decode(resolve(type.reference)),properList);
}
const metadata=[];
for(const symbol of manifest.symbols){
 const fn=get(resolve(symbol.reference)-6+12);
 if((fn&7)!==6||fn-6<start||fn+22>=end||get(fn-6)!==1578)continue;
 const row=codeSet.modules.find(m=>m.code_id===(get(fn-2)>>>2));assert(row);
 if(!row.arity[5].length)continue;
 const arity=get(fn-6+16),keys=get(arity-6+28);
 assert.equal(get(keys-6),250+256*row.arity[5].length);
 row.arity[5].forEach((wire,i)=>assert.equal(get(keys-2+4*i),resolve(row.symbols.find(s=>s.wire===wire).reference)));
 metadata.push([symbol.package,symbol.name,row.arity[5].length]);
}
assert(metadata.length>0,'whole-file keyword metadata');
const encode=a=>a===null?N:a===true?T:typeof a==='number'?a*4:symbolAddress(...a.symbol);
const cases=JSON.parse(fs.readFileSync(casesPath)),observations=[];
for(const c of cases){
 const fn=get(symbolAddress(...c.call)-6+12);
 try{observations.push({id:c.id,values:callObject(fn,c.args.map(encode))});}
 catch(error){throw new Error(c.id+': '+error.message,{cause:error});}
 if(process.argv.includes('--collect'))collect();
}
console.log(JSON.stringify({status:'PASS',initializersQueued:coldLoad.length,initializersExecuted:coldResults.length,coldResults,
 startupBlocker:initialized?null:'CCL::SET-PACKAGE',blockedCalls,observations,metadata,collections,objects:admitted.objects,modules:codeSet.modules.length}));
