// v1 admission path over every runtime bundle, keeping modules and instances alive as the Worker does.
import fs from 'node:fs';
import {performance} from 'node:perf_hooks';
import {decodeTargetBundle} from '../../../../runtime/wasm32/target-bundle.mjs';
import {compile,publish} from '../../../../runtime/wasm32/bundle.mjs';
const dir=process.argv[2];
const manifest=JSON.parse(fs.readFileSync(dir+'/bundle-manifest.json'));
const versions=JSON.parse(fs.readFileSync(dir+'/versions.json')),policy=JSON.parse(fs.readFileSync(dir+'/policy.json'));
const memory=new WebAssembly.Memory({initial:64,maximum:32769,shared:true});
const env={memory,tcr:1024,code_registry:4096,table:new WebAssembly.Table({element:'anyfunc',initial:65536}),tail_table:new WebAssembly.Table({element:'anyfunc',initial:65536}),call_error:new WebAssembly.Tag({parameters:['i32']}),type_error:new WebAssembly.Tag({parameters:['i32','i32']}),nonlocal_exit:new WebAssembly.Tag({parameters:['i32']})};
const keep=[];let slot=1,modules=0;const t0=performance.now();
const files=manifest.files.map(f=>({f,bytes:new Uint8Array(fs.readFileSync(dir+'/'+f.bundle))})); // as boot0's main thread holds them
const afterRead=process.memoryUsage().rss;
for(const {f,bytes} of files){
  const d=decodeTargetBundle(bytes,f.sha256);const set=d.manifest.codeSet;
  const slots=Object.fromEntries(set.modules.map(m=>[m.code_id,slot++]));
  const compiled=compile(set,{...versions,modules:set.modules.map(m=>[m.name,m.code_id,m.generation]),table_capacity:65536,reserved_slots:[0],slots},n=>d.modules.get(n).bytes,n=>d.modules.get(n).template,policy);
  const imports=m=>({env,owner:{ensure:()=>{}},integer:{calculate:()=>0},floating:{calculate:()=>0},symbols:Object.fromEntries(m.symbols.map(s=>[s.wire,8])),codes:Object.fromEntries(m.codes.map(c=>[c.name,4]))});
  const instances=publish(compiled,n=>imports(compiled.find(x=>x.record.name===n).record),env.table,env.tail_table);
  keep.push({d,compiled,instances});modules+=set.modules.length;
}
const u=process.memoryUsage();
console.log(JSON.stringify({files:files.length,modules,seconds:Math.round((performance.now()-t0)/100)/10,rssAfterReadingBundlesMB:Math.round(afterRead/1048576),rssAfterAdmissionMB:Math.round(u.rss/1048576),heapUsedMB:Math.round(u.heapUsed/1048576),externalMB:Math.round(u.external/1048576),arrayBuffersMB:Math.round(u.arrayBuffers/1048576)}));
