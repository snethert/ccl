import fs from 'node:fs';import assert from 'node:assert/strict';
import {restoreOwned} from './transport.mjs';import {digest} from './snapshot.mjs';
const source=JSON.parse(fs.readFileSync(process.argv[2])),record=JSON.parse(Buffer.from(source.hex,'hex'));
const base=2097152,size=65536,memory=new WebAssembly.Memory({initial:33,maximum:33,shared:true});
const symbols=Object.fromEntries(Object.entries(record.symbols).map(([k,v])=>[k,v+2048]));
const firstFunction=record.objects.find(o=>Buffer.from(record.image,'hex').readUInt32LE(o.offset)===1578);
assert(firstFunction);
const controls=[
 ['truncated-function','function count',r=>{const b=Buffer.from(r.image,'hex');b.writeUInt32LE(1322,firstFunction.offset);r.image=b.toString('hex');}],
 ['interior-root','unknown or interior pointer',r=>{r.roots[0]+=8;}],
 ['omitted-object','object coverage',r=>{r.objects.splice(1,1);}],
 ['missing-keyword-owner','owner symbol binding',r=>{r.symbols['KEYWORD::UNREGISTERED']=640006;}],
 ['aliased-owner','distinct symbols merged',r=>{},o=>{o['KEYWORD::Y']=o['KEYWORD::X'];}],
 ['tail-byte','unaccounted object bytes',r=>{r.image+='0000000000000000';}],
];
const results=[];
for(const [name,diagnostic,mutate,owner]of controls){const r=structuredClone(record),o={...symbols};mutate(r);owner?.(o);const bytes=Buffer.from(JSON.stringify(r));new Uint8Array(memory.buffer,base,size).fill(0xa5);assert.throws(()=>restoreOwned(bytes,digest(bytes),memory,base,size,o),e=>e.message===diagnostic,name);assert(new Uint8Array(memory.buffer,base,size).every(b=>b===0xa5),name+' no publication');results.push({name,status:'REJECTED',diagnostic});}
fs.writeFileSync(process.argv[3],JSON.stringify(results,null,2)+'\n');
