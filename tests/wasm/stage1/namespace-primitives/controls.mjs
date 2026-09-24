import fs from 'node:fs';
import assert from 'node:assert/strict';
import {pathToFileURL} from 'node:url';
import {fileClient} from './client.mjs';
import {serviceRequest} from './host.mjs';
import {REQUEST,SIZE,views,pair,CAPACITY} from './protocol.mjs';
import {manifest} from '../namespace/fixtures.mjs';
const out=process.argv[2],{createNamespace}=await import(pathToFileURL(out+'/runtime/namespace.mjs'));
const TCR=1024,ARGS=131072,HEAP=2097152,N=77825,rows=[];
function setup(){
 const memory=new WebAssembly.Memory({initial:48,maximum:32769,shared:true}),d=new DataView(memory.buffer);
 const get=p=>d.getUint32(p,true),put=(p,v)=>d.setUint32(p,v,true);
 put(TCR+8,1);put(TCR+32,2);put(TCR+64,ARGS);put(TCR+68,ARGS);put(TCR+72,ARGS+4096);put(TCR+56,HEAP);put(TCR+48,HEAP+32768);
 const path=HEAP,buffer=HEAP+128;
 put(path,10*256+191);Array.from('/ccl/a.bin').forEach((ch,i)=>put(path+4+4*i,ch.codePointAt(0)));put(path,10*256+191);
 // Use a ten-scalar absolute name in tests that do not inspect path spelling.
 put(buffer,8*256+199);new Uint8Array(memory.buffer,buffer+4,8).fill(219);
 const args=(op,a=4,b=buffer+6,c=32)=>[op*4,a,b,c].forEach((v,i)=>put(ARGS+i*4,v));args(1);
 let posts=0;
 const post=({generation,lifetime})=>{
  posts++;const {words:w,pair:p}=views(memory);w[5]=0;w[8]=0;w[4]=1;
  Atomics.store(p,0,pair(generation,1));
 };
 const client=extra=>fileClient({memory,tcr:TCR,post,collect:()=>{},allocate:()=>{throw Error('unexpected allocation');},...extra});
 return {memory,d,get,put,args,path,buffer,client,posts:()=>posts};
}
function refused(name,mutate,why){
 const x=setup();const args=mutate(x)??ARGS;
 const thread=new Uint8Array(x.memory.buffer,TCR,256).slice(),request=new Uint8Array(x.memory.buffer,REQUEST,SIZE).slice(),heap=new Uint8Array(x.memory.buffer,HEAP,32768).slice();
 assert.throws(()=>x.client()(args),new RegExp('file-admission: '+why),name);
 assert.equal(x.posts(),0,name+' reached host');
 for(const [p,bytes] of [[TCR,thread],[REQUEST,request],[HEAP,heap]])assert.deepEqual(new Uint8Array(x.memory.buffer,p,bytes.length),bytes,name+' wrote');
 rows.push({name,refusal:why});
}
refused('unbacked-args',x=>x.memory.buffer.byteLength-8,'backed span');
refused('unaligned-args',()=>ARGS+4,'argument frame');
refused('args-outside-stack',x=>{x.put(TCR+68,ARGS+8);},'argument frame');
refused('args-span-stack',x=>{x.put(TCR+72,ARGS+8);},'argument frame');
refused('incoming-root-mismatch',x=>{x.put(TCR+64,ARGS+8);},'thread state');
refused('not-running',x=>{x.put(TCR+32,3);},'thread state');
refused('lifetime-mismatch',x=>{x.put(TCR+8,2);},'thread state');
refused('lifetime-outside-profile',x=>{x.put(TCR+12,1);},'thread state');
refused('active-foreign-request',x=>{x.put(TCR+152,REQUEST);},'thread state');
refused('opcode-not-fixnum',x=>{x.put(ARGS,N);},'fixnum');
refused('unknown-opcode',x=>{x.args(8);},'operation');
refused('descriptor-not-fixnum',x=>{x.put(ARGS+4,N);},'fixnum');
refused('buffer-not-misc',x=>{x.put(ARGS+8,N);},'object tag');
refused('buffer-unbacked-header',x=>{x.put(ARGS+8,x.memory.buffer.byteLength+6);},'backed span');
refused('buffer-wrong-kind',x=>{x.put(x.buffer,8*256+191);},'object kind');
refused('buffer-unbacked-data',x=>{x.put(x.buffer,0xffffffc7);},'backed span');
refused('buffer-outside-owned-heap',x=>{x.put(TCR+48,x.buffer+4);},'object ownership');
refused('buffer-negative-count',x=>{x.put(ARGS+12,-4);},'buffer count');
refused('buffer-overrun',x=>{x.put(ARGS+12,36);},'buffer count');
refused('count-not-fixnum',x=>{x.put(ARGS+12,N);},'fixnum');
refused('seek-invalid-origin',x=>{x.args(2,4,0,12);},'seek origin');
refused('path-wrong-kind',x=>{x.args(5,x.buffer+6);},'object kind');
refused('path-too-long',x=>{x.put(x.path,4097*256+191);x.args(5,x.path+6);},'path length');
refused('path-surrogate',x=>{x.put(x.path+4,0xd800);x.args(5,x.path+6);},'scalar');
refused('path-non-scalar',x=>{x.put(x.path+4,0x110000);x.args(5,x.path+6);},'scalar');
refused('path-too-many-utf8-bytes',x=>{x.put(x.path,2049*256+191);for(let i=0;i<2049;i++)x.put(x.path+4+4*i,0x3bb);x.args(5,x.path+6);},'path bytes');
for(const [name,damage,why] of [
 ['wrong-generation',(w,p)=>Atomics.store(p,0,pair(9,1)),'completion identity'],
 ['missing-outcome',w=>{w[4]=0;},'completion identity'],
 ['inactive-result',w=>{w[6]=0;},'completion identity'],
 ['oversized-result',w=>{w[8]=CAPACITY+1;},'result extent'],
 ['unrepresentable-result',w=>{w[5]=0x20000000;},'result range'],
 ['partial-read-publication',w=>{w[5]=2;w[8]=1;},'read publication'],
 ['oversized-read-publication',w=>{w[5]=9;w[8]=9;},'read publication'],
 ['error-with-bytes',w=>{w[5]=-9;w[8]=1;},'read publication']]){
 const x=setup(),before=new Uint8Array(x.memory.buffer,x.buffer,16).slice();
 const thread=new Uint8Array(x.memory.buffer,TCR,256).slice();
 const run=x.client({post:({generation})=>{const {words:w,pair:p}=views(x.memory);w[4]=1;w[5]=0;w[8]=0;Atomics.store(p,0,pair(generation,1));damage(w,p);}});
 assert.throws(()=>run(ARGS),new RegExp(why),name);
 assert.deepEqual(new Uint8Array(x.memory.buffer,x.buffer,16),before,name+' partially stored');
 assert.deepEqual(new Uint8Array(x.memory.buffer,TCR,256),thread,name+' did not restore TCR');
 rows.push({name,refusal:why});
}
// Host checks are isolated from client admission, including seek overflow.
{
 const x=setup(),s=createNamespace(manifest()).session(),fd=s.open('/ccl/a.bin');
 const {words:w,pair:p}=views(x.memory);
 const request=(op,a,b,c)=>{w.fill(0);w[0]=op;w[1]=1;w[6]=1;w[9]=a;w[10]=b;w[11]=c;Atomics.store(p,0,pair(1,0));assert(serviceRequest(x.memory,s,1,1));return w[5];};
 assert.equal(request(2,fd,536870911,0),536870911);
 assert.equal(request(2,fd,1,1),-22);assert.equal(s.seek(fd,0,'cur'),536870911);
 assert.equal(request(2,fd,-536870912,1),-22);assert.equal(s.seek(fd,0,'cur'),536870911);
 assert.equal(request(2,fd,0,9),-22);
 assert.equal(request(7,fd,0,0),-30);
 rows.push({name:'host-seek-range-and-read-only',checks:5});
}
fs.writeFileSync(out+'/controls.json',JSON.stringify({status:'PASS',rows},null,2)+'\n');
console.log('NAMESPACE-ADMISSION-PASS',rows.length);
