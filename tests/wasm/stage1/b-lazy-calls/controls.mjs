import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';
import {LazyLoader,validate,sha} from './loader.mjs';import {inspect} from './binary.mjs';
const [dir,out]=process.argv.slice(2),read=n=>JSON.parse(fs.readFileSync(path.join(dir,n))),catalog=read('catalog.json');
const bytes=name=>fs.readFileSync(path.join(dir,'installed',name+'.wasm'));
const stub=new WebAssembly.Module(fs.readFileSync(path.join(dir,'lazy-stub.wasm'))),results=[];
const base=catalog.find(r=>r.name==='v1'),caller=catalog.find(r=>r.name==='dynamic_one');
function setup(records=catalog,provider=bytes){
 const memory=new WebAssembly.Memory({initial:8,maximum:32769,shared:true}),view=new DataView(memory.buffer),store=(p,v)=>view.setUint32(p,v,true);
 const table=new WebAssembly.Table({element:'anyfunc',initial:catalog.length+1,maximum:catalog.length+1}),tail_table=new WebAssembly.Table({element:'anyfunc',initial:catalog.length+1,maximum:catalog.length+1});
 const call_error=new WebAssembly.Tag({parameters:['i32']}),type_error=new WebAssembly.Tag({parameters:['i32','i32']});
 const tcr=256,symbols={},codes={},keywords=Object.fromEntries(['a','b','x','y','external','bad','allow-other-keys'].map((k,i)=>[k,524294+i*16]));
 store(4096,catalog.length+1);store(4100,1);
 for(const r of catalog){const i=r.slot-1,object=131072+32*i,symbol=196608+32*i,row=4104+16*r.slot;
  symbols[r.name]=symbol+6;codes[r.name]=4*r.code;
  [1322,4*r.code,77825,4,77825,77825].forEach((n,i)=>store(object+4*i,n));[1850,77825,77825,object+6,77825,77825,77825,77825].forEach((n,i)=>store(symbol+4*i,n));
  [r.slot,4,17,23].forEach((n,i)=>store(row+4*i,n));}
 const options={catalog:records,memory,table,tail_table,call_error,stub,readBytes:provider};
 const loader=new LazyLoader(options),imports={env:{memory,tcr,table,tail_table,code_registry:4096,call_error,type_error},symbols,codes,keywords},pairs=new Map();
 for(const r of records)pairs.set(r.name,loader.defer(r.name,imports));
 function init(args){new Uint8Array(memory.buffer,65528,32776).fill(0);store(65528,0);store(65532,args.length);args.forEach((n,i)=>store(65536+4*i,n));
  for(const [offset,value] of [[48,262144],[52,294912],[56,262144],[64,65536],[68,65536],[72,98304],[116,3],[120,73728],[124,74240],[128,65528]])store(tcr+offset,value);
  new Uint8Array(memory.buffer,73728,512).fill(0xa5);}
 const self=name=>131078+32*(catalog.find(r=>r.name===name).slot-1);
 const snapshot=()=>Buffer.from(memory.buffer).toString('hex');
 const entries=()=>catalog.map(r=>[table.get(r.slot),tail_table.get(r.slot)]);
 function refuses(fn,reason,code=7){const before=snapshot(),old=entries();let e;
  try{fn();}catch(x){e=x;}assert(e instanceof WebAssembly.Exception&&e.is(call_error),'checked installation refusal: '+reason);assert.equal(e.getArg(call_error,0),code,reason);
  assert.equal(loader.events.at(-1).reason,reason);assert.equal(snapshot(),before,reason+': memory unchanged');assert.deepEqual(entries(),old,reason+': both tables unchanged');}
 return {memory,table,tail_table,call_error,loader,imports,pairs,store,view,init,self,snapshot,entries,refuses};
}
function changedRecord(edit){return catalog.map(r=>{const x=structuredClone(r);if(r.name==='v1')edit(x);return x;});}
function recordBytes(data){return changedRecord(r=>{r.sha256=sha(data);});}
function reject(name,make,action,reason,code=7){const h=make();h.init([28]);h.refuses(()=>action(h),reason,code);results.push({name,status:'REJECTED',reason});}
const install=h=>h.loader.install(base.slot);
reject('digest-before-compile',()=>setup(catalog,n=>n==='v1'?bytes('v0'):bytes(n)),install,'BINARY_DIGEST');
reject('missing-module',()=>setup(catalog,n=>n==='v1'?fs.readFileSync(path.join(dir,'missing.wasm')):bytes(n)),install,'MISSING_MODULE');
reject('profile',()=>setup(changedRecord(r=>r.profile='unshared')),install,'PROFILE');
reject('export-role',()=>setup(changedRecord(r=>r.entries.entry.role='tail_entry')),install,'EXPORT_ROLE');
reject('export-index',()=>setup(changedRecord(r=>r.entries.entry.index=r.entries.tail_entry.index)),install,'EXPORT_ROLE');
reject('import-manifest',()=>setup(changedRecord(r=>r.imports[1].name='wrong')),install,'IMPORT_MANIFEST');
for(const [name,reason]of Object.entries(read('malformed.json'))){const b=fs.readFileSync(path.join(dir,'malformed',name+'.wasm'));
 reject(name,()=>setup(recordBytes(b),n=>n==='v1'?b:bytes(n)),install,reason);}
for(const [name,offset,value]of [['registry-slot',0,caller.slot],['registry-version',4,8],['registry-signature',8,71],['registry-role',12,71]])
 reject(name,()=>{const h=setup();h.store(4104+16*base.slot+offset,value);return h;},install,'REGISTRY_IDENTITY',4);
for(const role of ['entry','tail_entry'])reject('actual-table-substitution-'+role,()=>{const h=setup();const table=role==='entry'?h.table:h.tail_table;table.set(base.slot,h.pairs.get('dynamic_one')[role]);return h;},install,'TABLE_IDENTITY',4);
// A pinned manifest binds a particular generated module to its slot. Same-typed
// exports from another genuine generated module cannot be substituted by bytes.
reject('same-signature-wrong-code',()=>setup(catalog,n=>n==='v1'?bytes('opt'):bytes(n)),install,'BINARY_DIGEST');
// Failure after entering a real generated caller must restore the caller context.
{let broken=true;const h=setup(catalog,n=>n==='v1'&&broken?Buffer.from([0]):bytes(n));h.loader.install(caller.slot);h.init([h.self('v1'),28]);
 const old=[64,120,124,128,116].map(o=>h.view.getUint32(256+o,true)),args=Buffer.from(h.memory.buffer,65536,8).toString('hex'),output=Buffer.from(h.memory.buffer,73728,512).toString('hex');
 let error;try{h.pairs.get('dynamic_one').entry(h.self('dynamic_one'),2);}catch(e){error=e;}
 assert(error instanceof WebAssembly.Exception&&error.is(h.call_error));assert.equal(error.getArg(h.call_error,0),7);assert.deepEqual([64,120,124,128,116].map(o=>h.view.getUint32(256+o,true)),old);assert.equal(Buffer.from(h.memory.buffer,65536,8).toString('hex'),args);assert.equal(Buffer.from(h.memory.buffer,73728,512).toString('hex'),output);assert.equal(h.loader.snapshot().find(r=>r.slot===base.slot).state,'COLD');
 broken=false;assert.deepEqual(h.pairs.get('dynamic_one').entry(h.self('dynamic_one'),2),[28,1]);assert.equal(h.view.getUint32(73728,true),28);
 const installs=h.loader.events.filter(e=>e.event==='INSTALLED'&&e.slot===base.slot).length;assert.equal(installs,1);h.init([44]);assert.deepEqual(h.pairs.get('v1').entry(h.self('v1'),1),[44,1]);assert.equal(h.loader.events.filter(e=>e.event==='INSTALLED'&&e.slot===base.slot).length,1);
 results.push({name:'generated-caller-failure-retry-cached-stub',status:'PASS'});}
// Reentrancy is refused without destroying the outer loading guard or tables.
{let h;h=setup(catalog,n=>{if(n==='v1')h.loader.install(base.slot);return bytes(n);});h.init([28]);const before=h.snapshot(),old=h.entries();let e;try{install(h);}catch(x){e=x;}
 assert(e instanceof WebAssembly.Exception&&e.is(h.call_error));assert(h.loader.events.some(e=>e.reason==='REENTRANT_INSTALL'));assert.equal(h.snapshot(),before);assert.deepEqual(h.entries(),old);assert.equal(h.loader.snapshot().find(r=>r.slot===base.slot).state,'COLD');results.push({name:'recursive-install',status:'REJECTED',reason:'REENTRANT_INSTALL'});}
// Caller-owned descriptor and import objects cannot change admitted identities.
{const records=structuredClone(catalog),h=setup(records);records.find(r=>r.name==='v1').sha256=sha(bytes('v0'));h.imports.codes.v1=999;h.imports.env.tcr=0;h.init([28]);assert.doesNotThrow(()=>assert.deepEqual(h.pairs.get('v1').entry(h.self('v1'),1),[28,1]),'admitted identities stay immutable');results.push({name:'admission-copies-inputs',status:'PASS'});}
// Successful and cached publication have no authority over any memory byte.
{const h=setup();h.init(Array.from({length:130},(_,i)=>4*i));const before=h.snapshot(),old=h.entries();h.loader.install(base.slot);assert.equal(h.snapshot(),before);const after=h.entries();
 for(let i=0;i<after.length;i++)if(i!==base.slot-1)assert.deepEqual(after[i],old[i]);else{assert.notEqual(after[i][0],old[i][0]);assert.notEqual(after[i][1],old[i][1]);}
 h.loader.install(base.slot);assert.equal(h.snapshot(),before);assert.deepEqual(h.entries(),after);results.push({name:'paired-publication-and-cache-preserve-memory',status:'PASS'});}
// A caught recursive attempt must not clear the guard around the outer load.
{let h,attempts=0;h=setup(catalog,n=>{if(n==='v1')for(let i=0;i<2;i++){try{h.loader.install(caller.slot);assert.fail('recursive entry');}catch(e){assert(e instanceof WebAssembly.Exception&&e.is(h.call_error));assert.equal(h.loader.events.at(-1).reason,'REENTRANT_INSTALL');attempts++;}}return bytes(n);});
 h.init([28]);assert.deepEqual(h.pairs.get('v1').entry(h.self('v1'),1),[28,1]);assert.equal(attempts,2);assert.equal(h.loader.snapshot().find(r=>r.slot===caller.slot).state,'COLD');results.push({name:'caught-reentrancy-keeps-outer-guard',status:'PASS'});}
// A callee's Lisp-level refusal is after installation and must not evict it.
{const h=setup();h.init([]);let error;try{h.pairs.get('v1').entry(h.self('v1'),0);}catch(e){error=e;}
 assert(error instanceof WebAssembly.Exception&&error.is(h.call_error));assert.equal(error.getArg(h.call_error,0),1);assert.equal(h.loader.snapshot().find(r=>r.slot===base.slot).state,'READY');
 h.init([52]);assert.deepEqual(h.pairs.get('v1').entry(h.self('v1'),1),[52,1]);assert.equal(h.loader.events.filter(e=>e.event==='INSTALLED'&&e.slot===base.slot).length,1);results.push({name:'callee-refusal-does-not-uninstall',status:'PASS'});}
// Metadata errors are refused before any stub is published.
for(const [name,edit,reason]of [
 ['duplicate-slot',r=>r[1].slot=r[0].slot,'CODE_ROLE'],
 ['duplicate-name',r=>r[1].name=r[0].name,'CATALOG_UNIQUE'],
 ['reserved-slot',r=>{r[0].slot=0;r[0].code=0;},'SLOT'],
 ['out-of-range-slot',r=>{r[0].slot=catalog.length+1;r[0].code=catalog.length+1;},'SLOT'],
 ['wrong-signature-role',r=>r[0].signature=99,'CODE_ROLE'],
 ['wrong-role',r=>r[0].role=99,'CODE_ROLE']]){
 const records=structuredClone(catalog);edit(records);assert.throws(()=>setup(records),e=>e.message===reason,name);results.push({name,status:'REJECTED',reason});}
fs.writeFileSync(out,JSON.stringify({status:'PASS',cases:results},null,2)+'\n');
