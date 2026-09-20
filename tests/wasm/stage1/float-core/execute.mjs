import fs from 'node:fs';import assert from 'node:assert/strict';
const [binary,detectorPath,casesPath,output]=process.argv.slice(2),rows=JSON.parse(fs.readFileSync(casesPath));
const mod=new WebAssembly.Module(fs.readFileSync(binary)),detectorMod=new WebAssembly.Module(fs.readFileSync(detectorPath));
const OPS=['add','sub','mul','div','lt','le','eq','ne','ge','gt','single','double'];
const expectedImports=[{module:'env',name:'memory',kind:'memory'},...['add','sub','mul','div'].map(name=>({module:'detector',name,kind:'function'}))];
assert.deepEqual(WebAssembly.Module.imports(mod).sort((a,b)=>(a.module+a.name).localeCompare(b.module+b.name)),expectedImports.sort((a,b)=>(a.module+a.name).localeCompare(b.module+b.name)));
const reports=[];let current="setup";
try{
for(const base of [131072,1048576,2147483648]){
 const memory=new WebAssembly.Memory({initial:base<2147483648?32:32769,maximum:32769}),view=new DataView(memory.buffer),set=(p,v)=>view.setUint32(p,v,true),get=p=>view.getUint32(p,true);
 const detector=new WebAssembly.Instance(detectorMod,{env:{memory}}).exports;let witness=0;
 const api=Object.fromEntries(['add','sub','mul','div'].map(n=>[n,(a,b)=>{witness++;return detector[n](a,b);} ]));
 const svc=new WebAssembly.Instance(mod,{env:{memory},detector:api}).exports;
 const input=base,end=base+16384,out=base+16400,limit=out+32,result=base+16448;
 let cursor=input;
 const encode=x=>{
  if(x.kind==='integer'){
   let n=BigInt(x.value);if(n>=-536870912n&&n<=536870911n)return Number(BigInt.asUintN(32,n<<2n));
   let w=1;while(n<-(1n<<BigInt(32*w-1))||n>=(1n<<BigInt(32*w-1)))w++;
   const p=cursor;cursor+=8*Math.ceil((4+4*w)/8);assert(cursor<=end);set(p,256*w+7);n=BigInt.asUintN(32*w,n);for(let i=0;i<w;i++){set(p+4+4*i,Number(n&0xffffffffn));n>>=32n;}return p+6;
  }
  const w=Number(x.kind),p=cursor;cursor+=w===32?8:16;set(p,w===32?271:791);if(w===64)set(p+4,0);
  const raw=x.bits==='nan'?(w===32?0x7fc00000n:0x7ff8000000000000n):BigInt('0x'+x.bits);
  if(w===32)set(p+4,Number(raw));else{set(p+8,Number(raw&0xffffffffn));set(p+12,Number(raw>>32n));}return p+6;
 };
 const decode=(v,width,condition)=>{
  if(condition||width===0)return v===77825?'NIL':v===77838?'T':'BAD-BOOLEAN';
  assert.equal(v,out+6);assert.equal(get(out),width===32?271:791);
  let raw=width===32?BigInt(get(out+4)):BigInt(get(out+8))|(BigInt(get(out+12))<<32n);
  const exp=width===32?(raw>>23n)&255n:(raw>>52n)&2047n,mant=width===32?raw&0x7fffffn:raw&0xfffffffffffffn;
  if(exp===(width===32?255n:2047n)&&mant!==0n)return 'nan';return raw.toString(16).padStart(width/4,'0');
 };
 for(const c of rows){
  current=c.name;
  cursor=input;new Uint8Array(memory.buffer,input,16512).fill(0xa5);const a=encode(c.a),b=encode(c.b),before=Buffer.from(new Uint8Array(memory.buffer,input,end-input)),calls=witness;
  const status=svc.float_calculate(OPS.indexOf(c.op),a,b,input,end,out,limit,result,c.mask,c.safe);
  assert.equal(status,0,c.name+' status');const condition=get(result+8),width=get(result+20);
  const actual={value:decode(get(result),width,condition),flags:get(result+4),condition,stage:get(result+12),width,a_flags:get(result+24),b_flags:get(result+28)};
  assert.deepEqual(actual,c.expected,c.name+' @ '+base);assert.deepEqual(Buffer.from(new Uint8Array(memory.buffer,input,end-input)),before,'input preservation');
  const size=!condition&&width?width===32?8:16:0;assert.equal(get(result+16),out+size,'minimal allocation');
  assert(new Uint8Array(memory.buffer,out+size,limit-out-size).every(x=>x===0xa5),'output tail');
  assert(new Uint8Array(memory.buffer,end,16).every(x=>x===0xa5),'input gap');assert(new Uint8Array(memory.buffer,limit,16).every(x=>x===0xa5),'output gap');
  assert(new Uint8Array(memory.buffer,result+32,32).every(x=>x===0xa5),'result guard');
  if(!c.safe||!(c.mask&24))assert.equal(witness,calls,'unneeded exactness witness');
 }
 const refusals=[];
 const check=(name,edit,code)=>{
  current=name;cursor=input;new Uint8Array(memory.buffer,input,16512).fill(0xa5);
  const args=[0,encode({kind:'64',bits:'3ff0000000000000'}),4,input,end,out,limit,result,7,1];edit(args);
  const before=Buffer.from(new Uint8Array(memory.buffer,input,16512));
  assert.equal(svc.float_calculate(...args),code,name);
  assert.deepEqual(Buffer.from(new Uint8Array(memory.buffer,input,16512)),before,name+' preservation');refusals.push({name,code});
 };
 check('no-output-space',a=>a[6]=out,3);
 check('short-double-reservation',a=>a[6]=out+8,3);
 check('input-output-alias',a=>a[5]=input,1);
 check('result-input-alias',a=>a[7]=input,1);
 check('result-output-alias',a=>a[7]=out,1);
 check('unaligned-output',a=>a[5]++,1);
 check('unaligned-result',a=>a[7]++,1);
 check('unbacked-result',a=>a[7]=memory.buffer.byteLength-24,1);
 check('unbacked-input',a=>a[4]=memory.buffer.byteLength+8,1);
 check('reserved-stack-input',a=>a[3]=0,1);
 check('bad-mask',a=>a[8]=32,1);
 check('bad-safety',a=>a[9]=2,1);
 check('bad-operation',a=>a[0]=12,5);
 check('integer-only-arithmetic',a=>{a[1]=4;a[2]=8;},5);
 check('wrong-tag',a=>a[1]=77825,2);
 check('wrong-header',a=>set(a[1]-6,1047),2);
 check('short-object',a=>a[4]=input+8,2);
 check('before-input',a=>a[1]=input-2,2);
 check('fixnum-as-bignum',a=>{set(input,263);set(input+4,7);},2);
 check('redundant-sign',a=>{set(input,519);set(input+4,7);set(input+8,0);},2);
 check('integer-capacity',a=>{set(input,256*1026+7);set(input+4*1026,1);a[0]=11;},3);
 // Exact-fit publication and a selected condition with no result reservation.
 for(const width of [32,64]){
  current='exact-fit-'+width;cursor=input;new Uint8Array(memory.buffer,out,64).fill(0xa5);
  const a=encode({kind:String(width),bits:width===32?'3f800000':'3ff0000000000000'}),size=width===32?8:16;
  assert.equal(svc.float_calculate(0,a,4,input,end,out,out+size,result,7,1),0,current);
  assert.equal(get(result+16),out+size,current);assert.equal(get(out+size),0xa5a5a5a5,current+' guard');
 }
 current='condition-without-allocation';cursor=input;const zero=encode({kind:'64',bits:'0000000000000000'});
 new Uint8Array(memory.buffer,out,32).fill(0xa5);assert.equal(svc.float_calculate(3,zero,zero,input,end,out,out,result,31,1),0,current);assert.equal(get(result+8),1);assert.equal(get(result+16),out);assert(new Uint8Array(memory.buffer,out,32).every(x=>x===0xa5));
 current='memory-end-publication';assert.equal(svc.float_calculate(0,zero,4,input,end,out,limit,memory.buffer.byteLength-32,7,1),0,current);assert.equal(get(memory.buffer.byteLength-16),out+16,current);
 reports.push({base,cases:rows.length,witness_calls:witness,refusals,exact_fits:2,condition_without_allocation:true});
}
fs.writeFileSync(output,JSON.stringify({status:'PASS',reports},null,2)+'\n');
}catch(e){fs.writeFileSync(output,JSON.stringify({status:'FAIL',message:current+': '+e.message},null,2)+'\n');throw e;}
