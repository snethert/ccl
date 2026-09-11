import fs from 'node:fs';
import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {clang,ld,wat,checkLLVM} from '../runtime-boundary/toolchain.mjs';
import {preflight} from '../runtime-boundary/binary.mjs';
import {programWat} from './program.mjs';
export const here=path.dirname(fileURLToPath(import.meta.url));
export const repo=path.resolve(here,'../../../..');
export const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
export const fileSha=p=>sha(fs.readFileSync(p));
export const save=(p,r)=>fs.writeFileSync(p,JSON.stringify(r,null,2)+'\n');
export function build(out,prerequisite) {
  const log=[];
  function command(executable,args) {
    const r=spawnSync(executable,args,{cwd:repo,encoding:'utf8',timeout:30000});
    log.push({executable,args,status:r.status,signal:r.signal,error:r.error?.message,stdout:r.stdout,stderr:r.stderr});
    save(path.join(out,'build-commands.json'),log);
    if(r.error||r.signal||r.status!==0) throw Error(`frame build failed: ${executable}\n${r.stderr||r.error}`);
    return r.stdout.trim();
  }
  const versions={clang:command(clang,['--version']),linker:command(ld,['--version']),wabt:command(wat,['--version']),node:process.version,v8:process.versions.v8};
  checkLLVM(versions.clang,versions.linker);
  versions.paths={clang,linker:ld,wabt:wat};versions.executable_sha256={clang:fileSha(clang),linker:fileSha(ld),wabt:fileSha(wat)};
  fs.cpSync(path.join(prerequisite,'source'),path.join(out,'source'),{recursive:true});
  fs.cpSync(here,path.join(out,'source/debug-frames'),{recursive:true});
  const schema=JSON.parse(fs.readFileSync(path.join(here,'schema.json')));
  assert.ok((16+6*3+schema.frame_capacity*(12+8*6))*4<=schema.reply_bytes,'maximum inspection exceeds reply capacity');
  const runtime=JSON.parse(fs.readFileSync(path.join(prerequisite,'source/integrated-runtime/schema.json')));
  const combined={...runtime,tcr:{...runtime.tcr,...schema.tcr}};
  const inputs=fs.readdirSync(here).sort().map(n=>({path:'debug-frames/'+n,sha256:fileSha(path.join(here,n))}));
  for(const name of ['kernel.o','boundary.o']) inputs.push({path:'prerequisite/'+name,sha256:fileSha(path.join(prerequisite,name))});
  const baseId=sha(Buffer.from(JSON.stringify({inputs,versions,scope:'S0-LL23-b',schema})));
  const include=path.join(out,'source/debug-frames/build-id.h');
  fs.writeFileSync(include,'#ifndef BUILD_ID_WORDS\n#error A build-bound identifier is required\n#endif\n');
  function kernel(name,defines=[]) {
    const stem=path.join(out,name);fs.mkdirSync(path.dirname(stem),{recursive:true});
    const buildId=sha(Buffer.from(baseId+'\n'+defines.join('\n')));
    const words=buildId.match(/.{8}/g).map(x=>'0x'+x+'u');
    command(clang,['--target=wasm32-unknown-unknown','-O1','-ffreestanding','-fno-builtin','-fno-stack-protector','-matomics','-mbulk-memory',
      ...defines.map(d=>'-D'+d),'-DBUILD_ID_WORDS={'+words.join(',')+'}','-c',path.join(out,'source/debug-frames/frames.c'),'-o',stem+'.o']);
    command(ld,['--no-entry','--import-memory','--import-table','--shared-memory','--initial-memory=524288','--max-memory=1048576',
      '-z','stack-size=16384','--fatal-warnings','--export-all','--export=__stack_pointer','--export=__tls_base',
      '--Map='+stem+'.map',path.join(prerequisite,'boundary.o'),path.join(prerequisite,'kernel.o'),stem+'.o','-o',stem+'.wasm']);
    fs.writeFileSync(stem+'.disassembly.txt',command('wasm-objdump',['-dx',stem+'.wasm']));
    const bytes=fs.readFileSync(stem+'.wasm');return {bytes,metadata:preflight(bytes,combined),buildId};
  }
  function emit(name,options={}) {
    const stem=path.join(out,name);fs.mkdirSync(path.dirname(stem),{recursive:true});
    fs.writeFileSync(stem+'.wat',programWat(runtime,schema,options));
    command(wat,['--enable-threads','--enable-exceptions','--enable-tail-call',stem+'.wat','-o',stem+'.wasm']);
    return fs.readFileSync(stem+'.wasm');
  }
  const normal=kernel('kernel'),program=emit('program');
  const sourceLines=fs.readFileSync(path.join(out,'program.wat'),'utf8').split('\n');
  const sourceMap={version:1,build_id:normal.buildId,source:'program.wat',source_sha256:fileSha(path.join(out,'program.wat')),sites:{}};
  for(const [index,line] of sourceLines.entries()) {
    const m=line.match(/;; @site ([0-9,]+) (\S+) (\S+)/);if(!m)continue;
    for(const site of m[1].split(',')) {
      assert.ok(!sourceMap.sites[site]);
      sourceMap.sites[site]={function:m[2],operation:m[3],line:index+2,text:sourceLines[index+1].trim()};
    }
  }
  assert.deepEqual(Object.keys(sourceMap.sites).sort(),schema.codes.flatMap(c=>Object.keys(c.sites)).sort());
  save(path.join(out,'source-sites.json'),sourceMap);
  const mutants={};
  for(const [name,define] of Object.entries({rejectLiveHandle:'MUTANT_REJECT_LIVE_HANDLE',staleSlot:'MUTANT_STALE_SLOT',reusedGeneration:'MUTANT_REUSED_GENERATION',
    fabricatedValue:'MUTANT_FABRICATED_VALUE',wrongLexicalId:'MUTANT_WRONG_LEXICAL_ID',missingRoot:'MUTANT_MISSING_ROOT'}))
    mutants[name]=kernel('quarantine/'+name,[define]);
  const programMutants={wrongSite:emit('quarantine/wrongSite',{wrongSite:true}),wrongVersion:emit('quarantine/wrongVersion',{wrongVersion:true}),omitRestore:emit('quarantine/omitRestore',{omitRestore:true})};
  save(path.join(out,'build-identity.json'),{baseId,normal:normal.buildId,mutants:Object.fromEntries(Object.entries(mutants).map(([k,v])=>[k,v.buildId])),inputs,versions});
  save(path.join(out,'linked-metadata.json'),normal.metadata);
  return {schema:combined,frameSchema:schema,sourceMap,sourceLines,versions,buildId:normal.buildId,kernel:normal.bytes,metadata:normal.metadata,program,mutants,programMutants,
    emitted:fs.readFileSync(path.join(prerequisite,'emitted.wasm')),manifest:JSON.parse(fs.readFileSync(path.join(prerequisite,'entry-manifest.json')))};
}
