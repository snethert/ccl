import fs from 'node:fs';
import assert from 'node:assert/strict';
import {admitCodeArchive} from '../../../../runtime/wasm32/code-archive.mjs';
import {encodeTargetContainer,decodeTargetContainer} from '../../../../runtime/wasm32/target-bundle.mjs';
import {sha256} from '../../../../runtime/wasm32/sha256.mjs';
const [fixture,archiveDir]=process.argv.slice(2),read=n=>JSON.parse(fs.readFileSync(fixture+'/'+n));
const bytes=fs.readFileSync(archiveDir+'/smoke.wasm'),manifest=JSON.parse(fs.readFileSync(archiveDir+'/smoke.json'));
const memory=new WebAssembly.Memory({initial:32,maximum:32769,shared:true}),registry=4096;
const view=new DataView(memory.buffer),get=p=>view.getUint32(p,true),put=(p,v)=>view.setUint32(p,v,true);
const env={memory,tcr:1024,code_registry:registry,table:new WebAssembly.Table({element:'anyfunc',initial:128}),
 tail_table:new WebAssembly.Table({element:'anyfunc',initial:128}),call_error:new WebAssembly.Tag({parameters:['i32']}),
 type_error:new WebAssembly.Tag({parameters:['i32','i32']}),nonlocal_exit:new WebAssembly.Tag({parameters:['i32']})};
put(registry,128);put(registry+4,1);
let nextCode=16,nextRoot=65536,failRegistration=false,failReservation=false;
const roots=new Set(),unexpected=()=>{throw Error('unexpected capability');};
const options={maxGenerations:2,bytes,manifest,digest:sha256(bytes),env,versions:read('versions.json'),policy:read('policy.json'),
 capabilities:{owner:{ensure:unexpected},integer:{calculate:unexpected},floating:{calculate:unexpected}},
 allocateCode:(n,j)=>{const old=nextCode;nextCode+=n;j.push(()=>nextCode=old);return old;},
 reserveRoots:(n,j)=>{if(failReservation)throw Error('ROOT_REFUSAL');const base=nextRoot;nextRoot+=n*4;j.push(()=>nextRoot=base);return {base,count:n};},
 registerRoots:(block,cells,j)=>{if(failRegistration)throw Error('REGISTRATION_REFUSAL');cells.forEach(p=>roots.add(p));j.push(()=>cells.forEach(p=>roots.delete(p)));}};
const state=()=>({bytes:new Uint8Array(memory.buffer).slice(),nextCode,nextRoot,roots:[...roots],
 table:Array.from({length:128},(_,i)=>env.table.get(i)),tail:Array.from({length:128},(_,i)=>env.tail_table.get(i))});
const checks=[];
function refuse(name,run,pattern){const before=state();assert.throws(run,pattern);assert.deepEqual(state(),before);checks.push(name);}
for(const [name,change,pattern] of [
 ['null-function',m=>m.functions[0]=null,/FUNCTION/],['null-unit',m=>m.units[0]=null,/UNIT/],
 ['count-negative',m=>m.function_count=-1,/COUNTS/],['roots-fractional',m=>m.root_cells=1.5,/COUNTS/],
 ['duplicate-name',m=>m.functions[1].name=m.functions[0].name,/FUNCTION/],
 ['duplicate-export',m=>m.functions[1].export=m.functions[0].export,/FUNCTION/],
 ['duplicate-unit-name',m=>m.units[1].name=m.units[0].name,/UNIT/],
 ['missing-wire',m=>delete m.units[0].wire,/UNIT/],['empty-unit',m=>m.units[0].functions=[],/UNIT_FUNCTIONS/],
 ['shared-shape',m=>m.units[0].shared[0]=null,/SHARED_SYMBOLS/],
 ['shared-index',m=>m.units[0].shared[0][1]=9999,/SHARED_SYMBOL/],
 ['shared-cell',m=>m.units[0].shared[0][2]=9999,/SHARED_SYMBOL/],
 ['shared-duplicate',m=>m.units[0].shared.push(m.units[0].shared[0]),/SHARED_SYMBOL/],
 ['symbol-shape',m=>m.functions[0].symbols[0]=null,/IMPORTS/],
 ['symbol-duplicate',m=>m.functions[0].symbols.push(m.functions[0].symbols[0]),/SYMBOL_WIRE/],
 ['code-shape',m=>m.functions[0].codes.push(null),/CODE_IMPORT/],
 ['missing-d2',m=>delete m.d2,/D2/],['missing-entry',m=>m.entries[0]=null,/ENTRY_OFFSET/],
 ['entry-count',m=>m.entries.pop(),/EXPORT_SET/],
 ['packaging',m=>m.packaging='bad',/PACKAGING/],['versions',m=>m.abi.version++,/VERSIONS/],
 ['count',m=>m.function_count++,/INVENTORY/],['function-offset',m=>m.functions[0].code_offset=1,/FUNCTION/],
 ['unit-overlap',m=>m.units[1].root_base--,/UNIT/],['duplicate-function',m=>m.units[1].functions.push(0),/UNIT_FUNCTIONS/],
 ['symbol-index',m=>m.functions[0].symbols[0][1]=999,/SYMBOL_WIRE/],
 ['code-import',m=>m.functions[0].codes.push({name:'alien',code_offset:99999}),/CODE_IMPORT/],
 ['shared-identity',m=>m.units[0].shared[0][0]='alien',/SHARED_SYMBOL/],
 ['root-count',m=>m.root_cells++,/COMPLETE_UNITS/],['record-version',m=>m.units[0].record_version=9,/CODE_RECORD/],
 ['digest',m=>m.binary_sha256='0'.repeat(64),/DIGEST/],['body-digest',m=>m.entries[0].body_sha256='0'.repeat(64),/BODY_DIGEST/],
 ['range',m=>m.entries[0].entry.start++,/RANGE/],['entry-offset',m=>m.entries[0].code_offset++,/ENTRY_OFFSET/],
 ['import-manifest',m=>m.d2.outputs.full.imports.pop(),/IMPORT_MANIFEST/],
 ['classification',m=>m.d2.classification.wait=true,/FORBIDDEN_INSTRUCTIONS/],
 ['materializer',m=>m.d2.template.materializer.sha256='0'.repeat(64),/TEMPLATE_RECORD/],
 ['template',m=>m.template_sha256='0'.repeat(64),/TEMPLATE_DIGEST/],
 ['installation-record',m=>m.d2.outputs.full.byte_length++,/INSTALL_RECORD/]
]){const m=structuredClone(manifest);change(m);refuse(name,()=>admitCodeArchive({...options,manifest:m}),pattern);}
const container=encodeTargetContainer({units:manifest.units.map(u=>u.name),archive_sha256:manifest.binary_sha256,fasl:new Uint8Array([1,2,3])});
assert.deepEqual(decodeTargetContainer(container,sha256(container)).fasl,new Uint8Array([1,2,3]));checks.push('container-roundtrip');
for(const [name,mutate,pattern] of [
 ['container-magic',b=>new DataView(b.buffer).setUint32(0,0,true),/VERSION/],
 ['container-version',b=>new DataView(b.buffer).setUint32(4,1,true),/VERSION/],
 ['container-length',b=>new DataView(b.buffer).setUint32(12,100,true),/LENGTH/],
 ['container-fasl-digest',b=>b[b.length-1]^=1,/FASL_DIGEST/]
]){const b=container.slice();mutate(b);refuse(name,()=>decodeTargetContainer(b,sha256(b)),pattern);}
refuse('container-digest',()=>decodeTargetContainer(container,'0'.repeat(64)),/DIGEST/);
refuse('container-short',()=>decodeTargetContainer(container.subarray(0,15),'0'.repeat(64)),/SIZE/);
for(const bad of [{units:['same','same']},{units:[42]},{archive_sha256:'bad'}]){
 const b=encodeTargetContainer({units:['ok'],archive_sha256:manifest.binary_sha256,fasl:new Uint8Array(),...bad});
 refuse('container-manifest-'+JSON.stringify(bad),()=>decodeTargetContainer(b,sha256(b)),/MANIFEST/);
}
refuse('null-manifest',()=>admitCodeArchive({...options,manifest:null}),/MANIFEST/);
refuse('identical-tables',()=>admitCodeArchive({...options,env:{...env,tail_table:env.table}}),/CAPABILITIES/);
refuse('missing-root-authority',()=>admitCodeArchive({...options,reserveRoots:undefined}),/ROOT_AUTHORITY/);
refuse('generation-limit-shape',()=>admitCodeArchive({...options,maxGenerations:0}),/GENERATION_LIMIT/);
const wrongImport=Buffer.from(bytes);wrongImport[wrongImport.indexOf(Buffer.from('roots'))]='x'.charCodeAt(0);
refuse('binary-import-authority',()=>admitCodeArchive({...options,bytes:wrongImport}),/IMPORT_SET/);
const withStart=Buffer.concat([bytes,Buffer.from([8,1,0])]);
refuse('binary-start-section',()=>admitCodeArchive({...options,bytes:withStart}),/INITIALIZATION_OR_SECTION/);
const session=admitCodeArchive(options),names=manifest.units.map(u=>u.name),token=Symbol('file');
refuse('unknown-unit',()=>session.reserve(token,['missing']),/UNIT/);
refuse('duplicate-unit',()=>session.reserve(token,[names[0],names[0]]),/SESSION/);
failReservation=true;refuse('reservation-rollback',()=>session.reserve(token,names),/ROOT_REFUSAL/);failReservation=false;
const ensure=options.capabilities.owner.ensure;options.capabilities.owner.ensure=42;
const badImports=admitCodeArchive(options);refuse('instantiation-rollback',()=>badImports.reserve(token,names),/function import/);options.capabilities.owner.ensure=ensure;
const saved=nextCode;nextCode=127;refuse('code-capacity',()=>session.reserve(token,names),/CAPACITY/);nextCode=saved;
session.reserve(token,names);
refuse('duplicate-session',()=>session.reserve(token,names),/SESSION/);
const u=manifest.units[0],r=read('records.json').units.find(r=>r.name===u.wire),record=r.install_record??r.record,values=Array(u.symbol_count).fill(77825);
refuse('record-substitution',()=>session.install(token,u.wire,[6,'wrong'],values),/CODE_RECORD/);
refuse('symbol-count',()=>session.install(token,u.wire,record,[]),/SYMBOL_COUNT/);
refuse('invalid-word',()=>session.install(token,u.wire,record,values.map((v,i)=>i? v:-1)),/SYMBOL_COUNT/);
failRegistration=true;refuse('publication-rollback',()=>session.install(token,u.wire,record,values),/REGISTRATION_REFUSAL/);failRegistration=false;
put(registry+8+16*16,1);refuse('occupied-row',()=>session.install(token,u.wire,record,values),/SLOT_OCCUPIED/);put(registry+8+16*16,0);
session.install(token,u.wire,record,values);
const other=manifest.units.find(x=>x.name!==u.name&&x.shared.some(s=>u.shared.some(t=>s[2]===t[2]))),
 otherRecord=read('records.json').units.find(r=>r.name===other.wire);
refuse('shared-identity-mismatch',()=>session.install(token,other.wire,otherRecord.install_record??otherRecord.record,
 Array(other.symbol_count).fill(77838)),/SHARED_IDENTITY/);
put(registry+8+16*16,100);refuse('republish-registry-identity',()=>session.install(token,u.wire,record,values),/REGISTRY_CHANGED/);put(registry+8+16*16,24);
const entry=env.table.get(24);env.table.set(24,null);refuse('republish-table-identity',()=>session.install(token,u.wire,record,values),/TABLE_CHANGED/);env.table.set(24,entry);
const token2=Symbol('overlap');session.reserve(token2,names);assert.equal(session.storage().generations,2);session.release(token2);
const token3=Symbol('reuse');session.reserve(token3,names);assert.equal(session.storage().generations,2);session.release(token3);checks.push('overlap-partial-close-reuse');
const two=Symbol('two');session.reserve(two,names);
refuse('generation-limit',()=>session.reserve(Symbol('three'),names),/GENERATION_CAPACITY/);session.release(two);
session.release(token);assert.equal(session.storage().openSessions,0);checks.push('closed-session-release');
refuse('closed-install',()=>session.install(token,u.wire,record,values),/CODE_RECORD/);
console.log(JSON.stringify({status:'PASS',checks:checks.length,cases:checks,storage:session.storage()}));
