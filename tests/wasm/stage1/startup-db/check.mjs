import fs from 'node:fs';
import assert from 'node:assert/strict';
import {Worker,isMainThread,parentPort,workerData} from 'node:worker_threads';
if(isMainThread){
 const rows=[];for(const base of [4194304,2147483648])rows.push(await new Promise((resolve,reject)=>{const w=new Worker(new URL(import.meta.url),{workerData:{dir:process.argv[2],base}});w.once('message',resolve);w.once('error',reject);w.once('exit',c=>{if(c)reject(Error('Worker '+c));});}));
 const summary={status:'PASS',scenarios:rows.reduce((n,r)=>n+r.rows.length,0),refusals:rows.reduce((n,r)=>n+r.refusals.length,0),modules:4,placements:2,slot_credit:false};fs.writeFileSync(process.argv[3],JSON.stringify({summary,rows},null,2)+'\n');
}else{
 const {base,dir}=workerData,read=n=>JSON.parse(fs.readFileSync(dir+'/'+n)),NIL=77825,T=77838,TCR=16384,REG=4096,STACK=32768,RESULT=2048000,DONE=2300000,HT=2300033,DT=2300041;
 const memory=new WebAssembly.Memory({initial:32769,maximum:32769,shared:true}),v=new DataView(memory.buffer),get=p=>v.getUint32(p,true),put=(p,x)=>v.setUint32(p,x,true);
 const service=(await WebAssembly.instantiate(fs.readFileSync(dir+'/db.wasm'),{env:{memory}})).instance.exports;
 const table=new WebAssembly.Table({element:'anyfunc',initial:32}),tail_table=new WebAssembly.Table({element:'anyfunc',initial:32}),call_error=new WebAssembly.Tag({parameters:['i32']}),type_error=new WebAssembly.Tag({parameters:['i32','i32']}),nonlocal_exit=new WebAssembly.Tag({parameters:['i32']});
 const env={memory,tcr:TCR,table,tail_table,code_registry:REG,call_error,type_error,nonlocal_exit},adapter=new WebAssembly.Module(fs.readFileSync(dir+'/adapter.wasm'));
 function register(id,x){[id,4,17,23].forEach((n,j)=>put(REG+8+16*id+4*j,n));table.set(id,x.exports.entry);tail_table.set(id,x.exports.tail_entry);}
 function object(id){const p=2100000+32*id;[1578,4*id,NIL,4,NIL,NIL,NIL,0].forEach((n,j)=>put(p+4*j,n));return p+6;}
 put(REG,32);put(REG+4,1);const operation=object(1),entries=[],symbols={};
 const mat=read('compiled/materialized.json');assert.equal(mat.image,'');assert(mat.roots.every(x=>x===NIL));
 for(const [i,m] of read('compiled/modules.json').entries()){
  const mod=new WebAssembly.Module(fs.readFileSync(dir+'/compiled/'+m.name+'.wasm'));
  for(const imp of WebAssembly.Module.imports(mod))if(imp.module==='symbols'&&!(imp.name in symbols)){
   const p=2200000+32*Object.keys(symbols).length;[1850,NIL,NIL,NIL,NIL,0,NIL,0].forEach((n,j)=>put(p+4*j,n));symbols[imp.name]=p+6;
  }
  const inst=new WebAssembly.Instance(mod,{env,symbols});register(i+2,inst);entries.push({name:m.name,self:object(i+2),fn:inst.exports.entry});
 }
 put(77824,NIL);put(77828,NIL);put(77832,1850);for(let j=3;j<16;j++)put(77824+4*j,NIL);
 put(HT-1,NIL);put(HT+3,NIL);put(DT-1,NIL);put(DT+3,T);
 const head=base+6,node=i=>base+24+56*i+6,words=Array.from({length:64},(_,j)=>4*j).filter(x=>x!==116),rows=[],refusals=[];let end;
 function setup(count,reverse=false){
  end=base+24+56*count;new Uint8Array(memory.buffer,base,end-base+16).fill(0x96);
  [4*256+122,HT,head,head,364,0].forEach((n,j)=>put(base+4*j,n));
  const order=Array.from({length:count},(_,j)=>j);if(reverse)order.reverse();
  put(base+8,count?node(order.at(-1)):head);put(base+12,count?node(order[0]):head);
  for(let k=0;k<count;k++){
   const i=order[k],p=node(i)-6;[12*256+122,DT,k?node(order[k-1]):head,k+1<count?node(order[k+1]):head,4*(100+i),4*(500+i),...Array.from({length:7},(_,j)=>4*(16*i+j+5)),0].forEach((n,j)=>put(p+4*j,n));
  }
  new Uint8Array(memory.buffer,TCR,256).fill(0);new Uint8Array(memory.buffer,STACK,32768).fill(0);
  for(const [o,x]of [[0,TCR],[48,131072],[52,135168],[56,131072],[64,STACK+512],[68,STACK+16],[72,STACK+32768],[76,8192],[80,8192],[84,12288],[88,12288],[92,12288],[96,16384],[104,139264],[108,0],[120,STACK+1024],[124,STACK+1088],[128,STACK+8],[136,NIL],[200,7]])put(TCR+o,x);
  put(DONE,NIL);put(DONE+4,0);
  const inst=new WebAssembly.Instance(adapter,{env,hash:{run:service.db_run,collect:()=>{throw Error('unexpected collection');},config:0,operation:5,scratch:base,scratch_end:end,result:RESULT}});register(1,inst);
 }
 function snapshot(){return Uint8Array.from(new Uint8Array(memory.buffer,base,end-base+16));}
 function expected(before,count){const b=Uint8Array.from(before),d=new DataView(b.buffer);for(let i=0;i<count;i++)for(let slot=5;slot<12;slot++)d.setUint32(24+56*i+4+4*slot,NIL,true);return b;}
 const poison=()=>[NIL,NIL,1,0].map(x=>(~x)>>>0).forEach((x,j)=>put(RESULT+4*j,x));
 for(const native of read('compiled/native.json'))for(const reversed of [false,true]){
  const count=native.count;assert.equal(native.header_words,4);assert.equal(native.node_words,12);assert.deepEqual(native.cleared_slots,[5,6,7,8,9,10,11]);
  for(const name of ['raw','reset_db','reset_db_cleanup','reset_db_dynamic']){
   setup(count,reversed);const before=snapshot(),wanted=expected(before,count),saved=words.map(o=>get(TCR+o));poison();
   if(name==='raw'){
    assert.equal(service.db_run(head,base+24,5,HT,DT,base,end,RESULT),0,'raw status');assert.deepEqual(Array.from({length:4},(_,j)=>get(RESULT+4*j)),[NIL,NIL,1,0],'DB publication');
   }else{
    const entry=entries.find(e=>e.name===name),args=name==='reset_db_dynamic'?[operation,entries.find(e=>e.name==='reset_db_receiver').self,head,HT,DT,DONE+1]:[operation,head,HT,DT,DONE+1];
    args.forEach((x,j)=>put(STACK+512+4*j,x));let pair;
    try{pair=entry.fn(entry.self,args.length);}catch(e){throw Error(name+' '+(e.is?.(call_error)?'CHECKED_'+e.getArg(call_error,0):String(e)));}
    assert.equal(pair[0]>>>0,native.values[0],'native return');assert.equal(pair[1],name==='reset_db_dynamic'?2:1);assert.equal(get(TCR+116),pair[1]);
    for(let j=0;j<pair[1];j++)assert.equal(get(STACK+1024+4*j),NIL,'native values');
    assert.equal(get(DONE+4),4*({reset_db:401,reset_db_cleanup:402,reset_db_dynamic:403}[name]),'completion');
   }
   assert.deepEqual(snapshot(),wanted,'DB slots and preserved metadata');assert.deepEqual(words.map(o=>get(TCR+o)),saved,'TCR restoration');
   poison();assert.equal(service.db_run(head,base+24,5,HT,DT,base,end,RESULT),0);assert.deepEqual(Array.from({length:4},(_,j)=>get(RESULT+4*j)),[NIL,NIL,1,0],'idempotent publication');assert.deepEqual(snapshot(),wanted,'idempotence');
   rows.push({count,reversed,name,cleared:7*count,metadata_preserved:true});
  }
 }
 for(const [name,edit]of [
  ['header tag',a=>a[0]++],['header extent',a=>a[1]+=8],['owner extent',a=>a[6]--],['result alias',a=>a[7]=base],['wrong operation',a=>a[2]=4],['wrong header type',a=>a[3]=DT],['wrong dir type',a=>a[4]=HT],
  ['node header',()=>put(base+24,0)],['node descriptor',()=>put(base+28,HT)],['foreign successor',()=>put(base+12,DONE+6)],['interior successor',()=>put(base+12,node(0)+8)],['early end',()=>put(base+12,head)],['broken predecessor',()=>put(base+24+8,head+8)],['cycle',()=>put(base+24+12,node(0))],['wrong last',()=>put(base+8,head)],
 ]){
  setup(2);const a=[head,base+24,5,HT,DT,base,end,RESULT];edit(a);poison();const before=snapshot(),pub=Uint8Array.from(new Uint8Array(memory.buffer,RESULT,16)),saved=words.map(o=>get(TCR+o));const status=service.db_run(...a);assert(status,'DB refusal '+name);
  assert.deepEqual(snapshot(),before,'DB refusal preserves image');assert.deepEqual(new Uint8Array(memory.buffer,RESULT,16),pub,'DB refusal preserves publication');assert.deepEqual(words.map(o=>get(TCR+o)),saved);refusals.push({name,status});
 }
 parentPort.postMessage({base,rows,refusals});
}
