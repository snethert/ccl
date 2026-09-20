import fs from 'node:fs';import assert from 'node:assert/strict';import {execFileSync} from 'node:child_process';
import {inspect} from './binary.mjs';import {LazyLoader,validate,sha,PROFILE,OWNER_PROFILE,NUMERIC_PROFILE} from './loader.mjs';
import {numericCapabilities,admitNumericCapabilities} from './numeric-capabilities.mjs';
export function admissionControls({dir,options,imports,owner,integerBytes,integerDigest,images,mode}){
 const rows=[],base=fs.readFileSync(dir+'/compiled/n_add.wasm'),wat=fs.readFileSync(dir+'/compiled/n_add.wat','utf8'),r=options.catalog.find(r=>r.name==='n_add');
 const record=b=>{const m=inspect(b,{ownerRetry:true});return {...r,sha256:sha(b),imports:m.imports,entries:Object.fromEntries(m.exports.map(e=>[e.name,{index:e.index,role:e.name}]))};};
 const refuse=(name,fn,reason)=>{assert.throws(fn,e=>e.message===reason,name);rows.push({name,status:'REFUSED',reason});};
 validate(base,r);rows.push({name:'combined-profile',status:'PASS'});
 const factory=o=>numericCapabilities({memory:imports.env.memory,tcr:imports.env.tcr,owner,callError:imports.env.call_error,bytes:integerBytes,digest:integerDigest,pinned:images,...o});
 for(const [name,change,why] of [
  ['wrong-tcr',{tcr:1040},'NUMERIC_OWNER'],['wrong-memory',{memory:new WebAssembly.Memory({initial:1,maximum:32769,shared:true})},'NUMERIC_OWNER'],
  ['wrong-service-digest',{digest:'0'.repeat(64)},'integer owner capability']])refuse(name,()=>factory(change),why);
 const second=factory({}),foreignTag=factory({callError:new WebAssembly.Tag({parameters:['i32']})});
 for(const [name,bundle,env] of [
  ['forged-bundle',{...options.numericCapabilities},imports.env],
  ['foreign-error-tag',foreignTag,imports.env],
  ['wrong-bundle-tcr',options.numericCapabilities,{...imports.env,tcr:1040}],
 ])refuse(name,()=>admitNumericCapabilities(bundle,env),'NUMERIC_CAPABILITY');
 for(const [name,mutate,why] of [
  ['wrapped-integer',i=>i.integer.calculate=(...a)=>imports.integer.calculate(...a),'NUMERIC_IMPORT_CAPABILITY'],
  ['wrapped-owner',i=>i.owner.ensure=n=>imports.owner.ensure(n),'NUMERIC_IMPORT_CAPABILITY'],
  ['second-bundle-integer',i=>i.integer.calculate=second.calculate,'NUMERIC_IMPORT_CAPABILITY'],
  ['second-bundle-owner',i=>i.owner.ensure=second.ensure,'NUMERIC_IMPORT_CAPABILITY'],
  ['missing-integer',i=>delete i.integer,'NUMERIC_IMPORT_CAPABILITY'],
  ['missing-owner',i=>delete i.owner,'NUMERIC_IMPORT_CAPABILITY'],
  ['wrong-import-tcr',i=>i.env.tcr=1040,'NUMERIC_CAPABILITY'],
  ['getter-import',i=>Object.defineProperty(i.integer,'calculate',{get(){throw Error('GETTER_RAN');}}),'IMPORT_GETTER'],
 ]){
  const l=new LazyLoader(options),i={...imports,env:{...imports.env},owner:{...imports.owner},integer:{...imports.integer}};mutate(i);
  refuse(name,()=>l.defer('n_add',i),why);assert.equal(options.table.get(r.slot),null);assert.equal(options.tail_table.get(r.slot),null);
 }
 for(const [name,change,why] of [
  ['legacy-profile',x=>x.profile=PROFILE,'FUNCTION_IMPORT'],['owner-only-profile',x=>x.profile=OWNER_PROFILE,'OWNER_IMPORT_COUNT'],
  ['bad-profile',x=>x.profile='unknown','PROFILE'],['bad-digest',x=>x.sha256='0'.repeat(64),'BINARY_DIGEST'],
  ['bad-import-manifest',x=>x.imports=x.imports.slice(1),'IMPORT_MANIFEST'],['bad-export-index',x=>x.entries.entry.index++,'EXPORT_ROLE']]){
   const x=structuredClone(r);change(x);refuse(name,()=>validate(base,x),why);
 }
 const add=(s,form)=>s.trimEnd().slice(0,-1)+form+')';
 const edits=[
  ['integer-signature',s=>s.replace('(func $integer_slow (param i32 i32) (result i32))','(func $integer_slow (param i64 i32) (result i32))').replace('(call $integer_slow (local.get $op) (local.get $root))','(call $integer_slow (i64.extend_i32_u (local.get $op)) (local.get $root))'),'INTEGER_IMPORT'],
  ['owner-signature',s=>s.replace('(func $owner_ensure (param i32))','(func $owner_ensure (param i64))').replace('(call $owner_ensure (local.get $bytes))','(call $owner_ensure (i64.extend_i32_u (local.get $bytes)))'),'OWNER_IMPORT'],
  ['missing-integer',s=>s.replace('(import "integer" "calculate" (func $integer_slow (param i32 i32) (result i32)))','').replace('(call $integer_slow (local.get $op) (local.get $root))','(i32.const 0)'),'OWNER_IMPORT_COUNT'],
  ['integer-name',s=>s.replace('"integer" "calculate"','"integer" "other"'),'INTEGER_IMPORT'],
  ['integer-namespace',s=>s.replace('"integer" "calculate"','"foreign" "calculate"'),'IMPORT_AUTHORITY'],
  ['owner-name',s=>s.replace('"owner" "ensure"','"owner" "other"'),'OWNER_IMPORT'],
  ['extra-function',s=>s.replace('(module','(module (import "integer" "extra" (func $extra))'),'OWNER_IMPORT_COUNT'],
  ['start',s=>add(s,'(func $start) (start $start)'),'INITIALIZATION_OR_SECTION'],
  ['data',s=>add(s,'(data (i32.const 0) "changed")'),'INITIALIZATION_OR_SECTION'],
  ['defined-global',s=>add(s,'(global $extra i32 (i32.const 0))'),'INITIALIZATION_OR_SECTION'],
 ];
 for(const [name,edit,why] of edits){
  const source=edit(wat);assert.notEqual(source,wat);const path=dir+'/'+mode+'-admission-'+name;
  fs.writeFileSync(path+'.wat',source);execFileSync('/usr/local/bin/wat2wasm',['--enable-threads','--enable-tail-call','--enable-exceptions',path+'.wat','-o',path+'.wasm']);const b=fs.readFileSync(path+'.wasm');
  assert(WebAssembly.validate(b));let x;try{x=record(b);}catch{x={...r,sha256:sha(b)};}
  refuse(name,()=>validate(b,x),why);
 }
 // Retry after a real digest failure. No table or memory publication occurs.
 let corrupt=true;const l=new LazyLoader({...options,readBytes:name=>{const b=options.readBytes(name);return corrupt?Buffer.concat([b,Buffer.from([0])]):b;}});
 l.defer('n_add',imports);const first=options.table.get(r.slot),tail=options.tail_table.get(r.slot),before=sha(new Uint8Array(imports.env.memory.buffer));
 assert.throws(()=>l.install(r.slot),e=>e.is?.(imports.env.call_error)&&e.getArg(imports.env.call_error,0)===7);
 assert.equal(options.table.get(r.slot),first);assert.equal(options.tail_table.get(r.slot),tail);assert.equal(sha(new Uint8Array(imports.env.memory.buffer)),before);assert.equal(l.snapshot().find(x=>x.name==='n_add').state,'COLD');
 corrupt=false;l.install(r.slot);assert.equal(l.snapshot().find(x=>x.name==='n_add').state,'READY');assert.equal(sha(new Uint8Array(imports.env.memory.buffer)),before);
 options.table.set(r.slot,null);options.tail_table.set(r.slot,null);rows.push({name:'failed-install-atomic-retry',status:'PASS'});
 fs.writeFileSync(dir+'/'+mode+'-admission.json',JSON.stringify({status:'PASS',rows},null,2)+'\n');
}
