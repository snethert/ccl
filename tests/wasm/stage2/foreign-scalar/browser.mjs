import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
const [dir,playwright,config]=process.argv.slice(2),engines=await import(pathToFileURL(playwright));
const executables=config?JSON.parse(fs.readFileSync(config)):{};
const sha=file=>createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const server=http.createServer((req,res)=>{
  try {
    const relative=decodeURIComponent(new URL(req.url,'http://localhost').pathname).slice(1);
    if(!relative){res.setHeader('Content-Type','text/html');res.end('<!doctype html><title>Foreign scalar qualification</title>');return;}
    const file=path.resolve(dir,relative);if(!file.startsWith(path.resolve(dir)+path.sep))throw Error('path');
    res.setHeader('Content-Type',file.endsWith('.mjs')?'text/javascript':file.endsWith('.json')?'application/json':'application/wasm');
    res.end(fs.readFileSync(file));
  }catch{res.writeHead(404);res.end();}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const results=[];
try {
  for(const name of ['chromium','firefox','webkit']){
    let browser;
    try {
      let executable=executables[name]??engines[name].executablePath();
      // This installed Chromium bundle names the executable with its full product name.
      if(name==='chromium'&&!fs.existsSync(executable)&&fs.existsSync(executable+' for Testing'))executable+=' for Testing';
      browser=await engines[name].launch({headless:true,executablePath:executable,timeout:30000,
        env:{...process.env,TMPDIR:dir}});
      const page=await browser.newPage();await page.goto('http://127.0.0.1:'+server.address().port+'/');
      const result=await page.evaluate(()=>new Promise((resolve,reject)=>{
        const worker=new Worker('./worker.mjs',{type:'module'}),timer=setTimeout(()=>{worker.terminate();reject(Error('Worker timeout'));},30000);
        worker.onmessage=e=>{clearTimeout(timer);worker.terminate();resolve(e.data);};
        worker.onerror=e=>{clearTimeout(timer);worker.terminate();reject(Error(e.message));};
      }));
      results.push({...result,engine:name,version:browser.version(),executable,executable_sha256:sha(executable)});
    }catch(error){results.push({engine:name,status:'FAIL',error:String(error)});}
    finally{await browser?.close();}
    fs.writeFileSync(path.join(dir,'browser.json'),JSON.stringify({results,playwright,playwright_sha256:sha(playwright)},null,2)+'\n');
    console.log(JSON.stringify({engine:name,status:results.at(-1).status,checks:results.at(-1).checks,error:results.at(-1).error}));
  }
}finally{await new Promise(resolve=>server.close(resolve));}
if(results.some(r=>r.status!=='PASS'))process.exitCode=1;
