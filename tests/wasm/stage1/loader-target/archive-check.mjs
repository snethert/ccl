// Functional check of the archive path on the retained smoke fixture: mirrors
// tests/wasm/stage1/loader-target/check.mjs cases, plus a second generation.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {sha256} from '../../../../runtime/wasm32/sha256.mjs';
import {CollectorOwner} from '../../../../runtime/wasm32/collector-owner.mjs';
import {admitCodeArchive} from '../../../../runtime/wasm32/code-archive.mjs';
const out=process.argv[2],arch=process.argv[3],read=n=>JSON.parse(fs.readFileSync(out+'/'+n));
const bytes=fs.readFileSync(arch+'/smoke.wasm'),manifest=JSON.parse(fs.readFileSync(arch+'/smoke.json'));
assert.equal(manifest.binary_sha256,sha256(bytes));
const records=read('records.json'),functions=read('fixture-functions.json'),pools=read('fixture-pools.json');

const N=77825,T=77838,tcr=1024,registry=4096,root=131064;
const memory=new WebAssembly.Memory({initial:64,maximum:32769,shared:true});
const view=new DataView(memory.buffer),get=p=>view.getUint32(p,true),put=(p,n)=>view.setUint32(p,n,true);
const env={memory,tcr,code_registry:registry,table:new WebAssembly.Table({element:'anyfunc',initial:256}),tail_table:new WebAssembly.Table({element:'anyfunc',initial:256}),
  call_error:new WebAssembly.Tag({parameters:['i32']}),type_error:new WebAssembly.Tag({parameters:['i32','i32']}),nonlocal_exit:new WebAssembly.Tag({parameters:['i32']})};
put(registry,256);put(registry+4,1);
const unexpected=()=>{throw Error('unexpected service');};
let nextCode=16,nextRoot=524288;const registered=new Set();
const session=admitCodeArchive({bytes,manifest,digest:manifest.binary_sha256,env,slotOffset:8,versions:read('versions.json'),policy:read('policy.json'),
  capabilities:{owner:{ensure:unexpected},integer:{calculate:unexpected},floating:{calculate:unexpected}},
  allocateCode:(n,journal)=>{const base=nextCode;nextCode+=n;journal.push(()=>{nextCode=base;});return base;},
  reserveRoots:(n,journal)=>{const base=nextRoot;nextRoot+=4*n;for(let i=0;i<n;i++)put(base+4*i,N);journal.push(()=>{nextRoot=base;});return {base,count:n};},
  registerRoots:(roots,cells,journal)=>{cells.forEach(p=>{assert(p>=roots.base&&p<roots.base+4*roots.count);registered.add(p);});journal.push(()=>cells.forEach(p=>registered.delete(p)));}});
const unitOf=name=>manifest.units.find(u=>functions[u.wire].name?.symbol===name);
const record=u=>{const r=records.units.find(x=>x.name===u.wire);return r.install_record??r.record;};
let next=393216;const allocate=n=>{const p=next;next+=Math.ceil(n/8)*8;return p;};const literal=new Map();
function encode(v,vector=false){
  if(v===null)return N;if(v===true)return T;if(Number.isInteger(v))return (v*4)>>>0;
  if(Number.isInteger(v.character))return v.character*256+75;if(v.vector)return encode(v.vector,true);
  if(v.symbol){const k=JSON.stringify([v.package,v.symbol]);if(!literal.has(k)){const p=allocate(32),name=encode(v.symbol);[1850,name,N,N,N,0,N,0].forEach((x,i)=>put(p+4*i,x));literal.set(k,p+6);}return literal.get(k);}
  if(typeof v==='string'){const cs=Array.from(v),p=allocate(4+cs.length*4);put(p,cs.length*256+191);cs.forEach((c,i)=>put(p+4+i*4,c.codePointAt(0)));return p+6;}
  assert(Array.isArray(v));if(vector||v.length===0){const p=allocate(4+v.length*4);put(p,v.length*256+250);v.forEach((x,i)=>put(p+4+i*4,encode(x)));return p+6;}
  let tail=N;for(let i=v.length-1;i>=0;i--){const p=allocate(8);put(p,tail);put(p+4,encode(v[i]));tail=p+1;}return tail;}
const debug=encode([1,null,[]],true);
for(const [o,v] of [[48,3145728],[52,3211264],[56,3145728],[64,root+8],[68,root+8],[72,root+32776],[76,196608],[80,196608],[84,212992],[88,212992],[92,212992],[96,229376],[104,262144],[108,0],[116,0],[120,root+8200],[124,root+8264],[128,root],[188,N]])put(tcr+o,v);
put(root,0);put(root+4,1);put(root+8,35*4);
const LOAD='load-1';
function install(name,symbolsOverride){
  const u=unitOf(name),meta=functions[u.wire];
  const imports=symbolsOverride??meta.symbols.map(s=>encode(s));
  for(const i of record(u)[9]??[])put(imports[i]+22,4*(i+1));
  const code=session.install(LOAD,u.wire,record(u),imports);
  const arity=encode(meta.arity,true);put(arity-2+6*4,encode(meta.arity[6],true));
  const pool=encode([null,null,0x574153,0,[],null,...pools[u.wire]],true);put(pool-2,arity);put(pool+2,debug);
  const fn=allocate(32);[1578,code*4,N,4,arity,debug,pool,0].forEach((v,i)=>put(fn+i*4,v));
  const slot=get(registry+8+16*code);
  const call=args=>{call.words=args.map(v=>encode(v));return call.raw(call.words);};
  call.raw=words=>{words.forEach((v,i)=>put(root+8+4*i,v));return env.table.get(slot)(fn+6,words.length);};
  call.code=code;call.fn=fn+6;call.imports=imports;return call;}
session.reserve(LOAD,manifest.units.map(u=>u.name));
const checked=(f,args)=>{try{return f(args);}catch(e){if(e.is?.(env.call_error))throw Error('checked '+e.getArg(env.call_error,0));if(e.is?.(env.type_error)){const d=e.getArg(env.type_error,0);const lit=[...literal].find(([k,v])=>v===d);const el=i=>{const w=get(d-2+4*i);const l=[...literal].find(([k,v])=>v===w);return l?l[0]:w%8===6?'obj:'+get(w-6).toString(16):w;};throw Error('type_error '+d+' '+e.getArg(env.type_error,1)+' header='+(d%8===6?get(d-6).toString(16):'-')+' elements='+el(0)+','+el(1)+' allocNext='+next);}if(e.is?.(env.nonlocal_exit))throw Error('nonlocal_exit '+e.getArg(env.nonlocal_exit,0));throw e;}};
const addSeven=install('TARGET-LOADER-ADD-SEVEN');
assert.deepEqual(checked(addSeven,[35]),[42*4,1]);
const extrema=install('TARGET-LOADER-EXTREMA');
for(const [args,expected] of read('extrema-native.json')){const [first,count]=checked(extrema,args);assert.equal(count,expected.length);assert.equal(first>>2,expected[0]);assert.deepEqual(expected.map((_,i)=>get(root+8200+4*i)>>2),expected);}
const values=install('TARGET-LOADER-VALUES');put(tcr+124,root+8328);
for(const [input,result] of read('values-native.json')){const args=input??[],expected=result??[];const [first,count]=checked(values,args);assert.equal(count,expected.length);const words=expected.map(x=>x===null?N:x*4);assert.equal(first,words[0]??N);}
put(tcr+124,root+8264);
const assq=install('TARGET-LOADER-ASSQ');let assqCases=0;
for(const [args,expected] of read('assq-native.json')){if(expected==='TYPE-ERROR'){assert.throws(()=>assq(args),e=>e.is?.(env.type_error));}else{const [value,count]=checked(assq,args);assert.equal(count,1);let cursor=assq.words[1],found=N;while(cursor!==N){const pair=get(cursor+3);if(pair!==N&&get(pair+3)===assq.words[0]){found=pair;break;}cursor=get(cursor-1);}assert.equal(value,found);}assqCases++;}
const ordinaryKeys=install('TARGET-LOADER-ORDINARY-KEYS'),methodKeys=install('TARGET-LOADER-METHOD-KEYS');
const amount={package:'KEYWORD',symbol:'AMOUNT'},other={package:'KEYWORD',symbol:'OTHER'};
const keywordResults=[checked(ordinaryKeys,[40,amount,2])[0]>>2,checked(methodKeys,[null,40,amount,2,other,9])[0]>>2,checked(methodKeys,[null,40,other,9])[0]>>2];
assert.throws(()=>ordinaryKeys([40,other,9]),e=>e.is?.(env.call_error));keywordResults.push(true);
assert.deepEqual(keywordResults,read('keyword-native.json'));
const nested=manifest.units.find(u=>u.functions.length>1);assert(nested,'nested unit');
const nestedCode=session.install(LOAD,nested.wire,record(nested),functions[nested.wire].symbols.map(s=>encode(s)));
for(const id of nested.functions){const code=16+id;assert.equal(get(registry+8+16*code),code+8);assert.equal(typeof env.table.get(code+8),'function');}
// Same unit, same values, same session: identity, same code id.
assert.equal(session.install(LOAD,unitOf('TARGET-LOADER-ADD-SEVEN').wire,record(unitOf('TARGET-LOADER-ADD-SEVEN')),addSeven.imports),addSeven.code);
assert.throws(()=>session.install(LOAD,unitOf('TARGET-LOADER-ADD-SEVEN').wire,record(unitOf('TARGET-LOADER-ADD-SEVEN')),addSeven.imports.map((v,i)=>i===0?N:v)),/IMPORT_IDENTITY/);
// A second LOAD of the same file: reservation lands in a fresh generation; new ids; old closure intact.
const LOAD2='load-2';const g2=session.reserve(LOAD2,manifest.units.map(u=>u.name));assert.equal(session.storage().generations,2);
const u=unitOf('TARGET-LOADER-ADD-SEVEN');const code2=session.install(LOAD2,u.wire,record(u),functions[u.wire].symbols.map(s=>encode(s)));
assert.notEqual(code2,addSeven.code);assert.equal(code2,16+manifest.function_count+u.functions[0]);
assert.deepEqual(checked(addSeven,[1]),[8*4,1]);
const fn2=allocate(32);const arity=encode(functions[u.wire].arity,true);put(arity-2+24,encode([],true));const pool=encode([null,null,0x574153,0,[],null,...pools[u.wire]],true);put(pool-2,arity);put(pool+2,debug);
[1578,code2*4,N,4,arity,debug,pool,0].forEach((v,i)=>put(fn2+i*4,v));put(root+8,2*4);
assert.deepEqual(env.table.get(get(registry+8+16*code2))(fn2+6,1),[9*4,1]);
// Partial close releases reservations, keeps publications.
session.release(LOAD2);assert.throws(()=>session.install(LOAD2,unitOf('TARGET-LOADER-EXTREMA').wire,record(unitOf('TARGET-LOADER-EXTREMA')),[]),/CODE_RECORD|UNRESERVED_UNIT|SYMBOL_COUNT/);
// Refusals leave state: wrong record digest, wrong symbol count.
const before=[nextCode,registered.size,Array.from(new Uint32Array(memory.buffer,registry,2+256*4))];
assert.throws(()=>session.install(LOAD,unitOf('TARGET-LOADER-VECTOR-INIT').wire,[6,'x'],[]),/CODE_RECORD/);
assert.throws(()=>session.install(LOAD,unitOf('TARGET-LOADER-VECTOR-INIT').wire,record(unitOf('TARGET-LOADER-VECTOR-INIT')),[]),/SYMBOL_COUNT/);
assert.deepEqual([nextCode,registered.size,Array.from(new Uint32Array(memory.buffer,registry,2+256*4))],before);
// Real collector movement: both generations remain callable, and only
// registered root cells retain movable values. Fixture metadata is pinned.
if(process.argv[4]){
 const collector=fs.readFileSync(process.argv[4]);
 put(N-1,N);put(N+3,N);put(T-6,1850);for(let i=1;i<8;i++)put(T-6+4*i,N);
 const regions=[['tcr',tcr,tcr+256],['image',77824,77864],['image',393216,next],
  ['vstack',root,root+32776],['temp',196608,212992],['control',212992,229376],
  ['bindings',262144,266240],['external',524288,1048576],['c-stack',1048576,1114112],
  ['root-list',1114112,1179648],['scratch',1179648,2097152]]
  .map(([role,start,end],i)=>({name:role+i,role,start,end}));
 const owner=CollectorOwner.create(memory,collector,sha256(collector),{version:1,collector:'copying',workers:1,egc:false,tcr,
  maximumPages:32769,logCapacity:32768,regions,
  spaces:[3145728,3211264].map((start,i)=>({name:'heap'+i,start,end:start+65536})),
  groups:['module-constants','callbacks','registry','host'].map((kind,i)=>({kind,slots:i?[]:[...registered]}))});
 const moving=get(tcr+48);put(moving,N);put(moving+4,123*4);put(tcr+48,moving+8);
 const held=owner.atSafepoint(o=>o.rootCells([moving+1]));
 owner.atSafepoint(o=>o.collect());assert.notEqual(held.values()[0],moving+1);assert.equal(get(held.values()[0]+3),123*4);
 assert.deepEqual(checked(addSeven,[1]),[8*4,1]);put(root+8,2*4);
 assert.deepEqual(env.table.get(get(registry+8+16*code2))(fn2+6,1),[9*4,1]);
 owner.atSafepoint(()=>held.release());
}
console.log(JSON.stringify({status:'PASS',functions:manifest.function_count,helpers:manifest.helpers.length,rootCells:manifest.root_cells,generations:session.storage().generations,registeredRoots:registered.size,extremaCases:read('extrema-native.json').length,valuesCases:read('values-native.json').length,assqCases,keywordResults}));
