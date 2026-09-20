import fs from 'node:fs';import assert from 'node:assert/strict';
import {CollectorOwner} from './collector-owner.mjs';
import {floatService} from './float-service.mjs';
const dir=process.argv[2],outputFile=process.argv[3],inputs=JSON.parse(fs.readFileSync(dir+'/inputs.json'));
const bytes=fs.readFileSync(dir+'/float.wasm'),detectorBytes=fs.readFileSync(dir+'/detector.wasm'),collector=fs.readFileSync(dir+'/collector.wasm');
const cases=JSON.parse(fs.readFileSync(dir+'/cases.json')),N=77825,T=77838,TCR=1024,BASE=131064,ROOT=131080,IMAGE=786432;
const ops=['add','sub','mul','div','lt','le','eq','ne','ge','gt','single','double'];
let current='setup',memory,d,owner,layout,callError,calculate,collections=0,growths=0,ensures=0;
const rows=[];const get=p=>new DataView(memory.buffer).getUint32(p,true),put=(p,v)=>new DataView(memory.buffer).setUint32(p,v,true),t=o=>get(TCR+o),set=(o,v)=>put(TCR+o,v);
function setup(high=false,capacity=16384,maximumPages=32769){
 memory=new WebAssembly.Memory({initial:high?32769:48,maximum:maximumPages,shared:true});
 const A=high?2147483648:2097152,B=A+32768;
 const regions=[['tcr',TCR,TCR+256],['image',77824,77864],['image',IMAGE,IMAGE+16384],['vstack',BASE,BASE+32776],['temp',196608,212992],['control',212992,229376],['external',262144,266240],['bindings',266240,270336],['c-stack',1048576,1114112],['root-list',1180000,1198000],['scratch',1200000,1800000]].map(([role,start,end],i)=>({name:role+'-'+i,role,start,end}));
 // The image's unused bytes are valid empty conses; object starts are supplied
 // by this fixture owner. They are not arbitrary memory capabilities.
 for(const r of regions)new Uint8Array(memory.buffer,r.start,r.end-r.start).fill(0);
 put(N-1,N);put(N+3,N);put(T-6,1850);for(let i=1;i<8;i++)put(T-6+4*i,N);
 layout={version:1,collector:'copying',workers:1,egc:false,tcr:TCR,maximumPages,logCapacity:32768,regions,spaces:[A,B].map((start,i)=>({name:'heap-'+i,start,end:start+capacity})),groups:['module-constants','callbacks','registry','host'].map(kind=>({kind,slots:[]}))};
 set(48,A);set(52,A+capacity);set(56,A);set(68,BASE+8);set(72,BASE+32776);set(64,ROOT+24);set(128,ROOT);put(BASE,0);put(BASE+4,0);put(ROOT,BASE);put(ROOT+4,4);for(let i=0;i<4;i++)put(ROOT+8+4*i,N);
 set(80,196608);set(76,196608);set(84,212992);set(92,212992);set(88,212992);set(96,229376);set(104,266240);set(108,0);set(120,BASE+8200);set(124,BASE+8264);set(188,N);set(200,7);
 owner=CollectorOwner.create(memory,collector,inputs.collector_sha256,layout);callError=new WebAssembly.Tag({parameters:['i32']});calculate=floatService(options());
 return owner;
}
function options(extra={}){return {memory,tcr:TCR,owner,callError,bytes,digest:inputs.float_sha256,detectorBytes,detectorDigest:inputs.detector_sha256,pinned:[{start:IMAGE,end:IMAGE+16384}],...extra};}
function store(x,start){
 if(x.kind==='integer'){
  let n=BigInt(x.value);if(n>=-536870912n&&n<=536870911n)return {v:Number(BigInt.asUintN(32,n*4n)),size:0};
  let words=1;while(n<-(1n<<BigInt(32*words-1))||n>=(1n<<BigInt(32*words-1)))words++;
  const size=8*Math.ceil((4+4*words)/8);new Uint8Array(memory.buffer,start,size).fill(0);put(start,words*256+7);n=BigInt.asUintN(32*words,n);for(let i=0;i<words;i++){put(start+4+4*i,Number(n&0xffffffffn));n>>=32n;}return {v:start+6,size};
 }
 const wide=x.kind==='64',size=wide?16:8;new Uint8Array(memory.buffer,start,size).fill(0);put(start,wide?791:271);
 const raw=x.bits==='nan'?(wide?0x7ff8000000000000n:0x7fc00000n):BigInt('0x'+x.bits);put(start+(wide?8:4),Number(raw&0xffffffffn));if(wide)put(start+12,Number(raw>>32n));return {v:start+6,size};
}
function decode(v){
 if(v===N)return 'NIL';if(v===T)return 'T';assert.equal(v%8,6,'numeric tag');const h=get(v-6),wide=h===791;assert([271,791].includes(h),'float header');
 const raw=wide?(BigInt(get(v+6))<<32n)|BigInt(get(v+2)):BigInt(get(v-2));
 const exp=wide?0x7ff0000000000000n:0x7f800000n,frac=wide?0xfffffffffffffn:0x7fffffn;
 return (raw&exp)===exp&&(raw&frac)!==0n?'nan':raw.toString(16).padStart(wide?16:8,'0');
}
function reset(row,pinned=false){
 const space=owner.spaces[0];set(48,space.start);set(56,space.start);set(52,space.end);set(128,ROOT);put(ROOT,BASE);put(ROOT+4,4);put(ROOT+16,N);put(ROOT+20,N);set(200,row.mask);
 new Uint8Array(memory.buffer,IMAGE,16384).fill(0);
 let cursor=pinned?IMAGE:space.start;
 for(const [slot,x] of [[ROOT+8,row.a],[ROOT+12,row.b]]){const a=store(x,cursor);cursor+=a.size;put(slot,a.v);}
 if(!pinned)set(48,cursor);
 return {space,cursor};
}
function pack(e){return e.condition|(e.flags<<5)|(e.stage<<10)|(e.a_flags<<12)|(e.b_flags<<17);}
function snapshotOperand(slot){const v=get(slot);if(v%4===0)return {v};const p=v-6,h=get(p),size=h===271?8:h===791?16:8*Math.ceil((4+4*Math.floor(h/256))/8);return {bytes:Buffer.from(new Uint8Array(memory.buffer,p,size))};}
function assertOperand(slot,s){if(s.bytes){const v=get(slot);assert.deepEqual(Buffer.from(new Uint8Array(memory.buffer,v-6,s.bytes.length)),s.bytes,'operand preserved');}else assert.equal(get(slot),s.v);}
function invoke(row){
 const a=snapshotOperand(ROOT+8),b=snapshotOperand(ROOT+12),before=t(48),oldbase=t(56),beforeEnsure=ensures;
 const actual=calculate(ops.indexOf(row.op),ROOT,row.safe);
 assert.equal(actual,pack(row.expected),'packed status');assert.equal(decode(get(ROOT+16)),row.expected.value,'published value');assertOperand(ROOT+8,a);assertOperand(ROOT+12,b);assert.equal(get(ROOT+20),N,'padding root');assert.equal(t(128),ROOT,'root head');assert.equal(get(ROOT),BASE,'previous root');assert.equal(get(ROOT+4),4,'root count');assert.equal(t(200),row.mask,'FP control preserved');
 const size=row.expected.condition||row.expected.width===0?0:row.expected.width===32?8:16;
 assert.equal(ensures-beforeEnsure,size?1:0,'only allocated results assure');if(size){assert.equal(get(ROOT+16),t(48)-size+6,'current heap publication');}else assert.equal(t(48),before,'no allocation for condition/boolean');
 return {size,moved:oldbase!==t(56)};
}
try{
 for(const high of [false,true])for(const pressure of [false,true]){
  setup(high);let copies=0,ensureCount=0;const ensure=owner.ensure.bind(owner);
  owner.ensure=n=>{ensures++;ensureCount++;if(pressure){const old=t(56),end=t(52);owner.collect();collections++;copies++;new Uint8Array(memory.buffer,old,end-old).fill(0xdd);}return ensure(n);};
  for(let i=0;i<cases.length;i++){
   const row=cases[i];current=`${row.name}/${high?'high':'low'}/${pressure?'moving':'plain'}`;
   reset(row,i%7===0);invoke(row);
  }
  rows.push({name:current,comparisons:cases.length,collections:copies,ensures:ensureCount});
 }
 // Minimum heap: both operands stay live while collection and growth occur.
 const row={name:'growth',op:'add',a:{kind:'64',bits:'3ff0000000000000'},b:{kind:'64',bits:'4000000000000000'},mask:7,safe:1,expected:{width:64,value:'4008000000000000',flags:0,condition:0,stage:3,a_flags:0,b_flags:0}};
 for(const high of [false]){
  current='growth/'+high;setup(high,32);reset(row);const before=memory.buffer.byteLength,old=owner.view;const ensure=owner.ensure.bind(owner);owner.ensure=n=>{ensures++;const r=ensure(n);assert(r.grown,'real growth');growths++;return r;};invoke(row);assert(memory.buffer.byteLength>before);assert.notEqual(owner.view,old);
  // Once published, the result itself must survive another complete collection.
  owner.atSafepoint(o=>o.collect());assert.equal(decode(get(ROOT+16)),row.expected.value);rows.push({name:current,grown:true,resultMoved:true});
 }
 // A failed assurance may already have moved operands; never publish a result.
 current='failure-after-movement';setup(false,32,48);reset(row);const before=[snapshotOperand(ROOT+8),snapshotOperand(ROOT+12)],base=t(56);
 assert.throws(()=>calculate(0,ROOT,1),e=>e instanceof WebAssembly.Exception&&e.is(callError)&&e.getArg(callError,0)===6);
 assert.notEqual(t(56),base);assertOperand(ROOT+8,before[0]);assertOperand(ROOT+12,before[1]);assert.equal(get(ROOT+16),N);rows.push({name:current,code:6,moved:true});
 // Reuse each collected result as the next call's operand, then move again.
 current='result-chain';setup(false,64);reset(row);const chainEnsure=owner.ensure.bind(owner);
 owner.ensure=n=>{ensures++;owner.collect();return chainEnsure(n);};
 for(const [op,bits,answer] of [['add','4000000000000000','4008000000000000'],['mul','4010000000000000','4028000000000000'],['sub','3fe0000000000000','4027000000000000']]){
  const rhs=store({kind:'64',bits},IMAGE);put(ROOT+12,rhs.v);put(ROOT+16,N);
  const r={...row,op,b:{kind:'64',bits},expected:{...row.expected,value:answer}};
  invoke(r);owner.atSafepoint(o=>o.collect());assert.equal(decode(get(ROOT+16)),answer);put(ROOT+8,get(ROOT+16));
 }rows.push({name:current,steps:3});
 // Live changes to the TCR mask on the same capability, not a factory snapshot.
 current='live-mask';setup();const divide={...row,op:'div',b:{kind:'64',bits:'0000000000000000'}};const ensure=owner.ensure.bind(owner);owner.ensure=n=>{ensures++;return ensure(n);};
 for(const mask of [0,2,0,31,7]){
  const r={...divide,mask,expected:{width:64,value:mask&2?'NIL':'7ff0000000000000',flags:2,condition:mask&2?2:0,stage:3,a_flags:0,b_flags:0}};reset(r);invoke(r);
 }rows.push({name:current,checks:5});
 function refusal(name,damage,code=41,action=()=>calculate(0,ROOT,1)){
  current=name;setup();reset(row);damage();const before=Buffer.from(new Uint8Array(memory.buffer));assert.throws(action,e=>e instanceof WebAssembly.Exception&&e.is(callError)&&e.getArg(callError,0)===code,name);assert.deepEqual(Buffer.from(new Uint8Array(memory.buffer)),before,name+' memory unchanged');rows.push({name,code});
 }
 refusal('bad-root-count',()=>put(ROOT+4,3));refusal('bad-root-head',()=>set(128,BASE));refusal('dirty-result',()=>put(ROOT+16,0));refusal('dirty-padding',()=>put(ROOT+20,0));refusal('unknown-FP-mode',()=>set(200,32));
 refusal('bad-operation',()=>{},41,()=>calculate(12,ROOT,1));refusal('bad-safety',()=>{},41,()=>calculate(0,ROOT,2));refusal('unaligned-root',()=>{},41,()=>calculate(0,ROOT+4,1));refusal('outside-root',()=>{},41,()=>calculate(0,0,1));
 refusal('bad-tag',()=>put(ROOT+8,N),42);refusal('outside-object',()=>put(ROOT+8,999998),42);refusal('bad-header',()=>put(t(56),258),42);refusal('truncated-double',()=>set(48,t(56)+8),42);refusal('redundant-integer',()=>{put(t(56),519);put(t(56)+4,1);put(t(56)+8,0);},42);
 refusal('integer-only',()=>{put(ROOT+8,4);put(ROOT+12,8);},45);
 refusal('nested-owner',()=>{},6,()=>owner.atSafepoint(()=>calculate(0,ROOT,1)));
 refusal('bad-root-end',()=>set(72,ROOT+16));
 refusal('operand-in-stack',()=>put(ROOT+8,ROOT+6),42);
 current='no-room-owner';setup(false,32);reset(row);owner.ensure=()=>({collected:false});assert.throws(()=>calculate(0,ROOT,1),e=>e instanceof WebAssembly.Exception&&e.is(callError)&&e.getArg(callError,0)===6);assert.equal(get(ROOT+16),N);rows.push({name:current});
 current='busy-reentry';setup();reset(row);const saved=owner.ensure.bind(owner);owner.ensure=n=>{assert.throws(()=>calculate(0,ROOT,1),e=>e instanceof WebAssembly.Exception&&e.is(callError)&&e.getArg(callError,0)===41);return saved(n);};calculate(0,ROOT,1);rows.push({name:current});
 current='unary-ignores-second';setup();reset(row);put(ROOT+12,N);calculate(10,ROOT,1);assert.equal(decode(get(ROOT+16)),'3f800000');rows.push({name:current});
 current='recover-after-refusal';setup();reset(row);put(ROOT+8,N);assert.throws(()=>calculate(0,ROOT,1));reset(row);calculate(0,ROOT,1);assert.equal(decode(get(ROOT+16)),row.expected.value);rows.push({name:current});
 for(const [name,change,why] of [['bad-service-digest',{digest:'0'.repeat(64)},'FLOAT_CAPABILITY'],['bad-detector-digest',{detectorDigest:'0'.repeat(64)},'FLOAT_CAPABILITY'],['foreign-tcr',{tcr:TCR+16},'FLOAT_CAPABILITY'],['foreign-memory',{memory:new WebAssembly.Memory({initial:48,maximum:32769,shared:true})},'FLOAT_CAPABILITY'],['service-imports',{bytes:detectorBytes,digest:inputs.detector_sha256},'FLOAT_IMPORTS'],['invalid-pinned',{pinned:[{start:1,end:9}]},'FLOAT_PINNED']]){current=name;setup();assert.throws(()=>floatService(options(change)),new RegExp(why));rows.push({name});}
 fs.writeFileSync(outputFile,JSON.stringify({status:'PASS',comparisons:cases.length*4,collections,growths,rows},null,2)+'\n');
}catch(e){fs.writeFileSync(outputFile,JSON.stringify({status:'FAIL',case:current,message:e.message??String(e),code:e instanceof WebAssembly.Exception&&e.is(callError)?e.getArg(callError,0):null},null,2)+'\n');throw e;}
