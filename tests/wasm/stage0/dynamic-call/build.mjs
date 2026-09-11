import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {clang,ld,wat,checkLLVM} from '../runtime-boundary/toolchain.mjs';
import {preflight} from '../runtime-boundary/binary.mjs';
import {supportWat} from './support.mjs';
import {functionWat,stubWat} from './functions.mjs';
export const here=path.dirname(fileURLToPath(import.meta.url));
export const repo=path.resolve(here,'../../../..');
export const sha=b=>createHash('sha256').update(b).digest('hex');
export const save=(p,x)=>fs.writeFileSync(p,JSON.stringify(x,null,2)+'\n');
export function build(out,prerequisite,{mutant={},candidate}={}) {
  fs.mkdirSync(out,{recursive:true});
  const schema=JSON.parse(fs.readFileSync(path.join(here,'schema.json')));
  const runtime=JSON.parse(fs.readFileSync(path.join(prerequisite,'source/integrated-runtime/schema.json')));
  save(path.join(out,'build-configuration.json'),{candidate:candidate||'all',mutant,prerequisites:Object.fromEntries(['kernel.o','boundary.o','emitted.wasm'].map(p=>[p,sha(fs.readFileSync(path.join(prerequisite,p)))]))});
  const log=[];
  function command(executable,args) {
    const r=spawnSync(executable,args,{cwd:repo,encoding:'utf8',timeout:30000});
    log.push({executable,args,status:r.status,signal:r.signal,error:r.error?.message,stdout:r.stdout,stderr:r.stderr});save(path.join(out,'build-commands.json'),log);
    if(r.status!==0||r.error||r.signal)throw Error(`ABI build failed: ${executable}\n${r.stderr||r.error}`);
    return r.stdout.trim();
  }
  const versions={clang:command(clang,['--version']),linker:command(ld,['--version']),wabt:command(wat,['--version']),node:process.version,v8:process.versions.v8};
  checkLLVM(versions.clang,versions.linker);
  versions.paths={clang,linker:ld,wabt:wat};versions.executable_sha256=Object.fromEntries(Object.entries(versions.paths).map(([n,p])=>[n,sha(fs.readFileSync(p))]));
  fs.cpSync(path.join(prerequisite,'source'),path.join(out,'source'),{recursive:true});
  fs.cpSync(here,path.join(out,'source/dynamic-call'),{recursive:true});
  command(clang,['--target=wasm32-unknown-unknown','-O1','-ffreestanding','-fno-builtin','-fno-stack-protector','-matomics','-mbulk-memory',
    '-c',path.join(out,'source/dynamic-call/abi.c'),'-o',path.join(out,'abi.o')]);
  command(ld,['--no-entry','--import-memory','--import-table','--shared-memory','--initial-memory=524288','--max-memory=1048576',
    '-z','stack-size=16384','--fatal-warnings','--export-all','--export=__stack_pointer','--export=__tls_base',
    '--Map='+path.join(out,'kernel.map'),path.join(prerequisite,'boundary.o'),path.join(prerequisite,'kernel.o'),path.join(out,'abi.o'),'-o',path.join(out,'kernel.wasm')]);
  const kernel=fs.readFileSync(path.join(out,'kernel.wasm')), metadata=preflight(kernel,runtime);
  const first=Math.max(8,...metadata.reservedSlots.map(s=>s+1));
  const slots={first,minimum:first+schema.entries.length*3+3,entries:schema.entries.map((e,i)=>({...e,G:first+i*3,direct:first+i*3+1,adapter:first+i*3+2})),wrong:first+schema.entries.length*3};
  function emit(name,text) {
    const p=path.join(out,name);fs.mkdirSync(path.dirname(p),{recursive:true});fs.writeFileSync(p+'.wat',text);
    command(wat,['--enable-threads','--enable-exceptions','--enable-tail-call',p+'.wat','-o',p+'.wasm']);
    const bytes=fs.readFileSync(p+'.wasm');if(!WebAssembly.validate(bytes))throw Error('engine rejected '+name);return bytes;
  }
  const candidates={};
  for(const [name,k] of Object.entries(schema.candidates)) {
    if(candidate&&name!==candidate)continue;
    const support=emit(name+'/support',supportWat(runtime,schema,k,slots,mutant));
    const stub=emit(name+'/stub',stubWat(runtime,schema,k,slots,mutant));
    const debug={version:1,candidate:name,scope:'Hand-built lexical surrogates; source locations identify emitted WAT.',descriptors:{}};
    const modules=schema.entries.map(entry=>{
      let text=functionWat(runtime,schema,k,slots,entry,mutant);
      if(entry.code===10&&mutant.profile)text=text.replace('(memory 8 16 shared)','(memory 8 16)');
      if(entry.code===10&&mutant.unauthorizedStart)text=text.slice(0,-1)+' (func $initialize) (start $initialize))';
      const bytes=emit(name+'/'+entry.name,text);
      const sites={};
      for(const [file,kind] of [[entry.name,'site'],['stub','stub-site']]) {
        const source=fs.readFileSync(path.join(out,name,file+'.wat'),'utf8');
        source.split('\n').forEach((line,i)=>{const m=line.match(new RegExp('@'+kind+' ([0-9,]+) (.+)$'));if(m)for(const id of m[1].split(','))sites[kind==='site'?Number(id):entry.code*100+Number(id)]={path:name+'/'+file+'.wat',sha256:sha(Buffer.from(source)),line:i+2,description:m[2]};});
      }
      const bindings=Array.from({length:33},(_,i)=>({id:entry.code+':'+entry.version+':'+i,name:i?'arg'+(i-1):'self',package:null,offset:136+Math.floor(i/8)*40+(i%8)*4,storage:'tagged frame slot',live_when:i?'nargs >= '+i:'frame live',availability:{1:'unavailable by policy',3:'available'}}));
      debug.descriptors[entry.code]={code:entry.code,version:entry.version,root_descriptor:entry.code,bindings,source_sites:sites};
      return {...entry,bytes,sha256:sha(bytes)};
    });
    const wrong=emit(name+'/wrong-role',`(module (import "env" "table" (table ${slots.minimum} funcref)) (global $entered (export "entered") (mut i32) (i32.const 0))
      (type $F (func (param f64) (result f64)))
      (func (export "entry") (param i32 i32 ${'i32 '.repeat(k)}) (result i32 i32) (global.set $entered (i32.const 2)) (i32.const -300) (i32.const 1))
      (func (export "signature") (param f64) (result f64) (global.set $entered (i32.add (global.get $entered) (i32.const 1))) (local.get 0))
      (func (export "probe") (param f64) (result f64) (call_indirect (type $F) (local.get 0) (i32.const ${slots.wrong+1}))))`);
    save(path.join(out,name,'debug-metadata.json'),debug);
    candidates[name]={k,support,stub,modules,wrong,debug};
  }
  save(path.join(out,'linked-metadata.json'),metadata);save(path.join(out,'entries.json'),slots);save(path.join(out,'toolchain.json'),versions);
  return {schema,runtime,kernel,metadata,slots,candidates,versions,emitted:fs.readFileSync(path.join(prerequisite,'emitted.wasm'))};
}
