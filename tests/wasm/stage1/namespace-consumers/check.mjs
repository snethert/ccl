import fs from 'node:fs';
import assert from 'node:assert/strict';
import {Worker} from 'node:worker_threads';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {manifest} from './fixtures.mjs';
import {serviceRequest} from '../namespace-primitives/host.mjs';
const dir=process.argv[2];
const {createNamespace}=await import(pathToFileURL(dir+'/runtime/namespace.mjs'));
const namespace=createNamespace(manifest());
const calls=[],handles=new Set();
const result=await new Promise((resolve,reject)=>{
 const worker=new Worker(pathToFileURL(dir+'/namespace-worker.mjs'),{workerData:{dir,base:process.argv.includes('--high')?2146500608:8388608,indices:[0],movement:process.argv.includes('--move'),namespace:process.argv.includes('--namespace'),foreign:process.argv.includes('--foreign'),cclRoot:namespace.cclRoot}});
 const original=namespace.session();
 const session=new Proxy({},{get(target,key){
   const member=original[key];
   if(typeof member!=='function')return member;
   return (...args)=>{
     try{const result=member(...args);
       if(key==='open')handles.add(result);
       if(key==='close')handles.delete(args[0]);
       calls.push({operation:key,args,result:result instanceof Uint8Array?{length:result.length,sha256:createHash('sha256').update(result).digest('hex')}:result});
       return result;
     }catch(e){calls.push({operation:key,args,error:e.code});throw e;}
   };
 }});let memory;
 worker.on('error',reject);worker.on('exit',code=>{if(code)reject(Error('worker '+code));});
 worker.on('message',message=>{try{
  if(message.type==='memory')memory=message.memory;
  else if(message.type==='request')serviceRequest(memory,session,message.lifetime,message.generation);
  else{resolve(message);worker.terminate();}
 }catch(e){reject(e);worker.terminate();}});
});
const owners=new Map(JSON.parse(fs.readFileSync(dir+'/compiled/symbols.json')).map(s=>[s.id,s.package+'::'+s.name]));
function canonical(value){
 if(Array.isArray(value))return value.map(canonical);
 if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).map(([k,v])=>[k,k==='symbol'?owners.get(v):canonical(v)]));
 return value;
}
if(result.type==='done'){
 result.values=canonical(result.values);
 try {
  if(result.foreignValues)assert.deepEqual(canonical(result.foreignValues),[JSON.parse(fs.readFileSync(dir+'/../consumer-native.json.foreign'))],'native 32-bit foreign type observations');
  const reference=JSON.parse(fs.readFileSync(dir+'/../consumer-native.json'));
  const nth=(list,n)=>{while(n--)list=list[1];return list[0];};
  // Native :SUPERSEDE fails while creating a randomly named temporary file.
  // The read-only target rejects the requested pathname before that side
  // effect. Keep both observations and exclude this pathname from equality.
  const actualPath=nth(nth(nth(result.values[0],3),2),1);
  const nativePath=nth(nth(nth(reference[0],3),2),1);
  assert.equal(actualPath.string,'a.bin','read-only refusal identifies the requested file');
  assert.match(nativePath.string,/^\/ccl\/[0-9]+\.tem$/,'native supersede temporary-file refusal');
  result.substitutions=[{case:'OPEN :OUTPUT :SUPERSEDE error pathname',native:{...nativePath},target:{...actualPath},reason:'Refuse writes before creating or renaming a temporary file.'}];
  nativePath.string=actualPath.string;
  assert.deepEqual(result.values,reference,'native consumer observations except the declared supersede pathname');
  assert.equal(handles.size,0,'all opened handles closed');
  result.nativeMatched=true;
 } catch(e) {result.type='failed';result.message=e.stack;}
}
result.calls=calls;result.openHandles=[...handles];
result.base=process.argv.includes('--high')?2146500608:8388608;
result.collectOnRequest=process.argv.includes('--move');
console.log(JSON.stringify({type:result.type,nativeMatched:result.nativeMatched,requests:result.requests,collections:result.collections,message:result.message}));
fs.writeFileSync(dir+'/../consumer-result.json',JSON.stringify(result,null,2)+'\n');
fs.writeFileSync(dir+'/../consumer-result-'+result.base+'-'+result.collectOnRequest+'.json',JSON.stringify(result,null,2)+'\n');
if(result.type!=='done'){
 const body=JSON.stringify(result,null,2)+'\n';
 fs.mkdirSync(dir+'/../development',{recursive:true});
 fs.writeFileSync(dir+'/../development/'+createHash('sha256').update(body).digest('hex')+'.json',body);
}
if(result.type!=='done')process.exitCode=1;
