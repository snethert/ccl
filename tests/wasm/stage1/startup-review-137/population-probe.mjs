import fs from 'node:fs';import assert from 'node:assert/strict';
const [binary,output]=process.argv.slice(2),NIL=77825,rows=[];
for(const base of [262144,2147483648]){
 const memory=new WebAssembly.Memory({initial:Math.max(64,Math.ceil((base+65536)/65536)),maximum:32769,shared:true});
 const service=(await WebAssembly.instantiate(fs.readFileSync(binary),{env:{memory}})).instance.exports;
 const d=new DataView(memory.buffer),put=(p,v)=>d.setUint32(p,v,true),bytes=(p,n)=>new Uint8Array(memory.buffer,p,n),result=2048000;
 const cases=[
  {name:'object tag',object:base+7,end:base+17,record:base+1,code:2},
  {name:'exact extent',end:base+24,code:2},
  {name:'type alignment',type:1,code:2},
  {name:'result alignment',result:result+1,code:1},
  {name:'publication alias',result:base+8,code:1},
  {name:'operation bound',op:3,code:5},
 ];
 for(const row of cases){
  bytes(base-16,80).fill(0x5a);bytes(result-16,80).fill(0xa5);
  const record=row.record??base;[762,row.type??0,NIL,0].forEach((v,i)=>put(record+4*i,v));
  const before=bytes(base-16,80).slice(),published=bytes(result-16,80).slice();
  assert.equal(service.pop_run(row.object??base+6,row.end??base+16,row.op??0,NIL,NIL,0,0,row.result??result),row.code,row.name);
  assert.deepEqual(bytes(base-16,80),before,'object preservation '+row.name);assert.deepEqual(bytes(result-16,80),published,'result preservation '+row.name);
 }
 rows.push({base,refusals:cases.map(r=>({name:r.name,status:r.code}))});
}
fs.writeFileSync(output,JSON.stringify({status:'PASS',rows},null,2)+'\n');
