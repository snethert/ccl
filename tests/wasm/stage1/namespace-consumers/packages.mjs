import fs from 'node:fs';
import assert from 'node:assert/strict';

// Link existing compiler-owned symbols into the admitted, pinned package
// representation. This creates metadata from names, not native heap objects.
export async function packages({dir,memory,gen,owners,get,put,addRoot}) {
 const N=77825,T=77838,start=22*1048576,end=24*1048576,config=end,result=end+96;
 let next=start;
 const alloc=n=>{n=(n+7)&~7;const p=next;next+=n;assert(next<=end);new Uint8Array(memory.buffer,p,n).fill(0);return p;};
 const vector=(words,tag=250)=>{const p=alloc(4+4*words.length);put(p,(words.length<<8)|tag);words.forEach((v,i)=>put(p+4+4*i,v));return p+6;};
 const string=s=>vector(Array.from(s,c=>c.codePointAt(0)),191);
 const cons=(a,b)=>{const p=alloc(8);put(p,b);put(p+4,a);return p+1;};
 const hash=s=>Array.from(s).reduce((h,c)=>Math.imul(h^c.codePointAt(0),16777619)>>>0,2166136261);
 const groups=Map.groupBy(owners.filter(o=>o.package),o=>o.package),pkgs=new Map(),descriptors=new Map();
 for(const [name,rows] of groups) {
  let capacity=4;while(capacity<=rows.length)capacity*=2;
  assert(capacity<=8192,name+' table capacity');
  const table=()=>cons(vector(Array(capacity).fill(0)),cons(0,capacity*4));
  const p=alloc(40),internal=table(),external=table();
  put(p,2146);[internal,external,N,N,cons(string(name),N),N,N,N].forEach((v,i)=>put(p+4+4*i,v));
  pkgs.set(name,p+6);descriptors.set(name,{internal,external,capacity});
 }
 for(const row of owners)if(row.package) {
  const word=gen.ownerWords.get(row.id),pkg=pkgs.get(row.package),d=descriptors.get(row.package);
  put(word+10,pkg);
  if(row.package==='KEYWORD'){put(word+2,word);put(word+14,72);}
  const table=['KEYWORD','COMMON-LISP'].includes(row.package)?d.external:d.internal;
  const buckets=get(table+3);let i=hash(row.name)&(d.capacity-1);
  while(get(buckets-2+4*i))i=(i+1)&(d.capacity-1);
  put(buckets-2+4*i,word);const count=get(table-1)+3;put(count,get(count)+4);
 }
 // Canonical symbols have their own reserved storage.
 put(77880,pkgs.get('COMMON-LISP'));put(77848,pkgs.get('COMMON-LISP'));
 for(const [name,word] of [['NIL',77870],['T',T]]) {
  const d=descriptors.get('COMMON-LISP'),table=d.external,buckets=get(table+3);
  let i=hash(name)&(d.capacity-1);while(get(buckets-2+4*i))i=(i+1)&(d.capacity-1);
  put(buckets-2+4*i,word);const count=get(table-1)+3;put(count,get(count)+4);
 }
 const roots=vector([...pkgs.values()]);
 const status=name=>gen.ownerWords.get(owners.find(o=>o.package==='KEYWORD'&&o.name===name).id);
 new Uint8Array(memory.buffer,config,112).fill(0);
 [0x53594d31,start,end,next,roots,1,0,N,T,pkgs.get('KEYWORD'),status('INTERNAL'),status('EXTERNAL'),status('INHERITED'),
  25*1048576,1048576,0,0,N,7000000,gen.ownerEnd].forEach((v,i)=>put(config+4*i,v));
 let registry=N;
 for(const [name,pkg] of pkgs)registry=cons(cons(string(name),pkg),registry);
 put(config+12,next);
 const pad=()=>{const p=get(config+12),free=end-p;if(free)put(p,((free-4)<<8)|199);};
 pad();
 const registrySymbol=owners.find(o=>o.package==='CCL'&&o.name==='*WASM-PACKAGE-LITERALS*');
 put(gen.ownerWords.get(registrySymbol.id)+2,registry);
 const service=(await WebAssembly.instantiate(fs.readFileSync(dir+'/symbols.wasm'),{env:{memory}})).instance.exports;
 assert.equal(service.symbols_admit(config,result),0,'linked package admission');
 const admissionControls=[];
 const before=Uint8Array.from(new Uint8Array(memory.buffer,start,end-start));
 const lo=get(config+72),hi=get(config+76),scratch=get(config+52);
 for(const [name,a,b] of [
  ['alignment',lo+1,hi],['ordered range',hi+8,lo],['symbol stride',lo,hi+1],
  ['backed range',lo,memory.buffer.byteLength+32],['package overlap',start,start+32],
  ['descriptor overlap',config,config+32],['scratch overlap',scratch,scratch+32],
  ['result overlap',result,result+32],['zero lower bound',0,hi],
  ['relative symbol alignment',lo-8,hi-8],['absent linked range',0,0]
 ]) {
  put(config+72,a);put(config+76,b);
  try {
   assert.notEqual(service.symbols_admit(config,result),0,'linked symbol refusal: '+name);
   assert.deepEqual(new Uint8Array(memory.buffer,start,end-start),before,'package publication unchanged: '+name);
   admissionControls.push(name);
  } finally {put(config+72,lo);put(config+76,hi);}
 }
 const adapter=await WebAssembly.compile(fs.readFileSync(dir+'/symbol-adapter.wasm'));
 const calls=[0,0];
 for(const [op,name] of ['%WASM-SYMBOL-FIND','%WASM-SYMBOL-INTERN'].entries()) {
  const id=5+op;
  const run=(...args)=>{
   calls[op]++;const code=service.symbols_run(...args);
   if(!code&&get(result+12)){
    const word=get(result);for(const offset of [-2,2,6,10,18])addRoot(word+offset);
    pad();
   }
   return code;
  };
  const instance=new WebAssembly.Instance(adapter,{env:gen.env,symbols_runtime:{run,config,operation:op,result}});
  [id,4,17,23].forEach((v,i)=>put(4096+8+16*id+4*i,v));
  gen.env.table.set(id,instance.exports.entry);gen.env.tail_table.set(id,instance.exports.tail_entry);
  const p=1170040+32*op;[1578,id*4,N,4,N,N,N,0].forEach((v,i)=>put(p+4*i,v));
  const owner=owners.find(o=>o.package==='CCL'&&o.name===name);assert(owner,name);
  put(gen.ownerWords.get(owner.id)+6,p+6);
 }
 return {calls,packages:pkgs.size,symbols:owners.filter(o=>o.package).length,admissionControls};
}
