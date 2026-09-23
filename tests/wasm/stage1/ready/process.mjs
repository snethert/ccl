import {InitializationOwner} from './runtime/initialization-owner.mjs';
import {sha256} from './runtime/sha256.mjs';

// This selects the accepted single-Worker owner, not a second READY protocol.
export function processOwner(memory,gen,base,size){
 const region=(name,start,size,alignment=8)=>({name,owner:0,start,size,alignment,minimum:size});
 const regions=[{...region('control',1174208,72),owner:'process'},
  region('tcr-0',1024,256,16),region('vsp-0',131064,65536),
  region('tsp-0',700000,80000),region('csp-0',900000,100000),
  region('heap-0',base,size),region('tlb-0',680000,16384),
  region('cell-0',1174096,8),region('staging-0',1174104,104)];
 const words=Array(64).fill(0);
 const fields={0:0,4:0,8:1,20:1024,48:base,52:base+size,56:base,
  64:131576,68:131080,72:196600,76:700000,80:700000,84:780000,
  88:900000,92:900000,96:1000000,104:680000,108:4096,
  120:132088,124:132104,128:131072,188:77825,200:7};
 for(const [offset,value] of Object.entries(fields))words[offset/4]=value;
 const layout={version:1,workers:[0],regions,writes:[{region:'tcr-0',owner:0,offset:0,words}],
  modules:[],tableCapacity:4096,reservedSlots:[0]};
 return new InitializationOwner({memory,layout,layoutDigest:sha256(JSON.stringify(layout)),
  modules:[],table:gen.env.table,tail_table:gen.env.tail_table});
}
