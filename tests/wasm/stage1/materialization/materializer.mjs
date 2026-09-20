// D2 for production compiler modules. Classification and ABI are build inputs
// from the trusted owner; instruction classification is not guessed at runtime.
import {snapshotBytes} from './bytes.mjs';
import {sha256} from './sha256.mjs';
import {inspect} from './binary.mjs';
export const VERSION='wasm32-d2-generated-v1';
const need=(x,s)=>{if(!x)throw Error(s);};
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);

// Decode within section bounds, require shortest u32 encodings, and locate
// the byte ourselves. The manifest's offset never controls the parser.
export function memoryOffset(bytes){
 let p=8,end=bytes.length,found;
 const byte=()=>{need(p<end,'TRUNCATED');return bytes[p++];};
 const leb=()=>{let n=0;for(let i=0;i<5;i++){const b=byte();need(i<4||b<16,'LEB');n+=(b&127)*2**(7*i);if(!(b&128)){need(i===0||b!==0,'CANONICAL_LEB');return n;}}throw Error('LEB');};
 const name=()=>{const n=leb();need(n<=end-p,'NAME');const s=new TextDecoder('utf-8',{fatal:true}).decode(bytes.subarray(p,p+n));p+=n;return s;};
 const limits=()=>{const f=leb();need(f<=3,'LIMIT_FLAGS');leb();if(f&1)leb();};
 while(p<bytes.length){end=bytes.length;const id=byte(),size=leb();end=p+size;need(end<=bytes.length,'SECTION');
  if(id===2){const count=leb();for(let i=0;i<count;i++){
   const module=name(),field=name(),kind=byte();
   if(kind===0)leb();
   else if(kind===1){need(byte()===112,'TABLE_TYPE');limits();}
   else if(kind===2){need(!found&&module==='env'&&field==='memory','MEMORY_IMPORT');const offset=p;need(byte()===1,'CANONICAL_MEMORY');const minimum=leb(),maximum=leb();need(minimum<=maximum&&maximum<=65536,'MEMORY_LIMITS');found={offset,minimum,maximum};}
   else if(kind===3){byte();byte();}
   else if(kind===4){need(byte()===0,'TAG_ATTRIBUTE');leb();}
   else throw Error('IMPORT_KIND');
  }need(p===end,'IMPORT_END');}
  p=end;
 }
 need(found,'MEMORY_IMPORT');return found;
}
function structure(bytes){
 need(WebAssembly.validate(bytes),'INVALID_WASM');
 const m=inspect(bytes,{ownerRetry:true}),memory=memoryOffset(bytes);
 need(m.imports.filter(i=>i.kind==='memory').length===1,'MEMORY_IMPORT');
 return {...memory,imports:m.imports,exports:m.exports.map(e=>({name:e.name,kind:e.kind,index:e.index,signature:m.types[m.functions[e.index]]}))};
}
function features(bytes,c,policy){
 need(c.binary_sha256===sha256(bytes),'CLASSIFICATION_DIGEST');
 need(Array.isArray(c.features)&&same(c.features,[...new Set(c.features)].sort()),'FEATURE_ORDER');
 need(c.wait===false&&c.legacy===false,'FORBIDDEN_INSTRUCTIONS');
 need(c.features.every(f=>policy.features.includes(f)),'FEATURE_NOT_ADMITTED');
 return c.features;
}
export function manifest(input,abi,classification,policy){
 const bytes=snapshotBytes(input),s=structure(bytes);
 need(s.minimum===abi.minimum&&s.maximum===abi.maximum,'ABI_LIMITS');
 need(same(s.imports,abi.imports)&&same(s.exports,abi.exports),'ABI_INVENTORY');
 need(policy.materializer.version===VERSION&&/^[0-9a-f]{64}$/.test(policy.materializer.sha256),'MATERIALIZER');
 need(/^[0-9a-f]{64}$/.test(policy.engine_contract_sha256),'ENGINE_CONTRACT');
 need(typeof policy.engine?.name==='string'&&typeof policy.engine?.version==='string'&&/^[0-9a-f]{64}$/.test(policy.engine?.matrix_sha256),'ENGINE_IDENTITY');
 return {version:VERSION,template_sha256:sha256(bytes),original_byte:1,...s,features:features(bytes,classification,policy),materializer:structuredClone(policy.materializer),engine_contract_sha256:policy.engine_contract_sha256,engine:structuredClone(policy.engine)};
}
export function materialize(input,record,abi,classification,policy,profile){
 const bytes=snapshotBytes(input);
 need(sha256(bytes)===record.template_sha256,'TEMPLATE_DIGEST');
 const actual=manifest(bytes,abi,classification,policy);
 need(same(actual,record),'TEMPLATE_RECORD');
 need(['full','precompiled_callback'].includes(profile),'PROFILE');
 need(policy.admission[profile]===true,'PROFILE_NOT_ADMITTED');
 const shared=profile==='full';
 bytes[actual.offset]=shared?3:1;
 need(WebAssembly.validate(bytes),'INVALID_MATERIALIZED');
 const binary_sha256=sha256(bytes);
 need(shared?binary_sha256!==actual.template_sha256:binary_sha256===actual.template_sha256,'BINARY_IDENTITY');
 return {bytes,record:{version:VERSION,profile,shared,template_sha256:actual.template_sha256,binary_sha256,materializer:actual.materializer,engine_contract_sha256:actual.engine_contract_sha256,engine:actual.engine,offset:actual.offset,patched_byte:shared?3:1,limits:{minimum:actual.minimum,maximum:actual.maximum},imports:actual.imports.map(i=>i.kind==='memory'?{...i,flags:shared?3:1}:i),exports:actual.exports,features:actual.features,byte_length:bytes.length}};
}
// Re-derive against the trusted template/ABI/classification/policy. A supplied
// installation record cannot substitute its own template, profile or limits.
export function install(input,record,template,templateRecord,abi,classification,policy,profile){
 const bytes=snapshotBytes(input),expected=materialize(template,templateRecord,abi,classification,policy,profile);
 need(same(record,expected.record),'INSTALL_RECORD');
 need(sha256(bytes)===expected.record.binary_sha256,'INSTALLED_DIGEST');
 return new WebAssembly.Module(bytes);
}
