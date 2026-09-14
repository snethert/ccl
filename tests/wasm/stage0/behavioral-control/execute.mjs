import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {cases,check} from './assertions.mjs';
const [binary,out]=process.argv.slice(2);
const result={version:1,evidence_kind:'HAND-BUILT WASM CONTROL STIMULUS',status:'FAIL',cases:[],
  binary_sha256:createHash('sha256').update(fs.readFileSync(binary)).digest('hex'),node:process.version,v8:process.versions.v8};
try {
  const tag=new WebAssembly.Tag({parameters:['i32']});
  const instance=new WebAssembly.Instance(new WebAssembly.Module(fs.readFileSync(binary)),{host:{escape:tag}});
  const e=instance.exports,words=new Int32Array(e.memory.buffer),closures=[e.make(17),e.make(100)];
  result.closures=closures;
  for(const c of cases) {
    words.fill(0,64/4,88/4);words[128/4]=c.delta*4;words[132/4]=Number(c.exception);
    let returned=null,condition=null,exception=false;
    try {returned=e.invoke(closures[c.closure],2);}
    catch(error) {
      if(!(error instanceof WebAssembly.Exception)||!error.is(tag))throw error;
      exception=true;condition=error.getArg(tag,0);
    }
    const env=words[(closures[c.closure]+4)/4];
    const observed={name:c.name,returned,condition,exception,nvalues:e.nvalues.value,
      values:Array.from(words.subarray(64/4,88/4),x=>x>>2),factory_active:e.factory_active.value,
      log:Array.from(words.subarray(192/4,192/4+e.log_count.value)),cleanup_effect:e.cleanup_effect.value,
      capture:[words[env/4]>>2,words[env/4+1],words[env/4+2]>>2]};
    result.cases.push(observed);check(observed,c);
  }
  result.status='PASS';
} catch(error) {result.error={name:error.name,message:error.message,code:error.code,stack:error.stack};}
fs.writeFileSync(out,JSON.stringify(result,null,2)+'\n');
process.exitCode=result.status==='PASS'?0:1;
