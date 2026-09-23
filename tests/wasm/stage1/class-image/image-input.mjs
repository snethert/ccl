// Fixture boundary: capture once; fresh consumer Workers cannot call materialize.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {writeHeapImage,admitHeapImage} from './runtime/heap-image.mjs';

export function imageArguments({memory,base,limit,tcr,root,get,put,gen,conditionSlots,
                               expected,materialize,dir,mode,imageDir,codeDigest,bootstrap=false}) {
 const regions=[
  {name:'canonical',kind:'objects',start:77824,size:72},
  {name:'symbols',kind:'objects',start:7000000,size:gen.ownerEnd-7000000},
  {name:'names',kind:'objects',start:1200000,size:gen.symbolEnd-1200000},
  {name:'constants',kind:'objects',start:2097152,size:gen.imageEnd-2097152},
  {name:'arguments',kind:'roots',start:root,size:512}
 ];
 const slots=[...new Set([...gen.extraRoots,...conditionSlots,
                         ...expected.args.map((_,i)=>root+8+4*i)])].sort((a,b)=>a-b);
 const key=bootstrap?'class-ready':expected.caseId.replace(':','-'),stem=imageDir+'/'+key;
 let packet;
 if(mode==='write'){
  const args=materialize();put(root,0);put(root+4,args.length);
  args.forEach((value,i)=>put(root+8+4*i,value));
  packet=writeHeapImage({memory,start:base,end:get(tcr+48),regions,rootSlots:slots,codeDigest});
  fs.writeFileSync(stem+'.bin',packet.payload);
  fs.writeFileSync(stem+'.json',JSON.stringify({record:packet.record,digest:packet.digest,objects:packet.objects}));
 }else{
  assert.equal(mode,'read');packet=JSON.parse(fs.readFileSync(stem+'.json'));
  packet.payload=fs.readFileSync(stem+'.bin');
  // The old allocation area contains poison, never a usable graph projection.
  new Uint8Array(memory.buffer,base,limit-base).fill(0xda);
 }
 const image=admitHeapImage({memory,...packet,regions,start:base,limit,rootSlots:slots,codeDigest});
 assert.equal(image.state,'ADMITTED');
 image.install();put(tcr+48,image.end);put(root,0);put(root+4,expected.args.length);
 // Roots are registered before any generated initializer may allocate.
 const registered=new Set(gen.extraRoots);
 for(const slot of slots)if(!registered.has(slot)){gen.extraRoots.push(slot);registered.add(slot);}
 const args=expected.args.map((_,i)=>get(root+8+4*i));
 assert.equal(get(root+4),args.length);
 return {args,image,record:packet.digest,bytes:packet.record.bytes,objects:image.objects,
  saveReady(){
   const ready=writeHeapImage({memory,start:get(tcr+56),end:get(tcr+48),regions,rootSlots:slots,codeDigest});
   fs.writeFileSync(imageDir+'/class-ready.bin',ready.payload);
   fs.writeFileSync(imageDir+'/class-ready.json',JSON.stringify({record:ready.record,digest:ready.digest,objects:ready.objects}));
  }};
}
