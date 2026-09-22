import assert from 'node:assert/strict';
import fs from 'node:fs';
import {capture,restore,digest} from './snapshot.mjs';
const NIL=77825,memory=new WebAssembly.Memory({initial:20,maximum:32769}),base=262144;
const v=new DataView(memory.buffer),put=(p,x)=>v.setUint32(p,x,true);
[1578,4,NIL,4,NIL,NIL,NIL,0,1834,4,NIL,4,NIL,NIL,NIL,base+70,2042,0,NIL,base+97,NIL,NIL,0,0,NIL,492].forEach((x,i)=>put(base+4*i,x));
const objects=[{id:'ordinary',offset:0,tag:6},{id:'funcallable',offset:32,tag:6},{id:'immediates',offset:64,tag:6},{id:'slots',offset:96,tag:1}];
const packet=capture(memory,{base,length:104,objects,roots:[base+38],symbols:{}}),record=JSON.parse(packet.bytes),checks=[];
for(const dest of [1048576,2147483648]){
 const out=new WebAssembly.Memory({initial:Math.ceil((dest+65536)/65536),maximum:32769});
 const linked=restore(packet.bytes,packet.sha256,out,dest,104),view=new DataView(out.buffer),get=p=>view.getUint32(p,true);
 assert.deepEqual(linked.roots,[dest+38]);assert.equal(get(dest+60),dest+70);assert.equal(get(dest+76),dest+97);assert.equal(get(dest+100),492);
 const again=capture(out,{base:dest,length:104,objects,roots:linked.roots,symbols:{}});assert.equal(JSON.parse(again.bytes).image,Buffer.from(new Uint8Array(out.buffer,dest,104)).toString('hex'));checks.push({dest,moved:true});
 for(const [label,offset,value] of [['width',32,2090],['tag',60,NIL],['interior',60,base+78],['shape',64,1786]]){
  const bad=structuredClone(record),bytes=Buffer.from(bad.image,'hex');bytes.writeUInt32LE(value,offset);bad.image=bytes.toString('hex');const input=Buffer.from(JSON.stringify(bad)),before=Buffer.from(new Uint8Array(out.buffer,dest,104));
  assert.throws(()=>restore(input,digest(input),out,dest,104));assert.deepEqual(Buffer.from(new Uint8Array(out.buffer,dest,104)),before);checks.push({dest,refused:label});
 }
}
fs.writeFileSync(process.argv[2],JSON.stringify({status:'PASS',checks},null,2)+'\n');
