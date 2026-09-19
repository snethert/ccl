import {LazyLoader,validate,sha,PROFILE} from './loader.mjs';
import {entryRanges} from './ranges.mjs';
const need=(x,s)=>{if(!x)throw Error(s);},same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const key=pair=>{need(Array.isArray(pair)&&pair.length===2&&pair.every(x=>typeof x==='string'&&x.length),'BINDING_NAME');return JSON.stringify(pair);};
const uint=x=>Number.isInteger(x)&&x>=0&&x<=0xffffffff;
const NIL=77825,T=77838;
// Single Worker, synchronous owner boundary. Caller excludes execution/collection
// for this transaction. No callbacks or await occur between validation/publication.
export class BindingInstaller {
 #o;#generation=0;#head=null;#modules=new Map();#slots=new Set();#loaders=[];#symbols=new Map();
 constructor(o){
  this.#o=o;need(o.table!==o.tail_table,'DISTINCT_TABLES');need(Number.isInteger(o.reserved)&&o.reserved>0&&o.reserved<o.table.length,'RESERVED_PREFIX');
  need(o.registry%8===0&&o.registry>=0&&o.registry+8<=o.memory.buffer.byteLength,'REGISTRY_EXTENT');
  const v=new DataView(o.memory.buffer);need(v.getUint32(o.registry,true)<=o.table.length&&v.getUint32(o.registry,true)<=o.tail_table.length&&v.getUint32(o.registry+4,true)===1,'REGISTRY_HEADER');
  const addresses=new Set();for(const s of o.symbols){const k=key(s.name);need(!this.#symbols.has(k)&&uint(s.address)&&s.address%8===6&&!addresses.has(s.address),'SYMBOL_IDENTITY');this.#symbols.set(k,s.address);addresses.add(s.address);}
 }
 state(){return {generation:this.#generation,head:this.#head,modules:[...this.#modules.keys()]};}
 install(input,expectedBindings,catalog,readBytes,imports){
  // Snapshot owner data before any writes, including the code bytes.
  const m=structuredClone(input),rows=structuredClone(catalog),o=this.#o,v=new DataView(o.memory.buffer),get=p=>v.getUint32(p,true),put=(p,x)=>v.setUint32(p,x,true);
  const span=(p,n)=>need(uint(p)&&uint(n)&&p+n<=v.byteLength,'OBJECT_EXTENT');
  const object=(node,header,size)=>{need(uint(node)&&node%8===6,'OBJECT_TAG');span(node-6,size);need(get(node-6)===header,'OBJECT_HEADER');return node-6;};
  const vector=(node,count)=>{const p=object(node,count*256+250,Math.ceil((4+count*4)/8)*8);return Array.from({length:count},(_,i)=>get(p+4+i*4));};
  const ownerArity=f=>{const a=vector(get(f+16),7);need(a[0]===4&&a[1]%4===0&&a[2]%4===0,'ARITY_SCHEMA');const flags=a.slice(3,6).map(x=>{need(x===NIL||x===T,'ARITY_FLAGS');return x===T;});
   const q=a[6];need(uint(q)&&q%8===6,'KEY_VECTOR');span(q-6,4);const h=get(q-6);need(h%256===250,'KEY_VECTOR');const keys=vector(q,Math.floor(h/256)).map(x=>{const entry=o.keywords.find(k=>k.address===x);need(entry,'KEY_IDENTITY');return entry.name;});return [a[1]/4,a[2]/4,...flags,keys];};
  need(m.version===1&&m.generation===this.#generation+1&&m.previous===this.#head&&m.phase===(this.#generation?'runtime':'boot'),'MANIFEST_CHAIN');
  need(Array.isArray(m.modules)&&Array.isArray(m.functions)&&Array.isArray(m.bindings),'MANIFEST_SHAPE');
  const expected=expectedBindings.map(key);need(new Set(expected).size===expected.length,'EXPECTED_BINDINGS');
  const names=m.bindings.map(b=>key(b.name));need(names.length===expected.length&&new Set(names).size===names.length&&same([...names].sort(),[...expected].sort()),'COMPLETE_BINDINGS');
  const cats=new Map();for(const r of rows){need(!cats.has(r.name),'CATALOG_DUPLICATE');cats.set(r.name,r);}
  need(m.modules.length===rows.length,'COMPLETE_MODULES');
  const staged=new Map(),slots=new Set(),bytes=new Map();
  for(const r of m.modules){const c=cats.get(r.name);need(c&&!staged.has(r.name)&&!this.#modules.has(r.name),'MODULE_IDENTITY');
   need(same(r,c),'MODULE_MANIFEST');need(r.profile===PROFILE,'PROFILE');
   need(Number.isInteger(r.slot)&&r.slot>=o.reserved&&r.slot<get(o.registry)&&r.slot<o.table.length&&r.slot<o.tail_table.length&&!this.#slots.has(r.slot)&&!slots.has(r.slot),'SLOT_OWNER');
   need(r.code===r.slot&&r.version===4&&r.signature===17&&r.role===23,'CODE_ROLE');
   span(o.registry+8+16*r.code,16);need([0,4,8,12].every(i=>get(o.registry+8+16*r.code+i)===0)&&o.table.get(r.slot)===null&&o.tail_table.get(r.slot)===null,'SLOT_EMPTY');
   const b=Buffer.from(readBytes(r.name));validate(b,r);need(same(r.ranges,entryRanges(b)),'ENTRY_RANGES');
   need(Array.isArray(r.arity)&&r.arity.length===6&&Number.isInteger(r.captures)&&r.captures>=0,'CALLABLE_SHAPE');
   slots.add(r.slot);staged.set(r.name,r);bytes.set(r.name,b);
  }
  const functions=new Map();for(const f of m.functions){need(!functions.has(f.object),'FUNCTION_DUPLICATE');const c=staged.get(f.module)??this.#modules.get(f.module);need(c,'FUNCTION_CODE');
   const raw=object(f.object,1578,32);need(get(raw+4)===c.code*4&&get(raw+12)===c.version,'FUNCTION_IDENTITY');
   const pool=get(raw+24);need(uint(pool)&&pool%8===6,'POOL_SHAPE');span(pool-6,4);const h=get(pool-6);need(h%256===250&&Math.floor(h/256)>=2,'POOL_SHAPE');const pv=vector(pool,Math.floor(h/256));need(get(raw+16)===pv[0]&&get(raw+20)===pv[1],'METADATA_IDENTITY');
   need(same(ownerArity(raw),c.arity),'ARITY_IDENTITY');const debug=vector(get(raw+20),3);need(debug[0]===4,'DEBUG_SCHEMA');vector(debug[2],c.captures);
   if(c.captures){for(const cell of vector(get(raw+8),c.captures)){need(uint(cell)&&cell!==NIL&&cell%8===1,'CAPTURE_CELL');span(cell-1,8);}}
   else need(get(raw+8)===NIL,'EMPTY_ENVIRONMENT');
   functions.set(f.object,f);
  }
  const bindings=[];for(const b of m.bindings){const address=this.#symbols.get(key(b.name));need(address!==undefined,'UNREGISTERED_SYMBOL');const raw=object(address,1850,32);need(functions.has(b.object),'BINDING_FUNCTION');need(uint(b.previous)&&get(raw+12)===b.previous,'BINDING_PREVIOUS');bindings.push({where:raw+12,value:b.object});}
  const journal=[];const write=(where,value)=>{journal.push([where,get(where)]);put(where,value);};
  let loader;
  try{
   // All fallible compilation and validation precedes the final symbol writes.
   for(const r of staged.values()){const p=o.registry+8+16*r.code;[r.slot,r.version,r.signature,r.role].forEach((x,i)=>write(p+i*4,x));}
   loader=new LazyLoader({...o,code_registry:o.registry,catalog:[...staged.values()],readBytes:n=>bytes.get(n)});
   for(const r of staged.values())loader.defer(r.name,imports);
   for(const r of staged.values())loader.install(r.slot);
   for(const b of bindings)write(b.where,b.value);
  }catch(e){for(let i=journal.length-1;i>=0;i--)put(...journal[i]);for(const slot of slots){o.table.set(slot,null);o.tail_table.set(slot,null);}throw e;}
  // Keep prior module instances and code rows alive for saved function objects.
  for(const [n,c]of staged)this.#modules.set(n,c);for(const s of slots)this.#slots.add(s);this.#loaders.push(loader);this.#generation=m.generation;this.#head=sha(Buffer.from(JSON.stringify(m)));
  return {...this.state(),installed:loader.events.filter(e=>e.event==='INSTALLED'),bindings:bindings.length};
 }
}
