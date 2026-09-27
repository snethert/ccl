// Engine construction/limit qualification only; this does not execute Lisp.
import fs from 'node:fs';
import http from 'node:http';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
const [boot,runtime,out,playwright,executableConfig]=process.argv.slice(2);
const executables=executableConfig&&!executableConfig.startsWith('--')?JSON.parse(fs.readFileSync(executableConfig)):{};
const selected=process.argv.find(a=>a.startsWith('--engines='))?.slice(10).split(',')??['chromium','firefox','webkit'];
fs.mkdirSync(out,{recursive:true});
const engines=await import(pathToFileURL(playwright));
const files={'/boot.wasm':boot,'/runtime.wasm':runtime};
const inputs=Object.fromEntries(Object.entries(files).map(([name,path])=>[name,{path,bytes:fs.statSync(path).size,sha256:createHash('sha256').update(fs.readFileSync(path)).digest('hex')}]));
const server=http.createServer((req,res)=>{
 res.setHeader('Cross-Origin-Opener-Policy','same-origin');res.setHeader('Cross-Origin-Embedder-Policy','require-corp');
 if(req.url==='/'){res.setHeader('Content-Type','text/html');res.end('<!doctype html><title>Archive engine check</title>');return;}
 if(!files[req.url]){res.writeHead(404);res.end();return;}
 res.setHeader('Content-Type','application/wasm');fs.createReadStream(files[req.url]).pipe(res);
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const results=[];
try{for(const name of selected){
 let context;
 try{
  context=await engines[name].launchPersistentContext(out+'/'+name+'-profile',{headless:true,timeout:60000,...(executables[name]?{executablePath:executables[name]}:{})});
  const page=context.pages()[0]??await context.newPage();await page.goto('http://127.0.0.1:'+server.address().port+'/');
  const result=await page.evaluate(async inputs=>{
   const results=[];
   for(const [path,expected] of Object.entries(inputs)){
    const bytes=await (await fetch(path)).arrayBuffer(),begin=performance.now();
    const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
    if(digest!==expected.sha256)throw Error('input digest');
    const module=await WebAssembly.compile(bytes),imports=WebAssembly.Module.imports(module),exports=WebAssembly.Module.exports(module);
    if(imports.length!==13||imports.some(i=>!['env','owner','integer','floating'].includes(i.module)))throw Error('import inventory');
    const env={memory:new WebAssembly.Memory({initial:1,maximum:32769,shared:true}),tcr:0,roots:0,code_base:0,code_registry:0,
     table:new WebAssembly.Table({element:'anyfunc',initial:1}),tail_table:new WebAssembly.Table({element:'anyfunc',initial:1}),
     call_error:new WebAssembly.Tag({parameters:['i32']}),type_error:new WebAssembly.Tag({parameters:['i32','i32']}),nonlocal_exit:new WebAssembly.Tag({parameters:['i32']})};
    const unused=()=>{throw Error('unexpected execution');};
    const instance=await WebAssembly.instantiate(module,{env,owner:{ensure:unused},integer:{calculate:unused},floating:{calculate:unused}});
    if(Object.keys(instance.exports).length!==exports.length)throw Error('export inventory');
    results.push({path,sha256:digest,bytes:bytes.byteLength,imports:imports.length,exports:exports.length,constructionMs:performance.now()-begin});
   }
   return {userAgent:navigator.userAgent,crossOriginIsolated,results};
  },inputs);
  results.push({engine:name,executable:executables[name]??engines[name].executablePath(),status:'PASS',...result});
 }catch(error){results.push({engine:name,status:'FAIL',error:String(error)});}
 finally{await context?.close();}
 fs.writeFileSync(out+'/result.json',JSON.stringify({inputs,results,scope:'Compile and instantiate shipped bytes in fresh browser profiles; no Lisp execution or READY qualification.'},null,2)+'\n');
 console.log(JSON.stringify(results.at(-1)));
}}finally{await new Promise(resolve=>server.close(resolve));}
if(results.some(r=>r.status!=='PASS'))process.exitCode=1;
