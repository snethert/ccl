import fs from 'node:fs';import assert from 'node:assert/strict';
import {createStrongPopulation,POPULATION_POLICY} from './builder.mjs';
const [dir,output,only='all']=process.argv.slice(2),NIL=77825,tcr=1024,root=131064,config=1200000,result=2048000,rows=[];
for(const base of [262144,2147483648]){
 const memory=new WebAssembly.Memory({initial:Math.max(64,Math.ceil((base+65536)/65536)),maximum:32769,shared:true}),d=new DataView(memory.buffer),put=(p,v)=>d.setUint32(p,v,true),get=p=>d.getUint32(p,true),bytes=(p,n)=>new Uint8Array(memory.buffer,p,n);
 const collector=(await WebAssembly.instantiate(fs.readFileSync(dir+'/collector.wasm'),{env:{memory}})).instance.exports,service=(await WebAssembly.instantiate(fs.readFileSync(dir+'/population.wasm'),{env:{memory}})).instance.exports;
 const setup=()=>{
  bytes(tcr,256).fill(0);bytes(config,96).fill(0);bytes(base,256).fill(0);bytes(3145728,256).fill(0);
  [[48,base+16],[52,base+256],[56,base],[68,root+8],[72,196608],[128,root],[80,700000],[76,700000],[84,900000],[120,100000],[124,100064]].forEach(([o,v])=>put(tcr+o,v));
  put(config,tcr);put(config+16,3145728);put(config+20,3145984);put(config+68,32768);put(config+72,1180000);put(config+80,1800000);put(root,0);put(root+4,1);put(root+8,base+6);
  [602,0,NIL,0].forEach((v,i)=>put(base+4*i,v));bytes(result,16).fill(0xa5);
 };
 if(only==='all'||only==='identity'){
  for(const type of ['list','alist']){setup();const p=createStrongPopulation({memory,base,end:base+16,type,members:[],policy:POPULATION_POLICY});assert.equal(get(base),602,'typed builder');assert.equal(p.representation,'strong-population-v2');
   assert.equal(service.pop_run(p.object,p.end,2,NIL,NIL,0,0,result),0,'typed service');assert.equal(get(result),type==='list'?0:4);assert.equal(collector.collect(config),0,'typed collector');assert.equal(get(get(root+8)-6),602,'typed moved header');rows.push({base,type,status:0});}
  setup();put(base,762);assert.equal(service.pop_run(base+6,base+16,0,NIL,NIL,0,0,result),2,'ordinary vector is not population');assert(bytes(result,16).every(x=>x===0xa5));rows.push({base,ordinaryVectorRefused:true});
 }
 for(const [name,change] of [
  ['native-three',()=>{put(base,858);put(tcr+48,base+16);}],
  ['native-termination',()=>{put(base,1114);put(tcr+48,base+24);}],
  ['truncated',()=>{const p=memory.buffer.byteLength-8;put(p,602);put(p+4,0);put(tcr+56,p);put(tcr+48,p+8);put(tcr+52,p+8);put(root+8,p+6);}],
  ['type-lowbits',()=>put(base+4,1)],
  ['type-flags',()=>put(base+4,8)],
  ['padding',()=>put(base+12,1)],
 ]){if(only!=='all'&&only!==name)continue;
  setup();change();const origin=get(tcr+56),length=get(tcr+52)-origin,before=bytes(origin,length).slice(),saved=bytes(tcr,256).slice(),roots=bytes(root,16).slice();
  let status;try{status=collector.collect(config);}catch(e){assert.fail(name+' trapped '+e);}
  assert.equal(status,2,name);assert.deepEqual(bytes(origin,length),before,name+' source');assert.deepEqual(bytes(tcr,256),saved,name+' TCR');assert.deepEqual(bytes(root,16),roots,name+' roots');rows.push({base,refused:name,status});
 }
}
fs.writeFileSync(output,JSON.stringify({status:'PASS',rows},null,2)+'\n');
