// Independent raw checks. Host Math is an oracle here, never a runtime import.
import fs from 'node:fs';
import assert from 'node:assert/strict';
const [dir,output]=process.argv.slice(2);
const mod=new WebAssembly.Module(fs.readFileSync(dir+'/float.wasm'));
const detector=new WebAssembly.Module(fs.readFileSync(dir+'/detector.wasm'));
const names=['pow','sin','cos','acos','asin','cosh','log','tan','atan','atan2','exp','sinh','tanh','asinh','acosh','atanh'];
const imports=WebAssembly.Module.imports(mod);
assert.deepEqual(imports.filter(x=>x.kind==='function').map(x=>x.module+'/'+x.name).sort(),['detector/add','detector/div','detector/mul','detector/sub']);
let seed=0x12345678;const random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/2**32;};
const runs=[];
for(const base of [131072,1048576,2147483648]){
 const memory=new WebAssembly.Memory({initial:base===2147483648?32769:32,maximum:32769});
 const view=new DataView(memory.buffer),bytes=new Uint8Array(memory.buffer),put=(p,x)=>view.setUint32(p,x,true),get=p=>view.getUint32(p,true);
 const checks=new WebAssembly.Instance(detector,{env:{memory}}).exports;
 const api=new WebAssembly.Instance(mod,{env:{memory},detector:checks}).exports;
 assert(api.__stack_pointer.value<=131072,'private input overlaps libm stack');
 const end=base+64,out=base+80,limit=out+16,result=out+32;
 function encode(x,w,p){put(p,w===32?271:791);put(p+4,0);if(w===32)view.setFloat32(p+4,x,true);else view.setFloat64(p+8,x,true);return p+6;}
 function bits(x,w){const b=new ArrayBuffer(8),v=new DataView(b);if(w===32){v.setFloat32(0,x,true);return BigInt(v.getUint32(0,true));}v.setFloat64(0,x,true);return v.getBigUint64(0,true);}
 function ulps(a,b,w){if(a===0||b===0){assert(Object.is(a,b),'signed zero');return 0;}const sign=1n<<BigInt(w-1),ordered=n=>n&sign?sign-(n&(sign-1n)):sign+n;const aa=ordered(bits(a,w)),bb=ordered(bits(b,w));return Number(aa>bb?aa-bb:bb-aa);}
 let comparisons=0,identical=0,maxUlps=0;const directed=[];
 function reset(w,x,y){bytes.fill(0xa5,base,result+64);return [encode(x,w,base),encode(y,w,base+16)];}
 function call(op,a,b,mask=7,safe=1,reserve=16){return api.float_calculate_lisp(op,a,b,base,end,out,out+reserve,result,mask,safe);}
 for(let i=0;i<names.length;i++)for(const w of [64,32]){
  const op=12+2*i+(w===32),name=names[i];
  for(let n=0;n<160;n++){
   let x=(random()-.5)*8,y=(random()-.5)*6;
   if(name==='pow'){x=random()*8+.125;y=(random()-.5)*8;}
   if(name==='acosh')x=1+random()*100;
   if(name==='atanh')x=(random()-.5)*1.999;
   if(name==='log')x=2**((random()-.5)*100);
   if(name==='asin'||name==='acos')x=(random()-.5)*2;
   if(['sin','cos','tan'].includes(name)&&n%3===0)x=(random()-.5)*1e12;
   if(['exp','sinh','cosh'].includes(name))x=(random()-.5)*(w===32?140:1200);
   if(w===32){x=Math.fround(x);y=Math.fround(y);}
   const args=reset(w,x,y),before=bytes.slice(base,end);
   assert.equal(call(op,...args),0);assert.equal(get(result+8),0);assert.equal(get(result+4),0);
   const actual=w===32?view.getFloat32(out+4,true):view.getFloat64(out+8,true);
   const expected0=Math[name](x,y),expected=w===32?Math.fround(expected0):expected0;
   const delta=ulps(actual,expected,w);assert(delta<=2,`${name}/${w} ${x},${y}: ${actual} vs ${expected} (${delta} ULP)`);
   comparisons++;identical+=delta===0;maxUlps=Math.max(maxUlps,delta);
   assert.equal(get(result),out+6);assert.equal(get(result+12),3);assert.equal(get(result+16),out+(w===32?8:16));assert.equal(get(result+20),w);assert.equal(get(result+24),0);assert.equal(get(result+28),0);
   assert.deepEqual(bytes.slice(base,end),before);assert(bytes.slice(out+(w===32?8:16),limit).every(x=>x===0xa5));
  }
  for(const [label,x,y,mask,safe,reserve,status] of [
   ['unsupported-underflow',.5,.25,15,1,16,5],['unsupported-inexact',.5,.25,23,1,16,5],
   ['nonfinite',Infinity,.25,7,1,16,2],['nan',NaN,.25,7,1,16,2],
   ['short-result',name==='acosh'?2:.5,.25,7,1,w===32?0:8,3]]){
   const args=reset(w,x,y),before=bytes.slice(base,result+64);assert.equal(call(op,...args,mask,safe,reserve),status,label);assert.deepEqual(bytes.slice(base,result+64),before,label+' publication');directed.push({name,w,label,status});
  }
  const args=reset(w,.5,.25);assert.equal(call(op,...args,31,0,w===32?8:16),0,'unchecked mask and exact fit');assert.equal(get(result+4),0);directed.push({name,w,label:'unchecked-exact-fit'});
  const wrong=reset(w===32?64:32,.5,.25),before=bytes.slice(base,result+64);assert.equal(call(op,...wrong),2);assert.deepEqual(bytes.slice(base,result+64),before);directed.push({name,w,label:'wrong-width'});
 }
 // Literal mathematical identities are exact, not subject to the ULP allowance.
 for(const [name,x,y,want] of [
  ['pow',2,3,8],['pow',2,-2,.25],['pow',-2,3,-8],['pow',2,0,1],
  ['sin',0,0,0],['sin',-0,0,-0],['cos',0,0,1],['acos',1,0,0],
  ['asin',-0,0,-0],['cosh',0,0,1],['log',1,0,0],['tan',-0,0,-0],
  ['atan',-0,0,-0],['atan2',-0,1,-0],['exp',0,0,1],
  ['sinh',-0,0,-0],['tanh',-0,0,-0],['asinh',0,0,0],['asinh',-0,0,-0],['acosh',1,0,0],['atanh',0,0,0],['atanh',-0,0,-0]])for(const w of [64,32]){
  const op=12+2*names.indexOf(name)+(w===32),args=reset(w,x,y);
  assert.equal(call(op,...args),0);assert.equal(get(result+4),0);assert.equal(get(result+8),0);
  const actual=w===32?view.getFloat32(out+4,true):view.getFloat64(out+8,true);
  assert(Object.is(actual,want),`exact ${name}/${w}`);
  directed.push({name,w,label:'exact-identity',inputBits:[String(bits(x,w)),String(bits(y,w))],resultBits:String(bits(actual,w))});
 }
 for(const [op,x,y,flag] of [[18,2,0,1],[24,0,0,2],[12,0,-1,2],[32,1000,0,4],[33,1000,0,4],[40,0,0,1],[41,0,0,1],[42,1,0,2],[43,-1,0,2],[42,2,0,1],[43,-2,0,1]]){
  const w=op%2?32:64,args=reset(w,x,y);assert.equal(call(op,...args),0);assert.equal(get(result+4),flag);assert.equal(get(result+8),flag);assert.equal(get(result),77825);assert.equal(get(result+16),out);assert(bytes.slice(out,limit).every(x=>x===0xa5));directed.push({op,label:'enabled-condition',flag});
 }
 runs.push({base,comparisons,identical,maxUlps,directed,stackTop:api.__stack_pointer.value});
}
fs.writeFileSync(output,JSON.stringify({status:'PASS',runs,scope:'Finite sampled numerical comparison against independent host Math, two ULP maximum, exact signed zero. No full-domain error-bound or inexact/underflow-flag claim.'},null,2)+'\n');
console.log('PASS: raw libm comparisons',runs.reduce((n,r)=>n+r.comparisons,0));
