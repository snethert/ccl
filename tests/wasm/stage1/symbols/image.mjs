// Owner materialization for the sealed LL09 package slice. All pointer fields
// are recorded explicitly: relocation never guesses from tag-looking payload.
export const NIL=77825,T=77838,NILSYM=77864,CONFIG=1200000,RESULT=2048000;
export const hashName=s=>Array.from(s).reduce((h,c)=>Math.imul(h^c.codePointAt(0),16777619)>>>0,2166136261);
export function image(memory,base,{capacity=128,version=1,initialKeywords=[]}={}){
 if(![4194304,8388608,2147483648].includes(base))throw Error('unsupported image base');
 const end=base+65536;if(end>memory.buffer.byteLength)throw Error('unbacked image');
 const d=new DataView(memory.buffer),get=p=>d.getUint32(p,true),put=(p,v)=>d.setUint32(p,v,true),fields=new Set();let next=base;
 const alloc=n=>{n=(n+7)&~7;const p=next;next+=n;if(next>end)throw Error('image capacity');new Uint8Array(memory.buffer,p,n).fill(0);return p;};
 const ptr=(p,v)=>{fields.add(p);put(p,v);};
 const str=s=>{const a=Array.from(s,c=>c.codePointAt(0)),p=alloc(4+4*a.length);put(p,a.length*256+191);a.forEach((x,i)=>put(p+4+4*i,x));return p+6;};
 const vec=n=>{const p=alloc(4+4*n);put(p,n*256+250);for(let i=0;i<n;i++)ptr(p+4+4*i,0);return p+6;};
 const cons=(a,b)=>{const p=alloc(8);ptr(p,b);ptr(p+4,a);return p+1;};
 const table=()=>cons(vec(capacity),cons(0,capacity*4));
 const packages={};for(const name of ['CL','KEYWORD','A','B','USER']){const p=alloc(40);put(p,2146);for(let i=1;i<=8;i++)ptr(p+4*i,NIL);ptr(p+4,table());ptr(p+8,table());ptr(p+20,cons(str(name),NIL));packages[name]=p+6;}
 ptr(packages.USER+6,cons(packages.CL,NIL));
 function insert(sym,pkg,external){const p=sym===NIL?NILSYM:sym-6,t=get(pkg+(external?2:-2)),v=get(t+3),name=decode(get(p+4));let at=(version===1?hashName(name):hashName(name)^0x9e3779b9)&(capacity-1);while(get(v-2+4*at))at=(at+1)&(capacity-1);ptr(v-2+4*at,sym===NIL?NILSYM+6:sym);const count=get(t-1)+3;put(count,get(count)+4);}
 function symbol(name,pkg,external=false,fixed=null){const p=fixed??alloc(32),s=p===NILSYM?NIL:p+6;put(p,1850);ptr(p+4,str(name));ptr(p+8,pkg===packages.KEYWORD?s:51);ptr(p+12,NIL);ptr(p+16,pkg);put(p+20,pkg===packages.KEYWORD?72:0);ptr(p+24,NIL);put(p+28,0);insert(s,pkg,external);return s;}
 function decode(p){const n=get(p-6)>>>8;let s='';for(let i=0;i<n;i++)s+=String.fromCodePoint(get(p-2+4*i));return s;}
 symbol('NIL',packages.CL,true,NILSYM);symbol('T',packages.CL,true,77832);ptr(NILSYM+8,NIL);ptr(77840,T);put(NILSYM+20,72);put(77852,72);ptr(77824,NIL);ptr(77828,NIL);
 const statuses=['INTERNAL','EXTERNAL','INHERITED'].map(s=>symbol(s,packages.KEYWORD,true));
 for(const name of initialKeywords)if(!['INTERNAL','EXTERNAL','INHERITED'].includes(name))symbol(name,packages.KEYWORD,true);
 symbol('EXPORTED',packages.CL,true);symbol('HIDDEN',packages.CL);
 const roots=vec(5);Object.values(packages).forEach((p,i)=>ptr(roots-2+4*i,p));
 new Uint8Array(memory.buffer,CONFIG,80).fill(0);
 [0x53594d31,base,end,next,roots,version,0,NIL,T,packages.KEYWORD,...statuses,1900000,65536,0,0,NIL,0,0].forEach((v,i)=>put(CONFIG+4*i,v));
 let queryNext=1600000;
 function query(s){const a=Array.from(s,c=>c.codePointAt(0)),p=queryNext;queryNext+=(4+4*a.length+7)&~7;if(queryNext>1850000)throw Error('query capacity');put(p,a.length*256+191);a.forEach((x,i)=>put(p+4+4*i,x));return p+6;}
 function snapshot(){
  // Include symbols and strings added by INTERN/MAKE-SYMBOL after admission.
  const limit=get(CONFIG+12);let p=next;
  while(p<limit){const h=get(p),n=h>>>8;if((h&255)===191)p+=(4+4*n+7)&~7;else if(h===1850){for(const k of [4,8,12,16,24])fields.add(p+k);p+=32;}else throw Error('snapshot shape');}if(p!==limit)throw Error('snapshot extent');
  return {base,next:limit,bytes:Uint8Array.from(new Uint8Array(memory.buffer,base,limit-base)),fixed:Uint8Array.from(new Uint8Array(memory.buffer,77824,72)),fields:[...fields],config:Array.from({length:20},(_,i)=>get(CONFIG+i*4)),packages:{...packages},statuses:[...statuses]};
 }
 function restore(s,newBase){
  if(![4194304,8388608,2147483648].includes(newBase)||newBase+65536>memory.buffer.byteLength)throw Error('unsupported image base');
  const move=v=>[1,6].includes(v&7)&&v>=s.base&&v<s.next?v-s.base+newBase:v;
  new Uint8Array(memory.buffer,newBase,s.bytes.length).set(s.bytes);new Uint8Array(memory.buffer,77824,72).set(s.fixed);
  for(const old of s.fields){const p=old>=s.base?old-s.base+newBase:old;put(p,move(get(p)));}
  s.config.forEach((v,i)=>put(CONFIG+4*i,v));put(CONFIG+4,newBase);put(CONFIG+8,newBase+65536);put(CONFIG+12,newBase+s.bytes.length);for(const i of [16,36,40,44,48])put(CONFIG+i,move(get(CONFIG+i)));put(CONFIG+24,0);
  const movedFields=s.fields.map(p=>p>=s.base?p-s.base+newBase:p);fields.clear();for(const p of movedFields)fields.add(p);
  Object.assign(packages,Object.fromEntries(Object.entries(s.packages).map(([k,v])=>[k,move(v)])));statuses.splice(0,3,...s.statuses.map(move));base=newBase;next=newBase+s.bytes.length;
  return {move,packages:{...packages},statuses:[...statuses]};
 }
 return {get,put,packages,statuses,query,decode,snapshot,restore};
}
