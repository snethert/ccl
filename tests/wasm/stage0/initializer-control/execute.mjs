import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const [bundle,configPath,loaderPath,out]=process.argv.slice(2);
const config=JSON.parse(fs.readFileSync(configPath)),manifest=JSON.parse(fs.readFileSync(path.join(bundle,'manifest.json')));
const result={version:1,evidence_kind:'HAND-BUILT WASM BOOTSTRAP CONTROL STIMULUS',node:process.version,v8:process.versions.v8,config,publications:[],fetches:[]};
try {
  const {bootstrap}=await import(pathToFileURL(loaderPath).href);
  const memory=new WebAssembly.Memory({initial:1,maximum:1}),words=new Int32Array(memory.buffer);
  const failure=new WebAssembly.Tag({parameters:['i32']});
  words[0]=config.fail.reduce((mask,i)=>mask|(1<<i),0);
  const snapshot=()=>({started:Array.from(words.subarray(4,13)),completed:Array.from(words.subarray(16,25)),
    effects:Array.from(words.subarray(48,57)),calls:Array.from(words.subarray(32,32+words[1]))});
  result.report=await bootstrap(manifest,async m=>{
    result.fetches.push(m.id);
    const file=m.id===config.omit?'omitted-'+m.file:m.file;
    return fs.readFileSync(path.join(bundle,file));
  },{memory,failure,diagnostic:config.diagnostic,publish:receipt=>{
    result.publications.push({receipt,snapshot:snapshot()});
    fs.writeFileSync(path.join(out,'boot-ready.json'),JSON.stringify(result.publications.at(-1),null,2)+'\n',{flag:'wx'});
  }});
  result.memory=snapshot();result.ready_artifact=fs.existsSync(path.join(out,'boot-ready.json'));
  process.exitCode=result.report.status==='PASS'?0:1;
} catch(error) {
  result.unexpected={name:error.name,message:error.message,stack:error.stack};process.exitCode=2;
}
fs.writeFileSync(path.join(out,'observed.json'),JSON.stringify(result,null,2)+'\n');
