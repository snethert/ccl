import fs from 'node:fs';
import assert from 'node:assert/strict';
import path from 'node:path';
import {manifest,materialize,install,memoryOffset} from './materializer.mjs';
import {inspect} from './binary.mjs';
import {sha256} from './sha256.mjs';
const dir=process.argv[2],read=n=>JSON.parse(fs.readFileSync(path.join(dir,n))),save=(n,x)=>fs.writeFileSync(path.join(dir,n),JSON.stringify(x,null,2)+'\n');
const classification=read('classifications.json'),policy=read('policy.json'),modules={},checks=[];
const clone=structuredClone;
function refuse(name,fn,reason){let e;try{fn();}catch(x){e=x;}assert(e,'CONTROL '+name+' escaped');assert.equal(e.message,reason,'CONTROL '+name);checks.push({name,reason});}
for(const [name,c]of Object.entries(classification)){
 const template=fs.readFileSync(path.join(dir,'templates',name+'.wasm')),baseline=fs.readFileSync(path.join(dir,'baseline',name+'.wasm'));
 const parsed=inspect(baseline,{ownerRetry:true});
 const abi={minimum:1,maximum:32769,imports:parsed.imports.map(i=>i.kind==='memory'?{...i,flags:1}:i),exports:parsed.exports.map(e=>({name:e.name,kind:e.kind,index:e.index,signature:parsed.types[parsed.functions[e.index]]}))};
 const t=manifest(template,abi,c,policy),outputs={};
 assert.equal(template[t.offset],1);assert.equal(baseline[t.offset],3);
 const differences=[...template.keys()].filter(i=>template[i]!==baseline[i]);assert.deepEqual(differences,[t.offset],name+' shared emitter correspondence');
 for(const profile of ['full','precompiled_callback']){
  const r=materialize(template,t,abi,c,policy,profile);outputs[profile]=r.record;
  assert.deepEqual(r.bytes,new Uint8Array(profile==='full'?baseline:template),name+' exact profile bytes');
  assert(install(r.bytes,r.record,template,t,abi,c,policy,profile) instanceof WebAssembly.Module);
  const target=path.join(dir,profile);fs.mkdirSync(target,{recursive:true});fs.mkdirSync(path.join(target,'templates'),{recursive:true});
  fs.writeFileSync(path.join(target,name+'.wasm'),r.bytes);fs.writeFileSync(path.join(target,'templates',name+'.wasm'),template);
 }
 modules[name]={abi,classification:c,template:t,outputs};
}
const bundle={policy,modules};save('materialization.json',bundle);
for(const profile of ['full','precompiled_callback']){
 const target=path.join(dir,profile);
 for(const name of ['modules.json','pools.json','materialized.json','native-metadata.json','native-behavior.json'])fs.copyFileSync(path.join(dir,'templates',name),path.join(target,name));
 fs.copyFileSync(path.join(dir,'materialization.json'),path.join(target,'materialization.json'));
}
const first=Object.keys(modules)[0],x=modules[first],template=fs.readFileSync(path.join(dir,'templates',first+'.wasm'));
const call=(t=x.template,a=x.abi,c=x.classification,p=policy,profile='full',bytes=template)=>materialize(bytes,t,a,c,p,profile);
for(const [name,change,reason]of [
 ['wrong-template-hash',t=>t.template_sha256='0'.repeat(64),'TEMPLATE_DIGEST'],
 ['wrong-offset',t=>t.offset++,'TEMPLATE_RECORD'],
 ['wrong-original-byte',t=>t.original_byte=3,'TEMPLATE_RECORD'],
 ['wrong-limits',t=>t.maximum++,'TEMPLATE_RECORD'],
 ['missing-import',t=>t.imports.pop(),'TEMPLATE_RECORD'],
 ['wrong-export',t=>t.exports[0].name='other','TEMPLATE_RECORD'],
 ['wrong-feature-set',t=>t.features=[],'TEMPLATE_RECORD'],
 ['stale-materializer',t=>t.materializer.sha256='0'.repeat(64),'TEMPLATE_RECORD'],
 ['stale-engine-pin',t=>t.engine_contract_sha256='0'.repeat(64),'TEMPLATE_RECORD']
]){const t=clone(x.template);change(t);refuse(name,()=>call(t),reason);}
let a=clone(x.abi);a.imports.pop();refuse('abi-import',()=>call(x.template,a),'ABI_INVENTORY');
a=clone(x.abi);a.maximum++;refuse('abi-limit',()=>call(x.template,a),'ABI_LIMITS');
for(const [name,change,reason]of [
 ['classification-bytes',c=>c.binary_sha256='0'.repeat(64),'CLASSIFICATION_DIGEST'],
 ['wait',c=>c.wait=true,'FORBIDDEN_INSTRUCTIONS'],
 ['legacy',c=>c.legacy=true,'FORBIDDEN_INSTRUCTIONS'],
 ['unknown-feature',c=>c.features=['not-an-engine-feature'],'FEATURE_NOT_ADMITTED'],
 ['duplicate-feature',c=>c.features.push(c.features[0]),'FEATURE_ORDER']
]){const c=clone(x.classification);change(c);refuse(name,()=>manifest(template,x.abi,c,policy),reason);}
let p=clone(policy);p.materializer.version='stale';refuse('version',()=>call(x.template,x.abi,x.classification,p),'MATERIALIZER');
p=clone(policy);delete p.engine;refuse('missing-engine',()=>call(x.template,x.abi,x.classification,p),'ENGINE_IDENTITY');
p=clone(policy);p.admission.full=false;refuse('engine-profile',()=>call(x.template,x.abi,x.classification,p),'PROFILE_NOT_ADMITTED');
refuse('deferred-jspi',()=>call(x.template,x.abi,x.classification,policy,'single_thread_jspi'),'PROFILE');
const tampered=Uint8Array.from(template);tampered[tampered.length-1]^=1;
refuse('tampered-template',()=>call(x.template,x.abi,x.classification,policy,'full',tampered),'TEMPLATE_DIGEST');
const shared=fs.readFileSync(path.join(dir,'baseline',first+'.wasm'));
refuse('already-shared',()=>manifest(shared,x.abi,{...x.classification,binary_sha256:sha256(shared)},policy),'CANONICAL_MEMORY');
const final=call();
for(const [name,change]of [
 ['template-as-installed',r=>r.binary_sha256=r.template_sha256],
 ['stale-binary-hash',r=>r.binary_sha256='0'.repeat(64)],
 ['wrong-installed-profile',r=>r.profile='precompiled_callback'],
 ['wrong-installed-feature',r=>r.features=[]],
 ['wrong-installed-version',r=>r.materializer.version='stale'],
 ['wrong-installed-import',r=>r.imports[0].flags=1]
]){const r=clone(final.record);change(r);refuse(name,()=>install(final.bytes,r,template,x.template,x.abi,x.classification,policy,'full'),'INSTALL_RECORD');}
refuse('template-bytes-at-install',()=>install(template,final.record,template,x.template,x.abi,x.classification,policy,'full'),'INSTALLED_DIGEST');
for(const [name,row]of Object.entries(read('malformed.json'))){
 const bytes=fs.readFileSync(path.join(dir,'malformed',name+'.wasm'));
 refuse('malformed-'+name,()=>manifest(bytes,modules.leaf.abi,row.classification,policy),row.reason);
}
// Engine linking checks use the generated raw primitive (no heap objects).
const raw=modules.primitive,rawTemplate=fs.readFileSync(path.join(dir,'templates/primitive.wasm'));
const slots=new WebAssembly.Table({element:'anyfunc',initial:0}),conversion_error=new WebAssembly.Tag({parameters:['i32']});
let rawCalls=0,links=0;
for(const profile of ['full','precompiled_callback']){
 const r=materialize(rawTemplate,raw.template,raw.abi,raw.classification,policy,profile);
 const m=install(r.bytes,r.record,rawTemplate,raw.template,raw.abi,raw.classification,policy,profile);
 for(const [initial,maximum]of [[1,32769],[2,32769],[1,2]]){
  const memory=new WebAssembly.Memory({initial,maximum,shared:profile==='full'}),v=new DataView(memory.buffer);v.setUint32(1024,0x1234,true);
  const instance=new WebAssembly.Instance(m,{env:{memory,slots,conversion_error}});assert.equal(instance.exports.entry(1030),0x1234);rawCalls++;links++;
 }
 for(const spec of [{initial:1,maximum:32770,shared:profile==='full'},{initial:1,maximum:32769,shared:profile!=='full'},...(profile==='precompiled_callback'?[{initial:1}]:[])]){
  const memory=new WebAssembly.Memory(spec);assert.throws(()=>new WebAssembly.Instance(m,{env:{memory,slots,conversion_error}}),WebAssembly.LinkError);links++;
 }
 // A minimal valid generated leaf checks identical value delivery.
 const leaf=modules.leaf,bytes=fs.readFileSync(path.join(dir,profile,'leaf.wasm'));
 const lm=install(bytes,leaf.outputs[profile],fs.readFileSync(path.join(dir,'templates/leaf.wasm')),leaf.template,leaf.abi,leaf.classification,policy,profile);
 const memory=new WebAssembly.Memory({initial:2,maximum:32769,shared:profile==='full'}),v=new DataView(memory.buffer),put=(p,n)=>v.setUint32(p,n,true);
 put(256+64,1024);put(256+120,2048);put(1024,77825);
 const fn=new WebAssembly.Instance(lm,{env:{memory,tcr:256}}).exports.entry;
 assert.deepEqual(fn(77825,1),[116,1]);put(1024,4);assert.deepEqual(fn(77825,1),[68,1]);rawCalls+=2;
}
save('checks.json',{status:'PASS',modules:Object.keys(modules).length,refusals:checks,primitive_and_leaf_calls:rawCalls,link_cases:links});
