// One WABT classification and one D2 inventory for a linked archive. The large
// instruction listing is streamed and hashed without becoming a JS string.
import fs from 'node:fs';
import {spawn,execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {createInterface} from 'node:readline';
import {inspect} from '../../../../runtime/wasm32/binary.mjs';
import {entryRanges} from '../../../../runtime/wasm32/ranges.mjs';
import {manifest,materialize} from '../../../../runtime/wasm32/materializer.mjs';
import {sha256} from '../../../../runtime/wasm32/sha256.mjs';
export async function inventoryArchive(stem,policy,versions,archive){
 try {
 execFileSync('/usr/local/bin/wat2wasm',['--enable-all',stem+'.wat','-o',stem+'.template.wasm']);
 const bytes=fs.readFileSync(stem+'.template.wasm');
 const sections=execFileSync('/usr/local/bin/wasm-objdump',['-x',stem+'.template.wasm'],{encoding:'utf8',maxBuffer:64*1024*1024});
 const dump=spawn('/usr/local/bin/wasm-objdump',['-d',stem+'.template.wasm']),hash=createHash('sha256'),ops=new Set();
 let exnref=false,stderr='';
 const done=new Promise((resolve,reject)=>{dump.on('error',reject);dump.on('close',code=>code===0?resolve():reject(Error('objdump: '+stderr)));});
 dump.stderr.on('data',b=>stderr+=b);dump.stdout.on('data',b=>hash.update(b));
 const lines=createInterface({input:dump.stdout,crlfDelay:Infinity});
 const scanned=new Promise((resolve,reject)=>{lines.on('error',reject);lines.on('close',resolve);});
 lines.on('line',line=>{
  const instruction=line.split('|')[1]?.trim();if(instruction)ops.add(instruction.split(/\s+/)[0]);
  if(line.includes('exnref'))exnref=true;
 });
 await Promise.all([done,scanned]);
 const features=[],mnemonics=[...ops].sort();
 if(/-> \([^)]*,/.test(sections))features.push('multivalue');
 if(mnemonics.some(o=>o.startsWith('return_call')))features.push('tailcall');
 if(mnemonics.some(o=>o.includes('.atomic.')))features.push('atomics');
 if(mnemonics.some(o=>['try_table','throw','throw_ref'].includes(o)))features.push('exceptions');
 if(exnref||ops.has('throw_ref'))features.push('exnref');
 if(mnemonics.some(o=>['memory.copy','memory.fill','memory.init','data.drop'].includes(o)))features.push('bulk');
 const classification={binary_sha256:sha256(bytes),features:features.sort(),
  wait:mnemonics.some(o=>o.startsWith('memory.atomic.wait')||o==='memory.atomic.notify'),
  legacy:mnemonics.some(o=>['try','catch','catch_all','delegate','rethrow'].includes(o)),
  instruction_mnemonics:mnemonics,sections_sha256:sha256(sections),instructions_sha256:hash.digest('hex')};
 const x=inspect(bytes,{ownerRetry:true}),abi={minimum:1,maximum:32769,imports:x.imports,
  exports:x.exports.map(e=>({name:e.name,kind:e.kind,index:e.index,signature:x.types[x.functions[e.index]]}))};
 const template=manifest(bytes,abi,classification,policy),full=materialize(bytes,template,abi,classification,policy,'full');
 fs.writeFileSync(stem+'.wasm',full.bytes);
 const bodies=entryRanges(full.bytes,{ownerRetry:true,inspected:x,all:true}),byIndex=new Map(bodies.map(b=>[b.index,b]));
 const ranges=new Map(x.exports.map(e=>[e.name,{role:e.name,...byIndex.get(e.index)}]));
 fs.unlinkSync(stem+'.wat');
 return {...archive,...versions,binary_sha256:full.record.binary_sha256,template_sha256:template.template_sha256,
  helper_bodies:archive.helpers.map((name,i)=>({...bodies[i],name,body_sha256:sha256(full.bytes.subarray(bodies[i].start,bodies[i].end))})),
  d2:{abi,classification,template,outputs:{full:full.record}},entries:archive.functions.map(f=>{
   const entry=ranges.get(f.export+'.entry'),tail_entry=ranges.get(f.export+'.tail_entry');
   return {code_offset:f.code_offset,entry,tail_entry,
    body_sha256:sha256(Buffer.concat([full.bytes.subarray(entry.start,entry.end),full.bytes.subarray(tail_entry.start,tail_entry.end)]))};
  })};
 } catch (error) {
  const split=stem.lastIndexOf('/'), marker=stem.slice(0,split)+'/failure-inputs.json';
  const names=fs.existsSync(marker)?JSON.parse(fs.readFileSync(marker)):[];
  if(fs.existsSync(stem+'.wat'))
   fs.writeFileSync(marker,JSON.stringify([...new Set([...names,stem.slice(split+1)+'.wat'])]));
  throw error;
 }
}
