import {sha256} from './sha256.mjs';
import {CollectorOwner} from './collector-owner.mjs';
// Single trusted Worker. Object starts and exclusive heap ownership are supplied
// by the owner, not inferred from pointer tags. The private result is pointer-free.
export function floatService({memory,tcr,owner,callError,bytes,digest,detectorBytes,detectorDigest,pinned=[]}){
 const hash=sha256;
 if(!(owner instanceof CollectorOwner)||!(memory instanceof WebAssembly.Memory)||
    !(callError instanceof WebAssembly.Tag)||owner.tcr!==tcr||owner.view.buffer!==memory.buffer||
    hash(bytes)!==digest||hash(detectorBytes)!==detectorDigest)throw Error('FLOAT_CAPABILITY');
 const mod=new WebAssembly.Module(bytes),detector=new WebAssembly.Module(detectorBytes);
 const imports=WebAssembly.Module.imports(mod).map(x=>[x.module,x.name,x.kind].join('/')).sort();
 if(JSON.stringify(imports)!==JSON.stringify(['detector/add/function','detector/div/function','detector/mul/function','detector/sub/function','env/memory/memory'])||
    JSON.stringify(WebAssembly.Module.imports(detector))!==JSON.stringify([{module:'env',name:'memory',kind:'memory'}]))throw Error('FLOAT_IMPORTS');
 const privateMemory=new WebAssembly.Memory({initial:4,maximum:32769});
 const checks=new WebAssembly.Instance(detector,{env:{memory:privateMemory}}).exports;
 const wasm=new WebAssembly.Instance(mod,{env:{memory:privateMemory},detector:checks}).exports;
 const input=131072,inputEnd=147456,output=147456,outputEnd=147472,result=147472;
 const pv=new DataView(privateMemory.buffer),pb=new Uint8Array(privateMemory.buffer);
 let cachedView=new DataView(memory.buffer);
 const view=()=>{const b=memory.buffer;if(cachedView.buffer!==b)cachedView=new DataView(b);return cachedView;},get=p=>view().getUint32(p,true),set=(p,v)=>view().setUint32(p,v,true);
 const fail=n=>{throw new WebAssembly.Exception(callError,[n]);};
 const regions=pinned.map(r=>({...r}));
 for(const r of regions)if(!Number.isSafeInteger(r.start)||!Number.isSafeInteger(r.end)||r.start<0||r.start%8||r.end%8||r.end<r.start||r.end>memory.buffer.byteLength)throw Error('FLOAT_PINNED');
 let busy=false;
 return (op,root,safe)=>{
  op>>>=0;root>>>=0;safe>>>=0;
  if(busy||op>11||safe>1||root%8||root<get(tcr+68)||root+24>get(tcr+72)||
     get(tcr+128)!==root||get(root+4)!==4||get(root+16)!==77825||get(root+20)!==77825)fail(41);
  const mask=get(tcr+200);if(mask>31)fail(41);
  busy=true;
  try{
   let cursor=input;
   const stage=v=>{
    if(v%4===0)return v;
    if(v%8!==6)fail(42);
    const p=v-6,spans=[...regions,{start:get(tcr+56),end:get(tcr+48)}],region=spans.find(r=>p>=r.start&&p+4<=r.end);
    if(!region)fail(42);
    const h=get(p),n=Math.floor(h/256);
    const size=h===271?8:h===791?16:h%256===7&&n>0&&n<=1025?8*Math.ceil((4+4*n)/8):0;
    if(!size||p+size>region.end||cursor+size>inputEnd)fail(42);
    const dest=cursor;cursor+=size;pb.set(new Uint8Array(memory.buffer,p,size),dest);return dest+6;
   };
   const a=stage(get(root+8)),b=op>=10?0:stage(get(root+12));
   const status=wasm.float_calculate_lisp(op,a,b,input,inputEnd,output,outputEnd,result,mask,safe);
   if(status)fail(40+status);
   const read=o=>pv.getUint32(result+o,true),v=read(0),flags=read(4),selected=read(8),phase=read(12),size=read(16)-output,width=read(20),fa=read(24),fb=read(28);
   if(flags>31||selected>16||(selected&&(selected&(selected-1)))||phase<1||phase>3||fa>31||fb>31||
      ![0,32,64].includes(width)||size!==(selected||width===0?0:width===32?8:16)||
      (size?v!==output+6:![77825,77838].includes(v)))fail(41);
   if(size){try{owner.atSafepoint(o=>o.ensure(size));}catch{fail(6);}}
   // Assurance may move all operands and grow memory. Reload current pointers;
   // the private result has no Lisp references, and publication cannot safepoint.
   let published=v;
   if(size){
    const heap=get(tcr+48),limit=get(tcr+52);
    if(heap%8||heap<get(tcr+56)||heap+size>limit||heap+size>memory.buffer.byteLength)fail(6);
    new Uint8Array(memory.buffer,heap,size).set(pb.subarray(output,output+size));
    published=heap+6;set(tcr+48,heap+size);
   }
   set(root+16,published);
   // Raw return, never placed in a tagged slot. The future Lisp adapter decodes
   // status and signals while operands are still rooted. No condition here.
   return selected|(flags<<5)|(phase<<10)|(fa<<12)|(fb<<17);
  }finally{busy=false;}
 };
}
