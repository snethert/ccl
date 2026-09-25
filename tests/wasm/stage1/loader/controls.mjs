// Directed refusals use the real admission/installation path. Every negative
// case proves memory and both tables unchanged, including a bad final module.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {admitCrossImage} from './runtime/cross-image.mjs';
import {admitHeapImage,recordDigest} from './runtime/heap-image.mjs';
import {sha256} from './runtime/sha256.mjs';
import {inventory} from './d2.mjs';
const dir=process.argv[2],read=n=>JSON.parse(fs.readFileSync(dir+'/'+n));
const manifest=read('manifest.json'),record=read('heap-image.json'),codeSet=read('code-set.json');
const policy=JSON.parse(fs.readFileSync(new URL('./policy.json',import.meta.url)));
const versions=JSON.parse(fs.readFileSync(new URL('./versions.json',import.meta.url)));
const expected={...versions,modules:codeSet.modules.map(m=>[m.name,m.code_id,m.generation]),table_capacity:64,reserved_slots:[0,1,2,3],
 slots:Object.fromEntries(codeSet.modules.map(m=>[m.code_id,m.code_id+(process.argv.includes('--relocate')?20:8)]))};
const payload=fs.readFileSync(dir+'/heap.payload.bin'),fixed=fs.readFileSync(dir+'/static.bin');
const regions=[{name:'static',start:manifest.static.start,size:fixed.length,kind:'objects'},{name:'roots',start:manifest.roots.start,size:64,kind:'roots'}];
function fresh(){
 const memory=new WebAssembly.Memory({initial:64,maximum:32769,shared:true});
 new Uint8Array(memory.buffer,manifest.static.start,fixed.length).set(fixed);
 const v=new DataView(memory.buffer);v.setUint32(4096,64,true);v.setUint32(4100,1,true);
 const env={memory,tcr:1024,code_registry:4096,table:new WebAssembly.Table({initial:64,element:'anyfunc'}),tail_table:new WebAssembly.Table({initial:64,element:'anyfunc'}),
 call_error:new WebAssembly.Tag({parameters:['i32']}),type_error:new WebAssembly.Tag({parameters:['i32','i32']}),nonlocal_exit:new WebAssembly.Tag({parameters:['i32']})};
 return {memory,env,regions,expected:structuredClone(expected),policy,readTemplate:n=>fs.readFileSync(dir+'/'+n+'.template.wasm'),manifest:structuredClone(manifest),record:structuredClone(record),codeSet:structuredClone(codeSet),payload:Uint8Array.from(payload),
  readBytes:n=>fs.readFileSync(dir+'/'+n+'.wasm'),capabilities:{owner:{ensure:()=>{}},integer:{calculate:()=>0},floating:{calculate:()=>0}}};
}
const rows=[];
function rebind(x){x.expected.modules=x.codeSet.modules.map(m=>[m.name,m.code_id,m.generation]);x.manifest.codeDigest=sha256(JSON.stringify(x.codeSet));x.record.codeDigest=x.manifest.codeDigest;x.manifest.heap.digest=recordDigest(x.record);}
function heapRebind(x){x.record.payloadDigest=sha256(x.payload);x.manifest.heap.digest=recordDigest(x.record);}
function refused(name,mutate,pattern,install=false){
 const x=fresh();mutate(x);const before=Uint8Array.from(new Uint8Array(x.memory.buffer));
 assert.throws(()=>{const a=admitCrossImage(x);if(install)a.install();},pattern,name);
 assert.deepEqual(new Uint8Array(x.memory.buffer),before,name+' wrote memory');
 for(const table of [x.env.table,x.env.tail_table])for(let i=0;i<table.length;i++)assert.equal(table.get(i),null,name+' wrote table');
 rows.push({name,status:'REFUSED',unchanged:true});
}

refused('serialized engine slot',x=>{x.codeSet.modules[0].slot=24;rebind(x);},/SERIALIZED_SLOT/);
for(const [label,value] of [['missing',undefined],['reserved',3],['capacity',64],['fractional',24.5]])
 refused('owner slot '+label,x=>x.expected.slots[16]=value,/SLOT/);
refused('duplicate owner slot',x=>x.expected.slots[17]=x.expected.slots[16],/SLOT/);
refused('table authority',x=>x.expected.table_capacity=65,/TABLE_AUTHORITY/);
refused('missing owner mapping',x=>delete x.expected.slots,/TABLE_AUTHORITY/);
refused('missing profile',x=>{delete x.codeSet.modules[0].profile;rebind(x);},/PROFILE/);
// An actual keyword import with every D2 and outer digest rebound. This reaches
// the image-specific clause; the general generated-module ABI allows keywords.
refused('keyword import',x=>{
 const r=x.codeSet.modules[0],stem=new URL('./keyword-control',import.meta.url).pathname;
 const wat=fs.readFileSync(dir+'/'+r.name+'.wat','utf8').replace('(module','(module\n (import "keywords" "unresolved" (global $unresolved_keyword i32))');
 Object.assign(r,inventory(wat,stem,policy,versions));
 const read=x.readBytes,template=x.readTemplate;
 x.readBytes=n=>n===r.name?fs.readFileSync(stem+'.wasm'):read(n);
 x.readTemplate=n=>n===r.name?fs.readFileSync(stem+'.template.wasm'):template(n);
 rebind(x);
},/KEYWORD_IMPORT/);
refused('manifest version',x=>x.manifest.version++,/MANIFEST/);
refused('inventory digest',x=>x.codeSet.modules[0].arity[0]++,/CODE_DIGEST/);
refused('packaging',x=>{x.codeSet.packaging='forged';rebind(x);},/PACKAGING/);
refused('heap length',x=>x.manifest.heap.bytes+=8,/HEAP_LENGTH/);
refused('registry overlaps heap',x=>{x.env.code_registry=x.manifest.heap.start;const v=new DataView(x.memory.buffer);v.setUint32(x.env.code_registry,64,true);v.setUint32(x.env.code_registry+4,1,true);},/REGISTRY_OVERLAP/);
refused('module count',x=>x.manifest.modules++,/MODULE_COUNT/);
refused('same tables',x=>x.env.tail_table=x.env.table,/CAPABILITIES/);
refused('registry header',x=>new DataView(x.memory.buffer).setUint32(4100,0,true),/REGISTRY/);
refused('module name',x=>{x.codeSet.modules[0].name='../escape';rebind(x);},/NAME/);
refused('duplicate code id',x=>{x.codeSet.modules[1].code_id=x.codeSet.modules[0].code_id;rebind(x);},/CODE_ID/);
refused('code role',x=>{x.codeSet.modules[0].role++;rebind(x);},/CODE_ROLE/);
refused('callable shape',x=>{x.codeSet.modules[0].captures=-1;rebind(x);},/CALLABLE_SHAPE/);
refused('occupied registry',x=>new DataView(x.memory.buffer).setUint32(4096+8+16*16,16,true),/OCCUPIED/);
refused('last module corrupt',x=>{const original=x.readBytes,last=x.codeSet.modules.at(-1).name;x.readBytes=n=>{const b=Uint8Array.from(original(n));if(n===last)b[b.length-1]^=1;return b;};},/BINARY/,true);
refused('module profile',x=>{x.codeSet.modules[0].profile='unadmitted';rebind(x);},/PROFILE/);
refused('entry role',x=>{x.codeSet.modules[0].entries[0].role='tail_entry';rebind(x);},/EXPORT_ROLE|ROLE/);
refused('import manifest',x=>{x.codeSet.modules[0].d2.outputs.full.imports[0].minimum=2;rebind(x);},/IMPORT_MANIFEST/);
refused('byte length',x=>{x.codeSet.modules[0].d2.outputs.full.byte_length++;rebind(x);},/INSTALL_RECORD/);
refused('record digest',x=>x.manifest.heap.digest='0'.repeat(64),/record digest/);
refused('payload byte',x=>x.payload[4096]^=1,/payload digest/);
refused('dropped relocation',x=>{x.record.relocations.pop();x.manifest.heap.digest=recordDigest(x.record);},/unrelocated pointer/);
refused('root outside authority',x=>{x.record.roots.find(r=>r.slot.region==='roots').slot.offset=32;x.manifest.heap.digest=recordDigest(x.record);},/binding authority/);
refused('missing static binding',x=>{x.record.roots.splice(x.record.roots.findIndex(r=>r.slot.region==='static'),1);x.manifest.heap.digest=recordDigest(x.record);},/binding completeness/);
refused('static import changed',x=>new DataView(x.memory.buffer).setUint32(manifest.static.start+8,0,true),/import identity/);
refused('duplicate symbol wire',x=>{x.codeSet.modules[0].symbols.push(x.codeSet.modules[0].symbols[0]);rebind(x);},/SYMBOL_DUPLICATE/);
refused('unresolved symbol',x=>{const row=x.codeSet.modules[0],i=row.d2.outputs.full.imports.find(i=>i.module==='symbols');row.symbols=row.symbols.filter(s=>s.wire!==i.name);rebind(x);},/SYMBOL_IMPORT/);
refused('symbol interior reference',x=>{const s=x.codeSet.modules[0].symbols.find(s=>'heap'in s.reference);s.reference.heap+=4;rebind(x);},/heap boundary/);
refused('code import outside set',x=>{x.codeSet.modules[0].codes.push({name:'absent',code_id:63});rebind(x);},/CODE_IMPORT/);
// Change an actual inventoried header and rebind the outer digests, so these
// cases reach the D1 shape checks instead of merely failing SHA-256.
for(const [tag,cells,label,pattern] of [[98,9,'package width',/package shape/],[58,15,'host symbol width',/symbol shape/],[42,12,'host function width',/function shape/]]){
 refused(label,x=>{const v=new DataView(x.payload.buffer);const boundaries=[...x.record.relocations,...x.record.roots].map(r=>r.value).filter(r=>r.tag===6&&'heap'in r).map(r=>r.heap);const at=boundaries.find(p=>(v.getUint32(p,true)&255)===tag);assert(at!==undefined);v.setUint32(at,cells*256+tag,true);heapRebind(x);},pattern);
}
// Independent clauses of the new cross-image owner boundary.
for(const [field,value] of [['version',5],['signature',18]])
 refused('code role '+field,x=>{x.codeSet.modules[0][field]=value;rebind(x);},/CODE_ROLE/);
for(const [label,value] of [['noninteger',16.5],['reserved',15],['capacity',64]])
 refused('code id '+label,x=>{x.codeSet.modules[0].code_id=value;rebind(x);},/CODE_ID/);
refused('duplicate name',x=>{x.codeSet.modules[1].name=x.codeSet.modules[0].name;rebind(x);},/NAME/);
refused('memory capability',x=>x.env.memory=new WebAssembly.Memory({initial:64,maximum:32769,shared:true}),/CAPABILITIES/);
refused('registry alignment',x=>x.env.code_registry++,/REGISTRY/);
refused('registry extent',x=>x.env.code_registry=x.memory.buffer.byteLength,/REGISTRY/);
refused('registry capacity',x=>new DataView(x.memory.buffer).setUint32(4096,65,true),/REGISTRY/);
for(const [field,value] of [['version',2],['first_code_id',0]])
 refused('inventory '+field,x=>{x.codeSet[field]=value;rebind(x);},/PACKAGING/);
for(const [label,mutate] of [
 ['arity width',r=>r.arity.pop()],['required count',r=>r.arity[0]=-1],
 ['optional count',r=>r.arity[1]=0.5],['rest flag',r=>r.arity[2]=1],
 ['key flag',r=>r.arity[3]=1],['allow-other-keys flag',r=>r.arity[4]=1],
 ['keyword set',r=>r.arity[5]=['K']],['capture count',r=>r.captures=0.5]])
 refused('callable '+label,x=>{mutate(x.codeSet.modules[0]);rebind(x);},/CALLABLE_SHAPE/);
refused('duplicate code wire',x=>{const r=x.codeSet.modules.find(r=>r.codes.length);assert(r);r.codes.push(r.codes[0]);rebind(x);},/CODE_IMPORT/);
{
 const x=fresh(),a=admitCrossImage(x),p=4096+8+16*16;
 new DataView(x.memory.buffer).setUint32(p,16,true);
 const before=Uint8Array.from(new Uint8Array(x.memory.buffer));assert.throws(()=>a.install(),/REGISTRY_CHANGED/);
 assert.deepEqual(new Uint8Array(x.memory.buffer),before);
 for(const t of [x.env.table,x.env.tail_table])for(let i=0;i<t.length;i++)assert.equal(t.get(i),null);
 rows.push({name:'late registry mutation',status:'REFUSED',unchanged:true});
}
// An owner mutation after admission must roll back the paired table entries.
{
 const x=fresh(),a=admitCrossImage(x);new DataView(x.memory.buffer).setUint32(manifest.static.start+8,0,true);
 const before=Uint8Array.from(new Uint8Array(x.memory.buffer));assert.throws(()=>a.install(),/imports changed/);
 assert.deepEqual(new Uint8Array(x.memory.buffer),before);
 for(const t of [x.env.table,x.env.tail_table])for(let i=0;i<t.length;i++)assert.equal(t.get(i),null);
 rows.push({name:'late static mutation',status:'REFUSED',unchanged:true});
}
const clean=fresh(),a=admitCrossImage(clean);a.install();assert.equal(a.state,'INSTALLED');
const final=Uint8Array.from(new Uint8Array(clean.memory.buffer));assert.throws(()=>a.install(),/STATE/);assert.deepEqual(new Uint8Array(clean.memory.buffer),final);rows.push({name:'repeated install',status:'REFUSED',unchanged:true});
rows.push({name:'clean set installs',status:'INSTALLED',objects:a.objects});
console.log(JSON.stringify({status:'PASS',rows}));
