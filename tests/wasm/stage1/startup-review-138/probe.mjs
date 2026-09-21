import fs from 'node:fs';import assert from 'node:assert/strict';
const [kind,binary,output,only='all']=process.argv.slice(2),NIL=77825,rows=[];
for(const base of [262144,2147483648]){
 const memory=new WebAssembly.Memory({initial:Math.max(64,Math.ceil((base+65536)/65536)),maximum:32769,shared:true});
 const service=(await WebAssembly.instantiate(fs.readFileSync(binary),{env:{memory}})).instance.exports;
 const d=new DataView(memory.buffer),put=(p,v)=>d.setUint32(p,v,true),bytes=(p,n)=>new Uint8Array(memory.buffer,p,n),limit=memory.buffer.byteLength,result=2048000;
 const checked=(name,call,code)=>{let actual;try{actual=call();}catch(e){assert.fail(name+': trapped instead of refusal: '+e);}assert.equal(actual,code,name);};
 if(kind==='population'){
  const cases=[
   {name:'object backed',object:limit+6,end:limit+16,code:2},
   {name:'result backed',result:limit-8,code:1},
   {name:'key backed',key:limit+1,code:3},
   {name:'population header',header:1018,code:2},
   {name:'population type range',type:8,code:2},
   {name:'population padding',pad:1,code:2},
   {name:'key tag',key:28,code:3},
  ];
  for(const row of cases){if(only!=='all'&&only!==row.name)continue;
   bytes(base-16,80).fill(0x5a);bytes(result-16,80).fill(0xa5);bytes(limit-32,32).fill(0xa5);
   [row.header??762,row.type??0,NIL,row.pad??0].forEach((v,i)=>put(base+i*4,v));
   const regions=[[base-16,80],[result-16,80],[limit-32,32]],before=regions.map(([p,n])=>bytes(p,n).slice());
   checked(row.name,()=>service.pop_run(row.object??base+6,row.end??base+16,1,row.key??NIL,NIL,0,0,row.result??result),row.code);
   regions.forEach(([p,n],i)=>assert.deepEqual(bytes(p,n),before[i],row.name+' preservation'));
   rows.push({base,name:row.name,status:row.code});
  }
 }else{
  const end=base+service.ht_size(4),scratch=1900000;
  const run=key=>service.ht_run(base+6,end,1,key,68,scratch,scratch+131072,result);
  const cases=[{name:'cons span',key:limit+1},{name:'header span',key:limit+6},{name:'static opaque header',key:1048582,prepare:()=>put(1048576,42)}];
  for(const row of cases){if(only!=='all'&&only!==row.name)continue;
   assert.equal(service.ht_init(base,end,4),0);bytes(result,16).fill(0xa5);
   row.prepare?.();const before=bytes(base,end-base).slice();checked(row.name,()=>run(row.key),3);
   assert.deepEqual(bytes(base,end-base),before,row.name+' table preservation');assert(bytes(result,16).every(x=>x===0xa5),row.name+' result preservation');rows.push({base,name:row.name,status:3});
  }
  for(const family of ['number','cons']){
   if(family==='cons'&&kind!=='equal')continue;
   if(only!=='all'&&only!==family+' depth')continue;
   for(const depth of [1022,1023,1024,3000]){
    assert.equal(service.ht_init(base,end,4),0);let key=0;const stride=family==='number'?16:8;
    for(let i=0;i<depth;i++){const p=base+2048+i*stride;
     if(family==='number'){put(p,(2<<8)|26);put(p+4,0);put(p+8,key);put(p+12,0);key=p+6;}
     else{put(p,0);put(p+4,key);key=p+1;}
    }
    bytes(result,16).fill(0xa5);const before=bytes(base,end-base).slice(),graph=bytes(base+2048,depth*stride).slice();
    const code=depth<=1023?0:3;checked(family+' depth '+depth,()=>run(key),code);
    assert.deepEqual(bytes(base+2048,depth*stride),graph,family+' key preservation');
    if(code){assert.deepEqual(bytes(base,end-base),before,family+' table preservation');assert(bytes(result,16).every(x=>x===0xa5),family+' result preservation');}
    rows.push({base,name:family+' depth',depth,status:code});
   }
  }
 }
}
fs.writeFileSync(output,JSON.stringify({status:'PASS',rows},null,2)+'\n');
