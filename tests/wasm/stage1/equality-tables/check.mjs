import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createStrongEquality,STRONG_POLICY,plannedCapacity} from './owner.mjs';
import {Worker,isMainThread,parentPort,workerData} from 'node:worker_threads';
if(isMainThread){
 const rows=[];
 for(const mode of ['eql','equal'])for(const base of [262144,2147483648])for(const generated of [false,true]){
  rows.push(await new Promise((resolve,reject)=>{const w=new Worker(new URL(import.meta.url),{workerData:{dir:process.argv[2],base,mode,generated}});w.on('message',resolve);w.on('error',reject);w.on('exit',c=>{if(c)reject(Error('Worker '+c));});}));
 }
 fs.writeFileSync(process.argv[3],JSON.stringify({status:'PASS',rows},null,2)+'\n');
}else{
 const {dir,mode,base}=workerData,NIL=77825,T=77838,root=131064,tcr=1024,config=1200000,scratch=1900000,result=2048000,size=32768,space2=3145728;
 const memory=new WebAssembly.Memory({initial:Math.max(64,Math.ceil((base+65536)/65536)),maximum:32769,shared:true});
 const d=new DataView(memory.buffer),get=p=>d.getUint32(p,true),put=(p,v)=>d.setUint32(p,v,true),bytes=(p,n)=>new Uint8Array(memory.buffer,p,n);
 const service=(await WebAssembly.instantiate(fs.readFileSync(dir+'/'+mode+'.wasm'),{env:{memory}})).instance.exports;
 const collector=(await WebAssembly.instantiate(fs.readFileSync(dir+'/collector.wasm'),{env:{memory}})).instance.exports;
 assert.equal(service.ht_kind(),mode==='eql'?1:2);
 const gen=workerData.generated?await(await import('./generated.mjs')).install({dir,memory,tcr,get,put,service,scratch,scratchEnd:scratch+131072,result,collector,config}):null;
 const native=JSON.parse(fs.readFileSync(dir+'/native.json'));let capacity=4;
 put(tcr+48,base);put(tcr+52,base+size);put(tcr+56,base);put(tcr+68,root+8);put(tcr+72,196608);put(tcr+128,root);
 put(root,0);put(tcr+80,700000);put(tcr+76,700000);put(tcr+84,900000);put(tcr+120,100000);put(tcr+124,100064);put(tcr+104,610000);
 put(config,tcr);put(config+16,space2);put(config+20,space2+size);put(config+68,32768);put(config+72,1180000);put(config+80,1800000);
 let opaque=new Map();
 let table=base+6,cursor=base+service.ht_size(capacity),objects=[];
 function alloc(n){const p=cursor;cursor+=Math.ceil(n/8)*8;assert(cursor<get(tcr+52));bytes(p,cursor-p).fill(0);return p;}
 function node(tag,values){const p=alloc(4+4*values.length);put(p,(values.length<<8)|tag);values.forEach((v,i)=>put(p+4+4*i,v));return p+6;}
 function encode(o){
  if('immediate'in o)return o.immediate;
  if('character'in o)return (o.character*256+11)>>>0;
  if('ref'in o){assert(o.ref<objects.length);return objects[o.ref];}
  if('integer'in o){let v=BigInt(o.integer);if(v>=-536870912n&&v<=536870911n)return Number(BigInt.asUintN(32,v*4n));const digits=[];while(true){let low=Number(BigInt.asUintN(32,v));digits.push(low);v>>=32n;if((v===0n&&low<2147483648)||(v===-1n&&low>=2147483648))break;}return node(7,digits);}
  if('single'in o)return node(15,[o.single]);
  if('double'in o)return node(23,[0,...o.double]);
  if('opaque'in o){if(!opaque.has(o.opaque))opaque.set(o.opaque,o.kind==='symbol'?node(58,[NIL,NIL,NIL,NIL,NIL,NIL,0]):node(114,[NIL,NIL]));return opaque.get(o.opaque);}
  if('cons'in o){const car=encode(o.cons[0]),cdr=encode(o.cons[1]),p=alloc(8);put(p,cdr);put(p+4,car);return p+1;}
  if('string'in o)return node(191,o.string);
  if('bits'in o){const p=alloc(4+Math.ceil(o.bits.length/8));put(p,o.bits.length*256+255);o.bits.forEach((v,i)=>bytes(p+4+(i>>3),1)[0]|=v<<(i%8));return p+6;}
  for(const [name,tag]of[['vector',250],['ratio',10],['complex',26]])if(name in o)return node(tag,o[name].map(encode));
  throw Error('descriptor '+JSON.stringify(o));
 }
 for(const o of native.objects)objects.push(encode(o));
 put(tcr+48,cursor);put(root+4,objects.length+1);put(root+8,table);objects.forEach((v,i)=>put(root+12+4*i,v));
 let comparisons=0,collections=0,operations=0;
 function reset(){assert.equal(service.ht_init(table-6,table-6+service.ht_size(capacity),capacity),0);}
 function raw(op,key=NIL,value=NIL){
  bytes(result,16).fill(0x5a);
  assert.equal(service.ht_run(table,table-6+service.ht_size(capacity),op,key,value,scratch,scratch+131072,result),0,'status');
  const r=Array.from({length:4},(_,i)=>get(result+4*i));assert.equal(r[2],op===0?2:1,'count publication');assert([0,1].includes(r[3]),'rehash publication');return r;
 }
 function call(op,key=NIL,value=NIL){operations++;return gen?gen.invoke(op,table,key,value):raw(op,key,value);}
 function move(){
  const before=get(tcr+56);put(tcr+116,0);put(config+16,before===base?space2:base);put(config+20,get(config+16)+size);
  assert.equal(collector.collect(config),0,'collection');table=get(root+8);objects=objects.map((_,i)=>get(root+12+4*i));bytes(before,size).fill(0xda);collections++;
 }
 for(let i=0;i<objects.length;i++)for(let j=0;j<objects.length;j++){
  reset();const equal=native[mode][i][j]===1;
  assert.equal(call(1,objects[i],68)[0],68);
  if((i+j)%3===0)move();
  assert.deepEqual(call(0,objects[j],NIL).slice(0,2),equal?[68,T]:[NIL,NIL],mode+' lookup '+i+','+j);comparisons++;
  assert.equal(call(1,objects[j],84)[0],84);
  assert.equal(call(3)[0],equal?4:8,mode+' replace count '+i+','+j);comparisons++;
  move();assert.deepEqual(call(0,objects[i]).slice(0,2),[equal?84:68,T],mode+' moved lookup '+i+','+j);comparisons++;
  assert.equal(call(2,objects[j])[0],T);
  assert.deepEqual(call(0,objects[i]).slice(0,2),equal?[NIL,NIL]:[68,T],mode+' removal '+i+','+j);comparisons++;
 }
 // Build the actual captured EQL/EQUAL key graphs, including copied EQUAL
 // list spines. Method instances are identity placeholders, not CLOS bodies.
 const bootstrap=[];
 for(const row of native.bootstrap.filter(r=>r.test===mode)){
  assert.equal(row.keys.length,row.count);opaque.clear();cursor=get(tcr+48);
  capacity=2**Math.ceil(Math.log2(Math.max(4,60,row.count+Math.max(16,Math.ceil(row.count/4)))));
  const p=alloc(service.ht_size(capacity));table=p+6;
  const start=objects.length;
  for(const desc of [...row.keys,...row.copies])objects.push(encode(desc));
  put(tcr+48,cursor);put(root+8,table);put(root+4,objects.length+1);objects.forEach((v,i)=>put(root+12+4*i,v));
  const site={id:'captured-'+mode+'-'+row.count,test:mode,weak:'value',size:60,rehashSize:1.5,rehashThreshold:0.7};
  assert.equal(capacity,plannedCapacity(site,row.count));
  createStrongEquality({site,policy:STRONG_POLICY,memory,service,base:p,end:p+service.ht_size(capacity),capacity,liveCount:row.count});
  for(let i=0;i<row.count;i++)call(1,objects[start+i],4*i);
  assert.equal(call(3)[0],4*row.count);
  for(let round=0;round<3;round++){
   move();for(let i=0;i<row.count;i++)assert.deepEqual(call(0,objects[start+row.count+i]).slice(0,2),[4*i,T],'bootstrap lookup');
  }
  bootstrap.push({count:row.count,capacity,collections:3,lookups:row.count*3});
 }
 capacity=4; // use an exactly sized fresh table for the refusal controls
 cursor=get(tcr+48);table=alloc(service.ht_size(4))+6;put(tcr+48,cursor);put(root+8,table);
 // Content padding is not part of EQL(double) or EQUAL(bit-vector) identity.
 const checks=[];
 // Numeric double padding and unused bit-vector bits are deliberately dirty.
 reset();const probe=2300000;
 [((3<<8)|23),0,0,0,((3<<8)|23),0xdeadbeef,0,0].forEach((v,i)=>put(probe+4*i,v));
 raw(1,probe+6,68);assert.deepEqual(raw(0,probe+22).slice(0,2),[68,T],'double ignores padding');checks.push('double-padding');
 if(mode==='equal'){
  put(probe,(9<<8)|255);put(probe+4,0x00000101);put(probe+8,(9<<8)|255);put(probe+12,0xfffffd01);
  reset();raw(1,probe+6,68);assert.deepEqual(raw(0,probe+14).slice(0,2),[68,T],'bit unused bits');checks.push('bit-padding');
 }
 // Full replacement uses the selected equality, not pointer identity.
 reset();raw(1,objects[9],28);for(const k of [4,8,12])raw(1,k,28);
 assert.equal(raw(1,objects[10],44)[0],44,'full equivalent replacement');assert.equal(raw(3)[0],16);checks.push('full-equivalent');
 // Consistently formed duplicate numeric keys must refuse rehash atomically.
 reset();put(table-6+60,objects[9]);put(table-6+64,28);put(table-6+68,objects[10]);put(table-6+72,32);put(table-6+36,8);put(table+2,get(table+2)|2**29);
 const malformed=bytes(table-6,service.ht_size(capacity)).slice();bytes(result,16).fill(0x5a);
 assert.equal(service.ht_run(table,table-6+service.ht_size(capacity),3,NIL,NIL,scratch,scratch+131072,result),2,'duplicate eql rehash');assert.deepEqual(bytes(table-6,malformed.length),malformed);assert(bytes(result,16).every(x=>x===0x5a));checks.push('duplicate-rehash');
 // Owner checks must reject before either service entry runs.
 const site={id:'owner',test:mode,weak:'value',size:60,rehashSize:1.5,rehashThreshold:0.7},cap=plannedCapacity(site,0),ownerBase=2350000;
 const good={site,policy:STRONG_POLICY,memory,service,base:ownerBase,end:ownerBase+64+8*cap,capacity:cap,liveCount:0};
 let calls=0;const spy={ht_kind:()=>service.ht_kind(),ht_size:n=>{calls++;return service.ht_size(n);},ht_init:(...a)=>{calls++;return service.ht_init(...a);}};
 for(const [name,patch]of[
 ['policy',{policy:'unapproved'}],['test',{site:{...site,test:'eq'}}],['kind',{service:{...spy,ht_kind:()=>3}}],
 ['capacity',{capacity:4}],['unmeasured',{liveCount:undefined}],['extent',{end:good.end-8}],['alignment',{base:ownerBase+1}],['stack',{base:1048576,end:1048576+64+8*cap}],
 ]){calls=0;assert.throws(()=>createStrongEquality({...good,service:spy,...patch}));assert.equal(calls,0,'owner before service '+name);checks.push('owner-'+name);}
 assert.throws(()=>createStrongEquality({...good,service:{...spy,ht_size:()=>0}}),/service size/);checks.push('owner-size');
 assert.throws(()=>createStrongEquality({...good,service:{...spy,ht_init:()=>1}}),/construction/);checks.push('owner-status');

 reset();for(let i=0;i<4;i++)call(1,i*4,NIL);
 const before=bytes(table-6,service.ht_size(4)).slice(),pub=bytes(result,16).slice();
 assert.equal(service.ht_run(table,table-6+service.ht_size(4),1,100,28,scratch,scratch+131072,result),4,'full');assert.deepEqual(bytes(table-6,before.length),before);assert.deepEqual(bytes(result,16),pub);checks.push('full-preserves');
 // Every failed key admission precedes table/cache/result publication.
 const badBase=2200000;
 function refuse(name,key,expected=3){const b=bytes(table-6,service.ht_size(4)).slice(),r=bytes(result,16).slice();assert.equal(service.ht_run(table,table-6+service.ht_size(4),0,key,0,scratch,scratch+131072,result),expected,name);assert.deepEqual(bytes(table-6,b.length),b,name);assert.deepEqual(bytes(result,16),r,name);checks.push(name);}
 put(badBase,(3<<8)|15);refuse('single-shape',badBase+6);
 put(badBase,(2<<8)|31);refuse('macptr-outside-scope',badBase+6);
 refuse('sentinel',243);
 const edge=memory.buffer.byteLength-8;put(edge,(100<<8)|191);refuse('unbacked-string',edge+6);
 put(badBase,(3<<8)|23);put(badBase+4,0);put(badBase+8,0);put(badBase+12,0);
 put(result,(3<<8)|23);refuse('publication-alias',result+6);
 if(mode==='equal'){put(badBase,badBase+1);put(badBase+4,28);refuse('cyclic-structural-key',badBase+1);put(scratch,NIL);put(scratch+4,28);refuse('scratch-alias',scratch+1);}
 parentPort.postMessage({mode,base,generated:!!gen,objects:objects.length,comparisons,operations,collections,checks,bootstrap,...(gen?{dispatch:gen.counts()}: {})});
}
