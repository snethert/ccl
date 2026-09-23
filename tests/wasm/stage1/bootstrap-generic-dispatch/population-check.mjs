import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {CollectorOwner} from './runtime/collector-owner.mjs';
const bytes=fs.readFileSync(process.argv[2]),digest=createHash('sha256').update(bytes).digest('hex');
const N=77825,T=77838,PAGE=65536,TCR=1024,ROOT=131064,EXTERNAL=262144,BINDINGS=266240,A=2097152,B=2162688;
let memory;let width=1;
let d,owner,layout;const rows=[];
const get=p=>{d=new DataView(memory.buffer);return d.getUint32(p,true);},put=(p,v)=>{d=new DataView(memory.buffer);d.setUint32(p,v,true);};
const t=o=>get(TCR+o),set=(o,v)=>put(TCR+o,v);
function setup(capacity=256,spaces=[A,B]){
 const regions=[['tcr',TCR,TCR+256],['image',77824,77864],['image',786432,786432+8*Math.ceil((width+1)/2)],['vstack',ROOT,ROOT+32776],['temp',196608,212992],['control',212992,229376],['external',EXTERNAL,EXTERNAL+4096],['bindings',BINDINGS,BINDINGS+4096],['c-stack',1048576,1114112],['root-list',1180000,1184096],['scratch',1200000,1800000]].map(([role,start,end],i)=>({name:role+'-'+i,role,start,end}));
 layout={version:1,collector:'copying',workers:1,egc:false,tcr:TCR,maximumPages:32769,logCapacity:32768,regions,spaces:spaces.map((start,i)=>({name:'heap-'+i,start,end:start+capacity})),groups:['module-constants','callbacks','registry','host'].map((kind,i)=>({kind,slots:[EXTERNAL+4*i]}))};
 for(const r of [...regions,...layout.spaces])new Uint8Array(memory.buffer,r.start,r.end-r.start).fill(0);
 put(N-1,N);put(N+3,N);put(T-6,1850);for(let i=1;i<8;i++)put(T-6+4*i,N);
 // Pinned function object; its environment and literal pool are image roots.
 put(786432,width*256+130);for(let i=0;i<width;i++)put(786436+4*i,N);
 for(const g of layout.groups)for(const p of g.slots)put(p,N);
 set(48,spaces[0]);set(52,spaces[0]+capacity);set(56,spaces[0]);set(68,ROOT+8);set(72,ROOT+32776);set(64,ROOT+8);set(128,ROOT);put(ROOT,0);put(ROOT+4,0);
 set(80,196608);set(76,196608);set(84,212992);set(92,212992);set(88,212992);set(96,229376);set(104,BINDINGS);set(108,0);set(120,ROOT+8200);set(124,ROOT+8264);set(188,N);
 owner=CollectorOwner.create(memory,bytes,digest,layout);return owner;
}
function cons(car,cdr=N){const p=t(48);assert(p+8<=t(52));put(p,cdr);put(p+4,car);set(48,p+8);return p+1;}
function collect(){return owner.atSafepoint(o=>o.collect());}
function poison(from,end){new Uint8Array(memory.buffer,from,end-from).fill(0xdd);}
function pass(name,detail={}){rows.push({name,status:'PASS',...detail});}


for(const base of [A,2147483648]){
 memory=new WebAssembly.Memory({initial:Math.max(48,Math.ceil((base+65536)/PAGE)),maximum:32769,shared:true});
 for(const type of [0,4]){
  width=3;setup(256,[base,base+32768]);
  const child=cons(68),p=t(48);
  [858,0,type,child].forEach((v,i)=>put(p+4*i,v));set(48,p+16);put(EXTERNAL,p+6);
  [858,0,type,child].forEach((v,i)=>put(786432+4*i,v));
  owner=CollectorOwner.create(memory,bytes,digest,layout);
  collect();poison(base,base+256);
  const moved=get(EXTERNAL);assert.notEqual(moved,p+6);
  assert.equal(get(moved-2),0);assert.equal(get(moved+2),type);
  assert.equal(get(get(moved+6)+3),68);
  assert.equal(get(786444),get(moved+6),'pinned and moved population retain one child');
  pass('strong-population',{base,type});
 }
 for(const [name,header,link,type,used] of [
   ['short',602,0,0,16],['termination-shape',1114,0,0,24],
   ['gc-link',858,4,0,16],['type-flags',858,0,8,16],
   ['type-tag',858,0,1,16],['unbacked-tail',858,0,0,8]]){
  width=3;setup(256,[base,base+32768]);
  [header,link,type,N,N,N].forEach((v,i)=>put(base+4*i,v));set(48,base+used);put(EXTERNAL,base+6);
  const before=new Uint8Array(memory.buffer,TCR,256).slice(),objects=new Uint8Array(memory.buffer,base,32).slice();
  assert.throws(collect,/collection refused 2/);
  assert.deepEqual(new Uint8Array(memory.buffer,TCR,256),before);
  assert.deepEqual(new Uint8Array(memory.buffer,base,32),objects);
  assert.equal(get(EXTERNAL),base+6);pass(name,{base});
  width=3;setup(256,[base,base+32768]);
  [header,link,type,N].forEach((v,i)=>put(786432+4*i,v));
  if(name==='unbacked-tail')layout.regions.find(r=>r.start===786432).end=786440;
  assert.throws(()=>CollectorOwner.create(memory,bytes,digest,layout),/image population shape/);
  pass('pinned-'+name,{base});
 }
}
fs.writeFileSync(process.argv[3],JSON.stringify({status:'PASS',checks:rows.length,rows},null,2)+'\n');
