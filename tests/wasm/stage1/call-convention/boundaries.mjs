import fs from 'node:fs';
import assert from 'node:assert/strict';
const dir=process.argv[2],TCR=1024,REG=4096,FUN=8198,POOL=9006,NIL=77825;
const metadata=JSON.parse(fs.readFileSync(dir+'/metadata.json'));
const memory=new WebAssembly.Memory({initial:4,maximum:32769});
const table=new WebAssembly.Table({initial:64,element:'anyfunc'}),tail=new WebAssembly.Table({initial:64,element:'anyfunc'});
const call_error=new WebAssembly.Tag({parameters:['i32']});
const view=new DataView(memory.buffer),put=(p,v)=>view.setUint32(p,v,true),get=p=>view.getUint32(p,true);
const instances={};
for(const name of ['CC-ZERO','CC-V0','CC-V1','CC-V4','CC-V5','CC-V64','CC-TAIL','CC-DEPTH']){
 const module=new WebAssembly.Module(fs.readFileSync(dir+'/'+name+'.wasm'));
 const imports={env:{memory,tcr:TCR,table,tail_table:tail,code_registry:REG,call_error,
  type_error:new WebAssembly.Tag({parameters:['i32','i32']}),nonlocal_exit:new WebAssembly.Tag({parameters:['i32']})}};
 for(const i of WebAssembly.Module.imports(module))if(i.module!=='env'){
  imports[i.module]??={};imports[i.module][i.name]=i.kind==='global'?65536:()=>{throw Error('unexpected service '+i.name);};
 }
 instances[name]=new WebAssembly.Instance(module,imports).exports;
}
function reset(budget=256,name='CC-ZERO'){
 new Uint8Array(memory.buffer).fill(0);
 put(REG,64);put(REG+4,1);[8,4,17,23].forEach((v,i)=>put(REG+24+4*i,v));
 [1578,4,NIL,4,10006,11006,POOL,0].forEach((v,i)=>put(FUN-6+4*i,v));
 put(POOL-6,metadata[name].poolHeader);put(POOL-2,10006);put(POOL+2,11006);
 put(10000,2042);put(10004,4);put(10008,metadata[name].required*4);put(10012,metadata[name].optional*4);
 put(11000,1018);put(11004,4);
 put(TCR+64,16384);put(TCR+68,16384);put(TCR+72,32768);put(TCR+100,512);
 put(TCR+120,16448);put(TCR+124,16448+budget);
 table.set(8,instances['CC-ZERO'].entry);tail.set(8,instances['CC-ZERO'].tail_entry);
 put(65536,70006);put(70000,1850);put(70012,FUN);
}
let checks=0;
function refused(run,code){assert.throws(run,e=>e instanceof WebAssembly.Exception&&e.is(call_error)&&e.getArg(call_error,0)===code);checks++;}
reset();assert.deepEqual(instances['CC-ZERO'].resolve_test(FUN),[FUN,8]);checks++;
for(const word of [0,123,0xfffffffe]){reset();refused(()=>instances['CC-ZERO'].resolve_test(word),4);}
reset();put(REG+24,0);refused(()=>instances['CC-ZERO'].resolve_test(FUN),4);
reset();put(REG+28,8);refused(()=>instances['CC-ZERO'].resolve_test(FUN),4);
for(const self of [0,123,0xfffffffe]){reset();const before=new Uint8Array(memory.buffer).slice();
 refused(()=>instances['CC-ZERO'].entry(self,0),4);assert.deepEqual(new Uint8Array(memory.buffer),before);}
for(const [address,value] of [[POOL-2,12006],[POOL-6,250],[10000,1786],[11004,0],[10008,4]]){
 reset();put(address,value);const before=new Uint8Array(memory.buffer).slice();
 refused(()=>instances['CC-ZERO'].entry(FUN,0),4);assert.deepEqual(new Uint8Array(memory.buffer),before);checks++;
}
for(const [offset,value] of [[68,16385],[72,32769],[100,513],[100,65536],[120,16449],[124,32784]]){
 reset();put(TCR+offset,value);const before=new Uint8Array(memory.buffer).slice();
 refused(()=>instances['CC-ZERO'].entry(FUN,0),2);
 assert.deepEqual(new Uint8Array(memory.buffer),before,'public refusal must precede publication');checks++;
}
reset();instances['CC-ZERO'].guard_test(32256n,17000,18);checks++;
refused(()=>instances['CC-ZERO'].guard_test(32272n,17000,18),18);
assert.equal(get(256),1,'overflow signal must observe the reentrancy bit');assert.equal(get(TCR+180),0);checks++;
put(TCR+180,1);instances['CC-ZERO'].guard_test(32272n,17000,18);checks++;
refused(()=>instances['CC-ZERO'].guard_test(32784n,17000,18),2);
const resultRows=[];
for(const n of [0,1,4,5,64]){
 reset(256,'CC-V'+n);const result=instances['CC-V'+n].entry(FUN,0);
 assert.deepEqual(result,[n?0:NIL,n]);assert.equal(get(TCR+116),n);
 assert.deepEqual(Array.from({length:n},(_,i)=>get(16448+4*i)),Array.from({length:n},(_,i)=>4*i));
 resultRows.push({count:n,budget:64,status:'PASS'});checks++;
 if(n>4){reset(16,'CC-V'+n);refused(()=>instances['CC-V'+n].entry(FUN,0),3);resultRows.push({count:n,budget:4,status:'CHECKED_3'});}
}
reset(16,'CC-TAIL');put(TCR+72,18432);put(TCR+100,0);put(16384,400000);put(16388,0);
tail.set(8,instances['CC-TAIL'].tail_entry);table.set(8,instances['CC-TAIL'].entry);
assert.deepEqual(instances['CC-TAIL'].entry(FUN,2),[400000,1]);assert.equal(get(TCR+128),0);checks++;
let overflowDepth;
for(let n=0;n<100;n++){
 reset(16,'CC-DEPTH');put(TCR+72,18432);put(TCR+100,512);put(16384,n*4);
 tail.set(8,instances['CC-DEPTH'].tail_entry);table.set(8,instances['CC-DEPTH'].entry);
 try{assert.deepEqual(instances['CC-DEPTH'].entry(FUN,1),[n*4,1]);}
 catch(e){assert(e instanceof WebAssembly.Exception&&e.is(call_error));assert.equal(e.getArg(call_error,0),18);overflowDepth=n;break;}
}
assert(overflowDepth>0&&overflowDepth<100);assert.equal(get(TCR+180),0);checks++;
const report={status:'PASS',checks,stack:{base:16384,limit:32768,reserve:512,lastAcceptedEnd:32256,firstSignalledEnd:32272,reentrancy:true,overflowDepth,tailSteps:100000,tailStackBytes:2048},resultRows};
fs.writeFileSync(dir+'/boundaries.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
