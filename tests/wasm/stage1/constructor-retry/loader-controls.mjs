import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import {execFileSync} from 'node:child_process';
import {inspect} from './binary.mjs';import {inspect as legacyInspect} from './legacy-binary.mjs';import {validate,LazyLoader,sha,PROFILE,OWNER_PROFILE} from './loader.mjs';
const [dir,stubPath,out,legacyDir]=process.argv.slice(2);fs.mkdirSync(out);const original=fs.readFileSync(path.join(dir,'pair.wat'),'utf8'),ownerImport='(import "owner" "ensure" (func $owner_ensure (param i32)))';
const record=bytes=>{const info=inspect(bytes,{ownerRetry:true});return {name:'pair',slot:1,code:1,version:4,signature:17,role:23,profile:OWNER_PROFILE,sha256:sha(bytes),imports:info.imports,entries:Object.fromEntries(info.exports.map(e=>[e.name,{index:e.index,role:e.name}]))};};
const base=fs.readFileSync(path.join(dir,'installed/pair.wasm'));assert(validate(base,record(base)));const rows=[{id:'owner-profile',status:'PASS'}];
function assemble(name,source){const wat=path.join(out,name+'.wat'),bin=path.join(out,name+'.wasm');fs.writeFileSync(wat,source);execFileSync('/usr/local/bin/wat2wasm',['--enable-threads','--enable-tail-call','--enable-exceptions',wat,'-o',bin]);return fs.readFileSync(bin);}
function suffix(s,form){assert(s.trimEnd().endsWith(')'));return s.trimEnd().slice(0,-1)+form+')';}
const changes=[
 ['wrong-owner-name',s=>s.replace('"owner" "ensure"','"owner" "collect"'),'OWNER_IMPORT'],
 ['wrong-owner-namespace',s=>s.replace('"owner" "ensure"','"other" "ensure"'),'IMPORT_AUTHORITY'],
 ['second-function',s=>s.replace(ownerImport,ownerImport+'(import "owner" "extra" (func $extra))'),'OWNER_IMPORT_COUNT'],
 ['wrong-owner-signature',s=>s.replace(ownerImport,ownerImport.replace('(param i32)','(param i64)')).replace('(call $owner_ensure (local.get $bytes))','(call $owner_ensure (i64.extend_i32_u (local.get $bytes)))'),'OWNER_IMPORT'],
 ['missing-owner',s=>s.replace(ownerImport,'').replace('(call $owner_ensure (local.get $bytes))','(drop (local.get $bytes))'),'OWNER_IMPORT_COUNT'],
 ['owner-global',s=>s.replace(ownerImport,ownerImport+'(import "owner" "other" (global $other i32))'),'OWNER_IMPORT'],
 ['start-calls-owner',s=>suffix(s,'(func $evil (call $owner_ensure (i32.const 8))) (start $evil)'),'INITIALIZATION_OR_SECTION'],
 ['active-data',s=>suffix(s,'(data (i32.const 0) "changed")'),'INITIALIZATION_OR_SECTION'],
 ['export-owner-as-entry',s=>suffix(s.replace('(export "entry")',''),'(export "entry" (func $owner_ensure))'),'EXPORT_SIGNATURE'],
];
let baseInfo=inspect(base,{ownerRetry:true});
for(const [name,change,reason] of changes){const source=change(original);assert.notEqual(source,original);const bytes=assemble(name,source);assert(WebAssembly.validate(bytes));let r;
 try{r=record(bytes);}catch(e){assert.equal(e.message,reason);r={...record(base),sha256:sha(bytes)};}
 assert.throws(()=>validate(bytes,r),e=>e.message===reason,name);fs.writeFileSync(path.join(out,name+'.json'),JSON.stringify(r,null,2)+'\n');rows.push({id:name,status:'REFUSED',reason});}
for(const [name,change,reason] of [
 ['legacy-profile-with-owner',r=>r.profile=PROFILE,'FUNCTION_IMPORT'],
 ['manifest-import',r=>r.imports[0].name='other','IMPORT_MANIFEST'],
 ['wrong-entry-index',r=>r.entries.entry.index--,'EXPORT_ROLE'],
 ['wrong-entry-role',r=>r.entries.entry.role='tail_entry','EXPORT_ROLE'],
 ['wrong-digest',r=>r.sha256='0'.repeat(64),'BINARY_DIGEST']]){const r=record(base);change(r);assert.throws(()=>validate(base,r),e=>e.message===reason,name);rows.push({id:name,status:'REFUSED',reason});}
// Dropping the imported function from the index space corrupts the public roles.
const wrong={...baseInfo,functions:baseInfo.functions.slice(1)};assert.notDeepEqual(wrong.types[wrong.functions[wrong.exports.find(e=>e.name==='entry').index]],{params:['i32','i32'],results:['i32','i32']},'function-index witness distinguishes import offset');
const memory=new WebAssembly.Memory({initial:1,maximum:32769,shared:true}),table=new WebAssembly.Table({element:'anyfunc',initial:2}),tail_table=new WebAssembly.Table({element:'anyfunc',initial:2});
const call_error=new WebAssembly.Tag({parameters:['i32']}),type_error=new WebAssembly.Tag({parameters:['i32','i32']}),nonlocal_exit=new WebAssembly.Tag({parameters:['i32']});
const env={memory,table,tail_table,tcr:1024,code_registry:4096,call_error,type_error,nonlocal_exit};let calls=0;const ensure=()=>calls++;
const imports={env,owner:{ensure},symbols:{},keywords:{},codes:{}};for(const i of baseInfo.imports)if(['symbols','keywords','codes'].includes(i.module))imports[i.module][i.name]=0;
const stub=new WebAssembly.Module(fs.readFileSync(stubPath));
function options(){return {...env,catalog:[record(base)],stub,allocationEnsure:ensure,readBytes:()=>base};}
for(const [name,mutation] of [['substituted-capability',i=>i.owner.ensure=()=>{}],['absent-capability',i=>delete i.owner],['wrapped-capability',i=>i.owner.ensure=n=>ensure(n)]]){
 const loader=new LazyLoader(options()),i={...imports,owner:{ensure}};mutation(i);assert.throws(()=>loader.defer('pair',i),/OWNER_CAPABILITY/);assert.equal(table.get(1),null);assert.equal(tail_table.get(1),null);assert.equal(calls,0);rows.push({id:name,status:'REFUSED',reason:'OWNER_CAPABILITY'});
}
const data=new DataView(memory.buffer);[2,1,1,4,17,23].forEach((v,i)=>data.setUint32(i<2?4096+4*i:4120+4*(i-2),v,true));
const loader=new LazyLoader(options());loader.defer('pair',imports);loader.install(1);assert.equal(calls,0,'installation cannot invoke owner');assert.equal(loader.snapshot()[0].state,'READY');rows.push({id:'cold-install-without-owner-entry',status:'PASS'});
if(legacyDir){
 const old=fs.readFileSync(path.join(legacyDir,'installed/pair.wasm')),r=record(old);r.profile=PROFILE;assert(validate(old,r));
 rows.push({id:'legacy-profile',status:'PASS'});
 for(const m of JSON.parse(fs.readFileSync(path.join(legacyDir,'modules.json')))){const b=fs.readFileSync(path.join(legacyDir,'installed',m.name+'.wasm'));assert.deepEqual(inspect(b),legacyInspect(b));}
 rows.push({id:'legacy-reader-byte-structure',status:'PASS'});
 r.profile=OWNER_PROFILE;assert.throws(()=>validate(old,r),/OWNER_IMPORT_COUNT/);rows.push({id:'new-profile-without-owner',status:'REFUSED',reason:'OWNER_IMPORT_COUNT'});
}
fs.writeFileSync(path.join(out,'controls.json'),JSON.stringify({status:'PASS',checks:rows.length,rows},null,2)+'\n');console.log('PASS',rows.length,'owner loader controls');
