import fs from 'node:fs';import assert from 'node:assert/strict';import {createHash} from 'node:crypto';
import {inspect} from './binary.mjs';
import {CollectorOwner} from './collector-owner.mjs';import {integerService} from './service.mjs';
const [dir,collectorPath,integerPath,output]=process.argv.slice(2),read=n=>JSON.parse(fs.readFileSync(dir+'/'+n));
const mods=read('compiled/modules.json'),native=read('native.json'),material=read('compiled/materialized.json'),NIL=77825,T=77838,tcr=1024,ROOT=131064,OUT=139264;
const bytes=fs.readFileSync(collectorPath),digest=createHash('sha256').update(bytes).digest('hex'),integerBytes=fs.readFileSync(integerPath),integerDigest='a56d7f7ff3d5472d9a72f28ea93bc00f521d52a45b15f9b47b5cda4a29c58f59';
assert.equal(createHash('sha256').update(integerBytes).digest('hex'),integerDigest,'retained integer service pin');
const modules=new Map(mods.map(m=>[m.name,new WebAssembly.Module(fs.readFileSync(dir+'/compiled/'+m.name+'.wasm'))]));
const admission=[];
for(const m of mods){
 const b=fs.readFileSync(dir+'/compiled/'+m.name+'.wasm');
 assert.deepEqual(WebAssembly.Module.imports(modules.get(m.name)).filter(x=>x.kind==='function'),[{module:'integer',name:'calculate',kind:'function'}]);
 assert.throws(()=>inspect(b),/FUNCTION_IMPORT/);admission.push(m.name);
}
const rows=[];
for(const scenario of [{high:false,collect:false},{high:false,collect:true},{high:true,collect:false},{high:true,collect:true},{high:false,collect:true,tiny:true},{high:true,collect:true,tiny:true}]){
 const {high,collect,tiny}=scenario;
 const A=high?2147483648:2097152,B=A+32768,cap=tiny?32:32768;
 const memory=new WebAssembly.Memory({initial:high?32769:48,maximum:32769,shared:true});
 const get=p=>new DataView(memory.buffer).getUint32(p,true),store=(p,v)=>new DataView(memory.buffer).setUint32(p,v,true),set=(o,v)=>store(tcr+o,v),t=o=>get(tcr+o);
 const table=new WebAssembly.Table({element:'anyfunc',initial:mods.length+1}),tail_table=new WebAssembly.Table({element:'anyfunc',initial:mods.length+1});
 const call_error=new WebAssembly.Tag({parameters:['i32']}),type_error=new WebAssembly.Tag({parameters:['i32','i32']}),nonlocal_exit=new WebAssembly.Tag({parameters:['i32']});
 new Uint8Array(memory.buffer,material.base,material.image.length/2).set(Buffer.from(material.image,'hex'));
 let imageTop=8*Math.ceil((material.base+material.image.length/2)/8);const images=[{name:'pools',role:'image',start:material.base,end:imageTop}];
 const alloc=n=>{const p=imageTop;imageTop+=n;images.push({name:'image-'+p,role:'image',start:p,end:p+n});return p;};
 const symbol=()=>{const p=alloc(32);store(p,1850);for(let j=1;j<8;j++)store(p+4*j,NIL);store(p+28,0);return p+6;};
 const symbols={},keywords={},codes={},handles={};
 mods.forEach((m,i)=>{codes[m.name]=4*(i+1);if(m.top){const p=alloc(32),pool=material.roots[i];[1578,codes[m.name],NIL,4,get(pool-2),get(pool+2),pool,0].forEach((v,j)=>store(p+4*j,v));handles[m.name]=p+6;symbols[m.name]=symbol();store(symbols[m.name]+6,p+6);}});
 for(const mod of modules.values())for(const imp of WebAssembly.Module.imports(mod)){
  if(imp.module==='symbols'&&symbols[imp.name]===undefined)symbols[imp.name]=symbol();
  if(imp.module==='keywords'&&keywords[imp.name]===undefined)keywords[imp.name]=symbol();
 }
 for(const [i,n] of ['condition_handlers','condition_restarts','debugger_hook'].entries())if(symbols[n])store(symbols[n]+22,4*(i+3));
 const vector=(values,tag=250)=>{const p=alloc(8*Math.ceil((4+4*values.length)/8));store(p,256*values.length+tag);values.forEach((v,i)=>store(p+4+4*i,v));return p+6;};
 const string=text=>{const p=alloc(8*Math.ceil((4+4*text.length)/8));store(p,256*text.length+191);Array.from(text).forEach((c,i)=>store(p+4+4*i,c.codePointAt(0)));return p+6;};
 const names=['CONDITION','SIMPLE-CONDITION','SIMPLE-ERROR','TYPE-ERROR','CONTROL-ERROR','SIMPLE-WARNING','PROGRAM-ERROR','SIMPLE-PROGRAM-ERROR','UNDEFINED-FUNCTION','UNBOUND-VARIABLE','STORAGE-CONDITION','ERROR','NO-APPLICABLE-METHOD-EXISTS','ARITHMETIC-ERROR','DIVISION-BY-ZERO'];
 const masks=[1,9,31,39,71,393,519,527,1031,2055,4099,7,8199,16391,49159];
 const slots=[[],['FORMAT-CONTROL','FORMAT-ARGUMENTS'],['FORMAT-CONTROL','FORMAT-ARGUMENTS'],['DATUM','EXPECTED-TYPE','FORMAT-CONTROL'],[],['FORMAT-CONTROL','FORMAT-ARGUMENTS'],[],['FORMAT-CONTROL','FORMAT-ARGUMENTS','CONTEXT'],['NAME','ERROR-TYPE'],['NAME','ERROR-TYPE'],[],[],['GF','ARGS'],['OPERATION','OPERANDS','STATUS'],['OPERATION','OPERANDS','STATUS']];
 const shapes=read('compiled/native-condition-classes.json');assert.equal(shapes.length,15);
 symbols.condition_registry=vector(shapes.map((shape,i)=>{
  assert.equal(shape.name,names[i]);assert.deepEqual(shape.slots.map(s=>s.name),slots[i]);
  const name=symbol(),wrapperName=symbol(),fields=vector(shape.slots.map(()=>symbol())),defaults=vector(shape.slots.map(s=>s.default===null?NIL:typeof s.default==='string'?string(s.default):83));
  const instance=alloc(16);store(instance,882);store(instance+4,0);store(instance+8,NIL);store(instance+12,vector([instance+6,name,NIL],106));
  const wrapper=vector([wrapperName,4*i,instance+6,fields,NIL,NIL,NIL,NIL,NIL,NIL,NIL,4*i,masks[i]*4]);
  return vector([wrapper,masks[i]*4,defaults]);
 }));symbols.error_message=string('Checked Lisp runtime operation failed.');
 store(NIL-1,NIL);store(NIL+3,NIL);store(T-6,1850);for(let i=1;i<8;i++)store(T-6+4*i,NIL);
 store(4096,mods.length+1);store(4100,1);mods.forEach((m,i)=>[i+1,4,17,23].forEach((v,j)=>store(4104+16*(i+1)+4*j,v)));
 set(48,A);set(52,A+cap);set(56,A);set(68,ROOT+8);set(72,163840);set(64,ROOT+8);set(128,ROOT);store(ROOT,0);store(ROOT+4,0);
 set(80,196608);set(76,196608);set(84,229376);set(92,229376);set(88,229376);set(96,245760);set(104,266240);set(108,8);for(let i=0;i<8;i++)store(266240+4*i,243);set(188,NIL);set(120,OUT);set(124,OUT+64);
 const regions=[['tcr',1024,1280],['external',4096,16384],['image',77824,77864],['vstack',ROOT,163840],['temp',196608,229376],['control',229376,245760],['bindings',266240,270336],['c-stack',1048576,1114112],['root-list',1180000,1200000],['scratch',1200000,1800000]].map(([role,start,end],i)=>({name:role+i,role,start,end}));
 const layout={version:1,collector:'copying',workers:1,egc:false,tcr,maximumPages:32769,logCapacity:32768,regions:[...regions,...images],spaces:[{name:'a',start:A,end:A+cap},{name:'b',start:B,end:B+cap}],groups:['module-constants','callbacks','registry','host'].map(kind=>({kind,slots:[]}))};
 const owner=CollectorOwner.create(memory,bytes,digest,layout),service=integerService({memory,tcr,owner,callError:call_error,bytes:integerBytes,digest:integerDigest,pinned:images});
 let slow=0,moves=0,growths=0;const fast=[];
 const calculate=(op,root)=>{
  slow++;const from=t(56),spaces=owner.spaces;
  if(collect){for(let p=t(48);p<t(52);p+=8){store(p,NIL);store(p+4,0);}set(48,t(52));}
  let count,error;try{count=service(op,root);}catch(e){error=e;}
  if(t(56)!==from){const grew=!spaces.some(s=>s.start===t(56));moves+=grew?2:1;if(grew)growths++;for(const s of spaces)if(s.start!==t(56))new Uint8Array(memory.buffer,s.start,s.end-s.start).fill(0xdd);}
  if(error)throw error;return count;
 };
 const entries={};for(const [i,m] of mods.entries()){
  const instance=new WebAssembly.Instance(modules.get(m.name),{env:{memory,tcr,table,tail_table,code_registry:4096,call_error,type_error,nonlocal_exit},symbols,keywords,codes,integer:{calculate}});
  entries[m.name]=instance.exports.entry;table.set(i+1,instance.exports.entry);tail_table.set(i+1,instance.exports.tail_entry);
 }
 const encode=s=>{if(s==='nil')return NIL;if(s==='t')return T;if(typeof s==='object'){const car=encode(s.cons),p=t(48);assert(p+8<=t(52));store(p,NIL);store(p+4,car);set(48,p+8);return p+1;}let n=BigInt(s);if(n>=-536870912n&&n<=536870911n)return Number(BigInt.asUintN(32,n<<2n));let width=1;while(n<-(1n<<BigInt(width*32-1))||n>=(1n<<BigInt(width*32-1)))width++;const size=8*Math.ceil((4+4*width)/8),p=t(48);assert(p+size<=t(52));store(p,width*256+7);n=BigInt.asUintN(width*32,n);for(let i=0;i<width;i++){store(p+4+4*i,Number(n&0xffffffffn));n>>=32n;}set(48,p+size);return p+6;};
 const decode=v=>{if(v===NIL)return 'NIL';if(v===T)return 'T';if(v%4===0)return String((v>=2**31?v-2**32:v)/4);assert.equal(v%8,6);const p=v-6,h=get(p),n=Math.floor(h/256);assert.equal(h%256,7);let x=0n;for(let i=n-1;i>=0;i--)x=(x<<32n)|BigInt(get(p+4+4*i));return String(BigInt.asIntN(n*32,x));};
 for(const c of native){
  if(tiny&&c.function!=='n_literal')continue;
  set(48,t(56));set(64,ROOT+8);set(128,ROOT);set(120,OUT);set(124,OUT+64);set(140,0);set(148,0);set(192,0);set(76,196608);store(ROOT+4,c.args.length);c.args.forEach((v,i)=>store(ROOT+8+4*i,encode(v)));
  const before=slow;let pair;try{pair=entries[c.function](handles[c.function],c.args.length);}catch(e){if(e.is?.(call_error)){if(tiny&&high&&e.getArg(call_error,0)===6){assert(moves>0,'refusal after collection');assert.equal(t(128),ROOT);assert.equal(t(64),ROOT+8);rows.push({high,collect,tiny,refusal:6,moves});continue;}throw Error(c.function+'/'+c.id+' code '+e.getArg(call_error,0));}throw e;}
  const values=Array.from({length:pair[1]},(_,i)=>decode(get(OUT+4*i)));assert.deepEqual(values,c.expected,c.function+'/'+c.id);
  assert.equal(t(128),ROOT,'roots restored');assert.equal(t(64),ROOT+8,'VSP restored');assert.equal(t(140),0,'handlers restored');
  if(['n_add','n_sub','n_mul','n_ash','n_length','n_truncate'].includes(c.function)){
   const input=c.args.map(BigInt),output=c.expected.map(BigInt),fix=x=>x>=-536870912n&&x<=536870911n;
   if(input.every(fix)&&output.every(fix)){
    // ASH's deliberately conservative fast path also requires <=29 for a
    // positive count unless its operand is zero.
    if(c.function!=='n_ash'||input[1]<=29n||input[0]===0n){assert.equal(slow,before,'inline '+c.function+'/'+c.id);fast.push(c.function);}
   }
  }
  for(let i=3;i<=5;i++)assert.equal(get(266240+4*i),243,'binding vector restored');
 }
 if(!tiny){
  const refusals=[];
  for(const [name,fn,args,code] of [['zero-divisor','n_truncate',[4,0],34],['noninteger','n_add',[NIL,4],5],['input-budget','n_ash',[4,131072],33]]){
   set(48,t(56));set(64,ROOT+8);set(128,ROOT);set(120,OUT);set(124,OUT+64);store(ROOT+4,args.length);args.forEach((v,i)=>store(ROOT+8+4*i,v));let error;
   try{entries[fn](handles[fn],args.length);}catch(e){assert(e.is?.(call_error));error=e.getArg(call_error,0);}
   assert.equal(error,code,name);assert.equal(t(128),ROOT);assert.equal(t(64),ROOT+8);refusals.push({name,code});
  }
  // Refuse a host attempt to nest collecting numeric work in the owner boundary.
  set(48,t(56));set(64,ROOT+8);set(128,ROOT);store(ROOT+4,0);let error;
  try{owner.atSafepoint(()=>entries.n_literal(handles.n_literal,0));}catch(e){assert(e.is?.(call_error));error=e.getArg(call_error,0);}
  assert.equal(error,6,'nested boundary');assert.equal(t(128),ROOT);
  assert.equal(new Set(fast).size,6);rows.push({high,collect,cases:native.length,slow,moves,growths,modules:mods.length,refusals,nested:6,inline_checks:fast.length,inline_operations:[...new Set(fast)].sort()});
 }else if(!high){assert(growths>0);rows.push({high,collect,tiny,cases:1,slow,moves,growths});}
}
fs.writeFileSync(output,JSON.stringify({status:'PASS',admission,rows},null,2)+'\n');
