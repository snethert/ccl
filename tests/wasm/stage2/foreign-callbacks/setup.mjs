import {CollectorOwner} from './runtime/collector-owner.mjs';
import {deriveLayout} from './runtime/layout.mjs';
import {sha256} from './runtime/sha256.mjs';
const assert=(ok,why)=>{if(!ok)throw Error(why);};
export function setup(binaries,placement=0){
  const layout=deriveLayout({spaceBytes:65536,freeTarget:0,valueStack:1048576+placement},{bootFunctions:0,runtimeFunctions:0,runtimeRootCells:0,image:[{start:77824,end:77864}]}),tcr=layout.tcr;
  const memory=new WebAssembly.Memory({initial:layout.initialPages,maximum:32769,shared:true});
  const get=p=>new DataView(memory.buffer).getUint32(p,true),put=(p,v)=>new DataView(memory.buffer).setUint32(p,v,true);
  put(77824,77825);put(77828,77825);put(77832,1850);for(let p=77836;p<77864;p+=4)put(p,77825);
  for(const [o,v] of Object.entries({...layout.tcrWords,8:1,32:2,188:77825}))put(tcr+Number(o),v);
  put(layout.runtimeGlobals,1);for(const group of layout.groups)put(group.slots[0],77825);
  const head=layout.root+40,args=head+16,base=get(tcr+48),pair=base+1;
  put(base,77825);put(base+4,168);put(tcr+48,base+8);
  put(head,layout.root);put(head+4,5);put(head+8,77825);put(head+12,77825);
  put(args,0);put(args+4,0);put(args+8,pair);put(tcr+64,args);put(tcr+128,head);
  const owner=CollectorOwner.create(memory,binaries.collector,sha256(binaries.collector),layout),boundary=owner.foreignBoundary;
  return {memory,tcr,layout,owner,boundary,get,put,head,args,pair,
   snapshot:()=>new Uint8Array(memory.buffer).slice(),
   unchanged:before=>{const after=new Uint8Array(memory.buffer);assert(before.length===after.length&&before.every((v,i)=>v===after[i]),'refusal wrote memory');}};
 }
