// Trusted single-Worker Lisp marshalling. Foreign modules receive only scalars
// and offsets in their own memory. Request objects stay on generated B roots.
import {foreignFailure} from './foreign-module.mjs';
const NIL=77825;
class Refusal extends Error {}
const need=(ok,why)=>{if(!ok)throw new Refusal(why);};
export function foreignService({memory,tcr,owner,libraries,maximumTokens=536870911}) {
 need(Number.isInteger(maximumTokens)&&maximumTokens>0&&maximumTokens<=536870911,'TOKEN_LIMIT');
 const tokens=new Map(),names=new Map();let next=1,busy=false;
 const view=()=>new DataView(memory.buffer),get=p=>view().getUint32(p,true),put=(p,v)=>view().setUint32(p,v,true);
 const fix=word=>{need(word%4===0,'FIXNUM');return (word|0)>>2;};
 const object=(word,tag)=>{
  need(word%8===6&&word>=6&&word-2<=memory.buffer.byteLength,'OBJECT');
  const p=word-6,h=get(p),n=h>>>8;need((h&255)===tag&&p+4+n*(tag===199?1:4)<=memory.buffer.byteLength,'OBJECT');
  return {p,n};
 };
 const vector=(word,n)=>{const o=object(word,250);if(n!==undefined)need(o.n===n,'ARITY');return o;};
 const string=(word,data=false)=>{const {p,n}=object(word,191);need(data||n<=4096,'STRING');let s='';
  for(let i=0;i<n;i++){const ch=get(p+4+i*4);need(ch<=0x10ffff&&(ch<0xd800||ch>0xdfff),'CHARACTER');s+=String.fromCodePoint(ch);}return s;};
 const token=(word,kind)=>{const value=tokens.get(fix(word));need(value?.kind===kind,'TOKEN');return value;};
 const capacity=()=>need(next<=maximumTokens,'TOKENS_EXHAUSTED');
 const publish=value=>{const id=next++;tokens.set(id,value);return id*4;};
 function number(word,type){
  if(type==='i32'||type==='i64'){
   let value;
   if(word%4===0)value=BigInt(fix(word));
   else {const {p,n}=object(word,7);need(n>0&&n<=2,'INTEGER');value=0n;
    for(let i=n-1;i>=0;i--)value=(value<<32n)|BigInt(get(p+4+i*4));value=BigInt.asIntN(n*32,value);}
   need(BigInt.asIntN(type==='i32'?32:64,value)===value,'INTEGER_RANGE');return type==='i32'?Number(value):value;
  }
  const {p,n}=object(word,type==='f32'?15:23);need(n===(type==='f32'?1:3),'FLOAT');
  return type==='f32'?view().getFloat32(p+4,true):view().getFloat64(p+8,true);
 }
 function encoded(value,type){
  if(type==='i32'||type==='i64'){
   const n=BigInt(value);if(n>=-536870912n&&n<=536870911n)return {word:Number(n)*4};
   const limbs=BigInt.asIntN(32,n)===n?1:2,bytes=new Uint8Array(limbs===1?8:16),v=new DataView(bytes.buffer);
   v.setUint32(0,limbs*256+7,true);for(let i=0;i<limbs;i++)v.setUint32(4+i*4,Number(BigInt.asUintN(32,n>>BigInt(i*32))),true);return {bytes};
  }
  const bytes=new Uint8Array(type==='f32'?8:16),v=new DataView(bytes.buffer);
  v.setUint32(0,type==='f32'?271:791,true);
  if(type==='f32')v.setFloat32(4,value,true);else v.setFloat64(8,value,true);return {bytes};
 }
 return args=>{
  if(busy) return -4;
  busy=true;
  try{
   need(Number.isInteger(args)&&args>=0&&args+12<=memory.buffer.byteLength,'ARGUMENTS');
   const op=fix(get(args+4)),payload=()=>get(args+8),request=n=>vector(payload(),n),field=i=>get(request().p+4+i*4);
   if(op===0){
    const name=string(payload());if(names.has(name)){const id=names.get(name);need(tokens.get(id).library.state==='ready','RETIRED');return id*4;}
    capacity();const library=libraries.open(name),id=publish({kind:'library',library,name});names.set(name,id/4);return id;
   }
   if(op===1){const t=token(payload(),'library');libraries.close(t.name);return 0;}
   if(op===2){
    request(4);const {library}=token(field(0),'library'),name=string(field(1));
    const entry=library.declaration.exports.find(e=>e.name===name);need(entry,'EXPORT');
    const a=vector(field(2),entry.params.length),rangeSlots=new Set((entry.ranges??[]).map(r=>r.pointer));
    const values=entry.params.map((type,i)=>{const word=get(a.p+4+i*4);if(!rangeSlots.has(i))return number(word,type);
     const t=token(word,'range');need(t.library===library,'AFFINITY');return t.range;});
    const result=library.call(name,values),items=(entry.results.length===0?[]:entry.results.length===1?[result]:result).map((v,i)=>encoded(v,entry.results[i]));
    const vectorSize=8*Math.ceil((4+4*items.length)/8),size=vectorSize+items.reduce((n,r)=>n+(r.bytes?.length??0),0);
    // This may collect. Only JS scalars/private byte snapshots cross it.
    owner.atSafepoint(o=>o.ensure(size));
    const base=get(tcr+48);let cursor=base+vectorSize;
    new Uint8Array(memory.buffer,base,size).fill(0);put(base,items.length*256+250);
    for(let i=0;i<items.length;i++){const r=items[i];let word=r.word;
     if(r.bytes){new Uint8Array(memory.buffer,cursor,r.bytes.length).set(r.bytes);word=cursor+6;cursor+=r.bytes.length;}
     put(base+4+i*4,word);
    }
    put(tcr+48,base+size);put(request(4).p+16,base+6);return 0;
   }
   if(op===3){request(2);const {library}=token(field(0),'library'),size=fix(field(1));capacity();
    return publish({kind:'buffer',library,handle:library.allocate(size)});}
   if(op===4){const t=token(payload(),'buffer');return t.library.release(t.handle)?4:0;}
   if(op===5){request(2);const t=token(field(0),'buffer'),offset=fix(field(1));capacity();
    return publish({kind:'range',library:t.library,range:t.library.range(t.handle,offset)});}
   if(op===6||op===7){request(3);const t=token(field(0),'buffer'),offset=fix(field(1)),{p,n}=object(field(2),199);
    const bytes=new Uint8Array(memory.buffer,p+4,n);
    if(op===6)t.library.write(t.handle,offset,bytes);else bytes.set(t.library.read(t.handle,offset,n));return 0;}
   if(op===8){request(2);const t=token(field(0),'buffer');t.library.finalize(t.handle,owner,field(1));return 0;}
   if(op===9){need(payload()===NIL,'PAYLOAD');return owner.drainFinalizers()*4;}
   if(op===10){request(4);const t=token(field(0),'buffer'),offset=fix(field(1));
    need(field(3)===0,'ENCODING');
    const bytes=new TextEncoder().encode(string(field(2),true));
    t.library.write(t.handle,offset,bytes);return bytes.length*4;}
   if(op===11){request(5);const t=token(field(0),'buffer'),offset=fix(field(1)),length=fix(field(2));
    need(field(3)===0,'ENCODING');
    need(length>=0&&length<=0xffffff,'STRING_SIZE');
    const bytes=t.library.read(t.handle,offset,length);let text;
    try{text=new TextDecoder('utf-8',{fatal:true,ignoreBOM:true}).decode(bytes);}
    catch(error){if(error instanceof TypeError)throw new Refusal('UTF8');throw error;}
    const chars=Array.from(text,c=>c.codePointAt(0)),size=8*Math.ceil((4+4*chars.length)/8);
    // Only decoded scalar values survive a possible move of the request.
    owner.atSafepoint(o=>o.ensure(size));
    const base=get(tcr+48);new Uint8Array(memory.buffer,base,size).fill(0);
    put(base,chars.length*256+191);chars.forEach((ch,i)=>put(base+4+i*4,ch));
    put(tcr+48,base+size);put(request(5).p+20,base+6);return 0;}
   need(false,'OPERATION');
  }catch(error){
   if(error instanceof Refusal||error.message==='collector-owner: finalizer object')return -4;
   const failure=foreignFailure(error);if(failure)return -4*({trap:2,exception:3,host:4}[failure.kind]);
   // Owner admission failures must never become catchable Lisp conditions.
   if(error instanceof AggregateError||/ASYNC_BOUNDARY/.test(String(error)))throw error;
   if(/^(foreign-module:|foreign-libraries:)/.test(error.message)||error.name==='NamespaceError')return -4;
   throw error;
  }finally{busy=false;}
 };
}
