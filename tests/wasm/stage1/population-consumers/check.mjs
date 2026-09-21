import fs from 'node:fs';import assert from 'node:assert/strict';
import {Worker,isMainThread,parentPort,workerData} from 'node:worker_threads';
import {createStrongPopulation,POPULATION_POLICY} from './builder.mjs';import {install} from './install.mjs';
if(isMainThread){
 const rows=[];for(const base of [262144,2147483648])rows.push(await new Promise((ok,no)=>{const w=new Worker(new URL(import.meta.url),{workerData:{base,dir:process.argv[2]}});w.on('message',ok);w.on('error',no);w.on('exit',c=>{if(c)no(Error('Worker '+c));});}));
 fs.writeFileSync(process.argv[3],JSON.stringify({status:'PASS',rows},null,2)+'\n');
}else{
 const {base,dir}=workerData,NIL=77825,T=77838,tcr=1024,root=131064,config=1200000,result=2048000,size=32768,space2=3145728;
 const memory=new WebAssembly.Memory({initial:Math.max(64,Math.ceil((base+65536)/65536)),maximum:32769,shared:true});
 const d=new DataView(memory.buffer),get=p=>d.getUint32(p,true),put=(p,n)=>d.setUint32(p,n,true),bytes=(p,n)=>new Uint8Array(memory.buffer,p,n);
 const service=(await WebAssembly.instantiate(fs.readFileSync(dir+'/population.wasm'),{env:{memory}})).instance.exports;
 const collector=(await WebAssembly.instantiate(fs.readFileSync(dir+'/collector.wasm'),{env:{memory}})).instance.exports;
 const gen=await install({dir,memory,tcr,get,put,service,collector,config,result}),native=JSON.parse(fs.readFileSync(dir+'/native.json')),rows=[];
 function decode(v,depth=0){assert(depth<100,'finite result');if(v===NIL)return 'nil';if(v===T)return 't';for(const [k,x]of Object.entries(gen.keywords))if(v===x)return k;if((v&3)===0)return (v|0)>>2;if((v&7)===1)return [decode(get(v+3),depth+1),decode(get(v-1),depth+1)];throw Error('result tag '+v);}
 for(const expected of native){
  bytes(tcr,256).fill(0);bytes(config,96).fill(0);bytes(base,size).fill(0);bytes(space2,size).fill(0);
  for(const [o,v] of [[48,base],[52,base+size],[56,base],[68,root+8],[72,196608],[128,root],[80,700000],[76,700000],[84,900000],[120,100000],[124,100064],[104,610000]])put(tcr+o,v);
  put(config,tcr);put(config+16,space2);put(config+20,space2+size);put(config+68,32768);put(config+72,1180000);put(config+80,1800000);
  const a=base+1,b=base+9,log=base+17;[[0,92],[4,68],[8,148],[12,124],[16,0],[20,0]].forEach(([o,v])=>put(base+o,v));
  const start=base+24,p=createStrongPopulation({memory,base:start,end:start+32,type:expected.type,members:expected.type==='list'?[a,b]:[[a,b]],policy:POPULATION_POLICY}).object;
  put(tcr+48,start+32);put(root,0);put(root+4,4);[p,a,b,log].forEach((v,i)=>put(root+8+4*i,v));
  const values=gen.invoke(expected.name,[p,a,b,log]).map(v=>decode(v)),now=get(root+8),actual={name:expected.name,type:expected.type,values,contents:decode(get(now+2)),log:decode(get(root+20))};
  assert.deepEqual(actual,expected,expected.name+' native '+expected.type);
  // Discard all roots except the population and log, then collect and re-read.
  put(root+4,2);put(root+12,get(root+20));const old=get(tcr+56);put(config+16,old===base?space2:base);put(config+20,get(config+16)+size);
  assert.equal(collector.collect(config),0,expected.name+' population-only collect');bytes(old,size).fill(0xda);
  const moved=gen.invoke('pop_contents',[get(root+8)]);assert.deepEqual(decode(moved[0]),expected.contents,expected.name+' post-move contents');
  assert.deepEqual(decode(get(root+12)),expected.log,expected.name+' post-move log');rows.push({name:expected.name,type:expected.type,values:actual.values,contents:actual.contents,log:actual.log,internalCollection:['pc_collect','pc_closure','pc_cleanup','pc_exit'].includes(expected.name),externalCollection:true});
 }
 parentPort.postMessage({base,comparisons:rows.length,rows,...gen.summary()});
}
