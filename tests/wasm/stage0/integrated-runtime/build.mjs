import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { preflight } from '../runtime-boundary/binary.mjs';
import { programWat, lazyWat } from './program.mjs';
import { clang, ld, wat, checkLLVM } from '../runtime-boundary/toolchain.mjs';

export const here=path.dirname(fileURLToPath(import.meta.url));
export const repo=path.resolve(here,'../../../..');
export const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
export const fileSha=p=>sha(fs.readFileSync(p));
export const save=(p,value)=>fs.writeFileSync(p,JSON.stringify(value,null,2)+'\n');
export function build(out) {
  const commands=[];
  function command(executable,args) {
    const r=spawnSync(executable,args,{cwd:repo,encoding:'utf8',timeout:30000});
    commands.push({executable,args,status:r.status,signal:r.signal,error:r.error?.message,stdout:r.stdout,stderr:r.stderr});
    save(path.join(out,'build-commands.json'),commands);
    if(r.error||r.signal||r.status!==0) throw Error(`build command failed: ${executable}\n${r.stderr||r.error}`);
    return r.stdout.trim();
  }
  const versions={clang:command(clang,['--version']),linker:command(ld,['--version']),wabt:command(wat,['--version']),node:process.version,v8:process.versions.v8};
  checkLLVM(versions.clang,versions.linker);
  versions.paths={clang,linker:ld,wabt:wat};
  versions.executable_sha256={clang:fileSha(clang),linker:fileSha(ld),wabt:fileSha(wat)};
  const schema=JSON.parse(fs.readFileSync(path.join(here,'schema.json')));
  for(const name of ['integrated-runtime','runtime-boundary'])
    fs.cpSync(path.resolve(here,'..',name),path.join(out,'source',name),{recursive:true});
  const boundary=path.join(out,'source/runtime-boundary/kernel.c'), control=path.join(out,'source/integrated-runtime/control.c');
  const common=['--target=wasm32-unknown-unknown','-O1','-ffreestanding','-fno-builtin','-fno-stack-protector','-matomics','-mbulk-memory'];
  command(clang,[...common,'-c',boundary,'-o',path.join(out,'boundary.o')]);
  function kernel(name,defines=[]) {
    const stem=path.join(out,name); fs.mkdirSync(path.dirname(stem),{recursive:true});
    command(clang,[...common,...defines.map(d=>'-D'+d),'-c',control,'-o',stem+'.o']);
    command(ld,['--no-entry','--import-memory','--import-table','--shared-memory','--initial-memory=524288','--max-memory=1048576',
      '-z','stack-size=16384','--fatal-warnings','--export-all','--export=__stack_pointer','--export=__tls_base',
      '--Map='+stem+'.map',path.join(out,'boundary.o'),stem+'.o','-o',stem+'.wasm']);
    fs.writeFileSync(stem+'.disassembly.txt',command('wasm-objdump',['-dx',stem+'.wasm']));
    const bytes=fs.readFileSync(stem+'.wasm');
    return {bytes,metadata:preflight(bytes,schema)};
  }
  function watModule(name,source) {
    const stem=path.join(out,name); fs.mkdirSync(path.dirname(stem),{recursive:true});
    fs.writeFileSync(stem+'.wat',source);
    command(wat,['--enable-threads','--enable-exceptions',stem+'.wat','-o',stem+'.wasm']);
    return fs.readFileSync(stem+'.wasm');
  }
  const normal=kernel('kernel'), slot=Math.max(...normal.metadata.reservedSlots)+1;
  const emitted=watModule('emitted',fs.readFileSync(path.resolve(here,'../runtime-boundary/emitted.wat'),'utf8'));
  const lazy=watModule('lazy',lazyWat), manifest={slot,sha256:sha(lazy),signature:{params:['i32'],results:['i32']},role:'ordinary-fixture-entry',logical_code_id:1};
  const program=watModule('program',programWat(schema,slot));
  save(path.join(out,'linked-metadata.json'),normal.metadata); save(path.join(out,'entry-manifest.json'),manifest);
  const mutants={};
  for(const [name,define] of Object.entries({fetchAdd:'MUTANT_FETCH_ADD',omitRescan:'MUTANT_OMIT_RESCAN',staleC:'MUTANT_STALE_C_ROOT',prematureReuse:'MUTANT_PREMATURE_REUSE',ownerTrap:'MUTANT_OWNER_TRAP'}))
    mutants[name]=kernel('quarantine/'+name,[define]);
  const staleWasm=watModule('quarantine/staleWasm',programWat(schema,slot,{staleWasmRoot:true}));
  const omitExceptionPark=watModule('quarantine/omitExceptionPark',programWat(schema,slot,{omitExceptionPark:true}));
  return {schema,versions,kernel:normal.bytes,metadata:normal.metadata,emitted,program,lazy,manifest,mutants,staleWasm,omitExceptionPark};
}
