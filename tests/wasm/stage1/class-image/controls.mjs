import assert from 'node:assert/strict';
import fs from 'node:fs';
import {pathToFileURL} from 'node:url';
const [dir,output]=process.argv.slice(2);
const {writeHeapImage,admitHeapImage,recordDigest}=await import(pathToFileURL(dir+'/runtime/heap-image.mjs'));
const {sha256}=await import(pathToFileURL(dir+'/runtime/sha256.mjs'));
const memory=new WebAssembly.Memory({initial:4}),view=new DataView(memory.buffer);
const put=(p,w)=>view.setUint32(p,w,true),get=p=>view.getUint32(p,true);
const regions=[{name:'symbols',kind:'objects',start:4096,size:32},
               {name:'roots',kind:'roots',start:8192,size:16}];
const codeDigest='a'.repeat(64),start=16384,end=start+40,destination=32768;
// A cycle, shared cons, external symbol, and raw bits resembling a pointer.
[1850,77825,77825,77825,77825,0,77825,0].forEach((w,i)=>put(4096+4*i,w));
put(start,start+9);put(start+4,4102);
put(start+8,start+1);put(start+12,28);
put(start+16,762);put(start+20,start+1);put(start+24,start+1);put(start+28,start+38);
put(start+32,263);put(start+36,start+1); // bignum raw limb is not relocated
put(8192,start+22);
const input={memory,start,end,regions,rootSlots:[8192],codeDigest};
const packet=writeHeapImage(input),parameters={...packet,memory,regions,start:destination,limit:destination+4096,rootSlots:[8192],codeDigest};
const checks=[];
function refuse(name,change,reason,{resign=false}={}){
 const p={...parameters,record:structuredClone(packet.record),payload:packet.payload.slice(),regions:structuredClone(regions),rootSlots:[8192]};
 change(p);
 if(resign){p.record.payloadDigest=sha256(p.payload);p.digest=recordDigest(p.record);}
 const before=sha256(new Uint8Array(memory.buffer));
 assert.throws(()=>admitHeapImage(p),reason,name);
 assert.equal(sha256(new Uint8Array(memory.buffer)),before,name+' refuses before writes');checks.push(name);
}
refuse('record digest',p=>p.record.version=2,/record digest/);
refuse('payload digest',p=>p.payload[0]^=1,/payload digest/);
refuse('code identity',p=>p.codeDigest='b'.repeat(64),/code identity/);
refuse('capacity',p=>p.limit=destination+8,/capacity/);
refuse('destination alignment',p=>p.start++,/heap extent/);
refuse('destination overlap',p=>p.start=4096,/heap overlap/);
refuse('region overlap',p=>p.regions.push({...p.regions[0],name:'duplicate'}),/region overlap/);
refuse('region duplicate',p=>p.regions[1].name='symbols',/region name/);
refuse('binding authority',p=>p.rootSlots=[],/binding authority/);
refuse('binding completeness',p=>p.rootSlots.push(8196),/binding completeness/);
refuse('binding extent',p=>p.record.roots[0].slot.offset=15,/binding extent/,{resign:true});
refuse('duplicate binding',p=>p.record.roots.push(p.record.roots[0]),/binding authority/,{resign:true});
refuse('heap interior',p=>p.record.relocations[0].value={heap:4,tag:1},/heap boundary/,{resign:true});
refuse('wrong pointer tag',p=>p.record.relocations[0].value={heap:0,tag:6},/heap boundary/,{resign:true});
refuse('external interior',p=>p.record.relocations[0].value={region:'symbols',offset:8,tag:6},/import boundary/,{resign:true});
refuse('undeclared external',p=>p.record.relocations[0].value={region:'scratch',offset:0,tag:6},/import boundary/,{resign:true});
refuse('duplicate relocation',p=>p.record.relocations.push(p.record.relocations[0]),/relocation slot/,{resign:true});
refuse('missing relocation',p=>p.record.relocations.shift(),/unrelocated pointer/,{resign:true});
refuse('raw relocation',p=>p.record.relocations[0].slot=36,/relocation slot/,{resign:true});
refuse('header relocation',p=>p.record.relocations[0].slot=16,/relocation slot/,{resign:true});
refuse('naked pointer',p=>new DataView(p.payload.buffer).setUint32(12,16385,true),/unrelocated pointer/,{resign:true});
refuse('unknown kind',p=>new DataView(p.payload.buffer).setUint32(32,2,true),/object kind/,{resign:true});
refuse('malformed immediate',p=>p.record.roots[0].value={immediate:1},/immediate/,{resign:true});
put(4100,4);refuse('changed import',()=>{},/import identity/);put(4100,77825);
const admitted=admitHeapImage(parameters),changedPayload=packet.payload.slice();
packet.payload.fill(0); // caller mutation cannot change an admitted image
const installed=admitted.install();
assert.equal(get(8192),destination+22);assert.equal(get(destination),destination+9);
assert.equal(get(destination+8),destination+1);assert.equal(get(destination+20),get(destination+24));
assert.equal(get(destination+4),4102);assert.equal(get(destination+36),start+1);
assert.equal(installed.end,destination+40);assert.equal(admitted.state,'INSTALLED');
assert.throws(()=>admitted.install(),/install state/);
admitted.initialize(()=>true);assert.equal(admitted.state,'READY');
assert.throws(()=>admitted.initialize(()=>true),/initialize state/);
checks.push('cycles sharing raw bits','private snapshot','one shot READY');
packet.payload.set(changedPayload);
for(const mode of ['throw','false','async']){
 const candidate=admitHeapImage(parameters);candidate.install();
 assert.throws(()=>candidate.initialize(()=>{if(mode==='throw')throw Error('initializer');return mode==='async'?Promise.resolve(true):false;}));
 assert.equal(candidate.state,'FAILED');assert.throws(()=>candidate.initialize(()=>true),/initialize state/);
 checks.push('no READY after '+mode);
}
const changed=admitHeapImage(parameters);put(4100,4);
const before=sha256(new Uint8Array(memory.buffer));
assert.throws(()=>changed.install(),/imports changed/);
assert.equal(sha256(new Uint8Array(memory.buffer)),before);checks.push('TOCTOU import refusal');
fs.writeFileSync(output,JSON.stringify({status:'PASS',checks},null,2)+'\n');
console.log(JSON.stringify({status:'PASS',checks:checks.length}));
