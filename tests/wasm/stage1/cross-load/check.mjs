import fs from 'node:fs';
import assert from 'node:assert/strict';
import {Worker,isMainThread,parentPort,workerData} from 'node:worker_threads';
import {admitHeapImage,recordDigest} from './runtime/heap-image.mjs';
import {compile,publish,validate} from './runtime/bundle.mjs';
import {sha256} from './runtime/sha256.mjs';

const directory=isMainThread?process.argv[2]:workerData.directory;
const read=n=>JSON.parse(fs.readFileSync(directory+'/'+n));
const bytes=n=>fs.readFileSync(directory+'/'+n);
const image=read('artifact/image.json'),record=read('artifact/heap.json');
const bundle=read('artifact/bundle.json'),expected=read('artifact/expected.json');
const policy=read('policy.json'),payload=bytes('artifact/heap.bin'),canonical=bytes('artifact/static.bin');
const binary=n=>bytes(`artifact/module-${bundle.modules.find(m=>m.name===n).code_id}.wasm`);
const template=n=>bytes(`artifact/template-${bundle.modules.find(m=>m.name===n).code_id}.wasm`);
const NIL=77825,T=77838;

function fresh(base) {
  assert.equal(sha256(canonical),image.staticDigest);
  assert.equal(sha256(JSON.stringify(bundle)),image.codeDigest);
  const memory=new WebAssembly.Memory({initial:Math.ceil((base+payload.length+65536)/65536),maximum:32769,shared:true});
  const view=new DataView(memory.buffer),get=p=>view.getUint32(p,true),put=(p,x)=>view.setUint32(p,x,true);
  const region=image.regions.find(r=>r.name==='canonical');
  new Uint8Array(memory.buffer,region.start,canonical.length).set(canonical);
  const args={memory,record,payload,digest:image.digest,regions:image.regions,start:base,
    limit:memory.buffer.byteLength,codeDigest:image.codeDigest,rootSlots:image.rootSlots};
  return {memory,get,put,args,base,root:name=>get(image.roots.find(r=>r.name===name).slot)};
}

function observations(s) {
  const {get,root}=s;
  const effectSymbol=root('symbol:CCL:*WASM-LOADER-EFFECT*'),effect=get(effectSymbol+2);
  const funSymbol=root('symbol:CCL:WASM-LOADER-CONSTANT'),fun=get(funSymbol+6);
  assert.equal(get(fun-6),1578);assert.equal(get(fun+6),4);
  const pool=get(fun+18);
  assert.equal(get(fun+10),get(pool-2));assert.equal(get(fun+14),get(pool+2));
  const count=get(pool-6)>>>8,constant=get(pool-2+4*(count-1));
  assert.equal(get(constant-6),762);
  const pair=get(constant-2);
  assert.equal(pair,get(constant+2),'shared cons identity');
  assert.equal(pair%8,1);
  // D1's CDR is raw+0, CAR is raw+4. This is not the host's 16-byte cons.
  const values=[[get(effect+3)/4,get(effect-1)/4],[get(pair+3)/4,get(pair-1)/4,true]];
  assert.deepEqual(values,read('native.json'));
  assert.equal(get(77824),NIL);assert.equal(get(77828),NIL);
  assert.equal(get(T+2),T);assert.equal(get(77870+2),NIL);
  assert.equal(get(fun-2)/4,2,'logical code ID, independent of table slot');
  return {values,fun,pool,constant,pair,effect};
}

function execute(s,observation) {
  const {memory,get,put,root,base}=s,tcr=256,registry=16384;
  const table=new WebAssembly.Table({element:'anyfunc',initial:expected.table_capacity});
  const tail=new WebAssembly.Table({element:'anyfunc',initial:expected.table_capacity});
  const call_error=new WebAssembly.Tag({parameters:['i32']});
  const type_error=new WebAssembly.Tag({parameters:['i32','i32']});
  const nonlocal_exit=new WebAssembly.Tag({parameters:['i32']});
  let unavailableCalls=0;
  // This producer witness has no numeric operations. Unsupported capability
  // use fails the witness; no value or initializer result is manufactured.
  const unavailable=()=>{unavailableCalls++;throw Error('UNQUALIFIED_SERVICE');};
  put(registry,expected.table_capacity);put(registry+4,1);
  for(const m of bundle.modules)[m.slot,4,17,23].forEach((v,i)=>put(registry+8+16*m.code_id+4*i,v));
  const imports=name=>{
    const m=bundle.modules.find(m=>m.name===name),bindings=image.modules.find(x=>x.code_id===m.code_id);
    const symbols=Object.fromEntries(bindings.symbols.map(w=>[w,root(`import:${m.code_id}:${w}`)]));
    Object.assign(symbols,{condition_registry:0,error_message:NIL,expected_function:NIL});
    return {env:{memory,tcr,table,tail_table:tail,code_registry:registry,call_error,type_error,nonlocal_exit},
      integer:{calculate:unavailable},floating:{calculate:unavailable},symbols};
  };
  const compiled=compile(bundle,expected,binary,template,policy);
  const installed=publish(compiled,imports,table,tail);
  for(const [offset,value] of [[48,base+payload.length],[52,memory.buffer.byteLength],[56,base],
      [64,131072],[68,131072],[72,196608],[76,262144],[80,262144],[84,393216],
      [104,524288],[108,1],[116,0],[120,131584],[124,131616],[128,0],[140,0],[148,0]])
    put(tcr+offset,value);
  put(524288,243);
  const code=bundle.modules.find(m=>m.code_id===2);
  const [value,count]=table.get(code.slot)(observation.fun,0);
  assert.equal(value>>>0,observation.constant);assert.equal(count,1);
  assert.equal(get(131584),observation.constant);
  assert.equal(unavailableCalls,0);
  // IN-PACKAGE is a real queued initializer. It is preserved, not suppressed,
  // and the producer packet does not call it or claim a completed boot.
  const cold=root('cold-load-functions');assert.equal(cold%8,1);
  assert.equal(get(cold+3),root('function:1'));assert.equal(get(cold-1),NIL);
  return {installed:installed.length,calledCode:2,values:count,unavailableCalls,
          deferredInitializers:1,firstInitializerDependency:'CCL::SET-PACKAGE'};
}

function controls() {
  const s=fresh(2097152),list=[];
  const snapshot=()=>sha256(new Uint8Array(s.memory.buffer));
  const before=snapshot();
  function bad(name,edit,reason) {
    const args={...s.args,record:structuredClone(record),payload:Uint8Array.from(payload)};
    edit(args);
    assert.throws(()=>admitHeapImage(args),e=>e instanceof Error&&e.message===reason,name);
    assert.equal(snapshot(),before,name+' preserves memory');list.push({name,reason});
  }
  bad('image-record-digest',a=>a.digest='0'.repeat(64),'heap image: record digest');
  bad('image-payload-digest',a=>a.payload[0]^=1,'heap image: payload digest');
  bad('code-set-identity',a=>a.codeDigest='0'.repeat(64),'heap image: code identity');
  bad('missing-root-authority',a=>a.rootSlots=a.rootSlots.slice(1),'heap image: binding authority');
  bad('missing-relocation',a=>{a.record.relocations.pop();a.digest=recordDigest(a.record);},'heap image: unrelocated pointer');
  bad('interior-reference',a=>{const r=a.record.relocations.find(r=>r.value.heap!==undefined);r.value.heap+=4;a.digest=recordDigest(a.record);},'heap image: heap boundary');
  const packageOffset=new DataView(payload.buffer,payload.byteOffset,payload.length).getUint32(8,true)===2146?8:null;
  assert.equal(packageOffset,8);
  bad('package-width',a=>{new DataView(a.payload.buffer).setUint32(packageOffset,9*256+98,true);
    a.record.payloadDigest=sha256(a.payload);a.digest=recordDigest(a.record);},'heap image: package shape');
  // Malformed bundle clauses are isolated against a valid, complete heap.
  for(const [name,edit,reason] of [
    ['omitted-module',b=>b.modules.pop(),'INVENTORY'],
    ['wrong-binary',b=>b.modules[0].d2.outputs.full.binary_sha256='0'.repeat(64),'BINARY'],
    ['wrong-role',b=>b.modules[0].entries[0].table='tail','ROLE'],
    ['wrong-signature',b=>b.modules[0].entries[0].signature.params.pop(),'SIGNATURE'],
    ['reserved-slot',b=>b.modules[0].slot=1,'SLOT']]) {
    const b=structuredClone(bundle);edit(b);
    assert.throws(()=>validate(b,expected,binary),e=>e.message===reason,name);
    assert.equal(snapshot(),before);list.push({name,reason});
  }
  for(const [name,reason] of [['name','SERVICE_NAME'],['signature','SERVICE_SIGNATURE'],['duplicate','SERVICE_DUPLICATE']]) {
    const broken=bytes('service-controls/'+name+'.wasm');
    const read=n=>n===bundle.modules[1].name?broken:binary(n);
    assert.throws(()=>validate(bundle,expected,read),e=>e.message===reason,name);
    assert.equal(snapshot(),before);list.push({name:'service-'+name,reason});
  }
  const admitted=admitHeapImage(s.args);admitted.install();
  const o=observations(s);
  const saved=s.get(o.pair+3);
  s.put(o.pair+3,0); // 64-bit CDR store would overwrite D1's four-byte CAR.
  assert.throws(()=>observations(s),assert.AssertionError);
  s.put(o.pair+3,saved);observations(s);
  list.push({name:'host-width-cons-write',reason:'native observation mismatch'});
  return list;
}

if(isMainThread) {
  const profiles=[];
  for(const base of [2097152,8388608]) {
    profiles.push(await new Promise((resolve,reject)=>{
      const w=new Worker(new URL(import.meta.url),{workerData:{directory,base}});
      w.once('message',resolve);w.once('error',reject);w.once('exit',c=>{if(c)reject(Error('worker '+c));});
    }));
  }
  const first=fresh(2097152),second=fresh(4194304);
  admitHeapImage(first.args).install();admitHeapImage(second.args).install();
  const a=observations(first),b=observations(second);
  first.put(a.pair+3,100*4);assert.equal(second.get(b.pair+3),29*4);
  const result={status:'PASS',profiles,controls:controls(),independentInstances:true,
    filesTargetLoaded:0,boot:false};
  fs.writeFileSync(directory+'/checks.json',JSON.stringify(result,null,2)+'\n');
  console.log('CROSS-LOAD-CHECKS-PASS',profiles.length,result.controls.length);
} else {
  const s=fresh(workerData.base);admitHeapImage(s.args).install();
  const o=observations(s),execution=execute(s,o);
  parentPort.postMessage({base:s.base,values:o.values,sharing:true,execution});
}
