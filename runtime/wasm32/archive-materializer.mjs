import {sha256} from './sha256.mjs';
import {inspect} from './binary.mjs';
import {VERSION,memoryOffset} from './materializer.mjs';
const need=(v,s)=>{if(!v)throw Error(s);},same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);

// Archive D2 re-derivation: one template digest, one full digest, one structural
// parse and one engine module. Input is the caller's private owned snapshot. Only the canonical memory flag may differ.
function* installation(input,archive,policy,parsed){
 const bytes=input,d=archive.d2,fullDigest=yield bytes;
 need(fullDigest===archive.binary_sha256,'INSTALLED_DIGEST');
 need(Number.isInteger(d.template.offset)&&bytes[d.template.offset]===3,'MEMORY_PATCH');
 bytes[d.template.offset]=1;
 try{
 need(WebAssembly.validate(bytes),'INVALID_WASM');
 const templateDigest=yield bytes,m=parsed??inspect(bytes,{ownerRetry:true});
 const s={...memoryOffset(bytes),imports:m.imports.map(i=>i.kind==='memory'?{...i,flags:1}:i),
  exports:m.exports.map(e=>({name:e.name,kind:e.kind,index:e.index,signature:m.types[m.functions[e.index]]}))};
 need(s.offset===d.template.offset,'MEMORY_PATCH');
 need(templateDigest===archive.template_sha256&&d.classification.binary_sha256===templateDigest,'TEMPLATE_DIGEST');
 need(s.minimum===d.abi.minimum&&s.maximum===d.abi.maximum&&same(s.imports,d.abi.imports)&&same(s.exports,d.abi.exports),'ABI_INVENTORY');
 need(policy.materializer.version===VERSION&&/^[0-9a-f]{64}$/.test(policy.materializer.sha256),'MATERIALIZER');
 need(/^[0-9a-f]{64}$/.test(policy.engine_contract_sha256),'ENGINE_CONTRACT');
 need(typeof policy.engine?.name==='string'&&typeof policy.engine?.version==='string'&&/^[0-9a-f]{64}$/.test(policy.engine?.matrix_sha256),'ENGINE_IDENTITY');
 const c=d.classification;
 need(Array.isArray(c.features)&&same(c.features,[...new Set(c.features)].sort()),'FEATURE_ORDER');
 need(c.wait===false&&c.legacy===false,'FORBIDDEN_INSTRUCTIONS');
 need(c.features.every(f=>policy.features.includes(f)),'FEATURE_NOT_ADMITTED');
 const actual={version:VERSION,template_sha256:templateDigest,original_byte:1,...s,features:c.features,
  materializer:structuredClone(policy.materializer),engine_contract_sha256:policy.engine_contract_sha256,engine:structuredClone(policy.engine)};
 need(same(actual,d.template),'TEMPLATE_RECORD');need(policy.admission.full===true,'PROFILE_NOT_ADMITTED');
 const record={version:VERSION,profile:'full',shared:true,template_sha256:templateDigest,binary_sha256:fullDigest,
  materializer:actual.materializer,engine_contract_sha256:actual.engine_contract_sha256,engine:actual.engine,
  offset:actual.offset,patched_byte:3,limits:{minimum:actual.minimum,maximum:actual.maximum},
  imports:actual.imports.map(i=>i.kind==='memory'?{...i,flags:3}:i),exports:actual.exports,features:actual.features,byte_length:bytes.length};
 need(same(record,d.outputs.full),'INSTALL_RECORD');bytes[s.offset]=3;return new WebAssembly.Module(bytes);
 }finally{bytes[d.template.offset]=3;}
}
export function installArchive(...args){
 const iterator=installation(...args);let step=iterator.next();
 try{while(!step.done)step=iterator.next(sha256(step.value));return step.value;}
 catch(error){return iterator.throw(error);}
}
export async function installArchiveAsync(...args){
 const iterator=installation(...args);let step=iterator.next();
 try{while(!step.done){
  const hash=await crypto.subtle.digest('SHA-256',step.value);
  step=iterator.next(Array.from(new Uint8Array(hash),b=>b.toString(16).padStart(2,'0')).join(''));
 }return step.value;}catch(error){return iterator.throw(error);}
}
