// Independent observations of the native scalar-complex layouts. Payload
// words deliberately resemble pointers: neither GC nor image loading may
// relocate them or retain the dead cons to which they appear to point.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {pathToFileURL} from 'node:url';
const [dir,output]=process.argv.slice(2);
const {writeHeapImage,admitHeapImage,recordDigest}=await import(pathToFileURL(dir+'/runtime/heap-image.mjs'));
const {sha256}=await import(pathToFileURL(dir+'/runtime/sha256.mjs'));
const memory=new WebAssembly.Memory({initial:32769,maximum:32769,shared:true});
const view=new DataView(memory.buffer),get=p=>view.getUint32(p,true),put=(p,v)=>view.setUint32(p,v,true);
const bytes=(p,n)=>new Uint8Array(memory.buffer,p,n);
const collector=(await WebAssembly.instantiate(fs.readFileSync(dir+'/collector.wasm'),{env:{memory}})).instance.exports;
const tcr=1024,root=65536,config=1200000,to=3145728,NIL=77825,codeDigest='a'.repeat(64);
const regions=[{name:'roots',kind:'roots',start:root,size:32}];
const rows=[];
function setup(base,size){
 bytes(tcr,256).fill(0);bytes(config,96).fill(0);bytes(root,32).fill(0);bytes(base,128).fill(0);bytes(to,128).fill(0xa5);
 for(const [offset,value]of [[48,base+size],[52,base+4096],[56,base],[68,root+8],[72,98304],[128,root],[80,700000],[76,700000],[120,100000],[124,100064],[104,610000]])put(tcr+offset,value);
 put(root+4,1);put(root+8,base+6);
 for(const [offset,value]of [[0,tcr],[16,to],[20,to+4096],[68,32768],[72,1180000],[76,0],[80,1800000]])put(config+offset,value);
}
for(const base of [8388608,2146500608])for(const [tag,count,size]of [[71,3,16],[79,5,24]]){
 setup(base,size+8);put(base,count*256+tag);put(base+4,0);
 for(let offset=8;offset<size;offset+=4)put(base+offset,base+size+1);
 put(base+size,NIL);put(base+size+4,28);
 const original=bytes(base,size).slice();
 assert.equal(collector.collect(config),0);assert.equal(get(config+84),1,'raw fields retain no cons');
 assert.equal(get(tcr+48)-get(tcr+56),size);assert.deepEqual(bytes(get(root+8)-6,size),original);
 const image=writeHeapImage({memory,start:to,end:to+size,regions,rootSlots:[root+8],codeDigest});
 assert.equal(image.objects,1);assert.equal(image.record.relocations.length,0,'raw fields need no relocation');
 const destination=base+256;
 const options={...image,memory,start:destination,limit:destination+128,regions,rootSlots:[root+8],codeDigest};
 admitHeapImage(options).install();assert.equal(get(root+8),destination+6);assert.deepEqual(bytes(destination,size),original);
 rows.push({base,tag,size,status:'MOVED_AND_RELOADED_RAW'});
 for(const wrong of [count-1,count+1]){
  setup(base,size);put(base,wrong*256+tag);
  const old=bytes(base,size).slice(),roots=bytes(root,32).slice(),state=bytes(tcr,256).slice();
  assert.equal(collector.collect(config),2,'invalid count is a checked refusal');
  assert.deepEqual(bytes(base,size),old);assert.deepEqual(bytes(root,32),roots);assert.deepEqual(bytes(tcr,256),state);
  const record=structuredClone(image.record),payload=image.payload.slice();
  new DataView(payload.buffer).setUint32(0,wrong*256+tag,true);record.payloadDigest=sha256(payload);
  const before=bytes(destination,128).slice();
  assert.throws(()=>admitHeapImage({...options,record,payload,digest:recordDigest(record)}),/object kind/);
  assert.deepEqual(bytes(destination,128),before);
  rows.push({base,tag,wrong,status:'COUNT_REFUSED_WITHOUT_PUBLICATION'});
 }
 setup(base,size-8);put(base,count*256+tag);
 const before=bytes(tcr,256).slice();assert.equal(collector.collect(config),2,'truncated object');assert.deepEqual(bytes(tcr,256),before);
 rows.push({base,tag,status:'EXTENT_REFUSED'});
}
fs.writeFileSync(output,JSON.stringify({status:'PASS',rows},null,2)+'\n');
console.log('PASS',rows.length,'scalar complex layout checks');
