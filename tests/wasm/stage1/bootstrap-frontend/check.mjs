import fs from 'node:fs';
import assert from 'node:assert/strict';
import {Worker,isMainThread,parentPort,workerData} from 'node:worker_threads';
import {install} from './install.mjs';
if(isMainThread){
  const rows=[];
  for(const base of [262144,2147483648])
    rows.push(await new Promise((resolve,reject)=>{
      const worker=new Worker(new URL(import.meta.url),{workerData:{base,dir:process.argv[2]}});
      worker.on('message',resolve);worker.on('error',reject);
      worker.on('exit',code=>{if(code)reject(Error('worker '+code));});
    }));
  fs.writeFileSync(process.argv[3],JSON.stringify({status:'PASS',rows},null,2)+'\n');
  console.log('PASS:',rows.reduce((n,r)=>n+r.comparisons,0),'native comparisons');
}else{
  const {base,dir}=workerData,NIL=77825,T=77838,tcr=1024,root=131064;
  const config=1200000,size=65536,other=3145728;
  const memory=new WebAssembly.Memory({initial:Math.max(64,Math.ceil((base+size)/65536)),maximum:32769,shared:true});
  const view=new DataView(memory.buffer),get=p=>view.getUint32(p,true),put=(p,n)=>view.setUint32(p,n,true);
  const bytes=(p,n)=>new Uint8Array(memory.buffer,p,n);
  const collector=(await WebAssembly.instantiate(fs.readFileSync(dir+'/collector.wasm'),{env:{memory}})).instance.exports;
  const gen=await install({dir,memory,tcr,get,put});
  const native=JSON.parse(fs.readFileSync(dir+'/compiled/native.json')),rows=[];
  function encode(x){
    if(x===null)return NIL;if(x===true)return T;
    if(typeof x==='number')return (x*4)>>>0;
    assert(Array.isArray(x)&&x.length===2);
    const car=encode(x[0]),cdr=encode(x[1]),p=get(tcr+48);
    assert(p+8<=get(tcr+52));put(p,cdr);put(p+4,car);put(tcr+48,p+8);return p+1;
  }
  function decode(x){
    if(x===NIL)return null;if(x===T)return true;
    if((x&3)===0)return (x|0)>>2;
    assert.equal(x&7,1);return [decode(get(x+3)),decode(get(x-1))];
  }
  let collections=0;
  for(const expected of native){
    bytes(tcr,256).fill(0);bytes(config,96).fill(0);
    for(const [offset,value] of [[48,base],[52,base+size],[56,base],[68,131072],[72,196608],
       [128,root],[80,700000],[76,700000],[84,900000],[120,100000],[124,100064],[104,610000]])put(tcr+offset,value);
    put(config,tcr);put(config+16,other);put(config+20,other+size);
    put(config+68,32768);put(config+72,1180000);put(config+80,1800000);
    const args=expected.args.map(encode);
    put(root,0);put(root+4,args.length);args.forEach((x,i)=>put(root+8+4*i,x));
    // The same untouched definitions run with their arguments in both spaces.
    for(const move of [false,true]){
      if(move){
        // Start with fresh original arguments; the first call may mutate them.
        const fresh=expected.args.map(encode);fresh.forEach((x,i)=>put(root+8+4*i,x));
        const old=get(tcr+56);
        assert.equal(collector.collect(config),0,'collect '+expected.name);
        bytes(old,size).fill(0xda);collections++;
      }
      const actualArgs=args.map((_,i)=>get(root+8+4*i));
      const values=gen.invoke(expected.name,actualArgs).map(decode);
      const after=actualArgs.map(decode);
      assert.deepEqual({values,after},{values:expected.values,after:expected.after},expected.name+' moved='+move);
      rows.push({name:expected.name,moved:move,values,after});
    }
  }
  parentPort.postMessage({base,comparisons:rows.length,collections,rows,...gen.summary()});
}
