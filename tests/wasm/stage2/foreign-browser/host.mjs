// Browser namespace owner. Fetches finish outside Lisp execution; synchronous
// file requests use the existing mailbox and namespace provider on the page.
import {bundleNamespace} from '../../../../runtime/wasm32/target-load-session.mjs';
import {serviceRequest} from '../../../../runtime/wasm32/file-host.mjs';
import {sha256} from '../../../../runtime/wasm32/sha256.mjs';
const need=(ok,why)=>{if(!ok)throw Error('browser inputs: '+why);};
export async function readInput(input) {
 const response=await fetch(input.url);need(response.ok,'HTTP');
 const bytes=new Uint8Array(await response.arrayBuffer());
 need(bytes.length===input.bytes,'SIZE');need(sha256(bytes)===input.sha256,'DIGEST');
 return bytes;
}
export async function run(config) {
 need(crossOriginIsolated,'ISOLATION');
 const inputs=new Map();
 for(const input of config.preload)inputs.set(input.path,await readInput(input));
 const files=[];
 for(const file of config.files)files.push({...file,bytes:await readInput(file)});
 const namespace=bundleNamespace({files,retainCode:false}),session=namespace.session();
 const workerFiles=files.map(({path,sha256,bytes})=>{
  const container=namespace.containers.get(path);return {path,sha256,...(container?{container}:{bytes})};});
 const library=await readInput(config.library);
 const worker=new Worker(new URL('./worker.mjs',import.meta.url),{type:'module'});
 let memory,requests=0,archives=0,lastOutput='';
 try{return await new Promise((resolve,reject)=>{
  const timer=setTimeout(()=>reject(Error('browser boot timeout: '+JSON.stringify({requests,archives,lastOutput}))),600000);
  const fail=error=>{clearTimeout(timer);reject(error);};
  worker.onerror=e=>fail(Error(e.message));
  worker.onmessage=async ({data})=>{
   try{
    if(data.type==='output'){lastOutput=data.text;console.log('Lisp: '+data.text);return;}
    if(data.type==='memory'){memory=data.memory;return;}
    if(data.type==='request'){
     need(serviceRequest(memory,session,data.lifetime,data.generation),'FILE_REQUEST');requests++;return;
    }
    if(data.type==='archive-request'){
     const row=config.archives.find(a=>a.digest===data.digest);need(row,'ARCHIVE');
     const bytes=(await readInput(row.binary)).buffer,metadata=(await readInput(row.metadata)).buffer;
     worker.postMessage({type:'archive-input',digest:row.digest,bytes,metadata},[bytes,metadata]);
     need(bytes.byteLength===0&&metadata.byteLength===0,'TRANSFER');archives++;return;
    }
    if(['stderr','progress'].includes(data.type))return;
    clearTimeout(timer);resolve({...data,browserProvider:{requests,archives}});
   }catch(error){fail(error);}
  };
  worker.postMessage({type:'start',workerData:{...config.workerData,files:workerFiles},files:inputs,library});
 });}finally{worker.terminate();}
}
