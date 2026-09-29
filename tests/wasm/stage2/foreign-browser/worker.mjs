// Browser embedding for the same boot Worker used by the Node driver.
import {numericChecks} from './numeric-check.mjs';
import {runBoot} from '../../stage1/loader-target/boot-worker.mjs';
import {createForeignFixture} from '../foreign-api/fixture.mjs';
export function assert(ok, message='assertion') { if(!ok)throw Error(message); }
assert.equal=(actual,expected,message='equality')=>assert(Object.is(actual,expected),`${message}: ${actual} != ${expected}`);
self.onmessage=async ({data})=>{
 if(data.type!=='start')return;
 self.onmessage=null;
 const {workerData,files,library}=data, listeners=new Map();
 let numeric;
 const parentPort={postMessage:message=>self.postMessage(message.type?message:{...message,numericAdmission:numeric}),
  on(_type,listener){const wrapper=e=>listener(e.data);listeners.set(listener,wrapper);self.addEventListener('message',wrapper);},
  off(_type,listener){self.removeEventListener('message',listeners.get(listener));listeners.delete(listener);}};
 try{
  numeric=numericChecks(Object.fromEntries(['collector','integer','float','detector'].map(name=>[name,files.get('/runtime/'+name+'.wasm')])));
  await runBoot({workerData,parentPort,assert,
   readFile:name=>{const path=name instanceof URL?name.pathname:name;assert(files.has(path),'missing input '+path);return files.get(path);},
   writeFile:()=>{throw Error('browser diagnostic file capability unavailable');},
   output:(channel,text)=>self.postMessage({type:'output',channel,text}),
   // Calendar and CPU accounting are absent capabilities in this fixture.
   // processService must refuse if Lisp requests them; elapsed/wall clocks are real.
   environment:{browser:navigator.userAgent,crossOriginIsolated},
   createExtension:context=>createForeignFixture(context,{bytes:library,assert})});
 }catch(error){self.postMessage({status:'FAIL',error:String(error),stack:error.stack});}
};
