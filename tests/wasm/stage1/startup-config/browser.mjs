import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import {pathToFileURL} from 'node:url';
const [dir,playwright,executable,mode]=process.argv.slice(2);
const {chromium}=await import(pathToFileURL(playwright));
const server=http.createServer((req,res)=>{
 res.setHeader('Cross-Origin-Opener-Policy','same-origin');res.setHeader('Cross-Origin-Embedder-Policy','require-corp');
 try{
  const relative=decodeURIComponent(new URL(req.url,'http://localhost').pathname).slice(1),p=path.resolve(dir,relative||'index.html');
  if(!p.startsWith(path.resolve(dir)+path.sep))throw Error('path');
  res.setHeader('Content-Type',p.endsWith('.mjs')?'text/javascript':p.endsWith('.json')?'application/json':p.endsWith('.html')?'text/html':'application/octet-stream');res.end(fs.readFileSync(p));
 }catch{res.writeHead(404);res.end();}
});
await new Promise(r=>server.listen(0,'127.0.0.1',r));let browser;
try{
 browser=await chromium.launch({executablePath:executable,headless:true});
 const page=await browser.newPage();await page.goto('http://127.0.0.1:'+server.address().port+'/');
 const rows=[];
 for(const base of mode==='probe'?[4194304]:[4194304,2147483648])rows.push(await page.evaluate(({base,mode})=>new Promise((resolve,reject)=>{
  const w=new Worker('./worker.mjs?base='+base+'&mode='+mode,{type:'module'}),timer=setTimeout(()=>{w.terminate();reject(Error('Worker timeout'));},180000);
  w.onmessage=e=>{clearTimeout(timer);w.terminate();e.data.error?reject(Error(e.data.error)):resolve(e.data);};
  w.onerror=e=>{clearTimeout(timer);w.terminate();reject(Error(e.message));};
 }),{base,mode}));
 if(mode==='probe')fs.writeFileSync(path.join(dir,'browser-input.json'),JSON.stringify(rows[0],null,2)+'\n');
 else{
  const result={status:'PASS',rows};const node=JSON.parse(fs.readFileSync(path.join(dir,'execution.json')));
  if(JSON.stringify(result)!==JSON.stringify(node))throw Error('BROWSER_NODE_EXECUTION');
  fs.writeFileSync(path.join(dir,'browser.json'),JSON.stringify(result,null,2)+'\n');
 }
 fs.writeFileSync(path.join(dir,'browser-environment.json'),JSON.stringify({engine:browser.version(),crossOriginIsolated:await page.evaluate(()=>crossOriginIsolated),separateWorkerPerPlacement:true},null,2)+'\n');
 console.log(JSON.stringify({status:'PASS',mode,workers:rows.length}));
}finally{await browser?.close();await new Promise(r=>server.close(r));}
