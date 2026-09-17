import {fileURLToPath} from 'node:url';import fs from 'node:fs';import path from 'node:path';
import {inspect} from './binary.mjs';import {sha,PROFILE,validate} from './loader.mjs';
export function catalog(dir){const modules=JSON.parse(fs.readFileSync(path.join(dir,'modules.json')));
  return modules.map((module,index)=>{const bytes=fs.readFileSync(path.join(dir,'installed',module.name+'.wasm')),m=inspect(bytes);
    const record={name:module.name,slot:index+1,code:index+1,version:4,signature:17,role:23,sha256:sha(bytes),profile:PROFILE,imports:m.imports,
      entries:Object.fromEntries(m.exports.map(e=>[e.name,{index:e.index,role:e.name}]))};
    validate(bytes,record);return record;});}
if(process.argv[1]&&fs.realpathSync(process.argv[1])===fileURLToPath(import.meta.url))fs.writeFileSync(process.argv[3],JSON.stringify(catalog(process.argv[2]),null,2)+'\n');
