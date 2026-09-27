// Compare the changed hot helpers against the preceding compiler's actual
// Wasm, including each corrupt-owner refusal and both public table checks.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
const [before,after,out]=process.argv.slice(2),hash=b=>createHash('sha256').update(b).digest('hex');
fs.mkdirSync(out,{recursive:true});
function build(dir,label){
 const wat=JSON.parse(fs.readFileSync(dir+'/boot/code-set.json')).modules[0].wat;
 const exposed=wat.replace(/\)\s*$/, '(export "guard" (func $stack_guard)) (export "resolve" (func $resolve)) (export "object" (func $object_base)))');
 fs.writeFileSync(out+'/'+label+'.wat',exposed);
 execFileSync('/usr/local/bin/wat2wasm',['--enable-all',out+'/'+label+'.wat','-o',out+'/'+label+'.wasm']);
 const bytes=fs.readFileSync(out+'/'+label+'.wasm'),module=new WebAssembly.Module(bytes);
 const memory=new WebAssembly.Memory({initial:16,maximum:32769});
 const table=new WebAssembly.Table({element:'anyfunc',initial:64}),tail_table=new WebAssembly.Table({element:'anyfunc',initial:64});
 const call_error=new WebAssembly.Tag({parameters:['i32']});
 const env={memory,table,tail_table,tcr:1024,code_registry:4096,call_error,
  type_error:new WebAssembly.Tag({parameters:['i32','i32']}),nonlocal_exit:new WebAssembly.Tag({parameters:['i32']})};
 const imports={env,symbols:{},codes:{},owner:{ensure(){throw Error('unexpected allocation');}},integer:{calculate(){throw Error('unexpected integer');}},floating:{calculate(){throw Error('unexpected float');}}};
 for(const i of WebAssembly.Module.imports(module))if(['symbols','codes'].includes(i.module))imports[i.module][i.name]=77825;
 const x=new WebAssembly.Instance(module,imports).exports,dv=new DataView(memory.buffer),put=(p,v)=>dv.setUint32(p,v,true);
 function reset(){new Uint8Array(memory.buffer).fill(0);
  for(let i=0;i<64;i++){table.set(i,null);tail_table.set(i,null);}table.set(24,x.entry);tail_table.set(24,x.tail_entry);
  for(const [o,v] of [[68,131072],[72,132096],[80,131072],[84,132096],[92,131072],[96,132096],[100,256]])put(1024+o,v);
  put(4096,64);put(4100,1);[24,4,17,23].forEach((v,i)=>put(4104+16*16+4*i,v));
  put(8192,1850);put(8204,8254);[1578,64,77825,4].forEach((v,i)=>put(8248+4*i,v));
 }
 function run(test){reset();test.mutate?.({put,env,dv});const prior=Buffer.from(new Uint8Array(memory.buffer));let value;
  try{value={ok:test.call(x)};}catch(e){value=e.is?.(call_error)?{checked:e.getArg(call_error,0)}:{trap:String(e)};}
  assert.deepEqual(Buffer.from(memory.buffer),prior,test.name+' must preserve memory');return value;}
 return {run,source:hash(wat),binary:hash(bytes)};
}
const old=build(before,'before'),now=build(after,'after'),cases=[];
for(const kind of [18,19,20]){
 const base=kind===18?68:kind===19?80:92,limit=base+4;
 for(const end of [131071,131072,131840,131841,132096,132097,0x100000000])for(const reserve of [0,256])for(const flags of [0,1])
  cases.push({name:`guard ${kind} ${end} ${reserve} ${flags}`,mutate:({put})=>{put(1124,reserve);put(1204,flags);},call:x=>x.guard(BigInt(end),131200,kind)});
 for(const [name,offset,value] of [['base alignment',base,131073],['limit alignment',limit,132097],['reserve alignment',100,1],['reversed',base,132112],['reserve exceeds extent',100,2048],['limit exceeds memory',limit,2097152]])
  cases.push({name:`guard ${kind} ${name}`,mutate:({put})=>put(1024+offset,value),call:x=>x.guard(131200n,131200,kind)});
}
for(const node of [8198,8254,0,77825,0xfffffff6,1048574])cases.push({name:'resolve '+node,call:x=>x.resolve(node)});
for(const [name,mutate] of [
 ['symbol fcell',({put})=>put(8204,0)],['function header',({put})=>put(8248,1850)],
 ['code alignment',({put})=>put(8252,65)],['zero code',({put})=>put(8252,0)],
 ['version alignment',({put})=>put(8260,5)],['zero version',({put})=>put(8260,0)],
 ['capacity',({put})=>put(4096,16)],['registry format',({put})=>put(4100,0)],
 ['row version',({put})=>put(4364,8)],['row signature',({put})=>put(4368,0)],['row role',({put})=>put(4372,0)],
 ['zero slot',({put})=>put(4360,0)],['slot extent',({put})=>put(4360,64)],['null slot',({env})=>env.table.set(24,null)]
])cases.push({name:'resolve '+name,mutate,call:x=>x.resolve(8198)});
for(const test of cases){const a=old.run(test),b=now.run(test);assert(!a.trap,test.name+' must be a checked refusal: '+JSON.stringify(a));assert.deepEqual(b,a,test.name);}
const report={status:'PASS',cases:cases.length,before:{source:old.source,binary:old.binary},after:{source:now.source,binary:now.binary},checks:cases.map(t=>t.name)};
fs.writeFileSync(out+'/result.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:'PASS',cases:cases.length}));
