// Owner-installed snapshot leaf for the unchanged B adapter. Takes an empty
// pinned descriptor plus two NIL operands and returns a fresh D1 vector.
export function statisticsService({memory,owner,descriptor,result,units=1000}) {
 const NIL=77825;
 const span=(p,n)=>Number.isSafeInteger(p)&&p>=0&&p%4===0&&p+n<=memory.buffer.byteLength;
 if(owner.view.buffer!==memory.buffer||!span(descriptor-6,8)||!span(result,16)||
    (result<descriptor+2&&descriptor-6<result+16)||![1000,1000000].includes(units))throw Error('statistics admission');
 // Result scratch and descriptor are trusted pinned owner regions outside the
 // moving spaces, Lisp stacks and root list, as in the accepted leaf adapter.
 function digits(n){const a=[];while(n){a.push(Number(n&0xffffffffn));n>>=32n;}if(a.at(-1)>=0x80000000)a.push(0);return a;}
 return function run(table,end,op,a,b,scratch,scratchEnd,pub){
  table>>>=0;end>>>=0;pub>>>=0;a>>>=0;b>>>=0;
  let v=owner.view;
  if(table!==descriptor||end!==descriptor+2||op!==5||a!==NIL||b!==NIL||pub!==result||v.getUint32(descriptor-6,true)!==250)return 4;
  const values=owner.gctime(units); // Capture before assurance, which can collect.
  const raw=values.map(n=>n<=536870911n?null:digits(n));
  const sizes=raw.map(a=>a?Math.ceil((4+4*a.length)/8)*8:0),bytes=24+sizes.reduce((a,b)=>a+b,0);
  owner.atSafepoint(o=>o.ensure(bytes));
  v=owner.view;const base=v.getUint32(owner.tcr+48,true),limit=v.getUint32(owner.tcr+52,true);
  if(base%8||base+bytes>limit)return 3;
  let cursor=base+24;const words=[];
  for(let i=0;i<5;i++){
   if(!raw[i])words.push(Number(values[i])*4);
   else {const p=cursor;v.setUint32(p,(raw[i].length*256+7)>>>0,true);raw[i].forEach((w,j)=>v.setUint32(p+4+4*j,w,true));for(let j=4+raw[i].length*4;j<sizes[i];j+=4)v.setUint32(p+j,0,true);cursor+=sizes[i];words.push(p+6);}
  }
  v.setUint32(base,5*256+250,true);words.forEach((w,i)=>v.setUint32(base+4+4*i,w,true));
  v.setUint32(owner.tcr+48,base+bytes,true);
  [base+6,NIL,1,0].forEach((w,i)=>v.setUint32(pub+4*i,w,true));return 0;
 };
}
