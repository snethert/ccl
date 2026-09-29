// Serve exact build inputs and unchanged source modules to isolated browser Workers.
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import assert from 'node:assert/strict';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {sha256} from '../../../../runtime/wasm32/sha256.mjs';
import {archiveSource} from '../../stage1/loader-target/archive-source.mjs';
const [boot,level1,checks,library,out,playwright,browserConfig]=process.argv.slice(2);
const measureStartup=process.argv.includes('--startup-timing');
const root=fileURLToPath(new URL('../../../../',import.meta.url));
const engines=await import(pathToFileURL(playwright)),executables=JSON.parse(fs.readFileSync(browserConfig));
const routes=new Map(),preload=[],sources={};
const json=file=>JSON.parse(fs.readFileSync(file));
const input=(file,virtual)=>{
 const bytes=fs.readFileSync(file),url='/input/'+routes.size;
 routes.set(url,file);return {url,bytes:bytes.length,sha256:sha256(bytes),...(virtual?{path:virtual}:{})};
};
const pre=(file,virtual)=>preload.push(input(file,virtual));
const descriptor=a=>({kind:a.kind,digest:a.digest,manifestDigest:a.manifestDigest,function_count:a.function_count,root_cells:a.root_cells});
const artifacts=boot+'/boot/artifacts',manifest=json(artifacts+'/manifest.json');
const bootArchive=archiveSource(artifacts,manifest.archive,'boot');
const runtimeArchives=[level1,checks].flatMap(dir=>{const a=json(dir+'/bundle-manifest.json').archive;return a?[archiveSource(dir,a)]:[];});
const archives=[bootArchive,...runtimeArchives].map(a=>({...descriptor(a),binary:input(a.binaryPath),metadata:input(a.metadataPath)}));
for(const name of ['manifest.json','heap-image.json','static.bin','heap.payload.bin'])pre(artifacts+'/'+name,'/boot/boot/artifacts/'+name);
for(const name of ['policy.json','versions.json','host-call-adapter.wasm','observe.wasm'])pre(boot+'/'+name,'/boot/'+name);
for(const name of ['array-runtime.json','collector.wasm','integer.wasm','float.wasm','detector.wasm'])pre(boot+'/runtime-binaries/'+name,'/runtime/'+name);
pre(root+'runtime/wasm32/collector.c','/source/runtime/wasm32/collector.c');
pre(root+'tests/wasm/stage1/loader-target/boot-worker.mjs','/source/tests/wasm/stage1/loader-target/boot-worker.mjs');
// Hash the executed local module graph, including dynamically imported source.
function bind(file){
 const relative=path.relative(root,file);if(Object.hasOwn(sources,relative))return;
 const bytes=fs.readFileSync(file),text=bytes.toString();sources[relative]=sha256(bytes);
 for(const match of text.matchAll(/(?:from\s*|import\s*)['"]([^'"]+)['"]/g)){
  if(match[1].startsWith('.'))bind(path.resolve(path.dirname(file),match[1]));
 }
}
bind(fileURLToPath(new URL('./host.mjs',import.meta.url)));bind(fileURLToPath(new URL('./worker.mjs',import.meta.url)));
const files=[];
for(const dir of [level1,checks])for(const row of json(dir+'/bundle-manifest.json').files){
 const source=input(dir+'/'+row.bundle);assert.equal(source.sha256,row.sha256);
 files.push({...source,path:row.path});
}
const config={preload,files,archives,library:input(library),workerData:{
 measureStartup,out:'/boot',runtime:'/runtime',archives:runtimeArchives.map(descriptor),bootArchive:descriptor(bootArchive),
 layoutConfig:{freeTarget:0},startupLoads:[],postReadyLoads:['/ccl/bin/loader-benchmark.w32fsl'],omittedBundles:[],
 callbackSelection:json(root+'tests/wasm/stage1/startup-resets/selection.json'),scripts:sources,
 hostExtension:'foreign-api/fixture.mjs',extensionConfig:{provider:'digest-checked HTTP preload'}}};
fs.mkdirSync(out,{recursive:true});
fs.writeFileSync(out+'/inputs.json',JSON.stringify(config,null,2)+'\n');
fs.writeFileSync(out+'/sources.json',JSON.stringify(sources,null,2)+'\n');
const server=http.createServer((req,res)=>{
 try{
  res.setHeader('Cross-Origin-Opener-Policy','same-origin');res.setHeader('Cross-Origin-Embedder-Policy','require-corp');
  const url=new URL(req.url,'http://localhost').pathname;
  if(url==='/'){res.setHeader('Content-Type','text/html');res.end('<!doctype html><title>Generated Lisp foreign API</title>');return;}
  if(url==='/config.json'){res.setHeader('Content-Type','application/json');res.end(JSON.stringify(config));return;}
  let file=routes.get(url);
  if(url.startsWith('/source/')){
   file=path.resolve(root,decodeURIComponent(url.slice(8)));
   assert(Object.hasOwn(sources,path.relative(root,file)),'undeclared module');
   assert.equal(sha256(fs.readFileSync(file)),sources[path.relative(root,file)],'changed source');
  }
  assert(file,'unknown input');res.setHeader('Content-Type',file.endsWith('.mjs')?'text/javascript':'application/octet-stream');
  fs.createReadStream(file).pipe(res);
 }catch{res.writeHead(404);res.end();}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const results=[];
try{
 for(const name of (measureStartup?['chromium','firefox']:['chromium','firefox','webkit'])){
  let browser;
  try{
   const executable=executables[name];assert(executable,'explicit executable required');
   browser=await engines[name].launch({headless:true,executablePath:executable,timeout:30000,env:{...process.env,TMPDIR:out}});
   const page=await browser.newPage();page.on('console',message=>{if(message.text().startsWith('Lisp: ')||message.text().startsWith('TIMING '))console.log(name+' '+message.text().trim());});await page.goto('http://127.0.0.1:'+server.address().port+'/');
   const report=await page.evaluate(async()=>{
    const {run,readInput}=await import('/source/tests/wasm/stage2/foreign-browser/host.mjs');
    const config=await (await fetch('/config.json')).json(),refusals=[];
    for(const [name,input] of [
     ['HTTP',{...config.library,url:'/absent'}],
     ['SIZE',{...config.library,bytes:config.library.bytes+1}],
     ['DIGEST',{...config.library,sha256:'0'.repeat(64)}]]){
     let reason;try{await readInput(input);}catch(error){reason=String(error);}
     if(reason!=='Error: browser inputs: '+name)throw Error('input refusal '+name+': '+reason);
     refusals.push(name);
    }
    return {...await run(config),inputRefusals:refusals};
   });
   fs.writeFileSync(out+'/'+name+'.json',JSON.stringify(report,null,2)+'\n');
   results.push({engine:name,status:report.ready?'PASS':'FAIL',reason:report.reason??report.error,
    version:browser.version(),executable,executable_sha256:sha256(fs.readFileSync(executable))});
  }catch(error){results.push({engine:name,status:'FAIL',error:String(error)});}
  finally{await browser?.close();}
  fs.writeFileSync(out+'/browser.json',JSON.stringify({results,playwright,playwright_sha256:sha256(fs.readFileSync(playwright))},null,2)+'\n');
  console.log(JSON.stringify(results.at(-1)));
 }
}finally{await new Promise(resolve=>server.close(resolve));}
if(results.some(r=>r.status!=='PASS'))process.exitCode=1;
