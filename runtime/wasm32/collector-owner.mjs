// Single-Worker owner for the accepted copying service. No compiler/kernel edits.
import {sha256} from './sha256.mjs';
const PAGE=65536,NIL=77825,T=77838,REQUIRED=['module-constants','callbacks','registry','host'];
function need(x,why){if(!x)throw new Error('collector-owner: '+why);}
function integer(n){return Number.isSafeInteger(n)&&n>=0&&n<=0xffffffff;}
function contains(r,p,n=1){return p>=r.start&&p+n<=r.end;}
function overlaps(a,b){return a.start<b.end&&b.start<a.end;}
function align(n,a){return Math.ceil(n/a)*a;}
export class CollectorOwner {
 #roles=new Map();
 #scalarBoundary=new WebAssembly.Global({value:"i32",mutable:true},0);
 #memory;#collector;#layout;#view;#spaces;#boundary=false;#busy=false;#epoch=0;
 static create(memory,bytes,digest,layout){
  need(sha256(bytes)===digest,'collector digest');
  const mod=new WebAssembly.Module(bytes),imports=WebAssembly.Module.imports(mod);
  need(imports.length===1&&imports[0].module==='env'&&imports[0].name==='memory'&&imports[0].kind==='memory','collector imports');
  const owner=new CollectorOwner();owner.#memory=memory;owner.#layout=structuredClone(layout);owner.#spaces=structuredClone(layout.spaces);
  owner.#refresh();owner.#admit();
  owner.#collector=new WebAssembly.Instance(mod,{env:{memory}}).exports;
  need(owner.#collector.__stack_pointer.value===owner.#region('c-stack').end,'C stack extent');
  owner.#validate();return owner;
 }
 #refresh(){const buffer=this.#memory.buffer;if(!this.#view||this.#view.buffer!==buffer){this.#view=new DataView(buffer);this.#epoch++;}}
 get scalarAdmission(){
  const bounds={maximum:this.#layout.maximumPages};
  for(const [prefix,role] of [['v','vstack'],['t','temp'],['c','control'],['l','bindings']]){
   const r=this.#region(role);bounds[prefix+'0']=r.start;bounds[prefix+'1']=r.end;
  }
  return Object.freeze({boundary:this.#scalarBoundary,bounds:Object.freeze(bounds)});
 }
 get tcr(){return this.#layout.tcr;}
 get view(){this.#refresh();return this.#view;}
 get viewEpoch(){this.#refresh();return this.#epoch;}
 get spaces(){return structuredClone(this.#spaces);}
 #get(p){return this.view.getUint32(p,true);}
 #set(p,v){this.view.setUint32(p,v,true);}
 #t(o){return this.#get(this.#layout.tcr+o);}
 #region(role){if(this.#roles.has(role))return this.#roles.get(role);const rows=this.#layout.regions.filter(r=>r.role===role);need(rows.length===1,'region '+role);this.#roles.set(role,rows[0]);return rows[0];}
 #admit(){
  const l=this.#layout;need(l.collector==='copying'&&l.workers===1&&l.egc===false,'collector profile');need(l.version===1&&integer(l.maximumPages)&&l.maximumPages>0&&l.maximumPages<=65535,'layout version/maximum');
  need(Array.isArray(l.regions)&&Array.isArray(l.spaces)&&l.spaces.length===2,'region list');
  const names=new Set();for(const r of [...l.regions,...l.spaces]){
   need(typeof r.name==='string'&&!names.has(r.name),'unique region');names.add(r.name);
   need(integer(r.start)&&integer(r.end)&&r.start<r.end&&r.start%8===0&&r.end%8===0,'region extent');
   need(r.end<=this.view.byteLength,'region backed');
  }
  const all=[...l.regions,...l.spaces];for(let i=0;i<all.length;i++)for(let j=0;j<i;j++)need(!overlaps(all[i],all[j]),'regions overlap');
  for(const role of ['tcr','vstack','temp','control','c-stack','scratch','root-list','external','bindings'])this.#region(role);
  need(l.regions.every(r=>['tcr','vstack','temp','control','c-stack','scratch','root-list','external','bindings','image'].includes(r.role)),'region role');
  need(integer(l.tcr)&&l.tcr%16===0&&contains(this.#region('tcr'),l.tcr,256),'TCR extent');
  need(this.#region('scratch').start%16===0&&this.#region('scratch').end-this.#region('scratch').start>=96,'scratch header');
  need(this.#region('c-stack').start===1048576&&this.#region('c-stack').end===1114112,'compiled C stack');
  need(integer(l.logCapacity)&&l.logCapacity>0,'log capacity');
  need(this.view.byteLength/PAGE<=l.maximumPages,'memory maximum');
  need(Array.isArray(l.groups)&&l.groups.length===REQUIRED.length&&new Set(l.groups.map(g=>g.kind)).size===REQUIRED.length&&l.groups.every(g=>REQUIRED.includes(g.kind)&&Array.isArray(g.slots)),'root groups');
  const seen=new Set();for(const g of l.groups)for(const p of g.slots){
   need(integer(p)&&p%4===0&&contains(this.#region('external'),p,4)&&!seen.has(p),'external root slot');seen.add(p);
  }
  // The real distinguished objects, not just their values, have reserved homes.
  const images=l.regions.filter(r=>r.role==='image');
  need(images.some(r=>contains(r,NIL-1,8))&&images.some(r=>contains(r,T-6,32)),'canonical object ownership');
  need(this.#get(NIL-1)===NIL&&this.#get(NIL+3)===NIL&&this.#get(T-6)===1850,'canonical objects');
 }
 #imageSlots(){
  const result=[];
  for(const region of this.#layout.regions.filter(r=>r.role==='image')){
   let p=region.start;
   while(p<region.end){
    const h=this.#get(p),tag=h%256,n=Math.floor(h/256);let bytes=8,offset=0,count=2;
    if(tag%8===2||tag%8===7){
     offset=4;
     if([10,26,42,58,106,114,122,250].includes(tag)||(tag===130&&n>=1)){count=n;bytes=align(4+4*n,8);}
     else{count=0;let raw;
      if(tag===7&&n>0)raw=n*4;else if(tag===15&&n===1)raw=4;else if(tag===23&&n===3)raw=12;else if([159,167,175,183,191].includes(tag))raw=n*4;else if([199,207].includes(tag))raw=n;else if([215,223].includes(tag))raw=n*2;else if([231,239].includes(tag))raw=4+8*n;else if(tag===247)raw=4+16*n;else if(tag===255)raw=Math.ceil(n/8);
      need(raw!==undefined,'image kind');bytes=align(4+raw,8);
     }
    }
    need(p+bytes<=region.end,'image object extent');
    for(let i=0;i<count;i++)result.push(p+offset+4*i);
    p+=bytes;
   }
   need(p===region.end,'image inventory');
  }
  return result;
 }
 #validateLive(){
  this.#refresh();const view=this.#view,t=o=>view.getUint32(this.#layout.tcr+o,true);const spaces=this.#spaces,base=t(56),used=t(48),limit=t(52);
  const active=spaces.find(r=>r.start===base&&r.end===limit);need(active&&used>=base&&used<=limit&&used%8===0,'allocation ownership');
  const v=this.#region('vstack'),temp=this.#region('temp'),control=this.#region('control');
  need(t(68)===v.start+8&&t(72)===v.end,'value-stack ownership');
  need(t(80)===temp.start&&t(84)===temp.end&&t(76)>=temp.start&&t(76)<=temp.end,'temp-stack ownership');
  need(t(92)===control.start&&t(96)===control.end&&t(88)>=control.start&&t(88)<=control.end,'control-stack ownership');
  need(view.byteLength/PAGE<=this.#layout.maximumPages,'memory maximum');
  need(this.#get(NIL-1)===NIL&&this.#get(NIL+3)===NIL&&this.#get(T-6)===1850,'canonical objects');
  const tlb=t(104),cap=t(108);need(cap<=16777215&&tlb%4===0,'binding-vector shape');
  need(contains(active,tlb,cap*4)||contains(this.#region('bindings'),tlb,cap*4),'binding-vector ownership');
  const result=t(120),end=t(124);need(end>=result&&(contains(v,result,end-result)||contains(temp,result,end-result)),'result ownership');
  return active;
 }
 #validate(){
  const active=this.#validateLive();
  const slots=this.#imageSlots();for(const group of this.#layout.groups)slots.push(...group.slots);
  slots.push(this.#layout.tcr+188); // TCR v2 next_method_context: tagged-root.
  const list=this.#region('root-list');need(slots.length*4<=list.end-list.start,'root-list capacity');
  need(slots.length<=this.#layout.logCapacity,'root-update capacity');
  return {active,slots};
 }
 atSafepoint(action){
  need(!this.#boundary&&!this.#busy,'nested boundary');need(typeof action==='function','boundary callback');
  this.#boundary=true;this.#scalarBoundary.value=1;try{const value=action(this);need(!(value&&typeof value.then==='function'),'synchronous boundary');return value;}finally{this.#boundary=false;this.#scalarBoundary.value=0;}
 }
 #requireBoundary(){need(this.#boundary&&!this.#busy,'legal owner boundary');}
 #copy(destination){
  const {active,slots}=this.#validate(),scratch=this.#region('scratch'),list=this.#region('root-list');
  need(destination.start!==active.start&&destination.end<=this.view.byteLength,'destination');
  this.#busy=true;
  try{
   // All admission precedes the first scratch write. Mutator/image/root bytes
   // are committed only by the accepted collector after complete validation.
   new Uint8Array(this.#memory.buffer,scratch.start,96).fill(0);
   const set=(o,v)=>this.#set(scratch.start+o,v);set(0,this.#layout.tcr);set(16,destination.start);set(20,destination.end);set(68,this.#layout.logCapacity);set(72,list.start);set(76,slots.length);set(80,scratch.end);
   slots.forEach((p,i)=>this.#set(list.start+4*i,p));
   const status=this.#collector.collect(scratch.start);
   need(status===0,'collection refused '+status);
   return {source:active.start,destination:destination.start,objects:this.#get(scratch.start+84),reclaimed:this.#get(scratch.start+92),rootSlots:slots.length};
  }finally{this.#busy=false;}
 }
 collect(){this.#requireBoundary();const active=this.#validateLive();return this.#copy(this.#spaces.find(r=>r!==active));}
 growMemory(pages){
  this.#requireBoundary();this.#validate();need(integer(pages)&&pages>=this.view.byteLength/PAGE&&pages<=this.#layout.maximumPages,'growth maximum');
  const previous=this.view.byteLength/PAGE;
  if(pages>previous){try{this.#memory.grow(pages-previous);}catch{need(false,'engine growth refusal');}this.#refresh();need(this.view.byteLength===pages*PAGE,'growth view');}
  return {previous,pages,viewEpoch:this.viewEpoch};
 }
 ensure(bytes){
  this.#requireBoundary();need(integer(bytes)&&bytes>0&&bytes%8===0,'allocation request');
  // No root enumeration is needed until copying. Mutable owner state is still
  // checked before a fast assurance; collection re-inventories the live image.
  this.#validateLive();
  if(this.#t(52)-this.#t(48)>=bytes)return {collected:false,grown:false};
  const collection=this.collect();if(this.#t(52)-this.#t(48)>=bytes)return {collected:true,grown:false,collection};
  const live=this.#t(48)-this.#t(56),capacity=align(Math.max(2*(this.#t(52)-this.#t(56)),live+bytes),PAGE),start=this.view.byteLength;
  const end=start+2*capacity;need(end<=this.#layout.maximumPages*PAGE&&end<=0xffffffff,'heap growth maximum');
  this.growMemory(end/PAGE);
  const pair=[{name:'grown-a',start,end:start+capacity},{name:'grown-b',start:start+capacity,end}];
  const moved=this.#copy(pair[0]);this.#spaces=pair;
  return {collected:true,grown:true,collection,moved};
 }
}
