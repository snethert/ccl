import fs from 'node:fs';import assert from 'node:assert/strict';
const [dir,out,only='all']=process.argv.slice(2),rows=[],NIL=77825,T=77838;
for(const base of [262144,2147483648]){
 const memory=new WebAssembly.Memory({initial:Math.max(64,Math.ceil((base+65536)/65536)),maximum:32769,shared:true}),v=new DataView(memory.buffer),put=(p,x)=>v.setUint32(p,x,true),get=p=>v.getUint32(p,true),bytes=(p,n)=>new Uint8Array(memory.buffer,p,n);
 const service=(await WebAssembly.instantiate(fs.readFileSync(dir+'/eql.wasm'),{env:{memory}})).instance.exports;
 assert.equal(service.ht_kind(),1,'shared EQL service');assert.equal(typeof service.ht_run,'function');
 const result=2048000,call=(a,b,r=result)=>service.ht_eql(a,0,3,b,NIL,0,0,r);
 const setup=()=>{bytes(base,256).fill(0);bytes(result,32).fill(0xa5);put(base,NIL);put(base+4,NIL);put(base+8,NIL);put(base+12,NIL);
  for(const p of [base+32,base+48]){put(p,519);put(p+4,0);put(p+8,1);} // distinct canonical 2^32 bignums
  for(const p of [base+64,base+80]){put(p,791);v.setFloat64(p+8,2,true);}
 };
 if(only==='all')for(const [name,a,b,expected] of [
  ['nil',NIL,NIL,T],['nil-cons',NIL,base+1,NIL],['same-cons',base+1,base+1,T],['distinct-cons',base+1,base+9,NIL],
  ['fixnum',68,68,T],['unequal-fixnum',68,72,NIL],['bignum',base+38,base+54,T],['double',base+70,base+86,T],['different-types',8,base+70,NIL]
 ]){setup();const before=bytes(base,256).slice();assert.equal(call(a,b),0,name);assert.deepEqual([0,4,8,12].map(o=>get(result+o)),[expected,NIL,1,0],name+' publication');assert.deepEqual(bytes(base,256),before,name+' input');const table=base+256,end=table+service.ht_size(4);assert.equal(service.ht_init(table,end,4),0);assert.equal(service.ht_run(table+6,end,1,a,28,1900000,1900032,result),0);assert.equal(service.ht_run(table+6,end,0,b,NIL,1900000,1900032,result),0);assert.equal(get(result+4),expected,name+' shared table EQL');rows.push({base,name});}
 for(const [name,a,b,r,status] of [
  ['result-alignment',NIL,NIL,result+1,1],['result-bounds',NIL,NIL,memory.buffer.byteLength-8,1],['result-static',NIL,NIL,1048608,1],
  ['left-key',243,NIL,result,3],['right-key',NIL,251,result,3]
 ]){if(only!=='all'&&only!==name)continue;setup();const before=bytes(base,256).slice(),n=Math.min(16,memory.buffer.byteLength-r);bytes(r,n).fill(0xa5);const saved=bytes(r,n).slice();
  let actual;try{actual=call(a,b,r);}catch(e){assert.fail(name+' trapped '+e);}assert.equal(actual,status,name);assert.deepEqual(bytes(base,256),before,name+' source');assert.deepEqual(bytes(r,n),saved,name+' publication');rows.push({base,refusal:name});
 }
}
fs.writeFileSync(out,JSON.stringify({status:'PASS',rows},null,2)+'\n');
