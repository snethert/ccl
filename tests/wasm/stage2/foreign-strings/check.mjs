import {foreignService} from './runtime/foreign-service.mjs';
export function stringChecks({test,setup,equal,assert}) {
 const NIL=77825;
 const write=(f,h,s,offset=0,encoding=0)=>f.request(10,f.vec([h,offset*4,f.str(s),encoding]));
 const read=(f,h,n,offset=0,encoding=0)=>f.request(11,f.vec([h,offset*4,n*4,encoding,NIL]));
 const result=f=>{const w=f.get(f.get(f.args+8)-2+16),n=f.get(w-6)>>>8;equal(f.get(w-6)&255,191);return Array.from({length:n},(_,i)=>f.get(w-2+i*4));};
 const copy=(f,h,n)=>{equal(f.request(7,f.vec([h,0,f.bytes(new Uint8Array(n))])),0);const w=f.get(f.get(f.args+8)-2+8);return Array.from(new Uint8Array(f.memory.buffer,w-2,n));};
 const values=[0,0x7f,0x80,0x7ff,0x800,0xd7ff,0xe000,0xffff,0x10000,0x10ffff];
 const octets=[0,127,194,128,223,191,224,160,128,237,159,191,238,128,128,239,191,191,240,144,128,128,244,143,191,191];
 for(const n of [-1,0x1000000])test('string-size-admission-'+n,()=>{
  const f=setup();let reads=0;
  const library={allocate(){return {};},read(){reads++;return new Uint8Array();}};
  const service=foreignService({memory:f.memory,tcr:f.tcr,owner:f.owner,libraries:{open(){return library;}}});
  const request=(op,payload)=>{f.put(f.args+4,op*4);f.put(f.args+8,payload);return service(f.args);};
  const l=request(0,f.str('stub')),h=request(3,f.vec([l,4])),payload=f.vec([h,0,n*4,0,NIL]),frontier=f.get(f.tcr+48);
  equal(request(11,payload),-4);equal(reads,0);equal(f.get(f.tcr+48),frontier);equal(f.get(payload-2+16),NIL);
 });
 for(const placement of [0,65536])test('string-moving-'+placement,()=>{
  const f=setup({placement,boxCollect:true}),h=f.request(3,f.vec([f.library(),256]));
  equal(f.request(6,f.vec([h,0,f.bytes(Array(64).fill(126))])),0);
  equal(write(f,h,String.fromCodePoint(...values),3),octets.length*4);
  equal(String(copy(f,h,31)),String([126,126,126,...octets,126,126]));
  const before=f.get(f.tcr+56);equal(read(f,h,octets.length,3),0);assert(before!==f.get(f.tcr+56),'decode collected');
  equal(String(result(f)),String(values));equal(f.request(4,h),4);
 });
 for(const [name,s,bytes] of [['empty','',[]],['bom','\ufeffA',[239,187,191,65]],['nul','A\0B',[65,0,66]],['long','a'.repeat(4097),Array(4097).fill(97)]])
  test('string-'+name,()=>{const f=setup(),h=f.request(3,f.vec([f.library(),(bytes.length+1)*4]));
   equal(write(f,h,s),bytes.length*4);equal(String(copy(f,h,bytes.length+1)),String([...bytes,0]));
   equal(read(f,h,bytes.length),0);equal(String(result(f)),String(Array.from(s,c=>c.codePointAt(0))));equal(f.request(4,h),4);});
 const bad=[[128],[192,128],[193,191],[224,128,128],[237,160,128],[240,128,128,128],[244,144,128,128],[245,128,128,128],[255],[194],[226,130],[240,159,140],[226,65,172]];
 bad.forEach((bytes,i)=>test('string-malformed-'+i,()=>{
  const f=setup({boxCollect:true}),h=f.request(3,f.vec([f.library(),64]));equal(f.request(6,f.vec([h,0,f.bytes(bytes)])),0);
  const payload=f.vec([h,0,bytes.length*4,0,NIL]),frontier=f.get(f.tcr+48),count=f.owner.collectionCount;
  equal(f.request(11,payload),-4);equal(f.get(payload-2+16),NIL);equal(f.get(f.tcr+48),frontier);equal(f.owner.collectionCount,count);
  equal(String(copy(f,h,bytes.length)),String(bytes));equal(f.request(4,h),4);
 }));
 for(const op of [10,11])test('string-encoding-'+op,()=>{
  const f=setup(),h=f.request(3,f.vec([f.library(),16])),payload=f.vec(op===10?[h,0,f.str('A'),4]:[h,0,4,4,NIL]);
  const frontier=f.get(f.tcr+48),count=f.owner.collectionCount;equal(f.request(op,payload),-4);equal(f.get(f.tcr+48),frontier);equal(f.owner.collectionCount,count);
  if(op===11)equal(f.get(payload-2+16),NIL);equal(String(copy(f,h,4)),'0,0,0,0');equal(f.request(4,h),4);
 });
 for(const op of [10,11])for(const difference of [-1,1])test('string-arity-'+op+'-'+difference,()=>{
  const f=setup(),h=f.request(3,f.vec([f.library(),16]));
  const fields=op===10?[h,0,f.str('A'),0]:[h,0,4,0,NIL];
  if(difference===-1)fields.pop();else fields.push(NIL);
  const payload=f.vec(fields),frontier=f.get(f.tcr+48);equal(f.request(op,payload),-4);equal(f.get(f.tcr+48),frontier);
  equal(String(copy(f,h,4)),'0,0,0,0');equal(f.request(4,h),4);
 });
 for(const ch of [0xd800,0xdfff,0x110000])test('string-character-'+ch,()=>{
  const f=setup(),h=f.request(3,f.vec([f.library(),16])),s=f.str('x');f.put(s-2,ch);
  equal(f.request(10,f.vec([h,0,s,0])),-4);equal(String(copy(f,h,4)),'0,0,0,0');equal(f.request(4,h),4);
 });
 for(const [name,op,fields] of [
  ['write-bounds',10,(f,h)=>[h,12,f.str('é'),0]],['write-negative',10,(f,h)=>[h,-4,f.str(''),0]],
  ['read-bounds',11,(_f,h)=>[h,12,8,0,NIL]],['read-negative',11,(_f,h)=>[h,0,-4,0,NIL]],
  ['read-offset',11,(_f,h)=>[h,-4,0,0,NIL]],['read-length-type',11,(_f,h)=>[h,0,NIL,0,NIL]],
  ['write-offset-type',10,(f,h)=>[h,NIL,f.str(''),0]],['write-type',10,(f,h)=>[h,0,f.bytes([65]),0]],
  ['read-offset-type',11,(_f,h)=>[h,NIL,0,0,NIL]],
 ])test('string-'+name,()=>{const f=setup(),h=f.request(3,f.vec([f.library(),16])),payload=f.vec(fields(f,h)),frontier=f.get(f.tcr+48);
  equal(f.request(op,payload),-4);equal(f.get(f.tcr+48),frontier);if(op===11)equal(f.get(payload-2+16),NIL);
  equal(String(copy(f,h,4)),'0,0,0,0');equal(f.request(4,h),4);
 });
 for(const retirement of ['release','close','trap'])test('string-retired-'+retirement,()=>{
  const f=setup(),l=f.library(),h=f.request(3,f.vec([l,16]));
  if(retirement==='release')equal(f.request(4,h),4);else if(retirement==='close')equal(f.request(1,l),0);
  else equal(f.call(l,'run',[f.request(5,f.vec([h,0])),0,8]),-8);
  const entries=f.moves.length;equal(write(f,h,'A'),-4);equal(read(f,h,0),-4);equal(f.moves.length,entries);
 });
}
