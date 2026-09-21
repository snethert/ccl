import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createStrongEQ,strongPlan,STRONG_POLICY} from './policy.mjs';
const dir=process.argv[2],sites=JSON.parse(fs.readFileSync(dir+'/selection.json'));
const hash=await WebAssembly.compile(fs.readFileSync(dir+'/hash.wasm'));
const collector=await WebAssembly.compile(fs.readFileSync(dir+'/collector.wasm'));
let plans=0,refusals=0,collections=0;const rows=[];
for(const site of sites){
 const p=strongPlan(site,STRONG_POLICY);assert.equal(p.test,site.test,'equality preserved');assert.equal(p.weak,null,'strong plan');
 assert.equal(p.requestedWeak,site.weak);assert.equal(p.size,site.size);assert.equal(p.rehashSize,site.rehashSize);assert.equal(p.rehashThreshold,site.rehashThreshold);assert(Object.isFrozen(p));
 assert.throws(()=>strongPlan(site,null),/explicit policy/,'consent');refusals++;plans++;
}
for(const base of [262144,2147483648]){
 const memory=new WebAssembly.Memory({initial:Math.max(64,Math.ceil((base+32768)/65536)),maximum:32769,shared:true});
 const view=new DataView(memory.buffer),get=p=>view.getUint32(p,true),put=(p,n)=>view.setUint32(p,n,true);
 const service=(await WebAssembly.instantiate(hash,{env:{memory}})).exports,copy=(await WebAssembly.instantiate(collector,{env:{memory}})).exports;
 const tcr=1024,root=131064,cfg=1200000,scratch=1900000,result=2048000,other=3145728,size=32768,NIL=77825;
 for(const [ordinal,site] of sites.entries()){
  new Uint8Array(memory.buffer,base,size).fill(0xa5);
  const capacity=2**Math.ceil(Math.log2(Math.max(4,site.size))),bytes=64+8*capacity;
  const args={site,policy:STRONG_POLICY,memory,service,base,end:base+bytes,capacity};
  if(site.test!=='eq'){
   const before=new Uint8Array(memory.buffer,base,size).slice();assert.throws(()=>createStrongEQ(args),/equality service not installed/,'non-EQ admission');assert.deepEqual(new Uint8Array(memory.buffer,base,size),before);refusals++;continue;
  }
  for(const [name,changes] of [['policy',{policy:null}],['extent',{end:base+bytes+8}],['short capacity',{capacity:1}],['size',{site:{...site,size:capacity+1}}]]){
   const before=new Uint8Array(memory.buffer,base,size).slice();let entered=0;const guarded={ht_size:service.ht_size,ht_init:(...a)=>{entered++;return service.ht_init(...a);}};assert.throws(()=>createStrongEQ({...args,...changes,service:guarded}),undefined,name+' refusal');assert.equal(entered,0,name+' refusal before service');assert.deepEqual(new Uint8Array(memory.buffer,base,size),before,name+' no writes');refusals++;
  }
  let table=createStrongEQ(args).table;assert.equal(get(table+2),1<<30,'strong flags');
  new Uint8Array(memory.buffer,tcr,256).fill(0);new Uint8Array(memory.buffer,cfg,96).fill(0);
  put(tcr+48,base+bytes);put(tcr+52,base+size);put(tcr+56,base);put(tcr+68,root+8);put(tcr+72,196608);put(tcr+128,root);put(root,0);put(root+4,1);put(root+8,table);
  put(tcr+80,700000);put(tcr+76,700000);put(tcr+84,900000);put(tcr+120,100000);put(tcr+124,100064);put(tcr+104,610000);put(tcr+108,0);
  put(cfg,tcr);put(cfg+68,32768);put(cfg+72,1180000);put(cfg+80,1800000);
  const cons=n=>{const p=get(tcr+48);put(p,NIL);put(p+4,n*4);put(tcr+48,p+8);return p+1;};
  const key=cons(ordinal+1),value=cons(ordinal+101);cons(999); // unrooted garbage
  assert.equal(service.ht_run(table,table-6+bytes,1,key,value,scratch,scratch+131072,result),0);
  // Only the table is a collector root. JS locals are intentionally not roots.
  for(let pass=0;pass<3;pass++){
   const from=get(tcr+56),to=from===base?other:base;put(cfg+16,to);put(cfg+20,to+size);
   assert.equal(copy.collect(cfg),0,'strong collection');collections++;table=get(root+8);
   assert.equal(get(cfg+84),3,'three live objects');assert.equal(get(tcr+48)-get(tcr+56),bytes+16,'table alone retains key and value');assert.equal(get(cfg+92),pass===0?8:0,'garbage accounting');
   new Uint8Array(memory.buffer,from,size).fill(0xda);
   let found=[];for(let i=0;i<capacity;i++){const p=table-6+60+8*i,k=get(p);if(k!==243&&k!==251)found.push([k,get(p+4)]);}
   assert.equal(found.length,1);const [k,v]=found[0];assert.equal(get(k+3),(ordinal+1)*4);assert.equal(get(v+3),(ordinal+101)*4);
   assert.equal(service.ht_run(table,table-6+bytes,0,k,NIL,scratch,scratch+131072,result),0);assert.deepEqual([get(result),get(result+4),get(result+8)],[v,77838,2],'lookup after movement');
   assert.equal(get(table+2),1<<30,'rehash leaves strong flags');
  }
  rows.push({site:site.id,base,capacity,collections:3,retention:'keys-and-values'});
 }
}
fs.writeFileSync(process.argv[3],JSON.stringify({status:'PASS',plans,refusals,collections,rows},null,2)+'\n');
