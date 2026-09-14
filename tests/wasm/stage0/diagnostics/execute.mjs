import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {decode} from './map.mjs';
const [directory,configPath,reporterPath,output]=process.argv.slice(2);
const config=JSON.parse(fs.readFileSync(configPath));
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const result={version:1,scope:'HAND-BUILT WASM DIAGNOSTIC FIXTURE',node:process.version,v8:process.versions.v8,
  configuration:config,instantiated:false,returns:[],exceptions:[]};
try {
  const manifestBytes=fs.readFileSync(path.join(directory,'manifest.json')),manifest=JSON.parse(manifestBytes);
  const names=['module.wasm','template.wat','source.wat','abi.json','options.json','host-compiler.json'];
  if(manifest.version!==1||JSON.stringify(Object.keys(manifest.files).sort())!==JSON.stringify([...names].sort()))throw Error('BUILD_MANIFEST');
  const files={};for(const name of names){files[name]=fs.readFileSync(path.join(directory,name));
    if(sha(files[name])!==manifest.files[name])throw Error('BUILD_FILE_IDENTITY '+name);}
  const abi=JSON.parse(files['abi.json']);
  const map=decode(files['module.wasm'],abi);
  const mapBytes=fs.readFileSync(path.join(directory,'map.json'));
  if(sha(mapBytes)!==manifest.map_sha256||JSON.stringify(JSON.parse(mapBytes))!==JSON.stringify(map))throw Error('BUILD_MAP_IDENTITY');
  result.build={manifest_sha256:sha(manifestBytes),binary_sha256:sha(files['module.wasm']),module:manifest.module};
  result.map=map;
  const {reporter}=await import(pathToFileURL(reporterPath).href);
  const diag=reporter(result.build,map);let observed=null;
  const instance=await WebAssembly.instantiate(files['module.wasm'],{host:{observed:event=>{
    observed={event_id:event,logical_code_id:703};
    if(config.host_error)throw Error('H'.repeat(4096));
  }}});
  result.instantiated=true;
  for(const invocation of config.calls){observed=null;
    try{result.returns.push(instance.instance.exports[invocation.export](invocation.argument));}
    catch(error){
      result.exceptions.push({name:error.name,message:error.message,wasm_locations:String(error.stack??'').split('\n').filter(l=>l.includes('wasm://'))});
      if(config.hide_stack)error.stack='unsupported engine stack format';
      if(config.obscure_top){const lines=String(error.stack).split('\n');lines[1]='    at wasm://unsupported-top-frame';error.stack=lines.join('\n');}
      diag.capture(error,observed);
    }
  }
  result.report=diag.report;
  const rendered=JSON.stringify(diag.report);result.diagnostic_bytes=Buffer.byteLength(rendered);
  fs.writeFileSync(path.join(output,'diagnostics.json'),rendered+'\n');
  result.status='OBSERVED';
} catch(error){result.status=result.instantiated?'HARNESS_FAILURE':'PRE_EXECUTION_REFUSAL';result.error={name:error.name,message:error.message};}
fs.writeFileSync(path.join(output,'observed.json'),JSON.stringify(result,null,2)+'\n');
