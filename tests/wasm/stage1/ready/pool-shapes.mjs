import fs from 'node:fs';
import assert from 'node:assert/strict';
const [dir,output]=process.argv.slice(2);
const memory=new WebAssembly.Memory({initial:32769,maximum:32769,shared:true});
const view=new DataView(memory.buffer),get=p=>view.getUint32(p,true),put=(p,v)=>view.setUint32(p,v,true);
const bytes=(p,n)=>new Uint8Array(memory.buffer,p,n);
const collector=(await WebAssembly.instantiate(fs.readFileSync(dir+'/collector.wasm'),{env:{memory}})).instance.exports;
const tcr=1024,root=65536,config=1200000,to=3145728,NIL=77825,rows=[];
function setup(base){
 bytes(tcr,256).fill(0);bytes(config,96).fill(0);bytes(root,32).fill(0);bytes(base,32).fill(0);bytes(to,128).fill(0xa5);
 for(const [offset,value]of [[48,base+16],[52,base+4096],[56,base],[68,root+8],[72,98304],[128,root],[80,700000],[76,700000],[120,100000],[124,100064],[104,610000]])put(tcr+offset,value);
 put(root+4,1);put(root+8,base+6);
 for(const [offset,value]of [[0,tcr],[16,to],[20,to+4096],[68,32768],[72,1180000],[76,0],[80,1800000]])put(config+offset,value);
 put(base,338);put(base+4,base+9);put(base+8,NIL);put(base+12,148);
}
for(const base of [8388608,2146500608]){
 for(const rooted of [false,true]){
  setup(base);
  if(rooted){put(root+4,2);put(root+12,base+9);}
  const before=bytes(base,16).slice();
  assert.equal(collector.collect(config),0);
  assert.deepEqual(bytes(base,16),before,'source preserved');
  const moved=get(root+8)-6;assert.equal(get(moved),338);
  assert.equal(get(moved+4),NIL,'pool cleared');
  assert.equal(get(config+84),rooted?2:1,'cached contents not traced');
  if(rooted){const cell=get(root+12);assert.equal(get(cell-1),NIL);assert.equal(get(cell+3),148);}
  rows.push({base,rooted,status:'POOL_CLEARED'});
 }
 for(const n of [0,2]){
  setup(base);put(base,n*256+82);
  const before=[bytes(base,16).slice(),bytes(root,32).slice(),bytes(tcr,256).slice()];
  assert.equal(collector.collect(config),2,'pool count');
  assert.deepEqual([bytes(base,16),bytes(root,32),bytes(tcr,256)],before,'no publication');
  rows.push({base,n,status:'COUNT_REFUSED_WITHOUT_PUBLICATION'});
 }
}
fs.writeFileSync(output,JSON.stringify({status:'PASS',rows},null,2)+'\n');
console.log('PASS',rows.length,'pool checks');
