// Image-builder representation: ordinary vector + conses, never a weak header.
// Consumers must use this representation explicitly, not native population offsets.
export const POPULATION_POLICY='stage1-bootstrap-strong-population-v1';
export function createStrongPopulation({memory,base,end,type,members,policy}){
 if(policy!==POPULATION_POLICY)throw Error('population policy');
 if(type!=='list'&&type!=='alist')throw Error('population type');
 if(!Array.isArray(members))throw Error('population members');
 const word=x=>Number.isInteger(x)&&x>=0&&x<=0xffffffff;
 const copied=members.map(x=>type==='list'?x:Array.isArray(x)&&x.length===2?x.slice():null);
 if(!copied.every(x=>type==='list'?word(x):x!==null&&x.every(word)))throw Error('population member');
 const bytes=16+copied.length*(type==='list'?8:16);
 if(!(memory instanceof WebAssembly.Memory)||!Number.isSafeInteger(base)||base<0||base%8||
    !Number.isSafeInteger(end)||end!==base+bytes||end>memory.buffer.byteLength)throw Error('population extent');
 const v=new DataView(memory.buffer),put=(p,x)=>v.setUint32(p,x,true),NIL=77825;
 let cursor=base+16,head=NIL,previous=0;
 for(const member of copied){
  let value=member;
  if(type==='alist'){put(cursor,member[1]);put(cursor+4,member[0]);value=cursor+1;cursor+=8;}
  put(cursor,NIL);put(cursor+4,value);if(previous)put(previous,cursor+1);else head=cursor+1;previous=cursor;cursor+=8;
 }
 put(base,2*256+250);put(base+4,type==='list'?0:4);put(base+8,head);put(base+12,0);
 return Object.freeze({object:base+6,end,representation:'strong-population-v1'});
}
