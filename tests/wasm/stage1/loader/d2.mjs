// Build-side inventory. WABT independently classifies instructions; the D2
// materializer derives and checks the shared-memory output from its template.
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {inspect} from './runtime/binary.mjs';
import {sha256} from './runtime/sha256.mjs';
import {entryRanges} from './runtime/ranges.mjs';
import {manifest,materialize} from './runtime/materializer.mjs';
import {signatures} from './runtime/bundle.mjs';
import {PROFILE,OWNER_PROFILE,NUMERIC_PROFILE,FLOAT_PROFILE} from './runtime/loader.mjs';

export function inventory(wat,stem,policy,versions){
 fs.writeFileSync(stem+'.wat',wat);
 execFileSync('/usr/local/bin/wat2wasm',['--enable-all',stem+'.wat','-o',stem+'.template.wasm']);
 const bytes=fs.readFileSync(stem+'.template.wasm');
 const sections=execFileSync('/usr/local/bin/wasm-objdump',['-x',stem+'.template.wasm'],{encoding:'utf8'});
 const instructions=execFileSync('/usr/local/bin/wasm-objdump',['-d',stem+'.template.wasm'],{encoding:'utf8'});
 fs.writeFileSync(stem+'.sections.txt',sections);fs.writeFileSync(stem+'.instructions.txt',instructions);
 const ops=[...new Set(instructions.split('\n').filter(l=>l.includes('|')&&l.split('|')[1].trim()).map(l=>l.split('|')[1].trim().split(/\s+/)[0]))].sort();
 const features=[];
 if(/-> \([^)]*,/.test(sections))features.push('multivalue');
 if(ops.some(o=>o.startsWith('return_call')))features.push('tailcall');
 if(ops.some(o=>o.includes('.atomic.')))features.push('atomics');
 if(ops.some(o=>['try_table','throw','throw_ref'].includes(o)))features.push('exceptions');
 if(instructions.includes('exnref')||ops.includes('throw_ref'))features.push('exnref');
 if(ops.some(o=>['memory.copy','memory.fill','memory.init','data.drop'].includes(o)))features.push('bulk');
 const classification={binary_sha256:sha256(bytes),features:features.sort(),
  wait:ops.some(o=>o.startsWith('memory.atomic.wait')||o==='memory.atomic.notify'),
  legacy:ops.some(o=>['try','catch','catch_all','delegate','rethrow'].includes(o)),
  instruction_mnemonics:ops,sections_sha256:sha256(sections),instructions_sha256:sha256(instructions)};
 const x=inspect(bytes,{ownerRetry:true});
 const abi={minimum:1,maximum:32769,imports:x.imports,exports:x.exports.map(e=>({name:e.name,kind:e.kind,index:e.index,signature:x.types[x.functions[e.index]]}))};
 const template=manifest(bytes,abi,classification,policy),full=materialize(bytes,template,abi,classification,policy,'full');
 fs.writeFileSync(stem+'.wasm',full.bytes);
 const names=new Set(x.imports.map(i=>i.module+'.'+i.name));
 const profile=names.has('floating.calculate')?FLOAT_PROFILE:names.has('integer.calculate')?NUMERIC_PROFILE:names.has('owner.ensure')?OWNER_PROFILE:PROFILE;
 const ranges=entryRanges(full.bytes,{ownerRetry:true});
 return {generation:1,...versions,profile,d2:{abi,classification,template,outputs:{full:full.record}},
  entries:['entry','tail_entry'].map(role=>({role,export:role,table:role==='entry'?'public':'tail',
   function_index:x.exports.find(e=>e.name===role).index,signature:signatures[role],range:ranges.find(e=>e.role===role)}))};
}
