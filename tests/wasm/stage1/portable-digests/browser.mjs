import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import {pathToFileURL} from 'node:url';
const [dir,playwright,executable]=process.argv.slice(2);
const {chromium}=await import(pathToFileURL(playwright));
const server=http.createServer((req,res)=>{
 res.setHeader('Cross-Origin-Opener-Policy','same-origin');res.setHeader('Cross-Origin-Embedder-Policy','require-corp');
 try{
  const relative=decodeURIComponent(new URL(req.url,'http://localhost').pathname).slice(1),p=path.resolve(dir,relative||'index.html');
  if(!p.startsWith(path.resolve(dir)+path.sep))throw Error('path');
  res.setHeader('Content-Type',p.endsWith('.mjs')?'text/javascript':p.endsWith('.json')?'application/json':p.endsWith('.html')?'text/html':'application/octet-stream');res.end(fs.readFileSync(p));
 }catch{res.writeHead(404);res.end();}
});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
let browser;
try{
 browser=await chromium.launch({executablePath:executable,headless:true});
 const page=await browser.newPage();await page.goto('http://127.0.0.1:'+server.address().port+'/');
 const answers=[];
 for(const base of [1048576,2147483648])answers.push(await page.evaluate(base=>new Promise((resolve,reject)=>{
  const w=new Worker('./worker.mjs?base='+base,{type:'module'}),timer=setTimeout(()=>{w.terminate();reject(Error('Worker timeout'));},180000);
  w.onmessage=e=>{clearTimeout(timer);w.terminate();e.data.error?reject(Error('base '+base+': '+e.data.error)):resolve(e.data);};
  w.onerror=e=>{clearTimeout(timer);w.terminate();reject(Error(e.message));};
 }),base));
 if(JSON.stringify(answers[0].shared)!==JSON.stringify(answers[1].shared))throw Error('Worker shared checks differ');
 const answer={shared:answers[0].shared,binding:answers.flatMap(x=>x.binding)};
 fs.writeFileSync(path.join(dir,'browser.json'),JSON.stringify(answer,null,2)+'\n');
 fs.writeFileSync(path.join(dir,'browser-environment.json'),JSON.stringify({engine:browser.version(),executable,playwright,crossOriginIsolated:await page.evaluate(()=>crossOriginIsolated)},null,2)+'\n');
 const node=JSON.parse(fs.readFileSync(path.join(dir,'node.json')));
 if(JSON.stringify(answer.shared)!==JSON.stringify(node.shared)||JSON.stringify(answer.binding)!==JSON.stringify(node.binding))throw Error('Browser/Node observations differ');
 console.log(JSON.stringify({browser:browser.version(),checks:answer.shared.checks,bindingPlacements:answer.binding.length}));
}finally{await browser?.close();await new Promise(r=>server.close(r));}
