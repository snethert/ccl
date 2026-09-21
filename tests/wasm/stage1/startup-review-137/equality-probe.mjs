import fs from 'node:fs';import assert from 'node:assert/strict';
const [binary,output]=process.argv.slice(2),NIL=77825,T=77838,rows=[];
for(const base of [262144,2147483648]){
 const memory=new WebAssembly.Memory({initial:Math.max(64,Math.ceil((base+65536)/65536)),maximum:32769,shared:true});
 const service=(await WebAssembly.instantiate(fs.readFileSync(binary),{env:{memory}})).instance.exports;
 const d=new DataView(memory.buffer),get=p=>d.getUint32(p,true),put=(p,v)=>d.setUint32(p,v,true),bytes=(p,n)=>new Uint8Array(memory.buffer,p,n);
 const table=base+6,end=base+service.ht_size(4),scratch=1900000,result=2048000,cons=base+1024;
 put(NIL-1,NIL);put(NIL+3,NIL);put(cons,NIL);put(cons+4,NIL);
 const reset=()=>assert.equal(service.ht_init(base,end,4),0);
 const run=(op,key,value=NIL)=>service.ht_run(table,end,op,key,value,scratch,scratch+131072,result);
 reset();assert.equal(run(1,NIL,68),0);assert.equal(run(0,cons+1),0);assert.deepEqual([get(result),get(result+4)],[NIL,NIL],'NIL versus cons');
 reset();assert.equal(run(1,cons+1,68),0);assert.equal(run(0,NIL),0);assert.deepEqual([get(result),get(result+4)],[NIL,NIL],'cons versus NIL');
 const depths=[];
 for(const depth of [1022,1023,1024,3000]){
  reset();let key=NIL;
  for(let i=0;i<depth;i++){const p=base+2048+i*8;put(p,NIL);put(p+4,key);key=p+1;}
  const before=bytes(base,end-base).slice(),graph=bytes(base+2048,depth*8).slice();bytes(result,16).fill(0xa5);
  const code=run(1,key,68);assert.equal(code,depth<=1023?0:3,'bounded car depth '+depth);
  assert.deepEqual(bytes(base+2048,depth*8),graph,'key preservation');
  if(code){assert.deepEqual(bytes(base,end-base),before,'table preservation');assert(bytes(result,16).every(b=>b===0xa5),'publication preservation');}
  else{assert.equal(run(0,key),0);assert.deepEqual([get(result),get(result+4)],[68,T],'deep exact fit lookup');}
  depths.push({depth,status:code});
 }
 rows.push({base,nilConsAbsent:true,depths});
}
fs.writeFileSync(output,JSON.stringify({status:'PASS',rows},null,2)+'\n');
