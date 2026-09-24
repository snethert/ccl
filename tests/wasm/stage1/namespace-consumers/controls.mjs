import assert from 'node:assert/strict';

export function checkBoundaries({memory,gen,row,get,put,tcr,collect}) {
 const rows=[],N=77825,T=77838,bytes=(p,n)=>new Uint8Array(memory.buffer,p,n);
 collect();
 const raw=(tag,count,payload)=>{
  const size=(4+payload+7)&~7,p=get(tcr+48);
  assert(p+size<=get(tcr+52));bytes(p,size).fill(0);
  put(p,(count<<8)|tag);put(tcr+48,p+size);return p+6;
 };
 const copy=(...args)=>gen.invoke(row('NAMESPACE-BYTE-COPY'),args);
 const layouts=[[7,3,12],[159,3,12],[167,3,12],[175,3,12],[183,3,12],[191,3,12],
  [199,3,3],[207,3,3],[215,3,6],[223,3,6],[231,3,28],[239,3,28],[247,3,52],[255,17,3]];
 for(const [tag,count,size] of layouts) {
  const source=raw(tag,count,size),destination=raw(199,size+4,size+4);
  const pattern=Uint8Array.from({length:size},(_,i)=>(17+31*i)&255);
  bytes(source-2,size).set(pattern);bytes(destination-2,size+4).fill(219);
  assert.deepEqual(copy(source,0,destination,8,size*4),[destination]);
  assert.deepEqual(bytes(destination-2,size+4),Uint8Array.from([219,219,...pattern,219,219]));
  assert.deepEqual(copy(source,size*4,destination,0,0),[destination]);
  const before=Uint8Array.from(bytes(destination-6,(4+size+4+7)&~7));
  assert.throws(()=>copy(source,size*4,destination,0,4),/checked \d+$/);
  assert.deepEqual(bytes(destination-6,before.length),before,'logical bound precedes destination write');
  rows.push('copy layout '+tag);
 }
 const source=raw(199,8,8),destination=raw(199,8,8),node=raw(250,2,8),emptyBignum=raw(7,0,4);
 bytes(source-2,8).set([1,2,3,4,5,6,7,8]);bytes(destination-2,8).fill(219);
 const cases=[
  ['source tag',[0,0,destination,0,4]],['destination tag',[source,0,0,0,4]],
  ['source kind',[node,0,destination,0,4]],['destination kind',[source,0,node,0,4]],
  ['bignum count',[emptyBignum,0,destination,0,0]],
  ['source span',[(memory.buffer.byteLength+6)>>>0,0,destination,0,4]],
  ['destination span',[source,0,(memory.buffer.byteLength+6)>>>0,0,4]],
  ['source negative',[source,-4,destination,0,4]],['source nonfixnum',[source,T,destination,0,4]],
  ['destination negative',[source,0,destination,-4,4]],['destination nonfixnum',[source,0,destination,T,4]],
  ['count negative',[source,0,destination,0,-4]],['count nonfixnum',[source,0,destination,0,T]],
  ['source overrun',[source,32,destination,0,4]],['destination overrun',[source,0,destination,32,4]],
  ['empty copy offset',[source,36,destination,0,0]],['offset plus count',[source,2147483644,destination,0,2147483644]]
 ];
 for(const [name,args] of cases) {
  const before=Uint8Array.from(bytes(destination-6,16));
  assert.throws(()=>copy(...args),/checked \d+$/,'checked byte-copy refusal: '+name);
  assert.deepEqual(bytes(destination-6,16),before,'refusal preserves destination: '+name);
  rows.push(name);
 }
 const allocate=(...args)=>gen.invoke(row('NAMESPACE-VECTOR-ALLOCATE'),args);
 for(const [name,args] of [
  ['count negative',[-4,199*4,0]],['count nonfixnum',[T,199*4,0]],['count header overflow',[67108864,199*4,0]],
  ['unknown kind',[4,0,0]],['kind nonfixnum',[4,N,0]],
  ['u8 low',[4,199*4,-4]],['u8 high',[4,199*4,1024]],
  ['s8 low',[4,207*4,-516]],['s8 high',[4,207*4,512]],
  ['u16 low',[4,215*4,-4]],['u16 high',[4,215*4,262144]],
  ['s16 low',[4,223*4,-131076]],['s16 high',[4,223*4,131072]],
  ['u32 negative',[4,167*4,-4]],['s32 noninteger',[4,175*4,T]],['fixnum noninteger',[4,183*4,T]]
 ]) {
  const frontier=get(tcr+48);
  assert.throws(()=>allocate(...args),/checked \d+$/,'checked vector allocation refusal: '+name);
  assert.equal(get(tcr+48),frontier,'allocation refusal precedes publication: '+name);
  rows.push('allocate '+name);
 }
 return rows;
}
