// D1 heap/code image proposal. No host address is retained in the artifact.
import {sha256} from '../../../../runtime/wasm32/sha256.mjs';
const need=(v,s)=>{if(!v)throw Error('heap image: '+s);};
const uint=x=>Number.isInteger(x)&&x>=0&&x<=0xffffffff;
const align=n=>Math.ceil(n/8)*8;
const pointer=w=>w!==77825&&w!==77838&&(w%8===1||w%8===6);
const RELOCATION=0xfffffff9; // remains a pointer until its required patch is applied
const overlap=(a,n,b,m)=>a<b+m&&b<a+n;
export const recordDigest=r=>sha256(JSON.stringify(r));

// Inventory the complete allocation stream, as the accepted collector does.
// A tagged interior address cannot create an object boundary.
function inventory(data) {
 const v=new DataView(data.buffer,data.byteOffset,data.byteLength),objects=new Map(),slots=[];
 const word=p=>{need(p+4<=data.length,'object extent');return v.getUint32(p,true);};
 for(let p=0;p<data.length;){
  const h=word(p),tag=h%256,n=Math.floor(h/256);let size=8,offset=0,count=2,kind=1;
  if(tag%8===2||tag%8===7){
   kind=6;offset=4;
   if(tag===74){
    const cap=(n-14)/2;
    need(Number.isInteger(cap)&&cap>=4&&cap<=16384&&(cap&(cap-1))===0,'hash capacity');
    need(p+align(4+n*4)<=data.length,'hash extent');
    need((word(p+8)&~0x60000000)===0&&(word(p+8)&0x40000000)!==0&&word(p+52)===cap*4&&word(p+56)===0,'hash owner');
    need(word(p+4)===77825&&word(p+12)===0&&word(p+16)===77825&&word(p+20)===77825&&word(p+24)===0&&word(p+28)===77825,'hash prefix');
    need(word(p+32)%4===0&&word(p+36)%4===0&&(word(p+32)+word(p+36))/4<=cap,'hash counts');
    need(word(p+40)===0xfffffffc||(word(p+40)%4===0&&word(p+40)/4<cap),'hash cache');
    count=n;size=align(4+n*4);
   }else if(tag===90){
    need(n===3&&word(p+4)===0&&[0,4].includes(word(p+8)),'population');count=3;size=16;
   }else if([10,26,42,58,106,114,122,250].includes(tag)||(tag===130&&n>=1)){
    if(tag===42)need(n===6||n===7,'function shape');
    count=n;size=align(4+n*4);
   }else{
    count=0;let raw;
    if(tag===7&&n>0)raw=n*4;
    else if(tag===15&&n===1)raw=4;
    else if(tag===23&&n===3)raw=12;
    else if([159,167,175,183,191].includes(tag))raw=n*4;
    else if([199,207].includes(tag))raw=n;
    else if([215,223].includes(tag))raw=n*2;
    else if([231,239].includes(tag))raw=4+8*n;
    else if(tag===247)raw=4+16*n;
    else if(tag===255)raw=Math.ceil(n/8);
    need(raw!==undefined,'object kind');size=align(4+raw);
   }
  }
  need(p+size<=data.length,'object extent');
  objects.set(p,{kind,size,header:h});
  for(let i=0;i<count;i++)slots.push(p+offset+4*i);
  p+=size;
 }
 return {objects,slots};
}

function regions(memory,definitions) {
 need(memory instanceof WebAssembly.Memory,'memory');
 const out=definitions.map(r=>({...r})).sort((a,b)=>a.start-b.start),names=new Set();
 for(let i=0;i<out.length;i++){
  const r=out[i];
  need(typeof r.name==='string'&&!names.has(r.name),'region name');names.add(r.name);
  need(uint(r.start)&&uint(r.size)&&r.size>0&&r.start%8===0&&r.size%8===0&&r.start+r.size<=memory.buffer.byteLength,'region extent');
  need(['objects','roots'].includes(r.kind),'region kind');
  if(i)need(out[i-1].start+out[i-1].size<=r.start,'region overlap');
 }
 return out;
}
function location(rs,address,bytes=4) {
 const r=rs.find(r=>address>=r.start&&address+bytes<=r.start+r.size);
 need(r,'unowned reference '+address);return {region:r.name,offset:address-r.start};
}
function extent(memory,start,size,rs) {
 need(uint(start)&&uint(size)&&size>0&&start%8===0&&size%8===0&&start+size<=memory.buffer.byteLength,'heap extent');
 need(rs.every(r=>!overlap(start,size,r.start,r.size)),'heap overlap');
}
function imports(memory,rs,bindings) {
 return rs.map(r=>{
  const bytes=new Uint8Array(memory.buffer,r.start,r.size).slice();
  if(r.kind==='roots')bytes.fill(0); // owner-supplied root storage, not imported objects
  for(const b of bindings)if(b.slot.region===r.name)bytes.fill(0,b.slot.offset,b.slot.offset+4);
  return {name:r.name,size:r.size,kind:r.kind,sha256:sha256(bytes)};
 });
}
function externalObjects(memory,rs) {
 return new Map(rs.filter(r=>r.kind==='objects').map(r=>[r.name,inventory(new Uint8Array(memory.buffer,r.start,r.size)).objects]));
}
function resolve(ref,objects,external,rs,base) {
 need(ref&&typeof ref==='object','reference');
 if(Object.hasOwn(ref,'immediate')){
  need(Object.keys(ref).length===1&&uint(ref.immediate)&&!pointer(ref.immediate),'immediate');return ref.immediate;
 }
 need([1,6].includes(ref.tag),'reference tag');
 if(Object.hasOwn(ref,'heap')){
  need(Object.keys(ref).length===2&&uint(ref.heap)&&objects.get(ref.heap)?.kind===ref.tag,'heap boundary');return base+ref.heap+ref.tag;
 }
 need(Object.keys(ref).length===3&&uint(ref.offset),'import reference');
 const r=rs.find(r=>r.name===ref.region);
 need(r&&external.get(r.name)?.get(ref.offset)?.kind===ref.tag,'import boundary');return r.start+ref.offset+ref.tag;
}

export function writeHeapImage({memory,start,end,regions:definitions,rootSlots,codeDigest}) {
 const rs=regions(memory,definitions);extent(memory,start,end-start,rs);
 need(/^[0-9a-f]{64}$/.test(codeDigest),'code digest');
 const payload=new Uint8Array(memory.buffer,start,end-start).slice(),v=new DataView(payload.buffer);
 const {objects,slots}=inventory(payload),external=externalObjects(memory,rs);
 function reference(w){
  if(!pointer(w))return {immediate:w};
  const tag=w%8,p=w-tag;
  const ref=p>=start&&p<end?{heap:p-start,tag}:{...location(rs,p,8),tag};
  resolve(ref,objects,external,rs,start);return ref;
 }
 const roots=[...new Set(rootSlots)].sort((a,b)=>a-b).map(p=>{
  need(uint(p)&&p%4===0,'root alignment');
  return {slot:location(rs,p),value:reference(new DataView(memory.buffer).getUint32(p,true))};
 });
 const relocations=[];
 for(const slot of slots){const w=v.getUint32(slot,true);if(pointer(w)){
  relocations.push({slot,value:reference(w)});v.setUint32(slot,RELOCATION,true);
 }}
 const record={version:1,layout:'D1',bytes:payload.length,codeDigest,
  payloadDigest:sha256(payload),imports:imports(memory,rs,roots),roots,relocations};
 return {record,payload,digest:recordDigest(record),objects:objects.size};
}

// Admission is read-only. Installation publishes relocated roots only after
// the entire byte image and binding set have been validated in private memory.
export function admitHeapImage({memory,record,payload,digest,regions:definitions,start,limit,codeDigest,rootSlots}) {
 const r=structuredClone(record),data=Uint8Array.from(payload),rs=regions(memory,definitions);
 need(recordDigest(r)===digest,'record digest');
 need(r.version===1&&r.layout==='D1'&&r.bytes===data.length&&sha256(data)===r.payloadDigest,'payload digest');
 need(r.codeDigest===codeDigest&&/^[0-9a-f]{64}$/.test(codeDigest),'code identity');
 extent(memory,start,r.bytes,rs);need(uint(limit)&&start+r.bytes<=limit&&limit<=memory.buffer.byteLength,'capacity');
 const allowed=new Set(rootSlots),seen=new Set();
 const bindingAddresses=r.roots.map(b=>{
  const region=rs.find(x=>x.name===b.slot.region);
  need(region&&uint(b.slot.offset)&&b.slot.offset%4===0&&b.slot.offset+4<=region.size,'binding extent');
  const address=region.start+b.slot.offset;
  need(allowed.has(address)&&!seen.has(address),'binding authority');seen.add(address);return address;
 });
 need(seen.size===allowed.size,'binding completeness');
 need(JSON.stringify(imports(memory,rs,r.roots))===JSON.stringify(r.imports),'import identity');
 const {objects,slots}=inventory(data),external=externalObjects(memory,rs),fields=new Set(slots),patched=new Set();
 const view=new DataView(data.buffer);
 for(const x of r.relocations){
  need(fields.has(x.slot)&&!patched.has(x.slot)&&view.getUint32(x.slot,true)===RELOCATION,'relocation slot');
  patched.add(x.slot);view.setUint32(x.slot,resolve(x.value,objects,external,rs,start),true);
 }
 // No naked pointer in an unrelocated field. Every relocation is mandatory.
 for(const p of slots)need(patched.has(p)||!pointer(view.getUint32(p,true)),'unrelocated pointer');
 const values=r.roots.map(b=>resolve(b.value,objects,external,rs,start));
 for(const [p,o] of objects){
  if(o.header===1834){
   const q=view.getUint32(p+28,true),at=q-start-6;
   need(q%8===6&&objects.get(at)?.header===2042,'funcallable immediates');
  }
  if(o.header%256===74){
   // Address hashing becomes stale on relocation, even before the first GC.
   const n=Math.floor(o.header/256);
   for(let i=14;i<n;i+=2)if(pointer(view.getUint32(p+4+4*i,true))){view.setUint32(p+8,view.getUint32(p+8,true)|0x20000000,true);break;}
  }
 }
 let state='ADMITTED';
 const baseline=imports(memory,rs,r.roots);
 return Object.freeze({
  get state(){return state;},get end(){return start+data.length;},get objects(){return objects.size;},
  install(){
   need(state==='ADMITTED','install state');
   need(JSON.stringify(imports(memory,rs,r.roots))===JSON.stringify(baseline),'imports changed');
   new Uint8Array(memory.buffer,start,data.length).set(data);
   const v=new DataView(memory.buffer);bindingAddresses.forEach((p,i)=>v.setUint32(p,values[i],true));
   state='INSTALLED';return {start,end:start+data.length,rootSlots:[...bindingAddresses]};
  },
  initialize(run){
   need(state==='INSTALLED'&&typeof run==='function','initialize state');state='INITIALIZING';
   try{need(run()===true,'initializer completion');state='READY';}
   catch(error){state='FAILED';throw error;}
  }
 });
}
