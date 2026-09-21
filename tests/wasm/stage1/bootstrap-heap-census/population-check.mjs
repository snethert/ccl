import fs from 'node:fs';import assert from 'node:assert/strict';
import {createStrongPopulation,POPULATION_POLICY} from './population.mjs';
const dir=process.argv[2],census=JSON.parse(fs.readFileSync(dir+'/census.json'));
const mod=await WebAssembly.compile(fs.readFileSync(dir+'/collector.wasm'));
let rows=[];
for(const base of [262144,2147483648]){
 const memory=new WebAssembly.Memory({initial:Math.max(64,(base+65536)/65536),maximum:32769,shared:true});
 const collector=(await WebAssembly.instantiate(mod,{env:{memory}})).exports;
 const v=new DataView(memory.buffer),get=p=>v.getUint32(p,true),put=(p,x)=>v.setUint32(p,x,true);
 const tcr=1024,root=131064,cfg=1200000,other=3145728,size=65536,NIL=77825;
 for(const record of census.populations){
  if(record.type&65536){assert.equal(record.disposition,'BLOCKS_BOOTSTRAP_TERMINATION_SERVICE');rows.push({id:record.id,base,status:'BLOCKED_TERMINATION',collections:0});continue;}
  assert.equal(record.type,0,'captured ordinary population type');const count=record.count;
  new Uint8Array(memory.buffer,base,size).fill(0);new Uint8Array(memory.buffer,tcr,256).fill(0);new Uint8Array(memory.buffer,cfg,96).fill(0);
  const members=Array.from({length:count},(_,i)=>{put(base+8*i,NIL);put(base+8*i+4,4*(i+1));return base+8*i+1;});
  const start=base+8*count,end=start+16+8*count;
  let p=createStrongPopulation({memory,base:start,end,type:'list',members,policy:POPULATION_POLICY}).object;
  members.fill(NIL);put(end,NIL);put(end+4,396);
  put(tcr+48,end+8);put(tcr+52,base+size);put(tcr+56,base);put(tcr+68,root+8);put(tcr+72,196608);put(tcr+128,root);put(root,0);put(root+4,1);put(root+8,p);
  put(tcr+80,700000);put(tcr+76,700000);put(tcr+84,900000);put(tcr+120,100000);put(tcr+124,100064);put(tcr+104,610000);
  put(cfg,tcr);put(cfg+68,32768);put(cfg+72,1180000);put(cfg+80,1800000);
  for(let pass=0;pass<3;pass++){
   const from=get(tcr+56),to=from===base?other:base;put(cfg+16,to);put(cfg+20,to+size);assert.equal(collector.collect(cfg),0);p=get(root+8);
   assert.equal(get(tcr+48)-get(tcr+56),16+16*count,'population live bytes');assert.equal(get(cfg+84),1+2*count);assert.equal(get(cfg+92),pass===0?8:0);
   new Uint8Array(memory.buffer,from,size).fill(0xda);assert.equal(get(p-6),762);assert.equal(get(p-2),0);assert.equal(get(p+6),0,'population padding');
   let head=get(p+2);for(let i=0;i<count;i++){assert.notEqual(head,NIL);assert.equal(get(get(head+3)+3),4*(i+1),'population member/order');head=get(head-1);}assert.equal(head,NIL,'population length');
  }
  rows.push({id:record.id,base,count,collections:3,status:'PASS'});
 }
 // An out-of-memory span must refuse before the first store, even if its
 // vector and first cons would individually fit. This isolates the guard.
 const start=memory.buffer.byteLength-24,before=new Uint8Array(memory.buffer,start,24).slice();
 assert.throws(()=>createStrongPopulation({memory,base:start,end:start+32,type:'list',members:[NIL,NIL],policy:POPULATION_POLICY}),/population extent/);
 assert.deepEqual(new Uint8Array(memory.buffer,start,24),before,'population bound preserves prefix');
}
fs.writeFileSync(process.argv[3],JSON.stringify({status:'PASS',rows,collections:rows.reduce((n,r)=>n+r.collections,0)},null,2)+'\n');
