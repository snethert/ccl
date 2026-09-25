// Trusted-owner code-set admission. One generated function per module, two B roles.
import {sha256} from './sha256.mjs';
import {inspect} from './binary.mjs';
import {entryRanges} from './ranges.mjs';
import {install} from './materializer.mjs';
import {validate as validateGenerated} from './loader.mjs';
const need=(v,s)=>{if(!v)throw Error(s);},same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
export const PACKAGING='one-generated-function-per-module-v1';
export const signatures={entry:{params:['i32','i32'],results:['i32','i32']},tail_entry:{params:['i32','i32','i32'],results:['i32','i32']}};
const slotFor=(m,expected)=>expected.slots===undefined?m.slot:expected.slots[m.code_id];
export function validate(bundle,expected,read){
 need(bundle.version===1&&bundle.packaging===PACKAGING,'PACKAGING');
 need(same(bundle.abi,expected.abi)&&same(bundle.layout,expected.layout),'VERSIONS');
 need(same(bundle.modules.map(x=>[x.name,x.code_id,x.generation]),expected.modules),'INVENTORY');
 const codes=new Set(),slots=new Set(),names=new Set();
 for(const m of bundle.modules){
  need(Number.isSafeInteger(m.code_id)&&m.code_id>0&&!codes.has(m.code_id),'CODE_ID');codes.add(m.code_id);
  need(!names.has(m.name),'MODULE_NAME');names.add(m.name);
  const slot=slotFor(m,expected);
  need(expected.slots===undefined||m.slot===undefined,'SERIALIZED_SLOT');
  need(Number.isSafeInteger(slot)&&slot>0&&slot<expected.table_capacity&&!slots.has(slot)&&!expected.reserved_slots.includes(slot),'SLOT');slots.add(slot);
  need(Number.isSafeInteger(m.generation)&&m.generation>0,'GENERATION');
  need(same(m.abi,bundle.abi)&&same(m.layout,bundle.layout),'MODULE_VERSIONS');
  const bytes=read(m.name),options={ownerRetry:m.profile!==undefined};
  need(sha256(bytes)===m.d2.outputs.full.binary_sha256,'BINARY');
  const x=inspect(bytes,options),ranges=entryRanges(bytes,options);
  if(m.profile!==undefined)validateGenerated(bytes,{profile:m.profile,
   sha256:m.d2.outputs.full.binary_sha256,imports:m.d2.outputs.full.imports,
   entries:Object.fromEntries(m.entries.map(e=>[e.role,{index:e.function_index,role:e.role}]))});
  need(x.exports.length===2&&m.entries.length===2,'ENTRY_COUNT');
  for(const role of ['entry','tail_entry']){
   const a=m.entries.find(e=>e.role===role),b=x.exports.find(e=>e.name===role);
   need(a&&b&&a.export===role&&a.function_index===b.index&&a.table===(role==='entry'?'public':'tail'),'ROLE');
   need(same(a.signature,signatures[role])&&same(x.types[x.functions[b.index]],signatures[role]),'SIGNATURE');
   need(same(a.range,ranges.find(e=>e.role===role)),'RANGE');
  }
 }
 return true;
}
export function compile(bundle,expected,read,readTemplate,policy){
 validate(bundle,expected,read);
 return bundle.modules.map(m=>({record:{...m,slot:slotFor(m,expected)},module:install(read(m.name),m.d2.outputs.full,readTemplate(m.name),m.d2.template,m.d2.abi,m.d2.classification,policy,'full')}));
}
// Preflight the whole set before compilation or publication; no partial omission fallback.
export function publish(compiled,imports,table,tailTable){
 for(const {record:m}of compiled)need(table.get(m.slot)===null&&tailTable.get(m.slot)===null,'OCCUPIED');
 const instances=compiled.map(({record:m,module})=>({record:m,instance:new WebAssembly.Instance(module,imports(m.name))}));
 const written=[];
 try{for(const x of instances){written.push(x.record.slot);table.set(x.record.slot,x.instance.exports.entry);tailTable.set(x.record.slot,x.instance.exports.tail_entry);}}
 catch(e){for(const slot of written){table.set(slot,null);tailTable.set(slot,null);}throw e;}
 return instances;
}
