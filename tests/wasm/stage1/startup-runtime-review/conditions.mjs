// The accepted sealed registry shape, in a compact pinned image. This fixture
// needs SIMPLE-ERROR; other rows retain their accepted masks and slot counts.
export function installConditions(put,N){
 let top=810000;
 const alloc=bytes=>{const p=top;top+=Math.ceil(bytes/8)*8;for(let q=p;q<top;q+=4)put(q,0);return p;};
 const vector=(xs,tag=250)=>{const p=alloc(4+4*xs.length);put(p,256*xs.length+tag);xs.forEach((x,i)=>put(p+4+4*i,x));return p+6;};
 const symbol=()=>{const p=alloc(32);[1850,N,N,N,N,0,N,0].forEach((x,i)=>put(p+4*i,x));return p+6;};
 const text='Collector timing is unavailable.';const raw=alloc(4+4*text.length);put(raw,256*text.length+191);Array.from(text).forEach((x,i)=>put(raw+4+4*i,x.codePointAt(0)));const message=raw+6;
 const counts=[0,2,2,3,0,2,0,3,2,2,0,0],masks=[1,9,31,39,71,393,519,527,1031,2055,4099,7],wrappers=[];
 const rows=counts.map((count,i)=>{const name=symbol(),wrapperName=symbol(),slots=vector(Array.from({length:count},symbol)),defaults=vector(Array(count).fill(N));
  const p=alloc(16);put(p,882);put(p+4,0);put(p+8,N);put(p+12,vector([p+6,name,N],106));
  const wrapper=vector([wrapperName,4*i,p+6,slots,N,N,N,N,N,N,N,4*i,masks[i]*4]);wrappers.push(wrapper);return vector([wrapper,4*masks[i],defaults]);});
 const registry=vector(rows),p=alloc(16);put(p,882);put(p+4,0);put(p+8,wrappers[2]);put(p+12,vector([p+6,message,N],106));
 return {registry,condition:p+6,message,end:top};
}
