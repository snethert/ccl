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
 #blocks=[];
 #scalarBoundary=new WebAssembly.Global({value:"i32",mutable:true},0);
 #foreign=null;
 #callback=false;
 #finalizers=new Set();#finalizerQueue=new Set();#drainingFinalizers=false;
 #memory;#collector;#layout;#view;#spaces;#boundary=false;#busy=false;#epoch=0;#measure;
 static create(memory,bytes,digest,layout,{measure}={}){
  need(sha256(bytes)===digest,'collector digest');
  const mod=new WebAssembly.Module(bytes),imports=WebAssembly.Module.imports(mod);
  need(imports.length===1&&imports[0].module==='env'&&imports[0].name==='memory'&&imports[0].kind==='memory','collector imports');
  const owner=new CollectorOwner();owner.#memory=memory;owner.#layout=structuredClone(layout);owner.#spaces=structuredClone(layout.spaces);owner.#measure=measure;
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
 get collectionCount(){const count=this.#t(204);need(count<=536870911,'collection count');return count;}
 // The admitted collector profile has exactly one Lisp Worker. Its only GC
 // while FOREIGN is the synchronous collector capability below, on that same
 // Worker. This is not the multi-Worker gc_gen admission protocol.
 get foreignBoundary(){return Object.freeze({
  enter:operation=>{
   need(!this.#foreign&&!this.#callback&&!this.#boundary&&!this.#busy,'foreign reentry');
   need(typeof operation==='string','foreign operation');
   const words=new Int32Array(this.#memory.buffer),state=(this.tcr+32)/4;
   need(Atomics.load(words,state)===2&&this.#t(8)>0&&this.#t(12)===0&&this.#t(16)===0,'foreign thread');
   need(this.#t(144)===0&&Atomics.load(words,(this.tcr+152)/4)===0,'foreign descriptor');
   this.#validateLive();
   // B publishes its callable, scratch and arguments before the service call.
   // Keep that chain in place; never save tagged values in an untraced JS local.
   const head=this.#t(128),v=this.#region('vstack');
   need(head%8===0&&contains(v,head,16)&&head+16===this.#t(64),'foreign root head');
   const count=this.#get(head+4);
   need(count>=2&&contains(v,head,8+4*count),'foreign root extent');
   const offsets=[8,12,16,64,76,88,116,120,124,128,132,140,148,152,156,160,164,168];
   const token=Object.freeze({operation});
   this.#foreign={token,head,offsets,values:offsets.map(o=>this.#t(o))};
   this.#set(this.tcr+144,head);
   Atomics.store(words,state,3);
   return token;
  },
  leave:token=>{
   const frame=this.#foreign;
   need(frame&&token===frame.token,'foreign token');
   need(!this.#boundary&&!this.#busy,'foreign collecting');
   const words=new Int32Array(this.#memory.buffer);
   need(Atomics.load(words,(this.tcr+32)/4)===3&&this.#t(144)===frame.head,'foreign publication');
   need(frame.offsets.every((o,i)=>this.#t(o)===frame.values[i]),'foreign checkpoint');
   this.#validateLive();
   // Allocation bounds, moved binding-vector pointers and tagged roots belong
   // to the collector. Do not restore their stale pre-entry values.
   this.#set(this.tcr+144,0);
   Atomics.store(words,(this.tcr+32)/4,2);
   this.#foreign=null;
  }
 });}
 collectForeign(){
  need(this.#foreign&&Atomics.load(new Int32Array(this.#memory.buffer),(this.tcr+32)/4)===3,
       'foreign collection');
  return this.atSafepoint(o=>o.collect());
 }
 // Synchronous one-Worker callback admission. The trusted invoker must unwind
 // its B frames before returning (or throwing). No nested foreign entry yet.
 callForeignCallback(action){
  let frame;
  try{
   need(typeof action==='function'&&!this.#callback,'callback action');
   frame=this.#foreign;need(frame,'callback foreign');
   this.foreignBoundary.leave(frame.token);
  }catch(error){throw new AggregateError([error],'collector-owner: callback admission',{cause:error});}
  this.#callback=true;
  try{
   const result=action();
   if(result&&typeof result.then==='function')throw new AggregateError([], 'collector-owner: asynchronous callback');
   return result;
  }finally{
   try{
    need(!this.#boundary&&!this.#busy&&!this.#foreign,'callback boundary');
    need(this.#t(32)===2&&this.#t(144)===0,'callback publication');
    need(frame.offsets.every((offset,index)=>this.#t(offset)===frame.values[index]),'callback checkpoint');
    this.#validateLive();
    this.#foreign=frame;
    this.#set(this.tcr+144,frame.head);
    Atomics.store(new Int32Array(this.#memory.buffer),(this.tcr+32)/4,3);
    this.#callback=false;
   }catch(error){throw new AggregateError([error],'collector-owner: callback return',{cause:error});}
  }
 }
 #inhibitionState(){
  const region=this.#layout.regions.find(r=>r.role==='runtime-globals');
  if(!region)return {region:null,depth:0,pending:false};
  need(this.#get(region.start)===1&&this.#get(region.start+4)<=536870911&&
       this.#get(region.start+8)<=1&&this.#get(region.start+12)===0&&
       (this.#get(region.start+4)!==0||this.#get(region.start+8)===0),'inhibition state');
  return {region,depth:this.#get(region.start+4),pending:this.#get(region.start+8)===1};
 }
 get collectionInhibition(){return this.#inhibitionState().depth;}
 get collectionPending(){return this.#inhibitionState().pending;}
 inhibitCollection(delta){
  this.#requireBoundary();need(delta===1||delta===-1,'inhibition operation');
  const state=this.#inhibitionState();need(state.region,'runtime globals capability');
  const depth=state.depth+delta;
  need(depth>=0&&depth<=536870911,'inhibition depth');
  if(delta===1&&state.depth===0){
   // A lock can be taken before an allocation in native hash-table rehashing.
   // Put the heap at the owned tail before inhibition, where it can grow
   // without moving live objects or overwriting any embedding-owned region.
   const active=this.#validateLive();
   if(!this.#tailHeap(active))this.#relocateHeap(active.end-active.start);
  }
  this.#set(state.region.start+4,depth);
  if(depth===0&&state.pending){
   this.#set(state.region.start+8,0);this.collect();return 0;
  }
  return state.pending?-depth:depth;
 }
 #tailHeap(active){
  const other=this.#spaces.find(r=>r!==active),end=this.view.byteLength;
  return active.end===end||(active.end===other.start&&other.end===end);
 }
 #workspace(){
  const scratch=this.#region('scratch');
  const bytes=96+(this.#t(48)-this.#t(56))/8*20+this.#layout.logCapacity*12;
  if(bytes>scratch.end-scratch.start){
   const start=this.view.byteLength,end=start+align(Math.max(bytes,2*(scratch.end-scratch.start)),PAGE);
   this.growMemory(end/PAGE);scratch.start=start;scratch.end=end;
  }
 }
 #relocateHeap(capacity){
  capacity=align(capacity,PAGE);
  this.#workspace();
  const start=this.view.byteLength,end=start+2*capacity;
  need(end<=this.#layout.maximumPages*PAGE&&end<=0xffffffff,'heap growth maximum');
  this.growMemory(end/PAGE);
  const pair=[{name:'grown-a',start,end:start+capacity},{name:'grown-b',start:start+capacity,end}];
  const moved=this.#copy(pair[0]);this.#spaces=pair;return moved;
 }
 #growInhibited(bytes){
  const active=this.#validateLive();need(this.#tailHeap(active),'inhibited heap ownership');
  const live=this.#t(48)-active.start;
  const capacity=align(Math.max(2*(active.end-active.start),live+bytes),PAGE);
  const limit=active.start+capacity,otherStart=Math.max(limit,this.view.byteLength),end=otherStart+capacity;
  need(end<=this.#layout.maximumPages*PAGE&&end<=0xffffffff,'heap growth maximum');
  this.growMemory(end/PAGE);
  active.end=limit;
  this.#spaces=[active,{name:active.name==='grown-a'?'grown-b':'grown-a',start:otherStart,end}];
  this.#set(this.#layout.tcr+52,limit);
  this.#set(this.#inhibitionState().region.start+8,1);
  return {collected:false,grown:true,deferred:true};
 }
 get tcr(){return this.#layout.tcr;}
 get view(){this.#refresh();return this.#view;}
 get viewEpoch(){this.#refresh();return this.#epoch;}
 get spaces(){return structuredClone(this.#spaces);}
 // Observation only: current owned extents, not a reachability walk or GC.
 get storage(){return {spaces:this.spaces,scratch:{...this.#region('scratch')},
  rootList:{...this.#region('root-list')},external:{...this.#region('external')},
  reservedRootCells:this.#blocks.reduce((n,b)=>n+(b.end-b.start)/4,0),
  registeredRootCells:this.#layout.groups.reduce((n,g)=>n+g.slots.length,0)};}
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
  need(l.regions.every(r=>['tcr','vstack','temp','control','c-stack','scratch','root-list','external','bindings','image','runtime-globals','code-registry'].includes(r.role)),'region role');
  need(integer(l.tcr)&&l.tcr%16===0&&contains(this.#region('tcr'),l.tcr,256),'TCR extent');
  need(this.#region('scratch').start%16===0&&this.#region('scratch').end-this.#region('scratch').start>=96,'scratch header');
  need(this.#region('c-stack').start===1048576&&this.#region('c-stack').end===1114112,'compiled C stack');
  need(integer(l.logCapacity)&&l.logCapacity>0,'log capacity');
  need(l.freeTarget===undefined||integer(l.freeTarget),'free target');
  need(this.view.byteLength/PAGE<=l.maximumPages,'memory maximum');
  need(Array.isArray(l.groups)&&l.groups.length===REQUIRED.length&&new Set(l.groups.map(g=>g.kind)).size===REQUIRED.length&&l.groups.every(g=>REQUIRED.includes(g.kind)&&Array.isArray(g.slots)),'root groups');
  const seen=new Set();for(const g of l.groups)for(const p of g.slots){
   need(integer(p)&&p%4===0&&contains(this.#region('external'),p,4)&&!seen.has(p),'external root slot');seen.add(p);
  }
  const globals=l.regions.filter(r=>r.role==='runtime-globals');
  need(globals.length<=1&&globals.every(r=>r.start%16===0&&r.end-r.start===16),'runtime globals extent');
  const inhibition=this.#inhibitionState();
  need(inhibition.depth===0&&!inhibition.pending,'fresh inhibition state');
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
     if(tag===90){need(n===3&&p+16<=region.end&&this.#get(p+4)===0&&(this.#get(p+8)===0||this.#get(p+8)===4),'image population shape');count=3;bytes=16;}
     else if(tag===98){need(n===8,'image package shape');count=8;bytes=40;}
     else if([10,26,42,58,106,114,122,250].includes(tag)||(tag===130&&n>=1)){count=n;bytes=align(4+4*n,8);}
     else{count=0;let raw;
      if(tag===7&&n>0)raw=n*4;else if(tag===15&&n===1)raw=4;else if(tag===23&&n===3)raw=12;else if([159,167,175,183,191].includes(tag))raw=n*4;else if([199,207].includes(tag))raw=n;else if([215,223].includes(tag))raw=n*2;else if([231,239].includes(tag))raw=4+8*n;else if(tag===247)raw=4+16*n;else if(tag===255)raw=Math.ceil(n/8);
      need(raw!==undefined,'image kind');bytes=align(4+raw,8);
     }
    }
    need(p+bytes<=region.end,'image object extent');
    if(tag===42){
     need(n===6||n===7,'image function shape');
     if(n===7){const q=this.#get(p+28);need(q%8===6&&q-6+32<=this.#view.byteLength,'image immediates extent');need(this.#get(q-6)===2042,'image immediates shape');}
    }
    for(let i=0;i<count;i++)result.push(p+offset+4*i);
    p+=bytes;
   }
   need(p===region.end,'image inventory');
  }
  return result;
 }
 #validateLive(){
  this.#refresh();const view=this.#view,t=o=>view.getUint32(this.#layout.tcr+o,true);const spaces=this.#spaces,base=t(56),used=t(48),limit=t(52);
  need(t(204)<=536870911,'collection count');
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
  const slots=this.#imageSlots();for(const group of this.#layout.groups)for(const p of group.slots)slots.push(p);
  slots.push(this.#layout.tcr+188); // TCR v2 next_method_context: tagged-root.
  const list=this.#region('root-list');need(slots.length*4<=list.end-list.start,'root-list capacity');
  need(slots.length<=this.#layout.logCapacity,'root-update capacity');
  return {active,slots};
 }
 atSafepoint(action){
  need(!this.#boundary&&!this.#busy,'nested boundary');need(typeof action==='function','boundary callback');
  this.#boundary=true;this.#scalarBoundary.value=1;try{const value=action(this);need(!(value&&typeof value.then==='function'),'synchronous boundary');return value;}finally{this.#boundary=false;this.#scalarBoundary.value=0;}
 }
 rootCells(values){
  this.#requireBoundary();
  need(Array.isArray(values)&&values.every(integer),'root values');
  const {slots:live}=this.#validate(),region=this.#region('external');
  const used=new Set(this.#layout.groups.flatMap(g=>g.slots)),slots=[];
  for(let p=region.start;p<region.end&&slots.length<values.length;p+=4)if(!used.has(p)&&!this.#blocks.some(b=>p>=b.start&&p<b.end))slots.push(p);
  const list=this.#region('root-list');
  need(slots.length===values.length&&live.length+this.#reservedUnregistered()+slots.length<=this.#layout.logCapacity&&
       (live.length+this.#reservedUnregistered()+slots.length)*4<=list.end-list.start,'root capacity');
  const group=this.#layout.groups.find(g=>g.kind==='module-constants');
  slots.forEach((p,i)=>this.#set(p,values[i]));group.slots.push(...slots);
  let active=true;
  return Object.freeze({slots:Object.freeze(slots),
   values:()=>{need(active,'released roots');return slots.map(p=>this.#get(p));},
   release:()=>{this.#requireBoundary();need(active,'released roots');
    const removed=new Set(slots);group.slots=group.slots.filter(p=>!removed.has(p));
    slots.forEach(p=>this.#set(p,NIL));active=false;}
  });
 }
 // Weak anchors are owned heap objects, never tagged values retained as roots.
 // A registered action must contain only host capabilities, not Lisp pointers.
 registerFinalizer(word,action){
  this.#requireBoundary();
  need(typeof action==='function','finalizer action');
  const active=this.#validateLive(),tag=word%8;
  need(integer(word)&&(tag===1||tag===6)&&word-tag>=active.start&&
       word-tag<this.#t(48)&&this.validObject(word),'finalizer object');
  const row={word,action,state:'watching'};this.#finalizers.add(row);
  return Object.freeze({cancel:()=>{
   need(!this.#busy,'finalizer collecting');
   if(row.state==='done'||row.state==='cancelled')return false;
   this.#finalizers.delete(row);this.#finalizerQueue.delete(row);
   row.state='cancelled';row.word=0;row.action=null;return true;
  }});
 }
 get pendingFinalizers(){return this.#finalizerQueue.size;}
 drainFinalizers(){
  need(!this.#foreign&&!this.#callback&&!this.#boundary&&!this.#busy&&!this.#drainingFinalizers,'finalizer boundary');
  need(Atomics.load(new Int32Array(this.#memory.buffer),(this.tcr+32)/4)===2,'finalizer thread');
  this.#validateLive();
  this.#drainingFinalizers=true;let count=0;
  try{
   // One batch only. A destructor may collect and queue the next batch.
   for(const row of [...this.#finalizerQueue]){
    if(!this.#finalizerQueue.delete(row))continue;
    const action=row.action;row.action=null;row.state='done';count++;
    const value=action();need(!(value&&typeof value.then==='function'),'finalizer synchronous');
   }
   return count;
  }finally{this.#drainingFinalizers=false;}
 }
 #reservedUnregistered(){return this.#blocks.reduce((n,b)=>n+(b.end-b.start)/4-b.registered.size,0);}
 reserveRootBlock(count){
  this.#requireBoundary();need(integer(count)&&count>0,'root block count');
  const region=this.#region('external'),list=this.#region('root-list');
  const occupied=[...this.#blocks.map(b=>({start:b.start,end:b.end})),
   ...this.#layout.groups.flatMap(g=>g.slots.map(p=>({start:p,end:p+4})))].sort((a,b)=>a.start-b.start);
  let start=region.start;
  for(const r of occupied){if(start+4*count<=r.start)break;if(r.end>start)start=r.end;}
  const end=start+4*count,charged=this.#validate().slots.length+this.#reservedUnregistered()+count;
  need(end<=region.end&&charged<=this.#layout.logCapacity&&4*charged<=list.end-list.start,'root capacity');
  // Scratch must accommodate the charged root log before the reservation is
  // published. The C ABI still receives only the registered cells.
  need(96+this.#layout.logCapacity*12<=this.#region('scratch').end-this.#region('scratch').start,'root scratch capacity');
  let previous=new Uint8Array(this.#memory.buffer,start,4*count).slice(),active=true;
  for(let p=start;p<end;p+=4)this.#set(p,NIL);
  const block={start,end,registered:new Set()};this.#blocks.push(block);
  const group=this.#layout.groups.find(g=>g.kind==='module-constants');
  return Object.freeze({base:start,count,
   commit:()=>{need(active,'released roots');previous=null;},
   register:cells=>{this.#requireBoundary();need(active&&Array.isArray(cells)&&new Set(cells).size===cells.length,'root slice');
    for(const p of cells)need(integer(p)&&p>=start&&p<end&&p%4===0&&!block.registered.has(p),'root slice');
    for(const p of cells){block.registered.add(p);group.slots.push(p);}},
   unregister:cells=>{this.#requireBoundary();need(active&&new Set(cells).size===cells.length,'root slice');
    for(const p of cells)need(block.registered.has(p),'root slice');
    const remove=new Set(cells);for(const p of cells)block.registered.delete(p);
    group.slots=group.slots.filter(p=>!remove.has(p));},
   release:()=>{this.#requireBoundary();need(active&&block.registered.size===0,'released roots');
    if(previous)new Uint8Array(this.#memory.buffer,start,4*count).set(previous);
    else for(let p=start;p<end;p+=4)this.#set(p,NIL);
    this.#blocks.splice(this.#blocks.indexOf(block),1);previous=null;active=false;}
  });
 }
 // Printer validity is an ownership query, not a collection or a snapshot:
 // even a malformed argument must never enter the collector's root graph.
 validObject(word){
  this.#requireBoundary();need(integer(word),'object word');
  const active=this.#validateLive(),tag=word%8;
  if(word%4===0||tag===3||word===NIL||word===T)return true;
  if(tag!==1&&tag!==6)return false;
  const base=word-tag;
  const regions=this.#layout.regions.filter(r=>r.role==='image'&&r.enumerable!==false);
  regions.push({start:active.start,end:this.#t(48)});
  const region=regions.find(r=>contains(r,base));
  if(!region){
   // The emitter also constructs nonescaping callable records on the value
   // stack. These have the same six-cell shape recognized by collector.c.
   const v=this.#region('vstack'),top=this.#t(64);
   need(top>=v.start+8&&top<=v.end,'value-stack frontier');
   return tag===6&&base>=v.start+8&&base+32<=top&&this.#get(base)===1578;
  }
  for(let p=region.start;p<=base;){
   const h=this.#get(p),kind=h&255,n=h>>>8;let bytes=8,lowtag=1;
   if(kind%8===2||kind%8===7){
    lowtag=6;let raw;
    if([10,26,58,106,114,122,250].includes(kind)||
       (kind===42&&(n===6||n===7))||(kind===130&&n>=1)||
       (kind===98&&n===8)||(kind===90&&n===3)||(kind===82&&n===1)||
       (kind===66&&n===6)||(kind===50&&(n===4||n===7))||
       (kind===234&&n>=5)||(kind===242&&n===5)||
       (kind===74&&n>=16&&(n-14)%2===0))raw=n*4;
    else if((kind===7&&n>0)||(kind===15&&n===1)||
       ([23,71].includes(kind)&&n===3)||(kind===79&&n===5)||
       [159,167,175,183,191].includes(kind))raw=n*4;
    else if([199,207].includes(kind))raw=n;
    else if([215,223].includes(kind))raw=n*2;
    else if([231,239].includes(kind))raw=4+n*8;
    else if(kind===247)raw=4+n*16;
    else if(kind===255)raw=Math.ceil(n/8);
    if(raw===undefined)return false;
    bytes=align(4+raw,8);
   }
   if(p+bytes>region.end)return false;
   if(p===base)return tag===lowtag;
   p+=bytes;
  }
  return false;
 }
 heapSnapshot(mask){
  this.#requireBoundary();need(integer(mask)&&mask<=3,'heap areas');
  const inventory=()=>{
   const active=this.#validateLive(),objects=[];
   const regions=(mask&2?this.#layout.regions.filter(r=>r.role==='image'&&r.enumerable!==false):[]);
   if(mask&1)regions.push({start:active.start,end:this.#t(48)});
   for(const region of regions)for(let p=region.start;p<region.end;){
    const h=this.#get(p),tag=h&255,n=h>>>8;let bytes=8,lowtag=1;
    if(tag%8===2||tag%8===7){
     lowtag=6;let raw;
     if([10,26,42,50,58,66,74,82,90,98,106,114,122,130,234,242,250].includes(tag))raw=n*4;
     else if([7,15,23,71,79,159,167,175,183,191].includes(tag))raw=n*4;
     else if([199,207].includes(tag))raw=n;
     else if([215,223].includes(tag))raw=n*2;
     else if([231,239].includes(tag))raw=4+n*8;
     else if(tag===247)raw=4+n*16;
     else if(tag===255)raw=Math.ceil(n/8);
     need(raw!==undefined,'heap snapshot kind');bytes=align(4+raw,8);
    }
    need(p+bytes<=region.end,'heap snapshot extent');objects.push(p+lowtag);p+=bytes;
   }
   return objects;
  };
  let objects=inventory();const reserved=align(4+4*objects.length,8);
  this.ensure(reserved);objects=inventory();
  const bytes=align(4+4*objects.length,8),base=this.#t(48);
  need(bytes<=reserved&&base+bytes<=this.#t(52),'heap snapshot capacity');
  this.#set(base,objects.length*256+250);
  objects.forEach((word,i)=>this.#set(base+4+i*4,word));
  if(bytes>4+objects.length*4)this.#set(base+bytes-4,0);
  this.#set(this.#layout.tcr+48,base+bytes);return base+6;
 }
 #requireBoundary(){need(this.#boundary&&!this.#busy,'legal owner boundary');}
 #copy(destination){
  return this.#measure?this.#measure('collector.copy',()=>this.#copyInto(destination)):this.#copyInto(destination);
 }
 #copyInto(destination){
  const measure=this.#measure??((_p,run)=>run());
  const prepared=measure('collector.prepare',()=>{
   const {active,slots}=this.#validate(),scratch=this.#region('scratch'),list=this.#region('root-list');
   need(destination.start!==active.start&&destination.end<=this.view.byteLength,'destination');
   this.#workspace();
   const count=this.collectionCount;need(count<536870911,'collection count exhausted');
   new Uint8Array(this.#memory.buffer,scratch.start,96).fill(0);
   const set=(o,v)=>this.#set(scratch.start+o,v);set(0,this.#layout.tcr);set(16,destination.start);set(20,destination.end);set(68,this.#layout.logCapacity);set(72,list.start);set(76,slots.length);set(80,scratch.end);
   slots.forEach((p,i)=>this.#set(list.start+4*i,p));
   return {active,slots,scratch,count,usedBytes:this.#t(48)-this.#t(56)};
  });
  this.#busy=true;
  try{
   const {active,slots,scratch,count,usedBytes}=prepared;
   const status=measure('collector.c',()=>this.#collector.collect(scratch.start));
   need(status===0,'collection refused '+status);need(this.collectionCount===count+1,'collection count publication');
   // Query the successful collector's forwarding map before scratch reuse.
   // Publication only: no foreign or Lisp code runs inside the critical section.
   for(const row of this.#finalizers){
    const word=this.#collector.weak_forward(scratch.start,row.word)>>>0;
    need(word!==0xffffffff,'finalizer forwarding');row.word=word;
    if(word===0){row.state='queued';this.#finalizers.delete(row);this.#finalizerQueue.add(row);}
   }
   return {source:active.start,destination:destination.start,objects:this.#get(scratch.start+84),
    reclaimed:this.#get(scratch.start+92),rootSlots:slots.length,usedBytes,liveBytes:this.#t(48)-this.#t(56)};
  }finally{this.#busy=false;}
 }
 #collectFor(bytes){
  const active=this.#validateLive(),state=this.#inhibitionState();
  if(state.depth){this.#set(state.region.start+8,1);return {deferred:true};}
  const collection=this.#copy(this.#spaces.find(r=>r!==active));
  const live=this.#t(48)-this.#t(56),free=this.#t(52)-this.#t(48),target=this.#layout.freeTarget??0;
  if(free>=bytes+target)return collection;
  const capacity=align(Math.max(2*(this.#t(52)-this.#t(56)),live+bytes+target),PAGE);
  try{return {...collection,grown:true,moved:this.#relocateHeap(capacity)};}
  catch(error){
   // Headroom is a policy preference, never a reason to refuse an allocation
   // that fits. Corrupt roots and collector refusals still propagate.
   if(!['collector-owner: heap growth maximum','collector-owner: engine growth refusal'].includes(error.message))throw error;
   if(free>=bytes)return {...collection,headroomRefused:error.message};
   if(target===0)throw error;
   return {...collection,grown:true,headroomRefused:error.message,moved:this.#relocateHeap(align(live+bytes,PAGE))};
  }
 }
 collect(){this.#requireBoundary();return this.#collectFor(0);}
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
  if(this.collectionInhibition)return this.#growInhibited(bytes);
  const collection=this.#collectFor(bytes);
  return {collected:true,grown:collection.grown??false,collection,...(collection.moved?{moved:collection.moved}:{})};
 }
}
