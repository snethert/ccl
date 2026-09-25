// Bridge CCL's simulated D1 arena to the existing heap/code artifact contracts.
import fs from 'node:fs';
import path from 'node:path';
import {sha256} from './runtime/sha256.mjs';
import {writeHeapImage,admitHeapImage} from './runtime/heap-image.mjs';
import {inspect} from './runtime/binary.mjs';
import {entryRanges} from './runtime/ranges.mjs';
import {manifest,materialize} from './runtime/materializer.mjs';
import {PACKAGING,signatures,validate} from './runtime/bundle.mjs';

const out=process.argv[2], read=n=>JSON.parse(fs.readFileSync(path.join(out,n)));
const save=(n,x)=>fs.writeFileSync(path.join(out,n),JSON.stringify(x,null,2)+'\n');
const source=read('producer/cross-load.json'), policy=read('policy.json');
const versions=read('versions.json'), classifications=read('classifications.json');
fs.mkdirSync(path.join(out,'artifact'),{recursive:true});
const modules=source.modules.map(m=>{
  const bytes=fs.readFileSync(path.join(out,`producer/module-${m.code_id}.wasm`));
  const x=inspect(bytes,{ownerRetry:true}),abi={minimum:1,maximum:32769,imports:x.imports,
    exports:x.exports.map(e=>({name:e.name,kind:e.kind,index:e.index,signature:x.types[x.functions[e.index]]}))};
  const classification=classifications[m.code_id],template=manifest(bytes,abi,classification,policy);
  const full=materialize(bytes,template,abi,classification,policy,'full');
  fs.writeFileSync(path.join(out,`artifact/module-${m.code_id}.wasm`),full.bytes);
  fs.writeFileSync(path.join(out,`artifact/template-${m.code_id}.wasm`),bytes);
  const ranges=entryRanges(full.bytes,{ownerRetry:true});
  return {name:m.name,code_id:m.code_id,slot:m.code_id+3,generation:1,...versions,
    d2:{abi,classification,template,outputs:{full:full.record}},
    entries:['entry','tail_entry'].map(role=>({role,export:role,
      table:role==='entry'?'public':'tail',function_index:x.exports.find(e=>e.name===role).index,
      signature:signatures[role],range:ranges.find(e=>e.role===role)}))};
});
const bundle={version:1,packaging:PACKAGING,...versions,modules};
const expected={...versions,modules:modules.map(m=>[m.name,m.code_id,m.generation]),
  table_capacity:modules.length+4,reserved_slots:[0,1,2,3]};
validate(bundle,expected,n=>fs.readFileSync(path.join(out,`artifact/module-${modules.find(m=>m.name===n).code_id}.wasm`)));
save('artifact/bundle.json',bundle);save('artifact/expected.json',expected);
const codeDigest=sha256(JSON.stringify(bundle));
const heap=fs.readFileSync(path.join(out,'producer/heap.bin'));
const canonical=fs.readFileSync(path.join(out,'producer/static.bin'));
const memory=new WebAssembly.Memory({initial:32}),view=new DataView(memory.buffer);
new Uint8Array(memory.buffer,source.heapBase,heap.length).set(heap);
new Uint8Array(memory.buffer,source.staticBase,canonical.length).set(canonical);
const roots=source.roots.map(([name,value])=>({name,value}));
for(const [pkg,name,value] of source.symbols)roots.push({name:`symbol:${pkg}:${name}`,value});
for(const m of source.modules){
  roots.push({name:`function:${m.code_id}`,value:m.function});
  for(const [wire,value] of m.symbols)roots.push({name:`import:${m.code_id}:${wire}`,value});
}
const rootBase=4096,rootBytes=Math.ceil(roots.length*4/8)*8;
const rootSlots=roots.map((r,i)=>{const p=rootBase+i*4;view.setUint32(p,r.value,true);return p;});
// Canonical symbols are fixed-address objects. Their pointer-bearing fields
// are explicit relocation roots; they never retain builder arena addresses.
for(let p=source.staticBase+8;p<source.staticBase+canonical.length;p+=32)
  for(let field=1;field<=7;field++)rootSlots.push(p+4*field);
const regions=[{name:'roots',kind:'roots',start:rootBase,size:rootBytes},
  {name:'canonical',kind:'objects',start:source.staticBase,size:canonical.length}];
const image=writeHeapImage({memory,start:source.heapBase,end:source.heapBase+heap.length,
  regions,rootSlots,codeDigest});
// The canonical template contains no pointer to the simulated arena.
const staticTemplate=Uint8Array.from(canonical),sv=new DataView(staticTemplate.buffer);
for(const p of rootSlots)if(p>=source.staticBase&&p<source.staticBase+canonical.length)
  sv.setUint32(p-source.staticBase,77825,true);
fs.writeFileSync(path.join(out,'artifact/static.bin'),staticTemplate);
fs.writeFileSync(path.join(out,'artifact/heap.bin'),image.payload);
save('artifact/heap.json',image.record);
save('artifact/image.json',{version:1,digest:image.digest,codeDigest,regions,rootSlots,
  roots:roots.map((r,i)=>({name:r.name,slot:rootBase+4*i})),staticDigest:sha256(staticTemplate),
  modules:source.modules.map(m=>({code_id:m.code_id,symbols:m.symbols.map(([wire])=>wire)}))});
// A fresh image must pass the production admission before anything is called.
const fresh=new WebAssembly.Memory({initial:64});
new Uint8Array(fresh.buffer,source.staticBase,staticTemplate.length).set(staticTemplate);
const admitted=admitHeapImage({memory:fresh,record:image.record,payload:image.payload,
  digest:image.digest,regions,start:2097152,limit:4194304,codeDigest,rootSlots});
admitted.install();
save('producer-summary.json',{status:'PASS',faslPublished:true,modules:modules.length,
  objects:image.objects,heapBytes:heap.length,rootSlots:rootSlots.length,
  relocations:image.record.relocations.length,codeDigest,imageDigest:image.digest,
  targetBoot:false});
console.log('CROSS-LOAD-IMAGE-PASS');
