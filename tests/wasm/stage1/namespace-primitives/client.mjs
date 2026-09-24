import {REQUEST,SIZE,CAPACITY,views,pair,COMPLETE} from './protocol.mjs';
const N=77825;

export function fileClient({memory,tcr,post,collect,allocate,pinned=[],refuse=reason=>{throw new Error('file-admission: '+reason);},lifetime=1}) {
  let generation=0,active=false;
  const view=()=>new DataView(memory.buffer), get=p=>view().getUint32(p,true);
  const put=(p,v)=>view().setUint32(p,v,true);
  const fail=refuse;
  const span=(p,n)=>{if (!Number.isSafeInteger(p)||!Number.isSafeInteger(n)||p<0||n<0||p+n>memory.buffer.byteLength) fail('backed span');};
  const integer=v=>{if(v&3)fail('fixnum');return v>>2;};
  function object(v,kind) {
    if ((v&7)!==6 || v<6)fail('object tag');
    const base=v-6;span(base,4);
    const h=get(base),count=h>>>8;
    const tag=h&255;
    if (!(Array.isArray(kind)?kind.includes(tag):tag===kind))fail('object kind');
    const width=({191:4,199:1,207:1,215:2,223:2,167:4,175:4,183:4})[tag];
    const extent=4+count*width;
    span(base,extent);
    const heap=base>=get(tcr+56) && base+extent<=get(tcr+48);
    if(!heap && !(kind===191 && pinned.some(r=>base>=r.start&&base+extent<=r.end)))fail('object ownership');
    return {base,count,bytes:count*width};
  }
  function string(v) {
    const {base,count}=object(v,191);
    if(count>4096)fail('path length');
    let result='';
    for(let i=0;i<count;i++) {
      const code=get(base+4+4*i);
      if(code>0x10ffff || (code>=0xd800&&code<=0xdfff))fail('scalar');
      result+=String.fromCodePoint(code);
    }
    const bytes=new TextEncoder().encode(result);
    if(bytes.length>4096)fail('path bytes');
    return bytes;
  }
  return function run(args) {
    if(active)fail('nested request');
    span(args,16);
    if(args%8 || args<get(tcr+68) || args+16>get(tcr+72))fail('argument frame');
    if (get(tcr+64)!==args || get(tcr+32)!==2 || get(tcr+152)!==0 ||
        get(tcr+8)!==lifetime || get(tcr+12)!==0)fail('thread state');
    const op=integer(get(args)),av=get(args+4),bv=get(args+8),cv=get(args+12);
    if(op<0||op>7)fail('operation');
    let a=0,b=0,c=0,path=new Uint8Array();
    // Complete argument validation precedes any host action or TCR change.
    if([0,5,6].includes(op))path=string(av);else a=integer(av);
    if(op===0){b=integer(bv);c=integer(cv);}
    if(op===1 || op===7) {
      const buffer=object(bv,[199,207,215,223,167,175,183]);c=integer(cv);
      if(c<0 || c>buffer.bytes)fail('buffer count');
    }
    if(op===2){b=integer(bv);c=integer(cv);if(c<0||c>2)fail('seek origin');}
    if(generation===0xffffffff)fail('generation exhausted');
    span(REQUEST,SIZE);
    const saved=[144,152,156,160,164].map(o=>get(tcr+o));
    const {words:w,pair:p,payload}=views(memory);
    active=true;generation++;
    w.fill(0);payload.fill(0);payload.set(path);
    w[0]=op;w[1]=lifetime;w[6]=1;w[8]=path.length;w[9]=a;w[10]=b;w[11]=c;
    Atomics.store(p,0,pair(generation,0));
    put(tcr+144,REQUEST);put(tcr+152,REQUEST);put(tcr+156,REQUEST);put(tcr+160,1);put(tcr+164,lifetime);
    Atomics.store(new Int32Array(memory.buffer), (tcr+32)/4,3);
    try {
      post({generation,lifetime});
      while(Atomics.load(p,0)===pair(generation,0)) {
        if(Atomics.wait(w,2,0,30000)==='timed-out')fail('owner timeout');
      }
      if(Atomics.load(p,0)!==pair(generation,1)||w[4]!==COMPLETE||w[6]!==1)fail('completion identity');
      const result=w[5],length=w[8];
      if(length<0||length>CAPACITY)fail('result extent');
      if(result< -536870912||result>536870911)fail('result range');
      if(op===1 && (result<0 ? length!==0 : result!==length || length>c))fail('read publication');
      const bytes=payload.slice(0,length);
      w[6]=0;w[9]=0; // consumed; no heap pointer was stored here
      Atomics.store(new Int32Array(memory.buffer),(tcr+32)/4,2);
      // The single Lisp Worker resumes at a legal owner safepoint. Generated
      // argument roots stay live; the buffer is reloaded after movement.
      collect();
      if(op===1 && result>=0) {
        const buffer=object(get(args+8),[199,207,215,223,167,175,183]);
        if(length>buffer.bytes)fail('reloaded buffer');
        new Uint8Array(memory.buffer,buffer.base+4,length).set(bytes);
      }
      if(op===5) {
        if(result<0)return N;
        const text=new TextDecoder('utf-8',{fatal:true}).decode(bytes);
        const codes=Array.from(text,ch=>ch.codePointAt(0));
        const base=allocate((4+4*codes.length+7)&~7);
        put(base,(codes.length<<8)|191);
        codes.forEach((code,i)=>put(base+4+4*i,code));
        return (base+6)|0;
      }
      return (result*4)|0;
    } finally {
      // A failed owner request is terminal for this leaf invocation. It never
      // publishes a partial result or writes a buffer before completion checks.
      w[6]=0;[144,152,156,160,164].forEach((o,i)=>put(tcr+o,saved[i]));
      Atomics.store(new Int32Array(memory.buffer),(tcr+32)/4,2);active=false;
    }
  };
}
