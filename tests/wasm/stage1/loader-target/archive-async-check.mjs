import fs from 'node:fs';
import assert from 'node:assert/strict';
import {admitCodeArchive,admitCodeArchiveAsync} from '../../../../runtime/wasm32/code-archive.mjs';
import {inputInventory} from '../../../../runtime/wasm32/input-inventory.mjs';
const [fixture,dir]=process.argv.slice(2),read=n=>JSON.parse(fs.readFileSync(fixture+'/'+n));
const bytes=fs.readFileSync(dir+'/smoke.wasm'),manifest=JSON.parse(fs.readFileSync(dir+'/smoke.json')),inputs=inputInventory();
const memory=new WebAssembly.Memory({initial:32,maximum:32769,shared:true}),registry=4096;
const view=new DataView(memory.buffer);view.setUint32(registry,256,true);view.setUint32(registry+4,1,true);
const env={memory,tcr:1024,code_registry:registry,table:new WebAssembly.Table({element:'anyfunc',initial:256}),
 tail_table:new WebAssembly.Table({element:'anyfunc',initial:256}),call_error:new WebAssembly.Tag({parameters:['i32']}),
 type_error:new WebAssembly.Tag({parameters:['i32','i32']}),nonlocal_exit:new WebAssembly.Tag({parameters:['i32']})};
const unused=()=>{throw Error('unexpected publication');};
const options={bytes,manifest,digest:manifest.binary_sha256,env,versions:read('versions.json'),policy:read('policy.json'),
 allocateCode:unused,reserveRoots:unused,registerRoots:unused,
 onBuffers:(label,values)=>{inputs.release(label);if(values.length)inputs.hold(label,'validation',values);},
 onManifest:(label,value)=>{inputs.releaseManifest(label);if(value)inputs.holdManifest(label,value);}};
const clean=()=>{assert.equal(inputs.snapshot().bytes,0);assert.equal(inputs.snapshot().validationManifests,0);};
assert.deepEqual((await admitCodeArchiveAsync(options)).storage(),admitCodeArchive(options).storage());clean();
const checks=['sync/async admission identity'];
for(const [name,change] of [
 ['template digest',m=>m.template_sha256='0'.repeat(64)],
 ['ABI inventory',m=>m.d2.abi.minimum=2],
 ['classification',m=>m.d2.classification.wait=true],
 ['template record',m=>m.d2.template.byte_length=1],
 ['installed record',m=>m.d2.outputs.full.byte_length++],
 ['memory patch',m=>m.d2.template.offset=0],
 ['body digest',m=>m.entries[0].body_sha256='0'.repeat(64)],
 ['helper digest',m=>m.helper_bodies[0].body_sha256='0'.repeat(64)]
]){
 const m=structuredClone(manifest);change(m);let sync;
 assert.throws(()=>admitCodeArchive({...options,manifest:m}),e=>(sync=e.message,true));clean();
 await assert.rejects(()=>admitCodeArchiveAsync({...options,manifest:m}),e=>e.message===sync);clean();checks.push(name);
}
const original=crypto.subtle.digest;
try{
 Object.defineProperty(crypto.subtle,'digest',{configurable:true,value:()=>Promise.reject(Error('HASH_FAILURE'))});
 await assert.rejects(()=>admitCodeArchiveAsync(options),/HASH_FAILURE/);clean();checks.push('hash rejection releases ownership');
 let release,started;const gate=new Promise(r=>release=r),entered=new Promise(r=>started=r);let first=true;
 Object.defineProperty(crypto.subtle,'digest',{configurable:true,value:async function(...args){if(first){first=false;started();await gate;}return original.apply(this,args);}});
 const supplied=bytes.slice(),m=structuredClone(manifest),policy=structuredClone(options.policy),admitted=admitCodeArchiveAsync({...options,bytes:supplied,manifest:m,policy});
 await entered;supplied.fill(0);m.units.length=0;m.d2=null;policy.features.length=0;release();
 assert.equal((await admitted).storage().modules,1);clean();checks.push('caller mutations during suspension do not affect admission');
}finally{delete crypto.subtle.digest;}
console.log(JSON.stringify({status:'PASS',checks,ownership:inputs.snapshot()}));
