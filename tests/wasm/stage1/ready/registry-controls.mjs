// Oversized module lists and overlapping registries refuse before memory writes.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import assert from 'node:assert/strict';
const [dir,output]=process.argv.slice(2),work=path.join(path.dirname(output),'registry-control-work');
fs.mkdirSync(work);fs.mkdirSync(work+'/compiled');
const source=fs.readFileSync(dir+'/install.mjs','utf8');
const rows=[];
try{
 for(const [name,count,text,reason]of [
  ['module-capacity',4352,source,/fixture code registry capacity/],
  ['registry-overlap',0,source.replace('capacity=4352','capacity=4608'),/registry must precede NIL/]]){
  fs.writeFileSync(work+'/compiled/modules.json',JSON.stringify(Array(count).fill({})));
  fs.writeFileSync(work+'/compiled/materialized.json','{"image":"","roots":[]}');
  const file=work+'/'+name+'.mjs';fs.writeFileSync(file,text);
  const {install}=await import(pathToFileURL(file));
  const memory=new WebAssembly.Memory({initial:128,maximum:32769,shared:true});
  const view=new DataView(memory.buffer),bytes=new Uint8Array(memory.buffer);bytes.fill(0xa5);
  let writes=0;
  await assert.rejects(()=>install({dir:work,memory,tcr:1024,
    get:p=>view.getUint32(p,true),put:(p,n)=>{writes++;view.setUint32(p,n,true);}}),reason);
  assert.equal(writes,0);assert(bytes.every(v=>v===0xa5));
  rows.push({name,writes});
 }
}finally{fs.rmSync(work,{recursive:true});}
fs.writeFileSync(output,JSON.stringify({status:'PASS',capacity:4352,registry:4096,end:73736,nil:77824,rows},null,2)+'\n');
console.log('PASS registry admission');
