// Numeric-service import admission must compare fields, not descriptor key order.
import {CollectorOwner} from '../../../../runtime/wasm32/collector-owner.mjs';
import {deriveLayout} from '../../../../runtime/wasm32/layout.mjs';
import {integerService} from '../../../../runtime/wasm32/integer-service.mjs';
import {floatService} from '../../../../runtime/wasm32/float-service.mjs';
import {sha256} from '../../../../runtime/wasm32/sha256.mjs';
export function numericChecks(binaries) {
 const need=(ok,why)=>{if(!ok)throw Error('numeric admission: '+why);},rows=[];
 const layout=deriveLayout({spaceBytes:65536,freeTarget:0},{bootFunctions:0,runtimeFunctions:0,runtimeRootCells:0,image:[{start:77824,end:77864}]}),tcr=layout.tcr;
 const memory=new WebAssembly.Memory({initial:layout.initialPages,maximum:32769,shared:true}),view=new DataView(memory.buffer);
 const put=(p,n)=>view.setUint32(p,n,true),get=p=>view.getUint32(p,true);
 put(77824,77825);put(77828,77825);put(77832,1850);for(let p=77836;p<77864;p+=4)put(p,77825);
 for(const [o,n] of Object.entries({...layout.tcrWords,8:1,32:2,188:77825}))put(tcr+Number(o),n);
 put(layout.runtimeGlobals,1);for(const group of layout.groups)put(group.slots[0],77825);
 const owner=CollectorOwner.create(memory,binaries.collector,sha256(binaries.collector),layout);
 const context={memory,tcr,owner,callError:new WebAssembly.Tag({parameters:['i32']})};
 const integer=bytes=>integerService({...context,bytes,digest:sha256(bytes)});
 const floating=detectorBytes=>floatService({...context,bytes:binaries.float,digest:sha256(binaries.float),detectorBytes,detectorDigest:sha256(detectorBytes)});
 const imports=WebAssembly.Module.imports;
 const observedKeys=Object.keys(imports(new WebAssembly.Module(binaries.integer))[0]);
 const before=()=>JSON.stringify(Array.from({length:64},(_,i)=>get(tcr+4*i)));
 for(const [name,create,bytes] of [['integer',integer,binaries.integer],['detector',floating,binaries.detector]]){
  const state=before();need(typeof create(bytes)==='function',name+' valid');need(before()===state,name+' state');rows.push(name+'-valid');
  try{
   WebAssembly.Module.imports=mod=>imports(mod).map(i=>({kind:i.kind,name:i.name,module:i.module}));
   need(typeof create(bytes)==='function',name+' reordered');need(before()===state,name+' reordered state');rows.push(name+'-reordered');
  }finally{WebAssembly.Module.imports=imports;}
 }
 // Minimal real binaries: one ()->() type, and the declared imports. They need
 // no exports: every wrong inventory must refuse before instantiation.
 const str=s=>[s.length,...new TextEncoder().encode(s)],section=(id,data)=>[id,data.length,...data];
 const module=entries=>new Uint8Array([0,97,115,109,1,0,0,0,...section(1,[1,96,0,0]),
  ...section(2,[entries.length,...entries.flatMap(([m,n,k])=>[...str(m),...str(n),k,...(k===2?[0,1]:k===3?[127,0]:[0])])])]);
 const expected=['env','memory',2];
 for(const [label,entries] of [['missing',[]],['module',[['bad','memory',2]]],['name',[['env','wrongx',2]]],
  ['kind',[['env','memory',0]]],['extra',[expected,['env','extra',3]]]]){
  const bytes=module(entries);
  for(const [name,create,message] of [['integer',integer,'integer imports'],['detector',floating,'FLOAT_IMPORTS']]){
   const state=before();let error;try{create(bytes);}catch(e){error=e;}
   need(error?.message===message,name+' '+label+' checked refusal: '+error);
   need(before()===state,name+' '+label+' preserved state');rows.push(name+'-'+label);
  }
 }
 return {status:'PASS',checks:rows.length,rows,observedKeys};
}
