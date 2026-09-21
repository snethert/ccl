import fs from 'node:fs';import assert from 'node:assert/strict';
const [kind,binary,output,only='all']=process.argv.slice(2),NIL=77825,rows=[];
for(const base of [262144,2147483648]){
 const memory=new WebAssembly.Memory({initial:Math.max(64,Math.ceil((base+65536)/65536)),maximum:32769,shared:true});
 const service=(await WebAssembly.instantiate(fs.readFileSync(binary),{env:{memory}})).instance.exports;
 const d=new DataView(memory.buffer),put=(p,v)=>d.setUint32(p,v,true),bytes=(p,n)=>new Uint8Array(memory.buffer,p,n),limit=memory.buffer.byteLength,result=2048000;
 const checked=(name,call,expected)=>{let actual;try{actual=call();}catch(e){assert.fail(name+': trap instead of refusal: '+e);}assert.equal(actual,expected,name);};
 if(kind==='population'){
  const name='SET before result validation',member=base+33;[762,0,NIL,0].forEach((v,i)=>put(base+4*i,v));put(member-1,NIL);put(member+3,68);
  bytes(limit-16,16).fill(0xa5);const before=bytes(base,48).slice(),published=bytes(limit-16,16).slice();
  checked(name,()=>service.pop_run(base+6,base+16,1,member,NIL,0,0,limit-8),1);
  assert.deepEqual(bytes(base,48),before,name);assert.deepEqual(bytes(limit-16,16),published,name+' publication');rows.push({base,name,status:1});
 }else{
  const end=base+service.ht_size(4),scratch=1900000;
  const cases=kind==='equal'?[
   {name:'table overlap',key:base+1},
   {name:'static cons overlap',key:1048577,prepare:()=>{put(1048576,NIL);put(1048580,NIL);}},
  ]:[];
  // Components must be checked, even though top-level sentinels are checked by ht_run.
  for(const marker of [243,251])for(const field of [0,1])cases.push({name:'nested marker '+marker+' field '+field,key:base+1030,prepare:()=>{put(base+1024,538);put(base+1028,field===0?marker:0);put(base+1032,field===1?marker:0);put(base+1036,0);}});
  if(kind==='equal')for(const marker of [243,251])cases.push({name:'cons marker '+marker,key:base+2049,prepare:()=>{put(base+2048,NIL);put(base+2052,marker);}});
  for(const row of cases){if(only!=='all'&&!row.name.startsWith(only))continue;
   assert.equal(service.ht_init(base,end,4),0);row.prepare?.();bytes(result,16).fill(0xa5);
   const table=bytes(base,end-base).slice(),key=bytes(base+1024,1040).slice();
   checked(row.name,()=>service.ht_run(base+6,end,1,row.key,68,scratch,scratch+131072,result),3);
   assert.deepEqual(bytes(base,end-base),table,row.name+' table preservation');assert.deepEqual(bytes(base+1024,1040),key,row.name+' key preservation');assert(bytes(result,16).every(x=>x===0xa5),row.name+' publication');rows.push({base,name:row.name,status:3});
  }
 }
}
fs.writeFileSync(output,JSON.stringify({status:'PASS',rows},null,2)+'\n');
