import fs from 'node:fs';import assert from 'node:assert/strict';
import {createStrongPopulation,POPULATION_POLICY} from './population.mjs';
const dir=process.argv[2],module=await WebAssembly.compile(fs.readFileSync(dir+'/collector.wasm'));
let rows=[],refusals=0;
for(const base of [262144,2147483648]){
 const memory=new WebAssembly.Memory({initial:Math.max(64,(base+65536)/65536),maximum:32769,shared:true});
 const copy=(await WebAssembly.instantiate(module,{env:{memory}})).exports;
 const view=new DataView(memory.buffer),get=p=>view.getUint32(p,true),put=(p,x)=>view.setUint32(p,x,true);
 const tcr=1024,root=131064,cfg=1200000,other=3145728,size=65536,NIL=77825;
 for(const [site,type] of [['system-locks','list'],['threads','list'],['all-gfs','list'],['make-population','list'],['make-population','alist']]){
  new Uint8Array(memory.buffer,base,size).fill(0);new Uint8Array(memory.buffer,tcr,256).fill(0);new Uint8Array(memory.buffer,cfg,96).fill(0);
  put(base,NIL);put(base+4,68);put(base+8,NIL);put(base+12,116);const a=base+1,b=base+9;
  const members=type==='list'?[a,b]:[[a,b]],start=base+16,bytes=32,args={memory,base:start,end:start+bytes,type,members,policy:POPULATION_POLICY};
  for(const change of [{policy:null},{type:'weak-list'},{end:start+bytes+8},{base:start+4,end:start+4+bytes},{members:[NaN]},{members:[[a,-1]]}]){
   const before=new Uint8Array(memory.buffer,base,size).slice();assert.throws(()=>createStrongPopulation({...args,...change}));assert.deepEqual(new Uint8Array(memory.buffer,base,size),before);refusals++;
  }
  let p=createStrongPopulation(args).object;
  // Caller-owned arrays (and their pair arrays) are not the retained spine.
  if(type==='alist')members[0][0]=NIL;members[0]=NIL;
  const used=start+bytes;put(used,NIL);put(used+4,396); // one dead cons
  put(tcr+48,used+8);put(tcr+52,base+size);put(tcr+56,base);put(tcr+68,root+8);put(tcr+72,196608);put(tcr+128,root);put(root,0);put(root+4,1);put(root+8,p);
  put(tcr+80,700000);put(tcr+76,700000);put(tcr+84,900000);put(tcr+120,100000);put(tcr+124,100064);put(tcr+104,610000);
  put(cfg,tcr);put(cfg+68,32768);put(cfg+72,1180000);put(cfg+80,1800000);
  for(let pass=0;pass<3;pass++){
   const from=get(tcr+56),to=from===base?other:base;put(cfg+16,to);put(cfg+20,to+size);assert.equal(copy.collect(cfg),0,'strong population collection');p=get(root+8);
   assert.equal(get(tcr+48)-get(tcr+56),48,'population live bytes');assert.equal(get(cfg+84),5);assert.equal(get(cfg+92),pass===0?8:0);
   new Uint8Array(memory.buffer,from,size).fill(0xda);
   assert.equal(get(p-6),762);assert.equal(get(p-2),type==='list'?0:4,'population type');
   let head=get(p+2),key,value;
   if(type==='list'){key=get(head+3);head=get(head-1);value=get(head+3);assert.equal(get(head-1),NIL);}
   else{const pair=get(head+3);key=get(pair+3);value=get(pair-1);assert.equal(get(head-1),NIL);}
   assert.equal(get(key+3),68);assert.equal(get(value+3),116,'population retains values');
  }
  rows.push({site,type,base,collections:3});
 }
}
fs.writeFileSync(process.argv[3],JSON.stringify({status:'PASS',refusals,rows},null,2)+'\n');
