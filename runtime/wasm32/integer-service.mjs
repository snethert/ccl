import {sha256} from './sha256.mjs';
import {CollectorOwner} from './collector-owner.mjs';
// A single-Worker capability. Arithmetic is exclusively in the pinned Wasm
// service. The private buffer holds pointer-free integer results across GC.
export function integerService({memory,tcr,owner,callError,bytes,digest,pinned=[]}){
 if(!(owner instanceof CollectorOwner)||!(memory instanceof WebAssembly.Memory)||!(callError instanceof WebAssembly.Tag)||sha256(bytes)!==digest)throw Error('integer owner capability');
 if(owner.view.buffer!==memory.buffer)throw Error('integer memory capability');
 const mod=new WebAssembly.Module(bytes);if(JSON.stringify(WebAssembly.Module.imports(mod))!==JSON.stringify([{module:'env',name:'memory',kind:'memory'}]))throw Error('integer imports');
 const privateMemory=new WebAssembly.Memory({initial:4,maximum:32769});
 const wasm=new WebAssembly.Instance(mod,{env:{memory:privateMemory}}).exports;
 const input=131072,inputEnd=147456,output=147456,outputEnd=163840,scratch=163840,scratchEnd=180256,result=180272;
 if(wasm.integer_workspace_bytes()!==scratchEnd-scratch)throw Error('integer workspace');
 const pv=new DataView(privateMemory.buffer),pb=new Uint8Array(privateMemory.buffer);
 const fail=n=>{throw new WebAssembly.Exception(callError,[n]);},view=()=>new DataView(memory.buffer),get=p=>view().getUint32(p,true),set=(p,v)=>view().setUint32(p,v,true);
 const regions=pinned.map(r=>({...r}));for(const r of regions)if(!Number.isSafeInteger(r.start)||!Number.isSafeInteger(r.end)||r.start<0||r.end<r.start||r.end>memory.buffer.byteLength)throw Error('integer pinned extent');
 let busy=false;
 return (op,root)=>{
  op>>>=0;root>>>=0;
  if(busy)fail(31);
  if(op>5||root%8||root<get(tcr+68)||root+16>get(tcr+72)||get(tcr+128)!==root||get(root+4)!==2)fail(31);
  busy=true;
  try{
   let cursor=input;
   const stage=v=>{
    if(v%4===0)return v;
    if(v%8!==6)fail(32);
    const p=v-6,spans=[...regions,{start:get(tcr+56),end:get(tcr+48)}],region=spans.find(r=>p>=r.start&&p+4<=r.end);
    if(!region)fail(32);const h=get(p),n=Math.floor(h/256),size=8*Math.ceil((4+4*n)/8);
    if(h%256!==7||n===0||n>1025||p+size>region.end||cursor+size>inputEnd)fail(32);
    const dest=cursor;cursor+=size;pb.set(new Uint8Array(memory.buffer,p,size),dest);return dest+6;
   };
   const a=stage(get(root+8)),b=op===4?0:stage(get(root+12));
   const status=wasm.integer_calculate(op,a,b,input,inputEnd,output,outputEnd,scratch,scratchEnd,result);
   if(status)fail(30+status); // all input-budget statuses are non-retryable
   const read=p=>pv.getUint32(p,true),count=read(result+8),size=read(result+12)-output;
   if(count!==(op===5?2:1)||size>outputEnd-output||size%8)fail(31);
   if(size){try{owner.atSafepoint(o=>o.ensure(size));}catch{fail(6);}}
   // Assurance can move every operand and grow memory. No heap address from
   // before that call is used here; the private results contain no references.
   const heap=get(tcr+48),limit=get(tcr+52);if(heap%8||heap<get(tcr+56)||heap+size>limit||heap+size>memory.buffer.byteLength)fail(6);
   const relocate=v=>v%4===0?v:heap+(v-6-output)+6;
   const aResult=relocate(read(result)),bResult=count===2?relocate(read(result+4)):0;
   if(size)new Uint8Array(memory.buffer,heap,size).set(pb.subarray(output,output+size));
   set(tcr+48,heap+size);set(root+8,aResult);set(root+12,bResult);
   return count;
  }finally{busy=false;}
 };
}
