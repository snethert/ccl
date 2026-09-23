import assert from 'node:assert/strict';
import fs from 'node:fs';
const [dir,output]=process.argv.slice(2);
const {processOwner}=await import(new URL('file://'+dir+'/process.mjs'));
const bindings=JSON.parse(fs.readFileSync(dir+'/ready-bindings.json'));
const checks=[];
for(const fault of [null,'state','entry','missing-owner','ambiguous-owner','function-tag','function-header']){
 const memory=new WebAssembly.Memory({initial:320,maximum:32769,shared:true});
 const view=new DataView(memory.buffer),get=p=>view.getUint32(p,true),put=(p,n)=>view.setUint32(p,n,true);
 const owners=[],ownerWords=new Map();
 for(const [pkg,name,target] of bindings)for(const [p,n] of [[pkg,name],['CCL',target]]){
  const id='s'+owners.length,word=2097158+owners.length*32;
  owners.push({package:p,name:n,id});ownerWords.set(id,word);
  const fn=2200006+owners.length*32;put(word+6,fn);put(fn-6,42);
 }
 const gen={ownerWords,env:{table:new WebAssembly.Table({element:'anyfunc',initial:4096}),
                           tail_table:new WebAssembly.Table({element:'anyfunc',initial:4096})}};
 const original=bindings.map(([pkg,name])=>{
  const row=owners.find(x=>x.package===pkg&&x.name===name),slot=ownerWords.get(row.id)+6;
  return [slot,get(slot)];
 });
 if(fault==='missing-owner')owners.pop();
 if(fault==='ambiguous-owner')owners.push({...owners.at(-1)});
 if(fault==='function-tag')put(ownerWords.get(owners.at(-1).id)+6,0);
 if(fault==='function-header')put(get(ownerWords.get(owners.at(-1).id)+6)-6,250);
 const owner=processOwner(memory,gen,8388608,1048576);let calls=0;
 const invoke=()=>{calls++;
  bindings.forEach(([pkg,name,target],i)=>{
   const targetRow=owners.find(x=>x.package==='CCL'&&x.name===target);
   assert.equal(get(original[i][0]),get(ownerWords.get(targetRow.id)+6));
  });return [37];};
 const call=()=>owner.process(0,()=>{
  assert.deepEqual(owner.start({image:{state:fault==='state'?'ADMITTED':'INSTALLED'},
   entry:fault==='entry'?null:'ready',args:[],owners,get,put,bindings,invoke}),[37]);
 });
 if(fault){
  const reason={state:/READY_IMAGE_NOT_INSTALLED/,entry:/READY_ENTRY_REQUIRED/,
   'missing-owner':/READY binding identity/,'ambiguous-owner':/READY binding identity/,
   'function-tag':/READY function tag/,'function-header':/READY function header/}[fault];
  assert.throws(call,reason);assert.equal(calls,0);assert.equal(get(1174208),3);
  original.forEach(([slot,value])=>assert.equal(get(slot),value,'partial binding publication'));
 }else{call();assert.equal(calls,1);assert.equal(get(1174208),2);}
 checks.push(fault??'installed bindings before invocation');
}
fs.writeFileSync(output,JSON.stringify({status:'PASS',checks},null,2)+'\n');
