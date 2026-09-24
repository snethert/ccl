// Native basic streams retain four traced cells and a zero pad.
import fs from 'node:fs';
import assert from 'node:assert/strict';
const [dir,output]=process.argv.slice(2);
const memory=new WebAssembly.Memory({initial:32769,maximum:32769,shared:true});
const view=new DataView(memory.buffer),get=p=>view.getUint32(p,true),put=(p,v)=>view.setUint32(p,v,true);
const bytes=(p,n)=>new Uint8Array(memory.buffer,p,n);
const collector=(await WebAssembly.instantiate(fs.readFileSync(dir+'/collector.wasm'),{env:{memory}})).instance.exports;
const tcr=1024,root=65536,config=1200000,to=3145728,NIL=77825,rows=[];
function setup(base,size){
 bytes(tcr,256).fill(0);bytes(config,96).fill(0);bytes(root,32).fill(0);bytes(base,128).fill(0);bytes(to,128).fill(0xa5);
 for(const [offset,value]of [[48,base+size],[52,base+4096],[56,base],[68,root+8],[72,98304],[128,root],[80,700000],[76,700000],[120,100000],[124,100064],[104,610000]])put(tcr+offset,value);
 put(root+4,1);put(root+8,base+6);
 for(const [offset,value]of [[0,tcr],[16,to],[20,to+4096],[68,32768],[72,1180000],[76,0],[80,1800000]])put(config+offset,value);
}
for(const base of [8388608,2146500608]){
 setup(base,56);put(base,1074);put(base+20,0);
 for(let i=0;i<4;i++){put(base+4+i*4,base+24+i*8+1);put(base+24+i*8,NIL);put(base+28+i*8,i*4);}
 assert.equal(collector.collect(config),0);assert.equal(get(config+84),5,'all four fields traced');
 const moved=get(root+8)-6;
 assert.equal(get(moved),1074);assert.equal(get(moved+20),0);
 for(let i=0;i<4;i++){
  const pair=get(moved+4+i*4);assert(pair>=to&&pair<to+56);
  assert.equal(get(pair-1),NIL);assert.equal(get(pair+3),i*4);
 }
 rows.push({base,status:'FOUR_FIELDS_MOVED'});
 for(const n of [3,5]){
  setup(base,32);put(base,n*256+50);
  for(let i=1;i<8;i++)put(base+i*4,NIL);
  const before=[bytes(base,32).slice(),bytes(root,32).slice(),bytes(tcr,256).slice()];
  assert.equal(collector.collect(config),2,'stream count');
  assert.deepEqual([bytes(base,32),bytes(root,32),bytes(tcr,256)],before);
  rows.push({base,n,status:'COUNT_REFUSED_WITHOUT_PUBLICATION'});
 }
 setup(base,16);put(base,1074);
 const before=[bytes(base,16).slice(),bytes(root,32).slice(),bytes(tcr,256).slice()];
 assert.equal(collector.collect(config),2,'stream extent');
 assert.deepEqual([bytes(base,16),bytes(root,32),bytes(tcr,256)],before);
 rows.push({base,status:'EXTENT_REFUSED_WITHOUT_PUBLICATION'});
}
fs.writeFileSync(output,JSON.stringify({status:'PASS',rows},null,2)+'\n');
console.log('PASS',rows.length,'stream layout checks');
