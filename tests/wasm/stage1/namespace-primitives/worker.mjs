import fs from 'node:fs';
import assert from 'node:assert/strict';
import {parentPort,workerData} from 'node:worker_threads';
import {createHash} from 'node:crypto';
import {CollectorOwner} from '../../../../runtime/wasm32/collector-owner.mjs';
import {integerService} from '../../../../runtime/wasm32/integer-service.mjs';
import {floatService} from '../../../../runtime/wasm32/float-service.mjs';
import {pathToFileURL} from 'node:url';
const {fileClient}=await import(workerData.client ? pathToFileURL(workerData.client) : new URL('./client.mjs',import.meta.url));
import {REQUEST,SIZE} from './protocol.mjs';
const {out,base,movement}=workerData,N=77825,T=77838,TCR=1024,ROOT=131064,EXTERNAL=262144,BINDINGS=266240;
const memory=new WebAssembly.Memory({initial:Math.ceil((base+65536)/65536),maximum:32769,shared:true});
const d=new DataView(memory.buffer),get=p=>d.getUint32(p,true),put=(p,v)=>d.setUint32(p,v,true),set=(o,v)=>put(TCR+o,v),t=o=>get(TCR+o);
const read=n=>JSON.parse(fs.readFileSync(out+'/compiled/'+n));
const modules=read('modules.json'),symbols=read('symbols.json'),roots=read('pool-roots.json');
const pool=fs.readFileSync(out+'/compiled/pool.bin');
new Uint8Array(memory.buffer,2097152,pool.length).set(pool);
const symbolWords=new Map(symbols.map((row,i)=>[row.id,786438+32*i]));
const symbolNames=new Map(symbols.map(row=>[symbolWords.get(row.id),row.name]));
put(N-1,N);put(N+3,N);put(T-6,1850);for(let i=1;i<7;i++)put(T-6+4*i,N);put(T-6+28,0);
for(const row of symbols){const p=symbolWords.get(row.id)-6;put(p,1850);for(let i=1;i<7;i++)put(p+4*i,N);put(p+28,0);}
let functions=800000;
function functionObject(id,pool=N){const p=functions;functions+=32;[1578,id*4,N,4,N,N,pool,0].forEach((v,i)=>put(p+4*i,v));return p+6;}
const objects=modules.map((m,i)=>functionObject(i+2,roots[i])),leaf=functionObject(1);
const regions=[['tcr',TCR,TCR+256],['image',77824,77864],['image',786432,786432+32*symbols.length],['image',800000,functions],['image',2097152,2097152+pool.length],['vstack',ROOT,ROOT+32776],['temp',196608,212992],['control',212992,229376],['external',EXTERNAL,EXTERNAL+4096],['bindings',BINDINGS,BINDINGS+4096],['c-stack',1048576,1114112],['root-list',1180000,1184096],['scratch',1200000,1800000]].map(([role,start,end],i)=>({name:role+'-'+i,role,start,end}));
const layout={version:1,collector:'copying',workers:1,egc:false,tcr:TCR,maximumPages:32769,logCapacity:32768,regions,
 spaces:[base,base+32768].map((start,i)=>({name:'heap-'+i,start,end:start+16384})),
 groups:['module-constants','callbacks','registry','host'].map((kind,i)=>({kind,slots:[EXTERNAL+4*i]}))};
for(let i=0;i<4;i++)put(EXTERNAL+4*i,N);
set(0,1);set(8,1);set(32,2);set(48,base);set(52,base+16384);set(56,base);set(68,ROOT+8);set(72,ROOT+32776);set(64,ROOT+8);set(128,ROOT);put(ROOT,0);put(ROOT+4,0);
set(80,196608);set(76,196608);set(84,212992);set(92,212992);set(88,212992);set(96,229376);set(104,BINDINGS);set(108,0);set(120,ROOT+8200);set(124,ROOT+8264);set(188,N);
const bytes=fs.readFileSync(out+'/collector.wasm'),digest=createHash('sha256').update(bytes).digest('hex');
const owner=CollectorOwner.create(memory,bytes,digest,layout);
let collections=0,requests=0;
function collect(){if(movement){const old=t(56),limit=t(52);owner.atSafepoint(o=>o.collect());new Uint8Array(memory.buffer,old,limit-old).fill(0xdd);collections++;}}
function allocate(n){owner.atSafepoint(o=>o.ensure(n));const p=t(48);set(48,p+n);new Uint8Array(memory.buffer,p,n).fill(0);return p;}
const env={memory,tcr:TCR,table:new WebAssembly.Table({element:'anyfunc',initial:64}),tail_table:new WebAssembly.Table({element:'anyfunc',initial:64}),code_registry:4096,
 call_error:new WebAssembly.Tag({parameters:['i32']}),type_error:new WebAssembly.Tag({parameters:['i32','i32']}),nonlocal_exit:new WebAssembly.Tag({parameters:['i32']})};
put(4096,64);put(4100,1);
const binary=name=>fs.readFileSync(out+'/'+name+'.wasm');
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const integer=integerService({memory,tcr:TCR,owner,callError:env.call_error,bytes:binary('integer'),digest:hash(binary('integer')),pinned:regions.filter(r=>r.role==='image')});
const floating=floatService({memory,tcr:TCR,owner,callError:env.call_error,bytes:binary('float'),digest:hash(binary('float')),detectorBytes:binary('detector'),detectorDigest:hash(binary('detector')),pinned:regions.filter(r=>r.role==='image')});

function register(id,x){[id,4,17,23].forEach((v,i)=>put(4104+id*16+i*4,v));env.table.set(id,x.exports.entry);env.tail_table.set(id,x.exports.tail_entry);}
parentPort.postMessage({type:'memory',memory});
const run=fileClient({memory,tcr:TCR,collect,allocate,pinned:regions.filter(r=>r.role==='image'),refuse:reason=>{throw new WebAssembly.Exception(env.call_error,[4]);},post:request=>{requests++;parentPort.postMessage({type:'request',...request});}});
const adapter=new WebAssembly.Instance(new WebAssembly.Module(fs.readFileSync(out+'/adapter.wasm')),{env,files:{run}});register(1,adapter);
const entries=new Map();
for(let i=0;i<modules.length;i++){
 const m=modules[i],imports=Object.fromEntries(m.symbols.map(([wire,id])=>[wire,symbolWords.get(id)]));
 const wasm=new WebAssembly.Module(fs.readFileSync(out+'/compiled/'+m.name+'.wasm'));
 const x=new WebAssembly.Instance(wasm,{env,symbols:{condition_registry:N,error_message:N,expected_function:N,...imports},integer:{calculate:integer},floating:{calculate:floating},owner:{ensure:n=>owner.atSafepoint(o=>o.ensure(n))}});
 register(i+2,x);entries.set(m.definition,{fn:x.exports.entry,self:objects[i]});put(symbolWords.get(m.function)+6,objects[i]);
}
put(symbolWords.get(symbols.find(r=>r.name==='%WASM-FILE-REQUEST').id)+6,leaf);
function string(s){const codes=Array.from(s,c=>c.codePointAt(0)),p=allocate((4+codes.length*4+7)&~7);put(p,(codes.length<<8)|191);codes.forEach((v,i)=>put(p+4+i*4,v));return p+6;}
function vector(n){const p=allocate((4+n+7)&~7);put(p,(n<<8)|199);new Uint8Array(memory.buffer,p+4,n).fill(219);return p+6;}
function decode(v){if(v===N)return null;if(v===T)return true;if(!(v&3))return v>>2;if(symbolNames.has(v))return ':'+symbolNames.get(v);if((v&7)===6&&(get(v-6)&255)===191)return Array.from({length:get(v-6)>>>8},(_,i)=>String.fromCodePoint(get(v-2+4*i))).join('');throw Error('decode '+v);}
const calls={};
function call(name,args){
 const e=entries.get(name);assert(e,name);put(ROOT+4,args.length);args.forEach((v,i)=>put(ROOT+8+i*4,v));set(64,ROOT+8);set(128,ROOT);set(116,0);set(120,ROOT+8200);set(124,ROOT+8264);
 const before=Array.from({length:64},(_,i)=>t(i*4));let result;
 try{result=e.fn(e.self,args.length);}catch(error){if(error.is?.(env.call_error))throw Error(name+': checked '+error.getArg(env.call_error,0));throw error;}
 for(let i=0;i<64;i++)if(![48,52,56,116].includes(i*4))assert.equal(t(i*4),before[i],name+' TCR '+i*4);
 assert.equal(result[1],t(116));assert.equal(result[0]>>>0,get(ROOT+8200));
 calls[name]=(calls[name]||0)+1;
 return Array.from({length:result[1]},(_,i)=>decode(get(ROOT+8200+i*4)));
}
const rows=[],handles=new Map();
function row(op,...args){let value;
 switch(op){
 case 'open':{const [id,path,flags=0]=args;const v=call('FD-OPEN',[string(path),flags*4])[0];handles.set(id,v);value=v>=0?true:v;break;}
 case 'read':{const [id,n]=args,b=vector(n);value=call('FD-READ',[handles.get(id)*4,b,n*4]);const moved=get(ROOT+12),data=Array.from(new Uint8Array(memory.buffer,moved-2,n));value.push(data);break;}
 case 'seek':value=call('FD-LSEEK',[handles.get(args[0])*4,args[1]*4,args[2]*4]);break;
 case 'tell':value=call('FD-TELL',[handles.get(args[0])*4]);break;
 case 'size':value=call('FD-SIZE',[handles.get(args[0])*4]);break;
 case 'close':value=call('FD-CLOSE',[handles.get(args[0])*4]);break;
 case 'realpath':value=call('%REALPATH',[string(args[0])]);break;
 case 'kind':value=call('%UNIX-FILE-KIND',[string(args[0])]);break;
 case 'write':value=call('FD-WRITE',[handles.get(args[0])*4,vector(1),4]);break;
 case 'read-close':{value=call('NAMESPACE-READ-CLOSE',[string(args[0]),vector(8)]);value.push(Array.from(new Uint8Array(memory.buffer,get(ROOT+12)-2,8)));break;}
 case 'unwind-close':{const fd=call('NAMESPACE-UNWIND-CLOSE',[string(args[0])])[0];value=call('FD-CLOSE',[fd*4]);break;}
 case 'effects':{const path=string(args[0]);put(EXTERNAL,path);const p=allocate(8);put(p,N);put(p+4,N);const fd=call('NAMESPACE-OPEN-EFFECTS',[get(EXTERNAL),p+1])[0];const moved=get(ROOT+12);value=[fd>=0,get(moved+3)>>2,get(moved-1)>>2];call('FD-CLOSE',[fd*4]);put(EXTERNAL,N);break;}
 default:throw Error('test operation '+op);
 }
 rows.push({op,args,value});put(ROOT+4,0);set(116,0);return value;
}
for(const [op,...args] of JSON.parse(fs.readFileSync(out+'/cases.json')))row(op,...args);
const refusals=[];
for(const [name,args] of [
 ['FD-READ',[4,N,4]],['FD-READ',[4,vector(8),36]],
 ['FD-LSEEK',[4,0,12]],['FD-OPEN',[N,0]],
 ['FD-CLOSE',[N]],['FD-WRITE',[4,N,4]]]) {
 put(ROOT+4,args.length);args.forEach((v,i)=>put(ROOT+8+i*4,v));set(64,ROOT+8);set(128,ROOT);set(116,0);set(120,ROOT+8200);set(124,ROOT+8264);
 const before=Array.from({length:64},(_,i)=>t(i*4)),sent=requests,e=entries.get(name);
 assert.throws(()=>e.fn(e.self,args.length),error=>error.is?.(env.call_error)&&error.getArg(env.call_error,0)===4,name);
 for(let i=0;i<64;i++)assert.equal(t(i*4),before[i],name+' refusal TCR '+i*4);
 assert.equal(requests,sent,'refused call reached owner');refusals.push(name);
}
assert.equal(Object.keys(calls).length,12,'every generated definition executed');
parentPort.postMessage({type:'done',rows,calls,collections,requests,refusals,placement:base,movement});
