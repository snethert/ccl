import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {decode} from './map.mjs';
export const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
export const roles=['source','compiler','host-compiler','image','abi','template','module','installed-binary','test','options','log','schema','implementation'];
export function preflight(root, manifestBytes, expectedBuild) {
  if(sha(manifestBytes)!==expectedBuild)throw Error('BUILD_IDENTITY');
  const manifest=JSON.parse(manifestBytes);
  if(manifest.version!==1||manifest.profile!=='stage1-full-one-worker-leaf'||manifest.entries.length!==9)throw Error('BUILD_PROFILE');
  const seen=new Set(),present=new Set(),files=new Map();
  for(const f of manifest.files){
    if(typeof f.path!=='string'||!f.path||path.isAbsolute(f.path)||f.path.split('/').some(x=>['','..','.'].includes(x))||seen.has(f.path))throw Error('BUILD_PATH');
    seen.add(f.path);present.add(f.role);
    const real=fs.realpathSync(path.join(root,f.path));if(!real.startsWith(fs.realpathSync(root)+path.sep))throw Error('BUILD_ESCAPE');
    const bytes=fs.readFileSync(real);if(sha(bytes)!==f.sha256)throw Error('BUILD_FILE_IDENTITY '+f.path);files.set(f.path,bytes);
  }
  if(roles.some(r=>!present.has(r)))throw Error('BUILD_ROLE');
  const ids=new Set(),slots=new Set(),names=new Set();
  const entries=manifest.entries.map(e=>{
    if(!Number.isInteger(e.logical_code_id)||e.logical_code_id<=0||ids.has(e.logical_code_id)||!Number.isInteger(e.slot)||e.slot<1||e.slot>=16||slots.has(e.slot)||names.has(e.name)||e.entry_kind!=='B'||e.signature!=='(i32,i32)->(i32,i32)')throw Error('BUILD_ENTRY');
    ids.add(e.logical_code_id);slots.add(e.slot);names.add(e.name);
    for(const [key,role] of [['source','source'],['template','template']])if(!files.has(e[key])||manifest.files.find(f=>f.path===e[key]).role!==role)throw Error('BUILD_ENTRY_ARTIFACT');
    const bytes=files.get(e.binary),declared=manifest.files.find(f=>f.path===e.binary);
    if(!bytes||declared.role!=='installed-binary')throw Error('BUILD_BINARY_ROLE');
    const moduleBytes=files.get(e.module);
    if(!moduleBytes||manifest.files.find(f=>f.path===e.module).role!=='module'||!moduleBytes.equals(bytes))throw Error('BUILD_INSTALL_IDENTITY');
    const map=decode(bytes,e);return {...e,bytes,map};
  });
  return {manifest,entries};
}
export async function install(build,memory,tcr) {
  const table=new WebAssembly.Table({element:'anyfunc',initial:16,maximum:16}),entries=[];
  // All preflight checks have completed before any table slot can be filled.
  for(const e of build.entries){const {instance}=await WebAssembly.instantiate(e.bytes,{env:{memory,tcr}});entries.push({...e,entry:instance.exports.entry});}
  for(const e of entries)table.set(e.slot,e.entry);
  return {table,entries,invoke(e,self,args){if(table.get(e.slot)!==e.entry)throw Error('INSTALLED_SLOT_IDENTITY');return table.get(e.slot)(self,args);}};
}
