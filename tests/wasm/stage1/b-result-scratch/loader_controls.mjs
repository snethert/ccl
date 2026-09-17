import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import {pathToFileURL} from 'node:url';
import {catalog} from './catalog.mjs';import {inspect} from './binary.mjs';
const dir=process.argv[2],output=process.argv[3],{LazyLoader,validate,sha}=await import(process.argv[4]?pathToFileURL(path.resolve(process.argv[4])):new URL('./loader.mjs',import.meta.url));
const records=catalog(dir),record=records.find(r=>r.name==='ct_raw_throw'),bytes=fs.readFileSync(path.join(dir,'installed',record.name+'.wasm'));
const stub=new WebAssembly.Module(fs.readFileSync(process.argv[5]));let checks=[];
function setup(){const memory=new WebAssembly.Memory({initial:2,maximum:32769,shared:true}),table=new WebAssembly.Table({element:'anyfunc',initial:records.length+1}),tail_table=new WebAssembly.Table({element:'anyfunc',initial:records.length+1});new Uint8Array(memory.buffer).fill(0x5a);
 const call_error=new WebAssembly.Tag({parameters:['i32']}),nonlocal_exit=new WebAssembly.Tag({parameters:['i32']}),type_error=new WebAssembly.Tag({parameters:['i32','i32']});
 const options={catalog:[record],memory,table,tail_table,call_error,nonlocal_exit,stub,readBytes:()=>bytes};
 const imports={env:{memory,tcr:256,table,tail_table,code_registry:4096,call_error,type_error,nonlocal_exit},symbols:{},codes:{},keywords:{}};
 for(const i of record.imports)if(i.module!=='env')imports[i.module][i.name]=4;
 return {options,imports,memory,table,tail_table};}
function refused(name,reason,action){const f=setup(),before=Buffer.from(f.memory.buffer);assert.throws(()=>action(f),e=>e.message===reason,name);assert(Buffer.from(f.memory.buffer).equals(before),name+': no Lisp memory writes');assert.equal(f.table.get(record.slot),null,name+': public unpublished');assert.equal(f.tail_table.get(record.slot),null,name+': internal unpublished');checks.push({name,status:'REJECTED',reason});}
for(const r of records)validate(fs.readFileSync(path.join(dir,'installed',r.name+'.wasm')),r);
const f=setup(),view=new DataView(f.memory.buffer),put=(p,x)=>view.setUint32(p,x,true),row=4104+16*record.code;put(4096,records.length+1);put(4100,1);[record.slot,4,17,23].forEach((x,i)=>put(row+4*i,x));const before=Buffer.from(f.memory.buffer),loader=new LazyLoader(f.options);loader.defer(record.name,f.imports);loader.install(record.slot);assert.equal(loader.snapshot()[0].state,'READY');assert(Buffer.from(f.memory.buffer).equals(before),'installation does not write Lisp memory');checks.push({name:'genuine-distinct-tag-install',status:'PASS'});
for(const [name,value]of [['missing',undefined],['aliased',null],['not-tag',{}]])refused(name+'-exit-tag','DISTINCT_EXIT_TAG',f=>new LazyLoader({...f.options,nonlocal_exit:name==='aliased'?f.options.call_error:value}));
for(const name of ['missing','substituted','aliased'])refused(name+'-imported-tag','CAPABILITIES',f=>{const l=new LazyLoader(f.options);if(name==='missing')delete f.imports.env.nonlocal_exit;else f.imports.env.nonlocal_exit=name==='aliased'?f.options.call_error:new WebAssembly.Tag({parameters:['i32']});l.defer(record.name,f.imports);});
refused('old-profile','PROFILE',()=>validate(bytes,{...record,profile:'wasm32-shared-B-exnref-tail-catch-v1'}));
refused('omitted-tag-manifest','IMPORT_MANIFEST',()=>validate(bytes,{...record,imports:record.imports.filter(i=>i.name!=='nonlocal_exit')}));
const changed=Buffer.from(bytes);assert(changed.includes(Buffer.from('nonlocal_exit')));changed.write('other_exit___',changed.indexOf(Buffer.from('nonlocal_exit')),'ascii');assert(WebAssembly.validate(changed));
refused('different-binary-tag','ENV_IMPORTS',()=>validate(changed,{...record,sha256:sha(changed),imports:inspect(changed).imports}));
fs.writeFileSync(output,JSON.stringify({status:'PASS',qualified_modules:records.length,checks},null,2)+'\n');
