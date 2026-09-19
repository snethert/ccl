import fs from 'node:fs';
import assert from 'node:assert/strict';
const memory=new WebAssembly.Memory({initial:64,maximum:32769,shared:true});
memory.grow(32705);
const d=new DataView(memory.buffer),load=p=>d.getUint32(p,true),store=(p,v)=>d.setUint32(p,v>>>0,true);
const wasm=await WebAssembly.instantiate(fs.readFileSync(process.argv[2]),{env:{memory}});
const config=1200000,TCR=1024,ROOT=65536,STACK_END=98304,EXTRA=1180000,NIL=77825;
const check=(c,m)=>assert(c,m);
let tests=[];
function setup(from=262144,to=3145728,bytes=32768){
 new Uint8Array(memory.buffer,TCR,256).fill(0);new Uint8Array(memory.buffer,config,96).fill(0);
 new Uint8Array(memory.buffer,from,bytes).fill(0xcd);new Uint8Array(memory.buffer,to,bytes).fill(0xa5);
 store(TCR+48,from);store(TCR+52,from+bytes);store(TCR+56,from);
 store(TCR+68,ROOT+8);store(TCR+72,STACK_END);store(TCR+128,ROOT);store(ROOT,0);store(ROOT+4,0);
 store(TCR+80,700000);store(TCR+76,700000);store(TCR+120,100000);store(TCR+124,100064);
 store(TCR+104,610000);store(TCR+108,0);
 store(config,TCR);
 store(config+16,to);store(config+20,to+bytes);store(config+68,32768);store(config+72,EXTRA);store(config+76,0);store(config+80,1800000);
}
function alloc(words,tag=1){const p=load(TCR+48),size=8*Math.ceil(4*words.length/8);words.forEach((v,i)=>store(p+4*i,v));for(let n=words.length*4;n<size;n+=4)store(p+n,0);store(TCR+48,p+size);return p+tag;}
function roots(values){store(ROOT+4,values.length);values.forEach((v,i)=>store(ROOT+8+4*i,v));}
function run(name){const before=load(TCR+48)-load(TCR+56);assert.equal(wasm.instance.exports.collect(config),0,name);const live=load(TCR+48)-load(TCR+56);assert.equal(load(config+92),before-live,name+': reclamation accounting');tests.push({name,objects:load(config+84),roots:load(config+88),reclaimed:before-live});return live;}
for(const from of [262144,2147483648]){
 setup(from);const a=alloc([NIL,28]),b=alloc([a,a]);store(a-1,b);alloc([4,8]);roots([a,b,a,NIL,0xfffffffc]);assert.equal(run('cycle-sharing-'+from),16);assert.notEqual(load(ROOT+8),a,'roots actually moved');const x=load(ROOT+8),y=load(ROOT+12);assert.equal(load(ROOT+16),x);assert.equal(load(x-1),y,'cycle-sharing edges');assert.equal(load(y-1),x);assert.equal(load(y+3),x);assert.equal(load(ROOT+20),NIL);assert.equal(load(ROOT+24),0xfffffffc);
 // A second collection moves back into the original space, preserving identity.
 store(config+16,from);store(config+20,from+32768);run('second-space-'+from);assert.equal(load(load(ROOT+8)-1),load(ROOT+12));
 setup(from);const dead=alloc([NIL,68]),v=alloc([3*256+250,dead,dead,NIL],6),f=alloc([1578,4,v,4,NIL,NIL,v,0],6);roots([f]);run('function-vector-'+from);const fn=load(ROOT+8),env=load(fn+2),pool=load(fn+18);assert.equal(env,pool);assert.equal(load(env-2),load(env+2));
 setup(from);const junk=alloc([NIL,76]),str=alloc([2*256+191,junk,junk,0],6);roots([str]);assert.equal(run('raw-payload-not-roots-'+from),16,'raw-payload-not-roots');assert.equal(load(load(ROOT+8)-2),junk);assert.equal(load(config+84),1);
 setup(from);const z=alloc([NIL,84]),tlb=alloc([3*256+250,243,z,243],6);store(TCR+104,tlb-2);store(TCR+108,3);roots([]);assert.equal(run('raw-interior-tlb-'+from),24);assert.notEqual(load(TCR+104),tlb-2,'raw interior root moved');assert.equal(load(load(TCR+104)+4)-1,load(TCR+56)+16);assert.equal(load(load(load(TCR+104)+4)+3),84);
 setup(from);const q=alloc([NIL,92]);roots([]);store(ROOT+4,0xffffffff);store(ROOT+8,ROOT+32);store(ROOT+12,1);store(ROOT+32,q);run('inline-descriptor-'+from);assert.equal(load(load(ROOT+32)+3),92);
 setup(from);const k=alloc([NIL,100]);roots([]);store(ROOT+4,0xffffffff);store(ROOT+8,700016);store(ROOT+12,1);store(TCR+76,700032);store(700016,k);run('arena-descriptor-'+from);assert.equal(load(load(700016)+3),100);
 setup(from);const t=alloc([NIL,108]);roots([]);store(TCR+116,1);store(100000,t);store(100004,from+9);run('result-count-not-capacity-'+from);assert.equal(load(load(100000)+3),108);assert.equal(load(100004),from+9);
 setup(from);const nonroot=alloc([NIL,999*4]);roots([]);store(TCR,nonroot);assert.equal(run('raw-tcr-not-root-'+from),0);assert.equal(load(TCR),nonroot);
 setup(from);const split=alloc([NIL,508]);roots([split]);store(ROOT,ROOT+64);store(ROOT+64,0);store(ROOT+68,1);store(ROOT+72,split);run('nonmonotonic-root-chain-'+from);assert.equal(load(ROOT+8),load(ROOT+72));
 for(const [tag,count,words] of [[215,0,[]],[223,0,[]],[231,0,[0]],[215,5,[1,2,3]],[223,5,[4,5,6]],[231,2,[0,7,8,9,10]],[7,2,[from+1,from+6]],[15,1,[from+1]]]){setup(from);const rawObject=alloc([count*256+tag,...words],6),bytes=load(TCR+48)-from,original=new Uint8Array(memory.buffer,from,bytes).slice();roots([rawObject]);assert.equal(run('raw-width-'+tag+'-'+from),bytes,'D1 raw object extent');assert.deepEqual(new Uint8Array(memory.buffer,load(ROOT+8)-6,bytes),original,'all raw payload bytes');}
 setup(from);const empty=alloc([191,0],6);roots([empty]);assert.equal(run('empty-string-'+from),8);
 setup(from);const raw=alloc([3*256+23,0,from+1,from+6],6);roots([raw]);assert.equal(run('double-bits-'+from),16);assert.equal(load(load(ROOT+8)+2),from+1);
 setup(from);const e=alloc([NIL,116]);roots([]);store(EXTRA,600000);store(config+76,1);store(600000,e);run('owner-registry-'+from);assert.equal(load(load(600000)+3),116);
 setup(from);const cap=alloc([NIL,124]),heapEnv=alloc([506,cap],6);const tmp=ROOT+128;store(tmp,1578);store(tmp+4,4);store(tmp+8,heapEnv);store(tmp+12,4);store(tmp+16,NIL);store(tmp+20,NIL);store(tmp+24,NIL);store(tmp+28,0);roots([tmp+6]);run('stack-callable-'+from);assert.equal(load(ROOT+8),tmp+6);assert.equal(load(load(load(tmp+8)-2)+3),124);
 {setup(from);const cell=alloc([NIL,132]),fn=ROOT+128,env=ROOT+192;store(fn,1578);[4,env+6,4,NIL,NIL,NIL,0].forEach((x,i)=>store(fn+4+4*i,x));store(env,506);store(env+4,cell);roots([fn+6]);run('stack-environment-'+from);assert.notEqual(load(env+4),cell,'stack capture cell moved');assert.equal(load(load(env+4)+3),132);}
}
// Deterministic graph independent of collector enumeration: JS reachability is
// derived from the declared objects, and expected links are compared by identity.
let seed=0x81726354;const rng=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed;};
for(let trial=0;trial<20;trial++){
 setup();const graph=Array.from({length:100},()=>[rng()%100,rng()%100]);const ps=graph.map(()=>alloc([NIL,NIL]));graph.forEach((row,i)=>{store(ps[i]-1,ps[row[0]]);store(ps[i]+3,ps[row[1]]);});const live=new Set(),pending=[0];while(pending.length){let i=pending.pop();if(!live.has(i)){live.add(i);pending.push(...graph[i]);}}
 roots([ps[0]]);run('graph-'+trial);assert.equal(load(config+84),live.size);
 const mapping=new Map([[0,load(ROOT+8)]]),todo=[0];while(todo.length){const i=todo.pop(),p=mapping.get(i);for(let j=0;j<2;j++){const target=graph[i][j],actual=load(p-1+j*4);if(mapping.has(target))assert.equal(actual,mapping.get(target));else{mapping.set(target,actual);todo.push(target);}}}assert.equal(new Set(mapping.values()).size,live.size);
}
for(const [name,damage,code] of [
 ['to-space-reference',()=>store(ROOT+8,load(config+16)+1),3],
 ['tlb-count-overflow',()=>store(TCR+108,0x1000003),5],
 ['capacity',()=>store(config+20,load(config+16)),4],
 ['interior',()=>store(ROOT+8,load(TCR+56)+9),3],
 ['tag-mismatch',()=>store(ROOT+8,load(TCR+56)+6),3],
 ['root-cycle',()=>store(ROOT,ROOT),5],
 ['root-overflow',()=>store(ROOT+4,0xfffffffe),5],
 ['workspace',()=>store(config+68,0),6],
 ['unknown-header',()=>store(load(TCR+56),258),2],
]){
 setup();const p=alloc([NIL,4]);roots([p]);damage();const from=load(TCR+56),old=new Uint8Array(memory.buffer,from,8).slice(),stack=new Uint8Array(memory.buffer,ROOT,64).slice(),tcr=new Uint8Array(memory.buffer,TCR,256).slice();assert.equal(wasm.instance.exports.collect(config),code,name);assert.deepEqual(new Uint8Array(memory.buffer,from,8),old,name+': source unchanged');assert.deepEqual(new Uint8Array(memory.buffer,ROOT,64),stack,name+': roots unchanged');assert.deepEqual(new Uint8Array(memory.buffer,TCR,256),tcr,name+': TCR unchanged');tests.push({name,status:'REFUSED',code});
}
fs.writeFileSync(process.argv[3],JSON.stringify({status:'PASS',tests},null,2)+'\n');console.log('PASS',tests.length,'collector core checks');
