// Turn the cross-loader's raw output (heap.bin, static.bin, image.json,
// code-set.json) into the two coordinated artifacts: the heap-image.mjs
// record over a live Memory, and the code-set inventory whose module
// binaries are assembled from the emitted WAT. No host address survives:
// symbol imports become heap or static references, code imports code IDs.
import fs from 'node:fs';
import path from 'node:path';
import {writeHeapImage} from './runtime/heap-image.mjs';
import {sha256} from './runtime/sha256.mjs';
import {PACKAGING} from './runtime/bundle.mjs';
import {inventory} from './d2.mjs';
const need=(v,s)=>{if(!v)throw Error('write: '+s);};
const RUNTIME_SYMBOLS=['condition_registry','error_message','expected_function'],ROOTS=1190000,ROOT_NAMES=['cold-load-functions','all-packages','toplevel-function','unbound-function'];
export function write(dir,out,policy,versions){
 fs.mkdirSync(out,{recursive:true});
 const image=JSON.parse(fs.readFileSync(path.join(dir,'image.json'))),codeSet=JSON.parse(fs.readFileSync(path.join(dir,'code-set.json')));
 const heap=fs.readFileSync(path.join(dir,'heap.bin')),fixed=fs.readFileSync(path.join(dir,'static.bin'));
 need(image.version===1&&image.layout==='D1'&&heap.length===image.dynamic.bytes&&fixed.length===image.static.bytes,'image shape');
 need(image.dynamic.start%8===0&&heap.length%8===0&&image.static.start%8===0&&fixed.length%8===0,'alignment');
 const start=image.dynamic.start,end=start+heap.length;
 const memory=new WebAssembly.Memory({initial:Math.ceil((end+65536)/65536),maximum:32769,shared:true});
 new Uint8Array(memory.buffer,image.static.start,fixed.length).set(fixed);
 new Uint8Array(memory.buffer,start,heap.length).set(heap);
 const view=new DataView(memory.buffer);
 need(ROOTS+64<=start&&ROOTS>=image.static.start+fixed.length,'roots placement');
 ROOT_NAMES.forEach((name,i)=>{const w=image.values[name]??image.unbound;need(Number.isInteger(w),'root '+name);view.setUint32(ROOTS+4*i,w,true);});
 const regions=[{name:'static',start:image.static.start,size:fixed.length,kind:'objects'},{name:'roots',start:ROOTS,size:64,kind:'roots'}];
 const reference=w=>{const tag=w%8,p=w-tag;need(tag===6||tag===1,'reference tag');
  if(p>=start&&p<end)return {heap:p-start,tag};
  need(p>=image.static.start&&p<image.static.start+fixed.length,'reference outside the image: '+w);return {region:'static',offset:p-image.static.start,tag};};
 // Code set: assemble every module, record its identity, imports and entries.
 const modules=[];
 for(const m of codeSet.modules){
  m.symbols??=[];m.codes??=[];m.children??=[];m.arity=m.arity.map((v,i)=>i===5?(v??[]):i>=2?!!v:v); // the Lisp writer prints NIL as null
  const compiled=inventory(m.wat,path.join(out,m.name),policy,versions);
  const imports=compiled.d2.outputs.full.imports;
  const symbols=m.symbols.map(([wire,address])=>({wire,reference:reference(address)}));
  for(const i of imports)if(i.module==='symbols')need(symbols.some(s=>s.wire===i.name),'unresolved symbol '+i.name);
  for(const i of imports)if(i.module==='codes')need(m.codes.some(([name])=>name===i.name),'code import '+i.name);
  need(!imports.some(i=>i.module==='keywords'),'keyword imports are not admitted');
  modules.push({name:m.name,code_id:m.id,version:4,signature:17,role:23,arity:m.arity,captures:m.captures,...compiled,
   symbols,codes:m.codes.map(([name,id])=>({name,code_id:id})),children:m.children});
 }
 const bundle={version:1,packaging:PACKAGING,...versions,first_code_id:codeSet['first-code-id'],modules};
 const codeDigest=sha256(new TextEncoder().encode(JSON.stringify(bundle)));
 // Static NIL/T symbols contain outgoing pointers into the dynamic image.
 // Bind their node fields using the existing root relocation mechanism.
 need(fixed.length===72&&view.getUint32(image.static.start+8,true)===1850&&view.getUint32(image.static.start+40,true)===1850,'canonical static shape');
 const staticSlots=[0,4,...[8,40].flatMap(p=>[4,8,12,16,20,24,28].map(o=>p+o))].map(o=>image.static.start+o).filter(p=>{const w=view.getUint32(p,true);return (w%8===1||w%8===6)&&w>=start&&w<end;});
 const rootSlots=[...ROOT_NAMES.map((_,i)=>ROOTS+4*i),...staticSlots];
 const {record,payload,digest,objects}=writeHeapImage({memory,start,end,regions,rootSlots,codeDigest});
 for(const p of staticSlots)fixed.writeUInt32LE(0,p-image.static.start);

 fs.writeFileSync(path.join(out,'code-set.json'),JSON.stringify(bundle,null,1)+'\n');
 fs.writeFileSync(path.join(out,'heap-image.json'),JSON.stringify(record,null,1)+'\n');
 fs.writeFileSync(path.join(out,'heap.payload.bin'),payload);
 fs.writeFileSync(path.join(out,'static.bin'),fixed);
 const symbols=image.symbols.map(s=>({package:s.package,name:s.name,reference:reference(s.address)}));
 const manifest={version:1,layout:'D1',heap:{start,bytes:payload.length,digest,payloadDigest:record.payloadDigest,objects},static:{start:image.static.start,bytes:fixed.length,sha256:sha256(fixed)},
  roots:{start:ROOTS,names:ROOT_NAMES,slots:rootSlots},nil:image.nil,t:image.t,unbound:image.unbound,codeDigest,modules:modules.length,symbols};
 fs.writeFileSync(path.join(out,'manifest.json'),JSON.stringify(manifest,null,1)+'\n');
 return {digest,codeDigest,objects,modules:modules.length,relocations:record.relocations.length,heapBytes:payload.length};
}
if(process.argv[1]===new URL(import.meta.url).pathname)console.log(JSON.stringify(write(process.argv[2],process.argv[3],JSON.parse(fs.readFileSync(process.argv[4])),JSON.parse(fs.readFileSync(process.argv[5])))));
