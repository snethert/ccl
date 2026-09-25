// Isolate the linked-range clauses using the already qualified sealed image.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {image,CONFIG,RESULT,NIL} from '../symbols/image.mjs';

const names=['range alignment','range order','range stride','range backing',
 'package overlap','descriptor overlap','scratch overlap','result overlap',
 'zero linked base','symbol below range','symbol above range','symbol stride'];
export async function controls(binary,selected=null,expectAdmission=false) {
 const memory=new WebAssembly.Memory({initial:256,maximum:32769,shared:true});
 const service=(await WebAssembly.instantiate(binary,{env:{memory}})).instance.exports;
 const rows=[];
 for(const name of selected?[selected]:names) {
  const owner=image(memory,4194304),{get,put,packages,query}=owner;
  const lo=6291456,hi=lo+64;
  put(CONFIG+72,lo);put(CONFIG+76,hi);
  assert.equal(service.symbols_admit(CONFIG,RESULT),0,'positive admitted image');
  let call=()=>service.symbols_admit(CONFIG,RESULT),expected=1;
  const ranges={
   'range alignment':[lo+1,hi+1], 'range order':[hi,lo],
   'range stride':[lo,hi+8],
   'range backing':[memory.buffer.byteLength+32,memory.buffer.byteLength+64],
   'package overlap':[4194304,4194336],
   'descriptor overlap':[CONFIG,CONFIG+32],
   'scratch overlap':[get(CONFIG+52),get(CONFIG+52)+32],
   'result overlap':[RESULT,RESULT+32]
  };
  if(ranges[name]) {
   // No package symbol depends on this range. Removing the named config
   // clause must admit the complete image, not hit a later symbol refusal.
   put(CONFIG+72,ranges[name][0]);put(CONFIG+76,ranges[name][1]);
  } else {
   const p={'zero linked base':32,'symbol below range':lo-32,
    'symbol above range':hi,'symbol stride':lo+8}[name];
   assert.notEqual(p,undefined);
   const string=query('LINKED');
   [1850,string,51,NIL,packages.A,0,NIL,0].forEach((v,i)=>put(p+4*i,v));
   // Use SYMBOL-NAME: it reaches symbase directly and does not require a
   // counterfeit table. Every other field and guard remains valid.
   if(name==='zero linked base'){put(CONFIG+72,0);put(CONFIG+76,64);}
   call=()=>service.symbols_run(CONFIG,3,p+6,NIL,NIL,RESULT);expected=2;
   if(name!=='zero linked base') {
    // The same symbol succeeds with a legal encompassing range.
    const a=get(CONFIG+72),b=get(CONFIG+76);put(CONFIG+72,p);put(CONFIG+76,p+32);
    assert.equal(call(),0,'positive linked symbol');assert.equal(get(RESULT),string);
    put(CONFIG+72,a);put(CONFIG+76,b);
   }
  }
  new Uint8Array(memory.buffer,RESULT,16).fill(0x59);
  const regions=[[4194304,65536],[CONFIG,80],[RESULT,16],[77824,72],[0,64],[lo-32,128]];
  const before=regions.map(([p,n])=>Uint8Array.from(new Uint8Array(memory.buffer,p,n)));
  const result=call();
  assert.equal(result,expectAdmission?0:expected,name);
  if(!expectAdmission)regions.forEach(([p,n],i)=>assert.deepEqual(
   new Uint8Array(memory.buffer,p,n),before[i],name+' preserves publication'));
  rows.push({name,result,statePreserved:!expectAdmission});
 }
 return rows;
}
if(process.argv[1]===new URL(import.meta.url).pathname) {
 const rows=await controls(fs.readFileSync(process.argv[2]),process.argv[4]||null,process.argv[5]==='admit');
 fs.writeFileSync(process.argv[3],JSON.stringify(rows,null,2)+'\n');
}
