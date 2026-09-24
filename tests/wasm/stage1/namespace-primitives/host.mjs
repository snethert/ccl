import {views,pair,ERRNO,COMPLETE,CAPACITY} from './protocol.mjs';

// A session belongs to one Worker lifetime. The owner is given no heap pointer.
export function serviceRequest(memory, session, lifetime, generation) {
  const {words:w,pair:p,payload}=views(memory);
  if (Atomics.load(p,0)!==pair(generation,0) || Atomics.load(w,1)!==lifetime ||
      Atomics.load(w,6)!==1) return false;
  const op=w[0],a=w[9],b=w[10],c=w[11],length=w[8];
  if (length<0 || length>4096) throw new Error('request path extent');
  let result=0,bytes=new Uint8Array();
  try {
    const path=()=>new TextDecoder('utf-8',{fatal:true}).decode(payload.slice(0,length));
    switch(op) {
      case 0: result=session.open(path(),b===0?'read':'write');break;
      case 1: bytes=session.read(a,Math.min(c,CAPACITY));result=bytes.length;break;
      case 2: {
        if(![0,1,2].includes(c)){result=-22;break;}
        const position=b+(c===0?0:c===1?session.seek(a,0,'cur'):session.fstat(a).size);
        result=position<0||position>536870911?-22:session.seek(a,position,'set');break;
      }
      case 3: session.close(a);break;
      case 4: result=session.fstat(a).size;break;
      case 5: bytes=new TextEncoder().encode(session.realpath(path()));break;
      case 6: result=session.stat(path()).kind==='file'?1:2;break;
      case 7: result=-30;break;
      default: throw new Error('request opcode');
    }
  } catch(e) {
    if (!Object.hasOwn(ERRNO,e.code)) throw e;
    result=-ERRNO[e.code];bytes=new Uint8Array();
  }
  if (bytes.length>CAPACITY || !Number.isInteger(result) || result< -536870912 || result>536870911)
    throw new Error('request result range');
  // Recheck before writing, then publish outcome and all result bytes before
  // the atomic generation/wakeup transition. Stale completions write nothing.
  if (Atomics.load(p,0)!==pair(generation,0) || Atomics.load(w,6)!==1) return false;
  payload.fill(0);payload.set(bytes);w[5]=result;w[8]=bytes.length;w[4]=COMPLETE;
  if (Atomics.compareExchange(p,0,pair(generation,0),pair(generation,1))!==pair(generation,0))
    throw new Error('request completion race');
  Atomics.notify(w,2);return true;
}
