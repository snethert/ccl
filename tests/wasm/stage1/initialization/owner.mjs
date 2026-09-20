// Trusted layout, single process bootstrap followed by independently claimed Workers.
// No callback or module instantiation until all metadata and binaries pass preflight.
import {sha256} from './sha256.mjs';
import {snapshotBytes,hex} from './bytes.mjs';
import {validate} from './loader.mjs';
const need=(v,s)=>{if(!v)throw Error(s);};
export class InitializationOwner {
 #memory; #layout; #regions; #modules; #digest; #control;
 constructor({memory,layout,layoutDigest,modules}){
  need(memory instanceof WebAssembly.Memory&&memory.buffer instanceof SharedArrayBuffer,'SHARED_MEMORY');
  const l=structuredClone(layout);need(sha256(JSON.stringify(l))===layoutDigest,'LAYOUT_DIGEST');
  need(l.version===1&&l.workers.length>0&&l.workers.every((w,i)=>w===i),'WORKER_IDS');
  const names=new Set(),regions=l.regions.map(r=>({...r})).sort((a,b)=>a.start-b.start);
  for(let i=0;i<regions.length;i++){
   const r=regions[i];need(!names.has(r.name),'REGION_NAME');names.add(r.name);
   need(Number.isSafeInteger(r.start)&&Number.isSafeInteger(r.size)&&r.start>=0&&r.size>0&&r.start+r.size<=memory.buffer.byteLength,'REGION_EXTENT');
   need(Number.isSafeInteger(r.alignment)&&r.alignment>=4&&r.alignment<=65536&&(r.alignment&(r.alignment-1))===0&&r.start%r.alignment===0&&r.size%4===0,'REGION_ALIGNMENT');
   need(Number.isSafeInteger(r.minimum)&&r.minimum>0&&r.size>=r.minimum,'REGION_MINIMUM');
   need(r.owner==='process'||l.workers.includes(r.owner),'REGION_OWNER');
   if(i)need(regions[i-1].start+regions[i-1].size<=r.start,'REGION_OVERLAP');
  }
  const byName=new Map(regions.map(r=>[r.name,r])),control=byName.get('control');
  need(control?.owner==='process'&&control.size>=64+4*l.workers.length&&control.alignment>=8,'CONTROL_REGION');
  for(const id of l.workers){const t=byName.get('tcr-'+id);need(t?.owner===id&&t.size>=256&&t.alignment>=16,'TCR_REGION');}
  for(const row of l.writes){
   const r=byName.get(row.region);need(r&&r.name!=='control'&&row.owner===r.owner,'WRITE_AUTHORITY');
   need(Number.isSafeInteger(row.offset)&&row.offset>=0&&row.offset%4===0&&Array.isArray(row.words)&&row.offset+4*row.words.length<=r.size,'WRITE_EXTENT');
   need(row.words.every(x=>Number.isInteger(x)&&x>=0&&x<=0xffffffff),'WRITE_VALUE');
  }
  // Validate the actual raw pointers that generated entries will consume, not
  // just the range labels. This fixed bootstrap TCR profile binds schema v2.
  for(const id of l.workers){
   const r=n=>{const x=byName.get(n+'-'+id);need(x?.owner===id,'WORKER_REGIONS');return x;};
   const t=r('tcr'),v=r('vsp'),s=r('tsp'),c=r('csp'),h=r('heap'),b=r('tlb');r('cell');r('staging');
   need(v.size>=8192&&s.size>=4096&&c.size>=256&&h.size>=4096&&b.size>=256,'WORKER_MINIMUM');
   const words=new Uint32Array(t.size/4);
   for(const row of l.writes)if(row.region===t.name)words.set(row.words,row.offset/4);
   const expected={0:id,4:id,8:1,20:t.start,48:h.start,52:h.start+h.size,56:h.start,64:v.start+512,68:v.start+16,72:v.start+v.size,76:s.start,80:s.start,84:s.start+s.size,88:c.start,92:c.start,96:c.start+c.size,104:b.start,108:b.size/4,120:v.start+1024,124:v.start+1040,128:v.start+8,188:77825,200:7};
   for(let offset=0;offset<256;offset+=4)need(words[offset/4]===(expected[offset]??0),'TCR_INITIAL_STATE');
  }
  need(Number.isInteger(l.tableCapacity)&&l.tableCapacity>1&&Array.isArray(l.reservedSlots)&&l.reservedSlots.includes(0),'TABLE_LAYOUT');
  need(modules.length===l.modules.length,'MODULE_SET');const slots=new Set();
  this.#modules=modules.map((m,i)=>{
   need(m.name===l.modules[i].name&&m.record.sha256===l.modules[i].sha256,'MODULE_IDENTITY');
   const r=m.record;need(Number.isInteger(r.slot)&&r.slot>0&&r.slot<l.tableCapacity&&!slots.has(r.slot)&&!l.reservedSlots.includes(r.slot),'TABLE_SLOT');slots.add(r.slot);
   need(r.code===r.slot&&r.version===4&&r.signature===17&&r.role===23,'CODE_ROLE');
   const bytes=snapshotBytes(m.bytes);validate(bytes,m.record);return {name:m.name,bytes,record:structuredClone(m.record)};
  });
  this.#memory=memory;this.#layout=l;this.#regions=regions;this.#control=control;
  this.#digest=Uint8Array.from(layoutDigest.match(/../g),s=>parseInt(s,16));
 }
 // Expose validated copies only; the lazy loader rechecks each module on installation.
 modules(){return this.#modules.map(m=>({...m,bytes:snapshotBytes(m.bytes),record:structuredClone(m.record)}));}
 #state(){return new Int32Array(this.#memory.buffer,this.#control.start,this.#control.size/4);}
 #identity(){need(hex(new Uint8Array(this.#memory.buffer,this.#control.start+8,32))===hex(this.#digest),'PROCESS_IDENTITY');}
 #initialize(owner){
  for(const r of this.#regions)if(r.owner===owner&&r.name!=='control')new Uint8Array(this.#memory.buffer,r.start,r.size).fill(0);
  const v=new DataView(this.#memory.buffer);
  for(const w of this.#layout.writes)if(w.owner===owner){const r=this.#regions.find(r=>r.name===w.region);w.words.forEach((x,i)=>v.setUint32(r.start+w.offset+4*i,x,true));}
 }
 process(id,run){
  need(id===0,'BOOTSTRAP_WORKER');const state=this.#state();
  if(Atomics.load(state,0)===2){this.#identity();return false;}
  need(Atomics.compareExchange(state,0,0,1)===0,'PROCESS_STATE');
  try{
   new Uint8Array(this.#memory.buffer,this.#control.start+8,32).set(this.#digest);
   this.#initialize('process');
   need(Atomics.compareExchange(state,16+id,0,1)===0,'WORKER_STATE');this.#initialize(id);
   run();Atomics.store(state,16+id,2);Atomics.store(state,0,2);return true;
  }catch(e){Atomics.store(state,16+id,3);Atomics.store(state,0,3);throw e;}
 }
 worker(id,run){
  need(this.#layout.workers.includes(id),'WORKER_ID');const state=this.#state();
  need(Atomics.load(state,0)===2,'PROCESS_NOT_READY');this.#identity();
  need(Atomics.compareExchange(state,16+id,0,1)===0,'WORKER_STATE');
  try{this.#initialize(id);run();Atomics.store(state,16+id,2);}
  catch(e){Atomics.store(state,16+id,3);throw e;}
 }
}
