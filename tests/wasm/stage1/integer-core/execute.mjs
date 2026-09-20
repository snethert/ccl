import fs from 'node:fs';
import assert from 'node:assert/strict';
const [modulePath,casesPath,output]=process.argv.slice(2);
process.on('uncaughtException',error=>{fs.writeFileSync(output,JSON.stringify({status:'FAIL',message:error.message},null,2)+'\n');console.error(error);process.exitCode=1;});
const corpus=JSON.parse(fs.readFileSync(casesPath));
const code=await WebAssembly.compile(fs.readFileSync(modulePath));
assert.deepEqual(WebAssembly.Module.imports(code),[{module:'env',name:'memory',kind:'memory'}]);
const memory=new WebAssembly.Memory({initial:32769,maximum:32769});
const {exports:e}=await WebAssembly.instantiate(code,{env:{memory}});
const d=new DataView(memory.buffer);const bytes=new Uint8Array(memory.buffer);
const ops=['add','sub','mul','ash','length','truncate'];
const stats=[];const controls=[];
for(const base of [1048576,2147483648]){
 const input=base,inputEnd=base+16384,out=base+16384,limit=base+32768,scratch=base+32768,scratchEnd=base+49184,result=base+49200;
 let cursor;
 const put=(p,x)=>d.setUint32(p,x,true),get=p=>d.getUint32(p,true);
 function encode(s){
  const n=BigInt(s);if(n>=-536870912n&&n<=536870911n)return Number(BigInt.asUintN(32,n<<2n));
  let width=1;while(n<-(1n<<BigInt(width*32-1))||n>=(1n<<BigInt(width*32-1)))width++;
  const size=(4+4*width+7)&~7,p=cursor;cursor+=size;assert(cursor<=inputEnd);
  put(p,width*256+7);let v=BigInt.asUintN(width*32,n);
  for(let i=0;i<width;i++){put(p+4+4*i,Number(v&0xffffffffn));v>>=32n;}
  return p+6;
 }
 function decode(v){
  if(v%4===0)return String(d32(v)/4);
  assert.equal(v%8,6,'result tag');const p=v-6,h=get(p);assert.equal(h%256,7,'bignum subtag');const n=h>>>8;
  let x=0n;for(let i=n-1;i>=0;i--)x=(x<<32n)|BigInt(get(p+4+4*i));
  x=BigInt.asIntN(n*32,x);assert(x < -536870912n||x>536870911n,'canonical fixnum');
  if(n>1){const hi=get(p+4*n),prev=get(p+4*(n-1));assert(!((hi===0&&prev<0x80000000)||(hi===0xffffffff&&prev>=0x80000000)),'minimal sign');}
  return String(x);
 }
 function d32(x){return x>=2147483648?x-4294967296:x;}
 function prepare(a,b){bytes.fill(0xcc,input,result+16);cursor=input;const av=encode(a),bv=encode(b);return [av,bv];}
 function invoke(op,av,bv,changes={}){
  const spec={op,av,bv,input,inputEnd,out,limit,scratch,scratchEnd,result,...changes};
  return e.integer_calculate(...Object.values(spec));
 }
 assert.equal(e.integer_workspace_bytes(),16416);
 for(const c of corpus){
  const [a,b]=prepare(c.a,c.b);const before=bytes.slice(input,inputEnd),published=bytes.slice(out,limit),saved=bytes.slice(result,result+16);
  const status=invoke(ops.indexOf(c.op),a,b);
  try{
   assert.deepEqual(bytes.slice(input,inputEnd),before,'inputs unchanged');
   if(c.expected==='division-by-zero'){
    assert.equal(status,4,'division-by-zero');assert.deepEqual(bytes.slice(out,limit),published);assert.deepEqual(bytes.slice(result,result+16),saved);
   }else{
    assert.equal(status,0,'operation status');const count=get(result+8);assert.equal(count,c.expected.length,'value count');
    const got=[decode(get(result))];if(count===2)got.push(decode(get(result+4)));assert.deepEqual(got,c.expected,'exact values');
    const next=get(result+12);assert(next>=out&&next<=limit&&next%8===0,'allocation publication');
    assert.deepEqual(bytes.slice(next,limit),published.slice(next-out),'unused allocation unchanged');
    // Independently account minimal canonical signed-object widths.
    let expectedBytes=0;for(const v of c.expected){const n=BigInt(v);if(n>=-536870912n&&n<=536870911n)continue;let words=1;while(n<-(1n<<BigInt(32*words-1))||n>=(1n<<BigInt(32*words-1)))words++;expectedBytes+=(4+4*words+7)&~7;}
    assert.equal(next-out,expectedBytes,'exact allocation');
   }
  }catch(error){throw new Error(c.name+' @ '+base+': '+error.message,{cause:error});}
 }
 function refuse(name,op,a,b,want,changes={},corrupt=()=>{}){
  const [av,bv]=prepare(a,b);corrupt(av,bv);const inBefore=bytes.slice(input,inputEnd),outBefore=bytes.slice(out,limit),resBefore=bytes.slice(result,result+16);
  assert.equal(invoke(op,av,bv,changes),want,name);assert.deepEqual(bytes.slice(input,inputEnd),inBefore,name+' input');assert.deepEqual(bytes.slice(out,limit),outBefore,name+' allocation');assert.deepEqual(bytes.slice(result,result+16),resBefore,name+' publication');controls.push({name,base,status:want});
 }
 refuse('workspace-short',0,'1','2',3,{scratchEnd:scratch+16408});
 refuse('invalid-op',6,'1','2',5);
 refuse('scratch-overlap',0,'1','2',1,{scratch:out,scratchEnd:out+16416});
 refuse('output-overlap',0,'1','2',1,{out:input});
 refuse('result-overlap',0,'1','2',1,{result:out});
 refuse('C-stack-overlap',0,'1','2',1,{input:65536,inputEnd:65544});
 refuse('unaligned-owner',0,'1','2',1,{out:out+4});
 refuse('unbacked-owner',0,'1','2',1,{limit:2147614720});
 refuse('negative-owner-wrap',0,'1','2',1,{out:0xfffffff8,limit:0});
 refuse('no-output-space',0,'536870911','1',3,{limit:out});
 refuse('atomic-two-results',5,String((1n<<96n)+123n),String((1n<<40n)+9n),3,{limit:out+8});
 refuse('enormous-left-count',3,'1',String(1n<<100n),3);
 refuse('magnitude-limit',3,'1','32768',3);
 refuse('carry-over-limit',0,String((1n<<32768n)-1n),'1',3);
 refuse('multiply-over-limit',2,String((1n<<32768n)-1n),'2',3);
 refuse('noninteger-tag',0,'1','2',2,{av:input+1});
 refuse('unbacked-pointer',0,'1','2',2,{av:inputEnd+6});
 refuse('misaligned-pointer',0,'1','2',2,{av:input+14});
 refuse('wrong-header',0,'536870912','2',2,{},a=>put(a-6,263+8));
 refuse('zero-header-length',0,'536870912','2',2,{},a=>put(a-6,7));
 refuse('oversized-header',0,'536870912','2',2,{},a=>put(a-6,0xffffff07));
 refuse('redundant-positive-sign',0,'536870912','2',2,{},a=>{put(a-6,519);put(a+2,0);});
 refuse('redundant-negative-sign',0,'-536870913','2',2,{},a=>{put(a-6,519);put(a+2,0xffffffff);});
 refuse('boxed-fixnum',0,'536870912','2',2,{},a=>put(a-2,7));
 let src=input,dest=out,value=null,chainSteps=0;
 for(const c of corpus.filter(c=>c.chain)){
  if(value===null){[value]=prepare(c.a,'0');}
  assert.equal(decode(value),c.a,'chain incoming');
  const other=Number(BigInt.asUintN(32,BigInt(c.b)<<2n));
  const before=bytes.slice(src,src+16384);
  assert.equal(e.integer_calculate(ops.indexOf(c.op),value,other,src,src+16384,dest,dest+16384,scratch,scratchEnd,result),0,c.name+' chain status');
  assert.deepEqual(bytes.slice(src,src+16384),before,'chain source preserved');
  value=get(result);assert.equal(decode(value),c.expected[0],c.name+' chain result');
  if(c.expected.length===2)assert.equal(decode(get(result+4)),c.expected[1],'chain remainder');
  [src,dest]=[dest,src];chainSteps++;
 }
 stats.push({base,cases:corpus.length,chainSteps});
}
fs.writeFileSync(output,JSON.stringify({status:'PASS',placements:stats,refusals:controls},null,2)+'\n');
