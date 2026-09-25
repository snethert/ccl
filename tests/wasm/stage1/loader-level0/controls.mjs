// Isolate the new keyword metadata clauses; refusal precedes publication.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {admitCrossImage} from './runtime/cross-image.mjs';
import {recordDigest} from './runtime/heap-image.mjs';
import {sha256} from './runtime/sha256.mjs';
const dir=process.argv[2],read=n=>JSON.parse(fs.readFileSync(dir+'/'+n));
const manifest=read('manifest.json'),record=read('heap-image.json'),codeSet=read('code-set.json');
const policy=JSON.parse(fs.readFileSync(new URL('./policy.json',import.meta.url)));
const versions=JSON.parse(fs.readFileSync(new URL('./versions.json',import.meta.url)));
const expected={...versions,modules:codeSet.modules.map(m=>[m.name,m.code_id,m.generation]),
 table_capacity:64,reserved_slots:[0,1,2,3],slots:Object.fromEntries(codeSet.modules.map(m=>[m.code_id,m.code_id+8]))};
function fresh(){
 const memory=new WebAssembly.Memory({initial:64,maximum:32769,shared:true});
 new Uint8Array(memory.buffer,manifest.static.start,manifest.static.bytes).set(fs.readFileSync(dir+'/static.bin'));
 const view=new DataView(memory.buffer);view.setUint32(4096,64,true);view.setUint32(4100,1,true);
 const env={memory,tcr:1024,code_registry:4096,table:new WebAssembly.Table({initial:64,element:'anyfunc'}),
  tail_table:new WebAssembly.Table({initial:64,element:'anyfunc'}),call_error:new WebAssembly.Tag({parameters:['i32']}),
  type_error:new WebAssembly.Tag({parameters:['i32','i32']}),nonlocal_exit:new WebAssembly.Tag({parameters:['i32']})};
 return {memory,env,manifest:structuredClone(manifest),record:structuredClone(record),codeSet:structuredClone(codeSet),
  payload:fs.readFileSync(dir+'/heap.payload.bin'),regions:[{name:'static',start:manifest.static.start,size:manifest.static.bytes,kind:'objects'},
   {name:'roots',start:manifest.roots.start,size:64,kind:'roots'}],expected,policy,
  readBytes:n=>fs.readFileSync(dir+'/'+n+'.wasm'),readTemplate:n=>fs.readFileSync(dir+'/'+n+'.template.wasm'),
  capabilities:{owner:{ensure:()=>{}},integer:{calculate:()=>0},floating:{calculate:()=>0}}};
}
const rows=[];
for(const [name,mutate,pattern] of [
 ['keyword wire type',r=>{
   // Give the numeric key a valid property-name alias. Without the type
   // clause, KEYWORD_SYMBOL succeeds and the image really installs.
   const symbol=r.symbols.find(s=>s.wire===r.arity[5][0]);
   r.symbols.push({wire:'17',reference:symbol.reference});r.arity[5][0]=17;
  },/CALLABLE_SHAPE/],
 ['keywords without key flag',r=>r.arity[3]=false,/CALLABLE_SHAPE/],
 ['missing keyword wire',r=>r.arity[5][0]='missing_keyword_wire',/KEYWORD_SYMBOL/]]){
 const x=fresh(),row=x.codeSet.modules.find(r=>r.arity[5].length);assert(row);
 mutate(row);x.manifest.codeDigest=sha256(JSON.stringify(x.codeSet));x.record.codeDigest=x.manifest.codeDigest;
 x.manifest.heap.digest=recordDigest(x.record);
 const before=Uint8Array.from(new Uint8Array(x.memory.buffer));
 assert.throws(()=>admitCrossImage(x).install(),pattern,name);
 assert.deepEqual(new Uint8Array(x.memory.buffer),before);
 for(const t of [x.env.table,x.env.tail_table])for(let i=0;i<t.length;i++)assert.equal(t.get(i),null);
 rows.push({name,status:'REFUSED',unchanged:true});
}
const x=fresh(),a=admitCrossImage(x);a.install();assert.equal(a.state,'INSTALLED');
console.log(JSON.stringify({status:'PASS',rows,valid_keywords:'INSTALLED'}));
